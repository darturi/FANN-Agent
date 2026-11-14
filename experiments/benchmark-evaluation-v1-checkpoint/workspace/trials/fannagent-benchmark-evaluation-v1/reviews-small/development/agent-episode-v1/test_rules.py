import unittest
from data import validate_policy,choose,evaluate,FILTERS
class RuleTests(unittest.TestCase):
 def policy(self):return {'name':'p','rules':{'votes108':[{'cp':32,'conditions':[['frontier_gap','>=',.05]]}]},'rationale':'test'}
 def test_missing_feature_does_not_stop(self):
  row={'filter':'votes108','observations':{32:{'qualifying_count':10,'frontier_gap':None}},'proofs':{}}
  self.assertIsNone(choose(row,self.policy()))
 def test_insufficient_count_does_not_stop(self):
  row={'filter':'votes108','observations':{32:{'qualifying_count':9,'frontier_gap':.1}},'proofs':{}}
  self.assertIsNone(choose(row,self.policy()))
 def test_identifier_and_nonfinite_features_rejected(self):
  for feature,value in [('query_id',3),('frontier_gap',float('nan'))]:
   p=self.policy();p['rules']['votes108'][0]['conditions']=[[feature,'>=',value]]
   with self.assertRaises(AssertionError):validate_policy(p)
 def test_individual_recall_loss_cannot_be_hidden(self):
  rows={}
  for f in FILTERS:
   rows[f]={'group':0,'fold':0,'filter':f,'baseline_recall':1.,'native_ns':100,'noop_ns':105,'observations':{32:{'qualifying_count':10,'frontier_gap':.1}},'proofs':{'32':{'recall':.9}},'stop_ns':{32:50}}
  result=evaluate(rows,self.policy());self.assertEqual(result['loss_count'],1);self.assertFalse(result['quality_eligible_on_development'])
if __name__=='__main__':unittest.main(verbosity=2)
