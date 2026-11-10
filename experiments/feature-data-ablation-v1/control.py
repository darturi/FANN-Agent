"""Durable staged submission. advance never schedules past a failed gate."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
from contract import CONFIG,NAME,AB,read,save,sha,encoded


def verify(package,bundle=None):
    manifest=read(package/'manifest.json')
    for name,h in manifest['files'].items():
        p=package/name
        if p.is_symlink() or not p.is_file() or sha(p)!=h:raise ValueError('Package changed: '+name)
    cfg=read(package/'experiment.json')
    for name,value in CONFIG.items():
        if cfg.get(name)!=value:raise ValueError('Declared design changed: '+name)
    if bundle is not None:
        from verify_patch import check
        check(package,bundle)
        if sha(bundle/'images/runtime.sif')!=cfg['image_sha256']:raise ValueError('Pinned runtime image differs')
    return cfg


def persist(path,data):
    temp=path.with_name('.'+path.name+'.tmp');temp.write_bytes(encoded(data));temp.replace(path)


def identity(text):
    text=text.strip()
    if not re.fullmatch(r'[1-9][0-9]*(;torch)?',text):raise ValueError('Unknown scheduler response: '+text)
    return text.split(';')[0]


def command(package,record,phase,extra):
    base=['sbatch','--parsable','--account='+record['account'],'--export=NONE','--kill-on-invalid-dep=yes','--chdir='+str(package)]
    if record.get('constraint'):base+=['--constraint='+record['constraint']]
    return base+extra+[str(package/'slurm'/(phase+'.sbatch'))]+[
      str(package),record['bundle'],record['prepared'],record['campaign'],record['workspace'],record['sources'],record['apptainer']]


def dispatch(package,campaign,record,key,phase,part=None,dependency=None):
    journal=record.setdefault('dispatch',{})
    if key in journal:raise ValueError('Existing dispatch journal; inspect status, do not repeat '+key)
    journal[key]={'status':'dispatching'};persist(campaign/'submission.json',record)
    extra=['--output='+str(campaign/'logs'/(key+'-%A-%a.log'))]
    if part is not None:extra+=['--array='+str(part)]
    if dependency:extra+=['--dependency=afterok:'+dependency]
    result=subprocess.run(command(package,record,phase,extra),capture_output=True,text=True)
    if result.returncode:
        journal[key]={'status':'rejected','returncode':result.returncode,'stderr':result.stderr};persist(campaign/'submission.json',record)
        raise RuntimeError('Scheduler rejected '+key+': '+result.stderr)
    try:job=identity(result.stdout)
    except ValueError:
        journal[key]={'status':'unknown','stdout':result.stdout};persist(campaign/'submission.json',record);raise
    record['jobs'][key]=job;journal[key]={'status':'submitted','job_id':job};persist(campaign/'submission.json',record)
    return job


def submit(package,bundle,sources):
    if (package/'submission-binding.json').exists():raise ValueError('Existing binding; use status/advance, do not resubmit')
    cfg=verify(package,bundle)
    from protected import check
    protected=check(sources,package)
    account=os.environ['TORCH_SLURM_ACCOUNT']
    if not re.fullmatch(r'torch_pr_[A-Za-z0-9_]+',account):raise ValueError('Use an active Torch project account')
    prepared=Path(cfg['source_prepared']);scratch=Path(os.environ['TORCH_SCRATCH_ROOT']);results=Path(os.environ['TORCH_RESULTS_ROOT'])
    apptainer=Path(os.environ.get('TORCH_APPTAINER_BIN','/share/apps/apptainer/bin/apptainer'))
    for p in (package,bundle,sources,prepared,scratch,results,apptainer):
        if not p.is_absolute() or any(x in str(p) for x in (':',',','\n')):raise ValueError('Unsupported container path')
    if not os.access(apptainer,os.X_OK):raise ValueError('Apptainer is unavailable')
    ready=read(prepared/'READY.json')
    if ready['architecture']!='x86_64' or ready['image_sha256']!=cfg['image_sha256'] or read(prepared/'database-identity.json')!=read(package/'source-index.json'):
        raise ValueError('Original prepared index differs')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    scratch.mkdir(parents=True,exist_ok=True);results.mkdir(parents=True,exist_ok=True)
    provisional={'account':account,'constraint':os.environ.get('TORCH_CPU_CONSTRAINT'),'campaign':str(results/'unused'),
      'workspace':str(scratch),'bundle':str(bundle),'prepared':str(prepared),'sources':str(sources),'apptainer':str(apptainer)}
    for phase in ('build','acquire','fit','evaluate','measure'):
        subprocess.run(command(package,provisional,phase,['--test-only','--output=/dev/null']),check=True)
    campaign=Path(tempfile.mkdtemp(prefix='reviews-feature-data-ablation-v1-'+stamp+'.',dir=results))
    workspace=Path(tempfile.mkdtemp(prefix='torch-feature-data-ablation-v1.',dir=scratch));(campaign/'logs').mkdir()
    save(campaign/'protected-source-before.json',protected)
    record={**provisional,'campaign':str(campaign),'workspace':str(workspace),'package':str(package),'status':'submitting_initial',
      'jobs':{},'dispatch':{},'provider_calls':0,'confirmation_queries':0,'accounting':cfg['complete_call_accounting']}
    save(campaign/'submission.json',record)
    # Bind before the first real scheduler call, including unknown outcomes.
    save(package/'submission-binding.json',{'campaign':str(campaign),'package_manifest_sha256':sha(package/'manifest.json')})
    known=[]
    try:
        for key,phase,part in [('build','build',None),('acquire-0','acquire',0),('acquire-1','acquire',1),('fit','fit',None)]:
            known.append(dispatch(package,campaign,record,key,phase,part,known[-1] if known else None))
        record['status']='awaiting_calibration';persist(campaign/'submission.json',record)
    except BaseException:
        if known:subprocess.run(['scancel',*known],capture_output=True,text=True)
        record['status']='initial_submission_incomplete';persist(campaign/'submission.json',record);raise
    print(json.dumps(record,indent=2))
    print('Four initial allocations submitted. After fit completes, run control.py advance once. No model calls.')


def finished(campaign,phase):
    out=campaign/phase
    if not (out/'host-exit.json').exists():raise ValueError('Allocation still pending/running: '+phase)
    if read(out/'host-exit.json')['exit_code']:raise ValueError('Failed allocation: '+phase)
    if phase!='build' and (read(out/'job-exit.json')['exit_code'] or read(out/'status.json')['status']!='complete'):
        raise ValueError('Incomplete container stage: '+phase)
    return out


def advance(package,campaign):
    verify(package);record=read(campaign/'submission.json')
    if record['package']!=str(package):raise ValueError('Submission belongs to a different package')
    for phase in ('build','acquire/part-0','acquire/part-1','fit'):finished(campaign,phase)
    from execution import validate_fit
    lock=validate_fit(package,campaign/'fit')
    if not lock['proceed_to_evaluation']:
        record['status']='stopped_after_calibration';persist(campaign/'submission.json',record)
        print('No nonconstant policy passed calibration. No evaluation or timing jobs submitted. Run control.py collect.');return
    if 'evaluate' not in record['jobs']:
        dispatch(package,campaign,record,'evaluate','evaluate',dependency=record['jobs']['fit'])
        record['status']='awaiting_common_evaluation';persist(campaign/'submission.json',record)
        print('One common development evaluation allocation submitted. After completion, run control.py advance again.');return
    finished(campaign,'evaluate');screen=read(campaign/'evaluate/screen.json')
    if screen['fit_lock_sha256']!=sha(campaign/'fit/fit-lock.json'):raise ValueError('Evaluation belongs to a different fit lock')
    if not screen['proceed_to_timing']:
        record['status']='stopped_after_evaluation';persist(campaign/'submission.json',record)
        print('No policy passed common evaluation. No timing jobs submitted. Run control.py collect.');return
    if 'timing-first' in record['jobs']:
        print('Timing already dispatched. Use status; do not submit it again.');return
    known=[]
    try:
        known.append(dispatch(package,campaign,record,'timing-first','measure',0,record['jobs']['evaluate']))
        known.append(dispatch(package,campaign,record,'timing-remaining','measure','1-2%1',known[0]))
        record['status']='timing_submitted';persist(campaign/'submission.json',record)
    except BaseException:
        if known:subprocess.run(['scancel',*known],capture_output=True,text=True)
        record['status']='timing_submission_incomplete';persist(campaign/'submission.json',record);raise
    print('Three timing allocations submitted. Run control.py collect after all complete.')


def status(campaign):
    record=read(campaign/'submission.json');print('Campaign: '+str(campaign));print('Stage: '+record['status'])
    print('Initial allocations: 4; maximum allocations including gated evaluation/timing: 8')
    for phase in ('build','acquire/part-0','acquire/part-1','fit','evaluate','blocks/block-0','blocks/block-1','blocks/block-2'):
        for name in ('build.json','progress.json','status.json','failure.json','host-failure.json','host-exit.json'):
            p=campaign/phase/name
            if p.exists():print(phase+' '+name+': '+json.dumps(read(p),sort_keys=True))
    if record['jobs']:
        ids=','.join(record['jobs'].values());subprocess.run(['sacct','-j',ids,'--format=JobID,State,ExitCode,Elapsed']);subprocess.run(['squeue','-j',ids])


def collect(package,campaign):
    record=read(campaign/'submission.json');verify(package,Path(record['bundle']))
    if record['package']!=str(package):raise ValueError('Submission belongs to another package')
    for phase in ('build','acquire/part-0','acquire/part-1','fit'):finished(campaign,phase)
    from execution import validate_fit
    lock=validate_fit(package,campaign/'fit')
    if lock['proceed_to_evaluation']:
        finished(campaign,'evaluate');screen=read(campaign/'evaluate/screen.json')
        if screen['proceed_to_timing']:
            for i in range(3):finished(campaign,'blocks/block-'+str(i))
    archive=Path(str(campaign)+'.tar.gz')
    if archive.exists():
        if sha(archive)!=Path(str(archive)+'.sha256').read_text().split()[0]:raise ValueError('Collected archive changed')
        print('Existing verified archive: '+str(archive));return
    command=[record['apptainer'],'exec','--cleanenv','--containall','--no-home','--pwd','/results',
      '--bind',str(package)+':/patch:ro','--bind',str(campaign)+':/results:rw',
      '--env','PYTHONPATH=/patch:/patch/vendor:/opt/torch-reviews/vendor','--env','PYTHONDONTWRITEBYTECODE=1',
      '--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1',str(Path(record['bundle'])/'images/runtime.sif'),
      'python','/patch/report.py','--package','/patch','--campaign','/results']
    subprocess.run(command,check=True)
    copied=campaign/'package'
    if copied.exists():raise ValueError('Preserve partial collection; inspect copied package')
    shutil.copytree(package,copied,ignore=shutil.ignore_patterns('submission-binding.json','__pycache__'))
    with tarfile.open(archive,'x:gz') as tar:
        for p in sorted(campaign.rglob('*')):
            if p.is_symlink():raise ValueError('Symlink in result archive')
            if p.is_file():tar.add(p,arcname=campaign.name+'/'+str(p.relative_to(campaign)),recursive=False)
    save(Path(str(archive)+'.sha256'),sha(archive)+'  '+archive.name+'\n',raw=True)
    print('Download archive and checksum: '+str(archive))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['submit','status','advance','collect']);parser.add_argument('paths',nargs='*',type=Path)
    args=parser.parse_args();package=Path(__file__).resolve().parent
    if args.command=='submit':
        if len(args.paths)!=2:parser.error('submit requires original bundle and source-results root')
        submit(package,*[p.resolve() for p in args.paths])
    else:
        if len(args.paths)>1:parser.error('At most one campaign path')
        campaign=args.paths[0].resolve() if args.paths else Path(read(package/'submission-binding.json')['campaign'])
        if args.command=='status':status(campaign)
        elif args.command=='advance':advance(package,campaign)
        else:collect(package,campaign)


if __name__=='__main__':main()
