"""Protocol, budgets, routing, first stops and irreversible-gate regressions."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from contract import bootstrap,CONFIG,AB,accounting,read,save,digest,SOURCE,ROOT
bootstrap()
from policy import compose,validate,route,matched,first_stop,names
from evidence import verified_rows,seeds,historical_state
from episode_budget import EpisodeBudget
from fannagent.config import ModelConfig
from fannagent.store import Store
from fannagent.errors import AgentError,BudgetExceeded
from screen import screen,replay
from control import dispatch,reserve_stage

def model_config():
    d=read(ROOT/'trials/torch-reviews-aggressive-proposals-v2/model.json');d.update(ceiling_usd='10',allowance_usd='0');return ModelConfig.model_validate(d)

class StudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_state=historical_state();cls.cfg,cls.rows,cls.items,cls.pins=verified_rows()

    @classmethod
    def tearDownClass(cls):
        if historical_state()!=cls.old_state:raise AssertionError('Historical ledger changed during validation')

    def test_independent_inventory_and_exposure(self):
        self.assertEqual(len(self.rows),600);self.assertEqual(len({r['group'] for r in self.rows}),200)
        self.assertEqual({r['role'] for r in self.rows},{'original_learning','additional_learning','calibration'})
        split=read(SOURCE/'inputs/ablation-split.json')['selected_catalog_groups']
        allg=[g for gs in split.values() for g in gs];self.assertEqual(len(allg),len(set(allg)))
        self.assertEqual(len(split['evaluation']),60);self.assertEqual(len(split['reserved']),37)

    def test_provenance_seeds_are_valid(self):
        ss=seeds(self.cfg);self.assertEqual(len(ss),2)
        for s in ss.values():validate(s['policy'],self.cfg);self.assertIn('origin',s)

    def test_name_does_not_create_new_export(self):
        p=compose('a','continue');q=copy.deepcopy(p);q['name']='b';q['tree']['name']='b'
        self.assertEqual(validate(p,self.cfg)[1],validate(q,self.cfg)[1])
        q['eligible']=['unfiltered'];self.assertNotEqual(validate(p,self.cfg)[1],validate(q,self.cfg)[1])

    def test_only_actual_predicate_controls_route(self):
        self.assertEqual(route({'id':'anything-votes108','filter':None}),'unfiltered')
        self.assertEqual(route({'id':'anything','filter':{'field':'m_000000','op':'gte','value':108}}),'votes108')
        for f in [{'field':'other','op':'gte','value':108},{'field':'m_000000','op':'gte','value':109},{'field':'m_000000','op':'gte','value':True}]:
            self.assertEqual(route({'filter':f}),'other')

    def test_reject_identity_unqualified_and_wrong_groups(self):
        p=compose('bad',{'if':{'op':'eq','args':[{'feature':'query_id'},{'int':1}]},'then':'stop','else':'continue'})
        with self.assertRaises(Exception):validate(p,self.cfg)
        p=compose('bad','continue');p['tree']['feature_groups'].append('local_filter')
        with self.assertRaises(ValueError):validate(p,self.cfg)
        p=compose('bad','continue');p['eligible']=[]
        with self.assertRaises(ValueError):validate(p,self.cfg)
        p=compose('bad','continue');p['query_ids']=['x']
        with self.assertRaises(ValueError):validate(p,self.cfg)

    def test_guard_prevents_unsampled_and_unavailable_stops(self):
        p=compose('g','stop');q=copy.deepcopy(self.rows[0]);q['base_states']=[s for s in q['base_states'] if s['checkpoint_index']==3]
        self.assertIsNone(first_stop(p,q,self.cfg))
        p=compose('g',{'if':{'op':'gte','args':[{'feature':'frontier_count'},{'int':0}]},'then':'stop','else':'continue'})
        q=copy.deepcopy(self.rows[0]);q['base_states'][0]['features']['frontier_count']=None
        self.assertNotEqual(first_stop(p,q,self.cfg),1)

    def test_unknown_stopped_recall_not_imputed(self):
        p=compose('s','stop');q=copy.deepcopy(self.rows[0]);q['labels']['base'].pop('1')
        r=screen(p,[q],self.cfg);self.assertIsNone(r['assessment']);self.assertEqual(len(r['unknown']),1)

    def test_bypass_keeps_all_filters_and_no_fake_cost_claim(self):
        p=compose('s','continue',eligible=['unfiltered']);rr=replay(p,self.rows,self.cfg)
        self.assertEqual(len(rr),600);self.assertEqual(sum(r['native_bypass'] for r in rr),400)
        for r in rr:
            if r['native_bypass']:self.assertEqual(r['recall_delta'],0.);self.assertIn('unknown',r['proxy_assumptions'][0])
        self.assertIn('unmeasured',screen(p,self.rows,self.cfg)['timing_status'])

    def test_depth_and_guard_required(self):
        p=compose('bad','continue');p['tree']['root']='stop'
        with self.assertRaises(ValueError):validate(p,self.cfg)
        p=compose('x','continue');condition={'op':'gte','args':[{'feature':'checkpoint_index'},{'int':1}]};root='stop'
        for i in range(4):root={'if':condition,'then':root,'else':'continue'}
        with self.assertRaises(ValueError):validate(compose('deep',root),self.cfg)

    def test_matched_control_keeps_cost_structure(self):
        p=seeds(self.cfg)['cons_S32_64_128_t002']['policy'];m=matched(p)
        self.assertEqual(m['eligible'],p['eligible']);self.assertEqual(m['profile'],p['profile'])
        validate(m,self.cfg);self.assertTrue(all(r['checkpoint'] is None for r in replay(m,self.rows,self.cfg)))
        p['name']='x'*160;validate(matched(p),self.cfg)

    def test_precise_counts_and_full_cap(self):
        vals=[accounting('pilot',3),accounting('revision',1),accounting('confirmation',1)]
        self.assertEqual([v['backend_searches_per_block_maximum'] for v in vals],[56721,30321,12801])
        self.assertEqual(sum(3*v['backend_searches_per_block_maximum'] for v in vals),299529)
        self.assertEqual(sum(3*v['retained_pairs_per_block'] for v in vals),100980)
        self.assertLess(accounting('pilot',1)['backend_searches_per_block_maximum'],56721)

    def test_phase_limits_atomic_and_uncertain(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp),create=True);b=EpisodeBudget(s,model_config(),'A')
            charge=b.reserve(b.maximum_call())
            with self.assertRaises(AgentError):b.reserve(b.maximum_call())
            b.uncertain(charge,'test');self.assertEqual(b.status()['uncertain_reserved_usd'],'0.606208')
            for i in range(7):
                c=b.reserve(b.maximum_call());b.settle(c,Decimal('0.001'),{})
            with self.assertRaises(BudgetExceeded):b.reserve(b.maximum_call())
            b=EpisodeBudget(s,model_config(),'B')
            for i in range(4):
                c=b.reserve(b.maximum_call());b.settle(c,Decimal('0.001'),{})
            with self.assertRaises(BudgetExceeded):b.reserve(b.maximum_call())
            self.assertEqual(b.status()['provider_attempts_used'],12)

    def test_phase_money_not_borrowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp),create=True);b=EpisodeBudget(s,model_config(),'A')
            for i in range(6):
                c=b.reserve(Decimal('1'));b.settle(c,Decimal('1'),{})
            with self.assertRaises(BudgetExceeded):b.reserve(Decimal('.01'))
            b=EpisodeBudget(s,model_config(),'B');c=b.reserve(Decimal('4'));b.settle(c,Decimal('4'),{})
            with self.assertRaises(BudgetExceeded):b.reserve(Decimal('.01'))

    def test_bound_violation_disables_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp),create=True);b=EpisodeBudget(s,model_config(),'A');c=b.reserve(Decimal('.1'))
            with self.assertRaises(AgentError):b.settle(c,Decimal('.2'),{})
            with self.assertRaises(AgentError):b.reserve(Decimal('.1'))

    def test_irreversible_dispatch_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp);r={'dispatch':{},'jobs':{},'account':'torch_pr_test','bundle':'/b','prepared':'/p','workspace':'/w','campaign':str(c),'sources':'/s','apptainer':'/a'}
            def scheduler(*args,**kwargs):
                self.assertEqual(read(c/'submission.json')['dispatch']['block-0']['status'],'dispatching')
                return subprocess.CompletedProcess(args[0],0,'nonsense','')
            with patch('control.subprocess.run',side_effect=scheduler) as call:
                with self.assertRaises(ValueError):dispatch(c,c,r,0)
                with self.assertRaises(ValueError):dispatch(c,c,r,0)
                self.assertEqual(call.call_count,1)
            self.assertEqual(r['dispatch']['block-0']['status'],'unknown')

    def test_final_gate_recall_per_filter_and_both_cost_regimes(self):
        from fd_policy_tools import assess
        rr=[{'group':str(i),'stratum':f,'native_recall':1.,'recall_delta':-.006 if f=='votes108' else 0.,'valid':True,
            'activation_proxy_ms_saved':1.,'reuse_proxy_ms_saved':1.} for i in range(40) for f in CONFIG['filters']]
        r=assess(rr,.005);self.assertFalse(r['recall_pass'])
        self.assertGreaterEqual(r['reports']['overall']['recall_delta_ci95'][0],-.005)

    def test_confirmation_cannot_be_built_before_agent_completion(self):
        from package import selection
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp),create=True)
            with self.assertRaises(ValueError):selection(Path(tmp),s,'confirmation')
            s.set('phase_done_A',True)
            with self.assertRaises(ValueError):selection(Path(tmp),s,'confirmation')

    def test_failure_never_promotes_fallback(self):
        from package import selection
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);s=Store(run,create=True);p=compose('x','continue');h=validate(p,self.cfg)[1];chosen={'policy':p,'semantic_hash':h}
            s.set_many({'phase_done_A':True,'phase_done_B':True,'exports_A':{h:chosen}})
            save(run/'agent-final.json',{'status':'selected_initial','selection':chosen})
            with patch('package.verified_measurement',return_value={'candidate_qualification':{h:{'development_qualifies':False}}}):
                with self.assertRaises(ValueError):selection(run,s,'confirmation')

    def test_cross_package_stage_reservation_and_global_confirmation_consumption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'package';p.mkdir();save(p/'manifest.json',{})
            cfg={'episode_id':'episode-one','run_contract_sha256':'contract','module_sha256':'module','stage':'pilot'}
            reserve_stage(root,cfg,p,root/'campaign-one')
            with self.assertRaises(ValueError):reserve_stage(root,cfg,p,root/'campaign-two')
            cfg.update(stage='confirmation',confirmation_entitlement_sha256='same-unused-split',primary_hash='first-choice')
            reserve_stage(root,cfg,p,root/'confirmation-one')
            cfg.update(episode_id='episode-two',primary_hash='replacement')
            with self.assertRaises(ValueError):reserve_stage(root,cfg,p,root/'confirmation-two')
            self.assertEqual(read(root/'.selective-confirmation-same-unused-split.json')['candidate'],'first-choice')

    def test_live_status_is_readonly(self):
        import contextlib,io
        from study import status
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);s=Store(root,create=True);save(root/'contract.json',{'model':model_config().model_dump(mode='json')})
            s.set('episode_status','running_A');b=EpisodeBudget(s,model_config(),'A');c=b.reserve(b.maximum_call())
            with s.lease('run'),contextlib.redirect_stdout(io.StringIO()):r=status(root)
            self.assertEqual(r['budget']['provider_attempts_used'],1)
            self.assertEqual(r['budget']['uncertain_reserved_usd'],'0.606208')
            self.assertEqual(b.calls()[0]['status'],'reserved')

    def test_profile_cost_waste_is_visible(self):
        r=screen(compose('overpaying','continue','static23'),self.rows,self.cfg)
        self.assertEqual(r['smallest_supported_profile'],'light19');self.assertTrue(r['paying_for_larger_profile'])

    def test_fitter_profiles_and_masks_match_shared_interpreter(self):
        from fitting import fit_one
        groups=sorted({r['group'] for r in self.rows})[:40]
        for profile in ('light19','static23','progress34'):
            raw,proof=fit_one(self.rows,self.cfg,groups,profile,['unfiltered','votes32'],1280)
            self.assertEqual(proof['shared_interpreter_checks'],120)
            for q in self.rows:
                if q['group'] in groups and q['stratum']=='votes108':self.assertIsNone(first_stop(raw,q,self.cfg))

if __name__=='__main__':unittest.main()
