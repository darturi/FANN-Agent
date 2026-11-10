"""Vector-group uncertainty; no dependency on model or database clients."""
from collections import defaultdict
import math
import numpy as np


def summary(rows,config):
    # rows are the retained measurements for one policy/case, all three filters.
    groups=defaultdict(list)
    for row in rows:groups[row['group']].append(row)
    if len(groups)<2:raise ValueError('At least two independent vector groups required')
    matrix=np.asarray([[np.mean([r['policy_ms']-r['native_ms'] for r in rs]),
        np.mean([r['policy_outer_ms']-r['native_outer_ms'] for r in rs]),
        np.mean([r['recall_delta'] for r in rs]),
        np.mean([math.log(r['policy_ms']/r['native_ms']) for r in rs])] for rs in groups.values()])
    rng=np.random.default_rng(config['seed'])
    boot=matrix[rng.integers(0,len(matrix),size=(config['bootstrap_samples'],len(matrix)))].mean(axis=1)
    ci=np.quantile(boot,[.025,.975],axis=0)
    def mean(fn):return float(np.mean([fn(r) for r in rows]))
    return {'pairs':len(rows),'independent_vectors':len(groups),
        'native_ms':mean(lambda r:r['native_ms']),'policy_ms':mean(lambda r:r['policy_ms']),
        'gap_ms':float(matrix[:,0].mean()),'gap_ci95':ci[:,0].tolist(),
        'outer_gap_ms':float(matrix[:,1].mean()),'outer_gap_ci95':ci[:,1].tolist(),
        'recall_delta':float(matrix[:,2].mean()),'recall_delta_ci95':ci[:,2].tolist(),
        'log_latency_ratio_ci95':ci[:,3].tolist(),
        'native_recall':mean(lambda r:r['native_recall']),'policy_recall':mean(lambda r:r['policy_recall']),
        'returned_count':mean(lambda r:r['returned_count']),
        'collection_ms':None if any(r['work'] is None for r in rows) else mean(lambda r:r['work'].get('feature_collection_ns',0)/1e6),
        'layer0_distances':None if any(r['work'] is None for r in rows) else mean(lambda r:r['work']['layer0_distance_evaluations']),
        'all_valid':all(r['valid'] for r in rows),
        'recall_noninferior':bool(ci[0,2]>=-config['recall_tolerance']),
        'latency_improved':bool(ci[1,3]<0)}


def with_filters(rows,config):
    return {'overall':summary(rows,config),'per_filter':{f:summary([r for r in rows if r['stratum']==f],config) for f in config['filters']}}


def feasible(report,config):
    return report['overall']['all_valid'] and report['overall']['recall_noninferior'] and report['overall']['latency_improved'] and all(
        s['all_valid'] and s['recall_noninferior'] and s['native_recall']>=config['minimum_native_recall']
        for s in report['per_filter'].values())
