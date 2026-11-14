"""Independent full inventory/output/schedule/timer/attempt reconstruction."""
import argparse,collections,json,re
from pathlib import Path
from common import THRESHOLDS,matches,require,sha,threshold,write
from experiment import ARMS,LABELS,ordered,order_for,validate

def lines(path):
 with path.open() as f:
  for line in f:
   if line.strip():yield json.loads(line)
def verify(results,kit):
 for line in (kit/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);require(sha(kit/n)==h,'kit hash differs: '+n)
 host=json.loads((results/'host-exit.json').read_text());receipt=json.loads((results/'receipt.json').read_text());binding=json.loads((kit/'binding.json').read_text())
 require(host['exit_code']==0 and receipt['job_id']==host['job_id'] and receipt['status']=='three_agent_policies_qualified_and_development_timed','job did not complete')
 for n,h in receipt['raw_sha256'].items():require(sha(results/n)==h,'raw hash differs: '+n)
 for key in ('module_sha256','guard_source_sha256','agent_plan_sha256','compiled_policies_sha256'):require(receipt[key]==binding[key],'binding differs: '+key)
 require(receipt['split_sha256']==binding['split_manifest_sha256'] and receipt['selected_parent_ef_search']==640 and receipt['provider_calls']==receipt['validation_test_queries']==0,'scope differs')
 require(receipt['exported_snapshot_shared'] and receipt['data_index_before_after'] and receipt['cleanup_verified'],'integrity gate failed')
 queries=list(lines(kit/'queries.jsonl'));qs={q['id']:q for q in queries};require(len(qs)==len(queries)==3150,'query inventory')
 groups={int(re.fullmatch(r'reviews-clean-v(\d+)-(?:unfiltered|votes\d+)',q['id'])[1]) for q in queries};require(groups==set(binding['development_source_indices']) and len(groups)==450,'split inventory')
 expected={r['id']:r for r in lines(kit/'expected.jsonl')};prior={r['id']:r for r in lines(kit/'prior-references.jsonl')};require(set(expected)==set(prior)==set(qs),'reference coverage')
 eligible={int(t):set(ids) for t,ids in json.loads((results/'eligibility.json').read_text()).items()};require(set(eligible)==set(THRESHOLDS),'eligibility scope')
 count=collections.Counter();cache={};quality=collections.defaultdict(list)
 for r in lines(results/'quality.jsonl'):
  qid=r['id'];require(qid in qs and threshold(qs[qid])==r['filter'] and (qid,'native') not in cache,'quality inventory')
  require(matches(r['exact'],prior[qid]['exact']),'fresh exact differs');count['reference_exact']+=1;count['capture']+=1
  require([{k:v for k,v in o.items() if k!='collection_ns'} for o in r['checkpoints']]==[{k:v for k,v in o.items() if k!='collection_ns'} for o in expected[qid]['checkpoints']],'checkpoint parity')
  require(set(r['results'])==set(ARMS),'policy inventory')
  for name,v in r['results'].items():
   e=expected[qid][name];require(v['checkpoint']==e['checkpoint'] and matches(v['initial'],e['initial']) and matches(v['output'],e['output']) and v['fallback_used']==e['fallback_used'],'live first stop/output differs')
   score=validate(v,qs[qid],eligible[r['filter']],r['exact']);require(abs(score-v['recall'])<1e-12 and abs(score-e['recall'])<1e-12,'recall differs')
   require(score>=r['results']['native']['recall']-1e-12,'recall loss');count['ann']+=1;count['completion_exact']+=v['fallback_used'];cache[qid,name]=v;quality[r['filter'],name].append(score)
 require(len(cache)==12600 and all(len(quality[t,n])==450 and sum(quality[t,n])/450>=.95 for t in THRESHOLDS for n in ARMS),'incomplete quality/floor')
 times=collections.defaultdict(list)
 for filename,warmup in (('timing.jsonl',False),('warmup.jsonl',True)):
  seen=set();sequences={}
  for epoch in (0,1):
   for t in THRESHOLDS:sequences[epoch,t]=[q['id'] for q in ordered(queries,t,epoch)]
  for r in lines(results/filename):
   qid=r['id'];t=r['filter'];ep=r['epoch'];label=r['label'];key=qid,ep,label
   require(qid in qs and threshold(qs[qid])==t and ep in (0,1) and label in LABELS and key not in seen,'timing/warmup inventory');seen.add(key)
   j=sequences[ep,t].index(qid)
   if warmup:require(j<10,'wrong warmup')
   else:
    order=order_for(j,ep,THRESHOLDS.index(t));pos=order.index(label)
    require(r['order']==order and r['position']==pos and r['predecessor']==(order[pos-1] if pos else None),'schedule differs')
   name=label.rsplit('-',1)[0];e=cache[qid,name]
   require(matches(r['initial'],e['initial']) and matches(r['output'],e['output']) and r['fallback_used']==e['fallback_used'],'timed/warmup identity differs')
   validate(r,qs[qid],eligible[t],prior[qid]['exact']);count['ann']+=1;count['completion_exact']+=r['fallback_used']
   if not warmup:times[t,label].append(r['request_ns'])
  require(len(seen)==(1120 if warmup else 50400),'timing/warmup coverage')
 require(all(len(times[t,l])==900 for t in THRESHOLDS for l in LABELS),'timing cell coverage')
 require(receipt['searches']['total']==sum(count.values())<=160000 and all(receipt['searches'].get(k,0)==v for k,v in count.items()),'attempt ledger differs')
 metrics={}
 for name in ARMS:
  per={str(t):sum(times[t,name+'-A']+times[t,name+'-B'])/1800/1e6 for t in THRESHOLDS}
  metrics[name]={'per_condition_mean_ms':per,'equal_scalar_mean_ms':sum(per[str(t)] for t in THRESHOLDS if t>=0)/6,'identical_code_point_ratios':{str(t):sum(times[t,name+'-A'])/sum(times[t,name+'-B']) for t in THRESHOLDS}}
 for m in metrics.values():m['scalar_mean_ratio_to_native']=m['equal_scalar_mean_ms']/metrics['native']['equal_scalar_mean_ms']
 report={'status':'all_three_policies_verified_and_development_timed','groups':450,'quality_cases':3150,'compiled_policy_cases':9450,'timed_requests':50400,'warmup_requests':1120,'attempts':dict(count),'total_attempts':sum(count.values()),'metrics':metrics,'selection':'No final selection or validation access. Means and A/B point ratios are one-allocation development diagnostics; no confirmatory benefit claim.','validation_test_outcomes_opened':False,'scheduler_gate':'requires independent sacct COMPLETED 0:0 confirmation','module_sha256':binding['module_sha256']}
 write(results/'local-verification.json',report);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--kit',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.results,a.kit),indent=2))
