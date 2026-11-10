"""Strict selective execution and actual paired measurements; no model imports."""
import json
import random
import time
from pathlib import Path
from contract import CONFIG,FILTERS,EARLY,read,save,sha,digest,lines
from policy import validate,route,compose,matched,states,names,first_stop
from legacy_execution import Budget,prefix,install_eviction,write,execute as native_execute
from fd_execution import qualify

def load_backend(package):
    from legacy_execution import load_backend as load
    frozen,Base=load(package)
    from fannagent_pgvector.profiles import PROFILE
    class Backend(Base):
        runtime_profile=PROFILE
    return frozen,Backend

class Session:
    """Owned immutable policy; cold validation charged, tree compilation stays lazy."""
    def __init__(self,backend,raw,cfg):
        started=time.perf_counter_ns()
        self.backend=backend;self.raw,self.identity=validate(raw,cfg)
        self.k=cfg['k'];self.connection=backend.conn;self.preparation_ms=(time.perf_counter_ns()-started)/1e6

    def query(self,q,budget,*,trace=False):
        started=time.perf_counter_ns()
        b=self.backend
        with b._operation_lock:
            if b.conn is not self.connection or b.conn is None or b.conn.closed:raise RuntimeError('Selective session connection changed; create a new session')
            q=b.snapshot().query(q)
            bypass=q.get('k')!=self.k or route(q) not in self.raw['eligible']
            routing_ms=(time.perf_counter_ns()-started)/1e6
            budget.reserve('native_bypass' if bypass else 'policy_trace' if trace else 'policy')
            # Ordinary native SQL on bypass, including under trace/audit qualification.
            r=b.execute_probe(q,mode='native' if bypass else 'policy',policy=None if bypass else self.raw['tree'],trace=trace and not bypass)
            if not bypass and (not r.metadata.get('policy_applied') or r.metadata.get('policy_fallback') or r.metadata.get('policy_runtime_error')):
                raise RuntimeError('Policy not cleanly acknowledged')
            r.metadata.update(native_bypass=bypass,requested_composite_hash=self.identity,
                policy_ann_ms=r.latency_ms,routing_ms=routing_ms)
            r.latency_ms+=routing_ms
            return r

def arms_for(candidates,q,stage,cfg):
    arms=[]
    for identity,receipt in sorted(candidates.items()):
        raw=receipt['policy'];arms.extend([(identity,raw,'candidate'),('matched-'+identity,matched(raw),'matched')])
    # Empty mask is deliberately host-only: it cannot be exported as a learned policy.
    native=compose('native-route-control','continue');native['eligible']=[]
    arms.append(('routed-native',native,'native-control'))
    if stage!='confirmation':
        labels=q['labels']['base'];cp=next((cp for cp in EARLY if str(cp) in labels and labels[str(cp)]['valid'] and labels[str(cp)]['returned_count']==10 and labels[str(cp)]['recall']>=q['native_recall']),None)
        root='continue' if cp is None else {'if':{'op':'eq','args':[{'feature':'checkpoint_index'},{'int':cp}]},'then':'stop','else':'continue'}
        arms.append(('sparse-oracle',compose('sparse-oracle',root),'oracle'))
    return arms

def session(backend,raw,cfg):
    if raw['eligible']:return Session(backend,raw,cfg)
    # Validate the identical envelope/tree, then hold the host-only native mask.
    validating={**raw,'eligible':FILTERS.copy()};s=Session(backend,validating,cfg)
    s.raw['eligible']=[];s.identity=digest(['host-native-only',s.identity]);return s

def pair(frozen,backend,budget,q,truth,s,rng,meta,cold):
    order=['native','policy'];rng.shuffle(order);results={};outer={}
    for mode in order:
        started=time.perf_counter_ns()
        results[mode]=native_execute(backend,budget,q) if mode=='native' else s.query(q,budget)
        outer[mode]=(time.perf_counter_ns()-started)/1e6
    scores={m:frozen.score(truth,r) for m,r in results.items()};r=results['policy'];bypass=r.metadata['native_bypass']
    if not scores['native']['valid'] or len(results['native'].ids)!=10:raise RuntimeError('Invalid native timing reference')
    prep=s.preparation_ms if cold else 0.
    return {**meta,'query_id':q['id'],'group':q['id'].rsplit('-',1)[0],'stratum':route(q),
        'composite_hash':s.identity,'policy_hash':None if bypass else backend.validate_policy(s.raw['tree']).policy_hash,
        'native_bypass':bypass,'order':order,'native_ms':results['native'].latency_ms,
        'policy_ms':r.latency_ms+prep,'policy_ann_ms':r.metadata['policy_ann_ms'],
        'routing_ms':r.metadata['routing_ms'],'preparation_ms':prep,
        'native_outer_ms':outer['native'],'policy_outer_ms':outer['policy']+prep,
        'policy_already_activated':None if bypass else not cold,
        'native_recall':scores['native']['recall'],'policy_recall':scores['policy']['recall'],
        'recall_delta':scores['policy']['recall']-scores['native']['recall'],
        'valid':bool(scores['policy']['valid'] and len(r.ids)==10),'returned_count':len(r.ids),
        'stop_reason':None if bypass else r.metadata['stop_reason'],'checkpoint_count':None if bypass else r.metadata['checkpoint_count'],
        'work_available':not bypass,'work':None if bypass else r.metadata['work_counters'],
        'native_ids':results['native'].ids,'native_distances':results['native'].distances,
        'policy_ids':r.ids,'policy_distances':r.distances,
        'truth_strict':sorted(truth.strictly_better),'truth_ties':sorted(truth.boundary_ties),'truth_k':truth.effective_k}

def measure(backend,frozen,budget,package,out,block,notify):
    cfg=read(package/'experiment.json');stage=cfg['stage'];schedule=cfg['complete_call_accounting']
    candidates=read(package/'candidates.json');items=lines(package/'inputs/queries.jsonl')
    evidence={q['query_id']:q for q in read(package/'inputs/development-evidence.json')['queries']} if stage!='confirmation' else {}
    fixtures=lines(package/'inputs/qualification.jsonl')
    getter=qualify(backend,budget,fixtures,cfg);save(out/'qualified-features.json',getter)
    ordered=list(items);random.Random(CONFIG['seed']+block).shuffle(ordered);rng=random.Random(CONFIG['seed']+block)
    retained=0
    with (out/'pairs.jsonl').open('x') as pairs,(out/'warmups.jsonl').open('x') as warms,(out/'proofs.jsonl').open('x') as proofs,(out/'references.jsonl').open('x') as refs:
        for i,item in enumerate(ordered):
            q=item['query'];budget.reserve('exact_reference');truth=backend.exact_reference(q)
            native=native_execute(backend,budget,q);native_score=frozen.score(truth,native)
            if not native_score['valid'] or len(native.ids)!=10:raise RuntimeError('Invalid native reference')
            known=evidence.get(q['id']);profiles=list(('light19','static23','progress34')) if stage!='confirmation' else [next(iter(candidates.values()))['policy']['profile']]
            observed={}
            for profile in profiles:
                raw=compose('profile-reference','continue',profile)
                ref=session(backend,raw,cfg).query(q,budget,trace=True);observed[profile]=prefix(ref,names(cfg,profile))
                if (ref.ids,ref.distances)!=(native.ids,native.distances):raise RuntimeError('Profile changes native results')
                if known and observed[profile]!=states(known,profile,cfg):raise RuntimeError('Development trajectory changed')
            if known and native_score['recall']!=known['native_recall']:raise RuntimeError('Development native recall changed')
            write(refs,{'query_id':q['id'],'group':item['group'],'native_ids':native.ids,'native_distances':native.distances,
                'native_recall':native_score['recall'],'states':observed,'truth_strict':sorted(truth.strictly_better),
                'truth_ties':sorted(truth.boundary_ties),'truth_k':truth.effective_k})
            arms=arms_for(candidates,known,stage,cfg);random.Random(int(digest([CONFIG['seed'],q['id']]),16)).shuffle(arms)
            offset=len(arms)*block//3;arms=arms[offset:]+arms[:offset]
            for arm,raw,kind in arms:
                s=session(backend,raw,cfg);bypass=route(q) not in raw['eligible']
                proof=s.query(q,budget,trace=True)
                cp=None if bypass else __import__('fd_policy_tools').predict(raw['tree'],observed[raw['profile']],backend.runtime_profile)
                if not bypass:
                    got=prefix(proof,names(cfg,raw['profile']));expected=observed[raw['profile']]
                    if got!=(expected if cp is None else expected[:cp]):raise RuntimeError('Actual first-stop prefix differs')
                    if (proof.metadata['stop_reason']=='policy_stop')!=(cp is not None):raise RuntimeError('Actual stopping decision differs')
                if (bypass or cp is None) and (proof.ids,proof.distances)!=(native.ids,native.distances):raise RuntimeError('Native/continue result differs')
                write(proofs,{'query_id':q['id'],'arm':arm,'checkpoint':cp,'native_bypass':bypass,
                    'composite_hash':s.identity,'policy_ids':proof.ids,'policy_distances':proof.distances,
                    'observed_prefix_sha256':None if bypass else digest(prefix(proof,names(cfg,raw['profile'])))})
                # Evict server installation and Python prepared/compiled policies.
                install_eviction(backend,budget);backend._policies.clear()
                s=session(backend,raw,cfg)
                for rep in range(schedule['warm_passes']+2):
                    if not bypass:
                        active=backend._installed==backend.validate_policy(raw['tree']).policy_hash
                        if active!=(rep>0):raise RuntimeError('Cold/warm installation state differs')
                    row=pair(frozen,backend,budget,q,truth,s,rng,{'block':block,'arm':arm,'kind':kind,
                        'regime':'activation-cold' if rep==0 else 'reused-warm','repetition':0 if rep==0 else rep-2},rep==0)
                    if (row['policy_ids'],row['policy_distances'])!=(proof.ids,proof.distances):raise RuntimeError('Timed output differs from actual route proof')
                    if rep==1:write(warms,row)
                    else:write(pairs,row);retained+=1
            notify('measurement',query=i+1,total=len(items),backend_searches=budget.calls,retained_pairs=retained)
    if retained!=schedule['retained_pairs_per_block']:raise RuntimeError('Incomplete timing schedule')
    if budget.calls!=schedule['backend_searches_per_block_maximum']:raise RuntimeError('Backend accounting differs')
    return retained
