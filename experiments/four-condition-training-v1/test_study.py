"""Meaningful leakage, policy semantics, budget and submission regressions."""
import copy
import importlib.abc
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
PREVIEW=Path(os.environ['FOUR_TEST_PACKAGE'])
sys.path[:0]=[str(HERE),str(PREVIEW),str(PREVIEW/'vendor')]
from no_models import enforce
enforce()
from contract import CONFIG,CONDITIONS,EXTRA,GROUPS,accounting,digest,folds,read,sha
import control
import fitting
from fannagent_pgvector.profiles import PROFILE


def synthetic_rows():
    names=read(PREVIEW/'experiment.json')['base_feature_names'];rows=[]
    for i in range(100):
        for f,t in [('unfiltered',0),('votes32',32),('votes108',108)]:
            states=[]
            for cp in range(1,130):
                values={n:(.3 if PROFILE.runtime_features[n].kind=='float' else 10) for n in names}
                values.update(checkpoint_index=cp,frontier_count=i,completed_expansions=cp,
                    query_predicate_threshold=t,local_probe_examined=64,local_probe_passed=32,local_probe_pass_ratio=.5)
                states.append({'checkpoint_index':cp,'features':values})
            labels={str(cp):{'recall':1. if i<70 else .9,'valid':True,'returned_count':10,
                'layer0_distances':64*cp,'activation_ms_saved':1.,'reuse_ms_saved':1.} for cp in (1,2,4,8,16,32,64,128)}
            rows.append({'query_id':f'g{i:03}-{f}','group':f'g{i:03}','stratum':f,'native_recall':1.,'native_work':10000,
                'base_states':states,'local_states':states,'labels':{'base':labels,'local':labels},
                'continue_costs':{'base':{'activation_ms_saved':-1.,'reuse_ms_saved':-1.},'local':{'activation_ms_saved':-1.,'reuse_ms_saved':-1.}}})
    return names,rows


class StudyTests(unittest.TestCase):
    def test_exact_accounting_and_resource_limits(self):
        a=accounting();self.assertEqual((a['allocations'],a['acquisition_maximum_backend_calls'],a['measurement_maximum_backend_calls_per_block'],a['retained_pairs_total']),(5,38910,44610,46800))
        self.assertLess(a['measurement_maximum_backend_calls_per_block'],70000)

    def test_factorial_changes_only_declared_factors(self):
        self.assertEqual(CONDITIONS['A']['checkpoints'],CONDITIONS['C']['checkpoints'])
        self.assertEqual(CONDITIONS['B']['checkpoints'],CONDITIONS['D']['checkpoints'])
        self.assertFalse(CONDITIONS['A']['local_filter']);self.assertTrue(CONDITIONS['C']['local_filter'])

    def test_early_and_late_guards_use_shared_interpreter(self):
        _,rows=synthetic_rows();ss=rows[0]['local_states']
        for condition,want in [('A',32),('B',1),('C',32),('D',1)]:
            raw={'name':condition,'root':fitting.guard('stop',CONDITIONS[condition]['checkpoints']),
                'feature_groups':GROUPS+(['local_filter'] if CONDITIONS[condition]['local_filter'] else [])}
            self.assertEqual(fitting.predict(raw,ss,PROFILE),want)

    def test_missing_observation_continues(self):
        raw={'name':'missing','root':fitting.guard({'if':{'op':'gt','args':[{'feature':'local_probe_pass_ratio'},{'float':.1}]},'then':'stop','else':'continue'},[1]),'feature_groups':GROUPS+['local_filter']}
        states=[{'checkpoint_index':1,'features':{'checkpoint_index':1,'local_probe_pass_ratio':None}}]
        self.assertIsNone(fitting.predict(raw,states,PROFILE))

    def test_outer_fold_labels_do_not_change_its_fit(self):
        names,rows=synthetic_rows();mapping=folds([q['group'] for q in rows],5,'outer-v1');train=sorted(g for g,f in mapping.items() if f!=0)
        raw,_=fitting.fit(rows,'D',80.,PROFILE,names,train)
        changed=copy.deepcopy(rows)
        for q in changed:
            if mapping[q['group']]==0:
                for family in q['labels'].values():
                    for label in family.values():label['recall']=0.;label['activation_ms_saved']=-1000.
                for s in q['local_states']:s['features']['frontier_count']=10**6
        other,_=fitting.fit(changed,'D',80.,PROFILE,names,train)
        self.assertEqual(raw,other)

    def test_group_folds_are_balanced_and_repeatable(self):
        groups=[str(i) for i in range(100)];f=folds(groups,5,'outer-v1')
        self.assertEqual(f,folds(reversed(groups),5,'outer-v1'))
        self.assertEqual([sum(v==i for v in f.values()) for i in range(5)],[20]*5)

    def test_full_nested_lock_has_no_outer_or_inner_group_leakage(self):
        names,rows=synthetic_rows();e={'base_feature_names':names,'queries':rows}
        lock=fitting.build_lock(e,PROFILE,'synthetic-manifest','synthetic-module')
        self.assertEqual(len(lock['policies']),20)
        for key,p in lock['policies'].items():
            self.assertEqual((len(p['training_groups']),len(p['held_out_groups'])),(80,20))
            self.assertFalse(set(p['training_groups'])&set(p['held_out_groups']))
        for v in lock['nested_validation']:
            outer=lock['policies'][v['condition']+'/'+str(v['outer_fold'])]['held_out_groups']
            for trial in v['trials']:
                for p in trial['fit_proofs']:
                    self.assertEqual((len(p['training_groups']),len(p['validation_groups'])),(60,20))
                    self.assertFalse(set(p['training_groups'])&(set(p['validation_groups'])|set(outer)))

    def test_training_only_inventory(self):
        qs=[json.loads(s) for s in (PREVIEW/'inputs/queries.jsonl').read_text().splitlines()]
        self.assertEqual((len(qs),len({q['group'] for q in qs})),(300,100))
        self.assertEqual({q['split'] for q in qs},{'learning'})
        self.assertEqual(CONFIG['confirmation_queries_allowed'],0)

    def test_inner_margin_is_separate_from_final_criterion(self):
        self.assertEqual(CONFIG['recall_tolerance'],.005);self.assertEqual(CONFIG['development_recall_margin'],.0025)
        self.assertEqual(CONFIG['bootstrap_samples'],10000);self.assertEqual(CONFIG['seed'],20261019)
        self.assertEqual(CONFIG['ab_comparison']['status'],'inconclusive')

    def test_unknown_measurement_is_rejected(self):
        _,rows=synthetic_rows();q=rows[0];q=copy.deepcopy(q);q['labels']['base'].pop('32')
        raw={'name':'unknown','root':fitting.guard('stop',[32]),'feature_groups':GROUPS}
        with self.assertRaisesRegex(ValueError,'Unknown actual first stop'):fitting.outcome(q,raw,'A',PROFILE)

    def test_provider_import_guard(self):
        with self.assertRaisesRegex(RuntimeError,'forbidden'):__import__('openai')

    def test_partial_submission_binding_prevents_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'submission-binding.json').write_text('{}')
            with patch.object(control,'verify',return_value=CONFIG),self.assertRaisesRegex(ValueError,'Existing submission binding'):
                control.submit(p,p,p)

    def test_unknown_job_response_rejected(self):
        for s in ('','Submitted batch job 123','123\n456','0','123;other'):
            with self.assertRaises(ValueError):control.job_id(s)
        self.assertEqual(control.job_id('123;torch\n'),'123')

    def submission_fixture(self,root):
        p=root/'package';p.mkdir();sources=root/'sources';sources.mkdir();bundle=root/'bundle';bundle.mkdir()
        prepared=root/'prepared';prepared.mkdir();(root/'bin').mkdir();apptainer=root/'bin/apptainer';apptainer.write_text('#!/bin/sh\n');apptainer.chmod(0o755)
        module=sources/'old/build/modules/new-vector.so';module.parent.mkdir(parents=True);module.write_bytes(b'synthetic-module')
        identity={'synthetic':True}
        (p/'source-index.json').write_text(json.dumps(identity));(prepared/'database-identity.json').write_text(json.dumps(identity))
        (prepared/'READY.json').write_text(json.dumps({'architecture':'x86_64','image_sha256':CONFIG['image_sha256']}))
        (p/'manifest.json').write_text('{"files":{}}')
        cfg={**CONFIG,'source_prepared':str(prepared),'collector_campaign':'old','original_module_sha256':sha(module),'complete_call_accounting':accounting()}
        env={'TORCH_SLURM_ACCOUNT':'torch_pr_test','TORCH_SCRATCH_ROOT':str(root/'scratch'),'TORCH_RESULTS_ROOT':str(root/'results'),'TORCH_APPTAINER_BIN':str(apptainer)}
        return p,bundle,sources,cfg,env

    def test_submission_chain_and_binding_are_durable(self):
        import contextlib,io
        with tempfile.TemporaryDirectory() as d:
            p,bundle,sources,cfg,env=self.submission_fixture(Path(d));commands=[]
            def run(cmd,**kwargs):
                if '--test-only' in cmd:return SimpleNamespace(returncode=0)
                self.assertTrue((p/'submission-binding.json').exists())
                commands.append(cmd);return SimpleNamespace(returncode=0,stdout=str(900+len(commands)-1),stderr='')
            with patch.dict(os.environ,env),patch.object(control,'verify',return_value=cfg),patch('protected.check',return_value={}),patch.object(control.subprocess,'run',side_effect=run),contextlib.redirect_stdout(io.StringIO()):
                control.submit(p,bundle,sources)
            self.assertEqual(len(commands),4)
            self.assertIn('--dependency=afterok:900',commands[1]);self.assertIn('--dependency=afterok:901',commands[2]);self.assertIn('--dependency=afterok:902',commands[3])
            self.assertIn('--array=0',commands[2]);self.assertIn('--array=1-2%1',commands[3])
            campaign=Path(read(p/'submission-binding.json')['campaign'])
            self.assertEqual(read(campaign/'submission.json')['status'],'submitted')

    def test_unknown_submission_remains_bound_without_retry(self):
        import contextlib,io
        with tempfile.TemporaryDirectory() as d:
            p,bundle,sources,cfg,env=self.submission_fixture(Path(d))
            def run(cmd,**kwargs):
                return SimpleNamespace(returncode=0,stdout='unrecognized scheduler reply',stderr='')
            with patch.dict(os.environ,env),patch.object(control,'verify',return_value=cfg),patch('protected.check',return_value={}),patch.object(control.subprocess,'run',side_effect=run),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(ValueError):
                control.submit(p,bundle,sources)
            campaign=Path(read(p/'submission-binding.json')['campaign'])
            self.assertEqual(read(campaign/'submission.json')['status'],'submission_unknown')

    def test_resealing_does_not_change_final_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);cfg={**CONFIG,'recall_tolerance':.01};(p/'experiment.json').write_text(json.dumps(cfg))
            (p/'manifest.json').write_text(json.dumps({'files':{'experiment.json':sha(p/'experiment.json')}}))
            with self.assertRaisesRegex(ValueError,'recall_tolerance'):control.verify(p)

    def test_native_source_is_opt_in_and_bounded(self):
        c=(PREVIEW/'engine/src/fannbench.c').read_text();u=(PREVIEW/'engine/src/hnswutils.c').read_text()
        self.assertIn('executionState.localProbeNodes < 64',c)
        self.assertIn('executionState.localProbeExamined < 64',c)
        self.assertIn('distance != NULL && FannbenchLocalProbeEnabled()',u)
        self.assertIn('GetActiveSnapshot()',c)

    def test_package_manifest_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'experiment.json').write_text(json.dumps(CONFIG));(p/'manifest.json').write_text(json.dumps({'files':{'experiment.json':sha(p/'experiment.json')}}))
            self.assertEqual(control.verify(p)['recall_tolerance'],.005)
            (p/'experiment.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'changed'):control.verify(p)


if __name__=='__main__':unittest.main(verbosity=2)
