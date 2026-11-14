"""Synthetic full-size return exercises inventory and corruption rejection, not timing evidence."""
import collections,json,tempfile
from pathlib import Path
from common import sha,write,threshold,THRESHOLDS
from experiment import LABELS,ARMS,ordered,order_for
from verify_return import verify,lines
HERE=Path(__file__).resolve().parent;KIT=HERE.parent/'kits/agent-policy-qualification-v1'
def emit(f,r):f.write(json.dumps(r,separators=(',',':'))+'\n')
def main():
 queries=list(lines(KIT/'queries.jsonl'));expected={r['id']:r for r in lines(KIT/'expected.jsonl')};prior={r['id']:r for r in lines(KIT/'prior-references.jsonl')};binding=json.loads((KIT/'binding.json').read_text());counter=collections.Counter()
 def result(e):
  counter['ann']+=1;counter['completion_exact']+=e['fallback_used']
  return {**e,'initial_count':len(e['initial']),'required_count':10,'request_ns':1100 if e['fallback_used'] else 1000,'ann_ns':900,'fallback_ns':100 if e['fallback_used'] else 0,'guard_and_construction_ns':100}
 with tempfile.TemporaryDirectory(prefix='agent-verifier-fixture-') as tmp:
  out=Path(tmp);write(out/'host-exit.json',{'exit_code':0,'job_id':'synthetic-only'})
  write(out/'eligibility.json',json.loads((HERE.parent/'returns/job-22684501/results/eligibility.json').read_text()))
  with (out/'quality.jsonl').open('w') as f:
   for q in queries:
    qid=q['id'];e=expected[qid];r={'id':qid,'filter':threshold(q),'checkpoints':e['checkpoints'],'exact':prior[qid]['exact'],'results':{name:result(e[name]) for name in ARMS}};emit(f,r);counter['reference_exact']+=1;counter['capture']+=1
  for filename,warmup in (('timing.jsonl',False),('warmup.jsonl',True)):
   with (out/filename).open('w') as f:
    for ep in (0,1):
     for t in THRESHOLDS:
      for j,q in enumerate(ordered(queries,t,ep)[:10] if warmup else ordered(queries,t,ep)):
       order=order_for(j,ep,THRESHOLDS.index(t))
       for pos,label in enumerate(order):
        r={'id':q['id'],'filter':t,'epoch':ep,'label':label,**result(expected[q['id']][label.rsplit('-',1)[0]])}
        if not warmup:r.update(order=order,position=pos,predecessor=order[pos-1] if pos else None)
        emit(f,r)
  receipt={'job_id':'synthetic-only','status':'three_agent_policies_qualified_and_development_timed','split_sha256':binding['split_manifest_sha256'],'selected_parent_ef_search':640,'provider_calls':0,'validation_test_queries':0,'exported_snapshot_shared':True,'data_index_before_after':True,'cleanup_verified':True,'searches':{**counter,'total':sum(counter.values())},**{k:binding[k] for k in ('module_sha256','guard_source_sha256','agent_plan_sha256','compiled_policies_sha256')}}
  def seal():
   receipt['raw_sha256']={p.name:sha(p) for p in out.iterdir() if p.name not in ('receipt.json','local-verification.json')};write(out/'receipt.json',receipt)
  seal();report=verify(out,KIT);assert report['compiled_policy_cases']==9450 and report['timed_requests']==50400
  # Resign the changed fixture so the semantic check, rather than only a hash, catches it.
  p=out/'timing.jsonl';content=p.read_text();first,rest=content.split('\n',1);r=json.loads(first);r['position']+=1;p.write_text(json.dumps(r)+'\n'+rest);seal()
  try:verify(out,KIT)
  except RuntimeError as error:assert 'schedule differs' in str(error)
  else:raise AssertionError('bad schedule accepted')
  p.write_text(content);p=out/'quality.jsonl';first,rest=p.read_text().split('\n',1);r=json.loads(first);r['results']['conservative_a']['checkpoint']=123;p.write_text(json.dumps(r)+'\n'+rest);seal()
  try:verify(out,KIT)
  except RuntimeError as error:assert 'live first stop/output differs' in str(error)
  else:raise AssertionError('bad compiled stop accepted')
 result={'status':'passed','fixture':'synthetic return from frozen development references; fabricated timers; no live runtime/latency claim','all_quality_cases':3150,'compiled_policy_cases':9450,'timings':50400,'warmups':1120,'schedule_corruption_rejected':True,'first_stop_corruption_rejected':True,'attempt_ledger_reconstructed':True,'holdout_access':False}
 write(HERE/'checks/verifier-check.json',result);print(json.dumps(result))
if __name__=='__main__':main()
