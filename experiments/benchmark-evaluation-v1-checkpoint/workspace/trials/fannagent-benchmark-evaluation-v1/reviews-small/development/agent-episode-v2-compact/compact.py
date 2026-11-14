"""Fixed filter-focused EDA, not a host-selected policy search."""
import collections,math
from data import FILTERS,POINTS,FEATURES,encoded,choose,evaluate,validate_policy
# Bin edges fixed before model calls; do not optimize cutoffs to manufacture a rule.
EDGES={'frontier_gap':[-2,0,.01,.02,.03,.05,.075,.1,.15,.2,.3,2.00001],
       'tenth_distance':[0,.2,.25,.3,.35,.4,.45,.5,.6,.75,2.00001],
       'top10_new_since_previous':[-.5,.5,1.5,2.5,3.5,5.5,10.5],
       'qualifying_count':[10,12,16,24,32,64,128,257,641,247287]}
def num(x):return None if x is None else float(format(x,'.10g'))
def example(row,cp,full_precision=False):
    obs=row['observations'][cp];proof=row['proofs'][str(cp)]
    return {'anonymous_group':row['group'],'development_fold':row['fold'],
            'features':{f:obs.get(f) if full_precision else num(obs.get(f)) for f in FEATURES},
            'parent_hits':round(row['baseline_recall']*10),'stop_hits':round(proof['recall']*10),
            'stop_us':round(row['stop_ns'][cp]/1000,2),'parent_us':round(row['native_ns']/1000,2)}
def focused_bundle(rows):
    report={}
    for filter_ in FILTERS:
        data=[r for r in rows.values() if r['filter']==filter_];checkpoints={}
        for cp in POINTS:
            ready=[r for r in data if str(cp) in r['proofs']]
            safe=[r for r in ready if r['proofs'][str(cp)]['recall']>=r['baseline_recall']-1e-12]
            lossy=[r for r in ready if r['proofs'][str(cp)]['recall']<r['baseline_recall']-1e-12]
            feature_stats={}
            for feature,edges in EDGES.items():
                bins=[]
                for low,high in zip(edges,edges[1:]):
                    s=sum(r['observations'][cp].get(feature) is not None and low<=r['observations'][cp][feature]<high for r in safe)
                    l=sum(r['observations'][cp].get(feature) is not None and low<=r['observations'][cp][feature]<high for r in lossy)
                    if s+l:bins.append([low,high,s,l])
                extrema={}
                for label,pool in (('safe',safe),('lossy',lossy)):
                    values=sorted(r['observations'][cp][feature] for r in pool if r['observations'][cp].get(feature) is not None)
                    if values:extrema[label]=[num(values[0]),num(values[len(values)//2]),num(values[-1])]
                feature_stats[feature]={'nonempty_bins_low_inclusive_high_exclusive_safe_lossy':bins,'min_median_max':extrema}
            # Deterministic extremes, no claim of a separating conjunction.
            representatives={}
            for label,pool in (('safe',safe),('lossy',lossy)):
                selected=[]
                for key,reverse in (('frontier_gap',True),('tenth_distance',False),('top10_new_since_previous',False)):
                    eligible=[r for r in pool if r['observations'][cp].get(key) is not None]
                    eligible.sort(key=lambda r:(r['observations'][cp][key],r['group']),reverse=reverse)
                    for r in eligible[:1]:
                        if r['group'] not in {x['anonymous_group'] for x in selected}:selected.append(example(r,cp))
                representatives[label]=selected
            checkpoints[str(cp)]={'reached':sum(cp in r['observations'] for r in data),'eligible_measured_stops':len(ready),'preserves_query_recall':len(safe),'loses_query_recall':len(lossy),'features':feature_stats,'extreme_examples':representatives}
        report[filter_]={'queries':450,'parent_recall':sum(r['baseline_recall'] for r in data)/450,'parent_mean_us':sum(r['native_ns'] for r in data)/450/1000,'noop_mean_us':sum(r['noop_ns'] for r in data)/450/1000,'native_exact_fallbacks':sum(r['fallback'] for r in data),'checkpoints':checkpoints}
    return {'format':'compact-filter-EDA.v1','scope':'450 DEVELOPMENT vector groups; six scalar filters plus unfiltered; no validation/test','parent':'guarded native640 with shared exact completion guard','bin_note':'Univariate distributions and extrema are summaries, NOT safe policy seeds. Joint conditions must be evaluated on all full-precision development records.','features':'qualifying_count,tenth_distance,frontier_gap,top10_new_since_previous; cp16/32/64','case_example_note':'Anonymous group/fold and labels are evaluator information, never runtime features. Examples are deterministic extremes, not an exhaustive safety test.','cost_note':'Probe costs are only surrogates for a newly compiled rule. Final selection still requires live complete serving measurements.','filters':report}

def evaluated_feedback(rows,policy):
    validate_policy(policy);metrics=evaluate(rows,policy);failures=collections.defaultdict(list)
    for row in rows.values():
        cp=choose(row,policy)
        if cp and row['proofs'][str(cp)]['recall']<row['baseline_recall']-1e-12 and len(failures[row['filter']])<3:
            failures[row['filter']].append({'checkpoint':cp,**example(row,cp,full_precision=True)})
    # The all-record metrics are exact saved-output replay, not just the examples.
    metrics.pop('loss_examples',None)
    return {'metrics':metrics,'full_precision_failure_examples_by_filter':dict(failures),'evaluated_development_cases':3150,'no_live_queries':True,'runtime_feature_oracle_access':False}
