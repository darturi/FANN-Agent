"""Development-only assessment; conditional group bootstrap is not confirmatory inference."""
import collections,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from common import THRESHOLDS,sha,write,threshold
from experiment import ARMS,LABELS,ordered,order_for
from verify_return import lines
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;RESULTS=BASE/'returns/job-22928562/results';KIT=BASE/'kits/agent-policy-qualification-v1'
def main():
 verification=json.loads((RESULTS/'local-verification.json').read_text());receipt=json.loads((RESULTS/'receipt.json').read_text());binding=json.loads((KIT/'binding.json').read_text())
 freeze=json.loads((BASE/'freeze/agent-policy-qualification-v1.json').read_text());assert sha(BASE/'kits/agent-policy-qualification-v1.tar.gz')==freeze['archive_sha256'] and sha(KIT/'binding.json')==freeze['binding_sha256']
 prior=json.loads((BASE/'returns/job-22684501/results/receipt.json').read_text());assert receipt['graph']==prior['graph']
 assert receipt['limits']['memory_limit']==48*1024**3 and len(set(map(tuple,receipt['limits']['cores'])))==4 and receipt['searches']['total']==81456
 queries=list(lines(KIT/'queries.jsonl'));groups=sorted({q['id'].rsplit('-',1)[0] for q in queries});gi={g:i for i,g in enumerate(groups)};families=list(ARMS);fi={f:i for i,f in enumerate(families)}
 data=np.zeros((450,7,4,2,2),dtype=np.float64);component=collections.defaultdict(lambda:collections.Counter());phase=collections.Counter()
 quality=collections.defaultdict(lambda:collections.Counter())
 for r in lines(RESULTS/'quality.jsonl'):
  for name,v in r['results'].items():
   c=quality[r['filter'],name];c['queries']+=1;c['recall_sum']+=v['recall'];c['stops']+=v['checkpoint']>0;c['fallbacks']+=v['fallback_used'];c['losses']+=v['recall']<r['results']['native']['recall']-1e-12
 for filename,warmup in (('timing.jsonl',False),('warmup.jsonl',True)):
  stream=iter(lines(RESULTS/filename))
  for ep in (0,1):
   filters=list(THRESHOLDS);filters=filters[ep:]+filters[:ep]
   for t in filters:
    cases=ordered(queries,t,ep)
    expected=((q,label) for label in LABELS for q in cases[:10]) if warmup else ((q,label) for j,q in enumerate(cases) for label in order_for(j,ep,THRESHOLDS.index(t)))
    for q,label in expected:
     r=next(stream);assert (r['id'],r['filter'],r['epoch'],r['label'])==(q['id'],t,ep,label)
     phase[filename+'.ann']+=1;phase[filename+'.completion_exact']+=r['fallback_used']
     if warmup:continue
     name,ab=label.rsplit('-',1);g=gi[q['id'].rsplit('-',1)[0]];ti=THRESHOLDS.index(t);f=fi[name];a=0 if ab=='A' else 1
     assert data[g,ti,f,a,ep]==0;data[g,ti,f,a,ep]=r['request_ns']
     c=component[t,name]
     for k in ('request_ns','ann_ns','fallback_ns','guard_and_construction_ns'):c[k]+=r[k]
     c['requests']+=1;c['fallbacks']+=r['fallback_used']
  assert next(stream,None) is None
 assert np.all(data>0)
 # A shared group draw preserves every filter, family, label and epoch within a vector.
 rng=np.random.default_rng(20261110);draws=20000;control=[];ratios=[]
 flat=data.mean(axis=-1).reshape(450,-1)
 for start in range(0,draws,500):
  w=rng.multinomial(450,np.full(450,1/450),size=min(500,draws-start));means=(w@flat/450).reshape(-1,7,4,2)
  control.append(means[:,:,:,0]/means[:,:,:,1]);scalar=means[:,1:,:,:].mean(axis=(1,3));ratios.append(scalar/scalar[:,0,None])
 controls=np.concatenate(control);ratios=np.concatenate(ratios);point=data.mean(axis=(0,4));report={}
 for f,name in enumerate(families):
  per={}
  for ti,t in enumerate(THRESHOLDS):
   c=quality[t,name];m=component[t,name];ci=np.quantile(controls[:,ti,f],[.05,.95]).tolist();native=data[:,ti,0,:,:].mean()
   per[str(t)]={'queries':c['queries'],'mean_recall':c['recall_sum']/450,'losses':c['losses'],'stops':c['stops'],'qualification_fallbacks':c['fallbacks'],'mean_ms':point[ti,f].mean()/1e6,'mean_ratio_to_native':point[ti,f].mean()/native,'identical_code_ab_ratio':point[ti,f,0]/point[ti,f,1],'conditional_group_bootstrap_ab_90pct':ci,'ab_interval_within_098_102':ci[0]>=.98 and ci[1]<=1.02,'timed_fallbacks':m['fallbacks'],'mean_fallback_ms':m['fallback_ns']/m['requests']/1e6,'mean_ann_ms':m['ann_ns']/m['requests']/1e6,'mean_guard_construction_ms':m['guard_and_construction_ns']/m['requests']/1e6}
  q=verification['metrics'][name]
  report[name]={'equal_scalar_mean_ms':q['equal_scalar_mean_ms'],'scalar_ratio':q['scalar_mean_ratio_to_native'],'scalar_reduction_percent':100*(1-q['scalar_mean_ratio_to_native']),'conditional_group_bootstrap_scalar_ratio_95pct':np.quantile(ratios[:,f],[.025,.975]).tolist(),'per_condition':per}
 best=min(report[n]['equal_scalar_mean_ms'] for n in families if n!='native');ties=[n for n in families if n!='native' and report[n]['equal_scalar_mean_ms']<=best*1.01];assert ties==['broad_c_fixed']
 setup=json.loads((RESULTS/'setup.json').read_text());maps=json.loads((RESULTS/'membership-setup.json').read_text());elig=json.loads((RESULTS/'eligibility.json').read_text());assert len(maps)==7 and {m['threshold'] for m in maps}==set(THRESHOLDS)
 for m in maps:assert m['qualifying']==len(elig[str(m['threshold'])]) and m['bytes']>24 and m['build_ns']>0
 assert elig==json.loads((BASE/'returns/job-22684501/results/eligibility.json').read_text())
 for t in THRESHOLDS:
  plans=json.loads((RESULTS/f'plans-{t}.json').read_text());assert set(plans['ann'])==set(ARMS)
  def scans(plan):
   return ([plan] if 'Scan' in plan['Node Type'] else [])+[v for child in plan.get('Plans',[]) for v in scans(child)]
  for plan in plans['ann'].values():
   nodes=scans(plan);assert len(nodes)==1 and nodes[0]['Index Name']=='reviews_hnsw' and nodes[0]['Relation Name']=='reviews'
  nodes=scans(plans['completion_exact']);assert len(nodes)==1 and nodes[0]['Node Type']=='Seq Scan' and nodes[0]['Relation Name']=='reviews'
 assert len(setup)==21 and sum(r.get('warmup_requests',0) for r in setup)==1120
 for r in setup:assert r['open_attach_ns']>0 and r['close_ns']>0
 scheduler={'source':'user pasted sacct output from Torch','job_id':'22928562','state':'COMPLETED','exit_code':'0:0','elapsed':'00:49:08','step_elapsed':'00:49:07','step_maxrss_kib':6706152,'batch_state':'COMPLETED','batch_exit_code':'0:0','step_state':'COMPLETED','step_exit_code':'0:0','gate':'passed'};write(RESULTS/'scheduler-reported.json',scheduler)
 assessment={'status':'runtime_verified_all_candidates_quality_eligible_modest_development_benefit','scheduler_gate':'passed from user-reported sacct','groups':450,'quality_cases':3150,'compiled_policy_cases':9450,'timing_requests':50400,'warmup_requests':1120,'attempts':receipt['searches'],'phase_attempts':dict(phase),'exact_file_order_reconstructed':True,'graph_identity_matches_parent':True,'resource_and_membership_checks':'passed','metrics':report,'development_nominee':'broad_c_fixed','within_one_percent_candidates':ties,'final_policy_selected':False,'validation_test_outcomes_opened':False,'bootstrap':{'draws':draws,'seed':20261110,'unit':'450 vector groups resampled jointly across filters/families/labels/epochs','scope':'Conditional on ONE allocation. Not the protocol five-allocation hierarchical bootstrap, not confirmatory equivalence or practical-benefit inference.'},'setup_totals_ns':{k:sum(r.get(k,0) for r in setup) for k in ('open_attach_ns','warmup_ns','close_ns')},'membership_build_ns':sum(m['build_ns'] for m in maps),'receipt_sha256':sha(RESULTS/'receipt.json'),'sealed_binding_sha256':sha(KIT/'binding.json')}
 write(RESULTS/'development-assessment.json',assessment)
 print(json.dumps({'nominee':ties,'metrics':{n:{k:v for k,v in r.items() if k!='per_condition'} for n,r in report.items()},'phase_attempts':dict(phase),'machine':receipt['machine'],'bad_ab_intervals':{n:[t for t,r in m['per_condition'].items() if not r['ab_interval_within_098_102']] for n,m in report.items()}},indent=2))
if __name__=='__main__':main()
