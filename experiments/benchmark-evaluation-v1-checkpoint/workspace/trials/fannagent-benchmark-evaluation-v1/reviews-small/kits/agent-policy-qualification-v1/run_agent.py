"""Sealed provider-free development common-guard experiment."""
import argparse,json,os,sys,re
from pathlib import Path
from time import monotonic,perf_counter_ns
from common import THRESHOLDS,require,publish,sha,write
from experiment import run
HERE=Path(__file__).resolve().parent
PACKAGE_SHA='b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc'
IMAGE='7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a'
def main():
 p=argparse.ArgumentParser()
 for n in ('package','bundle','prepared','work','output'):p.add_argument('--'+n,type=Path,required=True)
 args=p.parse_args();sys.path.insert(0,str(args.package))
 from rb_native import load_stage,watchdog,resource_limits,memory_events,BASE_MANIFEST,RUNNER
 require(os.uname().machine=='x86_64' and os.environ.get('SLURM_JOB_ID','').isdigit(),'requires x86_64 Slurm job')
 binding=json.loads((HERE/'binding.json').read_text());require(sha(HERE/'queries.jsonl')==binding['queries_sha256'],'development inputs changed')
 require(sha(HERE/'vector.so')==binding['module_sha256'] and sha('/opt/postgresql/lib/vector.so')==binding['module_sha256'],'module changed')
 require(sha(args.bundle/'images/runtime.sif')==IMAGE,'runtime image changed')
 require(sha(HERE/'agent-plan.json')==binding['agent_plan_sha256'],'agent plan changed')
 require(sha(HERE/'compiled-policies.json')==binding['compiled_policies_sha256'],'compiled policies changed')
 require(sha(HERE/'guard.py')==binding['guard_source_sha256'],'shared guard changed')
 plan=json.loads((HERE/'agent-plan.json').read_text());require(plan['parent_ef_search']==640 and plan['query_attempt_cap']==160000,'agent design changed');args.parent_ef=640
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
 with watchdog(28200):
  try:
   identity=stage.frozen.restore(stage.source,args.bundle,args.prepared,args.work,runner,extra_sql=(HERE/'functions.sql').read_text());require(identity==stage.index,'graph identity changed')
   dsn=make_conninfo(runner.job_connection(args.work,admin=True),dbname='torch_reviews')
   with connect(dsn,autocommit=True) as keeper,keeper.transaction():
    keeper.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
    keeper.execute('SET LOCAL idle_in_transaction_session_timeout=0');keeper.execute('LOCK TABLE public.reviews IN SHARE MODE NOWAIT')
    args.snapshot=keeper.execute('SELECT pg_export_snapshot()').fetchone()[0]
    columns=keeper.execute("SELECT a.attname,format_type(a.atttypid,a.atttypmod) FROM pg_attribute a WHERE a.attrelid='public.reviews'::regclass AND a.attnum>0 AND NOT a.attisdropped").fetchall();require(('total_votes','bigint') in columns,'metadata schema mismatch')
    heap,index=keeper.execute("SELECT 'public.reviews'::regclass::oid,'public.reviews_hnsw'::regclass::oid").fetchone()
    metadata=keeper.execute('SELECT ctid::text,total_votes FROM ONLY public.reviews').fetchall();source=keeper.execute('SELECT id,total_votes FROM ONLY public.reviews').fetchall();require(len(source)==247286 and len({i for i,_ in source})==247286,'source ID mapping mismatch')
    for t in THRESHOLDS:
     start=perf_counter_ns();meta=publish(args.work/f'membership-{t}.bin',heap,index,metadata,t);meta['build_ns']=perf_counter_ns()-start;maps.append(meta)
    write(args.output/'membership-setup.json',maps)
    del metadata
    write(args.output/'eligibility.json',{str(t):sorted(i for i,v in source if t<0 or v is not None and v>=t) for t in THRESHOLDS})
    prior_rows=[json.loads(line) for line in (HERE/'prior-references.jsonl').read_text().splitlines()]
    require(sha(HERE/'prior-references.jsonl')==binding['prior_references_sha256'],'prior references changed')
    prior={row['id']:row for row in prior_rows};require(set(prior)=={q['id'] for q in queries},'prior query coverage differs')
    require(sha(HERE/'expected.jsonl')==binding['expected_sha256'],'expected outcomes changed')
    expected={r['id']:r for r in (json.loads(line) for line in (HERE/'expected.jsonl').read_text().splitlines())}
    require(set(expected)==set(prior),'expected development coverage changed')
    eligible={t:{i for i,v in source if t<0 or v is not None and v>=t} for t in THRESHOLDS}
    summary=run(Backend,args,queries,eligible,prior,expected,counter)
    stage.frozen.verify_import(runner,args.bundle,args.work)
  finally:
   stage.frozen.stop(args.work)
   for t in THRESHOLDS:(args.work/f'membership-{t}.bin').unlink(missing_ok=True)
   stage.frozen.verify_index(args.work,stage.index)
 require(memory_events(mg)==events_before,'memory limit event')
 require(len(summary)==7 and all(len(v)==4 and all(x['queries']==450 for x in v.values()) for v in summary.values()),'incomplete selected qualification')
 receipt={'status':'three_agent_policies_qualified_and_development_timed','job_id':os.environ['SLURM_JOB_ID'],'selected_parent_ef_search':640,'split_sha256':binding['split_manifest_sha256'],'module_sha256':binding['module_sha256'],'agent_plan_sha256':binding['agent_plan_sha256'],'compiled_policies_sha256':binding['compiled_policies_sha256'],'guard_source_sha256':binding['guard_source_sha256'],'provider_calls':0,'validation_test_queries':0,'groups':450,'requests':3150,'policies':3,'timed_requests':50400,'graph':stage.index,'searches':counter,'selected_qualification':summary,'limits':limits,'exported_snapshot_shared':True,'data_index_before_after':True,'cleanup_verified':True,'elapsed_seconds':monotonic()-started,'machine':{'hostname':os.uname().nodename,'architecture':os.uname().machine,'cpu_model':[l.split(':',1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')][:1]},'raw_sha256':{p.name:sha(p) for p in args.output.iterdir() if p.is_file()}}
 write(args.output/'receipt.json',receipt)
 print('THREE_AGENT_POLICY_QUALIFICATION_AND_TIMING_PASSED',flush=True)
if __name__=='__main__':main()
