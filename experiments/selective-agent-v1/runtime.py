"""Provider-free Torch execution with a private restored database."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import time
from no_models import enforce
enforce()
from contract import CONFIG,read,save,sha

def seal(out,package):
    save(out/'LOCK.json',{'package_manifest_sha256':sha(package/'manifest.json'),
        'files_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in {'LOCK.json','progress.json','host-exit.json','protected-source-after.json'}}})

def main():
    p=argparse.ArgumentParser();p.add_argument('--block',type=int,required=True);a=p.parse_args()
    package=Path('/patch');out=Path('/results');work=Path('/run');cfg=read(package/'experiment.json')
    if os.uname().machine!='x86_64':raise RuntimeError('Real Torch study requires x86_64')
    if a.block not in range(3):raise RuntimeError('Unknown block')
    from execution import load_backend,Budget,measure
    from database import prepare,stop
    from runtime_base import verify_index
    frozen,Backend=load_backend(package);started=time.monotonic();running=False;backend=None;code=1
    budget=Budget(cfg['complete_call_accounting']['backend_searches_per_block_maximum'])
    def notify(phase,**fields):
        value={'phase':phase,'stage':cfg['stage'],'block':a.block,'provider_calls':0,**fields}
        __import__('contract').replace(out/'progress.json',value);print(__import__('json').dumps(value),flush=True)
    def interrupted(number,frame):raise InterruptedError('Slurm signal '+str(number))
    for sig in (signal.SIGINT,signal.SIGTERM,signal.SIGUSR1):signal.signal(sig,interrupted)
    try:
        notify('restore_and_verify_index',backend_searches=0)
        expected=prepare(package,Path('/bundle'),Path('/prepared'),work,frozen);running=True
        save(out/'database-identity.json',expected)
        from fannagent_pgvector.profiles import PROFILE
        save(out/'runtime-identity.json',{'module_sha256':sha('/opt/postgresql/lib/vector.so'),
            'runtime_profile_hash':PROFILE.fingerprint,'registry_hash':PROFILE.native_registry_hash,
            'package_manifest_sha256':sha(package/'manifest.json'),'image_sha256':cfg['image_sha256']})
        if sha('/opt/postgresql/lib/vector.so')!=cfg['module_sha256']:raise RuntimeError('Different module mounted')
        backend=Backend(Path('/bundle'),work);backend.state['source_manifest']['settings']['hnsw.ef_search']='640'
        retained=measure(backend,frozen,budget,package,out,a.block,notify)
        verify_index(work,expected)
        if time.monotonic()-started>6600:raise RuntimeError('Work deadline exceeded')
        save(out/'status.json',{'status':'complete','stage':cfg['stage'],'block':a.block,'provider_calls':0,
            'query_filter_cases':cfg['complete_call_accounting']['cases'],
            'independent_vectors':cfg['complete_call_accounting']['independent_vectors'],
            'confirmation_queries':180 if cfg['stage']=='confirmation' else 0,
            'development_queries':0 if cfg['stage']=='confirmation' else 600,
            'qualification_backend_searches':921,'backend_searches':budget.calls,'operations':dict(budget.operations),
            'control_installations':budget.control_installations,'retained_pairs':retained,
            'control_sql_counts':{'explicit_eviction_install_queries':budget.control_installations,
                'trace_receipt_queries':budget.operations.get('policy_trace',0),
                'other_sql_statements':None,'note':'Search operations can contain multiple SQL statements; other SQL is not claimed as counted.'},
            'elapsed_seconds':time.monotonic()-started,'canonical_acceptance_established':False})
        code=0
    except BaseException as error:
        save(out/'failure.json',{'type':type(error).__name__,'message':str(error),'backend_searches':budget.calls,'operations':dict(budget.operations)});raise
    finally:
        cleanup=0
        if backend:backend.close()
        if running or (work/'pgdata/postmaster.pid').exists():
            try:stop(work)
            except BaseException:cleanup=1
        if (work/'server.log').exists():shutil.copyfile(work/'server.log',out/'server.log')
        save(out/'job-exit.json',{'exit_code':code or cleanup,'work_directory_retained':True})
        if cleanup:raise RuntimeError('Database cleanup failed')
    seal(out,package)

if __name__=='__main__':main()
