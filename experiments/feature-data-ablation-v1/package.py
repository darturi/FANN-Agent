"""Assemble a sealed model-free Torch package from qualified local inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
from contract import CONFIG,NAME,accounting,read,save,sha,digest
from native_patch import patch_engine,patch_adapter

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SEALED=ROOT/'trials/torch-reviews-results/four-condition-training-v1/torch-four-condition-training-v1'
ORIGINAL=ROOT/'trials/torch-reviews-policy-learning'
CATALOG=ROOT/'trials/morevec-reviews-durable-bounded/studies/prepared-20261012T040319Z/run/workspace/artifacts/6f23faeb4d4b6451d028d1dab117ba4e5b742a4be3082e4967b83d0a8e9d97bb.json'


def vector_hash(q):
    return hashlib.sha256(struct.pack('<'+'f'*len(q['vector']),*q['vector'])).hexdigest()


def inventory():
    catalog=read(CATALOG)
    if digest(catalog)!='6f23faeb4d4b6451d028d1dab117ba4e5b742a4be3082e4967b83d0a8e9d97bb':raise ValueError('Development catalog changed')
    prior=read(ORIGINAL/'inputs/split-provenance.json');groups={}
    for item in catalog['items']:groups.setdefault(item['group'],[]).append(item)
    if len(groups)!=450:raise ValueError('Original development inventory differs')
    seen=set()
    for group,items in groups.items():
        if len(items)!=3 or {i['query']['id'].rsplit('-',1)[-1] for i in items}!=set(CONFIG['filters']):raise ValueError('Filter inventory differs')
        hashes={vector_hash(i['query']) for i in items}
        if len(hashes)!=1 or next(iter(hashes)) in seen:raise ValueError('Independent vector inventory contains duplication')
        seen.update(hashes)
    original=sorted(g for g,role in prior['selection'].items() if role=='learning')
    excluded=set(prior['excluded_previously_used_groups'])|set(prior['selection'])
    remaining=sorted(set(groups)-excluded,key=lambda g:digest([CONFIG['seed'],'feature-data-v1',g]))
    if len(original)!=100 or len(remaining)!=197:raise ValueError('Unexposed development inventory differs')
    selected={'original_learning':original,'additional_learning':remaining[:60],
              'calibration':remaining[60:100],'evaluation':remaining[100:160],'reserved':remaining[160:]}
    chosen={}
    for role,identifiers in selected.items():
        chosen[role]=[{'role':role,'catalog_group':g,'group':i['query']['id'].rsplit('-',1)[0],
                       'query':{**i['query'],'filter':i['query'].get('filter')}}
                      for g in identifiers for i in groups[g]] if role!='reserved' else []
    all_groups=[g for values in selected.values() for g in values]
    if len(set(all_groups))!=len(all_groups):raise ValueError('Split groups overlap')
    old={q['query']['id']:q['query'] for q in read_lines(SEALED/'inputs/queries.jsonl')}
    if {r['query']['id']:r['query'] for r in chosen['original_learning']}!=old:raise ValueError('Original 100 learning vectors changed')
    provenance={'development_catalog_sha256':sha(CATALOG),'development_catalog_content_hash':digest(catalog),
      'eligible_unused_vectors':197,'selection_seed':CONFIG['seed'],'selected_catalog_groups':selected,
      'vector_hash_by_catalog_group':{g:vector_hash(groups[g][0]['query']) for g in all_groups},
      'original_exclusions_sha256':sha(ORIGINAL/'inputs/split-provenance.json'),
      'size_change_note':'Expanded learning pool is 160, not proposed 300: only 197 unused development vectors are available before preserving disjoint calibration/evaluation and 37 reserved vectors.',
      'canonical_calibration_or_test_read':False,'consumed_confirmation_used':False}
    return chosen,provenance


def read_lines(p):
    with p.open() as handle:
        return [json.loads(line) for line in handle]


def financial_state():
    old=ROOT/'trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix'
    code="import sys,json;sys.path.insert(0,sys.argv[1]);from build import check_sources;from common import digest;s,l,c=check_sources();print(json.dumps({'source_manifest':s,'charge_records':len(c),'charges_sha256':digest(c),'scientific_state_sha256':l['ledger_scientific_state_sha256']}))"
    return json.loads(subprocess.run([sys.executable,'-c',code,str(old)],check=True,capture_output=True,text=True).stdout)


def build(output):
    before=financial_state()
    if sha(SEALED/'manifest.json')!='6a76b56b91aa138a28c48d5b4868742766de843b4038d034d4f8304b84eacc80':raise ValueError('Qualified source manifest differs')
    for name,h in read(SEALED/'manifest.json')['files'].items():
        if sha(SEALED/name)!=h:raise ValueError('Qualified source changed: '+name)
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True);target=output/NAME
    if target.exists():raise ValueError('Preserve existing package; use a fresh output directory')
    target.mkdir()
    for name in ('design.py','runtime_base.py','reference_backend.py','preservation.py','prior_protected.py',
                 'legacy_protected.py','integrity.py','verify_patch.py','protected-campaigns.json','study_stats.py','source-index.json'):
        shutil.copyfile(SEALED/name,target/name)
    for p in HERE.glob('*.py'):
        if p.name not in ('package.py','test_study.py','native_integration.py'):shutil.copyfile(p,target/p.name)
    for name in ('README.md','COMMANDS.txt'):
        if (HERE/name).exists():shutil.copyfile(HERE/name,target/name)
    shutil.copytree(SEALED/'engine',target/'engine');patch_engine(target/'engine')
    shutil.copytree(SEALED/'vendor',target/'vendor',ignore=shutil.ignore_patterns('__pycache__','*.pyc'));patch_adapter(target/'vendor/fannagent_pgvector')
    (target/'inputs').mkdir()
    for name in ('original-learning-receipt.json','split-provenance.json','budget-receipt.json','training-640-light.jsonl','native-results.json'):
        shutil.copyfile(SEALED/'inputs'/name,target/'inputs'/name)
    selected,split=inventory();save(target/'inputs/ablation-split.json',split)
    partitions=[selected['original_learning'],selected['additional_learning']+selected['calibration']]
    for i,items in enumerate(partitions):save(target/'inputs'/('acquire-'+str(i)+'.jsonl'),''.join(json.dumps(r,sort_keys=True)+'\n' for r in items),raw=True)
    save(target/'inputs/evaluation.jsonl',''.join(json.dumps(r,sort_keys=True)+'\n' for r in selected['evaluation']),raw=True)
    protected=read(SEALED/'additional-protected.json')
    campaign=ROOT/'trials/torch-reviews-results/reviews-four-condition-training-v1-20261022T032823Z.qx3frkhp'
    protected[campaign.name]={**read(campaign/'analysis/verification.json')['raw_files_sha256']}
    save(target/'additional-protected.json',protected)
    old=read(SEALED/'experiment.json')
    cfg={**CONFIG,'base_feature_names':old['base_feature_names'],
         'static_feature_names':old['base_feature_names']+__import__('contract').LEGACY_EXTRA,
         'complete_call_accounting':accounting(),'source_preservation':before,
         'source_query_method_sha256':old['source_query_method_sha256'],
         'adapted_query_method_sha256':old['adapted_query_method_sha256'],
         'source_checkpoint':{'original_sealed_manifest_sha256':sha(SEALED/'manifest.json')},
         'query_file_sha256':{p.name:sha(p) for p in (target/'inputs').glob('*.jsonl')}}
    save(target/'experiment.json',cfg)
    for phase in ('build','acquire','fit','evaluate','measure'):
        script=f'''#!/usr/bin/env bash
#SBATCH --job-name=fd-{phase}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
umask 077
exec python3 "$1/job.py" {phase} "$@"
'''
        save(target/'slurm'/(phase+'.sbatch'),script,raw=True)
    manifest={'version':NAME,'original_manifest_sha256':read(SEALED/'manifest.json')['original_manifest_sha256'],
              'files':{str(p.relative_to(target)):sha(p) for p in sorted(target.rglob('*')) if p.is_file()},
              'provider_calls_allowed':0,'confirmation_queries_allowed':0}
    save(target/'manifest.json',manifest)
    archive=output/(NAME+'.tar.gz')
    with tarfile.open(archive,'x:gz') as tar:
        for p in sorted(target.rglob('*')):
            if p.is_file():tar.add(p,arcname=NAME+'/'+str(p.relative_to(target)),recursive=False)
    save(Path(str(archive)+'.sha256'),sha(archive)+'  '+archive.name+'\n',raw=True)
    if before!=financial_state():raise ValueError('Original financial/scientific state changed')
    print(json.dumps({'package':str(target),'archive':str(archive),'archive_sha256':sha(archive),
       'archive_bytes':archive.stat().st_size,'accounting':accounting(),'source_preservation':before},indent=2))
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'trials/torch-reviews-results/feature-data-ablation-v1')
    args=parser.parse_args();build(args.output)
