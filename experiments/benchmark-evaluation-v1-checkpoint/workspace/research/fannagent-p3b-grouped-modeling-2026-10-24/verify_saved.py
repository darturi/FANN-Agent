"""Data-only reconstruction of the frozen P3b run; never calls model.fit."""
from pathlib import Path
import gzip
import hashlib
import json
import sys
import numpy as np
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'agent/experiments/grouped-stop-modeling-v1'
OUT=ROOT/'trials/torch-reviews-grouped-stop-modeling-v1/runs/p3b-20261024-local-v1'
sys.path.insert(0,str(SOURCE))
import common
from common import read,digest,verify_inputs,offline_guard,load_api
from data import load,outcomes,GRID,FILTERS
from stats import Bootstrap,assess,paired


def sha(path):
    with Path(path).open('rb') as h:return hashlib.file_digest(h,'sha256').hexdigest()


def independent_scores(model,x):
    total=np.zeros(len(x))
    for tree in model['trees']:
        values=np.empty(len(x))
        pending=[(tree,np.arange(len(x)))]
        while pending:
            node,ix=pending.pop()
            if 'value' in node:
                values[ix]=node['value']
                continue
            column=x[ix,node['feature']]
            mask=(column==0) if node['op']=='bool_false' else (column<=node['cut']) if node['op']=='lte' else (column<node['cut'])
            pending.extend([(node['left'],ix[mask]),(node['right'],ix[~mask])])
        total+=values
    return total/len(model['trees'])


def actions(data,profile,model,ix,threshold):
    # Scan complete trajectories in temporal order, honoring the fixed grid.
    result=[]
    for i in ix:
        lo,hi=data.slices[i]
        ordinals=[cp for cp in GRID if cp<=hi-lo]
        x=data.full_x[profile][[lo+cp-1 for cp in ordinals]]
        predictions=independent_scores(model,x)
        chosen=next((GRID.index(cp) for cp,value in zip(ordinals,predictions) if value>=threshold),8)
        result.append(chosen)
    return np.array(result)


def tree_stats(tree,depth=0):
    if 'value' in tree:return [tree['groups']],depth
    left,dl=tree_stats(tree['left'],depth+1);right,dr=tree_stats(tree['right'],depth+1)
    return left+right,max(dl,dr)


def compare(a,b,path='result'):
    if isinstance(a,dict):
        assert isinstance(b,dict) and set(a)==set(b),path
        for k in a:compare(a[k],b[k],path+'/'+k)
    elif isinstance(a,list):
        assert isinstance(b,list) and len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
    elif isinstance(a,float):
        assert type(b) in (float,int) and np.isfinite(a) and np.isfinite(b) and abs(a-b)<=1e-12,(path,a,b)
    else:assert a==b,(path,a,b)


def main():
    assert not (OUT/'failure.json').exists()
    pins=verify_inputs()
    lock=read(OUT/'design-lock.json');check=read(OUT/'verification.json');performance=read(OUT/'performance.json')
    assert check['status']=='passed'
    for name,value in lock['source_files_sha256'].items():assert sha(SOURCE/name)==value,name
    for name,value in check['files_sha256'].items():assert sha(OUT/name)==value,name
    offline_guard(OUT)
    runtime=load_api();data=load(pins)
    folds=read(OUT/'folds.json');assert folds['outer']==data.folds
    fit_receipts=sorted((OUT/'fits').glob('*.json'))
    assert len(fit_receipts)==performance['scientific_estimator_fits']<=360
    models={};individual_trees=0
    for p in fit_receipts:
        receipt=read(p);file=OUT/receipt['model_file']
        assert sha(file)==receipt['model_file_sha256']
        with gzip.open(file,'rt') as h:model=json.load(h)
        assert digest(model)==receipt['model_sha256']
        groups=set(receipt['training_groups'])
        outer=receipt['outer_fold'];held={g for g,f in data.folds.items() if f==outer}
        assert not groups&held
        if receipt['stage']=='inner':
            inner=folds['inner'][str(outer)];validation={g for g,f in inner.items() if f==receipt['inner_fold']}
            assert not groups&validation and groups|validation==set(inner)
            assert groups=={g for g in inner if inner[g]!=receipt['inner_fold']}
        else:assert groups==set(data.folds)-held
        for tree in model['trees']:
            leaves,depth=tree_stats(tree)
            assert min(leaves)>=8
            assert depth <= (3 if receipt['method']=='shallow_tree' else 8)
        assert len(model['trees'])==(1 if receipt['method']=='shallow_tree' else 64)
        individual_trees+=len(model['trees'])
        if receipt['stage']=='outer_refit':models[(receipt['profile'],receipt['method'],outer,receipt['risk'])]=model
    print('Hashes, fits, group disjointness and all stored model bounds verified.',flush=True)
    inner_checks=0
    for p in sorted((OUT/'selection').glob('*.json')):
        record=read(p);tag=p.stem
        predictions=read(OUT/'inner-predictions'/(tag+'.json'))
        groups=record['training_groups'];boot=Bootstrap(groups);ix=data.indices(groups)
        assert predictions['query_ids']==[data.meta[i]['query_id'] for i in ix]
        eligible=[]
        for trial in record['trials']:
            scores=np.array([[(-np.inf if v is None else v) for v in row] for row in predictions['scores_by_risk'][str(trial['risk'])]])
            selected=np.array([next((j for j,v in enumerate(row) if v>=trial['threshold_ms']),8) for row in scores])
            assert selected.tolist()==trial['inner_oof_actions']
            rows=outcomes(data,record['profile'],ix,selected)
            result=assess(rows,boot,all_metrics=False)
            compare(result,trial['assessment'])
            if result['development_signal']:eligible.append(trial)
            inner_checks+=1
        winner=max(eligible,key=lambda t:(t['assessment']['utility_proxy_ms'],t['risk'],t['threshold_ms'])) if eligible else None
        assert record['chosen']==(None if winner is None else {'risk':winner['risk'],'threshold_ms':winner['threshold_ms']})
    print('All 560 inner candidate assessments and frozen selections reconstructed.',flush=True)
    totals={phase:{profile:{method:[] for method in ['shallow_tree','extra_trees']} for profile in ['static23','progress34']} for phase in ['calibrated','fixed_diagnostic']}
    outer_cases=0
    for p in sorted((OUT/'outer-records').glob('*.json')):
        saved=read(p);rows=saved['rows'];first=rows[0]
        profile,method,outer,phase=[first[k] for k in ['profile','method','outer_fold','phase']]
        ix=data.indices([g for g,f in data.folds.items() if f==outer])
        assert [r['query_id'] for r in rows]==[data.meta[i]['query_id'] for i in ix]
        if first['risk'] is None:
            selected=np.full(len(ix),8)
        else:
            model=models[(profile,method,outer,first['risk'])]
            selected=actions(data,profile,model,ix,first['threshold_ms'])
        reconstructed=outcomes(data,profile,ix,selected)
        for actual,old in zip(reconstructed,rows):
            for key,value in actual.items():compare(value,old[key],key)
        totals[phase][profile][method].extend(rows)
        outer_cases+=len(rows)
    boot=Bootstrap(data.folds)
    rebuilt={phase:{profile:{method:assess(rows,boot) for method,rows in methods.items()} for profile,methods in profiles.items()} for phase,profiles in totals.items()}
    compare(rebuilt,performance['reports'])
    comparisons={phase:{profile:paired(methods['extra_trees'],methods['shallow_tree'],boot) for profile,methods in profiles.items()} for phase,profiles in totals.items()}
    compare(comparisons,performance['paired_flexible_minus_shallow'])
    assert common.FITS==0
    verify_inputs()
    summary={'status':'passed','scientific_estimator_fits':len(fit_receipts),'individual_trees':individual_trees,
             'inner_candidate_assessments_reconstructed':inner_checks,'outer_first_stop_cases_reconstructed':outer_cases,
             'all_stored_model_hashes_and_pruning_bounds_verified':True,'all_inner_and_outer_group_splits_verified':True,
             'all_outer_model_first_stops_independently_reconstructed':True,'all_reports_and_paired_contrasts_match_tolerance':1e-12,
             'new_fits_in_verification':common.FITS,'new_measurements_provider_or_Torch_calls':0,
             'saved_performance_sha256':sha(OUT/'performance.json'),'design_lock_sha256':sha(OUT/'design-lock.json'),
             'source_and_input_preservation':True}
    # Output inside the already assigned run directory; verification source is separate.
    common.save(OUT/'verification-replay.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=1):main()
