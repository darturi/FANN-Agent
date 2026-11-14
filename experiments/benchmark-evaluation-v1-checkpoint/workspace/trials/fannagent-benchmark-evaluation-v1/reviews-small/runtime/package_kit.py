"""Seal development-only Torch qualification payload; no provider or search execution."""
import hashlib,io,json,shutil,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];STUDY=Path(__file__).resolve().parents[1];RUNTIME=STUDY/'runtime';KIT=STUDY/'kits/development-runtime-v2'
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
for name in ('qualify.py','common.py','verify_return.py','functions.sql','vector.so','run-on-compute.sh','submit.sh'):
 shutil.copyfile(RUNTIME/name,KIT/name)
shutil.copyfile(queries,KIT/'queries.jsonl')
for name in ('config.json','study-protocol.md'):shutil.copyfile(STUDY/'protocol'/name,KIT/name)
for line in (RUNTIME/'checks/smoke.log').read_text().splitlines():
 if line.startswith('SMOKE_RECEIPT '):smoke=json.loads(line.removeprefix('SMOKE_RECEIPT '))
assert smoke['status']=='passed' and len(smoke['conditions'])==7
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
save(KIT/'local-checks.json',{'module_build':'passed','synthetic_seven_filter_native_smoke':'passed','target_restore_loader':'pending native Torch execution; local amd64 emulation terminated with QEMU SIGSEGV','local_python_checks':8,'qualification_status':'not yet qualified on original graph'})
source_pins={str(p.relative_to(RUNTIME)):sha(p) for p in sorted((RUNTIME/'engine').rglob('*')) if p.is_file() and p.suffix in ('.c','.h','.inc')}
binding={'schema':'reviews-clean-development-qualification.v1','split_manifest_sha256':freeze['manifest_sha256'],'protocol_sha256':sha(STUDY/'protocol/study-protocol.md'),'config_sha256':sha(STUDY/'protocol/config.json'),'module_sha256':sha(KIT/'vector.so'),'queries_sha256':sha(KIT/'queries.jsonl'),'development_source_indices':[r['source_index'] for r in split['assignments'] if r['role']=='development'],'queries':3150,'provider_calls':0,'source_engine_hashes':source_pins,'local_smoke_sha256':sha(KIT/'local-smoke.json'),'historical_source_kit_sha256':expected}
save(KIT/'binding.json',binding)
with (KIT/'SHA256SUMS').open('w') as f:
 for p in sorted(KIT.iterdir()):
  if p.is_file() and p.name!='SHA256SUMS':f.write(sha(p)+'  '+p.name+'\n')
archive=STUDY/'kits/development-runtime-v2.tar.gz'
with tarfile.open(archive,'w:gz') as tar:tar.add(KIT,arcname='development-runtime-v2')
archive.with_suffix('.gz.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
save(STUDY/'freeze/protocol-freeze-v2.json',{'schema':'reviews-clean-study-protocol-freeze.v1','protocol_sha256':binding['protocol_sha256'],'config_sha256':binding['config_sha256'],'split_sha256':freeze['manifest_sha256'],'qualification_archive_sha256':sha(archive),'qualification_module_sha256':binding['module_sha256'],'runtime_status':'local synthetic smoke passed; original-graph Torch return pending','agent_dispatch':'not started; usage reconciliation and original-graph qualification required'})
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'binding':sha(KIT/'binding.json')},indent=2))
