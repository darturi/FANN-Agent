"""Reconstruct offline truth, all partial outputs, real unguarded timings and ledger."""
import argparse,collections,json,re
from pathlib import Path
from common import THRESHOLDS,matches,require,sha,threshold,write
from experiment import FAMILIES,POLICIES,LABELS,ordered,order_for,validate,result_only

def lines(path):
 with path.open() as f:
  for line in f:
   if line.strip():yield json.loads(line)

def scan_nodes(plan):
 return ([plan] if 'Scan' in plan['Node Type'] else [])+[v for c in plan.get('Plans',[]) for v in scan_nodes(c)]

def verify(results,kit):
 for line in (kit/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);require(sha(kit/n)==h,'kit hash differs: '+n)
 host=json.loads((results/'host-exit.json').read_text());receipt=json.loads((results/'receipt.json').read_text());binding=json.loads((kit/'binding.json').read_text())
 require(host['exit_code']==0 and receipt['job_id']==host['job_id'] and receipt['status']=='unguarded_development_qualified_and_timed','job did not complete')
 for n,h in receipt['raw_sha256'].items():require(sha(results/n)==h,'raw hash differs: '+n)
 for key in ('module_sha256','serving_source_sha256','startup_source_sha256','agent_plan_sha256','compiled_policies_sha256'):require(receipt[key]==binding[key],'binding differs: '+key)
 require(receipt['split_sha256']==binding['split_manifest_sha256'] and receipt['selected_parent_ef_search']==640 and receipt['provider_calls']==receipt['validation_test_queries']==receipt['exact_serving_calls']==0 and receipt['exact_offline_reference_calls']==3150,'scope differs')
 require(receipt['exported_snapshot_shared'] and receipt['data_index_before_after'] and receipt['cleanup_verified'],'integrity gate failed')
 queries=list(lines(kit/'queries.jsonl'));qs={q['id']:q for q in queries};require(len(qs)==len(queries)==3150,'query inventory')
 groups={int(re.fullmatch(r'reviews-clean-v(\d+)-(?:unfiltered|votes\d+)',q['id'])[1]) for q in queries};require(groups==set(binding['development_source_indices']) and len(groups)==450,'split inventory')
 expected={r['id']:r for r in lines(kit/'expected.jsonl')};prior={r['id']:r for r in lines(kit/'prior-references.jsonl')};require(set(expected)==set(prior)==set(qs),'reference coverage')
 eligible={int(t):set(ids) for t,ids in json.loads((results/'eligibility.json').read_text()).items()};require(set(eligible)==set(THRESHOLDS),'eligibility scope')
 truths={};reference_ns=0
 for r in lines(results/'exact-reference.jsonl'):
  qid=r['id'];require(qid in qs and qid not in truths and r['filter']==threshold(qs[qid]),'exact reference inventory')
  require(matches(r['output'],prior[qid]['exact']) and r['reference_query_ns']>0,'exact reference changed');truths[qid]=r['output'];reference_ns+=r['reference_query_ns']
 require(set(truths)==set(qs),'missing exact truth');count=collections.Counter(reference_exact=3150)
 cache={};quality=collections.defaultdict(list)
 for t in THRESHOLDS:
  nodes=scan_nodes(json.loads((results/f'exact-plan-{t}.json').read_text()));require(len(nodes)==1 and nodes[0]['Node Type']=='Seq Scan' and nodes[0]['Relation Name']=='reviews','offline exact plan differs')
  plans=json.loads((results/f'plans-{t}.json').read_text());require(set(plans)==set(FAMILIES),'ANN plan inventory')
  for plan in plans.values():
   nodes=scan_nodes(plan);require(len(nodes)==1 and nodes[0].get('Index Name')=='reviews_hnsw' and nodes[0]['Relation Name']=='reviews','ANN plan differs')
 for r in lines(results/'quality.jsonl'):
  qid=r['id'];t=r['filter'];require(qid in qs and threshold(qs[qid])==t and (qid,'native640') not in cache,'quality inventory')
  count['capture']+=1
  require([{k:v for k,v in o.items() if k!='collection_ns'} for o in r['checkpoints']]==[{k:v for k,v in o.items() if k!='collection_ns'} for o in expected[qid]['checkpoints']],'checkpoint parity')
  require(set(r['results'])==set(FAMILIES),'family inventory')
  for name,v in r['results'].items():
   require(set(v)=={'checkpoint','recall','output','returned_count','request_ns','construction_ns','sql_fetch_decode_ns'},'unexpected quality or fallback fields')
   score=validate(result_only(v),qs[qid],eligible[t],truths[qid]);require(abs(score-v['recall'])<1e-12,'recall differs')
   if name in expected[qid]['results']:
    e=expected[qid]['results'][name];require(v['checkpoint']==e['checkpoint'] and matches(v['output'],e['output']) and abs(score-e['recall'])<1e-12,'raw live first-stop/output differs')
   if FAMILIES[name][1] is None:require(v['checkpoint']==0,'native recorded a policy stop')
   if v['checkpoint']:require(v['returned_count']==10 and v['checkpoint'] in (16,32,64),'invalid compiled stop')
   count['ann']+=1;cache[qid,name]=v;quality[t,name].append((qid,v))
  require(matches(r['results']['noop640']['output'],r['results']['native640']['output']),'no-op changed native')
 require(len(cache)==28350 and all(len(quality[t,n])==450 for t in THRESHOLDS for n in FAMILIES),'incomplete quality')
 times=collections.defaultdict(list)
 # Reconstruct actual file order, not merely order metadata or unique coverage.
 for filename,warmup in (('timing.jsonl',False),('warmup.jsonl',True)):
  stream=iter(lines(results/filename));seen=set()
  for epoch in (0,1):
   filters=list(THRESHOLDS);filters=filters[epoch:]+filters[:epoch]
   for t in filters:
    cases=ordered(queries,t,epoch)
    sequence=((q,label) for label in LABELS for q in cases[:10]) if warmup else ((q,label) for j,q in enumerate(cases) for label in order_for(j,epoch,THRESHOLDS.index(t)))
    indices={q['id']:j for j,q in enumerate(cases)}
    for q,label in sequence:
     r=next(stream,None);require(r is not None,'missing timing/warmup row');qid=q['id'];key=qid,epoch,label
     require((r['id'],r['filter'],r['epoch'],r['label'])==(qid,t,epoch,label) and key not in seen,'execution order/inventory differs');seen.add(key)
     if not warmup:
      order=order_for(indices[qid],epoch,THRESHOLDS.index(t));pos=order.index(label);require(r['order']==order and r['position']==pos and r['predecessor']==(order[pos-1] if pos else None),'timing schedule differs')
     allowed={'id','filter','epoch','label','output','returned_count','request_ns','construction_ns','sql_fetch_decode_ns'} | (set() if warmup else {'order','position','predecessor'})
     require(set(r)==allowed,'unexpected timed metadata or fallback fields');name=label.rsplit('-',1)[0];e=cache[qid,name]
     require(matches(r['output'],e['output']),'timed output differs');validate(result_only(r),q,eligible[t],truths[qid]);count['ann']+=1
     if not warmup:times[t,label].append(r['request_ns'])
  require(next(stream,None) is None and len(seen)==(2520 if warmup else 113400),'extra or missing timing/warmup rows')
 require(all(len(times[t,l])==900 for t in THRESHOLDS for l in LABELS),'timing cell coverage')
 expected_count={'reference_exact':3150,'capture':3150,'ann':144270}
 require(dict(count)==expected_count and receipt['searches']=={**expected_count,'total':150570},'attempt ledger differs or serving exact executed')
 offline=json.loads((results/'offline-reference-cost.json').read_text());require(offline['queries']==3150 and offline['query_ns']==reference_ns and not offline['included_in_serving_endpoint'] and offline['all_exact_connections_closed_before_approximate_quality_and_timing'],'reference cost separation differs')
 startup=json.loads((results/'private-startup.json').read_text());require(startup['max_connections']==32 and startup['only_postgres_setting_change']=='max_connections16->32','private startup contract differs')
 setup=json.loads((results/'setup.json').read_text());require(len(setup)==28 and sum(r.get('warmup_requests',0) for r in setup)==2520 and all(r['connections']==18 for r in setup if r['phase']=='timing'),'setup or timed reader inventory differs')
 summaries={}
 for name in FAMILIES:
  means={str(t):sum(times[t,name+'-A']+times[t,name+'-B'])/1800/1e6 for t in THRESHOLDS};per={}
  for t in THRESHOLDS:
   rows=quality[t,name];per[str(t)]={'queries':450,'mean_recall':sum(v['recall'] for _,v in rows)/450,'short_outputs':sum(v['returned_count']<min(10,len(eligible[t])) for _,v in rows),'mean_returned_count':sum(v['returned_count'] for _,v in rows)/450,'recall_losses_to_native640':sum(v['recall']<cache[qid,'native640']['recall']-1e-12 for qid,v in rows),'stops':sum(v['checkpoint']>0 for _,v in rows),'mean_ms':means[str(t)],'identical_code_ab_ratio':sum(times[t,name+'-A'])/sum(times[t,name+'-B'])}
  summaries[name]={'per_condition':per,'equal_scalar_mean_ms':sum(means[str(t)] for t in THRESHOLDS if t>=0)/6,'quality_preserves_raw_native640':all(v['recall_losses_to_native640']==0 for v in per.values()),'absolute_95pct_floor_met_all_conditions':all(v['mean_recall']>=.95 for v in per.values())}
 native=summaries['native640']['equal_scalar_mean_ms']
 for m in summaries.values():m['scalar_mean_ratio_to_native640']=m['equal_scalar_mean_ms']/native
 eligible_policies=[n for n in POLICIES if summaries[n]['quality_preserves_raw_native640']]
 nominee=None
 if eligible_policies:
  best=min(summaries[n]['equal_scalar_mean_ms'] for n in eligible_policies);ties=[n for n in eligible_policies if summaries[n]['equal_scalar_mean_ms']<=best*1.01]
  programs=json.loads((kit/'compiled-policies.json').read_text())['arms'];byname={p['name']:p for p in programs.values()}
  def key(n):
   import hashlib
   p=byname[n];clauses=[c for values in p['rules'].values() for c in values];comparisons=sum(len(c['conditions']) for c in clauses);canonical=json.dumps(p['rules'],sort_keys=True,separators=(',',':')).encode()
   return comparisons,len(clauses),hashlib.sha256(canonical).hexdigest()
  nominee=min(ties,key=key)
 native_candidates=[n for n in FAMILIES if n.startswith('native') and summaries[n]['quality_preserves_raw_native640']];best=min(summaries[n]['equal_scalar_mean_ms'] for n in native_candidates);tuned=max((n for n in native_candidates if summaries[n]['equal_scalar_mean_ms']<=best*1.01),key=lambda n:FAMILIES[n][0])
 report={'status':'unguarded_development_return_verified','groups':450,'conditions':7,'quality_cases_per_family':3150,'quality_family_results':28350,'compiled_policy_cases':9450,'timed_requests':113400,'warmups':2520,'attempts':dict(count),'total_attempts':150570,'exact_serving_calls':0,'offline_reference_query_ns':reference_ns,'metrics':summaries,'development_agent_nominee':nominee,'matched_quality_native_nominee':tuned,'absolute_recall_floor':'reported diagnostic; not a relative-preservation gate','latency_claim':'one-allocation development measurements only; not final practical-benefit/equivalence inference','final_policy_selected':False,'scheduler_gate':'requires user-reported sacct COMPLETED0:0','validation_test_outcomes_opened':False}
 write(results/'local-verification.json',report);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--kit',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.results,a.kit),indent=2))
