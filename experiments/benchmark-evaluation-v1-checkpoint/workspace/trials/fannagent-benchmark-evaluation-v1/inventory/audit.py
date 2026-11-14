"""Metadata-only Phase 0 inventory. Never execute searches or inspect recall/distance values."""
from pathlib import Path
import hashlib,json,subprocess,collections
import numpy as np
import h5py
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'harness/downloads/morevec/MoRe_small'
def sha(b): return hashlib.sha256(b).hexdigest()
def file_sha(p):
 with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def dump(name,x): (OUT/name).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def key(v): return sha(np.asarray(v,dtype='<f4').tobytes())
with h5py.File(SOURCE/'queries/queries_flex_reviews_sim_0_0.hdf5') as f:
 raw=f['test'][:]; ids=[x.decode() if isinstance(x,bytes) else str(x) for x in f['rid'][:]]
f32=raw.astype(np.float32)
# Include both importer floats and load_queries' float32 normalization; reconcile by actual values.
norm=f32/np.linalg.norm(f32,axis=1)[:,None]
lookup={}
for i in range(len(raw)):
 for variant in (f32[i],norm[i]): lookup.setdefault(key(variant),set()).add(i)
assert len({key(v) for v in f32})==1000
if (OUT.parent/'reviews-small/freeze/split-freeze.json').exists():
 raise SystemExit('Inventory is pinned by the clean split; create a versioned audit instead of overwriting')
inventory=[]
for p in sorted(SOURCE.rglob('*reviews*.hdf5')):
 with h5py.File(p) as f:
  info={n:{'shape':list(o.shape),'dtype':str(o.dtype)} for n,o in f.items() if isinstance(o,h5py.Dataset)}
  if 'test' in f: assert np.array_equal(f['test'][:],raw)
  inventory.append({'path':str(p.relative_to(ROOT)),'sha256':file_sha(p),'bytes':p.stat().st_size,'datasets':info})
with h5py.File(SOURCE/'filters/reviews_filters_0.hdf5') as f: filters=[x.decode() for x in f['filters'][:]]
# Audit every tracked/unignored JSONL in research/experiment trees, not just latest manifests.
paths=subprocess.check_output(['rg','--files','--hidden','--no-ignore','-g','*.jsonl','-g','!release/**','-g','!**/.git/**','-g','!**/.venv/**','-g','!**/site-packages/**','-g','!**/offline-cache/**','-g','!**/cache/**','-g','!trials/fannagent-benchmark-evaluation-v1/**'],cwd=ROOT,text=True).splitlines()
evidence=collections.defaultdict(list); files=[]; errors=[]; cache={}
def queries(obj):
 if isinstance(obj,dict):
  if isinstance(obj.get('vector'),list) and len(obj['vector'])==768: yield obj
  # Query metadata only: do not walk checkpoints/results/recall or other outcome fields.
  for name in ('query','request','queries','requests','cases','workload'):
   val=obj.get(name)
   if isinstance(val,(dict,list)): yield from queries(val)
 elif isinstance(obj,list):
  for x in obj: yield from queries(x)
excluded=[]
resolved={}
for rel in sorted(paths):
 if not any(t in Path(rel).name.lower() for t in ("quer", "evaluation", "training", "learning", "acquire", "qualification", "study", "development", "fresh", "workload", "calibration", "reserved")):
  excluded.append(rel); continue
 p=ROOT/rel
 if p.is_symlink(): continue
 digest=file_sha(p)
 if digest in cache:
  record=dict(cache[digest]); record['path']=rel; record['duplicate_content']=True
 else:
  groups=set(); aliases=collections.defaultdict(set); matched=unmatched=0
  try:
   with p.open() as f:
    for line in f:
     if not line.strip(): continue
     obj=json.loads(line)
     for q in queries(obj):
      v=np.asarray(q['vector'],dtype=np.float32); vk=key(v); hits=resolved.get(vk,lookup.get(vk))
      if hits is None:
       # Resolve older decimal serialization by tightly bounded elementwise equality.
       delta=np.max(np.abs(norm-v),axis=1); idx=np.flatnonzero(delta<=2e-7)
       hits=set(map(int,idx)) if len(idx)==1 else set()
      resolved[vk]=hits
      if hits:
       assert len(hits)==1
       i=next(iter(hits)); groups.add(i); matched+=1
       aliases[i].add(str(q.get('id',q.get('query_id','unknown'))))
      else: unmatched+=1
  except (ValueError,OSError) as e: errors.append({'path':rel,'error':str(e)})
  record={'path':rel,'sha256':digest,'groups':sorted(groups),'matched_query_records':matched,'unmatched_768d_records':unmatched,'aliases':{str(k):sorted(v) for k,v in aliases.items()}}
  cache[digest]=record
 files.append(record)
 # Full imported workload is inventory, not evidence of running each query.
 if rel.startswith('harness/data/') and '/splits/' not in rel: continue
 for i in record['groups']:
  evidence[i].append({'path':rel,'sha256':digest,'aliases':record['aliases'].get(str(i),[])})
dump('source-inventory.json',{'sources':inventory,'filters':filters,'groups':1000,'dimension':768,'metric':'cosine (retained runtime; source distance semantics require Phase 2 verification)','ground_truth':'Shapes/dtypes only; distances and rids outcomes not loaded','matching':'float32 exact, normalized float32 exact, otherwise unique max-coordinate difference <=2e-7','jsonl_files_scanned':len(files),'errors':errors})
dump('historical-query-files.json',files)
dump('excluded-outcome-files.json',excluded)
dump('group-evidence.json',{str(k):v for k,v in sorted(evidence.items())})
print(json.dumps({'files':len(files),'unique_contents':len(cache),'historically_referenced_groups':len(evidence),'unreferenced_groups':1000-len(evidence),'errors':errors},indent=2))
