"""Shared policy interpreter, exact measured-outcome replay and fixed gates."""
from fd_contract import CONFIG, SEARCH, SEED, EARLY, EXTRA, LEGACY_EXTRA, GROUPS, CONDITIONS


def references(node):
    if isinstance(node,dict):
        if 'feature' in node:yield node['feature']
        for child in node.values():yield from references(child)
    elif isinstance(node,list):
        for child in node:yield from references(child)


def combine(op,items):
    if not items:return {'bool':True}
    if len(items)==1:return items[0]
    n=len(items)//2
    return {'op':op,'args':[combine(op,items[:n]),combine(op,items[n:])]}


def guard(root,checkpoints):
    required=sorted(set(references(root))|{'checkpoint_index'})
    available=combine('and',[{'op':'is_available','args':[{'feature':n}]} for n in required])
    allowed=combine('or',[{'op':'eq','args':[{'feature':'checkpoint_index'},{'int':cp}]} for cp in checkpoints])
    return {'if':{'op':'and','args':[available,allowed]},'then':root,'else':'continue'}


def policy(name,cp=None,progress=False,base=False,root=None):
    groups=GROUPS[:-1] if base else GROUPS+(['progress_filter'] if progress else [])
    if root is None:root='continue' if cp is None else {'if':{'op':'gte','args':[{'feature':'checkpoint_index'},{'int':cp}]},'then':'stop','else':'continue'}
    return {'name':name,'feature_groups':groups,'root':root}


def predict(raw,states,profile):
    from fannagent.api import FeatureValue,PolicyInput,validate_policy
    from fannagent.api.primitives.interpreter import evaluate_policy
    artifact=validate_policy(raw,profile);names=sorted(set(references(raw['root'])))
    floats=frozenset(n for n in names if profile.runtime_features[n].kind=='float')
    for s in states:
        f=s['features'];inp=PolicyInput(features={n:FeatureValue(available=f.get(n) is not None,value=f.get(n)) for n in names})
        if str(evaluate_policy(artifact,inp,float_features=floats))=='stop':return s['checkpoint_index']
    return None


def replay(raw,queries,arm,profile):
    family='local' if CONDITIONS[arm]['local_filter'] else 'base';result=[]
    for q in queries:
        cp=predict(raw,q[family+'_states'],profile)
        if cp is None:
            label=q['continue_costs'][family];recall=q['native_recall'];valid=True;count=10
        else:
            if str(cp) not in q['labels'][family]:raise ValueError('Unknown actual stop; acquisition required')
            label=q['labels'][family][str(cp)];recall=label['recall'];valid=label['valid'];count=label['returned_count']
        result.append({'query_id':q['query_id'],'group':q['group'],'stratum':q['stratum'],
          'checkpoint':cp,'native_recall':q['native_recall'],'policy_recall':recall,'recall_delta':recall-q['native_recall'],
          'valid':bool(valid and count==10),'returned_count':count,
          'activation_proxy_ms_saved':label['activation_ms_saved'],'reuse_proxy_ms_saved':label['reuse_ms_saved']})
    return result


def assess(rows,tolerance=.0025):
    import numpy as np
    reports={}
    for f in ['overall',*CONFIG['filters']]:
        selected=[r for r in rows if f=='overall' or r['stratum']==f]
        groups=sorted({r['group'] for r in selected})
        if len(groups)<2:raise ValueError('Two independent vector groups required')
        values=np.asarray([np.mean([r['recall_delta'] for r in selected if r['group']==g]) for g in groups])
        rng=np.random.default_rng(CONFIG['bootstrap_seed']);boot=values[rng.integers(0,len(values),size=(10000,len(values)))].mean(axis=1)
        reports[f]={'groups':len(groups),'recall_delta':float(values.mean()),'recall_delta_ci95':np.quantile(boot,[.025,.975]).tolist(),
          'all_valid':all(r['valid'] for r in selected),'native_recall':float(np.mean([r['native_recall'] for r in selected]))}
    passes=all(r['all_valid'] and r['recall_delta_ci95'][0]>=-tolerance and (f=='overall' or r['native_recall']>=.95) for f,r in reports.items())
    costs={m:float(np.mean([r[m+'_proxy_ms_saved'] for r in rows])) for m in ['activation','reuse']}
    return {'recall_pass':passes,'reports':reports,'cost_proxies':costs,'utility':min(costs.values()),
      'timing_status':'fixed-stop proxies only, not final policy latency'}
