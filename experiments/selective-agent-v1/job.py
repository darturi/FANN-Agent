"""Scheduler host wrapper; never import a model, never mutate shared inputs."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from contract import read,save,sha
from protected import check

def main():
    package,bundle,prepared,campaign,workspace,sources=map(Path,sys.argv[1:7]);apptainer=sys.argv[7]
    from control import verify
    cfg=verify(package,bundle)
    if os.uname().sysname!='Linux' or os.uname().machine!='x86_64' or not os.environ.get('SLURM_JOB_ID'):raise RuntimeError('Use a Torch x86_64 allocation')
    block=int(os.environ['SLURM_ARRAY_TASK_ID'])
    if block not in range(3):raise RuntimeError('Unknown block')
    before=check(sources,package)
    if before!=read(campaign/'protected-source-before.json'):raise RuntimeError('Sources changed after submission')
    if read(prepared/'database-identity.json')!=read(package/'source-index.json'):raise RuntimeError('Prepared physical index changed')
    out=campaign/'blocks'/('block-'+str(block));out.mkdir(parents=True,exist_ok=False);save(out/'protected-source-before.json',before)
    work=Path(tempfile.mkdtemp(prefix=cfg['stage']+'-'+os.environ['SLURM_JOB_ID']+'.',dir=workspace));work.chmod(0o700)
    for n in ('socket','tmp'):(work/n).mkdir(mode=0o700)
    (work/'.torch-owned').write_text(os.environ['SLURM_JOB_ID']+'\n')
    cmd=[apptainer,'exec','--cleanenv','--containall','--no-home','--pwd','/run']
    for a,b,c in [(package,'/patch','ro'),(bundle,'/bundle','ro'),(prepared,'/prepared','ro'),(out,'/results','rw'),
        (work,'/run','rw'),(package/'modules/vector.so','/opt/postgresql/lib/vector.so','ro')]:cmd+=['--bind',str(a)+':'+b+':'+c]
    for k,v in {'PYTHONPATH':'/patch:/patch/vendor:/opt/torch-reviews/vendor','PYTHONDONTWRITEBYTECODE':'1',
        'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','TMPDIR':'/run/tmp','TORCH_IMAGE_SHA256':cfg['image_sha256']}.items():cmd+=['--env',k+'='+v]
    cmd+=[str(bundle/'images/runtime.sif'),'python','/patch/runtime.py','--block',str(block)]
    process=None;code=1
    def interrupted(number,frame):
        if process:process.terminate()
        raise InterruptedError('Slurm signal '+str(number))
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):signal.signal(sig,interrupted)
    try:
        process=subprocess.Popen(cmd);result=process.wait();process=None
        if result or read(out/'job-exit.json')['exit_code']:raise RuntimeError('Container or cleanup failed')
        code=0
    except BaseException as error:
        save(out/'host-failure.json',{'type':type(error).__name__,'message':str(error)});raise
    finally:
        if process:
            process.terminate()
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        after=check(sources,package);save(out/'protected-source-after.json',after)
        save(out/'host-exit.json',{'exit_code':code or int(before!=after),'job_id':os.environ['SLURM_JOB_ID'],
            'protected_sources_unchanged':before==after,'work_directory':str(work),'provider_calls':0})
        if before!=after:raise RuntimeError('Protected sources changed')

if __name__=='__main__':main()
