"""Focused checks for new predicate routing, partial outputs and resource accounting."""
import unittest
from common import statement,require
from qualify import count_search,valid
class RuntimeChecks(unittest.TestCase):
 def test_all_seven_predicates_bind_safely(self):
  for t in (-1,743,527,310,192,108,32):
   q={'k':10,'vector':[.1]*768}
   if t>=0:q['filter']={'field':'totalvotes','op':'gte','value':t}
   sql,params=statement(q)
   self.assertEqual(sql.count('%s'),len(params));self.assertEqual('total_votes >= %s' in sql,t>=0)
   self.assertNotIn('id <= 16000',sql)
 def test_unexpected_predicate_rejected(self):
  with self.assertRaises(RuntimeError):statement({'k':10,'vector':[.1]*768,'filter':{'value':999}})
 def test_wrong_field_or_operator_rejected(self):
  for field,op in (('other','gte'),('totalvotes','lt')):
   with self.assertRaises(RuntimeError):statement({'k':10,'vector':[.1]*768,'filter':{'field':field,'op':op,'value':108}})
 def test_incomplete_native_is_a_quality_result(self):
  out=[(i,.1) for i in range(6)];truth=[(i,.1) for i in range(10)]
  self.assertEqual(valid(out,{},set(range(10)),truth),.6)
 def test_ineligible_and_duplicate_outputs_rejected(self):
  for out in ([(999,.1)],[(0,.1),(0,.1)]):
   with self.assertRaises(RuntimeError):valid(out,{},set(range(10)),[(0,.1)])
 def test_nonfinite_cosine_output_rejected(self):
  with self.assertRaises(RuntimeError):valid([(0,float('nan'))],{},{0},[(0,.1)])
 def test_budget_stops_before_dispatch(self):
  counter={'total':60000};calls=[]
  with self.assertRaises(RuntimeError):count_search(counter,'ann',lambda:calls.append(1))
  self.assertEqual(calls,[])
 def test_exact_ties_requested(self):
  sql,_=statement({'k':10,'vector':[.1]*768},exact=True)
  self.assertTrue(sql.endswith('FETCH FIRST 10 ROWS WITH TIES'))
class SourceInvariantChecks(unittest.TestCase):
 def test_search_algorithm_sources_unchanged(self):
  from pathlib import Path
  here=Path(__file__).resolve().parent
  for p in (here/'engine/src').glob('*.c'):
   if p.name!='hnsw.c':self.assertEqual(p.read_bytes(),(here.parent/'runtime/engine/src'/p.name).read_bytes())
if __name__=='__main__':unittest.main(verbosity=2)
