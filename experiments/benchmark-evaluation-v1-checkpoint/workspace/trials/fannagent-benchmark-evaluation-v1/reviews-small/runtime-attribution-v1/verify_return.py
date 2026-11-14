"""Reconstruct role/reader/CPU crossover, original-module timings and separate work counts."""
import argparse,collections,json
from pathlib import Path
from common import THRESHOLDS,matches,sha,require,write,threshold
from design import FAMILIES,ARMS,BLOCKS,role,cpu_for,order_for,ordered,forward_index,TIMING_ATTEMPTS,WORK_ATTEMPTS,TOTAL_ATTEMPTS
from experiment import SERVING_KEYS,COUNTERS,GRAPH_COUNTERS,validate

def lines(p):
 with p.open() as f:
  for line in f:
   if line.strip():yield json.loads(line)
def result(r):return {k:r[k] for k in SERVING_KEYS}
def scans(n):return ([n] if 'Scan' in n['Node Type'] else [])+[v for c in n.get('Plans',[]) for v in scans(c)]
def phase_receipt(folder,phase,binding):
 r=json.loads((folder/'receipt.json').read_text());require(r['status']=='attribution_'+phase+'_complete' and r['phase']==phase,'phase did not complete')
 for name,h in r['raw_sha256'].items():require(sha(folder/name)==h,'raw hash differs: '+phase+'/'+name)
 require(r['module_sha256']==binding[phase+'_module_sha256'],'wrong phase module; instrumentation contaminated timing')
 for key in ('agent_plan_sha256','compiled_policies_sha256','serving_source_sha256','startup_source_sha256'):require(r[key]==binding[key],'binding differs')
 require(r['split_sha256']==binding['split_manifest_sha256'] and r['provider_calls']==r['validation_test_queries']==r['exact_serving_calls']==0 and r['exact_offline_reference_calls']==3150,'scope or exact serving differs')
 require(r['groups']==450 and r['families']==5 and r['exported_snapshot_shared'] and r['data_index_before_after'] and r['cleanup_verified'],'integrity gate failed')
 require(r['limits']['memory_limit']==48*1024**3 and len(set(map(tuple,r['limits']['cores'])))==4,'resource contract differs')
 cpus=json.loads((folder/'allowed-cpus.json').read_text());require(len(cpus)==len(set(cpus))==4 and cpus==sorted(cpus) and set(cpus)==set(r['limits']['cpus']),'CPU inventory differs')
 startup=json.loads((folder/'private-startup.json').read_text());require(startup['max_connections']==32,'private reader capacity differs')
 return r,cpus

def references(folder,queries,prior):
 truth={};cost=0
 for r in lines(folder/'exact-reference.jsonl'):
  qid=r['id'];require(qid in queries and qid not in truth and r['filter']==threshold(queries[qid]),'offline reference inventory')
  require(matches(r['output'],prior[qid]['exact']) and r['reference_query_ns']>0,'offline truth differs');truth[qid]=r['output'];cost+=r['reference_query_ns']
 require(set(truth)==set(queries),'missing reference query')
 for t in THRESHOLDS:
  nodes=scans(json.loads((folder/f'exact-plan-{t}.json').read_text()));require(len(nodes)==1 and nodes[0]['Node Type']=='Seq Scan' and nodes[0]['Relation Name']=='reviews','offline exact plan differs')
 c=json.loads((folder/'offline-reference-cost.json').read_text());require(c['queries']==3150 and c['query_ns']==cost and not c['included_in_serving_endpoint'] and c['exact_connections_closed_before_search_phases'],'reference cost separation differs')
 return truth

def verify(results,kit):
 for line in (kit/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);require(sha(kit/n)==h,'kit hash differs: '+n)
 b=json.loads((kit/'binding.json').read_text());require(b['timing_module_sha256']!=b['work_module_sha256'],'timing/work modules not separate')
 host=json.loads((results/'host-exit.json').read_text());require(host['exit_code']==0,'host job failed')
 queries=list(lines(kit/'queries.jsonl'));qs={q['id']:q for q in queries};require(len(qs)==3150,'query coverage')
 import re
 groups={int(re.fullmatch(r'reviews-clean-v(\d+)-(?:unfiltered|votes\d+)',qid)[1]) for qid in qs};require(groups==set(b['development_source_indices']) and len(groups)==450,'development group inventory')
 expected={r['id']:r for r in lines(kit/'expected.jsonl')};prior={r['id']:r for r in lines(kit/'prior-references.jsonl')};require(set(expected)==set(prior)==set(qs),'expected/reference inventory')
 tr,cpus=phase_receipt(results/'timing','timing',b);wr,wcpus=phase_receipt(results/'work','work',b)
 require(tr['job_id']==wr['job_id']==host['job_id'] and tr['graph']==wr['graph']==b['graph'],'job/graph differs across modules')
 require(cpus==wcpus,'allocation CPU set changed between stages')
 require(tr['timed_requests']==630000 and tr['warmup_requests']==14000 and wr['timed_requests']==wr['warmup_requests']==0,'phase timing inventory differs')
 eligible={int(t):set(v) for t,v in json.loads((results/'timing/eligibility.json').read_text()).items()};require(set(eligible)==set(THRESHOLDS) and json.loads((results/'timing/eligibility.json').read_text())==json.loads((results/'work/eligibility.json').read_text()),'eligibility differs')
 truths=references(results/'timing',qs,prior);wtruths=references(results/'work',qs,prior);require(all(matches(truths[qid],wtruths[qid]) for qid in qs),'references differ across phases')
 cache={};quality=collections.defaultdict(list)
 for t in THRESHOLDS:
  plans=json.loads((results/'timing'/f'plans-{t}.json').read_text());require(set(plans)==set(FAMILIES),'ANN plan family inventory')
  for plan in plans.values():
   nodes=scans(plan);require(len(nodes)==1 and nodes[0].get('Index Name')=='reviews_hnsw','ANN plan changed')
 for r in lines(results/'timing/quality.jsonl'):
  qid=r['id'];t=r['filter'];require(qid in qs and threshold(qs[qid])==t and (qid,'native640') not in cache and set(r['results'])==set(FAMILIES),'quality coverage')
  strip=lambda o:{k:v for k,v in o.items() if k!='collection_ns'};require(list(map(strip,r['checkpoints']))==list(map(strip,expected[qid]['checkpoints'])),'live features differ')
  for name,v in r['results'].items():
   score=validate(result(v),qs[qid],eligible[t],truths[qid]);e=expected[qid]['results'][name]
   require(v['checkpoint']==e['checkpoint'] and abs(v['recall']-score)<1e-12 and abs(score-e['recall'])<1e-12 and matches(v['output'],e['output']),'quality output/first-stop differs')
   cache[qid,name]=v;quality[t,name].append(v)
 require(len(cache)==15750 and all(len(quality[t,n])==450 for t in THRESHOLDS for n in FAMILIES),'missing quality rows')
 # Each of20 real backend processes per filter must execute all five roles twice.
 assignments={};backend={};visits=collections.Counter();stream=iter(lines(results/'timing/assignments.jsonl'))
 for ti,t in enumerate(THRESHOLDS):
  for block,(cycle,rotation) in enumerate(BLOCKS):
   for reader in range(20):
    a=next(stream,None);require(a is not None,'missing assignment');name=role(reader,rotation);cpu=cpu_for(reader,ti,cpus)
    require((a['filter'],a['block'],a['cycle'],a['rotation'],a['reader'],a['family'],a['cpu'])==(t,block,cycle,rotation,reader,name,cpu) and a['affinity_after']==[cpu] and set(a['affinity_before'])<=set(cpus),'role/CPU assignment differs')
    require(type(a['pid']) is int and a['pid']>0,'invalid backend PID')
    key=t,reader
    if key in backend:require(backend[key]==(a['pid'],cpu),'role rotated into a different backend/CPU')
    else:backend[key]=a['pid'],cpu
    assignments[t,block,reader]=a;visits[t,reader,name]+=1
 require(next(stream,None) is None and len(assignments)==1400,'extra assignments')
 for t in THRESHOLDS:
  require(len({backend[t,r][0] for r in range(20)})==20,'backend PID aliasing')
  for reader in range(20):require(all(visits[t,reader,n]==2 for n in FAMILIES),'incomplete role crossover')
 times=collections.defaultdict(list);cpu_times=collections.defaultdict(list);counts=collections.Counter(reference_exact=3150,capture=3150,ann=15750)
 for filename,warmup in (('timing.jsonl',False),('warmup.jsonl',True)):
  stream=iter(lines(results/'timing'/filename));total=0
  for ti,t in enumerate(THRESHOLDS):
   for block,(cycle,rotation) in enumerate(BLOCKS):
    cases=ordered(queries,t,cycle,rotation)
    sequence=((q,reader,None) for reader in (range(20) if cycle==0 else reversed(range(20))) for q in cases[:10]) if warmup else ((q,reader,(pos,order)) for j,q in enumerate(cases) for order in (order_for(forward_index(j,cycle,450),cycle,rotation,ti),) for pos,reader in enumerate(order))
    for q,reader,schedule in sequence:
     r=next(stream,None);require(r is not None,'missing crossover request');total+=1;name=role(reader,rotation);pid,cpu=backend[t,reader]
     require((r['id'],r['filter'],r['block'],r['cycle'],r['rotation'],r['reader'],r['family'],r['pid'],r['cpu'])==(q['id'],t,block,cycle,rotation,reader,name,pid,cpu),'crossover request order/reader/CPU differs')
     allowed=set(SERVING_KEYS)|{'id','filter','block','cycle','rotation','reader','family','pid','cpu'}
     if not warmup:
      pos,order=schedule;allowed|={'order','position','predecessor'};require(r['order']==order and r['position']==pos and r['predecessor']==(order[pos-1] if pos else None),'Williams order differs')
     require(set(r)==allowed,'unexpected primary timing field; counters or fallback leaked')
     require(matches(r['output'],cache[q['id'],name]['output']),'timed/warmup output differs');validate(result(r),q,eligible[t],truths[q['id']]);counts['ann']+=1
     if not warmup:times[t,name].append(r['request_ns']);cpu_times[t,name,cpu].append(r['request_ns'])
  require(next(stream,None) is None and total==(14000 if warmup else 630000),'timing/warmup coverage differs')
 require(counts=={'reference_exact':3150,'capture':3150,'ann':659750} and tr['searches']=={**dict(counts),'total':TIMING_ATTEMPTS},'timing attempt ledger differs')
 for t in THRESHOLDS:
  for n in FAMILIES:
   require(len(times[t,n])==18000 and all(len(cpu_times[t,n,cpu])==4500 for cpu in cpus),'role/CPU observation coverage differs')
 work={};wstream=iter(lines(results/'work/work.jsonl'));work_pids={}
 for ti,t in enumerate(THRESHOLDS):
  cases=[q for q in queries if threshold(q)==t];cpu=wcpus[ti%4]
  for name in FAMILIES:
   for q in cases:
    r=next(wstream,None);require(r is not None and (r['id'],r['filter'],r['family'])==(q['id'],t,name),'work inventory differs');c=r['counts'];e=expected[q['id']]['results'][name]
    require(set(r)==set(SERVING_KEYS)|{'id','filter','family','checkpoint','recall','counts'},'unexpected work fields')
    score=validate(result(r),q,eligible[t],wtruths[q['id']]);require(matches(r['output'],e['output']) and r['checkpoint']==e['checkpoint'] and abs(score-r['recall'])<1e-12 and abs(score-e['recall'])<1e-12,'work module output/stop parity differs')
    require(set(c)==set(COUNTERS)|{'pid','start_cpu','end_cpu'} and c['start_cpu']==c['end_cpu']==cpu and all(type(c[k]) is int and c[k]>=0 for k in COUNTERS),'work counter/CPU schema differs')
    if t in work_pids:require(work_pids[t]==c['pid'],'work roles did not reuse backend')
    else:work_pids[t]=c['pid']
    require(c['vector_calls']>0 and c['layer0_queue_pops']>0 and c['feature_passes']<=3,'work counter bounds')
    if name=='native640':require(c['feature_passes']==c['membership_probes']==0,'native unexpectedly has feature work')
    work[q['id'],name]=c
 require(next(wstream,None) is None and len(work)==15750,'work coverage differs')
 require(wr['searches']=={'total':WORK_ATTEMPTS,'reference_exact':3150,'ann':15750},'work attempt ledger differs')
 work_summary={}
 for t in THRESHOLDS:
  qids=[q['id'] for q in queries if threshold(q)==t];work_summary[str(t)]={'noop_graph_counter_mismatches':sum(any(work[qid,'noop640'][k]!=work[qid,'native640'][k] for k in GRAPH_COUNTERS) for qid in qids),'means':{n:{k:sum(work[qid,n][k] for qid in qids)/450 for k in COUNTERS} for n in FAMILIES}}
 saved=json.loads((results/'work/work-summary.json').read_text())
 for t in THRESHOLDS:require(saved[str(t)]['noop_graph_counter_mismatches']==work_summary[str(t)]['noop_graph_counter_mismatches'],'work summary mismatch')
 setup=json.loads((results/'timing/setup.json').read_text());require(len(setup)==70 and sum(s['warmup_requests'] for s in setup)==14000,'setup inventory differs')
 metrics={n:{'equal_scalar_mean_ms':sum(sum(times[t,n])/18000/1e6 for t in THRESHOLDS if t>=0)/6,'per_condition_mean_ms':{str(t):sum(times[t,n])/18000/1e6 for t in THRESHOLDS},'per_condition_cpu_mean_ms':{str(t):{str(cpu):sum(cpu_times[t,n,cpu])/4500/1e6 for cpu in cpus} for t in THRESHOLDS}} for n in FAMILIES}
 for n,m in metrics.items():m['ratio_to_native640']=m['equal_scalar_mean_ms']/metrics['native640']['equal_scalar_mean_ms'];m['ratio_to_noop640']=m['equal_scalar_mean_ms']/metrics['noop640']['equal_scalar_mean_ms']
 report={'status':'counterbalanced_attribution_return_verified','groups':450,'conditions':7,'original_module_timing_requests':630000,'warmups':14000,'quality_family_results':15750,'work_queries':15750,'offline_exact_reference_queries':6300,'exact_serving_calls':0,'total_attempts':TOTAL_ATTEMPTS,'timing_attempts':tr['searches'],'work_attempts':wr['searches'],'role_assignments':1400,'roles_per_backend':5,'repetitions_per_role_backend':2,'metrics':metrics,'work':work_summary,'performance_claim':'diagnostic only; instrumentation times excluded; not a new final validation/test result','agent_disposition':'No robust performance success presumed. Unchanged policies; reassess evidence/objective only after diagnostic, preserving a negative result.','scheduler_gate':'requires independent sacct COMPLETED0:0','provider_calls':0,'validation_test_outcomes_opened':False}
 write(results/'local-verification.json',report);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--kit',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.results,a.kit),indent=2))
