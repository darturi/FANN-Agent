"""Seal only development queries, frozen programs and prior development references."""
import json,hashlib,shutil,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;STUDY=HERE.parent;KIT=STUDY/'kits/agent-policy-qualification-v1';OLD=STUDY/'kits/guard-qualification-v1';EP=STUDY/'development/agent-episode-v2-compact'
sys.path.insert(0,str(EP))
from data import load,choose,encoded,sha
from compile_policies import generate

def save(p,o):p.write_text(json.dumps(o,sort_keys=True,indent=2)+'\n')
def main():
 assert not KIT.exists(),'new version required';KIT.mkdir()
 for line in (OLD/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);assert sha(OLD/n)==h
 oldbind=json.loads((OLD/'binding.json').read_text())
 for n,h in oldbind['source_engine_hashes'].items():assert sha(STUDY/'runtime-parent-v1'/n)==h
 parent=STUDY/'freeze/guarded-parent-selection-v1.json';p=json.loads(parent.read_text());assert p['selected_parent_ef_search']==640 and p['scheduler_gate']=='passed' and p['guard_source_sha256']==sha(HERE/'guard.py')
 verification=json.loads((EP/'continuation-verification.json').read_text());assert verification['eligible_distinct_policies']==3 and verification['total_paid_requests']==3
 export=json.loads((HERE/'eligible-policies.json').read_text());policies=export['policies'];assert export==json.loads((EP/'eligible-policies.json').read_text()) and generate(policies)==(HERE/'engine/src/compiled_study_policies.inc').read_text()
 assert json.loads((HERE/'checks/compiler-parity.json').read_text())['compiled_c_first_stop_cases']==9450
 smoke=None
 for line in (HERE/'checks/smoke-2.log').read_text().splitlines():
  if line.startswith('SMOKE_RECEIPT '):smoke=json.loads(line[len('SMOKE_RECEIPT '):])
 assert smoke and smoke['status']=='passed' and len(smoke['conditions'])==7 and all(c['three_compiled_policy_first_stop_and_output_parity'] for c in smoke['conditions'])
 rows=load();expected={};native={}
 results=STUDY/'returns/job-22684501/results'
 for line in (results/'quality.jsonl').read_text().splitlines():
  r=json.loads(line)
  if r['ef']==640:native[r['id']]=r['native_guard']
 summary=json.loads((EP/'reconciled-summary.json').read_text());eligible={r['policy_sha256'] for r in summary['eligible_distinct_policies']}
 for qid,row in rows.items():
  n=native[qid];r={'id':qid,'checkpoints':list(row['observations'].values()),'native':{'checkpoint':0,'initial':n['initial'],'output':n['output'],'fallback_used':n['fallback_used'],'recall':row['baseline_recall']}}
  for policy in policies:
   assert hashlib.sha256(encoded(policy['rules'])).hexdigest() in eligible
   cp=choose(row,policy);initial=row['proofs'][str(cp)]['output'] if cp else n['initial'];output=initial if cp else n['output']
   r[policy['name']]={'checkpoint':cp or 0,'initial':initial,'output':output,'fallback_used':False if cp else n['fallback_used'],'recall':row['proofs'][str(cp)]['recall'] if cp else row['baseline_recall']}
  expected[qid]=r
 assert len(expected)==3150
 (KIT/'expected.jsonl').write_bytes(b''.join(encoded(expected[qid])+b'\n' for qid in sorted(expected)))
 for name in ('original-package.tar.gz','queries.jsonl','prior-references.jsonl','inherited-package-review.json','config.json','study-protocol.md'):shutil.copyfile(OLD/name,KIT/name)
 for name in ('common.py','guard.py','support.py','experiment.py','run_agent.py','verify_return.py','functions.sql','vector.so','run-on-compute.sh','submit.sh','agent-plan.json','compiled-policies.json','eligible-policies.json'):shutil.copyfile(HERE/name,KIT/name)
 shutil.copyfile(HERE/'README.md',KIT/'README.md');shutil.copyfile(STUDY/'protocol/agent-policy-qualification-amendment-v1.md',KIT/'development-amendment.md');shutil.copyfile(HERE/'checks/verifier-check.json',KIT/'local-verifier-check.json')
 shutil.copyfile(parent,KIT/'parent-freeze.json');save(KIT/'local-smoke.json',smoke);shutil.copyfile(HERE/'checks/compiler-parity.json',KIT/'compiler-parity.json')
 # Source archive retains the exact generated rules and build inputs, no queries/credentials.
 with tarfile.open(KIT/'engine-source.tar.gz','w:gz') as tar:
  for x in sorted((HERE/'engine').rglob('*')):
   if x.is_file() and x.suffix not in ('.o','.so','.bc'):tar.add(x,arcname='engine/'+str(x.relative_to(HERE/'engine')))
 binding={**{k:oldbind[k] for k in ('split_manifest_sha256','development_source_indices','queries','protocol_sha256','config_sha256','historical_source_kit_sha256')},'schema':'three-agent-development-qualification.v1','queries_sha256':sha(KIT/'queries.jsonl'),'module_sha256':sha(KIT/'vector.so'),'guard_source_sha256':sha(KIT/'guard.py'),'prior_references_sha256':sha(KIT/'prior-references.jsonl'),'expected_sha256':sha(KIT/'expected.jsonl'),'agent_plan_sha256':sha(KIT/'agent-plan.json'),'compiled_policies_sha256':sha(KIT/'compiled-policies.json'),'engine_source_sha256':sha(KIT/'engine-source.tar.gz'),'parent_freeze_sha256':sha(parent),'reconciled_pool_freeze_sha256':sha(EP/'reconciled-pool-freeze.json'),'policies':3,'provider_calls':0,'validation_test_queries':0}
 save(KIT/'binding.json',binding)
 (KIT/'SHA256SUMS').write_text(''.join(sha(x)+'  '+x.name+'\n' for x in sorted(KIT.iterdir()) if x.is_file() and x.name!='SHA256SUMS'))
 archive=KIT.with_suffix('.tar.gz')
 with tarfile.open(archive,'w:gz') as tar:tar.add(KIT,arcname=KIT.name)
 archive.with_suffix('.gz.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
 save(STUDY/'freeze/agent-policy-qualification-v1.json',{'status':'sealed development-only qualification/timing kit; original-graph gate pending','archive_sha256':sha(archive),'module_sha256':binding['module_sha256'],'binding_sha256':sha(KIT/'binding.json'),'agent_plan_sha256':binding['agent_plan_sha256'],'parent_freeze_sha256':sha(parent),'proposal_pool_freeze_sha256':binding['reconciled_pool_freeze_sha256'],'policies':3,'development_groups':450,'validation_test_outcomes_opened':False,'provider_calls':0})
 print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive)},indent=2))
if __name__=='__main__':main()
