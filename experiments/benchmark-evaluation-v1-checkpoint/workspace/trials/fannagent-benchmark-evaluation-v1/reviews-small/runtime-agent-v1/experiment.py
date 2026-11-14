"""Frozen three-program development qualification and eight-reader paired timings."""
import hashlib,json
from contextlib import ExitStack
from time import perf_counter_ns
from common import THRESHOLDS,capture,matches,require,sha,threshold,write,search
from guard import guarded_request,fallback_statement
from support import reader,check_plan,valid
SEED='reviews-agent-three-development-v1'
LABELS=('native-A','native-B','conservative_a-A','conservative_a-B','moderate_b_fixed-A','moderate_b_fixed-B','broad_c_fixed-A','broad_c_fixed-B')
ARMS={'native':None,'conservative_a':7,'moderate_b_fixed':8,'broad_c_fixed':9}
BASE=(0,1,7,2,6,3,5,4)
def exact_plan(c,q):
 sql,params=fallback_statement(q);plan=c.execute('EXPLAIN (FORMAT JSON) '+sql,params,prepare=False).fetchone()[0][0]['Plan'];scans=[]
 def visit(n):
  if 'Scan' in n['Node Type']:scans.append(n)
  for child in n.get('Plans',[]):visit(child)
 visit(plan);require(len(scans)==1 and scans[0]['Node Type']=='Seq Scan' and scans[0]['Relation Name']=='reviews','completion must use exact sequential scan')
 return plan

def reserve(counter,operation):
 require(counter['total']<160000,'agent development attempt cap');counter['total']+=1;counter[operation]=counter.get(operation,0)+1
def perform(counter,ann,exact,q,passing):return guarded_request(ann,exact,q,passing,lambda op:reserve(counter,op))
def validate(result,q,eligible,truth):
 require(result['required_count']==10 and len(result['output'])==10,'incomplete output')
 require(result['initial_count']==len(result['initial']) and result['fallback_used']==(len(result['initial'])<10),'wrong guard decision')
 valid(result['initial'],q,eligible,truth);score=valid(result['output'],q,eligible,truth)
 if result['fallback_used']:
  require(score==1 and all(i in dict(truth) and abs(d-dict(truth)[i])<=1e-6 for i,d in result['output']),'exact completion differs')
 else:require(matches(result['initial'],result['output']),'nonfallback changed identity')
 require(result['request_ns']==result['ann_ns']+result['fallback_ns']+result['guard_and_construction_ns'] and min(result['request_ns'],result['ann_ns'])>0 and min(result['fallback_ns'],result['guard_and_construction_ns'])>=0,'timer accounting')
 if not result['fallback_used']:require(result['fallback_ns']==0,'unexpected fallback time')
 return score

def order_for(j,epoch,ti):
 offset=(j+epoch+ti)%8;order=[LABELS[(v+offset)%8] for v in BASE]
 return list(reversed(order)) if epoch else order

def ordered(queries,t,epoch):
 cases=sorted((q for q in queries if threshold(q)==t),key=lambda q:hashlib.sha256((SEED+':'+q['id'].rsplit('-',1)[0]).encode()).hexdigest())
 return list(reversed(cases)) if epoch else cases

def run(Backend,args,queries,eligible,prior,expected,counter):
 cache={};setup=[];quality={}
 with (args.output/'quality.jsonl').open('x') as out:
  for t in THRESHOLDS:
   cases=[q for q in queries if threshold(q)==t];passing=len(eligible[t]);started=perf_counter_ns()
   with ExitStack() as stack:
    exact=stack.enter_context(reader(Backend,args,t,passing,exact=True));shadow=stack.enter_context(reader(Backend,args,t,passing,0))
    readers={name:stack.enter_context(reader(Backend,args,t,passing,arm)) for name,arm in ARMS.items()}
    setup.append({'phase':'quality','filter':t,'connections':6,'open_attach_ns':perf_counter_ns()-started})
    write(args.output/f'plans-{t}.json',{'ann':{name:check_plan(c,cases[0]) for name,c in readers.items()},'completion_exact':exact_plan(exact,cases[0])})
    for c in readers.values():require(c.execute("SELECT current_setting('hnsw.ef_search'),current_setting('hnsw.iterative_scan')").fetchone()==('640','off'),'parent settings differ')
    for j,q in enumerate(cases):
     qid=q['id'];reserve(counter,'reference_exact');truth,_=search(exact,q,exact=True);require(matches(truth,prior[qid]['exact']),'fresh exact truth changed')
     reserve(counter,'capture');cap=capture(shadow,q,f'agent-capture-{t}-{j}');require(matches(cap['output'],expected[qid]['native']['initial']),'capture native identity changed')
     want=expected[qid]['checkpoints'];actual=cap['checkpoints'];require(len(want)==len(actual),'checkpoint coverage changed')
     for a,b in zip(actual,want,strict=True):
      require({k:v for k,v in a.items() if k!='collection_ns'}=={k:v for k,v in b.items() if k!='collection_ns'},'live causal feature parity differs')
     results={}
     for name,c in readers.items():
      result=perform(counter,c,exact,q,passing);cp=0 if name=='native' else c.execute('SELECT fannagent.confirm_last()').fetchone()[0]
      target=expected[qid][name];require(cp==target['checkpoint'] and matches(result['initial'],target['initial']) and matches(result['output'],target['output']) and result['fallback_used']==target['fallback_used'],'compiled first-stop/guard/output parity differs')
      score=validate(result,q,eligible[t],truth);require(abs(score-target['recall'])<1e-12,'recall differs from frozen replay')
      if cp:require(not result['fallback_used'],'stop unexpectedly required completion')
      results[name]={'checkpoint':cp,'recall':score,**result};cache[qid,name]=results[name]
     require(all(r['recall']>=results['native']['recall']-1e-12 for r in results.values()),'candidate recall loss')
     out.write(json.dumps({'id':qid,'filter':t,'checkpoints':actual,'exact':truth,'results':results},allow_nan=False)+'\n');out.flush()
    closing=perf_counter_ns()
   setup[-1]['close_ns']=perf_counter_ns()-closing
   quality[str(t)]={name:{'queries':450,'mean_recall':sum(cache[q['id'],name]['recall'] for q in cases)/450,'stops':sum(cache[q['id'],name]['checkpoint']>0 for q in cases),'fallbacks':sum(cache[q['id'],name]['fallback_used'] for q in cases)} for name in ARMS}
   require(all(x['mean_recall']>=.95 for x in quality[str(t)].values()),'recall floor failed')
   print(json.dumps({'phase':'agent_quality','filter':t,'complete':450,'attempts':counter['total']}),flush=True)
 with (args.output/'timing.jsonl').open('x') as out,(args.output/'warmup.jsonl').open('x') as warm:
  for epoch in (0,1):
   filters=list(THRESHOLDS);filters=filters[epoch:]+filters[:epoch]
   for t in filters:
    ti=THRESHOLDS.index(t);cases=ordered(queries,t,epoch);passing=len(eligible[t]);start=perf_counter_ns()
    with ExitStack() as stack:
     exact=stack.enter_context(reader(Backend,args,t,passing,exact=True))
     readers={label:stack.enter_context(reader(Backend,args,t,passing,ARMS[label.rsplit('-',1)[0]])) for label in LABELS};opened=perf_counter_ns()
     for label,c in readers.items():
      name=label.rsplit('-',1)[0]
      for q in cases[:10]:
       r=perform(counter,c,exact,q,passing);e=cache[q['id'],name];require(matches(r['initial'],e['initial']) and matches(r['output'],e['output']) and r['fallback_used']==e['fallback_used'],'warmup differs')
       warm.write(json.dumps({'id':q['id'],'filter':t,'epoch':epoch,'label':label,**r},allow_nan=False)+'\n')
     warm.flush();warmed=perf_counter_ns();setup.append({'phase':'timing','filter':t,'epoch':epoch,'connections':9,'open_attach_ns':opened-start,'warmup_ns':warmed-opened,'warmup_requests':80})
     for j,q in enumerate(cases):
      order=order_for(j,epoch,ti)
      for position,label in enumerate(order):
       name=label.rsplit('-',1)[0];r=perform(counter,readers[label],exact,q,passing);e=cache[q['id'],name]
       require(matches(r['initial'],e['initial']) and matches(r['output'],e['output']) and r['fallback_used']==e['fallback_used'],'timed identity/guard differs')
       out.write(json.dumps({'id':q['id'],'filter':t,'epoch':epoch,'label':label,'order':order,'position':position,'predecessor':order[position-1] if position else None,**r},allow_nan=False)+'\n')
     out.flush();closing=perf_counter_ns()
    setup[-1]['close_ns']=perf_counter_ns()-closing
    print(json.dumps({'phase':'agent_timing','epoch':epoch,'filter':t,'attempts':counter['total']}),flush=True)
 write(args.output/'quality-summary.json',quality);write(args.output/'setup.json',setup)
 return quality
