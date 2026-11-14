"""Full-size synthetic return: 630k fabricated timings, counter/CPU/crossover corruption."""
import collections,json,tempfile,shutil
from pathlib import Path
from common import THRESHOLDS,sha,write,threshold
from support import valid
from design import FAMILIES,BLOCKS,role,cpu_for,order_for,ordered,forward_index
from experiment import COUNTERS,GRAPH_COUNTERS
from verify_return import verify,lines
HERE=Path(__file__).resolve().parent

def emit(f,r):f.write(json.dumps(r,separators=(',',':'))+'\n')
def run(kit):
 queries=list(lines(kit/'queries.jsonl'));expected={r['id']:r for r in lines(kit/'expected.jsonl')};binding=json.loads((kit/'binding.json').read_text());cpus=[0,1,2,3];source=HERE.parent/'returns/job-23045686/results';graph=json.loads((source/'receipt.json').read_text())['graph'];eligible=json.loads((source/'eligibility.json').read_text())
 def timed(output,ns=1000):return {'output':output,'returned_count':len(output),'request_ns':ns,'construction_ns':100,'sql_fetch_decode_ns':ns-100}
 with tempfile.TemporaryDirectory(prefix='attribution-verifier-fixture-') as tmp:
  root=Path(tmp);write(root/'host-exit.json',{'exit_code':0,'job_id':'synthetic-only'})
  for phase in ('timing','work'):
   out=root/phase;out.mkdir();write(out/'eligibility.json',eligible);write(out/'allowed-cpus.json',cpus);write(out/'private-startup.json',{'max_connections':32})
   with (out/'exact-reference.jsonl').open('w') as f:
    for q in queries:emit(f,{'id':q['id'],'filter':threshold(q),'output':expected[q['id']]['exact'],'reference_query_ns':10000})
   for t in THRESHOLDS:write(out/f'exact-plan-{t}.json',{'Node Type':'Seq Scan','Relation Name':'reviews'})
   write(out/'offline-reference-cost.json',{'queries':3150,'query_ns':31500000,'included_in_serving_endpoint':False,'exact_connections_closed_before_search_phases':True})
  out=root/'timing'
  for t in THRESHOLDS:write(out/f'plans-{t}.json',{n:{'Node Type':'Index Scan','Relation Name':'reviews','Index Name':'reviews_hnsw'} for n in FAMILIES})
  with (out/'quality.jsonl').open('w') as f:
   for q in queries:
    e=expected[q['id']];emit(f,{'id':q['id'],'filter':threshold(q),'checkpoints':e['checkpoints'],'results':{n:{'checkpoint':e['results'][n]['checkpoint'],'recall':e['results'][n]['recall'],**timed(e['results'][n]['output'])} for n in FAMILIES}})
  with (out/'assignments.jsonl').open('w') as f:
   for ti,t in enumerate(THRESHOLDS):
    for block,(cycle,rotation) in enumerate(BLOCKS):
     for reader in range(20):
      cpu=cpu_for(reader,ti,cpus);emit(f,{'filter':t,'block':block,'cycle':cycle,'rotation':rotation,'reader':reader,'family':role(reader,rotation),'pid':10000+ti*100+reader,'cpu':cpu,'affinity_before':cpus,'affinity_after':[cpu]})
  for filename,warmup in (('timing.jsonl',False),('warmup.jsonl',True)):
   with (out/filename).open('w') as f:
    for ti,t in enumerate(THRESHOLDS):
     for block,(cycle,rotation) in enumerate(BLOCKS):
      cases=ordered(queries,t,cycle,rotation)
      seq=((q,reader,None) for reader in (range(20) if cycle==0 else reversed(range(20))) for q in cases[:10]) if warmup else ((q,reader,(pos,order)) for j,q in enumerate(cases) for order in (order_for(forward_index(j,cycle,450),cycle,rotation,ti),) for pos,reader in enumerate(order))
      for q,reader,sched in seq:
       n=role(reader,rotation);cpu=cpu_for(reader,ti,cpus);r={'id':q['id'],'filter':t,'block':block,'cycle':cycle,'rotation':rotation,'reader':reader,'family':n,'pid':10000+ti*100+reader,'cpu':cpu,**timed(expected[q['id']]['results'][n]['output'],1000+FAMILIES.index(n)*100+cpu*10+reader%5)}
       if sched:
        pos,order=sched;r.update(order=order,position=pos,predecessor=order[pos-1] if pos else None)
       emit(f,r)
  write(out/'setup.json',[{'filter':t,'block':block,'warmup_requests':200} for t in THRESHOLDS for block in range(10)])
  out=root/'work'
  with (out/'work.jsonl').open('w') as f:
   for ti,t in enumerate(THRESHOLDS):
    for n in FAMILIES:
     for q in (q for q in queries if threshold(q)==t):
      e=expected[q['id']]['results'][n];base=10000 if not e['checkpoint'] else 5000
      c={'vector_calls':base,'layer0_neighbor_scores':base-100,'upper_neighbor_scores':80,'layer0_queue_pops':base//20,'layer0_adjacencies_examined':base*4,'feature_passes':0 if n=='native640' else 3,'membership_probes':0 if n=='native640' else 1000,'pid':20000+ti,'start_cpu':cpus[ti%4],'end_cpu':cpus[ti%4]}
      emit(f,{'id':q['id'],'filter':t,'family':n,'checkpoint':e['checkpoint'],'recall':e['recall'],'counts':c,**timed(e['output'])})
  write(out/'work-summary.json',{str(t):{'queries_per_family':450,'noop_graph_counter_mismatches':0} for t in THRESHOLDS})
  def seal(phase):
   out=root/phase;work=phase=='work';r={'status':'attribution_'+phase+'_complete','phase':phase,'job_id':'synthetic-only','module_sha256':binding[phase+'_module_sha256'],'split_sha256':binding['split_manifest_sha256'],**{k:binding[k] for k in ('agent_plan_sha256','compiled_policies_sha256','serving_source_sha256','startup_source_sha256')},'provider_calls':0,'validation_test_queries':0,'exact_serving_calls':0,'exact_offline_reference_calls':3150,'groups':450,'families':5,'exported_snapshot_shared':True,'data_index_before_after':True,'cleanup_verified':True,'limits':{'memory_limit':48*1024**3,'cores':[[0,c] for c in cpus],'cpus':cpus},'timed_requests':0 if work else 630000,'warmup_requests':0 if work else 14000,'graph':graph,'searches':{'total':18900,'reference_exact':3150,'ann':15750} if work else {'total':666050,'reference_exact':3150,'capture':3150,'ann':659750},'raw_sha256':{p.name:sha(p) for p in out.iterdir() if p.name!='receipt.json'}};write(out/'receipt.json',r)
  seal('timing');seal('work');v=verify(root,kit);assert v['total_attempts']==684950 and v['original_module_timing_requests']==630000
  from analyse import analyse
  a=analyse(root);assert len(a['timing'])==5 and a['timing']['native640']['ratio_to_native640']==1
  # Tamper/re-sign a small assignment stream, without keeping the timing file in memory.
  p=root/'timing/assignments.jsonl';original=p.read_text();first,rest=original.split('\n',1);r=json.loads(first);r['cpu']=(r['cpu']+1)%4;p.write_text(json.dumps(r)+'\n'+rest);seal('timing')
  try:verify(root,kit)
  except RuntimeError as e:assert 'role/CPU assignment differs' in str(e)
  else:raise AssertionError('bad CPU assignment accepted')
  p.write_text(original);seal('timing')
  # Wrong module must fail before any attempt to use its numbers as timings.
  p=root/'timing/receipt.json';receipt=p.read_text();r=json.loads(receipt);r['module_sha256']=binding['work_module_sha256'];write(p,r)
  try:verify(root,kit)
  except RuntimeError as e:assert 'wrong phase module' in str(e)
  else:raise AssertionError('instrumented timing module accepted')
  p.write_text(receipt)
 result={'status':'passed','fixture':'full-size fabricated timing/counter return from development outputs; no real performance claim','timing_records':630000,'work_records':15750,'warmups':14000,'total_attempts':684950,'exact_scoring_only':True,'full_reader_role_CPU_crossover_verified':True,'incorrect_CPU_assignment_rejected':True,'instrumented_primary_timing_rejected':True,'paired_analysis_executed':True,'validation_test_outcomes_opened':False};write(HERE/'checks/verifier-check.json',result);return result
if __name__=='__main__':print(json.dumps(run(HERE.parent/'kits/reader-attribution-v1'),indent=2))
