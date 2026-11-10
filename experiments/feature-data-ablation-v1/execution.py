"""Native acquisition, common calibration, locked evaluation and paired timing."""
import collections
import json
import math
from pathlib import Path
import random
import time

from contract import CONFIG,CONDITIONS,EXTRA,LEGACY_EXTRA,EARLY,GROUPS,SEED,AB,read,save,sha,digest,lines
from legacy_execution import Budget,execute,pair,prefix,install_eviction,load_backend,write,verify_probe
from policy_tools import policy,predict,replay,assess


def qualify(backend,budget,items,cfg):
    from fannagent_pgvector.profiles import PROFILE
    reports=[]
    for mode,names in [('base',cfg['base_feature_names']),('static',cfg['static_feature_names']),
                       ('progress',cfg['static_feature_names']+EXTRA)]:
        start=budget.calls
        for f in CONFIG['filters']:
            q=next(i['query'] for i in items if i['query']['id'].endswith('-'+f))
            ref=execute(backend,budget,q,policy('fd-getter-reference',progress=mode=='progress',base=mode=='base'),True)
            values=prefix(ref,names)[0]['features']
            for n in names:
                v=values[n];kind=PROFILE.runtime_features[n].kind
                if v is None:raise RuntimeError('Qualified getter unavailable: '+n)
                if kind=='bool':tests=[({'op':'eq','args':[{'feature':n},{'bool':v}]},True),({'op':'eq','args':[{'feature':n},{'bool':not v}]},False)]
                else:
                    if kind=='int' and type(v) is not int:raise RuntimeError('Integer getter type differs')
                    if kind=='float' and not math.isfinite(v):raise RuntimeError('Nonfinite getter')
                    bounds=[v,v+1] if kind=='int' else [float(v),1e-12 if float(v)==0 else math.nextafter(float(v),math.inf)]
                    tests=[({'op':'gte','args':[{'feature':n},{kind:int(b) if kind=='int' else float(b)}]},want) for b,want in zip(bounds,[True,False])]
                tests += [({'op':'is_available','args':[{'feature':n}]},True)]
                for expression,want in tests:
                    raw=policy('fd-getter-'+n,progress=mode=='progress',base=mode=='base',root={'if':expression,'then':'stop','else':'continue'})
                    r=execute(backend,budget,q,raw)
                    if (r.metadata['stop_reason']=='policy_stop' and r.metadata['checkpoint_count']==1)!=want:
                        raise RuntimeError('Native getter branch mismatch: '+n)
                raw=policy('fd-getter-availability-false',progress=mode=='progress',base=mode=='base',root={'if':{'op':'is_available','args':[{'feature':n}]},'then':'continue','else':'stop'})
                r=execute(backend,budget,q,raw)
                if r.metadata['stop_reason']=='policy_stop' and r.metadata['checkpoint_count']==1:raise RuntimeError('Availability false branch mismatch')
        reports.append({'profile':mode,'features':names,'backend_calls':budget.calls-start,'status':'passed'})
    if sum(r['backend_calls'] for r in reports)!=cfg['complete_call_accounting']['qualification_backend_calls_per_database_allocation']:
        raise RuntimeError('Getter accounting differs')
    return reports


def expected_progress(receipt,checkpoint,threshold):
    rows=[r for r in receipt['rows'] if r[0]<=checkpoint]
    windows=[w for w,n in zip(EARLY,receipt['fetches']) if w<=checkpoint and n]
    window=max(windows,default=0)
    passed=lambda r:threshold==0 or (not r[3] and r[2]>=threshold)
    valid=[r for r in rows if passed(r)];recent=[r for r in rows if r[0]==window]
    recent_valid=[r for r in recent if passed(r)];previous=[r for r in valid if r[0]!=window]
    minimum=min((r[4] for r in valid),default=0.)
    return {'progress_window_checkpoint':window,'progress_probe_examined':len(rows),'progress_probe_passed':len(valid),
      'progress_probe_pass_ratio':len(valid)/len(rows) if rows else 0.,
      'progress_recent_examined':len(recent),'progress_recent_passed':len(recent_valid),
      'progress_recent_pass_ratio':len(recent_valid)/len(recent) if recent else 0.,
      'progress_has_valid':bool(valid),'progress_valid_distance_min_or_zero':minimum,
      'progress_valid_distance_mean_or_zero':sum(r[4] for r in valid)/len(valid) if valid else 0.,
      'progress_valid_min_improvement_or_zero':max(0.,min(r[4] for r in previous)-minimum) if previous and valid else 0.}


def verify_progress(backend,q,states,nonce):
    receipt=json.loads(backend._connect().execute('SELECT fannagent.progress_probe()').fetchone()[0])
    if receipt['nonce']!=nonce or not receipt['enabled'] or len(receipt['fetches'])!=8 or any(n<0 or n>8 for n in receipt['fetches']):
        raise RuntimeError('Progress request binding/fetch budget differs')
    if sum(receipt['fetches'])>64 or len(receipt['rows'])>sum(receipt['fetches']) or receipt['nodes']>64:
        raise RuntimeError('Progress metadata budget exceeded')
    vector='['+','.join(format(float(v),'.9g') for v in q['vector'])+']'
    actual={r[0]:r[1:] for r in backend._connect().execute(
        'SELECT id,total_votes,embedding <=> %s::vector FROM public.reviews WHERE id=ANY(%s)',
        (vector,[r[1] for r in receipt['rows']])).fetchall()}
    for window,identifier,vote,null,distance in receipt['rows']:
        if window not in EARLY or identifier not in actual:raise RuntimeError('Progress sampled an undeclared node/window')
        v,d=actual[identifier]
        if (v is None)!=null or (not null and v!=vote) or abs(float(d)-distance)>1e-6:
            raise RuntimeError('Actual progress metadata/scored distance differs')
    threshold=0 if q.get('filter') is None else q['filter']['value']
    for state in states:
        wanted=expected_progress(receipt,state['checkpoint_index'],threshold)
        for name,value in wanted.items():
            observed=state['features'][name]
            if type(value) is bool:
                if type(observed) is not bool or observed!=value:raise RuntimeError('Boolean progress feature differs')
            elif not math.isclose(observed,value,rel_tol=1e-12,abs_tol=1e-12):raise RuntimeError('Causal progress feature differs: '+name)
    receipt['actual_metadata_sql_rows']={str(identifier):list(values) for identifier,values in actual.items()}
    return receipt


def acquire(backend,frozen,budget,items,package,out,notify):
    cfg=read(package/'experiment.json');names=cfg['static_feature_names'];original={q['query_id']:q for q in lines(package/'inputs/training-640-light.jsonl')}
    native_gold=read(package/'inputs/native-results.json');ordered=list(items);random.Random(SEED).shuffle(ordered)
    save(out/'qualified-features.json',qualify(backend,budget,items,cfg))
    evidence=[];reference_count=0
    with (out/'references.jsonl').open('x') as refs,(out/'proofs.jsonl').open('x') as proofs,(out/'pairs.jsonl').open('x') as pairs,(out/'warmups.jsonl').open('x') as warms,(out/'probe-verification.jsonl').open('x') as probes:
        for i,item in enumerate(ordered):
            q=item['query'];budget.reserve('exact_reference');truth=backend.exact_reference(q)
            native=execute(backend,budget,q);native_score=frozen.score(truth,native)
            if not native_score['valid'] or len(native.ids)!=10:raise RuntimeError('Incomplete native reference')
            if q['id'] in native_gold:
                gold=native_gold[q['id']]
                if (native.ids,native.distances,native_score['recall'])!=(gold['ids'],gold['distances'],gold['recall']):raise RuntimeError('Original native changed')
            static=execute(backend,budget,q,policy('fd-reference-static'),True);bs=prefix(static,names)
            old_receipt=verify_probe(backend,q,bs,static.metadata['request_nonce'])
            progress=execute(backend,budget,q,policy('fd-reference-progress',progress=True),True);ps=prefix(progress,names+EXTRA)
            progress_receipt=verify_progress(backend,q,ps,progress.metadata['request_nonce'])
            if [{**s,'features':{n:s['features'][n] for n in names}} for s in ps]!=bs:raise RuntimeError('Progress observations changed native traversal/static features')
            if q['id'] in original and [{**s,'features':{n:s['features'][n] for n in cfg['base_feature_names']}} for s in bs]!=original[q['id']]['states']:
                raise RuntimeError('Original qualified trajectory changed')
            if (static.ids,static.distances)!=(native.ids,native.distances) or (progress.ids,progress.distances)!=(native.ids,native.distances):raise RuntimeError('Observation changed native results')
            e={'query_id':q['id'],'group':item['group'],'role':item['role'],'stratum':q['id'].rsplit('-',1)[1],
               'native_recall':native_score['recall'],'native_work':static.metadata['work_counters']['layer0_distance_evaluations'],
               'base_states':bs,'local_states':ps,'labels':{'base':{},'local':{}},'continue_costs':{}}
            write(refs,{'query_id':q['id'],'native_ids':native.ids,'native_distances':native.distances,'native_recall':native_score['recall'],'base_states':bs,'local_states':ps})
            write(probes,{'query_id':q['id'],'static':old_receipt,'progress':progress_receipt,'actual_metadata_and_distance_verified':True})
            for family,is_progress,states in [('base',False,bs),('local',True,ps)]:
                for cp in [None,*[v for v in EARLY if v<=len(states)]]:
                    raw=policy('fd-acquire-'+family+'-'+str(cp),cp,progress=is_progress)
                    if cp is not None:
                        stopped=execute(backend,budget,q,raw,True)
                        if prefix(stopped,names+(EXTRA if is_progress else []))!=states[:cp] or stopped.metadata['stop_reason']!='policy_stop' or stopped.metadata['checkpoint_count']!=cp:
                            raise RuntimeError('Actual fixed-stop prefix differs')
                        write(proofs,{'query_id':q['id'],'family':family,'checkpoint':cp,'policy_hash':backend.validate_policy(raw).policy_hash,
                          'observed_prefix_sha256':digest(prefix(stopped,names+(EXTRA if is_progress else []))),
                          'policy_ids':stopped.ids,'policy_distances':stopped.distances})
                    install_eviction(backend,budget);retained=[]
                    for rep in range(3):
                        active=backend._installed==backend.validate_policy(raw).policy_hash
                        if active!=(rep>0):raise RuntimeError('Activation state differs')
                        row=pair(frozen,backend,budget,q,truth,raw,random.Random(SEED+reference_count),{
                          'phase':'acquisition','family':family,'checkpoint':cp,'role':item['role'],
                          'regime':'activation-cold' if rep==0 else 'reused-warm','repetition':0,'policy_already_activated':rep>0})
                        reference_count+=1
                        expected=(native.ids,native.distances) if cp is None else (stopped.ids,stopped.distances)
                        if (row['policy_ids'],row['policy_distances'])!=expected:raise RuntimeError('Timed fixed-stop result differs')
                        if rep==1:write(warms,row)
                        else:write(pairs,row);retained.append(row)
                    a,w=retained
                    label={'recall':a['policy_recall'],'valid':a['valid'],'returned_count':a['returned_count'],
                      'layer0_distances':a['work']['layer0_distance_evaluations'],
                      'activation_ms_saved':a['native_ms']-a['policy_ms'],'reuse_ms_saved':w['native_ms']-w['policy_ms']}
                    if cp is None:e['continue_costs'][family]=label
                    else:e['labels'][family][str(cp)]=label
            evidence.append(e);notify('acquisition',query=i+1,total=len(items),backend_searches=budget.calls)
    data={'version':'feature-data-acquisition.v1','base_feature_names':names,'queries':sorted(evidence,key=lambda q:q['query_id']),
          'model_calls':0,'confirmation_queries':0,'physical_index_sha256':sha(package/'source-index.json')}
    save(out/'evidence.json',data)
    return data


def validate_acquisition(folder,package):
    status=read(folder/'status.json')
    if status['status']!='complete' or read(folder/'host-exit.json')['exit_code'] or read(folder/'job-exit.json')['exit_code']:
        raise ValueError('Acquisition incomplete: '+str(folder))
    lock=read(folder/'LOCK.json')
    if lock['package_manifest_sha256']!=sha(package/'manifest.json'):raise ValueError('Acquisition package differs')
    for name,h in lock['files_sha256'].items():
        if sha(folder/name)!=h:raise ValueError('Acquisition evidence changed: '+name)
    return read(folder/'evidence.json')


def fit_study(package,campaign,out,notify):
    from tree_search import fit
    from fannagent_pgvector.profiles import PROFILE
    from fannagent.api import validate_policy
    parts=[validate_acquisition(campaign/'acquire'/('part-'+str(i)),package) for i in range(2)]
    rows=sum((p['queries'] for p in parts),[])
    if len(rows)!=600 or len({r['query_id'] for r in rows})!=600:raise ValueError('Training/calibration inventory differs')
    expected_counts={'original_learning':100,'additional_learning':60,'calibration':40}
    if {role:len({r['group'] for r in rows if r['role']==role}) for role in expected_counts}!=expected_counts:raise ValueError('Role inventory differs')
    calibration=[q for q in rows if q['role']=='calibration'];names=parts[0]['base_feature_names'];policies={};trials={};checks=0;fit_count=0
    for arm,spec in CONDITIONS.items():
        roles={'original_learning'}|({'additional_learning'} if spec['training_vectors']==160 else set())
        groups=sorted({q['group'] for q in rows if q['role'] in roles})
        if len(groups)!=spec['training_vectors'] or set(groups)&{q['group'] for q in calibration}:raise ValueError('Fitting/calibration leakage')
        candidates=[]
        for risk in CONFIG['risk_weights']:
            raw,proof=fit(rows,arm,risk,PROFILE,names,groups)
            # Every packed optimizer decision must agree with the full shared interpreter.
            family='local' if spec['local_filter'] else 'base'
            for q in rows:
                if q['group'] in set(groups):
                    if predict(raw,q[family+'_states'],PROFILE)!=proof['training_first_stops'][q['query_id']]:raise RuntimeError('Optimizer and shared interpreter differ')
                    checks+=1
            cases=replay(raw,calibration,arm,PROFILE);assessment=assess(cases)
            candidates.append({'risk':risk,'policy':raw,'proof':proof,'assessment':assessment,'calibration_replay':cases})
            fit_count+=1
            notify('calibration_fitting',arm=arm,risk=risk,conventional_fits=fit_count,total_fits=16,
                   backend_searches=0,provider_calls=0,recall_pass=assessment['recall_pass'],utility=assessment['utility'])
        eligible=[c for c in candidates if c['assessment']['recall_pass'] and c['assessment']['utility']>0]
        if eligible:
            chosen=sorted(eligible,key=lambda c:(-c['assessment']['utility'],-c['risk']))[0]
            raw=chosen['policy'];risk=chosen['risk']
            meaningful=any(r['checkpoint'] is not None for r in chosen['calibration_replay'])
        else:raw=policy('fd-'+arm+'-abstain',progress=spec['local_filter']);risk=None;meaningful=False
        policies[arm]={'policy':raw,'risk':risk,'policy_hash':validate_policy(raw,PROFILE).policy_hash,'training_groups':groups,
          'calibration_groups':sorted({q['group'] for q in calibration}),'nonconstant_selected_stop':meaningful}
        trials[arm]=candidates
    lock={'version':'feature-data-calibration-lock.v1','package_manifest_sha256':sha(package/'manifest.json'),
      'module_sha256':sha(campaign/'build/vector.so'),
      'acquisition_locks_sha256':{str(i):sha(campaign/'acquire'/('part-'+str(i))/'LOCK.json') for i in range(2)},
      'policies':policies,'trials':trials,'calibration_vectors':40,'shared_interpreter_checks':checks,
      'proceed_to_evaluation':any(p['nonconstant_selected_stop'] for p in policies.values()),
      'provider_calls':0,'confirmation_queries':0,'ab_comparison':AB,'canonical_acceptance_established':False,
      'timing_status':'new fitted-policy latency unmeasured'}
    save(out/'fit-lock.json',lock)
    return lock


def validate_fit(package,folder):
    lock=read(folder/'fit-lock.json');receipt=read(folder/'LOCK.json')
    if lock['package_manifest_sha256']!=sha(package/'manifest.json') or receipt['files_sha256']['fit-lock.json']!=sha(folder/'fit-lock.json'):
        raise ValueError('Frozen fit lock differs')
    if lock['ab_comparison']!=AB or lock['provider_calls'] or lock['confirmation_queries']:raise ValueError('Fit provenance differs')
    if sha(folder.parent/'build/vector.so')!=lock['module_sha256']:raise ValueError('Fitted module changed')
    for part,h in lock['acquisition_locks_sha256'].items():
        if sha(folder.parent/'acquire'/('part-'+part)/'LOCK.json')!=h:raise ValueError('Fitting input lock changed')
    return lock


def evaluate_candidates(backend,frozen,budget,package,campaign,out,evidence):
    from fannagent_pgvector.profiles import PROFILE
    lock=validate_fit(package,campaign/'fit');items=lines(package/'inputs/evaluation.jsonl');data={q['query_id']:q for q in evidence['queries']}
    if {i['group'] for i in items}&{g for p in lock['policies'].values() for g in p['training_groups']+p['calibration_groups']}:
        raise RuntimeError('Common evaluation overlaps fitting/calibration')
    records={arm:[] for arm in CONDITIONS}
    native_refs={x['query_id']:x for x in lines(out/'references.jsonl')}
    stopped_refs={(x['query_id'],x['family'],x['checkpoint']):x for x in lines(out/'proofs.jsonl')}
    with (out/'candidate-proofs.jsonl').open('x') as proofs:
        for item in items:
            q=item['query'];source=data[q['id']]
            for arm,p in lock['policies'].items():
                raw=p['policy'];progress=CONDITIONS[arm]['local_filter'];family='local' if progress else 'base'
                names=read(package/'experiment.json')['static_feature_names']+(EXTRA if progress else [])
                cp=predict(raw,source[family+'_states'],PROFILE)
                result=execute(backend,budget,q,raw,True)
                if prefix(result,names)!=(source[family+'_states'] if cp is None else source[family+'_states'][:cp]):raise RuntimeError('Locked actual policy prefix differs')
                if (result.metadata['stop_reason']=='policy_stop')!=(cp is not None):raise RuntimeError('Actual first stop differs')
                r=replay(raw,[source],arm,PROFILE)[0]
                # The exact reference was already acquired above; stopped proof must
                # match the actually acquired outcome at this same first checkpoint.
                native_ref=native_refs[q['id']]
                if cp is None:
                    expected=(native_ref['native_ids'],native_ref['native_distances'])
                else:
                    proof=stopped_refs[(q['id'],family,cp)]
                    expected=(proof['policy_ids'],proof['policy_distances'])
                if (result.ids,result.distances)!=expected:raise RuntimeError('Actual candidate outcome differs from measured label')
                records[arm].append(r)
                write(proofs,{'arm':arm,'query_id':q['id'],'checkpoint':cp,'policy_hash':p['policy_hash'],
                             'policy_ids':result.ids,'policy_distances':result.distances,'replay':r})
    reports={arm:assess(rows,tolerance=.005) for arm,rows in records.items()}
    for arm,r in reports.items():
        r['nonconstant_stop_cases']=sum(x['checkpoint'] is not None for x in records[arm])
        r['eligible_for_timing']=bool(lock['policies'][arm]['nonconstant_selected_stop'] and r['recall_pass'] and r['utility']>0)
    screen={'status':'complete','reports':reports,'proceed_to_timing':any(r['eligible_for_timing'] for r in reports.values()),
      'fit_lock_sha256':sha(campaign/'fit/fit-lock.json'),'provider_calls':0,'confirmation_queries':0,'ab_comparison':AB,
      'canonical_acceptance_established':False,'final_latency_gate':'unmeasured'}
    save(out/'screen.json',screen);return screen


def arms_for(q,lock):
    arms=[(a,p['policy'],'condition') for a,p in lock['policies'].items()]
    arms += [('continue-static',policy('fd-continue-static'),'continue'),
             ('continue-progress',policy('fd-continue-progress',progress=True),'continue')]
    cp=min((int(cp) for cp,l in q['labels']['base'].items() if l['valid'] and l['returned_count']==10 and l['recall']>=q['native_recall']),default=None)
    arms += [('oracle-sparse',policy('fd-oracle',cp,base=True),'oracle'),
             ('P160-native108',lock['policies']['P160']['policy'],'routing-control')]
    if len(arms)!=8:raise RuntimeError('Undeclared timing arms')
    return arms


def bypass108(q):
    # Actual validated query predicate, never the evaluator's stratum or query ID.
    predicate=q.get('filter')
    if predicate is None:return False
    if not (isinstance(predicate,dict) and set(predicate)=={'field','op','value'} and
            predicate['field']=='m_000000' and predicate['op']=='gte' and
            type(predicate['value']) is int and predicate['value'] in (32,108)):
        raise ValueError('Routing control requires the declared actual predicate')
    return predicate['value']==108


def timing_pair(frozen,backend,budget,q,truth,raw,rng,meta,routed):
    artifact=backend.validate_policy(raw);modes=['native','policy'];rng.shuffle(modes);results={};outer={};routing=0.;bypassed=False
    for mode in modes:
        started=time.perf_counter_ns();use=None if mode=='native' else raw
        if mode=='policy' and routed:
            decision_started=time.perf_counter_ns();bypassed=bypass108(q)
            use=None if bypassed else raw
            routing=(time.perf_counter_ns()-decision_started)/1e6
        results[mode]=execute(backend,budget,q,use)
        outer[mode]=(time.perf_counter_ns()-started)/1e6
    scores={m:frozen.score(truth,r) for m,r in results.items()};r=results['policy'];g,f=q['id'].rsplit('-',1)
    if not scores['native']['valid'] or len(results['native'].ids)!=10:raise RuntimeError('Incomplete native timing result')
    return {**meta,'query_id':q['id'],'group':g,'stratum':f,'policy_hash':None if bypassed else artifact.policy_hash,
      'order':modes,'native_ms':results['native'].latency_ms,'policy_ms':r.latency_ms+routing,
      'policy_ann_ms':r.latency_ms,'routing_ms':routing,'native_bypass':bypassed,'work_available':not bypassed,
      'native_outer_ms':outer['native'],'policy_outer_ms':outer['policy'],
      'native_recall':scores['native']['recall'],'policy_recall':scores['policy']['recall'],
      'recall_delta':scores['policy']['recall']-scores['native']['recall'],
      'valid':bool(scores['policy']['valid'] and len(r.ids)==10),'returned_count':len(r.ids),
      'work':None if bypassed else r.metadata['work_counters'],'native_ids':results['native'].ids,'native_distances':results['native'].distances,
      'policy_ids':r.ids,'policy_distances':r.distances,'truth_strict':sorted(truth.strictly_better),'truth_ties':sorted(truth.boundary_ties),'truth_k':truth.effective_k}


def measure(backend,frozen,budget,package,campaign,out,block,notify):
    from fannagent_pgvector.profiles import PROFILE
    cfg=read(package/'experiment.json');lock=validate_fit(package,campaign/'fit')
    screen=read(campaign/'evaluate/screen.json')
    if not screen['proceed_to_timing'] or screen['fit_lock_sha256']!=sha(campaign/'fit/fit-lock.json'):raise RuntimeError('No verified common-evaluation gate')
    source=validate_acquisition(campaign/'evaluate',package);data={q['query_id']:q for q in source['queries']}
    items=lines(package/'inputs/evaluation.jsonl');random.Random(SEED+block).shuffle(items)
    save(out/'qualified-features.json',qualify(backend,budget,items,cfg));retained=0;pair_rng=random.Random(SEED+block)
    with (out/'pairs.jsonl').open('x') as pairs,(out/'warmups.jsonl').open('x') as warms,(out/'proofs.jsonl').open('x') as proofs:
        for i,item in enumerate(items):
            q=item['query'];known=data[q['id']];budget.reserve('exact_reference');truth=backend.exact_reference(q)
            native=execute(backend,budget,q)
            if frozen.score(truth,native)['recall']!=known['native_recall']:raise RuntimeError('Evaluation native changed')
            for progress,family in [(False,'base'),(True,'local')]:
                ref=execute(backend,budget,q,policy('fd-block-reference',progress=progress),True)
                if prefix(ref,cfg['static_feature_names']+(EXTRA if progress else []))!=known[family+'_states']:
                    raise RuntimeError('Observed trajectory changed between allocations')
                if (ref.ids,ref.distances)!=(native.ids,native.distances):raise RuntimeError('Continue/native result differs')
            arms=arms_for(known,lock);random.Random(int(digest([SEED,q['id']]),16)).shuffle(arms)
            offset=len(arms)*block//3;arms=arms[offset:]+arms[:offset]
            for arm,raw,kind in arms:
                routed=kind=='routing-control';bypassed=routed and bypass108(q)
                progress='progress_filter' in raw['feature_groups'];base='local_filter' not in raw['feature_groups']
                names=cfg['base_feature_names'] if base else cfg['static_feature_names']+(EXTRA if progress else [])
                states=known['local_states' if progress else 'base_states']
                if base:states=[{**s,'features':{n:s['features'][n] for n in names}} for s in states]
                cp=None if bypassed else predict(raw,states,PROFILE)
                traced=execute(backend,budget,q,None if bypassed else raw,not bypassed)
                observed=None if bypassed else prefix(traced,names)
                if not bypassed and observed!=(states if cp is None else states[:cp]):raise RuntimeError('Actual timed-arm prefix differs')
                if not bypassed and (traced.metadata['stop_reason']=='policy_stop')!=(cp is not None):raise RuntimeError('Actual timed-arm stop differs')
                if (cp is None or kind=='continue') and (traced.ids,traced.distances)!=(native.ids,native.distances):raise RuntimeError('Continue/bypass changed native results')
                write(proofs,{'arm':arm,'query_id':q['id'],'checkpoint':cp,'native_bypass':bypassed,
                  'policy_hash':None if bypassed else backend.validate_policy(raw).policy_hash,
                  'observed_prefix_sha256':None if bypassed else digest(observed),'policy_ids':traced.ids,'policy_distances':traced.distances})
                install_eviction(backend,budget)
                for rep in range(5):
                    if not bypassed and (backend._installed==backend.validate_policy(raw).policy_hash)!=(rep>0):raise RuntimeError('Timing activation state differs')
                    row=timing_pair(frozen,backend,budget,q,truth,raw,pair_rng,{
                      'block':block,'arm':arm,'kind':kind,'regime':'activation-cold' if rep==0 else 'reused-warm',
                      'repetition':0 if rep==0 else rep-2,'policy_already_activated':None if bypassed else rep>0},routed)
                    if (row['policy_ids'],row['policy_distances'])!=(traced.ids,traced.distances):raise RuntimeError('Timed output differs from proof')
                    if rep==1:write(warms,row)
                    else:write(pairs,row);retained+=1
            notify('measurement',query=i+1,total=len(items),backend_searches=budget.calls,retained_pairs=retained)
    if retained!=cfg['complete_call_accounting']['timing_retained_pairs_per_block']:raise RuntimeError('Incomplete retained timing coverage')
    return retained
