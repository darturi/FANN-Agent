"""Assess the unguarded development return, with conditional diagnostics only."""
import collections,json,os,ast,inspect
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from common import sha,write,THRESHOLDS
from experiment import FAMILIES,POLICIES
from verify_return import lines
HERE=Path(__file__).resolve().parent;STUDY=HERE.parent;RESULTS=STUDY/'returns/job-23045686/results';KIT=STUDY/'kits/unguarded-development-v1'
def main():
 v=json.loads((RESULTS/'local-verification.json').read_text());r=json.loads((RESULTS/'receipt.json').read_text());freeze=json.loads((STUDY/'freeze/unguarded-development-v1.json').read_text());b=json.loads((KIT/'binding.json').read_text())
 assert sha(STUDY/'kits/unguarded-development-v1.tar.gz')==freeze['archive_sha256'] and sha(KIT/'binding.json')==freeze['binding_sha256']
 for key,file in (('protocol_sha256','study-protocol.md'),('config_sha256','config.json'),('module_sha256','vector.so'),('serving_source_sha256','serving.py'),('startup_source_sha256','startup.py'),('plan_sha256','agent-plan.json')):assert sha(KIT/file)==freeze[key]
 prior=json.loads((STUDY/'returns/job-22928562/results/receipt.json').read_text());assert r['graph']==prior['graph']
 elig=json.loads((RESULTS/'eligibility.json').read_text());assert elig==json.loads((STUDY/'returns/job-22928562/results/eligibility.json').read_text())
 assert r['limits']['memory_limit']==48*1024**3 and len(set(map(tuple,r['limits']['cores'])))==4
 # Inspect the exact sealed serving source, not a changed local implementation.
 serving=(KIT/'serving.py').read_text();tree=ast.parse(serving);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='request')
 assert [a.arg for a in fn.args.args]==['ann_conn','query','reserve'] and serving.count('.execute(')==1
 assert 'exact' not in ast.get_source_segment(serving,fn) and 'fallback' not in ast.get_source_segment(serving,fn)
 phase_source=(KIT/'experiment.py').read_text();assert "with (args.output/'exact-reference.jsonl')" in phase_source and 'return request(ann,q,' in phase_source
 groups=sorted({x['id'].rsplit('-',1)[0] for x in lines(KIT/'queries.jsonl')});gi={g:i for i,g in enumerate(groups)};families=list(FAMILIES);fi={n:i for i,n in enumerate(families)}
 data=np.zeros((450,7,9,2,2));phases=collections.Counter();components=collections.defaultdict(collections.Counter)
 for filename in ('timing.jsonl','warmup.jsonl'):
  for row in lines(RESULTS/filename):
   phases[filename+'.ann']+=1
   if filename=='warmup.jsonl':continue
   name,ab=row['label'].rsplit('-',1);g=gi[row['id'].rsplit('-',1)[0]];ti=THRESHOLDS.index(row['filter']);f=fi[name];a=0 if ab=='A' else 1;ep=row['epoch'];assert data[g,ti,f,a,ep]==0;data[g,ti,f,a,ep]=row['request_ns']
   for k in ('request_ns','construction_ns','sql_fetch_decode_ns'):components[row['filter'],name][k]+=row[k]
 assert np.all(data>0)
 rng=np.random.default_rng(20261110);flat=data.mean(axis=-1).reshape(450,-1);controls=[];native_ratios=[];noop_ratios=[]
 ni=fi['native640'];zi=fi['noop640']
 for start in range(0,20000,500):
  w=rng.multinomial(450,np.full(450,1/450),size=500);means=(w@flat/450).reshape(-1,7,9,2)
  controls.append(means[:,:,:,0]/means[:,:,:,1]);scalar=means[:,1:,:,:].mean(axis=(1,3));native_ratios.append(scalar/scalar[:,ni,None]);noop_ratios.append(scalar/scalar[:,zi,None])
 controls=np.concatenate(controls);native_ratios=np.concatenate(native_ratios);noop_ratios=np.concatenate(noop_ratios)
 metrics={}
 for f,name in enumerate(families):
  m=v['metrics'][name];per={}
  for ti,t in enumerate(THRESHOLDS):
   cell=m['per_condition'][str(t)];ab_ci=np.quantile(controls[:,ti,f],[.05,.95]).tolist();c=components[t,name]
   per[str(t)]={**cell,'ab_ratio_90pct_conditional_interval':ab_ci,'ab_interval_inside_098_102':ab_ci[0]>=.98 and ab_ci[1]<=1.02,'mean_construction_ms':c['construction_ns']/1800/1e6,'mean_sql_fetch_decode_ms':c['sql_fetch_decode_ns']/1800/1e6}
  epochs={str(ep):{'scalar_mean_ms':data[:,1:,f,:,ep].mean()/1e6,'ratio_to_native640':data[:,1:,f,:,ep].mean()/data[:,1:,ni,:,ep].mean(),'ratio_to_noop640':data[:,1:,f,:,ep].mean()/data[:,1:,zi,:,ep].mean()} for ep in (0,1)}
  metrics[name]={**{k:val for k,val in m.items() if k!='per_condition'},'per_condition':per,'reduction_percent_vs_native640':100*(1-m['scalar_mean_ratio_to_native640']),'ratio_to_noop640':m['equal_scalar_mean_ms']/v['metrics']['noop640']['equal_scalar_mean_ms'],'scalar_ratio_vs_native640_95pct_conditional_interval':np.quantile(native_ratios[:,f],[.025,.975]).tolist(),'scalar_ratio_vs_noop640_95pct_conditional_interval':np.quantile(noop_ratios[:,f],[.025,.975]).tolist(),'epochs':epochs}
 for name in ('native640','noop640',*POLICIES):
  assert sum(c['short_outputs'] for c in metrics[name]['per_condition'].values())==541 and all(c['recall_losses_to_native640']==0 for c in metrics[name]['per_condition'].values())
 setup=json.loads((RESULTS/'setup.json').read_text());maps=json.loads((RESULTS/'membership-setup.json').read_text());assert len(maps)==7
 for m in maps:assert m['qualifying']==len(elig[str(m['threshold'])]) and m['build_ns']>0
 for cell in setup:
  if cell['phase']!='offline_reference':assert cell['open_attach_ns']>0 and cell['close_ns']>0
 scheduler={'source':'user pasted sacct output from Torch','job_id':'23045686','state':'COMPLETED','exit_code':'0:0','elapsed':'00:43:47','step_elapsed':'00:43:45','step_maxrss_kib':6772996,'batch_state':'COMPLETED','batch_exit_code':'0:0','step_state':'COMPLETED','step_exit_code':'0:0','gate':'passed'};write(RESULTS/'scheduler-reported.json',scheduler)
 assessment={'status':'unguarded_runtime_verified_performance_contrasts_inconclusive_controls','scheduler_gate':'passed_user_reported_COMPLETED_0:0','groups':450,'conditions':7,'quality_family_results':28350,'compiled_policy_cases':9450,'timed_requests':113400,'warmups':2520,'ledger':r['searches'],'phase_counts':dict(phases),'exact_search_role':{'offline_reference_calls':3150,'serving_exact_calls':0,'exact_offline_query_ns':v['offline_reference_query_ns'],'all_reference_connections_closed_before_approximate_phases':True,'source_capability_check':'sealed serving accepts only ANN connection/query/reservation and executes one SELECT; no truth/fallback/exact connection','evidence_limit':'phase separation supported by sealed guest implementation and bound receipts/counters; no independent per-SQL wire trace retained'},'graph_matches_prior_qualification':True,'eligibility_matches_prior_qualification':True,'metrics':metrics,'nominal_development_agent_nominee':v['development_agent_nominee'],'matched_quality_native_nominee':v['matched_quality_native_nominee'],'performance_promotion':False,'bootstrap':{'draws':20000,'seed':20261110,'unit':'450 vector groups jointly across every filter/family/label/epoch','limitation':'conditional on one Torch allocation; not the protocol confirmatory allocation-level inference'},'setup_totals_ns':{k:sum(row.get(k,0) for row in setup) for k in ('open_attach_ns','warmup_ns','close_ns')},'membership_build_ns':sum(m['build_ns'] for m in maps),'provider_calls':0,'validation_test_outcomes_opened':False,'final_policy_selected':False,'recommendation':'Retain valid scientific results and all filters. Before validation, prepare one bounded timing-attribution diagnostic with unchanged policies/graph, counterbalanced reader-role assignment plus per-backend/CPU/order attribution; keep original pooled means, no control-gap subtraction or reader cherry-picking. No automatic rerun or further agent requests.'}
 write(RESULTS/'unguarded-assessment.json',assessment)
 print(json.dumps({'agent_nominee':v['development_agent_nominee'],'native_nominee':v['matched_quality_native_nominee'],'metrics':{n:{k:m[k] for k in ('equal_scalar_mean_ms','reduction_percent_vs_native640','quality_preserves_raw_native640','ratio_to_noop640','scalar_ratio_vs_native640_95pct_conditional_interval','epochs')} for n,m in metrics.items()},'all_bad_controls':{n:[t for t,c in m['per_condition'].items() if not c['ab_interval_inside_098_102']] for n,m in metrics.items()}},indent=2))
if __name__=='__main__':main()
