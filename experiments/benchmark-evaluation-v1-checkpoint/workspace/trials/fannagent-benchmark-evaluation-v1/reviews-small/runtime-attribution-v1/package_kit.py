"""Seal one development-only fixed reader/CPU/work diagnostic."""
import json,shutil,tarfile
from pathlib import Path
from common import sha,write
from design import FAMILIES,ARMS,BLOCKS,BASE,SEED,TIMING_ATTEMPTS,WORK_ATTEMPTS,TOTAL_ATTEMPTS
HERE=Path(__file__).resolve().parent;STUDY=HERE.parent;OLD=STUDY/'kits/unguarded-development-v1';KIT=STUDY/'kits/reader-attribution-v1'
def main():
 assert not KIT.exists(),'use a fresh version'
 for line in (OLD/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);assert sha(OLD/n)==h
 old=json.loads((OLD/'binding.json').read_text());assert sha(HERE/'timing-module.so')==old['module_sha256'] and sha(HERE/'serving.py')==old['serving_source_sha256'] and sha(HERE/'work-module.so')!=old['module_sha256']
 protocol=STUDY/'protocol/reader-attribution-v1.md';split=STUDY/'splits/split-manifest.json';assert sha(split)==old['split_manifest_sha256']
 receipts={}
 for phase,log in (('timing','smoke-timing.log'),('work','smoke-work-kernel-cpu.log')):
  for line in (HERE/'checks'/log).read_text().splitlines():
   if line.startswith('SMOKE_RECEIPT '):receipts[phase]=json.loads(line[len('SMOKE_RECEIPT '):])
  assert receipts[phase]['status']=='passed' and len(receipts[phase]['conditions'])==7 and all(c['all_roles_per_backend']==2 for c in receipts[phase]['conditions'])
 assert all(c['noop_graph_counters_equal_native'] for c in receipts['work']['conditions'])
 plan={'schema':'reader-cpu-work-attribution.v1','parent_ef_search':640,'families':list(FAMILIES),'arms':ARMS,'blocks':list(BLOCKS),'backend_readers_per_filter':20,'roles_per_backend':5,'repeats_per_role_backend':2,'allowed_physical_cpus':4,'williams_base':list(BASE),'schedule_seed':SEED,'groups':450,'conditions':[-1,743,527,310,192,108,32],'timing_module':'unchanged original module; zero added counters','work_module':'separate observation-only module; its times never enter performance estimates','timed_requests':630000,'warmup_requests':14000,'timing_quality_searches':15750,'instrumented_work_queries':15750,'offline_reference_exact_queries':6300,'exact_serving_calls':0,'phase_attempts':{'timing':TIMING_ATTEMPTS,'work':WORK_ATTEMPTS},'planned_attempts':TOTAL_ATTEMPTS,'query_attempt_cap':750000,'memory_gib':48,'wall_hours':8,'provider_calls':0,'validation_test_queries':0,'purpose':'bounded diagnostic, not performance promotion or model rescue','negative_disposition':'preserve valid negative/inconclusive result; if policy cost benefit is weak, revisit agent evidence/objective in separate authorized version without holdout feedback'}
 write(HERE/'agent-plan.json',plan);KIT.mkdir()
 for n in ('original-package.tar.gz','queries.jsonl','prior-references.jsonl','inherited-package-review.json','compiler-parity.json','eligible-policies.json','compiled-policies.json','expected.jsonl'):shutil.copyfile(OLD/n,KIT/n)
 for n in ('common.py','support.py','serving.py','startup.py','sessions.py','design.py','experiment.py','run_diagnostic.py','verify_return.py','analyse.py','functions.sql','work-functions.sql','timing-module.so','work-module.so','run-on-compute.sh','submit.sh','agent-plan.json','work-source-change.json','README.md'):shutil.copyfile(HERE/n,KIT/n)
 shutil.copyfile(OLD/'config.json',KIT/'base-config.json');shutil.copyfile(OLD/'study-protocol.md',KIT/'base-study-protocol.md')
 shutil.copyfile(protocol,KIT/'diagnostic-protocol.md');write(KIT/'local-smoke.json',receipts)
 with tarfile.open(KIT/'observer-source.tar.gz','w:gz') as tar:
  for p in sorted((HERE/'engine').rglob('*')):
   if p.is_file() and p.suffix not in ('.o','.so','.bc'):tar.add(p,arcname='engine/'+str(p.relative_to(HERE/'engine')))
 graph=json.loads((STUDY/'returns/job-23045686/results/receipt.json').read_text())['graph']
 binding={'schema':'reader-attribution-binding.v1','split_manifest_sha256':sha(split),'queries_sha256':sha(KIT/'queries.jsonl'),'development_source_indices':old['development_source_indices'],'graph':graph,'timing_module_sha256':sha(KIT/'timing-module.so'),'work_module_sha256':sha(KIT/'work-module.so'),'serving_source_sha256':sha(KIT/'serving.py'),'startup_source_sha256':sha(KIT/'startup.py'),'compiled_policies_sha256':sha(KIT/'compiled-policies.json'),'agent_plan_sha256':sha(KIT/'agent-plan.json'),'diagnostic_protocol_sha256':sha(KIT/'diagnostic-protocol.md'),'original_unguarded_protocol_sha256':sha(KIT/'base-study-protocol.md'),'original_unguarded_config_sha256':sha(KIT/'base-config.json'),'observer_source_sha256':sha(KIT/'observer-source.tar.gz'),'expected_sha256':sha(KIT/'expected.jsonl'),'prior_references_sha256':sha(KIT/'prior-references.jsonl'),'prior_unguarded_receipt_sha256':sha(STUDY/'returns/job-23045686/results/receipt.json'),'provider_calls':0,'validation_test_queries':0,'exact_serving_calls':0}
 write(KIT/'binding.json',binding)
 def sums():(KIT/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(KIT.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
 sums()
 from check_verifier import run as check
 check(KIT);shutil.copyfile(HERE/'checks/verifier-check.json',KIT/'local-verifier-check.json');sums()
 archive=KIT.with_suffix('.tar.gz')
 with tarfile.open(archive,'w:gz') as t:t.add(KIT,arcname=KIT.name)
 archive.with_suffix('.gz.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
 write(STUDY/'freeze/reader-attribution-v1.json',{'status':'fixed_development_diagnostic_sealed_pending_Torch','archive_sha256':sha(archive),'binding_sha256':sha(KIT/'binding.json'),'timing_module_sha256':binding['timing_module_sha256'],'work_module_sha256':binding['work_module_sha256'],'protocol_sha256':binding['diagnostic_protocol_sha256'],'split_sha256':sha(split),'planned_attempts':TOTAL_ATTEMPTS,'provider_calls':0,'validation_test_outcomes_opened':False,'agent_outcome':'no established robust latency success; unchanged programs; negative/inconclusive result is valid','purpose':'single attribution diagnostic, no automatic resubmission/promotion'})
 print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'planned_attempts':TOTAL_ATTEMPTS},indent=2))
if __name__=='__main__':main()
