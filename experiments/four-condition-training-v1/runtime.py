"""One contained process owns each database lifetime and cleanup."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import time

from no_models import enforce
enforce()

from contract import read, save, sha


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['build','acquire','measure']);parser.add_argument('--block',type=int,default=0)
    args=parser.parse_args();package=Path('/patch');out=Path('/results');cfg=read(package/'experiment.json')
    if os.uname().machine!='x86_64' and os.environ.get('FOUR_SYNTHETIC_VALIDATION')!='1':raise RuntimeError('Actual study requires x86_64')
    if args.phase=='build':
        engine=Path('/run/engine');shutil.copytree(package/'engine',engine)
        env={**os.environ,'PG_CONFIG':'/opt/postgresql/bin/pg_config'}
        with (out/'build.log').open('x') as log:
            subprocess.run(['make','clean'],cwd=engine,stdout=log,stderr=subprocess.STDOUT,check=True,env=env)
            subprocess.run(['make','-j2','OPTFLAGS=','PG_CONFIG=/opt/postgresql/bin/pg_config'],cwd=engine,stdout=log,stderr=subprocess.STDOUT,check=True,env=env)
        module=out/'vector.so';shutil.copyfile(engine/'vector.so',module)
        data=module.read_bytes()
        if data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',data,18)[0]!=62:raise RuntimeError('Built module is not Linux x86_64')
        save(out/'build.json',{'status':'complete','architecture':'x86_64','module_sha256':sha(module),
            'package_manifest_sha256':sha(package/'manifest.json'),'provider_calls':0})
        return
    from execution import Budget, acquisition, load_backend, measurement
    from database import prepare,stop
    frozen,Backend=load_backend(package);work=Path('/run');started=time.monotonic();code=1;running=False
    limit=cfg['complete_call_accounting']['acquisition_maximum_backend_calls' if args.phase=='acquire' else 'measurement_maximum_backend_calls_per_block']
    budget=Budget(limit)
    def notify(phase,**fields):
        value={'phase':phase,**fields};tmp=out/'.progress.tmp';tmp.write_bytes(__import__('contract').encoded(value));tmp.replace(out/'progress.json')
        print(__import__('json').dumps(value),flush=True)
    def interrupted(number,frame):raise InterruptedError('Slurm signal '+str(number))
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):signal.signal(sig,interrupted)
    try:
        notify('restore_and_verify_index',backend_searches=0)
        expected=prepare(package,Path('/bundle'),Path('/prepared'),work,frozen);running=True
        save(out/'database-identity.json',expected)
        save(out/'runtime-identity.json',{'module_sha256':sha('/opt/postgresql/lib/vector.so'),
            'package_manifest_sha256':sha(package/'manifest.json'),'image_sha256':cfg['image_sha256'],
            'query_file_sha256':sha(package/'inputs/queries.jsonl'),'runtime_profile_hash':frozen.PROFILE.fingerprint,
            'feature_registry_hash':frozen.FEATURE_REGISTRY_HASH})
        if args.phase=='acquire':status=acquisition(frozen,Backend,Path('/bundle'),work,package,out,budget,notify)
        else:status=measurement(frozen,Backend,Path('/bundle'),work,package,out,Path('/gate'),args.block,budget,notify)
        from runtime_base import verify_index
        verify_index(work,expected)
        status.update(measurement_seconds=time.monotonic()-started,canonical_acceptance_established=False)
        save(out/'status.json',status);code=0
    except BaseException as e:
        save(out/'failure.json',{'type':type(e).__name__,'message':str(e),'backend_searches':budget.calls,'operations':dict(budget.operations)});raise
    finally:
        cleanup=0
        if running or (work/'pgdata/postmaster.pid').exists():
            try:stop(work)
            except BaseException:cleanup=1
        if (work/'server.log').exists():shutil.copyfile(work/'server.log',out/'server.log')
        save(out/'job-exit.json',{'exit_code':code or cleanup,'persistent_container':True,'work_directory_retained':True})
        if cleanup:raise RuntimeError('PostgreSQL cleanup failed')


if __name__=='__main__':main()
