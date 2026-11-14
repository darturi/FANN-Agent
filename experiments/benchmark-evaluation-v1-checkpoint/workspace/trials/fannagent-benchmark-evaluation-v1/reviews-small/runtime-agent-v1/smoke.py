"""Native PostgreSQL smoke on a synthetic fixture; not original-graph qualification."""
import json,os,subprocess
from pathlib import Path
from psycopg import connect
from guard import guarded_request
from psycopg import sql
from common import THRESHOLDS,capture,matches,publish,require,search,threshold
POLICIES=json.loads(Path('/qual/eligible-policies.json').read_text())['policies']
def expected(cp_rows,policy,t):
 f='unfiltered' if t<0 else 'votes'+str(t)
 for clause in policy['rules'].get(f,[]):
  o=next((o for o in cp_rows if o['checkpoint']==clause['cp']),None)
  if o is not None and o['qualifying_count']>=10 and all(o.get(k) is not None and (o[k]>=v if op=='>=' else o[k]<=v) for k,op,v in clause['conditions']):return clause['cp']
 return 0
SQL='''CREATE EXTENSION vector;
CREATE TABLE reviews(id bigint,total_votes bigint,embedding vector(8));
INSERT INTO reviews SELECT i,CASE WHEN i<=10000 THEN 1000 WHEN i<=20000 THEN 600 WHEN i<=30000 THEN 400 WHEN i<=40000 THEN 250 WHEN i<=50000 THEN 150 WHEN i<=60000 THEN 50 ELSE 0 END, ARRAY[sin(i::float8),cos(i::float8/3),sin(i::float8/7),cos(i::float8/19),sin(i::float8/11),cos(i::float8/17),sin(i::float8/23),cos(i::float8/29)]::vector FROM generate_series(1,247286) i;
CREATE INDEX reviews_fixture_graph ON reviews USING hnsw(embedding vector_cosine_ops) WITH(m=32) WHERE id<=16000;
CREATE SCHEMA fannagent;
CREATE FUNCTION fannagent.bind_target(regclass,text,text,regclass) RETURNS oid AS '$libdir/vector','fannagent_bind_target' LANGUAGE C STRICT VOLATILE;
CREATE FUNCTION fannagent.begin_execution(text,text,bigint,text,integer,integer,text,bigint,text,text,text,boolean,bigint) RETURNS text AS '$libdir/vector','fannbench_begin_execution' LANGUAGE C VOLATILE;
CREATE FUNCTION fannagent.complete(text,integer) RETURNS text AS '$libdir/vector','fannbench_last_execution' LANGUAGE C VOLATILE;
CREATE FUNCTION fannagent.take_trace(text) RETURNS text AS '$libdir/vector','fannagent_take_trace' LANGUAGE C STRICT VOLATILE;
'''
def conn():
 c=connect('host=/tmp/socket dbname=postgres user=nobody',autocommit=True)
 c.execute("SELECT fannagent.bind_target('reviews','id','embedding','reviews_fixture_graph')")
 return c
def tx(c):
 c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');c.execute(sql.SQL('SET TRANSACTION SNAPSHOT {}').format(sql.Literal(EXPORTED_SNAPSHOT)));c.execute('SET LOCAL enable_seqscan=off');c.execute('SET LOCAL hnsw.ef_search=8192')
EXPORTED_SNAPSHOT=None
def main():
 global EXPORTED_SNAPSHOT
 Path('/tmp/socket').mkdir(mode=0o700)
 subprocess.run(['/opt/postgresql/bin/initdb','-D','/tmp/pgdata','-A','trust','-U','nobody'],check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['/opt/postgresql/bin/pg_ctl','-D','/tmp/pgdata','-l','/tmp/server.log','-o',"-c listen_addresses='' -c unix_socket_directories=/tmp/socket",'-w','start'],check=True)
 try:
  with connect('host=/tmp/socket dbname=postgres user=nobody',autocommit=True) as c:c.execute(SQL+Path('/qual/functions.sql').read_text())
  with conn() as keeper:
   keeper.execute('BEGIN ISOLATION LEVEL REPEATABLE READ');keeper.execute('LOCK TABLE reviews IN SHARE MODE');EXPORTED_SNAPSHOT=keeper.execute('SELECT pg_export_snapshot()').fetchone()[0];heap,index=keeper.execute("SELECT 'reviews'::regclass::oid,'reviews_fixture_graph'::regclass::oid").fetchone();rows=keeper.execute('SELECT ctid::text,total_votes FROM reviews').fetchall();results=[]
   for t in THRESHOLDS:
    meta=publish(Path(f'/tmp/membership-{t}.bin'),heap,index,rows,t);q={'id':str(t),'k':10,'vector':[.3,.1,.8,.4,.9,.2,.6,.5]}
    if t>=0:q['filter']={'field':'totalvotes','op':'gte','value':t}
    with conn() as c:
     tx(c);native,_=search(c,q,fixture=True);c.execute('COMMIT')
     tx(c);c.execute("SELECT fannagent.study_local_bind('reviews',%s,%s)",(t,meta['qualifying']));local=capture(c,q,'local',fixture=True);c.execute('COMMIT')
     tx(c);c.execute("SELECT fannagent.study_attach('reviews','reviews_fixture_graph',%s,0,%s)",(t,meta['qualifying']));shared=capture(c,q,'shared',fixture=True)
     require(matches(local['output'],native) and matches(shared['output'],native),'capture changed native outputs')
     for lo,so in zip(local['checkpoints'],shared['checkpoints'],strict=True):
      require({k:v for k,v in lo.items() if k!='collection_ns'}=={k:v for k,v in so.items() if k!='collection_ns'},'local/shared features differ')
     forced_outputs={}
     for o in shared['checkpoints']:
      if o['qualifying_count']<10:continue
      forced=capture(c,q,'forced'+str(o['checkpoint']),budget=o['budget'],fixture=True)
      forced_outputs[o['checkpoint']]=forced['output']
      require(len(forced['output'])==10 and abs(max(d for _,d in forced['output'])-o['tenth_distance'])<=1e-6,'forced stop distance mismatch')
     c.execute('COMMIT')
     for arm in (1,2,3,4,5,6,7,8,9):
      tx(c);c.execute("SELECT fannagent.study_attach('reviews','reviews_fixture_graph',%s,%s,%s)",(t,arm,meta['qualifying']));out,_=search(c,q,fixture=True);cp=c.execute('SELECT fannagent.confirm_last()').fetchone()[0];c.execute('COMMIT')
      if arm>=7:
       wanted=expected(shared['checkpoints'],POLICIES[arm-7],t);require(cp==wanted,'compiled live checkpoint differs');require(matches(out,forced_outputs[wanted] if wanted else native),'compiled live output differs')
      if arm==6:require(cp==0 and matches(out,native),'no-stop changed native')
      if arm in (3,4,5):
       target=(16,32,64)[arm-3];obs=next((o for o in shared['checkpoints'] if o['checkpoint']==target and o['qualifying_count']>=10),None)
       if obs:require(cp==target and len(out)==10 and abs(max(d for _,d in out)-obs['tenth_distance'])<=1e-6,'live forced stop mismatch')
     # Header validation rejects a map attached with a wrong expected cohort.
     tx(c)
     try:c.execute("SELECT fannagent.study_attach('reviews','reviews_fixture_graph',%s,0,%s)",(t,meta['qualifying']-1))
     except Exception:c.execute('ROLLBACK')
     else:raise RuntimeError('wrong membership cohort accepted')
    guard_checks=[]
    for effort in (2,8192):
     outputs=[]
     with conn() as exact:
      tx(exact);exact.execute('SET LOCAL enable_seqscan=on');exact.execute('SET LOCAL enable_indexscan=off');exact.execute('SET LOCAL enable_indexonlyscan=off');exact.execute('SET LOCAL enable_bitmapscan=off')
      for arm in (None,6):
       with conn() as ann:
        tx(ann);ann.execute('SET LOCAL hnsw.ef_search='+str(effort))
        if arm is not None:ann.execute("SELECT fannagent.study_attach('reviews','reviews_fixture_graph',%s,%s,%s)",(t,arm,meta['qualifying']))
        attempts=[];result=guarded_request(ann,exact,q,meta['qualifying'],attempts.append,fixture=True)
        require(len(result['output'])==10,'guard result incomplete')
        if effort==2:require(result['fallback_used'] and attempts==['ann','completion_exact'],'short guard did not run exact')
        if arm==6:require(ann.execute('SELECT fannagent.confirm_last()').fetchone()[0]==0,'no-op stopped')
        outputs.append(result)
      require(matches(outputs[0]['initial'],outputs[1]['initial']) and matches(outputs[0]['output'],outputs[1]['output']) and outputs[0]['fallback_used']==outputs[1]['fallback_used'],'native/agent common guard parity differs')
     guard_checks.append({'ef':effort,'fallback_used':outputs[0]['fallback_used'],'both_paths_complete':True,'same_exported_snapshot':True})
    results.append({'threshold':t,'guard_checks':guard_checks,'checkpoints':len(shared['checkpoints']),'shared_local_native_parity':True,'forced_stop_parity':True,'no_stop_parity':True,'wrong_header_rejected':True,'three_compiled_policy_first_stop_and_output_parity':True})
   require(all(r['checkpoints']==3 for r in results),'fixture did not exercise all checkpoints')
   print('SMOKE_RECEIPT '+json.dumps({'status':'passed','fixture':'synthetic 8-dimensional partial graph','original_graph_qualified':False,'conditions':results,'architecture':os.uname().machine}),flush=True)
 finally:subprocess.run(['/opt/postgresql/bin/pg_ctl','-D','/tmp/pgdata','-m','fast','-w','stop'],check=True)
if __name__=='__main__':main()
