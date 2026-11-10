"""Offline synthetic real-PostgreSQL regression against the original native path.

Run in the existing queue-statistics fixture, with /tmp and PostgreSQL libraries
on tmpfs, /opt/torch-reviews holding synthetic inputs, /patch the staged upload,
/candidate/vector.so the newly compiled library and /output writable results.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

sys.path.insert(0,'/study')
from contract import EXTRA,read,sha,CONFIG
from execution import Budget,load_backend,prefix,qualify,verify_probe,verify_progress
from policy_tools import policy,predict,guard



def main():
    frozen,Backend=load_backend(Path('/patch'))
    libdir=Path('/usr/lib/postgresql/17/lib')
    for source in Path('/opt/queue-fixture/baseline-lib').iterdir():
        target=libdir/source.name
        if source.is_dir():shutil.copytree(source,target)
        else:shutil.copyfile(source,target)
    lib=libdir/'vector.so';work=Path('/tmp/fd-native');work.mkdir(mode=0o700);(work/'socket').mkdir(mode=0o700)
    (work/'.torch-owned').write_text('synthetic-native-check\n');frozen.initialize_auth(work)
    def run(*args):subprocess.run(list(map(str,args)),check=True,stdout=subprocess.DEVNULL)
    run('initdb','-D',work/'pgdata','--username=torch_owner','--pwfile='+str(work/'admin.pw'),'--auth-local=scram-sha-256','--auth-host=reject','--encoding=UTF8','--locale=C')
    running=False
    def start():
        nonlocal running
        run('pg_ctl','-D',work/'pgdata','-l',work/'server.log','-w','start','-o',
            "-c listen_addresses='' -c unix_socket_directories="+str(work/'socket')+' -c hba_file='+str(work/'pg_hba.conf')+' -c shared_buffers=128MB')
        running=True
    def stop():
        nonlocal running
        if running:run('pg_ctl','-D',work/'pgdata','-m','fast','-w','stop');running=False
    rng=np.random.default_rng(20261019);vs=rng.normal(size=(4260,16)).astype(np.float32);vs/=np.linalg.norm(vs,axis=1,keepdims=True)
    rows=[{'source_id':i,'vector':v.tolist(),'metadata':{'total_votes':None if i%23==0 else i%200}} for i,v in enumerate(vs[:4000])]
    items=[]
    for i,v in enumerate(vs[4000:4004]):
        for f,t in [('unfiltered',None),('votes32',32),('votes108',108)]:
            items.append({'query':{'id':'synthetic-'+str(i)+'-'+f,'vector':v.tolist(),'k':10,
                'filter':None if t is None else {'field':'m_000000','op':'gte','value':t}}})
    refs={};comparisons=0;stop_comparisons=0;probe_checks=0;backend=None
    try:
        shutil.copyfile('/previous/vector.so',lib);start()
        with psycopg.connect(frozen.job_connection(work,admin=True),autocommit=True) as c:c.execute('CREATE DATABASE torch_reviews')
        with psycopg.connect(make_conninfo(frozen.job_connection(work,admin=True),dbname='torch_reviews'),autocommit=True) as c:
            password=(work/'reader.pgpass').read_text().strip().rsplit(':',1)[1]
            c.execute(sql.SQL('CREATE ROLE torch_reader LOGIN PASSWORD {}').format(sql.Literal(password)))
            c.execute('CREATE EXTENSION vector');c.execute('CREATE TABLE reviews(id bigint PRIMARY KEY,embedding vector(16),total_votes bigint)')
            with c.cursor().copy('COPY reviews FROM STDIN') as cp:
                for r in rows:
                    cp.write_row((r['source_id'],'['+','.join(format(float(x),'.9g') for x in r['vector'])+']',r['metadata']['total_votes']))
            c.execute('SET max_parallel_maintenance_workers=0');c.execute('CREATE INDEX reviews_hnsw ON reviews USING hnsw(embedding vector_cosine_ops) WITH(m=16,ef_construction=64)');c.execute('ANALYZE reviews')
            c.execute(frozen.FUNCTIONS.split('CREATE OR REPLACE FUNCTION fannagent.begin_execution(\n text,text,bigint,text,integer,integer,text,bigint,text,text,text,boolean,bigint)')[0])
            c.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC');c.execute('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA fannagent FROM PUBLIC')
            c.execute('GRANT CONNECT ON DATABASE torch_reviews TO torch_reader');c.execute('GRANT USAGE ON SCHEMA public,fannagent TO torch_reader')
            c.execute('GRANT SELECT ON reviews TO torch_reader');c.execute('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA fannagent TO torch_reader');c.execute('ALTER ROLE torch_reader SET default_transaction_read_only=on')
            c.execute('CHECKPOINT');location,oid=c.execute("SELECT pg_relation_filepath('reviews_hnsw'),'reviews_hnsw'::regclass::oid").fetchone()
        index_hash=sha(work/'pgdata'/location)
        (work/'database-identity.json').write_text(json.dumps({'index_oid':oid,'index_identity':index_hash}))
        stop()
        names=read('/patch/experiment.json')['static_feature_names']
        for version,module in [('baseline','/previous/vector.so'),('candidate','/candidate/vector.so')]:
            shutil.copyfile(module,lib);start();backend=Backend(Path('/opt/torch-reviews'),work)
            with psycopg.connect(make_conninfo(frozen.job_connection(work,admin=True),dbname='torch_reviews'),autocommit=True) as c:
                functions=frozen.FUNCTIONS if version=='candidate' else frozen.FUNCTIONS.split('CREATE OR REPLACE FUNCTION fannagent.progress_probe')[0]
                c.execute(functions)
                c.execute('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA fannagent FROM PUBLIC')
                c.execute('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA fannagent TO torch_reader')
            backend.state['source_manifest']['settings']['hnsw.ef_search']='640'
            for item in items:
                q=item['query'];native=backend.execute_probe(q)
                r=backend.execute_probe(q,mode='policy',policy=backend.validate_policy(policy('synthetic-static')),trace=True)
                static=prefix(r,names)
                assert (r.ids,r.distances)==(native.ids,native.distances)
                value={'ids':r.ids,'distances':r.distances,'states':static}
                if version=='baseline':refs[q['id']]=value
                else:
                    assert value==refs[q['id']];comparisons+=1
                    verify_probe(backend,q,static,r.metadata['request_nonce'])
                    p=backend.execute_probe(q,mode='policy',policy=backend.validate_policy(policy('synthetic-progress',progress=True)),trace=True)
                    progress=prefix(p,names+EXTRA)
                    assert [{**s,'features':{n:s['features'][n] for n in names}} for s in progress]==static
                    assert (p.ids,p.distances)==(native.ids,native.distances)
                    receipt=verify_progress(backend,q,progress,p.metadata['request_nonce'])
                    assert all(x<=8 for x in receipt['fetches']) and sum(receipt['fetches'])<=64
                    probe_checks+=len(progress)
                    for enabled,states in [(False,static),(True,progress)]:
                        for cp in (1,2,4,8,16,32,64,128):
                            if cp>len(states):continue
                            raw=policy('synthetic-stop',cp,progress=enabled)
                            stopped=backend.execute_probe(q,mode='policy',policy=backend.validate_policy(raw),trace=True)
                            assert prefix(stopped,names+(EXTRA if enabled else []))==states[:cp]
                            assert predict(raw,states,frozen.PROFILE)==cp
                            assert stopped.metadata['checkpoint_count']==cp
                            stop_comparisons+=1
            if version=='candidate':
                budget=Budget(2000)
                getters=qualify(backend,budget,items,read('/patch/experiment.json'))
                assert budget.calls==921
                backend.execute_probe(items[-1]['query'],mode='policy',policy=backend.validate_policy(policy('synthetic-reset')))
                reset=json.loads(backend._connect().execute('SELECT fannagent.progress_probe()').fetchone()[0])
                assert not reset['enabled'] and not reset['rows'] and sum(reset['fetches'])==0
                if os.environ.get('FD_PIPELINE')=='1':
                    pipeline(backend,frozen,work,vs[4000:4260])
            backend.close();backend=None;stop();assert sha(work/'pgdata'/location)==index_hash
        result={'status':'passed','architecture':os.uname().machine,'synthetic_only':True,'provider_calls':0,
          'original_native_static_prefix_comparisons':comparisons,'actual_stop_prefix_comparisons':stop_comparisons,
          'causal_progress_checkpoint_checks':probe_checks,'numeric_boolean_availability_getter_calls':921,
          'request_reset_verified':True,'physical_index_unchanged':True,'candidate_module_sha256':sha('/candidate/vector.so')}
        Path('/output/native-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    finally:
        if backend:backend.close()
        stop()
        if (work/'server.log').exists():shutil.copyfile(work/'server.log','/output/server.log')
        if os.environ.get('FD_PIPELINE')=='1':shutil.copytree(work,'/output/fixture-state')

def pipeline(backend,frozen,work,vectors):
    """Actual DB requests and independent collection, using synthetic vectors only.

    Natural calibration selection is preserved. A separate, explicitly forced
    branch exercises evaluation/timing even when the natural selection abstains;
    that branch can never be presented as a scientific qualification.
    """
    from contract import save,lines,CONDITIONS,AB
    from execution import acquire,fit_study,evaluate_candidates,measure
    from runtime import seal
    from report import analyze,timing_report,reproduce_acquisition
    from fannagent_pgvector.profiles import PROFILE
    from fannagent.api import validate_policy
    package=Path('/output/synthetic-package');shutil.copytree('/patch',package)
    def replace_fixture(path,value,raw=False):
        path.unlink(missing_ok=True);save(path,value,raw=raw)
    # This local fixture changes dimensions, row count and vector inputs only.
    CONFIG.update(row_count=4000,dimension=16)
    cfg=read(package/'experiment.json');cfg.update(row_count=4000,dimension=16)
    cfg['synthetic_validation_only']=True
    roles=['original_learning']*100+['additional_learning']*60+['calibration']*40+['evaluation']*60
    items=[]
    for i,(v,role) in enumerate(zip(vectors,roles)):
        for f,t in [('unfiltered',None),('votes32',32),('votes108',108)]:
            group='fixture-vector-'+str(i).zfill(3)
            items.append({'role':role,'group':group,'catalog_group':'synthetic-'+str(i),
              'query':{'id':group+'-'+f,'vector':v.tolist(),'k':10,
              'filter':None if t is None else {'field':'m_000000','op':'gte','value':t}}})
    parts=[items[:300],items[300:600]]
    for i,part in enumerate(parts):
        replace_fixture(package/'inputs'/('acquire-'+str(i)+'.jsonl'),''.join(json.dumps(x)+'\n' for x in part),raw=True)
    replace_fixture(package/'inputs/evaluation.jsonl',''.join(json.dumps(x)+'\n' for x in items[600:]),raw=True)
    replace_fixture(package/'inputs/training-640-light.jsonl','',raw=True);replace_fixture(package/'inputs/native-results.json',{})
    replace_fixture(package/'source-index.json',read(work/'database-identity.json'))
    cfg['query_file_sha256']={p.name:sha(p) for p in (package/'inputs').glob('*.jsonl')}
    replace_fixture(package/'experiment.json',cfg)
    manifest=read(package/'manifest.json')
    manifest['files']={name:sha(package/name) for name in manifest['files']};replace_fixture(package/'manifest.json',manifest)
    campaign=Path('/output/synthetic-natural-campaign');campaign.mkdir()
    def folder(relative):
        out=campaign/relative;out.mkdir(parents=True);save(out/'protected-source-before.json',{'synthetic_only':True})
        return out
    def complete(out,budget=None,**status):
        save(out/'status.json',{'status':'complete','synthetic_only':True,**status,
          **({'backend_searches':budget.calls,'operations':dict(budget.operations)} if budget else {})})
        save(out/'job-exit.json',{'exit_code':0})
        save(out/'runtime-identity.json',{'module_sha256':sha('/candidate/vector.so'),'package_manifest_sha256':sha(package/'manifest.json')})
        save(out/'database-identity.json',read(package/'source-index.json'))
        seal(out,package);save(out/'protected-source-after.json',{'synthetic_only':True});save(out/'host-exit.json',{'exit_code':0})
    def notify(phase,**fields):
        if fields.get('query',0)%30==0:print(json.dumps({'fixture_phase':phase,**fields}),flush=True)
    built=folder('build');shutil.copyfile('/candidate/vector.so',built/'vector.so')
    save(built/'build.json',{'module_sha256':sha(built/'vector.so'),'package_manifest_sha256':sha(package/'manifest.json')})
    save(built/'protected-source-after.json',{'synthetic_only':True});save(built/'host-exit.json',{'exit_code':0})
    total=0
    for i,part in enumerate(parts):
        out=folder('acquire/part-'+str(i));budget=Budget(39321)
        acquire(backend,frozen,budget,part,package,out,notify);complete(out,budget);total+=budget.calls
    fitted=folder('fit');lock=fit_study(package,campaign,fitted,notify);complete(fitted)
    # Exercise the complete natural path through its actual terminal gate.
    natural={'calibration_proceed':lock['proceed_to_evaluation']}
    if lock['proceed_to_evaluation']:
        out=folder('evaluate');budget=Budget(24681)
        evidence=acquire(backend,frozen,budget,items[600:],package,out,notify)
        screen=evaluate_candidates(backend,frozen,budget,package,campaign,out,evidence)
        complete(out,budget);total+=budget.calls
        natural['evaluation_proceed']=screen['proceed_to_timing']
        if screen['proceed_to_timing']:
            for block in range(3):
                out=folder('blocks/block-'+str(block));budget=Budget(17481)
                retained=measure(backend,frozen,budget,package,campaign,out,block,notify)
                assert retained==5760;complete(out,budget,retained_pairs=retained);total+=budget.calls
    report=analyze(campaign,package)
    natural.update(independent_report_reproduction=True,status=report['status'])
    if report['timing_executed']:
        result={'status':'passed','synthetic_only':True,'provider_calls':0,'new_reviews_measurements':0,
          'natural_selection':natural,'acquisition_query_cases':600,'evaluation_query_cases':180,
          'actual_candidate_proofs':720,'timing_blocks':3,'timing_retained_pairs':17280,
          'timing_native_bypass_pairs':720,'backend_calls_all_pipeline_phases':total,
          'timing_raw_reproduction':True,'original_ab':AB}
        save(Path('/output/pipeline-checks.json'),result);print(json.dumps(result,indent=2),flush=True)
        return
    branch=Path('/output/synthetic-forced-branch-campaign');shutil.copytree(campaign,branch);campaign=branch
    # Explicit fixture intervention, never a claimed fitted or qualified policy.
    lock=read(campaign/'fit/fit-lock.json');lock['synthetic_forced_branch_only']=True
    for arm,p in lock['policies'].items():
        raw=policy('fixture-fixed-stop-'+arm,32,progress=CONDITIONS[arm]['local_filter'])
        p.update(policy=raw,policy_hash=validate_policy(raw,PROFILE).policy_hash,nonconstant_selected_stop=True)
    lock['proceed_to_evaluation']=True;replace_fixture(campaign/'fit/fit-lock.json',lock)
    (campaign/'fit/LOCK.json').unlink();seal(campaign/'fit',package)
    out=folder('evaluate');budget=Budget(24681)
    evidence=acquire(backend,frozen,budget,items[600:],package,out,notify)
    screen=evaluate_candidates(backend,frozen,budget,package,campaign,out,evidence);total+=budget.calls
    observed_gate=screen['proceed_to_timing'];screen['proceed_to_timing']=True
    screen['synthetic_forced_branch_only']=True;replace_fixture(out/'screen.json',screen);complete(out,budget)
    reproduce_acquisition(campaign,'evaluate',package,items[600:],PROFILE,True)
    for block in range(3):
        out=folder('blocks/block-'+str(block));budget=Budget(17481)
        retained=measure(backend,frozen,budget,package,campaign,out,block,notify)
        assert retained==5760;complete(out,budget,retained_pairs=retained);total+=budget.calls
    timed,per_block=timing_report(campaign,package,evidence,lock,PROFILE)
    assert len(timed)==8 and len(per_block)==3
    # The production collector must reject this intervention as a fitted result.
    try:analyze(campaign,package)
    except ValueError as error:
        assert str(error)=='Calibration fit/selection does not independently reproduce'
    else:raise AssertionError('Collector accepted the forced fixture fit lock')
    result={'status':'passed','synthetic_only':True,'provider_calls':0,'new_reviews_measurements':0,
      'natural_selection':natural,'forced_branch_scientific_qualification':False,
      'actual_common_evaluation_gate_before_intervention':observed_gate,
      'forced_branch_rejected_by_production_collector':True,'acquisition_query_cases':600,
      'evaluation_query_cases':180,'actual_candidate_proofs':720,'timing_blocks':3,
      'timing_retained_pairs':17280,'timing_native_bypass_pairs':720,
      'backend_calls_all_pipeline_phases':total,'timing_raw_reproduction':True,'original_ab':AB}
    save(Path('/output/pipeline-checks.json'),result);print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
