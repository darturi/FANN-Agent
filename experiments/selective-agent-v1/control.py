"""Durable three-allocation stage submission and provider-free collection."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
from contract import CONFIG,NAME,read,save,sha,replace,accounting

def verify(package,bundle=None):
    from integrity import safe_file
    manifest=read(package/'manifest.json')
    for name,h in manifest['files'].items():
        p=safe_file(package,name)
        if p.is_symlink() or sha(p)!=h:raise ValueError('Package changed: '+name)
    cfg=read(package/'experiment.json')
    fixture=cfg.get('synthetic_only',False)
    if not fixture and not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}',cfg['episode_id']):raise ValueError('Invalid episode identity')
    for k,v in CONFIG.items():
        if fixture and k in {'module_sha256','dimension','row_count'}:continue
        if cfg.get(k)!=v:raise ValueError('Protocol changed: '+k)
    if not fixture and cfg.get('fixture_cases') is not None:raise ValueError('Fixture override in real study')
    if cfg['complete_call_accounting']!=accounting(cfg['stage'],len(read(package/'candidates.json')),cfg.get('fixture_cases') if fixture else None):raise ValueError('Count declaration differs')
    if sha(package/'modules/vector.so')!=cfg['module_sha256']:raise ValueError('Binary identity differs')
    if bundle is not None:
        from verify_patch import check
        check(package,bundle)
        if sha(bundle/'images/runtime.sif')!=cfg['image_sha256']:raise ValueError('Image identity differs')
    return cfg

def command(package,record,extra):
    args=['sbatch','--parsable','--account='+record['account'],'--export=NONE','--kill-on-invalid-dep=yes','--chdir='+str(package)]
    if record.get('constraint'):args+=['--constraint='+record['constraint']]
    return args+extra+[str(package/'slurm/measure.sbatch'),str(package),record['bundle'],record['prepared'],
        record['campaign'],record['workspace'],record['sources'],record['apptainer']]

def dispatch(package,campaign,record,block,dependency=None):
    key='block-'+str(block)
    if key in record['dispatch']:raise ValueError('Existing/unknown dispatch; do not repeat')
    record['dispatch'][key]={'status':'dispatching'};replace(campaign/'submission.json',record)
    extra=['--array='+str(block),'--output='+str(campaign/'logs'/(key+'-%A-%a.log'))]
    if dependency:extra+=['--dependency=afterok:'+dependency]
    try:r=subprocess.run(command(package,record,extra),capture_output=True,text=True)
    except BaseException:
        record['dispatch'][key]={'status':'unknown'};replace(campaign/'submission.json',record);raise
    if r.returncode:
        record['dispatch'][key]={'status':'rejected','returncode':r.returncode,'stderr':r.stderr};replace(campaign/'submission.json',record)
        raise RuntimeError('Scheduler rejected allocation: '+r.stderr)
    if not re.fullmatch(r'[1-9][0-9]*(;torch)?',r.stdout.strip()):
        record['dispatch'][key]={'status':'unknown','stdout':r.stdout};replace(campaign/'submission.json',record)
        raise ValueError('Unknown sbatch result; never resubmit')
    job=r.stdout.strip().split(';')[0];record['jobs'][key]=job
    record['dispatch'][key]={'status':'submitted','job_id':job};replace(campaign/'submission.json',record)
    return job

def reserve_stage(results,cfg,package,campaign):
    """Exclusive creation covers reuploads and crashes before the first sbatch."""
    folder=results/('.'+NAME+'-'+cfg['episode_id']);folder.mkdir(exist_ok=True)
    save(folder/'protocol.json',{'episode_id':cfg['episode_id'],'run_contract_sha256':cfg['run_contract_sha256'],
        'maximum_allocations':9,'module_sha256':cfg['module_sha256']})
    path=folder/(cfg['stage']+'.json')
    if path.exists():raise ValueError('This episode stage is already reserved; inspect its campaign instead of resubmitting')
    save(path,{'campaign':str(campaign),'manifest_sha256':sha(package/'manifest.json'),'reserved_allocations':3})
    if cfg['stage']=='confirmation':
        entitlement=results/('.selective-confirmation-'+cfg['confirmation_entitlement_sha256']+'.json')
        if entitlement.exists():raise ValueError('Confirmation vectors already reserved/consumed')
        save(entitlement,{'episode_id':cfg['episode_id'],'candidate':cfg['primary_hash'],'campaign':str(campaign),
            'status':'consumed_before_dispatch'})

def submit(package,bundle,sources):
    if (package/'submission-binding.json').exists():raise ValueError('Existing binding; use status/collect')
    cfg=verify(package,bundle)
    if cfg.get('synthetic_only'):raise ValueError('Synthetic validation packages cannot be submitted to Torch')
    from protected import check
    protected=check(sources,package)
    account=os.environ['TORCH_SLURM_ACCOUNT']
    if not re.fullmatch(r'torch_pr_[A-Za-z0-9_]+',account):raise ValueError('Use an active Torch account')
    prepared=Path(cfg['source_prepared']);scratch=Path(os.environ['TORCH_SCRATCH_ROOT']);results=Path(os.environ['TORCH_RESULTS_ROOT'])
    apptainer=Path(os.environ.get('TORCH_APPTAINER_BIN','/share/apps/apptainer/bin/apptainer'))
    for p in (package,bundle,sources,prepared,scratch,results,apptainer):
        if not p.is_absolute() or any(s in str(p) for s in (':',',','\n')):raise ValueError('Unsupported container path')
    ready=read(prepared/'READY.json')
    if ready['architecture']!='x86_64' or ready['image_sha256']!=cfg['image_sha256'] or read(prepared/'database-identity.json')!=read(package/'source-index.json'):
        raise ValueError('Prepared database/index differs')
    if not os.access(apptainer,os.X_OK):raise ValueError('Apptainer unavailable')
    scratch.mkdir(parents=True,exist_ok=True);results.mkdir(parents=True,exist_ok=True)
    provisional={'account':account,'constraint':os.environ.get('TORCH_CPU_CONSTRAINT'),'bundle':str(bundle),'sources':str(sources),
        'prepared':str(prepared),'workspace':str(scratch),'campaign':str(results/'dry-run'),'apptainer':str(apptainer)}
    subprocess.run(command(package,provisional,['--test-only','--array=0','--output=/dev/null']),check=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    campaign=Path(tempfile.mkdtemp(prefix='reviews-selective-agent-v1-'+cfg['stage']+'-'+stamp+'.',dir=results))
    workspace=Path(tempfile.mkdtemp(prefix='selective-'+cfg['stage']+'.',dir=scratch));(campaign/'logs').mkdir()
    reserve_stage(results,cfg,package,campaign)
    save(campaign/'protected-source-before.json',protected)
    record={**provisional,'package':str(package),'campaign':str(campaign),'workspace':str(workspace),
        'status':'submitting','jobs':{},'dispatch':{},'stage':cfg['stage'],'episode_id':cfg['episode_id'],
        'accounting':cfg['complete_call_accounting'],'provider_calls':0}
    save(campaign/'submission.json',record)
    save(package/'submission-binding.json',{'campaign':str(campaign),'package_manifest_sha256':sha(package/'manifest.json')})
    known=[]
    try:
        for block in range(3):known.append(dispatch(package,campaign,record,block,known[-1] if known else None))
        record['status']='submitted';replace(campaign/'submission.json',record)
    except BaseException:
        if known:subprocess.run(['scancel',*known],capture_output=True,text=True)
        record['status']='submission_incomplete';replace(campaign/'submission.json',record);raise
    print(json.dumps(record,indent=2))

def bound(package):
    b=read(package/'submission-binding.json')
    if b['package_manifest_sha256']!=sha(package/'manifest.json'):raise ValueError('Submission binding changed')
    campaign=Path(b['campaign']);r=read(campaign/'submission.json')
    if r['package']!=str(package):raise ValueError('Campaign belongs to another package')
    return campaign,r

def status(package):
    cfg=verify(package);campaign,r=bound(package)
    print('Campaign: '+str(campaign));print('Stage: '+r['stage']+'; exactly three allocations; entire episode maximum nine.')
    print(json.dumps({'provider_calls_on_Torch':0,'accounting':r['accounting'],'dispatch':r['dispatch']},indent=2))
    for i in range(3):
        for n in ('progress.json','status.json','failure.json','host-failure.json','host-exit.json'):
            p=campaign/'blocks'/('block-'+str(i))/n
            if p.exists():print('Block '+str(i)+' '+n+': '+json.dumps(read(p)))
    if r['jobs']:
        ids=','.join(r['jobs'].values());subprocess.run(['sacct','-j',ids,'--format=JobID,State,ExitCode,Elapsed']);subprocess.run(['squeue','-j',ids])

def collect(package):
    cfg=verify(package);campaign,r=bound(package);archive=Path(str(campaign)+'.tar.gz')
    if archive.exists():
        if sha(archive)!=Path(str(archive)+'.sha256').read_text().split()[0]:raise ValueError('Archive changed')
        print('Existing verified archive: '+str(archive));return
    complete=all((campaign/'blocks'/('block-'+str(i))/'host-exit.json').exists() and not read(campaign/'blocks'/('block-'+str(i))/'host-exit.json')['exit_code'] for i in range(3))
    failed=any((campaign/'blocks'/('block-'+str(i))/'host-exit.json').exists() and read(campaign/'blocks'/('block-'+str(i))/'host-exit.json')['exit_code'] for i in range(3))
    if not complete and not failed:raise ValueError('Stage still pending; use status')
    if complete:
        cmd=[r['apptainer'],'exec','--cleanenv','--containall','--no-home','--pwd','/results',
            '--bind',str(package)+':/patch:ro','--bind',str(campaign)+':/results:rw',
            '--env','PYTHONPATH=/patch:/patch/vendor','--env','PYTHONDONTWRITEBYTECODE=1',
            str(Path(r['bundle'])/'images/runtime.sif'),'python','/patch/report.py','/results','/patch']
        subprocess.run(cmd,check=True)
    else:
        (campaign/'analysis').mkdir(exist_ok=True)
        save(campaign/'analysis/performance.json',{'status':'incomplete_or_failed','stage':cfg['stage'],
            'candidate_qualification':{},'provider_calls':0,'canonical_acceptance_established':False,'ab_comparison':cfg['ab_comparison']})
    with tarfile.open(archive,'x:gz') as tar:
        for p in sorted(campaign.rglob('*')):
            if p.is_symlink():raise ValueError('Symlink in returned results')
            if p.is_file():tar.add(p,arcname=campaign.name+'/'+str(p.relative_to(campaign)),recursive=False)
    save(Path(str(archive)+'.sha256'),sha(archive)+'  '+archive.name+'\n',raw=True)
    print(json.dumps(read(campaign/'analysis/performance.json').get('candidate_qualification',{}),indent=2))
    print('Download archive and checksum: '+str(archive))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['submit','status','collect']);p.add_argument('paths',nargs='*');a=p.parse_args()
    package=Path(__file__).resolve().parent
    if a.command=='submit':
        if len(a.paths)!=2:p.error('submit ORIGINAL_BUNDLE SOURCE_RESULTS_ROOT')
        submit(package,*[Path(s).resolve() for s in a.paths])
    elif a.paths:p.error('status/collect use the persistent binding; no shell variable needed')
    elif a.command=='status':status(package)
    else:collect(package)
