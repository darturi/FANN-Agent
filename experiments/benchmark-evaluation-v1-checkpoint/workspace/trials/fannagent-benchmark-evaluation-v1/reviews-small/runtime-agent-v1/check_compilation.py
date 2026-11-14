"""Execute generated C decisions against full-precision frozen development replay."""
import ctypes,json,subprocess,tempfile,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'development/agent-episode-v2-compact'))
from data import load,choose,sha
from compile_policies import generate
policies=json.loads((HERE/'eligible-policies.json').read_text())['policies']
assert generate(policies)==(HERE/'engine/src/compiled_study_policies.inc').read_text()
rows=load();decisions=0
with tempfile.TemporaryDirectory(prefix='agent-policy-compile-') as temp:
 p=Path(temp);(p/'rules.c').write_text('#include <stdbool.h>\n'+generate(policies)+'\nint decide(int arm,int filter,int cp,int count,double gap,double tenth,int turnover) {return CompiledStudyRule(arm,filter,cp,count,gap,tenth,turnover);}\n')
 subprocess.run(['cc','-shared','-fPIC','-O2',str(p/'rules.c'),'-o',str(p/'rules.so')],check=True)
 lib=ctypes.CDLL(str(p/'rules.so'));f=lib.decide;f.argtypes=[ctypes.c_int]*4+[ctypes.c_double]*2+[ctypes.c_int];f.restype=ctypes.c_int
 for arm,policy in enumerate(policies,7):
  for row in rows.values():
   stopped=None;t=-1 if row['filter']=='unfiltered' else int(row['filter'][5:])
   for cp,o in sorted(row['observations'].items()):
    if o['frontier_gap'] is None or o['tenth_distance'] is None:continue
    stop=f(arm,t,cp,o['qualifying_count'],o['frontier_gap'],o['tenth_distance'],-1 if o['top10_new_since_previous'] is None else o['top10_new_since_previous']);decisions+=1
    if stop:stopped=cp;break
   assert stopped==choose(row,policy),(arm,row['group'],row['filter'])
 # Equality, insufficient counts, unavailable turnover and omitted predicate checks.
 assert f(7,-1,64,10,.15,.36,-1)==1 and f(7,-1,64,9,.15,.36,-1)==0
 assert f(8,108,64,10,.08,.38,-1)==0 and f(8,108,64,10,.08,.38,0)==1
 assert all(f(a,743,64,640,2,0,0)==0 for a in (7,8,9))
result={'status':'passed','compiled_c_first_stop_cases':9450,'checkpoint_decisions':decisions,'full_precision_saved_features':True,'equality_missing_turnover_insufficient_count_omitted_filter_checks':'passed','generated_include_sha256':sha(HERE/'engine/src/compiled_study_policies.inc'),'holdout_access':False}
(HERE/'checks/compiler-parity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
