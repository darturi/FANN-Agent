"""Full-size synthetic return and corruption checks; fabricated timers, no performance claim."""
import collections,json,tempfile
from pathlib import Path
from common import THRESHOLDS,sha,write,threshold
from support import valid
from experiment import FAMILIES,LABELS,ordered,order_for
from verify_return import verify,lines
HERE=Path(__file__).resolve().parent

def emit(f,r):f.write(json.dumps(r,separators=(',',':'))+'\n')
def run(kit):
 queries=list(lines(kit/'queries.jsonl'));expected={r['id']:r for r in lines(kit/'expected.jsonl')};binding=json.loads((kit/'binding.json').read_text());eligible=json.loads((HERE.parent/'returns/job-22928562/results/eligibility.json').read_text());counter=collections.Counter();cache={}
 def timed(out):
  counter['ann']+=1;return {'output':out,'returned_count':len(out),'request_ns':1000,'construction_ns':100,'sql_fetch_decode_ns':900}
 with tempfile.TemporaryDirectory(prefix='unguarded-verifier-fixture-') as tmp:
  out=Path(tmp);write(out/'host-exit.json',{'exit_code':0,'job_id':'synthetic-only'});write(out/'eligibility.json',eligible);write(out/'private-startup.json',{'max_connections':32,'only_postgres_setting_change':'max_connections16->32'})
  with (out/'exact-reference.jsonl').open('w') as f:
   for q in queries:emit(f,{'id':q['id'],'filter':threshold(q),'output':expected[q['id']]['exact'],'reference_query_ns':10000});counter['reference_exact']+=1
  write(out/'offline-reference-cost.json',{'queries':3150,'query_ns':3150*10000,'included_in_serving_endpoint':False,'all_exact_connections_closed_before_approximate_quality_and_timing':True})
  for t in THRESHOLDS:
   write(out/f'exact-plan-{t}.json',{'Node Type':'Seq Scan','Relation Name':'reviews'})
   write(out/f'plans-{t}.json',{n:{'Node Type':'Index Scan','Relation Name':'reviews','Index Name':'reviews_hnsw'} for n in FAMILIES})
  setup=[{'phase':'offline_reference','filter':t,'total_ns':1} for t in THRESHOLDS]+[{'phase':'quality','filter':t,'connections':10,'open_attach_ns':1,'close_ns':1} for t in THRESHOLDS]+[{'phase':'timing','filter':t,'epoch':ep,'connections':18,'open_attach_ns':1,'close_ns':1,'warmup_requests':180,'warmup_ns':1} for ep in (0,1) for t in THRESHOLDS];write(out/'setup.json',setup)
  with (out/'quality.jsonl').open('w') as f:
   for q in queries:
    qid=q['id'];t=threshold(q);e=expected[qid];results={};counter['capture']+=1
    for name,(ef,arm) in FAMILIES.items():
     if name in e['results']:r=e['results'][name];output=r['output'];cp=r['checkpoint']
     else:output=e['results']['native640']['output'][:{40:2,80:4,160:6,320:8}[ef]];cp=0
     score=valid(output,q,set(eligible[str(t)]),e['exact']);results[name]={'checkpoint':cp,'recall':score,**timed(output)};cache[qid,name]=output
    emit(f,{'id':qid,'filter':t,'checkpoints':e['checkpoints'],'results':results})
  for filename,warmup in (('timing.jsonl',False),('warmup.jsonl',True)):
   with (out/filename).open('w') as f:
    for ep in (0,1):
     filters=list(THRESHOLDS);filters=filters[ep:]+filters[:ep]
     for t in filters:
      cases=ordered(queries,t,ep);sequence=((q,label) for label in LABELS for q in cases[:10]) if warmup else ((q,label) for j,q in enumerate(cases) for label in order_for(j,ep,THRESHOLDS.index(t)))
      indices={q['id']:j for j,q in enumerate(cases)}
      for q,label in sequence:
       r={'id':q['id'],'filter':t,'epoch':ep,'label':label,**timed(cache[q['id'],label.rsplit('-',1)[0]])}
       if not warmup:
        order=order_for(indices[q['id']],ep,THRESHOLDS.index(t));pos=order.index(label);r.update(order=order,position=pos,predecessor=order[pos-1] if pos else None)
       emit(f,r)
  receipt={'job_id':'synthetic-only','status':'unguarded_development_qualified_and_timed','split_sha256':binding['split_manifest_sha256'],'selected_parent_ef_search':640,'provider_calls':0,'validation_test_queries':0,'exact_serving_calls':0,'exact_offline_reference_calls':3150,'exported_snapshot_shared':True,'data_index_before_after':True,'cleanup_verified':True,'searches':{**counter,'total':sum(counter.values())},**{k:binding[k] for k in ('module_sha256','serving_source_sha256','startup_source_sha256','agent_plan_sha256','compiled_policies_sha256')}}
  def seal():
   receipt['raw_sha256']={p.name:sha(p) for p in out.iterdir() if p.name not in ('receipt.json','local-verification.json')};write(out/'receipt.json',receipt)
  seal();report=verify(out,kit);assert report['total_attempts']==150570 and report['exact_serving_calls']==0 and not report['metrics']['native640']['absolute_95pct_floor_met_all_conditions']
  def reject(needle):
   seal()
   try:verify(out,kit)
   except RuntimeError as error:assert needle in str(error),str(error)
   else:raise AssertionError('corruption accepted')
  p=out/'timing.jsonl';original=p.read_text();first,rest=original.split('\n',1);r=json.loads(first);r['position']+=1;p.write_text(json.dumps(r)+'\n'+rest);reject('timing schedule differs');p.write_text(original)
  p=out/'quality.jsonl';original=p.read_text();first,rest=original.split('\n',1);r=json.loads(first);r['results']['native40']['recall']=1;p.write_text(json.dumps(r)+'\n'+rest);reject('recall differs');p.write_text(original)
  receipt['searches']['completion_exact']=1;receipt['searches']['total']+=1;reject('attempt ledger differs')
 result={'status':'passed','fixture':'fabricated full-size return from development outputs; no new ANN queries and no real timing claim','quality_family_results':28350,'timed_requests':113400,'warmups':2520,'attempts':150570,'short_outputs_score_normally':True,'low_absolute_recall_does_not_disqualify_preservation':True,'schedule_corruption_rejected':True,'inflated_partial_result_recall_rejected':True,'completion_exact_attempt_rejected':True,'validation_test_outcomes_opened':False};write(HERE/'checks/verifier-check.json',result);return result
if __name__=='__main__':print(json.dumps(run(HERE.parent/'kits/unguarded-development-v1'),indent=2))
