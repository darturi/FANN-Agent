"""Check historical reservations using read-only broker state and saved outcome identities."""
import collections,hashlib,json,re,sqlite3,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def file_sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(name,o):
 content=json.dumps(o,indent=2,sort_keys=True)+'\n'
 p=OUT/name
 if (OUT.parent/'reviews-small/freeze/split-freeze.json').exists() and p.exists() and p.read_text()!=content:
  raise RuntimeError('Reservation evidence is frozen; write a versioned replacement')
 p.write_text(content)
cat=[json.loads(l) for l in (OUT/'snapshots/phase0-provisional/query-catalog.jsonl').read_text().splitlines()]
index={r['float32_sha256']:r['source_index'] for r in cat}
states=[]; roles={}; pins={}
for p in sorted(ROOT.glob('trials/morevec-reviews-*bounded/studies/*/run/state.sqlite3')):
 db_pins={str(q.relative_to(ROOT)):file_sha(q) for q in (p,Path(str(p)+'-wal')) if q.exists()}
 c=sqlite3.connect(f'file:{p}?mode=ro',uri=True)
 keys=[k for (k,) in c.execute('select key from state')]
 protected=[k for k in keys if k.startswith(('calibration:','test_','frozen'))]
 kinds=c.execute('select kind,scope,count(*) from artifacts group by kind,scope').fetchall()
 record={'path':str(p.relative_to(ROOT)),'sha256':file_sha(p),'protected_state_keys':protected,'artifact_kind_counts':kinds}
 assert not protected
 r=c.execute("select path from artifacts where kind='study'").fetchone()
 if r:
  sp=p.parent/r[0]; study=json.loads(sp.read_text()); local={}
  for item in study['items']:
   m=re.fullmatch(r'reviews-bounded-v(\d+)-(?:unfiltered|votes\d+)',item['query']['id']); assert m
   i=int(m[1]); assert i not in local or local[i]==item['split'];local[i]=item['split']
  assert not roles or local==roles;roles=local
  pins[str(sp.relative_to(ROOT))]=file_sha(sp)
  record['group_role_counts']=dict(collections.Counter(local.values()))
 c.close()
 assert all(file_sha(ROOT/q)==h for q,h in db_pins.items())
 pins.update(db_pins)
 states.append(record)
assert collections.Counter(roles.values())=={'development':450,'calibration':150,'test':150}
ap=ROOT/'trials/torch-reviews-results/feature-data-ablation-v1/torch-feature-data-ablation-v1/inputs/ablation-split.json'
a=json.loads(ap.read_text()); reserved={index[a['vector_hash_by_catalog_group'][g]] for g in a['selected_catalog_groups']['reserved']}
protected={i for i,r in roles.items() if r!='development'}
candidates=protected|reserved
# Search stable bounded aliases in all local JSON/JSONL evidence, including ignored files.
pattern=OUT/'reservation-alias-pattern.txt'
pattern.write_text('reviews-bounded-v(?:'+'|'.join(f'{i:04d}' for i in sorted(candidates))+')(?=[^0-9]|$)\n')
args=['rg','-l','--pcre2','--hidden','--no-ignore','-g','*.json','-g','*.jsonl','-g','!release/**','-g','!**/.git/**','-g','!**/.venv/**','-g','!**/site-packages/**','-g','!**/offline-cache/**','-g','!**/cache/**','-g','!trials/fannagent-benchmark-evaluation-v1/**','-f',str(pattern),'trials','agent','agent-main','agent-pgvector','agent-showcase','harness','research']
proc=subprocess.run(args,cwd=ROOT,text=True,capture_output=True);assert proc.returncode in (0,1),proc.stderr
paths=sorted(proc.stdout.splitlines()); outcomes=collections.defaultdict(list); refs=[];errors=[];cache={}
outcome_keys={'native_recall','policy_recall','recall','native_ms','policy_ms','checkpoints','labels','neighbors','result_ids','stop_labels','measurements','distances','trace','recall_delta','returned_ids','exact_ids','topk'}
rx=re.compile(r'reviews-bounded-v(\d+)(?!\d)')
def inspect(o,found):
 if isinstance(o,dict):
  identifiers=[]
  for k in ('id','query_id','group','vector_group'):
   if isinstance(o.get(k),str): identifiers.append(o[k])
  if isinstance(o.get('query'),dict) and isinstance(o['query'].get('id'),str):identifiers.append(o['query']['id'])
  groups={int(m.group(1)) for s in identifiers for m in rx.finditer(s)}&candidates
  if groups and outcome_keys.intersection(o):
   for i in groups: found[i].update(outcome_keys.intersection(o))
  for v in o.values():
   if isinstance(v,(dict,list)):inspect(v,found)
 elif isinstance(o,list):
  for v in o:
   if isinstance(v,(dict,list)): inspect(v,found)
for rel in paths:
 p=ROOT/rel; h=file_sha(p)
 if h not in cache:
  found=collections.defaultdict(set)
  try:
   with p.open() as f:
    if p.suffix=='.jsonl':
     for line in f:
      if line.strip(): inspect(json.loads(line),found)
    else:inspect(json.load(f),found)
  except (ValueError,OSError) as e: errors.append({'path':rel,'error':str(e)})
  cache[h]={str(i):sorted(v) for i,v in found.items()}
 rec={'path':rel,'sha256':h,'outcome_groups':cache[h]};refs.append(rec)
 for i,keys in cache[h].items():outcomes[int(i)].append({'path':rel,'sha256':h,'outcome_keys':keys})
assert not errors,errors
summary_evidence=[]
for rel in ('trials/morevec-reviews-bounded/execution-20261012T003700Z/status.json','trials/morevec-reviews-bounded/execution-20261012T003900Z/status.json','trials/morevec-reviews-fixed-bounded/execution-20261012T015808Z/status.json','trials/morevec-reviews-durable-bounded/execution-20261012T053001Z/status.json','trials/morevec-reviews-overhead-predictor/run-20261013T133737Z/audit.json'):
 p=ROOT/rel; o=json.loads(p.read_text()); pins[rel]=file_sha(p)
 keep={k:v for k,v in o.items() if k in ('held_out_test_consumed','calibrations','held_out_queries_executed','calibration_executions','final_test_executions','backend_searches')}
 assert all(v is False or v==0 for v in keep.values())
 summary_evidence.append({'path':rel,'fields':keep})
protected_hits=protected&set(outcomes)
reserved_hits=reserved&set(outcomes)
write('reservation-evidence-files.json',refs)
write('reservation-audit.json',{'scope':'local broker states, study manifests, canonical aliases in saved JSON/JSONL outcomes; no complete remote/chat access log','broker_states':states,'execution_summary_checks':summary_evidence,'pins':{**pins,str(ap.relative_to(ROOT)):file_sha(ap),'agent/src/fannagent/study.py':file_sha(ROOT/'agent/src/fannagent/study.py')},'historical_assignments':{str(i):r for i,r in sorted(roles.items())},'late_reserved_groups':sorted(reserved),'late_reserved_groups_with_prior_outcomes':sorted(reserved_hits),'canonical_protected_groups':sorted(protected),'canonical_protected_groups_with_outcome_hits':sorted(protected_hits),'outcome_evidence':{str(i):v for i,v in sorted(outcomes.items())},'matched_files_scanned':len(refs),'distinct_contents_scanned':len(cache),'scan_errors':errors,'disposition':'recover canonical protected groups only if no outcome hits; late reservations with outcomes stay development'})
print(json.dumps({'files':len(refs),'unique_contents':len(cache),'late_reserved_prior_outcomes':len(reserved_hits),'canonical_protected_outcome_hits':len(protected_hits),'errors':errors},indent=2))
