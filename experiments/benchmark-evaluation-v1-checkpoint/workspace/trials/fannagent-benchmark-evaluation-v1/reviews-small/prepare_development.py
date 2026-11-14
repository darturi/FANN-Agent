"""Export only frozen development queries for the new episode; never open holdout outcomes."""
from pathlib import Path
import hashlib,json
import h5py
import numpy as np
ROOT=Path(__file__).resolve().parents[3]; STUDY=Path(__file__).resolve().parent
INV=STUDY.parent/'inventory'
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def prepare():
 freeze=json.loads((STUDY/'freeze/split-freeze.json').read_text())
 manifest_path=ROOT/freeze['manifest_path']; assert digest(manifest_path)==freeze['manifest_sha256'],'split manifest changed'
 manifest=json.loads(manifest_path.read_text())
 for name,h in freeze['role_file_hashes'].items():assert digest(STUDY/'splits'/name)==h,'role file changed'
 for rel,h in manifest['input_hashes'].items():assert digest(ROOT/rel)==h,'split evidence changed'
 groups=[json.loads(l) for l in (STUDY/'splits/development.jsonl').read_text().splitlines()]
 assert len(groups)==450 and all(g['role']=='development' for g in groups)
 selected=sorted(groups,key=lambda g:g['source_index']); indices=[g['source_index'] for g in selected]
 source=ROOT/'harness/downloads/morevec/MoRe_small/queries/queries_flex_reviews_sim_0_0.hdf5'
 inv=json.loads((INV/'source-inventory.json').read_text()); source_pin=next(x['sha256'] for x in inv['sources'] if x['path']==str(source.relative_to(ROOT)))
 assert digest(source)==source_pin,'source query file changed'
 with h5py.File(source,'r') as f: vectors=np.asarray(f['test'][indices],dtype=np.float32)
 for group,v in zip(selected,vectors):assert 'reviews-small-sha256:'+hashlib.sha256(v.astype('<f4').tobytes()).hexdigest()==group['group']
 # Semantic fields are canonical importer names. Bind to an engine's physical
 # fields only after checking its schema; do not assume m_000000 is totalvotes.
 thresholds=[None,743,527,310,192,108,32]; queries=[]
 for group,v in zip(selected,vectors):
  for threshold in thresholds:
   name='unfiltered' if threshold is None else f'votes{threshold}'
   q={'schema_version':1,'id':f"reviews-clean-v{group['source_index']:04d}-{name}",'vector':v.astype(float).tolist(),'k':10}
   if threshold is not None:q['filter']={'field':'totalvotes','op':'gte','value':threshold}
   queries.append(q)
 target=STUDY/'development/inputs';target.mkdir(parents=True,exist_ok=True)
 content=''.join(json.dumps(q,sort_keys=True,separators=(',',':'))+'\n' for q in queries)
 p=target/'queries.jsonl'
 if p.exists():assert p.read_text()==content,'existing development export differs'
 else:p.write_text(content)
 receipt={'schema':'fannagent-development-inputs.v1','split_sha256':freeze['manifest_sha256'],'source_sha256':source_pin,'queries_sha256':digest(p),'groups':450,'queries':len(queries),'filters_per_group':7,'roles':['development'],'semantic_filter_field':'totalvotes','vector_representation':'published query float64 converted to float32; serving normalization/formatter must be qualified','agent_feedback':'query inputs only; no search or outcomes generated','qualification':'pending Phase 1 protocol and engine adapter checks'}
 (target/'manifest.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in receipt.items() if k in ('groups','queries','roles','split_sha256')},indent=2))
if __name__=='__main__':prepare()
