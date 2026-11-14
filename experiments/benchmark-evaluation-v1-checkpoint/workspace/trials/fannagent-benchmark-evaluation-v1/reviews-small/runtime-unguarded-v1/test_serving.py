"""Serving and scoring contracts for the removal of exact completion."""
import ast,inspect,unittest
from pathlib import Path
from unittest.mock import patch
from serving import request
from support import valid
from startup import start,install
class Conn:
 def __init__(self,rows):self.rows=rows;self.calls=[]
 def execute(self,*a,**kw):self.calls.append((a,kw));return self
 def fetchall(self):return self.rows
Q={'k':10,'vector':[.1]*8}
class Contracts(unittest.TestCase):
 def test_short_answer_one_call_no_replacement(self):
  c=Conn([(i,.1) for i in range(7)]);attempts=[];r=request(c,Q,attempts.append)
  self.assertEqual(len(c.calls),1);self.assertEqual(attempts,['ann']);self.assertEqual(r['returned_count'],7);self.assertEqual(r['output'],c.rows and [[i,.1] for i in range(7)])
  self.assertEqual(valid(r['output'],Q,set(range(10)),[(i,.1) for i in range(10)]),.7)
 def test_zero_result_scores_zero(self):
  c=Conn([]);r=request(c,Q,lambda op:None);self.assertEqual(r['output'],[]);self.assertEqual(valid([],Q,set(range(10)),[(i,.1) for i in range(10)]),0)
 def test_denominator_not_returned_count(self):
  self.assertEqual(valid([(1,.1)],Q,{1,2,3},[(1,.1),(2,.1),(3,.1)]),1/3)
  self.assertEqual(valid([],Q,set(),[]),1)
 def test_wrong_neighbors_not_credited(self):
  self.assertEqual(valid([(1,.2)],Q,{1,2},[(2,.1)]),0)
 def test_duplicate_ineligible_nonfinite_are_errors(self):
  for rows in ([(1,.1),(1,.1)],[(99,.1)],[(1,float('nan'))]):
   with self.assertRaises(RuntimeError):valid(rows,Q,{1,2},[(1,.1),(2,.1)])
 def test_sql_exception_not_hidden(self):
  class Broken(Conn):
   def execute(self,*a,**kw):raise ValueError('SQL failure')
  with self.assertRaises(ValueError):request(Broken([]),Q,lambda op:None)
 def test_cap_checked_before_dispatch(self):
  c=Conn([])
  def deny(op):raise RuntimeError('cap')
  with self.assertRaises(RuntimeError):request(c,Q,deny)
  self.assertEqual(c.calls,[])
 def test_exact_timer_components(self):
  ticks=iter((10,20,80));r=request(Conn([]),Q,lambda op:None,clock=lambda:next(ticks));self.assertEqual(r['request_ns'],70);self.assertEqual(r['construction_ns'],10);self.assertEqual(r['sql_fetch_decode_ns'],60)
 def test_serving_has_no_exact_or_outcome_capability(self):
  self.assertEqual(set(inspect.signature(request).parameters),{'ann_conn','query','reserve','fixture','clock'})
  s=inspect.getsource(request);self.assertNotIn('truth',s);self.assertNotIn('exact',s);self.assertNotIn('fallback',s);self.assertEqual(s.count('.execute('),1)
 def test_private_startup_only_capacity_changes(self):
  root=Path(__file__).resolve().parents[4];p=root/'trials/reviews-persistent-batch-native-v1/reviews-persistent-batch-native-v1/inputs/trials/torch-reviews-selective-agent-v1/runs/20261022T192817Z-66ed81d6/packages/pilot/torch-selective-agent-v1-pilot-20261022T192817Z-66ed81d6/database.py'
  tree=ast.parse(p.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='start');mod=ast.Module(body=[node],type_ignores=[])
  import subprocess
  g={'subprocess':subprocess};exec(compile(mod,str(p),'exec'),g)
  with patch('subprocess.run') as previous:g['start'](Path('/run'))
  with patch('subprocess.run') as updated:start(Path('/run'))
  old=list(previous.call_args.args[0]);old[0]='/opt/postgresql/bin/pg_ctl';old[old.index('-o')+1]=old[old.index('-o')+1].replace('max_connections=16','max_connections=32');self.assertEqual(old,updated.call_args.args[0]);self.assertEqual(previous.call_args.kwargs,updated.call_args.kwargs)
if __name__=='__main__':unittest.main(verbosity=2)
