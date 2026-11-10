"""Immutable stage packages; confirmation vectors are read only after the gate."""
from pathlib import Path
import json
import shutil
import tarfile
from contract import HERE,ROOT,SOURCE,CAMPAIGN,CONFIG,NAME,AB,read,save,sha,lines,digest,accounting

RUNTIME_FILES=['contract.py','policy.py','execution.py','runtime.py','job.py','control.py','report.py',
    'fd_contract.py','fd_execution.py','fd_policy_tools.py','legacy_contract.py','legacy_execution.py',
    'runtime_base.py','reference_backend.py','database.py','design.py','preservation.py','prior_protected.py',
    'legacy_protected.py','integrity.py','verify_patch.py','protected.py','study_stats.py','no_models.py']

def verified_measurement(run,store,stage):
    binding=store.get('measurement_'+stage)
    if not binding:raise ValueError('Import and independently verify '+stage+' measurements first')
    path=run/'measurements'/stage/'performance.json'
    if sha(path)!=binding['performance_sha256']:raise ValueError('Imported measurements changed')
    result=read(path)
    if result['status']!='verified' or result['stage']!=stage or result['episode_id']!=store.get('episode_id'):raise ValueError('Different measurements')
    package=Path(store.get('packages')[stage]['path'])
    from control import verify
    verify(package)
    if result['package_manifest_sha256']!=sha(package/'manifest.json'):raise ValueError('Measured package changed')
    return result

def selection(run,store,stage):
    if not store.get('phase_done_A'):raise ValueError('Agent did not explicitly freeze initial proposals')
    if stage=='pilot':
        lock=read(run/'proposal-lock.json')
        if lock['exports']!=store.get('exports_A'):raise ValueError('Proposal lock changed')
        return lock['exports']
    if not store.get('phase_done_B'):raise ValueError('The agent has not finished its single feedback response')
    final=read(run/'agent-final.json');chosen=final['selection']
    if chosen is None:raise ValueError('Agent abstained; no more jobs')
    identity=chosen['semantic_hash']
    if chosen!=(store.get('exports_A',{})|store.get('exports_B',{})).get(identity):raise ValueError('Final export changed')
    if stage=='revision':
        if final['status']!='awaiting_revision_measurement':raise ValueError('No agent revision to measure')
    elif stage=='confirmation':
        source='revision' if final['status']=='awaiting_revision_measurement' else 'pilot'
        measurement=verified_measurement(run,store,source)
        if not measurement['candidate_qualification'].get(identity,{}).get('development_qualifies'):
            raise ValueError('Final agent candidate failed development qualification; no substitution or confirmation')
    else:raise ValueError('Unknown stage')
    return {identity:chosen}

def build(run,store,stage):
    from evidence import source_config,historical_state
    from policy import validate
    run=Path(run);before=historical_state();source_cfg=source_config();candidates=selection(run,store,stage)
    for h,c in candidates.items():
        if validate(c['policy'],source_cfg)[1]!=h:raise ValueError('Export semantic hash differs')
    old=store.get('packages',{})
    if stage in old:
        from control import verify
        target=Path(old[stage]['path']);verify(target)
        if sha(target/'manifest.json')!=old[stage]['manifest_sha256']:raise ValueError('Stage package changed')
        return target
    episode=store.get('episode_id');name=NAME+'-'+stage+'-'+episode
    parent=run/'packages'/stage;parent.mkdir(parents=True,exist_ok=True);target=parent/name
    if target.exists():raise ValueError('Partial package exists; inspect and preserve it')
    target.mkdir();(target/'inputs').mkdir();(target/'modules').mkdir();(target/'slurm').mkdir()
    for namefile in RUNTIME_FILES:shutil.copyfile(HERE/namefile,target/namefile)
    shutil.copytree(SOURCE/'vendor',target/'vendor',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    core=HERE/'vendor/fannagent' if (HERE/'vendor/fannagent').exists() else ROOT/'agent/src/fannagent'
    shutil.copytree(core,target/'vendor/fannagent',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for namefile in ('source-index.json','protected-campaigns.json','additional-protected.json'):
        shutil.copyfile(SOURCE/namefile,target/namefile)
    additional=read(target/'additional-protected.json')
    additional[CAMPAIGN.name]={**read(run/'private/source-pins.json')['raw'],'build/vector.so':CONFIG['module_sha256'],
        'fit/fit-lock.json':sha(CAMPAIGN/'fit/fit-lock.json')}
    (target/'additional-protected.json').unlink();save(target/'additional-protected.json',additional)
    shutil.copyfile(CAMPAIGN/'build/vector.so',target/'modules/vector.so')
    shutil.copyfile(SOURCE/'inputs/original-learning-receipt.json',target/'inputs/original-learning-receipt.json')
    development=lines(run/'private/development.jsonl')
    fixtures=[next(i for i in development if i['query']['id'].endswith('-'+f)) for f in CONFIG_FILTERS()]
    save(target/'inputs/qualification.jsonl',''.join(json.dumps(i,sort_keys=True)+'\n' for i in fixtures),raw=True)
    if stage=='confirmation':
        # No holdout values are opened before final selection and the measured development gate.
        queries=lines(SOURCE/'inputs/evaluation.jsonl')
        if len(queries)!=180 or len({i['group'] for i in queries})!=60 or {i['group'] for i in queries}&{i['group'] for i in development}:
            raise ValueError('Confirmation entitlement differs/overlaps')
        save(target/'primary-lock.json',{'candidate':next(iter(candidates)),'agent_final_sha256':sha(run/'agent-final.json'),
            'run_contract_sha256':sha(run/'contract.json'),'module_sha256':CONFIG['module_sha256'],
            'development_measurement':store.get('measurement_revision') or store.get('measurement_pilot')})
    else:
        queries=development;shutil.copyfile(run/'evidence/corpus.json',target/'inputs/development-evidence.json')
    save(target/'inputs/queries.jsonl',''.join(json.dumps(i,sort_keys=True)+'\n' for i in queries),raw=True)
    save(target/'candidates.json',candidates)
    cfg={**source_cfg,**CONFIG,'stage':stage,'episode_id':episode,'run_contract_sha256':sha(run/'contract.json'),
        'scope':'Single agent engineering episode; one measured feedback round and one-shot workload confirmation; canonical acceptance separate',
        'new_fits':'None on Torch; host fitting and model calls have separate provenance',
        'synthetic_only':store.get('synthetic_only',False),'complete_call_accounting':accounting(stage,len(candidates)),
        'provider_calls_allowed':0,'confirmation_queries_allowed':180 if stage=='confirmation' else 0,
        'primary_hash':next(iter(candidates)) if stage!='pilot' else None,
        'confirmation_entitlement_sha256':sha(SOURCE/'inputs/evaluation.jsonl') if stage=='confirmation' else None,
        'source_preservation':before}
    save(target/'experiment.json',cfg)
    script='''#!/usr/bin/env bash
#SBATCH --job-name=selective-policy
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
umask 077
exec python3 "$1/job.py" "$@"
'''
    save(target/'slurm/measure.sbatch',script,raw=True)
    for n in ('README.md','TOOLS.md'):
        shutil.copyfile(HERE/n,target/n)
    save(target/'manifest.json',{'version':NAME,'original_manifest_sha256':read(SOURCE/'manifest.json')['original_manifest_sha256'],
        'files':{str(p.relative_to(target)):sha(p) for p in sorted(target.rglob('*')) if p.is_file()},'provider_calls_allowed':0})
    archive=parent/(name+'.tar.gz')
    with tarfile.open(archive,'x:gz') as tar:
        for p in sorted(target.rglob('*')):
            if p.is_file():tar.add(p,arcname=name+'/'+str(p.relative_to(target)),recursive=False)
    save(Path(str(archive)+'.sha256'),sha(archive)+'  '+archive.name+'\n',raw=True)
    commands=commands_for(run,target,archive,stage)
    save(parent/'COMMANDS.txt',commands,raw=True)
    old[stage]={'path':str(target),'manifest_sha256':sha(target/'manifest.json'),'archive':str(archive),
        'commands':str(parent/'COMMANDS.txt')};store.set('packages',old)
    if before!=historical_state():raise ValueError('Historical ledger changed')
    return target

def CONFIG_FILTERS():
    from contract import FILTERS
    return FILTERS

def commands_for(run,target,archive,stage):
    package=target.name;controller=HERE/'study.py';python=ROOT/'agent/.venv/bin/python'
    return f'''MAC: verify and upload this frozen {stage} package.
(
  set -euo pipefail
  cd '{archive.parent}'
  shasum -a 256 -c '{archive.name}.sha256'
  scp -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519 -o StrictHostKeyChecking=yes -o UpdateHostKeys=no \\
    '{archive.name}' '{archive.name}.sha256' dar579@dtn012.hpc.nyu.edu:/home/dar579/
)

TORCH LOGIN TERMINAL: extract and submit ONCE.
(
  set -euo pipefail
  cd /home/dar579
  sha256sum -c '{archive.name}.sha256'
  test ! -e '{package}'
  tar -xzf '{archive.name}'
  source /home/dar579/torch-reviews-first/torch.env
  export TORCH_SLURM_ACCOUNT=torch_pr_288_courant
  python3 '/home/dar579/{package}/control.py' submit /home/dar579/torch-reviews-first /home/dar579/torch-reviews-results
)

TORCH: works after a fresh login; checks all three allocations.
python3 /home/dar579/{package}/control.py status

TORCH: after completion, collect full raw results and checksum.
python3 /home/dar579/{package}/control.py collect

MAC: download the exact bound campaign, then independently analyze it.
(
  set -euo pipefail
  cd '{run}'
  torch_options=(-o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519 -o StrictHostKeyChecking=yes -o UpdateHostKeys=no)
  torch_run="$(ssh "${{torch_options[@]}}" dar579@dtn012.hpc.nyu.edu 'cat /home/dar579/{package}/submission-binding.json' | '{python}' -c 'import json,sys; print(json.load(sys.stdin)["campaign"])')"
  scp "${{torch_options[@]}}" "dar579@dtn012.hpc.nyu.edu:${{torch_run}}.tar.gz" "dar579@dtn012.hpc.nyu.edu:${{torch_run}}.tar.gz.sha256" .
  shasum -a 256 -c "$(basename "$torch_run").tar.gz.sha256"
  '{python}' '{controller}' ingest --run '{run}' --stage {stage} --archive "${{torch_run##*/}}.tar.gz"
)

All Torch phases make zero model calls. Final recall unchanged. Original A/B inconclusive.
'''
