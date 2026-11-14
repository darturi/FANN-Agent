"""Describe existing qualified feature aliases; no fitting or policy evaluation."""
from pathlib import Path
import hashlib,json,collections as C
H=Path(__file__).resolve().parent
R=H.parents[1]
a=json.loads((H/'audit.json').read_text())
p=R/'trials/torch-reviews-selective-agent-v1/runs/20261022T192817Z-66ed81d6/evidence/corpus.json'
assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==a['source_input_hashes'][str(p.relative_to(R))]
qs=json.loads(p.read_text())['queries']
names=[n for n,d in a['feature_definitions'].items() if d['group'] in {'basic','work','queue','distances'}]
digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
groups={}
for q in qs:groups.setdefault(q['group'],{})[q['stratum']]=q
counts=C.Counter()
for group,items in groups.items():
 x,y=items['votes32'],items['votes108']
 proj=lambda q:[{**s,'features':{n:s['features'][n] for n in names}} for s in q['base_states']]
 equal=proj(x)==proj(y)
 counts['filtered_vector_pairs']+=1;counts['identical_light19_filtered_trajectory_pairs']+=equal
 anyconflict=False
 for cp in x['labels']['base']:
  if cp not in y['labels']['base']:continue
  a1,b1=x['labels']['base'][cp],y['labels']['base'][cp]
  target=lambda label,q:label['valid'] and label['returned_count']==10 and label['recall']>=q['native_recall']
  counts['paired_measured_grid_states']+=1
  if target(a1,x)!=target(b1,y):
   counts['different_complete_recall_preservation_labels']+=1
   anyconflict=True
 counts['vectors_with_any_different_complete_recall_preservation_label']+=anyconflict
result={'version':'p3a-feature-alias-diagnostics.v1','counts':dict(counts),'target_definition':'Complete top-10 with recall at least this query native recall; descriptive per-state label, not final policy acceptance.','interpretation':'Light19 aliases the two filtered trajectories. Static23/progress34 have validated actual query_predicate_threshold as qualified runtime input; learner must not substitute group/query ID or evaluator stratum. Composite routing remains a separate actual-predicate boundary. Dynamic progress observations are recorded but predictive value is untested.','new_fits_simulations_or_measurements':0}
with (H/'feature-diagnostics.json').open('x') as h:json.dump(result,h,indent=2,sort_keys=True);h.write('\n')
print(json.dumps(result,indent=2))
