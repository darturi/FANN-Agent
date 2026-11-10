"""Split integrity, causal observations, scientific gates and submission safety."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(Path(sys.argv[1]).resolve()/'vendor') if len(sys.argv)>1 else '/nonexistent',
             str(ROOT/'trials/torch-reviews-first/sources')]
if len(sys.argv)>1:sys.argv=sys.argv[:1]
import contract
import control
from execution import expected_progress,bypass108,timing_pair,Budget
from package import inventory
from policy_tools import assess,policy


def stub_record(campaign,package):
    return {'account':'torch_pr_test','campaign':str(campaign),'package':str(package),'bundle':'/bundle',
      'prepared':'/prepared','workspace':'/scratch','sources':'/sources','apptainer':'/apptainer',
      'jobs':{'fit':'100'},'dispatch':{},'status':'awaiting_calibration'}


def finished_files(campaign,phase):
    folder=campaign/phase;folder.mkdir(parents=True,exist_ok=True)
    for name,value in [('host-exit.json',{'exit_code':0}),('job-exit.json',{'exit_code':0}),('status.json',{'status':'complete'})]:
        (folder/name).write_text(json.dumps(value))


class StudyTests(unittest.TestCase):
    def test_disjoint_development_only_inventory(self):
        selected,split=inventory();roles=split['selected_catalog_groups']
        self.assertEqual({k:len(v) for k,v in roles.items()},
          {'original_learning':100,'additional_learning':60,'calibration':40,'evaluation':60,'reserved':37})
        groups=[g for values in roles.values() for g in values]
        self.assertEqual(len(groups),len(set(groups)))
        self.assertEqual(len(set(split['vector_hash_by_catalog_group'].values())),len(groups))
        self.assertEqual(selected['reserved'],[])
        old=json.loads((ROOT/'trials/torch-reviews-policy-learning/inputs/split-provenance.json').read_text())
        blocked=set(old['excluded_previously_used_groups'])|{g for g,r in old['selection'].items() if r=='confirmation'}
        self.assertFalse(set(groups)&blocked)

    def test_search_algorithm_frozen(self):
        original=(ROOT/'agent/experiments/offline-first-stop-fitter-v1/first_stop.py').read_text()
        current=(HERE/'tree_search.py').read_text().replace('from contract import SEARCH as DESIGN, digest','from offline_common import DESIGN, digest').replace('from policy_tools import guard','from fitting import guard').replace("['progress_filter']","['local_filter']")
        self.assertEqual(ast.dump(ast.parse(original)),ast.dump(ast.parse(current)))

    def test_budget_counts_and_limits(self):
        a=contract.accounting()
        self.assertEqual(a['maximum_campaign_backend_calls'],155766)
        self.assertEqual(a['acquisition_backend_calls_per_shard_maximum'],39321)
        self.assertEqual(a['evaluation_backend_calls_maximum'],24681)
        self.assertEqual(a['timing_backend_calls_per_block'],17481)
        self.assertEqual(a['timing_retained_pairs_total'],17280)
        self.assertTrue(all(a[k]<70000 for k in ['acquisition_backend_calls_per_shard_maximum','evaluation_backend_calls_maximum','timing_backend_calls_per_block']))

    def test_progress_excludes_future_windows(self):
        receipt={'fetches':[2,1,0,0,0,0,0,0],'rows':[[1,1,120,False,.4],[1,2,0,False,.1],[2,3,120,False,.05]]}
        first=expected_progress(receipt,1,108);later=expected_progress(receipt,2,108)
        self.assertEqual(first['progress_probe_examined'],2)
        self.assertEqual(first['progress_probe_passed'],1)
        self.assertEqual(first['progress_valid_distance_min_or_zero'],.4)
        self.assertEqual(later['progress_recent_examined'],1)
        self.assertAlmostEqual(later['progress_valid_min_improvement_or_zero'],.35)

    def test_empty_progress_is_explicitly_exposed(self):
        r=expected_progress({'fetches':[1,0,0,0,0,0,0,0],'rows':[[1,1,0,True,.1]]},1,108)
        self.assertFalse(r['progress_has_valid']);self.assertEqual(r['progress_probe_examined'],1)
        self.assertEqual(r['progress_probe_pass_ratio'],0.)
        self.assertEqual(r['progress_valid_distance_mean_or_zero'],0.)

    def test_unfiltered_null_metadata_still_passes(self):
        r=expected_progress({'fetches':[1,0,0,0,0,0,0,0],'rows':[[1,1,0,True,.1]]},1,0)
        self.assertTrue(r['progress_has_valid']);self.assertEqual(r['progress_probe_passed'],1)

    def test_routing_uses_actual_predicate(self):
        self.assertTrue(bypass108({'id':'anything-unfiltered','filter':{'field':'m_000000','op':'gte','value':108}}))
        self.assertFalse(bypass108({'id':'anything-votes108','filter':None}))
        self.assertFalse(bypass108({'filter':{'field':'m_000000','op':'gte','value':32}}))
        with self.assertRaises(ValueError):bypass108({'filter':{'field':'other','op':'gte','value':108}})

    def test_final_gate_is_per_filter(self):
        rows=[]
        for g in range(40):
            for f in contract.CONFIG['filters']:
                rows.append({'group':str(g),'stratum':f,'recall_delta':-.006 if f=='votes108' else 0,
                  'native_recall':1.,'valid':True,'activation_proxy_ms_saved':1.,'reuse_proxy_ms_saved':1.})
        r=assess(rows,.005)
        self.assertGreaterEqual(r['reports']['overall']['recall_delta_ci95'][0],-.005)
        self.assertFalse(r['recall_pass'])
        self.assertLess(r['reports']['votes108']['recall_delta_ci95'][0],-.005)

    def test_native_floor_and_completeness_are_required(self):
        rows=[{'group':str(g),'stratum':f,'recall_delta':0.,'native_recall':.94 if f=='votes108' else 1.,
          'valid':True,'activation_proxy_ms_saved':1.,'reuse_proxy_ms_saved':1.} for g in range(40) for f in contract.CONFIG['filters']]
        self.assertFalse(assess(rows,.005)['recall_pass'])
        for r in rows:r.update(native_recall=1.)
        rows[0]['valid']=False
        self.assertFalse(assess(rows,.005)['recall_pass'])

    def test_both_timing_proxies_required(self):
        rows=[{'group':str(g),'stratum':f,'recall_delta':0.,'native_recall':1.,'valid':True,
          'activation_proxy_ms_saved':1.,'reuse_proxy_ms_saved':-.1} for g in range(40) for f in contract.CONFIG['filters']]
        r=assess(rows)
        self.assertTrue(r['recall_pass']);self.assertLess(r['utility'],0)

    def test_dispatch_binding_precedes_scheduler(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp);p=c/'package';p.mkdir();r=stub_record(c,p)
            def scheduler(*args,**kwargs):
                self.assertEqual(json.loads((c/'submission.json').read_text())['dispatch']['evaluate']['status'],'dispatching')
                return subprocess.CompletedProcess(args[0],0,'456;torch\n','')
            with patch('control.subprocess.run',side_effect=scheduler) as run:
                self.assertEqual(control.dispatch(p,c,r,'evaluate','evaluate',dependency='100'),'456')
                with self.assertRaises(ValueError):control.dispatch(p,c,r,'evaluate','evaluate')
                self.assertEqual(run.call_count,1)

    def test_unknown_dispatch_cannot_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp);r=stub_record(c,c)
            with patch('control.subprocess.run',return_value=subprocess.CompletedProcess([],0,'unparseable\n','')) as run:
                with self.assertRaises(ValueError):control.dispatch(c,c,r,'evaluate','evaluate')
                with self.assertRaises(ValueError):control.dispatch(c,c,r,'evaluate','evaluate')
                self.assertEqual(run.call_count,1)
            self.assertEqual(json.loads((c/'submission.json').read_text())['dispatch']['evaluate']['status'],'unknown')

    def test_failed_calibration_submits_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp);p=c/'package';p.mkdir();r=stub_record(c,p);(c/'submission.json').write_text(json.dumps(r))
            for phase in ('build','acquire/part-0','acquire/part-1','fit'):finished_files(c,phase)
            with patch('control.verify'),patch('execution.validate_fit',return_value={'proceed_to_evaluation':False}),patch('control.subprocess.run') as run:
                control.advance(p,c);run.assert_not_called()
            self.assertEqual(json.loads((c/'submission.json').read_text())['status'],'stopped_after_calibration')

    def test_failed_evaluation_submits_no_timing(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp);p=c/'package';p.mkdir();r=stub_record(c,p);r['jobs']['evaluate']='456';(c/'submission.json').write_text(json.dumps(r))
            for phase in ('build','acquire/part-0','acquire/part-1','fit','evaluate'):finished_files(c,phase)
            (c/'fit/fit-lock.json').write_text('{}')
            (c/'evaluate/screen.json').write_text(json.dumps({'fit_lock_sha256':contract.sha(c/'fit/fit-lock.json'),'proceed_to_timing':False}))
            with patch('control.verify'),patch('execution.validate_fit',return_value={'proceed_to_evaluation':True}),patch('control.subprocess.run') as run:
                control.advance(p,c);run.assert_not_called()
            self.assertEqual(json.loads((c/'submission.json').read_text())['status'],'stopped_after_evaluation')

    def test_successful_gates_submit_once_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp);p=c/'package';p.mkdir();r=stub_record(c,p)
            (c/'submission.json').write_text(json.dumps(r))
            for phase in ('build','acquire/part-0','acquire/part-1','fit'):finished_files(c,phase)
            calls=[]
            def scheduler(args,**kwargs):
                calls.append(args)
                return subprocess.CompletedProcess(args,0,str(455+len(calls))+';torch\n','')
            with patch('control.verify'),patch('execution.validate_fit',return_value={'proceed_to_evaluation':True}),patch('control.subprocess.run',side_effect=scheduler):
                control.advance(p,c)
                self.assertEqual(len(calls),1)
                self.assertIn('--dependency=afterok:100',calls[0])
                finished_files(c,'evaluate');(c/'fit/fit-lock.json').write_text('{}')
                (c/'evaluate/screen.json').write_text(json.dumps({'fit_lock_sha256':contract.sha(c/'fit/fit-lock.json'),'proceed_to_timing':True}))
                control.advance(p,c);control.advance(p,c)
            self.assertEqual(len(calls),3)
            self.assertIn('--array=0',calls[1]);self.assertIn('--dependency=afterok:456',calls[1])
            self.assertIn('--array=1-2%1',calls[2]);self.assertIn('--dependency=afterok:457',calls[2])
            self.assertEqual(json.loads((c/'submission.json').read_text())['status'],'timing_submitted')

    def test_host_imports_need_no_third_party_packages(self):
        package=Path(__import__('fannagent_pgvector').__file__).resolve().parents[2]
        result=subprocess.run([sys.executable,'-S','-c',
          'import sys;sys.path.insert(0,sys.argv[1]);import control,execution,job',str(package)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_resealing_cannot_change_final_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);cfg=copy.deepcopy(contract.CONFIG);cfg['recall_tolerance']=.01
            (p/'experiment.json').write_text(json.dumps(cfg))
            (p/'manifest.json').write_text(json.dumps({'files':{'experiment.json':contract.sha(p/'experiment.json')}}))
            with self.assertRaisesRegex(ValueError,'Declared design changed: recall_tolerance'):control.verify(p)

    def test_provider_import_guard(self):
        result=subprocess.run([sys.executable,'-c',
          'import sys;sys.path.insert(0,sys.argv[1]);from no_models import enforce;enforce();import openai',str(HERE)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Provider/model imports are forbidden in this study: openai',result.stderr)

    def test_real_native_bypass_has_no_policy_counters(self):
        backend=SimpleNamespace(validate_policy=lambda raw:SimpleNamespace(policy_hash='fixture-hash'))
        native=SimpleNamespace(ids=list(range(10)),distances=[i/10 for i in range(10)],latency_ms=2.,metadata={})
        frozen=SimpleNamespace(score=lambda truth,result:{'valid':True,'recall':1.})
        truth=SimpleNamespace(strictly_better=set(range(9)),boundary_ties={9},effective_k=10)
        q={'id':'fixture-votes108','filter':{'field':'m_000000','op':'gte','value':108}}
        with patch('execution.execute',return_value=native) as execute:
            r=timing_pair(frozen,backend,Budget(2),q,truth,policy('fixture'),__import__('random').Random(1),
              {'policy_already_activated':None,'regime':'activation-cold'},True)
        self.assertTrue(r['native_bypass']);self.assertIsNone(r['work'])
        self.assertIsNone(r['policy_hash']);self.assertFalse(r['work_available'])
        self.assertTrue(all(call.args[3] is None for call in execute.call_args_list))
        from report import validate_row
        validate_row(r,r)
        from study_stats import summary
        values=summary([r,{**r,'group':'fixture-second'}],{**contract.CONFIG,'seed':20261019})
        self.assertIsNone(values['collection_ms']);self.assertIsNone(values['layer0_distances'])
        self.assertEqual(values['recall_delta'],0)

    def test_final_statistics_only_add_unavailable_work_support(self):
        original=(ROOT/'trials/torch-reviews-results/four-condition-training-v1/torch-four-condition-training-v1/study_stats.py').read_text()
        current=(HERE/'study_stats.py').read_text().replace("None if any(r['work'] is None for r in rows) else ",'')
        self.assertEqual(ast.dump(ast.parse(original)),ast.dump(ast.parse(current)))

    def test_contract_and_original_ab_unchanged(self):
        self.assertEqual(contract.AB,{'status':'inconclusive','complete_pairs':0,'selection_effect_established':False})
        self.assertEqual(contract.CONFIG['recall_tolerance'],.005)
        self.assertEqual(contract.CONFIG['development_recall_margin'],.0025)
        self.assertEqual(contract.CONFIG['minimum_native_recall'],.95)
        self.assertEqual(contract.CONFIG['bootstrap_samples'],10000)
        self.assertEqual(contract.CONFIG['bootstrap_seed'],20261019)


if __name__=='__main__':unittest.main(verbosity=2)
