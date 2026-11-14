from pathlib import Path
import hashlib,json
import h5py
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
def sha(p):
 with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
files=[]
for base in ('morevec-reviews-small','morevec-reviews-small-v2'):
 for name in ('manifest.yaml','records.parquet'):
  p=ROOT/'harness/data'/base/name
  files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
for rel in ('harness/src/fannbench/datasets/morevec.py','harness/src/fannbench/data.py','agent/experiments/reviews-persistent-batch-v1/qualified-confirmation/freeze.json','agent/experiments/reviews-persistent-batch-v1/qualified-confirmation/stage_inputs.py','research/fannagent-controlled-reviews-batch-manifest-2026-11-08.json'):
 p=ROOT/rel; files.append({'path':rel,'sha256':sha(p)})
with h5py.File(ROOT/'harness/downloads/morevec/MoRe_small/datasets/reviews_dataset_0.hdf5') as f:
 ids=[v.decode() if isinstance(v,bytes) else str(v) for v in f['train_rid'][:]]
with h5py.File(ROOT/'harness/downloads/morevec/MoRe_small/queries/queries_flex_reviews_sim_0_0.hdf5') as f:
 qids=[v.decode() if isinstance(v,bytes) else str(v) for v in f['rid'][:]]
t=pq.read_table(ROOT/'harness/data/morevec-reviews-small-v2/records.parquet',columns=['id','source_id'])
assert t['source_id'].to_pylist()==ids
assert t['id'].to_pylist()==list(range(len(ids)))
assert len(set(ids))==len(ids) and set(qids)<=set(ids)
(OUT/'storage-inventory.json').write_text(json.dumps({'files':files,'id_mapping':{'corpus_rows':len(ids),'unique_source_ids':len(set(ids)),'canonical_ids':'zero-based source row order; verified against v2 Parquet','queries_in_corpus':len(qids),'self_match':'Query source IDs are present in corpus. Preserve eligibility; no self-match removal introduced. Official ground-truth self-match/tie semantics require Phase 2 qualification.'},'database_identity':'Historical original graph is referenced by existing freeze/kit manifests. No database started or restored; physical PG backup/index identity must be requalified before execution.','ground_truth':'HDF5 rid is query identity; rids (1000,100) are source-ID neighbors; distances (1000,100). Only schema was inspected, not held-out neighbor/distance outcomes.'},indent=2)+'\n')
print('Storage checksums and source-ID mapping verified')
