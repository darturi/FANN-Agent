"""Reconstruct gates from sealed raw measurements with trusted local code."""
import argparse
import math
from pathlib import Path
from no_models import enforce
from contract import CONFIG,AB,read,save,sha,digest,lines

def validate_row(r,ref):
    for mode in ('native','policy'):
        ids=r[mode+'_ids'];distances=r[mode+'_distances']
        if len(ids)!=len(distances) or len(set(ids))!=len(ids) or len(ids)>10 or any(not math.isfinite(d) for d in distances):raise ValueError('Invalid IDs/distances')
        strict=len(set(ids)&set(ref['truth_strict']));ties=min(10-len(ref['truth_strict']),len(set(ids)&set(ref['truth_ties'])))
        if abs((strict+ties)/10-r[mode+'_recall'])>1e-12:raise ValueError('Recall does not reproduce from exact truth')
        for field in (mode+'_ms',mode+'_outer_ms'):
            if not math.isfinite(r[field]) or r[field]<=0:raise ValueError('Invalid measured time')
    if r['native_ids']!=ref['native_ids'] or r['native_distances']!=ref['native_distances'] or r['native_recall']!=ref['native_recall']:raise ValueError('Native changed')
    if r['returned_count']!=len(r['policy_ids']) or r['valid']!=(len(r['policy_ids'])==10):raise ValueError('Completeness differs')
    if r['recall_delta']!=r['policy_recall']-r['native_recall']:raise ValueError('Recall delta differs')
    if sorted(r['order'])!=['native','policy']:raise ValueError('Not a paired comparison')
    if r['policy_ms']!=r['policy_ann_ms']+r['routing_ms']+r['preparation_ms'] or min(r['routing_ms'],r['preparation_ms'])<0:raise ValueError('Preparation/routing cost omitted or double counted')
    if r['regime']=='reused-warm' and r['preparation_ms']!=0:raise ValueError('Warm preparation counted again')
    if r['native_bypass']:
        if any(r[k] is not None for k in ('policy_hash','policy_already_activated','work','checkpoint_count','stop_reason')) or r['work_available']:
            raise ValueError('Fabricated native-bypass engine state')
        if (r['policy_ids'],r['policy_distances'])!=(ref['native_ids'],ref['native_distances']):raise ValueError('Bypass changed native result')
    else:
        if r['policy_already_activated']!=(r['regime']=='reused-warm'):raise ValueError('Activation state differs')
        if r['work']['frontier_snapshot_count'] or r['work']['frontier_sort_count']:raise ValueError('Unbudgeted full frontier statistics')

def analyze(campaign,package,output=None):
    from control import verify
    from policy import route,names
    from execution import arms_for,session
    from fd_policy_tools import predict
    from fannagent_pgvector.profiles import PROFILE
    from study_stats import with_filters,feasible
    cfg=verify(package);schedule=cfg['complete_call_accounting'];stage=cfg['stage']
    candidates=read(package/'candidates.json');items={i['query']['id']:i for i in lines(package/'inputs/queries.jsonl')}
    evidence={q['query_id']:q for q in read(package/'inputs/development-evidence.json')['queries']} if stage!='confirmation' else {}
    if len(items)!=schedule['cases'] or len({i['group'] for i in items.values()})!=schedule['independent_vectors']:raise ValueError('Case inventory differs')
    all_rows=[];raw_hashes={};per_block={};reference_identity=None
    for block in range(3):
        folder=campaign/'blocks'/('block-'+str(block));status=read(folder/'status.json')
        for n in ('job-exit.json','host-exit.json'):
            if read(folder/n)['exit_code']:raise ValueError('Failed block')
        if read(folder/'protected-source-before.json')!=read(folder/'protected-source-after.json'):raise ValueError('Sources changed')
        if status['status']!='complete' or status['provider_calls'] or status['backend_searches']!=schedule['backend_searches_per_block_maximum']:raise ValueError('Status/accounting differs')
        runtime=read(folder/'runtime-identity.json')
        if runtime['module_sha256']!=cfg['module_sha256'] or runtime['registry_hash']!=PROFILE.native_registry_hash or runtime['runtime_profile_hash']!=PROFILE.fingerprint:
            raise ValueError('Execution module/registry/profile differs')
        if runtime['package_manifest_sha256']!=sha(package/'manifest.json') or runtime['image_sha256']!=cfg['image_sha256']:raise ValueError('Runtime package/image identity differs')
        getters=read(folder/'qualified-features.json')
        if sum(g['backend_calls'] for g in getters)!=921 or any(g['status']!='passed' for g in getters):raise ValueError('Incomplete getter qualification')
        lock=read(folder/'LOCK.json')
        if lock['package_manifest_sha256']!=sha(package/'manifest.json'):raise ValueError('Block source differs')
        for name,h in lock['files_sha256'].items():
            if sha(folder/name)!=h:raise ValueError('Raw file changed: '+name)
            raw_hashes[str((folder/name).relative_to(campaign))]=h
        refs={r['query_id']:r for r in lines(folder/'references.jsonl')}
        if set(refs)!=set(items):raise ValueError('Reference coverage differs')
        ri=digest(refs)
        if reference_identity is not None and ri!=reference_identity:raise ValueError('Results/observations changed between blocks')
        reference_identity=ri
        proofs={(r['query_id'],r['arm']):r for r in lines(folder/'proofs.jsonl')}
        wanted=set();warm_wanted=set();proof_wanted=set()
        for qid,item in items.items():
            ref=refs[qid]
            if ref['group']!=item['group']:raise ValueError('Group identity changed')
            for arm,raw,kind in arms_for(candidates,evidence.get(qid),stage,cfg):
                proof_wanted.add((qid,arm));proof=proofs[(qid,arm)]
                bypass=route(item['query']) not in raw['eligible']
                cp=None if bypass else predict(raw['tree'],ref['states'][raw['profile']],PROFILE)
                if proof['native_bypass']!=bypass or proof['checkpoint']!=cp:raise ValueError('Actual route/first-stop proof differs')
                if not bypass:
                    ss=ref['states'][raw['profile']]
                    if proof['observed_prefix_sha256']!=digest(ss if cp is None else ss[:cp]):raise ValueError('Stopped prefix differs')
                if (bypass or cp is None) and (proof['policy_ids'],proof['policy_distances'])!=(ref['native_ids'],ref['native_distances']):raise ValueError('Continue/native proof differs')
                wanted.add((qid,arm,'activation-cold',0))
                wanted.update((qid,arm,'reused-warm',rep) for rep in range(schedule['warm_passes']))
                warm_wanted.add((qid,arm,'reused-warm',-1))
        if set(proofs)!=proof_wanted:raise ValueError('Duplicate/missing arm proofs')
        selected=[]
        for filename,expected,retained in [('pairs.jsonl',wanted,True),('warmups.jsonl',warm_wanted,False)]:
            seen=set()
            for r in lines(folder/filename):
                key=(r['query_id'],r['arm'],r['regime'],r['repetition'])
                if key in seen or key not in expected or r['block']!=block:raise ValueError('Duplicate/unexpected timing row')
                seen.add(key);validate_row(r,refs[r['query_id']]);p=proofs[(r['query_id'],r['arm'])]
                if (r['policy_ids'],r['policy_distances'])!=(p['policy_ids'],p['policy_distances']):raise ValueError('Timed output differs from proof')
                if not r['native_bypass'] and r['checkpoint_count']!=(p['checkpoint'] if p['checkpoint'] is not None else len(refs[r['query_id']]['states'][next(raw['profile'] for a,raw,k in arms_for(candidates,evidence.get(r['query_id']),stage,cfg) if a==r['arm'])])):
                    raise ValueError('Timed stop checkpoint differs')
                if retained:selected.append(r)
            if seen!=expected:raise ValueError('Incomplete timing schedule')
        if len(selected)!=schedule['retained_pairs_per_block'] or status['retained_pairs']!=len(selected):raise ValueError('Retained count differs')
        all_rows+=selected;per_block[str(block)]={'pairs':len(selected),'backend_searches':status['backend_searches']}
    stats_cfg={**cfg,'seed':cfg['bootstrap_seed']};reports={};qualifications={}
    for arm in sorted({r['arm'] for r in all_rows}):
        modes={}
        for regime in ('activation-cold','reused-warm'):
            rows=[r for r in all_rows if r['arm']==arm and r['regime']==regime]
            report=with_filters(rows,stats_cfg)
            for s in [report['overall'],*report['per_filter'].values()]:
                s['ms_saved']=-s['gap_ms'];s['percent_saved']=100*(s['native_ms']-s['policy_ms'])/s['native_ms']
            enough=all(s['independent_vectors']>=30 for s in [report['overall'],*report['per_filter'].values()])
            final=not cfg.get('synthetic_only',False) and enough and feasible(report,stats_cfg)
            dev=final and all(s['recall_delta_ci95'][0]>=-.0025 for s in [report['overall'],*report['per_filter'].values()])
            failures=[]
            for f,s in [('overall',report['overall']),*report['per_filter'].items()]:
                if not s['all_valid']:failures.append(f+': incomplete/invalid results')
                if s['recall_delta_ci95'][0]<-.005:failures.append(f+': final recall lower bound below -0.5 pp')
                if s['recall_delta_ci95'][0]<-.0025:failures.append(f+': development recall reserve below -0.25 pp')
                if f!='overall' and s['native_recall']<.95:failures.append(f+': native recall floor below 95%')
            if not report['overall']['latency_improved']:failures.append('overall: latency ratio upper bound is not below zero')
            if not enough:failures.append('Fewer than 30 independent vectors')
            modes[regime]={'report':report,'final_gate_passed':final,'development_gate_passed':dev,
                'native_bypass_fraction':sum(r['native_bypass'] for r in rows)/len(rows),
                'mean_routing_ms':sum(r['routing_ms'] for r in rows)/len(rows),
                'mean_preparation_ms':sum(r['preparation_ms'] for r in rows)/len(rows),
                'mean_ann_ms':sum(r['policy_ann_ms'] for r in rows)/len(rows),
                'qualification_diagnostics':failures,
                'policy_stops':sum(r['stop_reason']=='policy_stop' for r in rows)}
        reports[arm]=modes
        if arm in candidates:
            stops=any(m['policy_stops']>0 for m in modes.values())
            qualifications[arm]={'activation_qualifies':modes['activation-cold']['final_gate_passed'],
                'reuse_qualifies':modes['reused-warm']['final_gate_passed'],
                'final_qualifies':all(m['final_gate_passed'] for m in modes.values()),
                'development_qualifies':stops and all(m['development_gate_passed'] for m in modes.values()),
                'actual_policy_stops_observed':stops,
                'diagnostics':{regime:m['qualification_diagnostics'] for regime,m in modes.items()}}
    result={'status':'verified','stage':stage,'episode_id':cfg['episode_id'],'package_manifest_sha256':sha(package/'manifest.json'),
        'retained_pairs':len(all_rows),'per_block':per_block,'reports':reports,'candidate_qualification':qualifications,
        'provider_calls':0,'synthetic_only':cfg.get('synthetic_only',False),'canonical_acceptance_established':False,'ab_comparison':AB,'final_criteria_unchanged':True,
        'confirmation_entitlement_sha256':cfg.get('confirmation_entitlement_sha256'),
        'scope':'One-shot workload confirmation' if stage=='confirmation' else 'Exposed development measurements',
        'raw_files_sha256':raw_hashes}
    out=Path(output) if output else campaign/'analysis';out.mkdir(parents=True,exist_ok=True)
    save(out/'performance.json',result)
    header='Arm | activation saved ms | activation saved % | reuse saved ms | reuse saved % | recall loss pp | development gate | final gate'
    text=[header]
    for arm,m in reports.items():
        x=m['activation-cold']['report']['overall'];y=m['reused-warm']['report']['overall'];q=qualifications.get(arm,{})
        text.append(f"{arm} | {x['ms_saved']:+.6f} | {x['percent_saved']:+.3f} | {y['ms_saved']:+.6f} | {y['percent_saved']:+.3f} | {-100*x['recall_delta']:+.3f} | {q.get('development_qualifies','control')} | {q.get('final_qualifies','control')}")
    text+=['All filters retained; no overhead subtracted. Oracle is hindsight and nondeployable.',
        'Original A/B: inconclusive, zero complete pairs. Canonical acceptance: false.']
    save(out/'report.txt','\n'.join(text)+'\n',raw=True)
    return result

if __name__=='__main__':
    enforce();p=argparse.ArgumentParser();p.add_argument('campaign',type=Path);p.add_argument('package',type=Path);a=p.parse_args()
    print(__import__('json').dumps(analyze(a.campaign,a.package)['candidate_qualification'],indent=2))
