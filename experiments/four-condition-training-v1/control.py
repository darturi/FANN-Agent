"""Torch submission binding, visible allocation counts, status and collection."""
import argparse
import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

from contract import CONFIG, NAME, encoded,read,save,sha


def verify(package,bundle=None):
    manifest=read(package/'manifest.json')
    for name,expected in manifest['files'].items():
        p=package/name
        if p.is_symlink() or not p.is_file() or sha(p)!=expected:raise ValueError('Package file changed: '+name)
    cfg=read(package/'experiment.json')
    for k,v in CONFIG.items():
        if cfg.get(k)!=v:raise ValueError('Predeclared contract changed: '+k)
    if bundle is not None:
        from verify_patch import check
        check(package,bundle)
        if sha(bundle/'images/runtime.sif')!=cfg['image_sha256']:raise ValueError('Runtime image changed')
    return cfg


def job_id(raw):
    raw=raw.strip()
    if not re.fullmatch(r'[1-9][0-9]*(;torch)?',raw):raise ValueError('Unknown sbatch response: '+raw)
    return raw.split(';')[0]


def persist(path,value):
    temp=path.with_name('.'+path.name+'.tmp');temp.write_bytes(encoded(value));temp.replace(path)


def submit(package,bundle,sources):
    cfg=verify(package,bundle)
    if (package/'submission-binding.json').exists():raise ValueError('Existing submission binding; inspect status/journal instead of resubmitting')
    from protected import check
    protected=check(sources,package)
    prepared=Path(cfg['source_prepared']);ready=read(prepared/'READY.json')
    if read(prepared/'database-identity.json')!=read(package/'source-index.json') or ready['image_sha256']!=cfg['image_sha256'] or ready['architecture']!='x86_64':raise ValueError('Original prepared index differs')
    if sha(sources/cfg['collector_campaign']/'build/modules/new-vector.so')!=cfg['original_module_sha256']:raise ValueError('Original module differs')
    account=os.environ['TORCH_SLURM_ACCOUNT'];scratch=Path(os.environ['TORCH_SCRATCH_ROOT']).resolve();results=Path(os.environ['TORCH_RESULTS_ROOT']).resolve()
    apptainer=Path(os.environ.get('TORCH_APPTAINER_BIN','/share/apps/apptainer/bin/apptainer'))
    if not re.fullmatch(r'torch_pr_[A-Za-z0-9_]+',account):raise ValueError('Use an active Torch project account')
    for p in (package,bundle,sources,prepared,scratch,results,apptainer):
        if not p.is_absolute() or any(s in str(p) for s in (':',',','\n')):raise ValueError('Unsupported container binding path')
    if not os.access(apptainer,os.X_OK):raise ValueError('Apptainer unavailable')
    base=['sbatch','--parsable','--account='+account,'--export=NONE','--kill-on-invalid-dep=yes','--chdir='+str(package)]
    if os.environ.get('TORCH_CPU_CONSTRAINT'):base+=['--constraint='+os.environ['TORCH_CPU_CONSTRAINT']]
    def command(stage,extra,campaign,workspace):
        phase=stage if stage in ('build','acquire') else 'measure'
        return base+extra+[str(package/'slurm'/(phase+'.sbatch'))]+list(map(str,(package,bundle,prepared,campaign,workspace,sources,apptainer)))
    for stage in ('build','acquire','first'):
        subprocess.run(command(stage,['--test-only','--output=/dev/null']+(['--array=0'] if stage=='first' else []),results/'unused',scratch),check=True)
    scratch.mkdir(parents=True,exist_ok=True);results.mkdir(parents=True,exist_ok=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    campaign=Path(tempfile.mkdtemp(prefix='reviews-four-condition-training-v1-'+stamp+'.',dir=results))
    workspace=Path(tempfile.mkdtemp(prefix='torch-four-condition-training-v1.',dir=scratch))
    for n in ('build','acquire','blocks','logs'):(campaign/n).mkdir()
    save(campaign/'protected-source-before.json',protected)
    record={'status':'submitting','campaign':str(campaign),'package':str(package),'bundle':str(bundle),
        'prepared':str(prepared),'workspace':str(workspace),'sources':str(sources),'apptainer':str(apptainer),
        'jobs':{},'provider_calls':0,'confirmation_queries':0,'accounting':cfg['complete_call_accounting']}
    save(campaign/'submission.json',record)
    # Bind before any actual sbatch. Unknown/partial outcomes cannot be repeated.
    save(package/'submission-binding.json',{'campaign':str(campaign),'package_manifest_sha256':sha(package/'manifest.json')})
    known=[]
    try:
        for stage in ('build','acquire','first','remaining'):
            extra=['--dependency=afterok:'+known[-1]] if known else []
            if stage=='first':extra+=['--array=0']
            elif stage=='remaining':extra+=['--array=1-2%1']
            extra+=['--output='+str(campaign/'logs'/(stage+'-%A-%a.log'))]
            proc=subprocess.run(command(stage,extra,campaign,workspace),capture_output=True,text=True)
            if proc.returncode:raise RuntimeError('sbatch rejected '+stage+': '+proc.stderr)
            try:identity=job_id(proc.stdout)
            except ValueError:
                record.update(status='submission_unknown',unknown_response=proc.stdout);raise
            known.append(identity);record['jobs'][stage]=identity;persist(campaign/'submission.json',record)
        record['status']='submitted';persist(campaign/'submission.json',record)
    except BaseException as e:
        record['error']=str(e)
        if record['status']!='submission_unknown':record['status']='submission_failed'
        if known:
            canceled=subprocess.run(['scancel',*known],capture_output=True,text=True)
            record['cancellation']={'known_new_jobs_only':known,'returncode':canceled.returncode}
        persist(campaign/'submission.json',record)
        print('Preserve and inspect '+str(campaign/'submission.json')+' before any retry',flush=True);raise
    print(__import__('json').dumps(record,indent=2))
    print('Five allocations submitted. No model calls. Original A/B: inconclusive.')
    print('Status: python3 '+str(package/'control.py')+' status')
    print('Collect after completion: python3 '+str(package/'control.py')+' collect')


def resolve(package,path):
    return Path(path).resolve() if path else Path(read(package/'submission-binding.json')['campaign'])


def status(campaign):
    r=read(campaign/'submission.json');print('Campaign: '+str(campaign));print('Allocations: build + acquire/fit + 3 measurement blocks')
    for name in ['build','acquire',*[f'blocks/block-{i}' for i in range(3)]]:
        for f in ('build.json','status.json','progress.json','failure.json','host-failure.json','host-exit.json'):
            p=campaign/name/f
            if p.exists():print(name+' '+f+': '+__import__('json').dumps(read(p),sort_keys=True))
    if r['jobs']:
        subprocess.run(['sacct','-j',','.join(r['jobs'].values()),'--format=JobID,State,ExitCode,Elapsed'])
        subprocess.run(['squeue','-j',','.join(r['jobs'].values())])


def collect(package,campaign):
    r=read(campaign/'submission.json');verify(package,Path(r['bundle']))
    if Path(r['package'])!=package:raise ValueError('Submission belongs to another package')
    for phase in ['build','acquire',*[f'blocks/block-{i}' for i in range(3)]]:
        if read(campaign/phase/'host-exit.json')['exit_code']:raise ValueError('Incomplete/failed allocation: '+phase)
    archive=Path(str(campaign)+'.tar.gz')
    if archive.exists():
        if sha(archive)!=Path(str(archive)+'.sha256').read_text().split()[0]:raise ValueError('Existing archive changed')
        print('Existing verified archive: '+str(archive));return
    # Execute sealed package code in the pinned runtime, never returned code.
    args=[r['apptainer'],'exec','--cleanenv','--containall','--no-home','--pwd','/results',
        '--bind',str(package)+':/patch:ro','--bind',str(campaign)+':/results:rw',
        '--env','PYTHONPATH=/patch:/patch/vendor:/opt/torch-reviews/vendor',
        '--env','PYTHONDONTWRITEBYTECODE=1','--env','OPENBLAS_NUM_THREADS=1','--env','OMP_NUM_THREADS=1',
        str(Path(r['bundle'])/'images/runtime.sif'),'python','/patch/report.py','--campaign','/results','--package','/patch']
    subprocess.run(args,check=True)
    copied=campaign/'package'
    if copied.exists():raise ValueError('Preserve existing copied package; inspect collection state')
    shutil.copytree(package,copied,ignore=shutil.ignore_patterns('submission-binding.json','__pycache__'))
    with tarfile.open(archive,'x:gz') as tar:
        for p in sorted(campaign.rglob('*')):
            if p.is_symlink():raise ValueError('Symlink in result archive')
            if p.is_file():tar.add(p,arcname=campaign.name+'/'+str(p.relative_to(campaign)),recursive=False)
    save(Path(str(archive)+'.sha256'),sha(archive)+'  '+archive.name+'\n',raw=True)
    print('Download archive and checksum: '+str(archive))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['submit','status','collect']);parser.add_argument('paths',nargs='*',type=Path)
    args=parser.parse_args();package=Path(__file__).resolve().parent
    if args.command=='submit':
        if len(args.paths)!=2:parser.error('submit requires original bundle and source-results root')
        submit(package,*[p.resolve() for p in args.paths])
    elif len(args.paths)>1:parser.error('At most one campaign path')
    else:(status if args.command=='status' else lambda p:collect(package,p))(resolve(package,args.paths[0] if args.paths else None))


if __name__=='__main__':main()
