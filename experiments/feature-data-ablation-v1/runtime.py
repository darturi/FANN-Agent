"""Contained build/acquisition/fitting/evaluation/timing with private DB cleanup."""
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
from contract import CONFIG,read,save,sha,encoded,lines


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['build','acquire','fit','evaluate','measure']);parser.add_argument('--part',type=int,default=0)
    args=parser.parse_args();package=Path('/patch');out=Path('/results');campaign=Path('/campaign');cfg=read(package/'experiment.json')
    if os.uname().machine!='x86_64' and os.environ.get('FD_SYNTHETIC_VALIDATION')!='1':raise RuntimeError('Actual study requires x86_64')
    started=time.monotonic()
    def notify(phase,**fields):
        value={'phase':phase,'provider_calls':0,**fields};temp=out/'.progress.tmp';temp.write_bytes(encoded(value));temp.replace(out/'progress.json')
        print(__import__('json').dumps(value),flush=True)
    if args.phase=='build':
        engine=Path('/run/engine');shutil.copytree(package/'engine',engine)
        with (out/'build.log').open('x') as log:
            subprocess.run(['make','clean','PG_CONFIG=/opt/postgresql/bin/pg_config'],cwd=engine,stdout=log,stderr=subprocess.STDOUT,check=True)
            subprocess.run(['make','-j2','OPTFLAGS=','PG_CONFIG=/opt/postgresql/bin/pg_config'],cwd=engine,stdout=log,stderr=subprocess.STDOUT,check=True)
        module=out/'vector.so';shutil.copyfile(engine/'vector.so',module);data=module.read_bytes()
        if data[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',data,18)[0]!=62:raise RuntimeError('Built module is not x86_64 ELF')
        save(out/'build.json',{'status':'complete','architecture':'x86_64','module_sha256':sha(module),
          'package_manifest_sha256':sha(package/'manifest.json'),'provider_calls':0})
        return
    from execution import Budget,fit_study,acquire,evaluate_candidates,measure,load_backend
    if args.phase=='fit':
        code=1
        try:
            # The fitting process has no reason to contact a database or a network.
            import sys
            def audit(event,values):
                if event in ('socket.connect','socket.connect_ex','subprocess.Popen','os.system'):raise RuntimeError('Offline fitting forbids '+event)
            sys.addaudithook(audit)
            lock=fit_study(package,campaign,out,notify)
            save(out/'status.json',{'status':'complete','stage':'calibration-fitting','provider_calls':0,
              'backend_searches':0,'conventional_fits':16,'proceed_to_evaluation':lock['proceed_to_evaluation'],
              'confirmation_queries':0,'elapsed_seconds':time.monotonic()-started,'canonical_acceptance_established':False})
            code=0
        except BaseException as error:
            save(out/'failure.json',{'type':type(error).__name__,'message':str(error)});raise
        finally:save(out/'job-exit.json',{'exit_code':code,'database_started':False})
        seal(out,package);return
    from database import prepare,stop
    frozen,Backend=load_backend(package);work=Path('/run');running=False;code=1;backend=None
    key={'acquire':'acquisition_backend_calls_per_shard_maximum','evaluate':'evaluation_backend_calls_maximum','measure':'timing_backend_calls_per_block'}[args.phase]
    budget=Budget(cfg['complete_call_accounting'][key])
    def interrupted(number,frame):raise InterruptedError('Slurm signal '+str(number))
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1):signal.signal(sig,interrupted)
    try:
        notify('restore_and_verify_index',backend_searches=0)
        expected=prepare(package,Path('/bundle'),Path('/prepared'),work,frozen);running=True
        save(out/'database-identity.json',expected)
        save(out/'runtime-identity.json',{'module_sha256':sha('/opt/postgresql/lib/vector.so'),
          'package_manifest_sha256':sha(package/'manifest.json'),'runtime_profile_hash':frozen.PROFILE.fingerprint,
          'feature_registry_hash':frozen.FEATURE_REGISTRY_HASH,'image_sha256':cfg['image_sha256']})
        backend=Backend(Path('/bundle'),work);backend.state['source_manifest']['settings']['hnsw.ef_search']='640'
        status={'status':'complete','stage':args.phase,'provider_calls':0,'confirmation_queries':0,'canonical_acceptance_established':False}
        if args.phase in ('acquire','evaluate'):
            name='evaluation.jsonl' if args.phase=='evaluate' else 'acquire-'+str(args.part)+'.jsonl'
            items=lines(package/'inputs'/name)
            if args.phase=='acquire' and (len(items)!=300 or any(i['role']=='evaluation' for i in items)):raise RuntimeError('Training/calibration query entitlement differs')
            if args.phase=='evaluate' and (len(items)!=180 or any(i['role']!='evaluation' for i in items)):raise RuntimeError('Common evaluation entitlement differs')
            evidence=acquire(backend,frozen,budget,items,package,out,notify)
            status.update(query_filter_cases=len(items),independent_vectors=len({i['group'] for i in items}),
              actual_stop_executions=sum(len(q['labels']['base'])+len(q['labels']['local']) for q in evidence['queries']),
              metadata_receipt_sql_reads=2*len(items),metadata_verification_sql_reads=2*len(items))
            if args.phase=='evaluate':
                screen=evaluate_candidates(backend,frozen,budget,package,campaign,out,evidence)
                status['proceed_to_timing']=screen['proceed_to_timing']
        else:status.update(block=args.part,retained_pairs=measure(backend,frozen,budget,package,campaign,out,args.part,notify))
        from runtime_base import verify_index
        verify_index(work,expected)
        if time.monotonic()-started>6600:raise RuntimeError('Allocation work exceeded fixed deadline')
        status.update(backend_searches=budget.calls,operations=dict(budget.operations),control_installations=budget.control_installations,
                      elapsed_seconds=time.monotonic()-started)
        save(out/'status.json',status);code=0
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
        if cleanup:raise RuntimeError('PostgreSQL cleanup failed')
    seal(out,package)


def seal(out,package):
    save(out/'LOCK.json',{'package_manifest_sha256':sha(package/'manifest.json'),
      'files_sha256':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name not in ('LOCK.json','progress.json','host-exit.json','protected-source-after.json')}})


if __name__=='__main__':main()
