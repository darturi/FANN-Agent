"""Freeze reviewed group roles; refuse to overwrite an existing different freeze."""
import collections,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; INV=Path(__file__).resolve().parent
STUDY=INV.parent/'reviews-small'; SPLITS=STUDY/'splits'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def serialized(o):return json.dumps(o,indent=2,sort_keys=True)+'\n'
def sealed_write(p,content):
 if p.exists() and p.read_text()!=content: raise RuntimeError(f'Frozen file differs: {p}; create a versioned replacement')
 if not p.exists():p.write_text(content)
audit=json.loads((INV/'reservation-audit.json').read_text())
assert audit['canonical_protected_groups_with_outcome_hits']==[]
assert len(audit['late_reserved_groups_with_prior_outcomes'])==37
assert all(sha(ROOT/p)==h for p,h in audit['pins'].items())
old=json.loads((INV/'snapshots/phase0-provisional/split-manifest.json').read_text())
rows=[json.loads(l) for l in (INV/'snapshots/phase0-provisional/query-catalog.jsonl').read_text().splitlines()]
source={r['source_index']:r for r in rows}
historical={int(i):r for i,r in audit['historical_assignments'].items()}
available={r['source_index'] for r in old['assignments'] if r['role'] in ('validation','test')}
assert len(available)==125 and available.isdisjoint(historical)
roles={i:('validation' if historical.get(i)=='calibration' else historical[i] if i in historical else 'test' if i in available else 'excluded_historical') for i in range(1000)}
counts=dict(collections.Counter(roles.values()));assert counts=={'development':450,'validation':150,'test':275,'excluded_historical':125}
assert all(roles[i]=='development' for i in audit['late_reserved_groups'])
assert all(roles[r['source_index']]=='development' for r in old['assignments'] if r['role'] in ('development','consumed_evaluation_development'))
evidence=json.loads((INV/'group-evidence.json').read_text())
assert not available.intersection(map(int,evidence))
# Every historical query-bearing inventory intersection with held-out groups must
# be a metadata-only study input, never a development/training/confirmation cohort.
files=json.loads((INV/'historical-query-files.json').read_text()); protected=set(audit['canonical_protected_groups']);cross=[]
for f in files:
 hits=protected.intersection(f['groups'])
 if hits:
  assert Path(f['path']).name=='study-queries.jsonl',f['path']
  cross.append({'path':f['path'],'sha256':f['sha256'],'protected_groups':len(hits),'classification':'private study input, no outcome exposure; broker audit verified'})
assignments=[]
for i in range(1000):
 r=source[i]; assignments.append({'source_index':i,'group':'reviews-small-sha256:'+r['float32_sha256'],'source_query_id':r['source_query_id'],'role':roles[i],'historical_role':historical.get(i),'basis':'recovered protected partition' if i in protected else 'no historical inventory reference' if i in available else 'prior development outcomes' if i in historical else 'earlier workload; excluded conservatively'})
for role in counts:
 selected=[x for x in assignments if x['role']==role]
 sealed_write(SPLITS/(role+'.jsonl'),''.join(json.dumps(x,sort_keys=True)+'\n' for x in selected))
manifest={'schema':'fannagent-clean-query-split.v1','status':'frozen','date':'2026-11-10','authority':'user-authorized restart after reservation audit','dataset':'MoReVec Reviews Small','policy_learning_split':'researcher-defined; MoReVec publishes corpus and query workload, not this learning partition','algorithm':'preserve historical development/calibration/test groups; map calibration to validation; add all 125 unreferenced groups to test; exclude earlier 125 groups','random_seed':None,'seed_reason':'no new random assignment; deterministic historical-role preservation','counts':counts,'query_filter_pairs':{k:v*7 for k,v in counts.items()},'scope':{'filters':['unfiltered','votes743','votes527','votes310','votes192','votes108','votes32'],'k':10,'dimension':768,'metric':'cosine; runtime and ground truth qualification remains mandatory'},'assignments':assignments,'historical_protected_inventory_crosscheck':cross,'independence':'group-disjoint across every filter; same vector identities retain roles at overlapping scales','precision':{'test_independent_groups':275,'zero_loss_one_sided_95pct_upper_loss_probability':1-0.05**(1/275),'inference_limit':'does not establish a worst-case 0.25 percentage point population mean recall noninferiority margin; fixed-workload and population claims remain distinct'},'access_rules':{'development':'agent generation, tuning, folds, runtime qualification','validation':'single bounded selection after development proposals and selection rule are frozen; no feedback-driven proposal revision','test':'no outcomes before final policy/baseline/analysis/schedule freeze; never agent feedback for this version','excluded_historical':'not available for validation or test'},'method_restart':'new agent proposal episode on development; previous policy is a historical comparator, not a substitute for this episode','limitations':['Local recorded-history evidence, not proof of unrecorded remote/chat access','Private query metadata is not query-specific outcome exposure','No statistical thresholds or job/provider budgets are authorized by this split alone; Phase 1 protocol must be finalized before running'],'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in (INV/'reservation-audit.json',INV/'reservation-evidence-files.json',INV/'source-inventory.json',INV/'storage-inventory.json',INV/'snapshots/phase0-provisional/split-manifest.json')},'role_file_hashes':{p.name:sha(p) for p in sorted(SPLITS/(role+'.jsonl') for role in counts)}}
sealed_write(SPLITS/'split-manifest.json',serialized(manifest))
sealed_write(STUDY/'freeze/split-freeze.json',serialized({'schema':'fannagent-split-freeze.v1','manifest_path':str((SPLITS/'split-manifest.json').relative_to(ROOT)),'manifest_sha256':sha(SPLITS/'split-manifest.json'),'counts':counts,'role_file_hashes':manifest['role_file_hashes'],'policy_and_analysis_freeze':'pending Phase 1 and subsequent development; split freeze is already binding'}))
# Updated catalog is a versioned artifact; original provisional catalog is preserved.
for r in rows:r['role']=roles[r['source_index']];r.pop('proposed_role',None);r['split_manifest_sha256']=sha(SPLITS/'split-manifest.json')
sealed_write(SPLITS/'query-catalog.jsonl',''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
verification={'roles':counts,'catalog_rows':len(rows),'disjoint_groups':len(assignments),'late_reservations_with_outcomes_excluded_from_holdout':37,'recovered_canonical_protected_groups':len(protected),'historical_consumed_groups_all_development':True,'outcome_scan_hits_in_recovered_holdout':0,'all_input_hashes_verified':True,'role_file_hashes_verified':True,'freeze_sha256':sha(STUDY/'freeze/split-freeze.json')}
sealed_write(SPLITS/'verification.json',serialized(verification))
print(serialized(verification))
