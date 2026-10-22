"""Host jobs enforce seals, dependencies, resource limits and source preservation."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

from contract import encoded,read,save,sha
from protected import check
from verify_patch import check as verify


def main():
    phase=sys.argv[1];package,bundle,prepared,campaign,workspace,sources=map(Path,sys.argv[2:8]);apptainer=sys.argv[8]
    if os.uname().sysname!='Linux' or os.uname().machine!='x86_64' or not os.environ.get('SLURM_JOB_ID'):raise RuntimeError('Use an x86_64 Torch allocation')
    verify(package,bundle);cfg=read(package/'experiment.json');before=check(sources,package)
    if before!=read(campaign/'protected-source-before.json'):raise RuntimeError('Protected sources changed after submission')
    if read(prepared/'database-identity.json')!=read(package/'source-index.json'):raise RuntimeError('Original physical index backup differs')
    ready=read(prepared/'READY.json')
    if ready['architecture']!='x86_64' or ready['image_sha256']!=cfg['image_sha256']:raise RuntimeError('Backup runtime differs')
    original=sources/cfg['collector_campaign']/'build/modules/new-vector.so'
    if sha(original)!=cfg['original_module_sha256']:raise RuntimeError('Original module changed')
    block=int(os.environ.get('SLURM_ARRAY_TASK_ID','0'))
    if phase=='measure' and block not in range(3):raise RuntimeError('Undeclared block')
    out=campaign/('blocks/block-'+str(block) if phase=='measure' else phase)
    if phase=='measure':out.mkdir()
    save(out/'protected-source-before.json',before)
    module=None;gate=campaign/'acquire'
    if phase!='build':
        build=read(campaign/'build/build.json');module=campaign/'build/vector.so'
        if build['status']!='complete' or build['module_sha256']!=sha(module) or build['package_manifest_sha256']!=sha(package/'manifest.json'):raise RuntimeError('Build identity differs')
    if phase=='measure':
        if read(gate/'status.json')['status']!='complete' or read(gate/'job-exit.json')['exit_code'] or read(gate/'host-exit.json')['exit_code']:raise RuntimeError('Acquisition did not complete cleanly')
        from execution import validate_lock
        lock,_=validate_lock(package,gate)
        if lock['module_sha256']!=sha(module):raise RuntimeError('Qualified module differs')
    work=Path(tempfile.mkdtemp(prefix='four-'+phase+'-'+os.environ['SLURM_JOB_ID']+'.',dir=str(workspace)));work.chmod(0o700)
    for d in ('socket','tmp'):(work/d).mkdir(mode=0o700)
    (work/'.torch-owned').write_text(os.environ['SLURM_JOB_ID']+'\n')
    cmd=[apptainer,'exec','--cleanenv','--containall','--no-home','--pwd','/run']
    mounts=[(package,'/patch','ro'),(bundle,'/bundle','ro'),(work,'/run','rw'),(out,'/results','rw')]
    if phase!='build':mounts.extend([(prepared,'/prepared','ro'),(module,'/opt/postgresql/lib/vector.so','ro')])
    if phase=='measure':mounts.append((gate,'/gate','ro'))
    for a,b,c in mounts:cmd+=['--bind',str(a)+':'+b+':'+c]
    env={'PYTHONPATH':'/patch:/opt/torch-reviews/vendor','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':'/run/tmp',
        'SLURM_JOB_ID':os.environ['SLURM_JOB_ID'],'TORCH_IMAGE_SHA256':cfg['image_sha256'],'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
    for k,v in env.items():cmd+=['--env',k+'='+v]
    cmd+=[str(bundle/'images/runtime.sif'),'python','/patch/runtime.py',phase]
    if phase=='measure':cmd+=['--block',str(block)]
    process=None;code=1
    def interrupted(number,frame):
        if process:process.terminate()
        raise InterruptedError('Slurm signal '+str(number))
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):signal.signal(sig,interrupted)
    try:
        process=subprocess.Popen(cmd);result=process.wait();process=None
        if result:raise RuntimeError('Container failed with exit '+str(result))
        if phase!='build' and read(out/'job-exit.json')['exit_code']:raise RuntimeError('Container cleanup failed')
        code=0
    except BaseException as e:
        save(out/'host-failure.json',{'type':type(e).__name__,'message':str(e)});raise
    finally:
        if process:
            process.terminate()
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        after=check(sources,package);save(out/'protected-source-after.json',after)
        save(out/'host-exit.json',{'exit_code':code or int(before!=after),'completed_sources_unchanged':before==after,
            'job_id':os.environ['SLURM_JOB_ID'],'work_directory':str(work),'provider_calls':0})
        if before!=after:raise RuntimeError('Original sources changed')


if __name__=='__main__':main()
