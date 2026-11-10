"""Synthetic checks of first-stop semantics, grouping, leakage and fixed gates."""
import copy
import sys
import unittest

from offline_common import AB, DESIGN, initialize
initialize()
import numpy as np
from fannagent_pgvector.profiles import PROFILE
from fitting import guard, predict
from first_stop import compile_tree, first_indices, fit, prepare, scores
from compare import replay, summarize


NAMES = ['checkpoint_index','frontier_count']


def fixture(count=32):
    rows = []
    for g in range(count):
        for f in ('unfiltered','votes32','votes108'):
            group = 'synthetic-g'+str(g).zfill(3)
            states = [{'checkpoint_index':cp,'features':{'checkpoint_index':cp,'frontier_count':g}} for cp in (1,2)]
            labels = {str(cp):{'recall':1. if cp==2 or g<count//2 else .5,
                              'valid':True,'returned_count':10,'layer0_distances':64*cp,
                              'activation_ms_saved':4. if cp==1 else 2.,
                              'reuse_ms_saved':3. if cp==1 else 1.5} for cp in (1,2)}
            cont = {'recall':1.,'valid':True,'returned_count':10,'layer0_distances':1000,
                    'activation_ms_saved':-1.,'reuse_ms_saved':-.5}
            rows.append({'query_id':group+'-'+f,'group':group,'stratum':f,'native_recall':1.,
                         'native_work':1000,'base_states':states,'local_states':copy.deepcopy(states),
                         'labels':{'base':labels,'local':copy.deepcopy(labels)},
                         'continue_costs':{'base':cont,'local':copy.deepcopy(cont)}})
    return rows


def groups(rows):
    return sorted({r['group'] for r in rows})


class ComparisonTests(unittest.TestCase):
    def test_earliest_bit_is_first_stop(self):
        self.assertEqual(first_indices(np.asarray([[0,1,2,3,128,255]]),8).tolist(),[[8,0,1,0,7,0]])

    def test_later_safe_stop_cannot_hide_earlier_loss(self):
        rows=fixture();data=prepare(rows,'B',PROFILE,NAMES,groups(rows))
        earlier=scores(data,np.full(len(rows),3,dtype=np.uint16),80.)[0]
        later=scores(data,np.full(len(rows),2,dtype=np.uint16),80.)[0]
        self.assertLess(earlier,later)

    def test_invalid_first_stop_is_infeasible(self):
        rows=fixture();rows[0]['labels']['base']['1']['valid']=False
        data=prepare(rows,'B',PROFILE,NAMES,groups(rows))
        self.assertEqual(scores(data,np.ones(len(rows),dtype=np.uint16),20.)[0],-1e100)

    def test_unmeasured_scoring_state_rejected(self):
        rows=fixture();data=prepare(rows,'B',PROFILE,NAMES,groups(rows))
        with self.assertRaisesRegex(ValueError,'unmeasured state'):
            scores(data,np.full(len(rows),4,dtype=np.uint16),20.)

    def test_vector_scores_match_scalar_whole_queries(self):
        rows=fixture();data=prepare(rows,'B',PROFILE,NAMES,groups(rows))
        masks=np.random.default_rng(5).integers(0,4,size=(25,len(rows)),dtype=np.uint16)
        actual=scores(data,masks,80.)
        for k,mask in enumerate(masks):
            a=[];w=[];loss={f:[] for f in ('all','unfiltered','votes32','votes108')}
            for q,m in zip(data.rows,mask):
                cp=None if m==0 else (1 if int(m)&1 else 2)
                label=q['continue_costs']['base'] if cp is None else q['labels']['base'][str(cp)]
                deficit=0. if cp is None else max(0.,q['native_recall']-label['recall'])
                a.append(label['activation_ms_saved']);w.append(label['reuse_ms_saved'])
                loss['all'].append(deficit);loss[q['stratum']].append(deficit)
            wanted=min(np.mean(a),np.mean(w))-80.*max(np.mean(v) for v in loss.values())
            self.assertAlmostEqual(float(actual[k]),float(wanted))

    def test_unknown_actual_stop_rejected(self):
        rows=fixture();del rows[0]['labels']['base']['2']
        with self.assertRaisesRegex(ValueError,'Unknown actual stop'):
            prepare(rows,'B',PROFILE,NAMES,groups(rows))

    def test_missing_observation_not_imputed(self):
        rows=fixture();rows[0]['base_states'][0]['features']['frontier_count']=None
        with self.assertRaisesRegex(ValueError,'incomplete'):
            prepare(rows,'B',PROFILE,NAMES,groups(rows))

    def test_no_int64_rounding(self):
        rows=fixture();rows[0]['base_states'][0]['features']['frontier_count']=2**53+1
        with self.assertRaisesRegex(ValueError,'exactly represented'):
            prepare(rows,'B',PROFILE,NAMES,groups(rows))

    def test_training_only_thresholds_and_outcomes(self):
        rows=fixture(48);train=groups(rows)[:32]
        first,proof=fit(rows,'B',80.,PROFILE,NAMES,train)
        changed=copy.deepcopy(rows)
        for q in changed:
            if q['group'] not in train:
                q['labels']['base']['1']['recall']=0.
                q['labels']['base']['2']['activation_ms_saved']=1e9
                for state in q['base_states']:state['features']['frontier_count']=-10000
        second,proof2=fit(changed,'B',80.,PROFILE,NAMES,train)
        self.assertEqual((first,proof),(second,proof2))

    def test_group_support_not_state_count(self):
        rows=fixture(4);_,proof=fit(rows,'B',80.,PROFILE,NAMES,groups(rows))
        self.assertEqual(proof['candidate_scores_computed'],0)
        self.assertEqual(proof['decision_nodes_without_guard'],0)

    def test_small_safe_tree_and_shared_interpreter_agree(self):
        rows=fixture();raw,proof=fit(rows,'B',80.,PROFILE,NAMES,groups(rows))
        self.assertLessEqual(proof['decision_nodes_without_guard'],7)
        result=replay(raw,rows,'B',PROFILE)
        self.assertTrue(all(r['recall_delta']==0 and r['checkpoint'] is not None for r in result))
        for q,r in zip(rows,result):
            cp=predict(raw,q['base_states'],PROFILE)
            self.assertEqual(cp,r['checkpoint'])
            self.assertEqual(cp,proof['training_first_stops'][q['query_id']])
        self.assertGreater(np.mean([r['reuse_proxy_ms_saved'] for r in result]),1.5)

    def test_guard_only_allows_declared_checkpoints(self):
        rows=fixture();raw,_=fit(rows,'B',80.,PROFILE,NAMES,groups(rows))
        extra={'checkpoint_index':3,'features':{'checkpoint_index':3,'frontier_count':0}}
        self.assertIsNone(predict(raw,[extra],PROFILE))

    def test_maximum_tree_fits_existing_policy_language(self):
        from fannagent.api import validate_policy
        names=['frontier_count','queue_pops','completed_expansions','retained_result_count',
               'layer0_distance_evaluations','upper_distance_evaluations','unique_discoveries']
        atoms=[(n,'int',10) for n in names]
        tree=(0,(1,(3,True,False),(4,False,True)),(2,(5,True,False),(6,False,True)))
        raw={'name':'test-max-tree','feature_groups':['basic','work','queue','distances'],
             'root':guard(compile_tree(tree,atoms),[1,2,4,8,16,32,64,128])}
        validate_policy(raw,PROFILE)

    def test_final_recall_gate_checks_each_filter(self):
        rows=fixture();raw={'name':'test-continue','root':'continue','feature_groups':['basic']}
        records=replay(raw,rows,'B',PROFILE)
        for r in records:
            if r['stratum']=='votes108':
                r['recall_delta']=-.006;r['policy_recall']=.994
        report=summarize(records)
        self.assertTrue(report['overall']['final_recall_replay_pass'])
        self.assertFalse(report['per_filter']['votes108']['final_recall_replay_pass'])
        self.assertEqual(report['final_latency_gate'],'unmeasured')
        self.assertFalse(report['final_combined_acceptance'])

    def test_fixed_design_and_original_ab(self):
        self.assertEqual(DESIGN['final_recall_tolerance'],.005)
        self.assertEqual(DESIGN['development_recall_margin'],.0025)
        self.assertEqual(DESIGN['bootstrap_samples'],10000)
        self.assertEqual(DESIGN['minimum_native_recall'],.95)
        self.assertEqual(AB,{'status':'inconclusive','complete_pairs':0,'selection_effect_established':False})

    def test_model_and_network_guards(self):
        with self.assertRaisesRegex(RuntimeError,'Provider/model imports are forbidden'):__import__('openai')
        with self.assertRaisesRegex(RuntimeError,'Offline comparison forbids'):
            sys.audit('socket.connect',None,None)
        with self.assertRaisesRegex(RuntimeError,'Offline comparison forbids'):
            sys.audit('subprocess.Popen',None,None,None,None)


if __name__=='__main__':
    unittest.main(verbosity=2)
