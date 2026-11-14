"""Package the unguarded serving redesign without opening any holdout inputs."""
import json,shutil,tarfile
from pathlib import Path
from common import sha,write
from experiment import FAMILIES,LABELS,BASE,SEED
HERE=Path(__file__).resolve().parent;STUDY=HERE.parent;OLD=STUDY/'kits/agent-policy-qualification-v1';KIT=STUDY/'kits/unguarded-development-v1'
def main():
 assert not KIT.exists(),'use a fresh sealed kit version'
 for line in (OLD/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);assert sha(OLD/n)==h
 prior=json.loads((OLD/'binding.json').read_text());freeze=json.loads((STUDY/'freeze/agent-policy-qualification-v1.json').read_text());assert freeze['module_sha256']==sha(HERE/'vector.so')==prior['module_sha256']
 split=STUDY/'splits/split-manifest.json';assert sha(split)==prior['split_manifest_sha256'];assert json.loads((HERE/'checks/saved-output-rescore.json').read_text())['source_receipt_sha256']==sha(STUDY/'returns/job-22928562/results/receipt.json')
 plan={'schema':'unguarded-development.v1','parent_ef_search':640,'native_ef_grid':[40,80,160,320,640],'iterative_scan':'off','families':{n:{'ef':v[0],'arm':v[1]} for n,v in FAMILIES.items()},'labels':list(LABELS),'williams_base':list(BASE),'schedule_seed':SEED,'groups':450,'conditions':[-1,743,527,310,192,108,32],'queries':3150,'quality_family_results':28350,'offline_exact_reference_queries':3150,'capture_queries':3150,'timed_requests':113400,'warmup_requests':2520,'planned_attempts':150570,'query_attempt_cap':160000,'timing_epochs':2,'exact_serving_calls':0,'exact_reference_connections_closed_before_approximate_phases':True,'short_outputs':'return unchanged; score missing neighbors as misses','95pct_absolute_recall_floor':'diagnostic only; not a gate','relative_quality':'zero query losses vsactual raw native640 in every condition','private_postgres_max_connections':32,'resource':{'cpus':4,'memory_gib':48,'wall_hours':8},'provider_calls':0,'validation_test_queries':0,'policy_provenance':'three unchanged programs generated using guarded development labels; no fresh agent episode','confirmatory_claim':False,'final_policy_selected':False}
 write(HERE/'agent-plan.json',plan)
 smoke=None
 for line in (HERE/'checks/smoke-capacity-2.log').read_text().splitlines():
  if line.startswith('SMOKE_RECEIPT '):smoke=json.loads(line[len('SMOKE_RECEIPT '):])
 assert smoke and smoke['status']=='passed' and len(smoke['conditions'])==7 and smoke['eighteen_readers_plus_keeper_opened'] and smoke['private_max_connections']==32
 assert all(len(c['short_results_unmodified'])==5 and all(v['ann_calls']==1 and v['exact_serving_calls']==0 and v['returned_count']<10 for v in c['short_results_unmodified']) for c in smoke['conditions'])
 KIT.mkdir()
 for n in ('original-package.tar.gz','queries.jsonl','prior-references.jsonl','inherited-package-review.json','engine-source.tar.gz','compiler-parity.json'):shutil.copyfile(OLD/n,KIT/n)
 for n in ('common.py','support.py','serving.py','startup.py','experiment.py','run_unguarded.py','verify_return.py','functions.sql','vector.so','compiled-policies.json','eligible-policies.json','expected.jsonl','agent-plan.json','run-on-compute.sh','submit.sh','README.md'):shutil.copyfile(HERE/n,KIT/n)
 shutil.copyfile(STUDY/'protocol/study-protocol-unguarded-v1.md',KIT/'study-protocol.md');shutil.copyfile(STUDY/'protocol/config-unguarded-v1.json',KIT/'config.json');shutil.copyfile(HERE/'checks/saved-output-rescore.json',KIT/'saved-output-rescore.json');write(KIT/'local-smoke.json',smoke)
 write(KIT/'local-checks.json',{'module':'unchanged x86_64 module qualified in job22928562','compiled_c_first_stop_cases':9450,'unguarded_serving_unit_checks':10,'all_seven_condition_synthetic_postgresql_smoke':'passed; short native/noop/policy outputs unchanged; exact only scores separately','reader_capacity':'18 concurrent readers plus keeper passed under max_connections32','original_graph_unguarded_timing':'pending','holdout_access':False})
 binding={'schema':'unguarded-development-binding.v1','split_manifest_sha256':sha(split),'queries_sha256':sha(KIT/'queries.jsonl'),'development_source_indices':prior['development_source_indices'],'queries':3150,'module_sha256':sha(KIT/'vector.so'),'compiled_policies_sha256':sha(KIT/'compiled-policies.json'),'serving_source_sha256':sha(KIT/'serving.py'),'startup_source_sha256':sha(KIT/'startup.py'),'protocol_sha256':sha(KIT/'study-protocol.md'),'config_sha256':sha(KIT/'config.json'),'expected_sha256':sha(KIT/'expected.jsonl'),'prior_references_sha256':sha(KIT/'prior-references.jsonl'),'agent_plan_sha256':sha(KIT/'agent-plan.json'),'engine_source_sha256':sha(KIT/'engine-source.tar.gz'),'prior_agent_qualification_receipt_sha256':sha(STUDY/'returns/job-22928562/results/receipt.json'),'original_agent_pool_freeze_sha256':sha(STUDY/'development/agent-episode-v2-compact/reconciled-pool-freeze.json'),'provider_calls':0,'validation_test_queries':0,'exact_serving_calls':0,'historical_guarded_experiments_preserved':True}
 write(KIT/'binding.json',binding)
 (KIT/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(KIT.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
 from check_verifier import run as check_verifier
 check_verifier(KIT)
 shutil.copyfile(HERE/'checks/verifier-check.json',KIT/'local-verifier-check.json')
 (KIT/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(KIT.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
 archive=KIT.with_suffix('.tar.gz')
 with tarfile.open(archive,'w:gz') as t:t.add(KIT,arcname=KIT.name)
 archive.with_suffix('.gz.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
 write(STUDY/'freeze/unguarded-development-v1.json',{'status':'sealed_unguarded_development_kit_pending_Torch_return','archive_sha256':sha(archive),'binding_sha256':sha(KIT/'binding.json'),'protocol_sha256':binding['protocol_sha256'],'config_sha256':binding['config_sha256'],'module_sha256':binding['module_sha256'],'serving_source_sha256':binding['serving_source_sha256'],'startup_source_sha256':binding['startup_source_sha256'],'plan_sha256':binding['agent_plan_sha256'],'split_sha256':sha(split),'quality_reference':'actual unguarded native640','partial_output_handling':'score normally; no serving completion','validation_test_outcomes_opened':False,'provider_calls':0,'exact_serving_calls':0})
 print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'planned_attempts':150570},indent=2))
if __name__=='__main__':main()
