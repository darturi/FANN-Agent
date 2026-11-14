"""Offline exact truth, then unguarded quality and paired latency experiments."""
import hashlib,json
from contextlib import ExitStack
from time import perf_counter_ns
from common import THRESHOLDS,capture,matches,require,threshold,write,search
from serving import request
from support import reader,check_plan,valid
SEED='reviews-unguarded-development-v1'
FAMILIES={'native40':(40,None),'native80':(80,None),'native160':(160,None),'native320':(320,None),'native640':(640,None),'noop640':(640,6),'conservative_a':(640,7),'moderate_b_fixed':(640,8),'broad_c_fixed':(640,9)}
POLICIES=('conservative_a','moderate_b_fixed','broad_c_fixed')
LABELS=tuple(n+'-'+ab for n in FAMILIES for ab in ('A','B'))
BASE=(0,1,17,2,16,3,15,4,14,5,13,6,12,7,11,8,10,9)
CAP=160000

def reserve(counter,operation):
 require(counter['total']<CAP,'unguarded development attempt cap');counter['total']+=1;counter[operation]=counter.get(operation,0)+1

def perform(counter,ann,q):return request(ann,q,lambda op:reserve(counter,op))

def validate(result,q,eligible,truth):
 require(set(result)=={'output','returned_count','request_ns','construction_ns','sql_fetch_decode_ns'},'unexpected serving result or fallback field')
 require(result['returned_count']==len(result['output']),'returned count differs')
 require(result['request_ns']==result['construction_ns']+result['sql_fetch_decode_ns'] and result['request_ns']>0 and result['sql_fetch_decode_ns']>0 and result['construction_ns']>=0,'timer accounting')
 return valid(result['output'],q,eligible,truth)

def order_for(j,epoch,ti):
 offset=(j+epoch+ti)%len(LABELS);order=[LABELS[(v+offset)%len(LABELS)] for v in BASE]
 return list(reversed(order)) if epoch else order

def ordered(queries,t,epoch):
 cases=sorted((q for q in queries if threshold(q)==t),key=lambda q:hashlib.sha256((SEED+':'+q['id'].rsplit('-',1)[0]).encode()).hexdigest())
 return list(reversed(cases)) if epoch else cases

def result_only(record):return {k:record[k] for k in ('output','returned_count','request_ns','construction_ns','sql_fetch_decode_ns')}

def run(Backend,args,queries,eligible,prior,expected,counter):
 cache={};truths={};setup=[];quality={};reference_elapsed=0
 # All exact references finish and their connections close before ANN qualification/timing.
 with (args.output/'exact-reference.jsonl').open('x') as out:
  for t in THRESHOLDS:
   cases=[q for q in queries if threshold(q)==t];start=perf_counter_ns()
   with reader(Backend,args,t,len(eligible[t]),exact=True) as exact:
    write(args.output/f'exact-plan-{t}.json',check_plan(exact,cases[0],exact=True))
    for q in cases:
     reserve(counter,'reference_exact');truth,ns=search(exact,q,exact=True);require(matches(truth,prior[q['id']]['exact']),'offline exact truth changed');truths[q['id']]=truth;reference_elapsed+=ns
     out.write(json.dumps({'id':q['id'],'filter':t,'output':truth,'reference_query_ns':ns},allow_nan=False)+'\n')
   out.flush();print(json.dumps({'phase':'offline_exact_reference','filter':t,'attempts':counter['total']}),flush=True)
   setup.append({'phase':'offline_reference','filter':t,'total_ns':perf_counter_ns()-start})
 with (args.output/'quality.jsonl').open('x') as out:
  for t in THRESHOLDS:
   cases=[q for q in queries if threshold(q)==t];passing=len(eligible[t]);started=perf_counter_ns()
   with ExitStack() as stack:
    shadow=stack.enter_context(reader(Backend,args,t,passing,0));readers={name:stack.enter_context(reader(Backend,args,t,passing,arm,ef=ef)) for name,(ef,arm) in FAMILIES.items()}
    setup.append({'phase':'quality','filter':t,'connections':10,'open_attach_ns':perf_counter_ns()-started})
    write(args.output/f'plans-{t}.json',{name:check_plan(c,cases[0]) for name,c in readers.items()})
    for name,c in readers.items():require(c.execute("SELECT current_setting('hnsw.ef_search'),current_setting('hnsw.iterative_scan')").fetchone()==(str(FAMILIES[name][0]),'off'),'ANN settings differ')
    for j,q in enumerate(cases):
     qid=q['id'];truth=truths[qid];reserve(counter,'capture');cap=capture(shadow,q,f'unguarded-capture-{t}-{j}');require(matches(cap['output'],expected[qid]['results']['native640']['output']),'capture native changed')
     actual=cap['checkpoints'];want=expected[qid]['checkpoints'];require(len(actual)==len(want),'checkpoint coverage changed')
     for a,b in zip(actual,want,strict=True):require({k:v for k,v in a.items() if k!='collection_ns'}=={k:v for k,v in b.items() if k!='collection_ns'},'live feature parity differs')
     results={}
     for name,c in readers.items():
      result=perform(counter,c,q);cp=0 if FAMILIES[name][1] is None else c.execute('SELECT fannagent.confirm_last()').fetchone()[0]
      score=validate(result,q,eligible[t],truth)
      if name in expected[qid]['results']:
       target=expected[qid]['results'][name];require(cp==target['checkpoint'] and matches(result['output'],target['output']) and abs(score-target['recall'])<1e-12,'saved raw output/first-stop/recall parity differs')
      if cp:require(result['returned_count']==10,'policy stopped without ten eligible candidates')
      results[name]={'checkpoint':cp,'recall':score,**result};cache[qid,name]=results[name]
     require(matches(results['native640']['output'],results['noop640']['output']),'always-continue changed native')
     # Recall loss is a scientific outcome, not an exception that discards timing evidence.
     out.write(json.dumps({'id':qid,'filter':t,'checkpoints':actual,'results':results},allow_nan=False)+'\n');out.flush()
    closing=perf_counter_ns()
   setup[-1]['close_ns']=perf_counter_ns()-closing
   quality[str(t)]={name:{'queries':450,'mean_recall':sum(cache[q['id'],name]['recall'] for q in cases)/450,'short_outputs':sum(cache[q['id'],name]['returned_count']<min(10,passing) for q in cases),'recall_losses_to_native640':sum(cache[q['id'],name]['recall']<cache[q['id'],'native640']['recall']-1e-12 for q in cases),'stops':sum(cache[q['id'],name]['checkpoint']>0 for q in cases)} for name in FAMILIES}
   print(json.dumps({'phase':'unguarded_quality','filter':t,'queries':450,'attempts':counter['total']}),flush=True)
 with (args.output/'timing.jsonl').open('x') as out,(args.output/'warmup.jsonl').open('x') as warm:
  for epoch in (0,1):
   filters=list(THRESHOLDS);filters=filters[epoch:]+filters[:epoch]
   for t in filters:
    ti=THRESHOLDS.index(t);cases=ordered(queries,t,epoch);passing=len(eligible[t]);start=perf_counter_ns()
    with ExitStack() as stack:
     readers={label:stack.enter_context(reader(Backend,args,t,passing,FAMILIES[label.rsplit('-',1)[0]][1],ef=FAMILIES[label.rsplit('-',1)[0]][0])) for label in LABELS};opened=perf_counter_ns()
     for label,c in readers.items():
      name=label.rsplit('-',1)[0]
      for q in cases[:10]:
       r=perform(counter,c,q);require(matches(r['output'],cache[q['id'],name]['output']),'warmup output differs');warm.write(json.dumps({'id':q['id'],'filter':t,'epoch':epoch,'label':label,**r},allow_nan=False)+'\n')
     warm.flush();warmed=perf_counter_ns();setup.append({'phase':'timing','filter':t,'epoch':epoch,'connections':18,'open_attach_ns':opened-start,'warmup_ns':warmed-opened,'warmup_requests':180})
     for j,q in enumerate(cases):
      order=order_for(j,epoch,ti)
      for pos,label in enumerate(order):
       name=label.rsplit('-',1)[0];r=perform(counter,readers[label],q);require(matches(r['output'],cache[q['id'],name]['output']),'timed output differs')
       out.write(json.dumps({'id':q['id'],'filter':t,'epoch':epoch,'label':label,'position':pos,'predecessor':order[pos-1] if pos else None,'order':order,**r},allow_nan=False)+'\n')
     out.flush();closing=perf_counter_ns()
    setup[-1]['close_ns']=perf_counter_ns()-closing
    print(json.dumps({'phase':'unguarded_timing','epoch':epoch,'filter':t,'attempts':counter['total']}),flush=True)
 write(args.output/'quality-summary.json',quality);write(args.output/'setup.json',setup);write(args.output/'offline-reference-cost.json',{'queries':3150,'query_ns':reference_elapsed,'included_in_serving_endpoint':False,'all_exact_connections_closed_before_approximate_quality_and_timing':True})
 require(counter=={'total':150570,'reference_exact':3150,'capture':3150,'ann':144270},'attempt ledger differs from fixed design')
 return quality
