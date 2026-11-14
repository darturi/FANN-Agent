"""Persistent reader PIDs, transaction-isolated role changes and verified CPU affinity."""
import os
from contextlib import contextmanager
from common import require
@contextmanager
def session(Backend,args):
 b=Backend(args.bundle,args.work);b.state['source_manifest']['settings']['hnsw.ef_search']='640'
 try:
  c=b._connect();require(c.autocommit,'reader requires autocommit for separate role transactions');yield c
 finally:b.close()
@contextmanager
def bind(c,args,t,passing,arm):
 from psycopg import sql
 with c.transaction():
  c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
  c.execute(sql.SQL('SET TRANSACTION SNAPSHOT {}').format(sql.Literal(args.snapshot)))
  c.execute('SET LOCAL max_parallel_workers_per_gather=0');c.execute('SET LOCAL idle_in_transaction_session_timeout=0');c.execute('SET LOCAL hnsw.ef_search=640');c.execute('SET LOCAL hnsw.iterative_scan=off')
  if arm is not None:c.execute("SELECT fannagent.study_attach('reviews','reviews_hnsw',%s,%s,%s)",(t,arm,passing))
  yield c

def pin(pid,cpu,allowed):
 require(cpu in allowed and pid>0,'invalid reader CPU/PID');before=sorted(os.sched_getaffinity(pid));os.sched_setaffinity(pid,{cpu});require(os.sched_getaffinity(pid)=={cpu},'reader affinity did not apply')
 return {'pid':pid,'cpu':cpu,'affinity_before':before,'affinity_after':[cpu]}
