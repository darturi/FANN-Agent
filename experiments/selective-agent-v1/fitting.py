"""Audited beam growth, adapted only for profile/mask and light work objective."""
import copy
import numpy as np
import beam_search as beam
from contract import EARLY,digest
from policy import compose,validate
from screen import screen

def fit_one(queries,cfg,groups,profile,eligible,risk):
    from fannagent_pgvector.profiles import PROFILE
    from policy import names
    # Preserve the frozen search itself; map its input slots explicitly.
    condition='P160' if profile=='progress34' else 'S160'
    selected=copy.deepcopy([q for q in queries if q['group'] in set(groups)])
    family='local' if profile=='progress34' else 'base'
    for q in selected:
        if profile=='light19':
            for label in [q['continue_costs'][family],*q['labels'][family].values()]:
                work=0. if label is q['continue_costs'][family] else 1-label['layer0_distances']/max(1,q['native_work'])
                label['activation_ms_saved']=label['reuse_ms_saved']=work
        if q['stratum'] not in eligible:
            # All three cases/group remain present. Disable stop states on the native route.
            q[family+'_states']=[];q['labels'][family]={}
            q['continue_costs'][family]={'activation_ms_saved':0.,'reuse_ms_saved':0.,'valid':True,'returned_count':10}
    # The original algorithm emits static groups and reads the passed base pool;
    # profile-specific pool selection and final artifact wrapping are adapters.
    base=cfg['base_feature_names'] if profile=='light19' else cfg['static_feature_names']
    tree,proof=beam.fit(selected,condition,risk,PROFILE,base,groups)
    raw=compose('agent-helper-'+digest([sorted(groups),profile,eligible,risk])[:12],tree['root']['then'],profile,eligible)
    raw,identity=validate(raw,cfg)
    from policy import first_stop
    for q in queries:
        if q['group'] in set(groups) and first_stop(raw,q,cfg)!=proof['training_first_stops'][q['query_id']]:
            raise RuntimeError('Packed fitter and shared first-stop interpreter disagree')
    proof.update(semantic_hash=identity,profile=profile,eligible=eligible,
        objective='normalised physical work minus risk times worst-filter recall deficit' if profile=='light19'
        else 'lower activation/reuse fixed-stop saving minus risk times worst-filter recall deficit',
        bypass_cost='zero ranking convention; actual routing cost unmeasured',helper_origin='audited beam growth',
        shared_interpreter_checks=3*len(groups))
    return raw,proof

def fit(queries,cfg,folds,profile,eligible,risk):
    if profile not in {'light19','static23','progress34'} or risk not in {20,80,320,1280}:raise ValueError('Use declared profile/risk grid')
    if not eligible or set(eligible)-{'unfiltered','votes32','votes108'}:raise ValueError('Eligibility mask')
    groups=sorted(folds);checks=[]
    for fold in range(5):
        train=[g for g in groups if folds[g]!=fold];test=[q for q in queries if folds[q['group']]==fold]
        raw,proof=fit_one(queries,cfg,train,profile,eligible,risk)
        checks.append({'fold':fold,'training_groups':train,'proof':proof,'screen':screen(raw,test,cfg)})
    raw,proof=fit_one(queries,cfg,groups,profile,eligible,risk)
    return {'policy':raw,'proof':proof,'fold_checks':checks,'screen':screen(raw,queries,cfg),'primitive_fits':6,
        'scope':'Adaptive development diagnostics; no independent confirmation or latency qualification'}
