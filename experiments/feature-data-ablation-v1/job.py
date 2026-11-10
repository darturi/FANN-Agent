"""Torch host wrapper: seals, private workspaces and source preservation."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from contract import read,save,sha
from protected import check
from verify_patch import check as check_bundle


def main():
    phase=sys.argv[1];package,bundle,prepared,campaign,workspace,sources=map(Path,sys.argv[2:8]);apptainer=sys.argv[8]
    from control import verify
    verify(package,bundle)
    if os.uname().sysname!='Linux' or os.uname().machine!='x86_64' or not os.environ.get('SLURM_JOB_ID'):raise RuntimeError('Use an x86_64 Torch allocation')
    before=check(sources,package)
    if before!=read(campaign/'protected-source-before.json'):raise RuntimeError('Protected sources changed after submission')
    cfg=read(package/'experiment.json');part=int(os.environ.get('SLURM_ARRAY_TASK_ID','0'))
    if phase=='acquire' and part not in range(2) or phase=='measure' and part not in range(3):raise RuntimeError('Undeclared allocation part')
    relative='acquire/part-'+str(part) if phase=='acquire' else 'blocks/block-'+str(part) if phase=='measure' else phase
    out=campaign/relative;out.mkdir(parents=True,exist_ok=False)
    save(out/'protected-source-before.json',before)
    if read(prepared/'database-identity.json')!=read(package/'source-index.json'):raise RuntimeError('Original index backup changed')
    ready=read(prepared/'READY.json')
    if ready['architecture']!='x86_64' or ready['image_sha256']!=cfg['image_sha256']:raise RuntimeError('Backup image differs')
    if sha(sources/cfg['collector_campaign']/'build/modules/new-vector.so')!=cfg['original_module_sha256']:raise RuntimeError('Original module changed')
    module=None
    if phase!='build':
        module=campaign/'build/vector.so';built=read(campaign/'build/build.json')
        if built['module_sha256']!=sha(module) or built['package_manifest_sha256']!=sha(package/'manifest.json'):raise RuntimeError('New build identity differs')
    if phase in ('evaluate','measure'):
        from execution import validate_fit
        lock=validate_fit(package,campaign/'fit')
        if not lock['proceed_to_evaluation'] or lock['module_sha256']!=sha(module):raise RuntimeError('No valid calibration gate')
    work=Path(tempfile.mkdtemp(prefix='feature-data-'+phase+'-'+os.environ['SLURM_JOB_ID']+'.',dir=workspace));work.chmod(0o700)
    for n in ('socket','tmp'):(work/n).mkdir(mode=0o700)
    (work/'.torch-owned').write_text(os.environ['SLURM_JOB_ID']+'\n')
    cmd=[apptainer,'exec','--cleanenv','--containall','--no-home','--pwd','/run']
    mounts=[(package,'/patch','ro'),(bundle,'/bundle','ro'),(campaign,'/campaign','ro'),(out,'/results','rw'),(work,'/run','rw')]
    if phase!='build':mounts.append((module,'/opt/postgresql/lib/vector.so','ro'))
    if phase in ('acquire','evaluate','measure'):mounts.append((prepared,'/prepared','ro'))
    for a,b,c in mounts:cmd+=['--bind',str(a)+':'+b+':'+c]
    for k,v in {'PYTHONPATH':'/patch:/patch/vendor:/opt/torch-reviews/vendor','PYTHONDONTWRITEBYTECODE':'1',
       'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','TMPDIR':'/run/tmp','SLURM_JOB_ID':os.environ['SLURM_JOB_ID']}.items():cmd+=['--env',k+'='+v]
    cmd += [str(bundle/'images/runtime.sif'),'python','/patch/runtime.py',phase,'--part',str(part)]
    process=None;code=1
    def interrupted(number,frame):
        if process:process.terminate()
        raise InterruptedError('Slurm signal '+str(number))
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):signal.signal(sig,interrupted)
    try:
        process=subprocess.Popen(cmd);exit_code=process.wait();process=None
        if exit_code:raise RuntimeError('Container failed: '+str(exit_code))
        if phase!='build' and read(out/'job-exit.json')['exit_code']:raise RuntimeError('Container cleanup failed')
        code=0
    except BaseException as error:
        save(out/'host-failure.json',{'type':type(error).__name__,'message':str(error)});raise
    finally:
        if process:
            process.terminate()
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        after=check(sources,package);save(out/'protected-source-after.json',after)
        save(out/'host-exit.json',{'exit_code':code or int(before!=after),'protected_sources_unchanged':before==after,
          'job_id':os.environ['SLURM_JOB_ID'],'work_directory':str(work),'provider_calls':0})
        if before!=after:raise RuntimeError('Original sources changed')


if __name__=='__main__':main()
