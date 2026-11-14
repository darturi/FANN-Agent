"""Crossover coverage, paired mirroring, original serving and module boundaries."""
import collections,unittest,hashlib
from pathlib import Path
from design import FAMILIES,BLOCKS,BASE,role,cpu_for,order_for,TIMING_ATTEMPTS,WORK_ATTEMPTS,TOTAL_ATTEMPTS
class Design(unittest.TestCase):
 def test_every_process_every_role_twice(self):
  for reader in range(20):self.assertEqual(collections.Counter(role(reader,r) for _,r in BLOCKS),{n:2 for n in FAMILIES})
 def test_every_role_on_every_cpu_each_block(self):
  for ti in range(7):
   for cycle,rotation in BLOCKS:
    counts=collections.Counter((role(r,rotation),cpu_for(r,ti,[3,7,11,19])) for r in range(20));self.assertEqual(counts,{(n,cpu):1 for n in FAMILIES for cpu in (3,7,11,19)})
 def test_exact_matched_cycle_mirroring(self):
  for ti in range(7):
   for rotation in range(5):
    for j in range(450):self.assertEqual(order_for(j,0,rotation,ti),list(reversed(order_for(j,1,rotation,ti))))
 def test_williams_rows_cover_positions_and_predecessors(self):
  positions=collections.Counter();edges=collections.Counter()
  for j in range(20):
   row=order_for(j,0,0,0);self.assertEqual(set(row),set(range(20)))
   for i,r in enumerate(row):positions[r,i]+=1
   for a,b in zip(row,row[1:]):edges[a,b]+=1
  self.assertEqual(set(positions.values()),{1});self.assertEqual(len(edges),20*19);self.assertEqual(set(edges.values()),{1})
 def test_fixed_attempt_arithmetic(self):
  self.assertEqual(TIMING_ATTEMPTS,3150+3150+5*3150+10*20*10*7+10*20*450*7)
  self.assertEqual(WORK_ATTEMPTS,3150+5*3150);self.assertEqual(TOTAL_ATTEMPTS,TIMING_ATTEMPTS+WORK_ATTEMPTS);self.assertEqual(TOTAL_ATTEMPTS,684950)
 def test_original_timing_code_and_binary_unchanged(self):
  h=Path(__file__).resolve().parent
  for n in ('common.py','serving.py','compiled-policies.json','eligible-policies.json'):
   self.assertEqual((h/n).read_bytes(),(h.parent/'runtime-unguarded-v1'/n).read_bytes())
  self.assertEqual((h/'timing-module.so').read_bytes(),(h.parent/'runtime-unguarded-v1/vector.so').read_bytes())
 def test_counter_module_changes_observer_source_only(self):
  h=Path(__file__).resolve().parent;old=h.parent/'runtime-agent-v1/engine'
  for p in (old/'src').glob('*.c'):
   if p.name!='fannbench.c':self.assertEqual(p.read_bytes(),(h/'engine/src'/p.name).read_bytes())
 def test_native_and_counter_module_exports_separate(self):
  h=Path(__file__).resolve().parent
  self.assertNotEqual((h/'timing-module.so').read_bytes(),(h/'work-module.so').read_bytes())
  self.assertNotIn('diagnostic_reset',(h/'functions.sql').read_text());self.assertIn('diagnostic_reset',(h/'work-functions.sql').read_text())
if __name__=='__main__':unittest.main(verbosity=2)
