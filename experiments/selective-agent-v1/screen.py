"""Whole-query first stops and honest profile-specific development diagnostics."""
from collections import Counter
from contract import CONFIG,FILTERS,EARLY
from policy import validate,first_stop,names,references
from fd_policy_tools import assess

def replay(raw,queries,cfg):
    raw,identity=validate(raw,cfg);result=[]
    family='local' if raw['profile']=='progress34' else 'base'
    for q in queries:
        bypass=q['stratum'] not in raw['eligible'];cp=first_stop(raw,q,cfg)
        label=q['continue_costs'][family] if cp is None else q['labels'][family].get(str(cp))
        if label is None:
            result.append({'query_id':q['query_id'],'group':q['group'],'stratum':q['stratum'],
                'checkpoint':cp,'status':'unknown_actual_stop'});continue
        recall=q['native_recall'] if bypass or cp is None else label['recall']
        # Zero is a work/cost-ranking convention for a native branch, not measured routing latency.
        preserving=[(int(c),v) for c,v in q['labels'][family].items() if v['valid'] and v['returned_count']==10 and v['recall']>=q['native_recall']]
        earliest=min(preserving,default=(None,None),key=lambda x:x[0])
        result.append({'query_id':q['query_id'],'group':q['group'],'stratum':q['stratum'],
            'checkpoint':cp,'native_bypass':bypass,'native_recall':q['native_recall'],'policy_recall':recall,
            'recall_delta':recall-q['native_recall'],'valid':True if bypass else label['valid'] and label['returned_count']==10,
            'returned_count':10 if bypass else label['returned_count'],
            'work_fraction_saved':0. if bypass or cp is None else 1-label['layer0_distances']/max(1,q['native_work']),
            'earliest_measured_preserving_checkpoint':earliest[0],
            'avoidable_continued_work':None if bypass or earliest[1] is None else max(0.,
                (q['native_work'] if cp is None else label['layer0_distances'])-earliest[1]['layer0_distances']),
            'activation_proxy_ms_saved':0. if bypass else label['activation_ms_saved'],
            'reuse_proxy_ms_saved':0. if bypass else label['reuse_ms_saved'],
            'proxy_source_profile':'progress34' if family=='local' else 'static23',
            'proxy_assumptions':['Native bypass routing cost unknown; zero is ranking only'] if bypass else [],
            'status':'measured_recall_loss' if recall<q['native_recall'] else 'native_bypass' if bypass else 'continued' if cp is None else 'measured_stop'})
    return result

def screen(raw,queries,cfg):
    raw,identity=validate(raw,cfg);rows=replay(raw,queries,cfg)
    unknown=[r for r in rows if r['status']=='unknown_actual_stop']
    assessment=None if unknown else assess(rows,CONFIG['development_recall_margin'])
    used=set(references(raw['tree']['root']))
    smallest=next(p for p in ('light19','static23','progress34') if used<=set(names(cfg,p)))
    return {'semantic_hash':identity,'profile':raw['profile'],'eligible':raw['eligible'],
        'feature_groups_paid':raw['tree']['feature_groups'],'features_used':sorted(set(references(raw['tree']['root']))),
        'smallest_supported_profile':smallest,'paying_for_larger_profile':smallest!=raw['profile'],
        'stop_distribution':dict(Counter(str(r['checkpoint']) for r in rows)),
        'losses':[r for r in rows if r['status']=='measured_recall_loss'],'unknown':unknown,
        'assessment':assessment,'first_stops':rows,
        'timing_status':'unmeasured fitted-policy latency; fixed-stop proxies are diagnostic only',
        'light19_cost_status':'unmeasured; static23 values are other-profile diagnostics',
        'native_bypass_cost_status':'unmeasured; zero proxy convention does not establish native-equal timing'}
