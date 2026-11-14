"""Provider-free original-graph qualification of frozen development groups only."""
import argparse,json,os,sys,re
from contextlib import contextmanager,ExitStack
from pathlib import Path
from time import perf_counter_ns,monotonic
from common import THRESHOLDS,CHECKPOINTS,capture,matches,publish,require,search,sha,statement,threshold,write
HERE=Path(__file__).resolve().parent
PACKAGE_SHA='b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc'
IMAGE='7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a'
@contextmanager
def reader(Backend,args,t,passing,arm=None,local=False,exact=False):
 b=Backend(args.bundle,args.work);b.state['source_manifest']['settings']['hnsw.ef_search']='640'
 try:
  c=b._connect()
  with c.transaction():
   c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
   c.execute('SET LOCAL max_parallel_workers_per_gather=0')
   if exact:
    c.execute('SET LOCAL enable_seqscan=on');c.execute('SET LOCAL enable_indexscan=off');c.execute('SET LOCAL enable_indexonlyscan=off');c.execute('SET LOCAL enable_bitmapscan=off')
   elif local:c.execute("SELECT fannagent.study_local_bind('reviews',%s,%s)",(t,passing))
   elif arm is not None:c.execute("SELECT fannagent.study_attach('reviews','reviews_hnsw',%s,%s,%s)",(t,arm,passing))
   yield c
 finally:b.close()
def count_search(counter,operation,fn,*a,**kw):
 require(counter['total']<40000,'qualification search cap');counter['total']+=1;counter[operation]=counter.get(operation,0)+1;return fn(*a,**kw)
def valid(out,q,eligible,truth):
 require(len(out)<=min(10,len(eligible)) and len({i for i,_ in out})==len(out),'invalid/incomplete results')
 require(all(i in eligible and -1e-6<=d<=2+1e-6 for i,d in out),'ineligible/nonfinite cosine results')
 boundary=max((d for _,d in truth),default=0);return sum(d<=boundary+1e-6 for _,d in out)/max(1,min(10,len(eligible)))
def check_plan(c,q,exact=False):
 s,p=statement(q,exact=exact);plan=c.execute('EXPLAIN (FORMAT JSON) '+s,p,prepare=False).fetchone()[0][0]['Plan'];nodes=[]
 def visit(n):
  if 'Scan' in n['Node Type']:nodes.append(n)
  for x in n.get('Plans',[]):visit(x)
 visit(plan);require(len(nodes)==1 and nodes[0].get('Relation Name')=='reviews','unexpected scan relation')
 require(nodes[0]['Node Type']=='Seq Scan' if exact else nodes[0].get('Index Name')=='reviews_hnsw','wrong execution path')
 return plan
def main():
 p=argparse.ArgumentParser()
 for n in ('package','bundle','prepared','work','output'):p.add_argument('--'+n,type=Path,required=True)
 args=p.parse_args();sys.path.insert(0,str(args.package))
 from rb_native import load_stage,watchdog,resource_limits,memory_events,BASE_MANIFEST,RUNNER
 require(os.uname().machine=='x86_64' and os.environ.get('SLURM_JOB_ID','').isdigit(),'requires x86_64 Slurm job')
 binding=json.loads((HERE/'binding.json').read_text());require(sha(HERE/'queries.jsonl')==binding['queries_sha256'],'development inputs changed')
 require(sha(HERE/'vector.so')==binding['module_sha256'] and sha('/opt/postgresql/lib/vector.so')==binding['module_sha256'],'module changed')
 require(sha(args.bundle/'images/runtime.sif')==IMAGE,'runtime image changed')
 queries=[json.loads(l) for l in (HERE/'queries.jsonl').read_text().splitlines()]
 require(len(queries)==3150 and len({q['id'] for q in queries})==3150,'query coverage changed')
 groups={int(re.fullmatch(r'reviews-clean-v(\d+)-(?:unfiltered|votes\d+)',q['id']).group(1)) for q in queries}
 require(groups==set(binding['development_source_indices']),'non-development query input')
 require(all(len(q['vector'])==768 for q in queries),'dimension changed')
 stage=load_stage(args.package,PACKAGE_SHA)
 require(sha(args.bundle/'manifest.json')==BASE_MANIFEST,'base bundle manifest changed')
 base=json.loads((args.bundle/'manifest.json').read_text())['files']
 for name in ('images/runtime.sif','inputs/reviews.parquet','inputs/local-identity.json','experiment.json'):
  require(sha(args.bundle/name)==base[name],'base input changed: '+name)
 require(sha('/opt/torch-reviews/runner.py')==RUNNER,'retained runner changed')
 ready=json.loads((args.prepared/'READY.json').read_text())
 require(ready['architecture']=='x86_64' and ready['image_sha256']==IMAGE and json.loads((args.prepared/'database-identity.json').read_text())==stage.index,'prepared restore identity changed')
 for folder in (args.package,args.bundle,args.prepared,HERE):require(os.statvfs(folder).f_flag&os.ST_RDONLY,'input mount must be read-only')
 runner,Backend=stage.frozen.execution.load_backend(stage.source)
 for d in (args.work,args.output):require(d.is_dir() and not any(d.iterdir()) and not d.stat().st_mode&0o077,'require new private empty work/output')
 (args.work/'socket').mkdir(mode=0o700);(args.work/'.torch-owned').write_text(os.environ['SLURM_JOB_ID']+'\n')
 import rb_native
 rb_native.MEMORY_BYTES=48*1024**3  # This new qualification's explicit resource contract.
 limits,mg=resource_limits();events_before=memory_events(mg);counter={'total':0};maps=[];summary={};started=monotonic()
 from psycopg import connect
 from psycopg.conninfo import make_conninfo
 with watchdog(10200):
  try:
   identity=stage.frozen.restore(stage.source,args.bundle,args.prepared,args.work,runner,extra_sql=(HERE/'functions.sql').read_text());require(identity==stage.index,'graph identity changed')
   dsn=make_conninfo(runner.job_connection(args.work,admin=True),dbname='torch_reviews')
   with connect(dsn,autocommit=True) as keeper,keeper.transaction():
    keeper.execute('SET LOCAL idle_in_transaction_session_timeout=0');keeper.execute('LOCK TABLE public.reviews IN SHARE MODE NOWAIT')
    columns=keeper.execute("SELECT a.attname,format_type(a.atttypid,a.atttypmod) FROM pg_attribute a WHERE a.attrelid='public.reviews'::regclass AND a.attnum>0 AND NOT a.attisdropped").fetchall();require(('total_votes','bigint') in columns,'metadata schema mismatch')
    heap,index=keeper.execute("SELECT 'public.reviews'::regclass::oid,'public.reviews_hnsw'::regclass::oid").fetchone()
    metadata=keeper.execute('SELECT ctid::text,total_votes FROM ONLY public.reviews').fetchall();source=keeper.execute('SELECT id,total_votes FROM ONLY public.reviews').fetchall();require(len(source)==247286 and len({i for i,_ in source})==247286,'source ID mapping mismatch')
    for t in THRESHOLDS:
     start=perf_counter_ns();meta=publish(args.work/f'membership-{t}.bin',heap,index,metadata,t);meta['build_ns']=perf_counter_ns()-start;maps.append(meta)
    del metadata
    write(args.output/'eligibility.json',{str(t):sorted(i for i,v in source if t<0 or v is not None and v>=t) for t in THRESHOLDS})
    for t in THRESHOLDS:
     cases=[q for q in queries if threshold(q)==t];require(len(cases)==450,'filter group count differs')
     eligible={i for i,v in source if t<0 or v is not None and v>=t};passing=len(eligible);require(passing==next(m['qualifying'] for m in maps if m['threshold']==t),'eligibility mismatch')
     stats={'queries':0,'native_incomplete':0,'native_mean_recall':0.,'checkpoints':{str(cp):0 for cp in CHECKPOINTS},'forced_checks':0,'local_shared_checks':0,'no_stop_parity':0}
     with reader(Backend,args,t,passing,exact=True) as exact,reader(Backend,args,t,passing) as native,reader(Backend,args,t,passing,0) as shadow,reader(Backend,args,t,passing,local=True) as local,ExitStack() as live_stack:
      live_readers={arm:live_stack.enter_context(reader(Backend,args,t,passing,arm)) for arm in (1,2,3,4,5,6)}
      plans={'exact':check_plan(exact,cases[0],True),'native':check_plan(native,cases[0])}
      with (args.output/f'qualification-{t}.jsonl').open('x') as out:
       for j,q in enumerate(cases):
        truth,exact_ns=count_search(counter,'exact',search,exact,q,exact=True);nat,native_ns=count_search(counter,'native',search,native,q)
        cap=count_search(counter,'capture',capture,shadow,q,f'capture-{t}-{j}');require(matches(cap['output'],nat),'shared capture changed native output')
        if j<10:
         lc=count_search(counter,'local_control',capture,local,q,f'local-{t}-{j}');require(matches(lc['output'],nat),'local capture changed native')
         for a,b in zip(lc['checkpoints'],cap['checkpoints'],strict=True):require({k:v for k,v in a.items() if k!='collection_ns'}=={k:v for k,v in b.items() if k!='collection_ns'},'local/shared features differ')
         stats['local_shared_checks']+=1
        proofs={}
        for obs in cap['checkpoints']:
         cp=obs['checkpoint'];stats['checkpoints'][str(cp)]+=1
         if obs['qualifying_count']<10:continue
         forced=count_search(counter,'forced_trace',capture,shadow,q,f'forced-{t}-{j}-{cp}',budget=obs['budget'])
         expected=[e for k,e in sorted(cap['states'].items()) if k<=cp];actual=[e for k,e in sorted(forced['states'].items()) if k<=cp]
         require([(e['index'],e['features']) for e in actual]==[(e['index'],e['features']) for e in expected],'forced traversal prefix changed')
         require(len(forced['output'])==10 and abs(max(d for _,d in forced['output'])-obs['tenth_distance'])<=1e-6,'forced output differs from checkpoint')
         proofs[str(cp)]={'output':forced['output'],'recall':valid(forced['output'],q,eligible,truth),'budget':obs['budget']};stats['forced_checks']+=1
        # Live continuation and stop arms use independently attached persistent readers.
        live={}
        for arm in (1,2,3,4,5,6):
         c=live_readers[arm]
         result,ns=count_search(counter,'live',search,c,q);cp=c.execute('SELECT fannagent.confirm_last()').fetchone()[0]
         if arm==6:require(cp==0 and matches(result,nat),'no-stop continuation changed native output');stats['no_stop_parity']+=int(arm==6)
         if arm in (3,4,5):
          target=CHECKPOINTS[arm-3];proof=proofs.get(str(target));require(cp==(target if proof else 0),'unexpected forced stop checkpoint')
          require(matches(result,proof['output'] if proof else nat),'live/forced output differs')
         if arm in (1,2):
          chosen=next((o['checkpoint'] for o in cap['checkpoints'] if o['qualifying_count']>=10 and o['frontier_gap'] is not None and ((arm==1 and o['checkpoint']==32 and o['frontier_gap']>=.05) or (arm==2 and ((o['checkpoint']==16 and o['frontier_gap']>=.02 and o['tenth_distance']<=.44) or (o['checkpoint']==32 and o['frontier_gap']>=.025 and o['tenth_distance']<=.38) or (o['checkpoint']==64 and o['frontier_gap']>=.05))))),0)
          require(cp==chosen and matches(result,proofs[str(chosen)]['output'] if chosen else nat),'historical rule replay differs')
         live[str(arm)]={'checkpoint':cp,'output':result,'request_ns':ns,'complete':len(result)==min(10,passing),'recall':valid(result,q,eligible,truth)}
        recall=valid(nat,q,eligible,truth);stats['native_mean_recall']+=recall;stats['queries']+=1;stats['native_incomplete']+=int(len(nat)!=min(10,passing))
        out.write(json.dumps({'id':q['id'],'threshold':t,'exact':truth,'exact_ns':exact_ns,'native':nat,'native_ns':native_ns,'native_recall':recall,'native_complete':len(nat)==min(10,passing),'checkpoints':cap['checkpoints'],'capture_request_ns':cap['request_ns'],'forced':proofs,'live':live},allow_nan=False)+'\n');out.flush()
        if j%50==0:print(json.dumps({'filter':t,'completed':j+1,'searches':counter['total']}),flush=True)
     stats['native_mean_recall']/=450;summary[str(t)]=stats;write(args.output/f'plans-{t}.json',plans)
    stage.frozen.verify_import(runner,args.bundle,args.work)
  finally:
   stage.frozen.stop(args.work)
   for t in THRESHOLDS:(args.work/f'membership-{t}.bin').unlink(missing_ok=True)
  stage.frozen.verify_index(args.work,stage.index)
 require(memory_events(mg)==events_before,'memory limit event')
 require(all(s['queries']==450 and s['no_stop_parity']==450 and s['local_shared_checks']==10 for s in summary.values()),'incomplete qualification')
 write(args.output/'receipt.json',{'status':'runtime_qualified','job':os.environ['SLURM_JOB_ID'],'split_sha256':binding['split_manifest_sha256'],'protocol_sha256':binding['protocol_sha256'],'module_sha256':binding['module_sha256'],'graph':stage.index,'groups':450,'queries':3150,'provider_calls':0,'validation_queries':0,'test_queries':0,'searches':counter,'summary':summary,'lookup_maps':maps,'limits':limits,'machine':{'hostname':os.uname().nodename,'architecture':os.uname().machine,'cpu_model':[line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')][:1]},'elapsed_seconds':monotonic()-started,'data_index_before_after':True,'raw_sha256':{p.name:sha(p) for p in args.output.iterdir() if p.is_file()}})
 print('DEVELOPMENT_RUNTIME_QUALIFICATION_PASSED',flush=True)
if __name__=='__main__':main()
