"""Synthetic SQL/role-switch/CPU/counter smoke, not benchmark performance evidence."""
import json,os,subprocess
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from psycopg import connect
from psycopg import sql
from common import THRESHOLDS,capture,matches,publish,require,search,sha
from sessions import bind,pin
from startup import start
from design import FAMILIES,ARMS,BLOCKS,role,cpu_for
from experiment import GRAPH_COUNTERS,COUNTERS
PHASE=os.environ['DIAG_PHASE'];POLICIES={p['name']:p for p in json.loads(Path('/qual/eligible-policies.json').read_text())['policies']}
SQL='''CREATE EXTENSION vector;
CREATE TABLE reviews(id bigint,total_votes bigint,embedding vector(8));
INSERT INTO reviews SELECT i,CASE WHEN i<=10000 THEN 1000 WHEN i<=20000 THEN 600 WHEN i<=30000 THEN 400 WHEN i<=40000 THEN 250 WHEN i<=50000 THEN 150 WHEN i<=60000 THEN 50 ELSE 0 END, ARRAY[sin(i::float8),cos(i::float8/3),sin(i::float8/7),cos(i::float8/19),sin(i::float8/11),cos(i::float8/17),sin(i::float8/23),cos(i::float8/29)]::vector FROM generate_series(1,247286) i;
CREATE INDEX reviews_hnsw ON reviews USING hnsw(embedding vector_cosine_ops) WITH(m=32) WHERE id<=16000;
CREATE SCHEMA fannagent;
CREATE FUNCTION fannagent.bind_target(regclass,text,text,regclass) RETURNS oid AS '$libdir/vector','fannagent_bind_target' LANGUAGE C STRICT VOLATILE;
CREATE FUNCTION fannagent.begin_execution(text,text,bigint,text,integer,integer,text,bigint,text,text,text,boolean,bigint) RETURNS text AS '$libdir/vector','fannbench_begin_execution' LANGUAGE C VOLATILE;
CREATE FUNCTION fannagent.complete(text,integer) RETURNS text AS '$libdir/vector','fannbench_last_execution' LANGUAGE C VOLATILE;
CREATE FUNCTION fannagent.take_trace(text) RETURNS text AS '$libdir/vector','fannagent_take_trace' LANGUAGE C STRICT VOLATILE;
'''
def conn():
 c=connect('host=/tmp/socket dbname=postgres user=nobody',autocommit=True);c.execute("SELECT fannagent.bind_target('reviews','id','embedding','reviews_hnsw')");return c

def choose(obs,name,t):
 if name not in POLICIES:return 0
 f='unfiltered' if t<0 else 'votes'+str(t)
 for clause in POLICIES[name]['rules'].get(f,[]):
  o=next((o for o in obs if o['checkpoint']==clause['cp']),None)
  if o is not None and o['qualifying_count']>=10 and all(o.get(k) is not None and (o[k]>=v if op=='>=' else o[k]<=v) for k,op,v in clause['conditions']):return clause['cp']
 return 0

def main():
 require(PHASE in ('timing','work'),'unknown phase');require(sha('/opt/postgresql/lib/vector.so')==sha('/qual/'+PHASE+'-module.so'),'wrong smoke module')
 Path('/tmp/socket').mkdir(mode=0o700);subprocess.run(['/opt/postgresql/bin/initdb','-D','/tmp/pgdata','-A','trust','-U','nobody'],check=True,stdout=subprocess.DEVNULL);Path('/tmp/pg_hba.conf').write_text('local all all trust\n');start(Path('/tmp'))
 results=[]
 try:
  with connect('host=/tmp/socket dbname=postgres user=nobody',autocommit=True) as c:c.execute(SQL+Path('/qual/'+('functions.sql' if PHASE=='timing' else 'work-functions.sql')).read_text())
  with conn() as keeper:
   keeper.execute('BEGIN ISOLATION LEVEL REPEATABLE READ');keeper.execute('LOCK TABLE reviews IN SHARE MODE');args=SimpleNamespace(snapshot=keeper.execute('SELECT pg_export_snapshot()').fetchone()[0]);heap,index=keeper.execute("SELECT 'reviews'::regclass::oid,'reviews_hnsw'::regclass::oid").fetchone();rows=keeper.execute('SELECT ctid::text,total_votes FROM reviews').fetchall();cpus=sorted(os.sched_getaffinity(0));require(len(cpus)==4,'smoke needs four allowed CPUs')
   for ti,t in enumerate(THRESHOLDS):
    meta=publish(Path(f'/tmp/membership-{t}.bin'),heap,index,rows,t);q={'id':str(t),'k':10,'vector':[.3,.1,.8,.4,.9,.2,.6,.5]}
    if t>=0:q['filter']={'field':'totalvotes','op':'gte','value':t}
    with conn() as c,bind(c,args,t,meta['qualifying'],None):native,_=search(c,q,fixture=True)
    proofs={}
    with conn() as c,bind(c,args,t,meta['qualifying'],0):
     cap=capture(c,q,'smoke-cap',fixture=True);require(matches(cap['output'],native),'capture changed output')
     for o in cap['checkpoints']:
      if o['qualifying_count']>=10:proofs[o['checkpoint']]=capture(c,q,'force'+str(o['checkpoint']),budget=o['budget'],fixture=True)['output']
    count_baseline=None;noops_equal=True
    with ExitStack() as stack:
     pool={r:stack.enter_context(conn()) for r in range(20)};pids={r:c.execute('SELECT pg_backend_pid()').fetchone()[0] for r,c in pool.items()};require(len(set(pids.values()))==20,'duplicate backend PID')
     for r,pid in pids.items():pin(pid,cpu_for(r,ti,cpus),cpus)
     visits={r:[] for r in pool}
     for block,(cycle,rotation) in enumerate(BLOCKS):
      for r,c in pool.items():
       name=role(r,rotation);visits[r].append(name)
       with bind(c,args,t,meta['qualifying'],ARMS[name]):
        if PHASE=='work':c.execute('SELECT fannagent.diagnostic_reset()')
        output,_=search(c,q,fixture=True)
        counts=None if PHASE=='timing' else json.loads(c.execute('SELECT fannagent.diagnostic_read()').fetchone()[0]);cp=0 if name=='native640' else c.execute('SELECT fannagent.confirm_last()').fetchone()[0];want=choose(cap['checkpoints'],name,t)
        require(cp==want and matches(output,proofs[want] if want else native),'same-backend role switching changed search')
        require(os.sched_getaffinity(pids[r])=={cpu_for(r,ti,cpus)},'CPU assignment differs')
        if counts is not None:
         require(counts['pid']==pids[r] and counts['start_cpu']==counts['end_cpu']==cpu_for(r,ti,cpus),'actual CPU observation differs: '+json.dumps({'counts':counts,'pid':pids[r],'expected_cpu':cpu_for(r,ti,cpus),'affinity':sorted(os.sched_getaffinity(pids[r]))}));require(counts['vector_calls']>0 and counts['layer0_queue_pops']>0,'zero work counter')
         if name=='native640':require(counts['feature_passes']==counts['membership_probes']==0,'native has feature work');count_baseline=counts
         if name=='noop640' and count_baseline:noops_equal &= all(counts[k]==count_baseline[k] for k in GRAPH_COUNTERS)
     require(all(all(v.count(n)==2 for n in FAMILIES) for v in visits.values()),'not every backend executed each family twice')
    # A low-effort query is returned short, even on the instrumented path.
    with conn() as c,bind(c,args,t,meta['qualifying'],None):
     c.execute('SET LOCAL hnsw.ef_search=2');short,_=search(c,q,fixture=True);require(len(short)<10,'short answer repaired')
    results.append({'threshold':t,'persistent_readers':20,'blocks':10,'all_roles_per_backend':2,'cpu_pinning_and_role_output_parity':True,'short_output_preserved':True,'noop_graph_counters_equal_native':noops_equal if PHASE=='work' else None})
   print('SMOKE_RECEIPT '+json.dumps({'status':'passed','phase':PHASE,'fixture':'synthetic8d partial HNSW graph; not original graph/performance evidence','conditions':results,'exact_serving_calls':0,'separate_module_role':'unchanged timing' if PHASE=='timing' else 'observation-only counters','cpus':cpus}),flush=True)
 finally:subprocess.run(['/opt/postgresql/bin/pg_ctl','-D','/tmp/pgdata','-m','fast','-w','stop'],check=True)
if __name__=='__main__':main()
