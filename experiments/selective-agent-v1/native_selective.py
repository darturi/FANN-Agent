"""Actual PostgreSQL selective routes and small synthetic full-driver regression."""
import sys
sys.path.insert(0,'/study')
import copy
import json
from pathlib import Path
import random
import shutil
from unittest.mock import patch
from contract import CONFIG,EARLY,FILTERS,read,save,sha,digest,accounting
from policy import compose,validate,names,states
from execution import Session,session,pair,Budget,measure,prefix,native_execute

def check(backend,frozen,work,vectors,original_items):
    cfg=read('/patch/experiment.json');checks=0;budget=Budget(60000)
    for profile in ('light19','static23','progress34'):
        raw=compose('selective-native-check',{'if':{'op':'eq','args':[{'feature':'checkpoint_index'},{'int':4}]},'then':'stop','else':'continue'},profile,['unfiltered','votes32'])
        s=session(backend,raw,cfg)
        for item in original_items[:3]:
            q=item['query'];native=native_execute(backend,budget,q);before=backend._installed;cache=len(backend._policies.entries)
            if q['filter'] and q['filter']['value']==108:
                with patch.object(backend,'_install_policy',side_effect=AssertionError('Bypass installed policy')):
                    r=s.query(q,budget,trace=True)
                assert r.metadata['ordinary_default'] and r.metadata['native_bypass'] and r.evidence is None
                assert (r.ids,r.distances)==(native.ids,native.distances)
                assert backend._installed==before and len(backend._policies.entries)==cache
            else:
                r=s.query(q,budget,trace=True);ss=prefix(r,names(cfg,profile))
                assert not r.metadata['native_bypass'] and r.metadata['checkpoint_count']==4 and len(ss)==4
            checks+=1
        # An unsupported but valid actual predicate takes native, regardless of query ID.
        q={**original_items[0]['query'],'id':'misleading-votes32','filter':{'field':'m_000000','op':'gte','value':109}}
        expected=native_execute(backend,budget,q);r=s.query(q,budget,trace=True)
        assert r.metadata['native_bypass'] and (r.ids,r.distances)==(expected.ids,expected.distances);checks+=1
        q={**original_items[0]['query'],'k':5}
        expected=native_execute(backend,budget,q);r=s.query(q,budget,trace=True)
        assert r.metadata['native_bypass'] and (r.ids,r.distances)==(expected.ids,expected.distances);checks+=1
        with patch.object(backend,'execute_probe',side_effect=RuntimeError('deliberate native fixture failure')):
            try:s.query(original_items[0]['query'],budget)
            except RuntimeError:checks+=1
            else:raise AssertionError('Runtime failure was swallowed')
        backend.close()
        try:s.query(original_items[0]['query'],budget)
        except RuntimeError:checks+=1
        else:raise AssertionError('Stale connection was reused')
        backend._connect();session(backend,raw,cfg).query(original_items[0]['query'],budget);checks+=1
    return {'route_error_reconnect_checks':checks,'full_driver':pipeline(backend,frozen,work,vectors,cfg)}

def pipeline(backend,frozen,work,vectors,source_cfg):
    """Same measure/report functions, smaller disjoint synthetic inputs, no scientific pass."""
    from fd_policy_tools import policy as fixed
    from report import analyze
    from package import RUNTIME_FILES
    parent=Path('/output/driver');parent.mkdir();package=parent/'package';package.mkdir();(package/'inputs').mkdir();(package/'modules').mkdir()
    for name in RUNTIME_FILES:shutil.copyfile(Path('/study')/name,package/name)
    shutil.copytree('/patch/vendor',package/'vendor')
    shutil.copytree('/opt/torch-reviews/vendor/fannagent',package/'vendor/fannagent')
    shutil.copyfile('/candidate/vector.so',package/'modules/vector.so')
    items=[];data=[]
    for i,v in enumerate(vectors[:30]):
        for f in FILTERS:
            q={'id':'fixture-'+str(i)+'-'+f,'vector':v.tolist(),'k':10,
                'filter':None if f=='unfiltered' else {'field':'m_000000','op':'gte','value':int(f[5:])}}
            items.append({'query':q,'group':'fixture-'+str(i),'role':'synthetic_development'})
            native=native_execute(backend,Budget(100),q);truth=backend.exact_reference(q)
            rr={}
            for profile in ('static23','progress34'):
                result=session(backend,compose('reference','continue',profile),source_cfg).query(q,Budget(100),trace=True)
                rr[profile]=prefix(result,names(source_cfg,profile))
            # Sparse oracle labels are actual cp1 results, acquired only on synthetic data.
            cp_result=session(backend,compose('oracle-label',{'if':{'op':'eq','args':[{'feature':'checkpoint_index'},{'int':1}]},'then':'stop','else':'continue'}),source_cfg).query(q,Budget(100),trace=True)
            score=frozen.score(truth,cp_result)
            data.append({'query_id':q['id'],'group':'fixture-'+str(i),'stratum':f,'native_recall':frozen.score(truth,native)['recall'],
                'base_states':rr['static23'],'local_states':rr['progress34'],
                'labels':{'base':{'1':{'recall':score['recall'],'valid':score['valid'],'returned_count':len(cp_result.ids)}},'local':{}},
                'continue_costs':{}})
    candidates={}
    for profile in ('light19','static23','progress34'):
        root={'if':{'op':'eq','args':[{'feature':'checkpoint_index'},{'int':4}]},'then':'stop','else':'continue'}
        raw=compose('fixture-'+profile,root,profile,['unfiltered','votes32']);h=validate(raw,source_cfg)[1]
        candidates[h]={'policy':raw,'semantic_hash':h,'origin':'Synthetic fixture only'}
    cfg={**source_cfg,**CONFIG,'stage':'pilot','synthetic_only':True,'fixture_cases':90,'episode_id':'synthetic-driver',
        'row_count':4000,'dimension':16,'module_sha256':sha('/candidate/vector.so'),'run_contract_sha256':'synthetic',
        'complete_call_accounting':accounting('pilot',3,90)}
    save(package/'experiment.json',cfg);save(package/'candidates.json',candidates)
    save(package/'inputs/development-evidence.json',{'queries':data})
    for n,value in [('queries.jsonl',items),('qualification.jsonl',items[:3])]:
        save(package/'inputs'/n,''.join(json.dumps(i)+'\n' for i in value),raw=True)
    original_manifest=read('/patch/manifest.json')['original_manifest_sha256']
    save(package/'manifest.json',{'original_manifest_sha256':original_manifest,
        'files':{str(p.relative_to(package)):sha(p) for p in package.rglob('*') if p.is_file()}})
    campaign=parent/'campaign';campaign.mkdir();total=0
    from runtime import seal
    for block in range(3):
        out=campaign/'blocks'/('block-'+str(block));out.mkdir(parents=True)
        b=Budget(cfg['complete_call_accounting']['backend_searches_per_block_maximum'])
        count=measure(backend,frozen,b,package,out,block,lambda *a,**kw:None);total+=b.calls
        for n,obj in [('status.json',{'status':'complete','provider_calls':0,'backend_searches':b.calls,'retained_pairs':count}),
            ('job-exit.json',{'exit_code':0}),('protected-source-before.json',{}),('protected-source-after.json',{}),
            ('runtime-identity.json',{'module_sha256':cfg['module_sha256'],
                'registry_hash':backend.runtime_profile.native_registry_hash,'runtime_profile_hash':backend.runtime_profile.fingerprint,
                'package_manifest_sha256':sha(package/'manifest.json'),'image_sha256':cfg['image_sha256']})]:save(out/n,obj)
        seal(out,package);save(out/'host-exit.json',{'exit_code':0})
    report=analyze(campaign,package)
    assert report['retained_pairs']==3*90*8*4
    assert all(not q['final_qualifies'] for q in report['candidate_qualification'].values())
    # Exercise the different confirmation schedule with one actual synthetic block.
    cp=parent/'confirmation-package';shutil.copytree(package,cp)
    chosen=next(iter(candidates));confirmation_cfg={**cfg,'stage':'confirmation','complete_call_accounting':accounting('confirmation',1,90)}
    for n,obj in [('experiment.json',confirmation_cfg),('candidates.json',{chosen:candidates[chosen]})]:
        (cp/n).unlink();save(cp/n,obj)
    out=parent/'confirmation-block';out.mkdir();b=Budget(confirmation_cfg['complete_call_accounting']['backend_searches_per_block_maximum'])
    confirmation_pairs=measure(backend,frozen,b,cp,out,0,lambda *a,**kw:None)
    assert confirmation_pairs==90*3*9
    return {'pilot_blocks':3,'pilot_backend_searches':total,'pilot_retained_pairs':report['retained_pairs'],
        'confirmation_driver_block_searches':b.calls,'confirmation_driver_retained_pairs':confirmation_pairs,
        'raw_report_reproduced':True,'synthetic_never_qualifies':True,'new_Reviews_measurements':0}
