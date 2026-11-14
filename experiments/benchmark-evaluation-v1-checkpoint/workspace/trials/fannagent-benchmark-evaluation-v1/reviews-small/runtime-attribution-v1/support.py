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
def reader(Backend,args,t,passing,arm=None,local=False,exact=False,ef=640):
 b=Backend(args.bundle,args.work);b.state['source_manifest']['settings']['hnsw.ef_search']=str(ef)
 try:
  c=b._connect()
  with c.transaction():
   c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
   from psycopg import sql
   require(bool(getattr(args,'snapshot',None)),'exported snapshot required')
   c.execute(sql.SQL('SET TRANSACTION SNAPSHOT {}').format(sql.Literal(args.snapshot)))
   c.execute('SET LOCAL max_parallel_workers_per_gather=0')
   c.execute('SET LOCAL idle_in_transaction_session_timeout=0')
   if exact:
    c.execute('SET LOCAL enable_seqscan=on');c.execute('SET LOCAL enable_indexscan=off');c.execute('SET LOCAL enable_indexonlyscan=off');c.execute('SET LOCAL enable_bitmapscan=off')
   elif local:c.execute("SELECT fannagent.study_local_bind('reviews',%s,%s)",(t,passing))
   elif arm is not None:c.execute("SELECT fannagent.study_attach('reviews','reviews_hnsw',%s,%s,%s)",(t,arm,passing))
   c.execute("SET LOCAL hnsw.iterative_scan=off")
   yield c
 finally:b.close()
def count_search(counter,operation,fn,*a,**kw):
 require(counter['total']<225000,'qualification search cap');counter['total']+=1;counter[operation]=counter.get(operation,0)+1;return fn(*a,**kw)
def valid(out,q,eligible,truth):
 if not eligible:
  require(not out,"nonempty result for empty eligible population");return 1.0
 require(len(out)<=min(10,len(eligible)) and len({i for i,_ in out})==len(out),'oversized/duplicate results')
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
