"""Seal development-only Torch qualification payload; no provider or search execution."""
import hashlib,io,json,shutil,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];STUDY=Path(__file__).resolve().parents[1];RUNTIME=STUDY/'runtime-guard-v1';KIT=STUDY/'kits/guard-qualification-v1'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
config=json.loads((STUDY/'protocol/config.json').read_text());split=json.loads((STUDY/'splits/split-manifest.json').read_text());freeze=json.loads((STUDY/'freeze/split-freeze.json').read_text())
assert sha(STUDY/'splits/split-manifest.json')==freeze['manifest_sha256']==config['split_manifest_sha256']
source=ROOT/'trials/reviews-persistent-batch-native-v1/confirmation-shared-v1/fannagent-votes108-shared-kit.tar.gz'
# Pin the historical input archive against its recorded sidecar before extracting.
expected=source.with_suffix(source.suffix+'.sha256').read_text().split()[0];assert sha(source)==expected
KIT.mkdir(exist_ok=True)
assert not any(KIT.iterdir()),'use a fresh versioned kit directory'
with tarfile.open(source,'r:gz') as old:
 (KIT/'original-package.tar.gz').write_bytes(old.extractfile('original-package.tar.gz').read())
queries=STUDY/'development/inputs/queries.jsonl';receipt=json.loads((STUDY/'development/inputs/manifest.json').read_text());assert sha(queries)==receipt['queries_sha256']
for name in ('run_guard.py','common.py','guard.py','support.py','experiment.py','verify_guard_return.py','functions.sql','vector.so','run-on-compute.sh','submit.sh'):
 shutil.copyfile(RUNTIME/name,KIT/name)
shutil.copyfile(queries,KIT/'queries.jsonl')
for name in ('config.json','study-protocol.md'):shutil.copyfile(STUDY/'protocol'/name,KIT/name)
for line in (RUNTIME/'checks/smoke.log').read_text().splitlines():
 if line.startswith('SMOKE_RECEIPT '):smoke=json.loads(line.removeprefix('SMOKE_RECEIPT '))
assert smoke['status']=='passed' and len(smoke['conditions'])==7
assert all(len(c['guard_checks'])==2 and c['guard_checks'][0]['fallback_used'] and c['guard_checks'][0]['both_paths_complete'] for c in smoke['conditions'])
save(KIT/'local-smoke.json',smoke)
with tarfile.open(KIT/'original-package.tar.gz','r:gz') as old:
 members=old.getmembers();assert not any(m.issym() or m.islnk() or Path(m.name).is_absolute() or '..' in Path(m.name).parts for m in members)
 m=next(m for m in members if m.name=='reviews-persistent-batch-native-v1/manifest.json');data=old.extractfile(m).read();assert hashlib.sha256(data).hexdigest()=='b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc'
 # Every serialized 768-d query in the inherited restore package must be development.
 import struct
 allowed={r['group'].split(':')[-1] for r in split['assignments'] if r['role']=='development'}
 seen=set()
 def inspect(o):
  if isinstance(o,dict):
   if isinstance(o.get('vector'),list) and len(o['vector'])==768:
    h=hashlib.sha256(struct.pack('<768f',*o['vector'])).hexdigest();assert h in allowed,'inherited package contains non-development vector';seen.add(h)
   for v in o.values():
    if isinstance(v,(dict,list)):inspect(v)
  elif isinstance(o,list):
   for v in o:
    if isinstance(v,(dict,list)):inspect(v)
 for m in members:
  if m.isfile() and m.name.endswith(('.json','.jsonl')):
   content=old.extractfile(m).read()
   if m.name.endswith('.jsonl'):
    for line in content.splitlines():
     if line.strip():inspect(json.loads(line))
   else:inspect(json.loads(content))
 save(KIT/'inherited-package-review.json',{'archive_sha256':sha(KIT/'original-package.tar.gz'),'query_vector_groups':len(seen),'all_serialized_queries_development':True,'archive_paths_safe':True})
prior_results=STUDY/'returns/job-22635567/results'
verification=json.loads((prior_results/'extended-verification.json').read_text());assert verification['records_verified']==3150 and verification['forced_outputs_verified']==7940
prior_receipt=json.loads((prior_results/'receipt.json').read_text())
for name,h in prior_receipt['raw_sha256'].items():assert sha(prior_results/name)==h
prior=[]
for t in (-1,743,527,310,192,108,32):
 for line in (prior_results/f'qualification-{t}.jsonl').read_text().splitlines():
  row=json.loads(line);prior.append({k:row[k] for k in ('id','exact','native')})
assert len(prior)==3150 and len({r['id'] for r in prior})==3150
(KIT/'prior-references.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in prior))
shutil.copyfile(STUDY/'protocol/completion-guard-plan-v1.json',KIT/'guard-plan.json')
shutil.copyfile(STUDY/'runtime-parent-v1/source-change.json',KIT/'source-change.json')
negative=STUDY/'returns/job-22643346/results'
verification=json.loads((negative/'negative-verification.json').read_text());assert verification['sweep_rows_verified']==15750
assert sha(negative/'parent-sweep.jsonl')==verification['raw_sha256']['parent-sweep.jsonl']
shutil.copyfile(negative/'parent-sweep.jsonl',KIT/'prior-sweep.jsonl')
save(KIT/'local-checks.json',{'module_build':'passed','synthetic_seven_filter_common_guard_smoke':'passed; native/noop, short/full, shared exported snapshot','target_restore_loader':'same inherited loader verified natively in job22635567; new parent target requalification pending','local_python_checks':7,'qualification_status':'not yet qualified on original graph'})
source_pins={str(p.relative_to(STUDY/'runtime-parent-v1')):sha(p) for p in sorted((STUDY/'runtime-parent-v1/engine').rglob('*')) if p.is_file() and p.suffix in ('.c','.h','.inc')}
binding={'schema':'reviews-clean-development-qualification.v1','split_manifest_sha256':freeze['manifest_sha256'],'protocol_sha256':sha(STUDY/'protocol/study-protocol.md'),'config_sha256':sha(STUDY/'protocol/config.json'),'module_sha256':sha(KIT/'vector.so'),'queries_sha256':sha(KIT/'queries.jsonl'),'development_source_indices':[r['source_index'] for r in split['assignments'] if r['role']=='development'],'queries':3150,'provider_calls':0,'source_engine_hashes':source_pins,'prior_references_sha256':sha(KIT/'prior-references.jsonl'),'prior_qualification_receipt_sha256':sha(prior_results/'receipt.json'),'guard_plan_sha256':sha(KIT/'guard-plan.json'),'guard_source_sha256':sha(KIT/'guard.py'),'prior_sweep_sha256':sha(KIT/'prior-sweep.jsonl'),'local_smoke_sha256':sha(KIT/'local-smoke.json'),'historical_source_kit_sha256':expected}
save(KIT/'binding.json',binding)
with (KIT/'SHA256SUMS').open('w') as f:
 for p in sorted(KIT.iterdir()):
  if p.is_file() and p.name!='SHA256SUMS':f.write(sha(p)+'  '+p.name+'\n')
archive=STUDY/'kits/guard-qualification-v1.tar.gz'
with tarfile.open(archive,'w:gz') as tar:tar.add(KIT,arcname='guard-qualification-v1')
archive.with_suffix('.gz.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
save(STUDY/'freeze/guard-plan-freeze-v1.json',{'schema':'reviews-clean-study-protocol-freeze.v1','protocol_sha256':binding['protocol_sha256'],'config_sha256':binding['config_sha256'],'split_sha256':freeze['manifest_sha256'],'qualification_archive_sha256':sha(archive),'qualification_module_sha256':binding['module_sha256'],'guard_plan_sha256':binding['guard_plan_sha256'],'guard_source_sha256':binding['guard_source_sha256'],'prior_job':'22635567','runtime_status':'native-only sweep negative; common guard smoke passed; original-graph guard qualification/timing pending','agent_dispatch':'not started; usage reconciliation and original-graph qualification required'})
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'binding':sha(KIT/'binding.json')},indent=2))
