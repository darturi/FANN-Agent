"""Predicate-scoped membership and development-only qualification primitives."""
import hashlib,json,math,os,struct
from pathlib import Path
from time import perf_counter_ns
THRESHOLDS=(-1,743,527,310,192,108,32)
CHECKPOINTS=(16,32,64)
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,o):Path(p).write_text(json.dumps(o,sort_keys=True,indent=2,allow_nan=False)+'\n')
def publish(path,heap,index,rows,threshold):
 decoded=[]
 for tid,votes in rows:
  b,o=map(int,str(tid).strip('()').split(','));require(b>=0 and 1<=o<=512,'invalid TID')
  decoded.append((b,o-1,threshold<0 or votes is not None and votes>=threshold))
 require(len(decoded)==247286,'wrong corpus size');passing=sum(p for _,_,p in decoded)
 contents=bytearray((max(b for b,_,_ in decoded)+1)*128)
 for b,o,p in decoded:
  byte=b*128+o//4;shift=(o%4)*2;require(not contents[byte]&(3<<shift),'duplicate TID');contents[byte]|=(3 if p else 1)<<shift
 require(len(contents)+24<=256*1024*1024,'map too large')
 with path.open('xb') as f:f.write(struct.pack('<8sIIII',b'V108MAP1',heap,index,247286,passing));f.write(contents);f.flush();os.fchmod(f.fileno(),0o400);os.fsync(f.fileno())
 return {'threshold':threshold,'qualifying':passing,'bytes':path.stat().st_size,'sha256':sha(path)}
def threshold(q):return q.get('filter',{}).get('value',-1)
def statement(q,*,exact=False,fixture=False):
 t=threshold(q);require(t in THRESHOLDS and q['k']==10,'unexpected query semantics')
 require(len(q['vector']) in (8,768) and all(math.isfinite(v) for v in q['vector']),'invalid vector')
 vector='['+','.join(format(float(v),'.9g') for v in q['vector'])+']'
 predicates=[];params=[vector]
 if fixture:predicates.append('id <= 16000')
 if t>=0:predicates.append('total_votes >= %s');params.append(t)
 query='SELECT id, embedding <=> %s::vector AS distance FROM public.reviews'+(' WHERE '+' AND '.join(predicates) if predicates else '')+' ORDER BY embedding <=> %s::vector'
 params.append(vector)
 return query+(' FETCH FIRST 10 ROWS WITH TIES' if exact else ' LIMIT 10'),tuple(params)
def search(conn,q,*,exact=False,fixture=False):
 s,p=statement(q,exact=exact,fixture=fixture);start=perf_counter_ns();out=conn.execute(s,p,prepare=False).fetchall();elapsed=perf_counter_ns()-start
 return [[i,float(d)] for i,d in out],elapsed
def matches(a,b):return len(a)==len(b) and {i for i,_ in a}=={i for i,_ in b} and all(abs(dict(a)[i]-d)<=1e-6 for i,d in b)
def capture(conn,q,nonce,*,budget=None,fixture=False):
 t=threshold(q)
 require(conn.execute('SELECT fannagent.begin_execution(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',('fixed_budget' if budget else 'policy_noop',None,budget,nonce,10,int(t>=0),'checkpoints',10485760,'research','research','basic,distances,query_context,queue,work',False,max(0,t))).fetchone()==(nonce,),'begin failed')
 out,elapsed=search(conn,q,fixture=fixture)
 telemetry=json.loads(conn.execute('SELECT fannagent.complete(%s,%s)',(nonce,len(out))).fetchone()[0]);obs=json.loads(conn.execute('SELECT fannagent.shadow_read(%s)',(nonce,)).fetchone()[0]);raw=conn.execute('SELECT fannagent.take_trace(%s)',(nonce,)).fetchone()[0]
 events=[json.loads(line) for line in raw.splitlines() if line.strip()];states={int(e['index']):e for e in events if e.get('type')=='checkpoint'}
 require(telemetry['returned_count']==len(out),'completion count differs')
 for o in obs:
  cp=o['checkpoint'];require(cp in states and o['extra_heap_fetches']==0,'checkpoint mismatch')
  e=states[cp];o['budget']=e['target'];frontier=e['features'].get('frontier_distance_min');o['frontier_gap']=None if frontier is None or o['tenth_distance'] is None else frontier-o['tenth_distance']
 return {'output':out,'request_ns':elapsed,'checkpoints':obs,'states':states,'telemetry':telemetry}
