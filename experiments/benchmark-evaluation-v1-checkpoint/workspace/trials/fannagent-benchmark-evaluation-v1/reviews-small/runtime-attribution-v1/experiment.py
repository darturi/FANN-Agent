"""Original-module crossover timing, separate instrumented work counts, exact offline only."""
import json,os
from contextlib import ExitStack
from time import perf_counter_ns
from common import THRESHOLDS,search,capture,matches,require,write,threshold
from support import reader,valid,check_plan
from serving import request
from sessions import session,bind,pin
from design import FAMILIES,ARMS,BLOCKS,role,cpu_for,order_for,ordered,forward_index,TIMING_ATTEMPTS,WORK_ATTEMPTS
SERVING_KEYS=('output','returned_count','request_ns','construction_ns','sql_fetch_decode_ns')
COUNTERS=('vector_calls','layer0_neighbor_scores','upper_neighbor_scores','layer0_queue_pops','layer0_adjacencies_examined','feature_passes','membership_probes')
GRAPH_COUNTERS=COUNTERS[:5]

def reserve(counter,op,phase):
 cap=700000 if phase=='timing' else 25000
 require(counter['total']<cap,'diagnostic phase attempt cap');counter['total']+=1;counter[op]=counter.get(op,0)+1

def perform(counter,c,q,phase):return request(c,q,lambda op:reserve(counter,op,phase))

def validate(result,q,eligible,truth):
 require(set(result)==set(SERVING_KEYS) and result['returned_count']==len(result['output']),'unexpected serving metadata or count')
 require(result['request_ns']==result['construction_ns']+result['sql_fetch_decode_ns'] and result['request_ns']>0 and result['sql_fetch_decode_ns']>0 and result['construction_ns']>=0,'timer accounting')
 return valid(result['output'],q,eligible,truth)

def offline(Backend,args,queries,eligible,prior,counter):
 truths={};cost=0
 with (args.output/'exact-reference.jsonl').open('x') as out:
  for t in THRESHOLDS:
   cases=[q for q in queries if threshold(q)==t]
   with reader(Backend,args,t,len(eligible[t]),exact=True) as exact:
    write(args.output/f'exact-plan-{t}.json',check_plan(exact,cases[0],exact=True))
    for q in cases:
     reserve(counter,'reference_exact',args.phase);truth,ns=search(exact,q,exact=True);require(matches(truth,prior[q['id']]['exact']),'offline truth differs');truths[q['id']]=truth;cost+=ns
     out.write(json.dumps({'id':q['id'],'filter':t,'output':truth,'reference_query_ns':ns},allow_nan=False)+'\n')
   out.flush();print(json.dumps({'phase':args.phase+'_offline_exact','filter':t,'attempts':counter['total']}),flush=True)
 write(args.output/'offline-reference-cost.json',{'queries':3150,'query_ns':cost,'included_in_serving_endpoint':False,'exact_connections_closed_before_search_phases':True})
 return truths

def qualify(Backend,args,queries,eligible,expected,truths,counter):
 cache={};summary={}
 with (args.output/'quality.jsonl').open('x') as out:
  for t in THRESHOLDS:
   cases=[q for q in queries if threshold(q)==t];passing=len(eligible[t])
   with ExitStack() as stack:
    shadow=stack.enter_context(reader(Backend,args,t,passing,0));live={name:stack.enter_context(reader(Backend,args,t,passing,ARMS[name])) for name in FAMILIES}
    write(args.output/f'plans-{t}.json',{name:check_plan(c,cases[0]) for name,c in live.items()})
    for j,q in enumerate(cases):
     qid=q['id'];target=expected[qid];reserve(counter,'capture','timing');cap=capture(shadow,q,f'attribution-{t}-{j}');require(matches(cap['output'],target['results']['native640']['output']),'capture output differs')
     strip=lambda o:{k:v for k,v in o.items() if k!='collection_ns'}
     require(list(map(strip,cap['checkpoints']))==list(map(strip,target['checkpoints'])),'causal features differ')
     results={}
     for name,c in live.items():
      result=perform(counter,c,q,'timing');cp=0 if name=='native640' else c.execute('SELECT fannagent.confirm_last()').fetchone()[0];e=target['results'][name];score=validate(result,q,eligible[t],truths[qid])
      require(cp==e['checkpoint'] and matches(result['output'],e['output']) and abs(score-e['recall'])<1e-12,'raw first-stop/output/recall differs')
      results[name]={'checkpoint':cp,'recall':score,**result};cache[qid,name]=results[name]
     out.write(json.dumps({'id':qid,'filter':t,'checkpoints':cap['checkpoints'],'results':results},allow_nan=False)+'\n')
   out.flush();summary[str(t)]={name:{'queries':450,'mean_recall':sum(cache[q['id'],name]['recall'] for q in cases)/450,'short_outputs':sum(cache[q['id'],name]['returned_count']<10 for q in cases)} for name in FAMILIES}
   print(json.dumps({'phase':'timing_module_quality','filter':t,'attempts':counter['total']}),flush=True)
 write(args.output/'quality-summary.json',summary);return cache,summary

def run_timing(Backend,args,queries,eligible,prior,expected,counter):
 cpus=sorted(os.sched_getaffinity(0));require(len(cpus)==4,'requires four allowed CPUs');write(args.output/'allowed-cpus.json',cpus)
 truths=offline(Backend,args,queries,eligible,prior,counter);cache,summary=qualify(Backend,args,queries,eligible,expected,truths,counter);setup=[]
 with (args.output/'timing.jsonl').open('x') as out,(args.output/'warmup.jsonl').open('x') as warm,(args.output/'assignments.jsonl').open('x') as assignment:
  for ti,t in enumerate(THRESHOLDS):
   passing=len(eligible[t]);open_start=perf_counter_ns()
   with ExitStack() as sessions:
    pool={r:sessions.enter_context(session(Backend,args)) for r in range(20)}
    pids={r:c.execute('SELECT pg_backend_pid()').fetchone()[0] for r,c in pool.items()};require(len(set(pids.values()))==20,'readers must be distinct persistent backends')
    placements={r:pin(pids[r],cpu_for(r,ti,cpus),cpus) for r in pool};open_ns=perf_counter_ns()-open_start
    for block,(cycle,rotation) in enumerate(BLOCKS):
     cases=ordered(queries,t,cycle,rotation);started=perf_counter_ns()
     with ExitStack() as transactions:
      for r,c in pool.items():
       require(os.sched_getaffinity(pids[r])=={placements[r]['cpu']},'reader affinity changed')
       name=role(r,rotation);transactions.enter_context(bind(c,args,t,passing,ARMS[name]))
       require(c.execute("SELECT pg_backend_pid(),current_setting('hnsw.ef_search'),current_setting('hnsw.iterative_scan')").fetchone()==(pids[r],'640','off'),'reader PID/settings changed')
       assignment.write(json.dumps({'filter':t,'block':block,'cycle':cycle,'rotation':rotation,'reader':r,'family':name,**placements[r]},allow_nan=False)+'\n')
      attached=perf_counter_ns()
      # Mirror reader warmup order across the matched Latin cycles.
      for r in range(20) if cycle==0 else reversed(range(20)):
       name=role(r,rotation)
       for q in cases[:10]:
        result=perform(counter,pool[r],q,'timing');require(matches(result['output'],cache[q['id'],name]['output']),'warmup output differs')
        warm.write(json.dumps({'id':q['id'],'filter':t,'block':block,'cycle':cycle,'rotation':rotation,'reader':r,'family':name,'pid':pids[r],'cpu':placements[r]['cpu'],**result},allow_nan=False)+'\n')
      warmed=perf_counter_ns()
      for j,q in enumerate(cases):
       order=order_for(forward_index(j,cycle,450),cycle,rotation,ti)
       for pos,r in enumerate(order):
        name=role(r,rotation);result=perform(counter,pool[r],q,'timing');require(matches(result['output'],cache[q['id'],name]['output']),'timed output differs')
        out.write(json.dumps({'id':q['id'],'filter':t,'block':block,'cycle':cycle,'rotation':rotation,'reader':r,'family':name,'pid':pids[r],'cpu':placements[r]['cpu'],'order':order,'position':pos,'predecessor':order[pos-1] if pos else None,**result},allow_nan=False)+'\n')
      closing=perf_counter_ns()
     close_ns=perf_counter_ns()-closing
     for r,pid in pids.items():require(os.sched_getaffinity(pid)=={placements[r]['cpu']},'reader affinity changed during block')
     setup.append({'filter':t,'block':block,'cycle':cycle,'rotation':rotation,'persistent_open_ns':open_ns if block==0 else 0,'bind_ns':attached-started,'warmup_ns':warmed-attached,'transaction_close_ns':close_ns,'warmup_requests':200})
     for file in (out,warm,assignment):file.flush()
     print(json.dumps({'phase':'counterbalanced_timing','filter':t,'block':block,'cycle':cycle,'rotation':rotation,'attempts':counter['total']}),flush=True)
    pool_closing=perf_counter_ns()
   setup[-1]['persistent_close_ns']=perf_counter_ns()-pool_closing
 write(args.output/'setup.json',setup);require(counter=={'total':TIMING_ATTEMPTS,'reference_exact':3150,'capture':3150,'ann':659750},'timing attempt ledger differs')
 return summary

def run_work(Backend,args,queries,eligible,prior,expected,counter):
 cpus=sorted(os.sched_getaffinity(0));require(len(cpus)==4,'requires four CPUs');write(args.output/'allowed-cpus.json',cpus)
 truths=offline(Backend,args,queries,eligible,prior,counter);summary={};cache={}
 with (args.output/'work.jsonl').open('x') as out:
  for ti,t in enumerate(THRESHOLDS):
   cases=[q for q in queries if threshold(q)==t];passing=len(eligible[t])
   with session(Backend,args) as c:
    pid=c.execute('SELECT pg_backend_pid()').fetchone()[0];cpu=cpus[ti%4];placement=pin(pid,cpu,cpus)
    for name in FAMILIES:
     with bind(c,args,t,passing,ARMS[name]):
      for q in cases:
       qid=q['id'];c.execute('SELECT fannagent.diagnostic_reset()');result=perform(counter,c,q,'work');counts=json.loads(c.execute('SELECT fannagent.diagnostic_read()').fetchone()[0]);cp=0 if name=='native640' else c.execute('SELECT fannagent.confirm_last()').fetchone()[0];target=expected[qid]['results'][name]
       score=validate(result,q,eligible[t],truths[qid]);require(cp==target['checkpoint'] and matches(result['output'],target['output']) and abs(score-target['recall'])<1e-12,'instrumented output/first-stop parity differs')
       require(counts['pid']==pid and counts['start_cpu']==counts['end_cpu']==cpu and os.sched_getaffinity(pid)=={cpu},'observed work CPU/PID differs')
       require(set(counts)==set(COUNTERS)|{'pid','start_cpu','end_cpu'} and all(type(counts[k]) is int and counts[k]>=0 for k in COUNTERS),'invalid counters')
       if name=='native640':require(counts['feature_passes']==counts['membership_probes']==0,'native unexpectedly collected decision features')
       require(counts['vector_calls']>0 and counts['layer0_queue_pops']>0 and counts['feature_passes']<=3,'work counter bounds')
       cache[qid,name]=counts
       # Instrumented request time is saved for audit, never pooled into timing estimates.
       out.write(json.dumps({'id':qid,'filter':t,'family':name,'checkpoint':cp,'recall':score,'counts':counts,**result},allow_nan=False)+'\n')
    out.flush()
   summary[str(t)]={'queries_per_family':450,'noop_graph_counter_mismatches':sum(any(cache[q['id'],'noop640'][k]!=cache[q['id'],'native640'][k] for k in GRAPH_COUNTERS) for q in cases)}
   print(json.dumps({'phase':'separate_search_work','filter':t,'attempts':counter['total'],**summary[str(t)]}),flush=True)
 write(args.output/'work-summary.json',summary);require(counter=={'total':WORK_ATTEMPTS,'reference_exact':3150,'ann':15750},'work attempt ledger differs')
 return summary
