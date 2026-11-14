"""Prespecified local diagnostic summaries, paired by group/backend/CPU; no promotion."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,json
from pathlib import Path
import numpy as np
from design import FAMILIES,cpu_for
from common import THRESHOLDS,write
from verify_return import lines

def analyse(results):
 verification=json.loads((results/'local-verification.json').read_text());require=__import__('common').require;require(verification['status']=='counterbalanced_attribution_return_verified','verify return first')
 rows=results/'timing/timing.jsonl';cpus=json.loads((results/'timing/allowed-cpus.json').read_text());groups=sorted({r['id'].rsplit('-',1)[0] for r in lines(results/'timing/quality.jsonl')});gi={g:i for i,g in enumerate(groups)};fi={n:i for i,n in enumerate(FAMILIES)};data=np.zeros((450,7,20,2,5))
 for r in lines(rows):
  key=gi[r['id'].rsplit('-',1)[0]],THRESHOLDS.index(r['filter']),r['reader'],r['cycle'],fi[r['family']]
  require(data[key]==0,'duplicate group/backend/cycle/role');data[key]=r['request_ns']
 require(np.all(data>0),'missing crossover observations')
 paired=data.mean(axis=(2,3));rng=np.random.default_rng(20261113);ratios=[];noops=[]
 for _ in range(40):
  weights=rng.multinomial(450,np.full(450,1/450),size=500)
  means=(weights@paired[:,1:,:].mean(axis=1))/450
  ratios.append(means/means[:,0,None]);noops.append(means/means[:,1,None])
 ratios=np.concatenate(ratios);noops=np.concatenate(noops);means=data[:,1:,:,:,:].mean(axis=(0,1,2,3));per={}
 for f,name in enumerate(FAMILIES):
  cpu_summaries={}
  for cpu in cpus:
   per_filter=[]
   for ti in range(1,7):
    readers=[r for r in range(20) if cpu_for(r,ti,cpus)==cpu];v=data[:,ti,readers,:,:].mean(axis=(0,1,2));per_filter.append(v)
   val=np.stack(per_filter).mean(axis=0);cpu_summaries[str(cpu)]={'mean_ms':val[f]/1e6,'ratio_to_native640':val[f]/val[0],'ratio_to_noop640':val[f]/val[1]}
  backend={str(t):{str(r):{'ratio_to_native640':data[:,ti,r,:,f].mean()/data[:,ti,r,:,0].mean(),'ratio_to_noop640':data[:,ti,r,:,f].mean()/data[:,ti,r,:,1].mean()} for r in range(20)} for ti,t in enumerate(THRESHOLDS)}
  per[name]={'mean_ms':means[f]/1e6,'ratio_to_native640':means[f]/means[0],'ratio_to_noop640':means[f]/means[1],'native_ratio_95pct_conditional_group_interval':np.quantile(ratios[:,f],[.025,.975]).tolist(),'noop_ratio_95pct_conditional_group_interval':np.quantile(noops[:,f],[.025,.975]).tolist(),'per_cpu':cpu_summaries,'per_backend_within_filter':backend,'per_cycle_native_ratio':{str(c):data[:,1:,:,c,f].mean()/data[:,1:,:,c,0].mean() for c in (0,1)}}
 work=verification['work'];reductions={}
 for n in FAMILIES:
  reductions[n]={}
  for counter in ('vector_calls','layer0_neighbor_scores','layer0_queue_pops','feature_passes','membership_probes'):
   mean=sum(work[str(t)]['means'][n][counter] for t in THRESHOLDS if t>=0)/6;base=sum(work[str(t)]['means']['native640'][counter] for t in THRESHOLDS if t>=0)/6
   reductions[n][counter]={'equal_scalar_mean_count':mean,'ratio_to_native640':mean/base if base else None}
 out={'status':'diagnostic_summaries_only_no_final_policy_promotion','timing':per,'work_counters':reductions,'counter_interpretation':'native/noop graph-counter mismatches are findings to investigate, not automatically hidden or disqualifying. Instrumented times are excluded.','uncertainty':'20000 group draws, seed20261113, preserve all filters/backend/cycle/role pairs; conditional on one allocation, not final allocation-level inference.','agent_disposition':'Runtime recall pass is not robust performance success. If useful work savings or net cost benefit remain weak, retain bounded negative and revise agent evidence/objective in a separately authorized version. No new provider call here.','validation_test_outcomes_opened':False}
 write(results/'diagnostic-analysis.json',out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);a=p.parse_args();print(json.dumps(analyse(a.results),indent=2))
