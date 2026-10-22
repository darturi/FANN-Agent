"""Actual native acquisition, qualification and paired timing; no model imports."""
import collections
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
import time

from contract import CONFIG, CONDITIONS, EARLY, EXTRA, GROUPS, SEED, digest, lines, read, save, sha


class Budget:
    def __init__(self, maximum, seconds=6600):
        self.maximum = maximum; self.seconds = seconds; self.started = time.monotonic()
        self.calls = 0; self.operations = collections.Counter(); self.control_installations = 0

    def reserve(self, operation):
        if self.calls >= self.maximum or time.monotonic() - self.started > self.seconds:
            raise RuntimeError('Predeclared backend/time budget exhausted')
        self.calls += 1; self.operations[operation] += 1


def load_backend(package):
    # Import the staged, pinned adapter first. The frozen runner's later sys.path
    # insertion cannot replace an already imported package and its __path__.
    sys.path.insert(0, '/opt/torch-reviews/vendor')
    sys.path.insert(0, str(package))
    sys.path.insert(0, str(package / 'vendor'))
    import fannagent_pgvector.backend
    spec = importlib.util.spec_from_file_location('four_frozen_reviews', '/opt/torch-reviews/runner.py')
    frozen = importlib.util.module_from_spec(spec); spec.loader.exec_module(frozen)
    from reference_backend import ExactReferenceMixin
    class Backend(ExactReferenceMixin, frozen.TorchBackend):
        pass
    return frozen, Backend


def policy(name, cp=None, local=False, root=None):
    if root is None:
        root = 'continue' if cp is None else {'if': {'op': 'gte', 'args': [{'feature':'checkpoint_index'}, {'int':cp}]}, 'then':'stop', 'else':'continue'}
    return {'name':name, 'root':root, 'feature_groups':GROUPS + (['local_filter'] if local else [])}


def matched(raw):
    def node(n):
        return 'continue' if isinstance(n,str) else {'if':n['if'], 'then':node(n['then']), 'else':node(n['else'])}
    return {**raw, 'name':'matched-' + raw['name'], 'root':node(raw['root'])}


def execute(backend, budget, q, raw=None, trace=False):
    budget.reserve('policy_trace' if trace else 'policy' if raw is not None else 'native')
    result = backend.execute_probe(q, mode='policy' if raw is not None else 'native',
        policy=backend.validate_policy(raw) if raw is not None else None, trace=trace)
    if raw is not None:
        m = result.metadata
        if not m.get('policy_applied') or m.get('policy_fallback') or m.get('policy_runtime_error'):
            raise RuntimeError('Policy was not cleanly acknowledged')
    return result


def prefix(result, names):
    if not result.evidence or result.evidence['truncated']: raise RuntimeError('Missing/truncated native trace')
    return [{'checkpoint_index':c['index'], 'features':{n:c['features'].get(n) for n in names}} for c in result.evidence['checkpoints']]


def pair(frozen, backend, budget, q, truth, raw, rng, metadata):
    artifact = backend.validate_policy(raw)
    modes = ['native','policy']; rng.shuffle(modes); results = {}; outer = {}
    for mode in modes:
        clock = time.perf_counter_ns()
        results[mode] = execute(backend, budget, q, raw if mode == 'policy' else None)
        outer[mode] = (time.perf_counter_ns() - clock) / 1e6
    score = {m:frozen.score(truth,r) for m,r in results.items()}
    if not score['native']['valid'] or len(results['native'].ids) != 10: raise RuntimeError('Invalid/incomplete native reference')
    t = results['policy']; group,stratum = q['id'].rsplit('-',1)
    return {**metadata, 'query_id':q['id'], 'group':group, 'stratum':stratum,
        'policy_hash':artifact.policy_hash, 'order':modes,
        'native_ms':results['native'].latency_ms, 'policy_ms':t.latency_ms,
        'native_outer_ms':outer['native'], 'policy_outer_ms':outer['policy'],
        'native_recall':score['native']['recall'], 'policy_recall':score['policy']['recall'],
        'recall_delta':score['policy']['recall']-score['native']['recall'],
        'valid':bool(score['policy']['valid'] and len(t.ids)==10), 'returned_count':len(t.ids),
        'stop_reason':t.metadata['stop_reason'], 'checkpoint_count':t.metadata['checkpoint_count'],
        'work':t.metadata['work_counters'], 'native_ids':results['native'].ids, 'native_distances':results['native'].distances,
        'policy_ids':t.ids, 'policy_distances':t.distances,
        'truth_strict':sorted(truth.strictly_better), 'truth_ties':sorted(truth.boundary_ties), 'truth_k':truth.effective_k}


def install_eviction(backend,budget):
    raw = policy('four-eviction')
    artifact = backend.validate_policy(raw)
    if backend.install_policy(artifact)['policy_hash'] != artifact.policy_hash: raise RuntimeError('Eviction acknowledgement differs')
    budget.control_installations += 1


def write(handle, value):
    handle.write(json.dumps(value,sort_keys=True,allow_nan=False)+'\n'); handle.flush()


def qualify_getters(backend,budget,items,names,local):
    from fannagent_pgvector.profiles import PROFILE
    calls = 0
    for f in CONFIG['filters']:
        q = next(i['query'] for i in items if i['query']['id'].endswith('-'+f))
        ref = execute(backend,budget,q,policy('four-getter-reference',local=local),True); calls += 1
        values = prefix(ref,names)[0]['features']
        for name in names:
            value = values[name]
            if value is None: raise RuntimeError('Qualification getter unavailable: '+name)
            kind=PROFILE.runtime_features[name].kind
            if kind=='int' and type(value) is not int:raise RuntimeError('Integer getter has noninteger value: '+name)
            bounds = [value,value+1] if kind=='int' else [float(value),1e-12 if float(value)==0 else math.nextafter(float(value),math.inf)]
            for want,bound in zip((True,False),bounds):
                root = {'if':{'op':'gte','args':[{'feature':name},{'int' if type(bound) is int else 'float':bound}]},'then':'stop','else':'continue'}
                r = execute(backend,budget,q,policy('four-getter-'+name,local=local,root=root)); calls += 1
                if (r.metadata['stop_reason']=='policy_stop' and r.metadata['checkpoint_count']==1) != want:
                    raise RuntimeError('Numeric getter branch differs: '+name)
            for want in (True,False):
                root = {'if':{'op':'is_available','args':[{'feature':name}]},'then':'stop' if want else 'continue','else':'continue' if want else 'stop'}
                r = execute(backend,budget,q,policy('four-availability-'+name,local=local,root=root)); calls += 1
                if (r.metadata['stop_reason']=='policy_stop' and r.metadata['checkpoint_count']==1) != want:
                    raise RuntimeError('Availability getter branch differs: '+name)
    assert calls == 3*(1+4*len(names))
    return {'status':'passed','backend_calls':calls,'features':names,'local_filter':local}


def verify_probe(backend,q,states,nonce=None):
    receipt = json.loads(backend._connect().execute('SELECT fannagent.local_probe()').fetchone()[0])
    if nonce is not None and receipt.get('nonce')!=nonce:raise RuntimeError('Probe audit belongs to another request')
    if not receipt['enabled'] or not 0 < receipt['nodes'] <= 64 or not 0 < receipt['examined'] <= 64:
        raise RuntimeError('Bounded local probe did not execute')
    sample = receipt['rows']
    if len(sample) != receipt['examined']: raise RuntimeError('Probe receipt count differs')
    actual = {r[0]:r[1] for r in backend._connect().execute('SELECT id,total_votes FROM public.reviews WHERE id=ANY(%s)',([r[0] for r in sample],)).fetchall()}
    for identifier,vote,null in sample:
        if identifier not in actual or (actual[identifier] is None) != null or (not null and actual[identifier] != vote):
            raise RuntimeError('Probe metadata does not reproduce from the query snapshot')
    threshold = 0 if q.get('filter') is None else q['filter']['value']
    previous = 0
    for state in states:
        f = state['features']; n = f['local_probe_examined']
        expected = sum(q.get('filter') is None or (not null and vote >= threshold) for _,vote,null in sample[:n])
        if not previous <= n <= len(sample) or f['query_predicate_threshold'] != threshold or f['local_probe_passed'] != expected:
            raise RuntimeError('Probe prefix or predicate binding differs')
        if (f['local_probe_pass_ratio'] is None) != (n == 0): raise RuntimeError('Probe ratio availability differs')
        if n and abs(f['local_probe_pass_ratio']-expected/n)>1e-12: raise RuntimeError('Probe ratio differs')
        previous = n
    return {'query_id':q['id'], 'receipt':receipt, 'actual_metadata_verified':True,
        'causal_prefix_feature_checks':len(states), 'metadata_SQL_reads':1}


def acquisition(frozen,Backend,bundle,work,package,out,budget,notify):
    cfg = read(package/'experiment.json'); items = lines(package/'inputs/queries.jsonl')
    base_names = cfg['base_feature_names']; local_names = base_names + EXTRA
    original = {r['query_id']:r for r in lines(package/'inputs/training-640-light.jsonl')}
    expected_results = read(package/'inputs/native-results.json')
    backend = Backend(bundle,work); backend.state['source_manifest']['settings']['hnsw.ef_search']='640'
    rng = random.Random(SEED); ordered=list(items); rng.shuffle(ordered); evidence=[]
    try:
        getter = [qualify_getters(backend,budget,items,base_names,False),qualify_getters(backend,budget,items,local_names,True)]
        save(out/'qualified-features.json',getter)
        with (out/'references.jsonl').open('x') as refs,(out/'pairs.jsonl').open('x') as pairs,(out/'warmups.jsonl').open('x') as warms,(out/'proofs.jsonl').open('x') as proofs,(out/'probe-verification.jsonl').open('x') as probes:
            for index,item in enumerate(ordered):
                q=item['query']; budget.reserve('exact_reference'); truth=backend.exact_reference(q)
                native=execute(backend,budget,q); native_score=frozen.score(truth,native)
                expected=expected_results[q['id']]
                if native.ids!=expected['ids'] or native.distances!=expected['distances'] or native_score['recall']!=expected['recall']:
                    raise RuntimeError('Original native output changed: '+q['id'])
                base=execute(backend,budget,q,policy('four-reference-base'),True)
                local=execute(backend,budget,q,policy('four-reference-local',local=True),True)
                bs=prefix(base,base_names); ls=prefix(local,local_names)
                if bs!=original[q['id']]['states'] or [{**s,'features':{n:s['features'][n] for n in base_names}} for s in ls]!=bs:
                    raise RuntimeError('Base/local traversal differs from the original qualified prefix')
                if (base.ids,base.distances)!=(native.ids,native.distances) or (local.ids,local.distances)!=(native.ids,native.distances):
                    raise RuntimeError('Continue result differs')
                write(probes,verify_probe(backend,q,ls,local.metadata['request_nonce']))
                e={'query_id':q['id'],'group':q['id'].rsplit('-',1)[0],'stratum':q['id'].rsplit('-',1)[1],
                    'native_recall':native_score['recall'],'native_work':base.metadata['work_counters']['layer0_distance_evaluations'],
                    'base_states':bs,'local_states':ls,'labels':{'base':{},'local':{}},'continue_costs':{}}
                write(refs,{'query_id':q['id'],'native_ids':native.ids,'native_distances':native.distances,
                    'native_recall':e['native_recall'],'base_states':bs,'local_states':ls})
                for family,is_local,states in [('base',False,bs),('local',True,ls)]:
                    # Continue cost is measured without tracing, including activation.
                    for cp in [None,*[v for v in EARLY if v<=len(states)]]:
                        raw=policy('four-acquire-'+family+'-'+str(cp),cp,is_local)
                        if cp is not None:
                            r=execute(backend,budget,q,raw,True)
                            if prefix(r,local_names if is_local else base_names)!=states[:cp] or r.metadata['stop_reason']!='policy_stop' or r.metadata['checkpoint_count']!=cp:
                                raise RuntimeError('Actual stop prefix differs')
                            score=frozen.score(truth,r)
                            write(proofs,{'query_id':q['id'],'family':family,'checkpoint':cp,'policy_hash':backend.validate_policy(raw).policy_hash,
                                'observed_prefix':prefix(r,local_names if is_local else base_names),'policy_ids':r.ids,'policy_distances':r.distances,
                                'recall':score['recall'],'valid':bool(score['valid'] and len(r.ids)==10)})
                        install_eviction(backend,budget); retained=[]
                        for rep in range(3):
                            expected_active = backend._installed == backend.validate_policy(raw).policy_hash
                            if expected_active != (rep > 0): raise RuntimeError('Acquisition activation state differs')
                            meta={'phase':'acquisition','family':family,'checkpoint':cp,'arm':family+'/'+str(cp),
                                'regime':'activation-cold' if rep==0 else 'reused-warm','repetition':0,
                                'policy_already_activated':rep>0}
                            row=pair(frozen,backend,budget,q,truth,raw,rng,meta)
                            if cp is not None and (row['policy_ids'],row['policy_distances'])!=(r.ids,r.distances): raise RuntimeError('Timed acquisition outcome differs')
                            if cp is None and (row['policy_ids'],row['policy_distances'])!=(native.ids,native.distances): raise RuntimeError('Continue cost result differs')
                            if rep==1: write(warms,row)
                            else: write(pairs,row); retained.append(row)
                        a,w=retained
                        label={'recall':a['policy_recall'],'valid':a['valid'],'returned_count':a['returned_count'],
                            'layer0_distances':a['work']['layer0_distance_evaluations'],
                            'activation_ms_saved':a['native_ms']-a['policy_ms'],'reuse_ms_saved':w['native_ms']-w['policy_ms']}
                        if cp is None:e['continue_costs'][family]=label
                        else:e['labels'][family][str(cp)]=label
                evidence.append(e);notify('acquisition',query=index+1,total=300,backend_searches=budget.calls)
        result={'version':'four-condition-acquisition.v1','base_feature_names':base_names,'queries':sorted(evidence,key=lambda q:q['query_id']),
            'model_calls':0,'confirmation_queries':0,'physical_index_sha256':sha(package/'source-index.json')}
        save(out/'evidence.json',result)
        from fitting import build_lock
        notify('nested_group_fitting',backend_searches=budget.calls)
        lock=build_lock(result,frozen.PROFILE,sha(package/'manifest.json'),sha('/opt/postgresql/lib/vector.so'))
        save(out/'fit-lock.json',lock)
        save(out/'LOCK.json',{'status':'frozen_before_measurement','evidence_sha256':sha(out/'evidence.json'),
            'fit_lock_sha256':sha(out/'fit-lock.json'),'package_manifest_sha256':sha(package/'manifest.json'),
            'module_sha256':sha('/opt/postgresql/lib/vector.so'),'policies':20,'outer_folds':5,
            'raw_files_sha256':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in {'progress.json','LOCK.json'}}})
        if time.monotonic()-budget.started>6600:raise RuntimeError('Acquisition/fitting exceeded allocation budget')
        return {'status':'complete','stage':'acquisition-and-fitting','training_queries':300,'confirmation_queries':0,
            'provider_calls':0,'backend_searches':budget.calls,'operations':dict(budget.operations),
            'probe_receipt_sql_reads':len(items),'metadata_verification_sql_reads':len(items),
            'control_installations':budget.control_installations,'frozen_policies':20,'new_actual_stop_outcomes':sum(len(q['labels']['base'])+len(q['labels']['local']) for q in evidence)}
    finally: backend.close()


def validate_lock(package,gate):
    cfg=read(package/'experiment.json'); receipt=read(gate/'LOCK.json'); lock=read(gate/'fit-lock.json'); evidence=read(gate/'evidence.json')
    if receipt['status']!='frozen_before_measurement' or receipt['package_manifest_sha256']!=sha(package/'manifest.json'):
        raise ValueError('No valid premeasurement lock')
    if receipt['fit_lock_sha256']!=sha(gate/'fit-lock.json') or receipt['evidence_sha256']!=sha(gate/'evidence.json'):
        raise ValueError('Fit/evidence changed after freeze')
    if lock['evidence_sha256']!=digest(evidence) or lock['ab_comparison']!=cfg['ab_comparison'] or lock['provider_calls']:
        raise ValueError('Fit provenance differs')
    for name,h in receipt['raw_files_sha256'].items():
        if sha(gate/name)!=h:raise ValueError('Acquisition source changed: '+name)
    for key,p in lock['policies'].items():
        condition,fold=key.split('/')
        if set(p['training_groups'])&set(p['held_out_groups']):raise ValueError('Outer validation leakage')
        if p['held_out_groups']!=sorted(g for g,f in lock['folds'].items() if f==int(fold)):raise ValueError('Fold coverage differs')
        if p['training_groups']!=sorted(g for g,f in lock['folds'].items() if f!=int(fold)):raise ValueError('Training coverage differs')
        if ('local_filter' in p['policy']['feature_groups'])!=CONDITIONS[condition]['local_filter']:raise ValueError('Feature condition differs')
    return lock,evidence


def arms_for(q,lock):
    fold=lock['folds'][q['group']]; arms=[]
    for condition in CONDITIONS:
        item=lock['policies'][condition+'/'+str(fold)];raw=item['policy']
        arms += [(condition,raw,'condition'),('matched-'+condition,matched(raw),'matched-continue')]
    for family,local in [('base',False),('local',True)]:arms.append(('continue-'+family,policy('four-continue-'+family,local=local),'continue'))
    for n in (4096,8192):
        raw=policy('four-fixed-'+str(n),root={'if':{'op':'gte','args':[{'feature':'layer0_distance_evaluations'},{'int':n}]},'then':'stop','else':'continue'})
        arms.append(('fixed-'+str(n),raw,'fixed'))
    cp=min((int(cp) for cp,r in q['labels']['base'].items() if r['valid'] and r['returned_count']==10 and r['recall']>=q['native_recall']),default=None)
    arms.append(('oracle-sparse',policy('four-oracle',cp),'oracle'))
    assert len(arms)==13
    return arms


def measurement(frozen,Backend,bundle,work,package,out,gate,block,budget,notify):
    from fitting import predict
    cfg=read(package/'experiment.json');lock,evidence=validate_lock(package,gate)
    if lock['module_sha256']!=sha('/opt/postgresql/lib/vector.so'):raise ValueError('Measured module differs from fitted/qualified module')
    data={q['query_id']:q for q in evidence['queries']};items=lines(package/'inputs/queries.jsonl')
    backend=Backend(bundle,work);backend.state['source_manifest']['settings']['hnsw.ef_search']='640';rng=random.Random(SEED+block)
    ordered=list(items);rng.shuffle(ordered);count=0
    try:
        save(out/'qualified-features.json',[qualify_getters(backend,budget,items,cfg['base_feature_names'],False),
            qualify_getters(backend,budget,items,cfg['base_feature_names']+EXTRA,True)])
        with (out/'pairs.jsonl').open('x') as pairs,(out/'warmups.jsonl').open('x') as warmups,(out/'proofs.jsonl').open('x') as proofs:
            for index,item in enumerate(ordered):
                q=item['query'];source=data[q['id']];budget.reserve('exact_reference');truth=backend.exact_reference(q)
                native=execute(backend,budget,q)
                if frozen.score(truth,native)['recall']!=source['native_recall']:raise RuntimeError('Native recall changed')
                # Reproduce both causal feature trajectories in every allocation.
                for family,local in [('base',False),('local',True)]:
                    ref=execute(backend,budget,q,policy('four-block-reference-'+family,local=local),True)
                    if prefix(ref,cfg['base_feature_names']+(EXTRA if local else []))!=source[family+'_states']:
                        raise RuntimeError('Acquired observations changed between allocations')
                    if (ref.ids,ref.distances)!=(native.ids,native.distances):raise RuntimeError('Reference result differs')
                arms=arms_for(source,lock);arm_rng=random.Random(int(digest([SEED,q['id']]),16));arm_rng.shuffle(arms)
                offset=len(arms)*block//3;arms=arms[offset:]+arms[:offset]
                for arm,raw,kind in arms:
                    local='local_filter' in raw['feature_groups'];names=cfg['base_feature_names']+(EXTRA if local else [])
                    states=source['local_states' if local else 'base_states'];predicted=predict(raw,states,frozen.PROFILE)
                    traced=execute(backend,budget,q,raw,True)
                    if prefix(traced,names)!=(states if predicted is None else states[:predicted]):raise RuntimeError('Actual first-stop prefix differs')
                    if (traced.metadata['stop_reason']=='policy_stop')!=(predicted is not None):raise RuntimeError('Actual first stop differs')
                    if kind in ('continue','matched-continue') and (traced.ids,traced.distances)!=(native.ids,native.distances):raise RuntimeError('Matched/native result differs')
                    write(proofs,{'arm':arm,'query_id':q['id'],'fold':lock['folds'][source['group']],
                        'predicted_checkpoint':predicted,'policy_hash':backend.validate_policy(raw).policy_hash,
                        'observed_prefix_sha256':digest(prefix(traced,names)),'policy_ids':traced.ids,'policy_distances':traced.distances})
                    install_eviction(backend,budget)
                    for rep in range(5):
                        expected_active = backend._installed == backend.validate_policy(raw).policy_hash
                        if expected_active != (rep > 0): raise RuntimeError('Measurement activation state differs')
                        row=pair(frozen,backend,budget,q,truth,raw,rng,{'phase':'measurement','block':block,'arm':arm,'kind':kind,
                            'fold':lock['folds'][source['group']],'regime':'activation-cold' if rep==0 else 'reused-warm',
                            'repetition':0 if rep==0 else rep-2,'policy_already_activated':rep>0,'local_filter':local})
                        if (row['policy_ids'],row['policy_distances'])!=(traced.ids,traced.distances):raise RuntimeError('Timed output differs from qualified output')
                        if rep==1:write(warmups,row)
                        else:write(pairs,row);count+=1
                notify('measurement',query=index+1,total=300,backend_searches=budget.calls,retained_pairs=count)
        if count!=cfg['complete_call_accounting']['retained_pairs_per_block']:raise RuntimeError('Incomplete timed coverage')
        return {'status':'complete','stage':'training-measurement','block':block,'retained_pairs':count,
            'training_queries':300,'confirmation_queries':0,'provider_calls':0,'backend_searches':budget.calls,
            'operations':dict(budget.operations),'control_installations':budget.control_installations,
            'fit_lock_sha256':sha(gate/'fit-lock.json'),'canonical_acceptance_established':False}
    finally:backend.close()
