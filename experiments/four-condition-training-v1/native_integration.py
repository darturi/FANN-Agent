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
from contract import EXTRA,read,sha
from execution import Budget,load_backend,policy,prefix,qualify_getters,verify_probe
from fitting import guard,predict


def main():
    frozen,Backend=load_backend(Path('/patch'))
    libdir=Path('/usr/lib/postgresql/17/lib')
    for source in Path('/opt/queue-fixture/baseline-lib').iterdir():
        target=libdir/source.name
        if source.is_dir():shutil.copytree(source,target)
        else:shutil.copyfile(source,target)
    lib=libdir/'vector.so';work=Path('/tmp/four-native');work.mkdir(mode=0o700);(work/'socket').mkdir(mode=0o700)
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
    rng=np.random.default_rng(20261019);vs=rng.normal(size=(4100,16)).astype(np.float32);vs/=np.linalg.norm(vs,axis=1,keepdims=True)
    rows=[{'source_id':i,'vector':v.tolist(),'metadata':{'total_votes':i%200}} for i,v in enumerate(vs[:4000])]
    items=[]
    for i,v in enumerate(vs[4000:4004]):
        for f,t in [('unfiltered',None),('votes32',32),('votes108',108)]:
            items.append({'query':{'id':'synthetic-'+str(i)+'-'+f,'vector':v.tolist(),'k':10,
                'filter':None if t is None else {'field':'m_000000','op':'gte','value':t}}})
    refs={};comparisons=0;stop_comparisons=0;probe_checks=0;backend=None
    try:
        shutil.copyfile('/opt/queue-fixture/candidate-vector.so',lib);start()
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
        names=read('/patch/experiment.json')['base_feature_names']
        for version,module in [('baseline','/opt/queue-fixture/candidate-vector.so'),('candidate','/candidate/vector.so')]:
            shutil.copyfile(module,lib);start();backend=Backend(Path('/opt/torch-reviews'),work)
            if version=='candidate':
                with psycopg.connect(make_conninfo(frozen.job_connection(work,admin=True),dbname='torch_reviews'),autocommit=True) as c:
                    c.execute(frozen.FUNCTIONS)
                    c.execute('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA fannagent FROM PUBLIC')
                    c.execute('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA fannagent TO torch_reader')
            backend.state['source_manifest']['settings']['hnsw.ef_search']='640'
            for item in items:
                q=item['query'];native=backend.execute_probe(q)
                r=backend.execute_probe(q,mode='policy',policy=backend.validate_policy(policy('synthetic-base')),trace=True)
                base=prefix(r,names)
                assert (r.ids,r.distances)==(native.ids,native.distances)
                value={'ids':r.ids,'distances':r.distances,'states':base}
                if version=='baseline':refs[q['id']]=value
                else:
                    assert value==refs[q['id']];comparisons+=1
                    local=backend.execute_probe(q,mode='policy',policy=backend.validate_policy(policy('synthetic-local',local=True)),trace=True)
                    states=prefix(local,names+EXTRA)
                    assert [{**s,'features':{n:s['features'][n] for n in names}} for s in states]==base
                    assert (local.ids,local.distances)==(native.ids,native.distances)
                    receipt=verify_probe(backend,q,states,local.metadata['request_nonce']);probe_checks+=receipt['causal_prefix_feature_checks']
                    for is_local,ss in [(False,base),(True,states)]:
                        for cp in (1,2,4,8,16,32,64,128):
                            if cp>len(ss):continue
                            raw=policy('synthetic-stop',cp,is_local)
                            stopped=backend.execute_probe(q,mode='policy',policy=backend.validate_policy(raw),trace=True)
                            assert prefix(stopped,names+(EXTRA if is_local else []))==ss[:cp]
                            assert predict(raw,ss,frozen.PROFILE)==cp
                            assert stopped.metadata['checkpoint_count']==cp and stopped.metadata['stop_reason']=='policy_stop'
                            stop_comparisons+=1
                    # Availability/checkpoint guard cannot fire at an ineligible ordinal.
                    for allowed in ([32,64,128],[1,2,4,8,16,32,64,128]):
                        raw=policy('synthetic-guard',local=True,root=guard('stop',allowed))
                        r=backend.execute_probe(q,mode='policy',policy=backend.validate_policy(raw),trace=True)
                        assert r.metadata['checkpoint_count']==allowed[0]
            if version=='candidate':
                budget=Budget(1000)
                getters=[qualify_getters(backend,budget,items,names,False),qualify_getters(backend,budget,items,names+EXTRA,True)]
                assert budget.calls==510
                # A following legacy request must not retain enabled local observations.
                q=items[-1]['query'];backend.execute_probe(q,mode='policy',policy=backend.validate_policy(policy('synthetic-reset')))
                reset=json.loads(backend._connect().execute('SELECT fannagent.local_probe()').fetchone()[0])
                assert not reset['enabled'] and reset['examined']==0 and not reset['rows']
                if '--pipeline' in sys.argv:
                    pipeline(frozen,Backend,backend,work,vs[4000:],names,location,oid)
            backend.close();backend=None;stop();assert sha(work/'pgdata'/location)==index_hash
        result={'status':'passed','architecture':os.uname().machine,'synthetic_only':True,'model_calls':0,'confirmation_queries':0,
            'original_native_and_prefix_comparisons':comparisons,'actual_stop_prefix_comparisons':stop_comparisons,
            'local_probe_checkpoint_checks':probe_checks,'getter_calls':510,'request_reset_verified':True,
            'candidate_module_sha256':sha('/candidate/vector.so'),'physical_index_unchanged':True}
        Path('/output/native-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    finally:
        if backend:backend.close()
        stop()
        if (work/'server.log').exists():shutil.copyfile(work/'server.log','/output/server.log')


def pipeline(frozen,Backend,backend,work,vectors,names,location,oid):
    """Exercise the complete acquisition/fit/timing/report path on synthetic data."""
    import time
    sys.path.insert(0,'/study')
    from contract import CONFIG,encoded
    from execution import acquisition,measurement
    from report import analyze
    p=Path('/tmp/pipeline-package');shutil.copytree('/patch',p)
    campaign=Path('/tmp/pipeline-campaign');campaign.mkdir()
    for phase in ('build','acquire','blocks'):(campaign/phase).mkdir()
    expected={};source=[];queries=[]
    for i,v in enumerate(vectors):
        for f,t in [('unfiltered',None),('votes32',32),('votes108',108)]:
            group='pipeline-'+str(i);q={'id':group+'-'+f,'vector':v.tolist(),'k':10,
                'filter':None if t is None else {'field':'m_000000','op':'gte','value':t}}
            native=backend.execute_probe(q);truth=backend.exact_reference(q)
            ref=backend.execute_probe(q,mode='policy',policy=backend.validate_policy(policy('pipeline-original')),trace=True)
            expected[q['id']]={'ids':native.ids,'distances':native.distances,'recall':frozen.score(truth,native)['recall']}
            source.append({'query_id':q['id'],'states':prefix(ref,names)})
            queries.append({'query':q,'group':group,'split':'learning'})
    (p/'inputs/queries.jsonl').write_text(''.join(json.dumps(q)+'\n' for q in queries))
    (p/'inputs/training-640-light.jsonl').write_text(''.join(json.dumps(q)+'\n' for q in source))
    (p/'inputs/native-results.json').write_bytes(encoded(expected))
    identity={'index_oid':oid,'index_identity':sha(work/'pgdata'/location),'row_count':4000,'dimension':16}
    (p/'source-index.json').write_bytes(encoded(identity))
    cfg=read(p/'experiment.json');cfg.update(row_count=4000,dimension=16);(p/'experiment.json').write_bytes(encoded(cfg))
    manifest=read(p/'manifest.json');manifest['files']={str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file() and f.name!='manifest.json'}
    (p/'manifest.json').write_bytes(encoded(manifest))
    shutil.copyfile('/candidate/vector.so',campaign/'build/vector.so')
    (campaign/'build/build.json').write_bytes(encoded({'status':'complete','architecture':'aarch64','module_sha256':sha('/candidate/vector.so'),'package_manifest_sha256':sha(p/'manifest.json')}))
    def setup(out):
        out.mkdir(exist_ok=True)
        for n in ('protected-source-before.json','protected-source-after.json'):(out/n).write_text('{}\n')
        (out/'host-exit.json').write_text('{"exit_code":0}\n');(out/'job-exit.json').write_text('{"exit_code":0}\n')
        (out/'database-identity.json').write_bytes(encoded(identity))
        (out/'runtime-identity.json').write_bytes(encoded({'module_sha256':sha('/candidate/vector.so'),'package_manifest_sha256':sha(p/'manifest.json'),'query_file_sha256':sha(p/'inputs/queries.jsonl')}))
    setup(campaign/'build');setup(campaign/'acquire')
    started=time.monotonic()
    def notify(phase,**fields):
        if fields.get('query',0)%50==0:print(json.dumps({'synthetic_pipeline':phase,**fields}),flush=True)
    budget=Budget(cfg['complete_call_accounting']['acquisition_maximum_backend_calls'])
    status=acquisition(frozen,Backend,Path('/opt/torch-reviews'),work,p,campaign/'acquire',budget,notify)
    (campaign/'acquire/status.json').write_bytes(encoded(status))
    for block in range(3):
        out=campaign/'blocks'/('block-'+str(block));setup(out)
        b=Budget(cfg['complete_call_accounting']['measurement_maximum_backend_calls_per_block'])
        status=measurement(frozen,Backend,Path('/opt/torch-reviews'),work,p,out,campaign/'acquire',block,b,notify)
        (out/'status.json').write_bytes(encoded(status))
    # Test-only dataset dimensions; no final statistical criterion is changed.
    old=CONFIG['row_count'],CONFIG['dimension'];CONFIG.update(row_count=4000,dimension=16)
    try:result=analyze(campaign,p)
    finally:CONFIG['row_count'],CONFIG['dimension']=old
    receipt={'status':'passed','synthetic_only':True,'independent_groups':100,'conditions':4,
        'nested_fits_reproduced':True,'measurement_blocks':3,'retained_pairs':result['retained_pairs'],
        'acquisition':result['acquisition'],'provider_calls':0,'confirmation_queries':0,
        'elapsed_seconds':time.monotonic()-started,'ab_comparison':result['ab_comparison']}
    Path('/output/pipeline-checks.json').write_bytes(encoded(receipt));print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
