"""Independent saved-raw reconstruction; never promotes or launches jobs."""
import argparse
import collections
import math
from pathlib import Path
import tempfile
import sys
from no_models import enforce
enforce()
from contract import CONFIG,CONDITIONS,EXTRA,EARLY,AB,read,save,sha,digest,lines
from control import verify,finished


def validate_row(row,reference):
    if (row['native_ids'],row['native_distances'],row['native_recall'])!=(reference['native_ids'],reference['native_distances'],reference['native_recall']):
        raise ValueError('Native result differs from reference')
    if row['truth_k']!=10 or row['group']!=row['query_id'].rsplit('-',1)[0] or row['stratum']!=row['query_id'].rsplit('-',1)[1]:raise ValueError('Query identity differs')
    for mode in ('native','policy'):
        ids=row[mode+'_ids'];distances=row[mode+'_distances']
        if len(ids)!=len(distances) or len(set(ids))!=len(ids) or len(ids)>10 or any(not math.isfinite(v) for v in distances):raise ValueError('Invalid result IDs/distances')
        strict=len(set(ids)&set(row['truth_strict']));ties=min(10-len(row['truth_strict']),len(set(ids)&set(row['truth_ties'])))
        if abs((strict+ties)/10-row[mode+'_recall'])>1e-12:raise ValueError('Recall does not reproduce from exact reference')
        for field in (mode+'_ms',mode+'_outer_ms'):
            if not math.isfinite(row[field]) or row[field]<=0:raise ValueError('Invalid measured latency')
    if row['returned_count']!=len(row['policy_ids']) or row['valid']!=(len(row['policy_ids'])==10):raise ValueError('Completeness flag differs')
    if abs(row['recall_delta']-(row['policy_recall']-row['native_recall']))>1e-12:raise ValueError('Recall difference differs')
    if row.get('native_bypass'):
        if row['policy_hash'] is not None or row['policy_already_activated'] is not None or row['work_available'] or row['work'] is not None:raise ValueError('Fabricated bypass policy state')
    else:
        if row['work']['frontier_snapshot_count'] or row['work']['frontier_sort_count']:raise ValueError('Unbudgeted queue snapshot/sort')
        if row['policy_already_activated']!=(row['regime']=='reused-warm'):raise ValueError('Activation state differs')
    if 'routing_ms' in row:
        if row['routing_ms']<0 or row['policy_ms']!=row['policy_ann_ms']+row['routing_ms']:raise ValueError('Routing cost omitted/altered')


def verify_phase(campaign,phase):
    folder=finished(campaign,phase)
    if read(folder/'protected-source-before.json')!=read(folder/'protected-source-after.json'):raise ValueError('Protected sources changed')
    if phase!='build':
        for name,h in read(folder/'LOCK.json')['files_sha256'].items():
            if sha(folder/name)!=h:raise ValueError('Sealed raw file changed: '+phase+'/'+name)
    return folder


def reproduce_acquisition(campaign,phase,package,items,profile,evaluation=False):
    from execution import validate_acquisition,expected_progress
    from policy_tools import policy
    from fannagent.api import validate_policy
    folder=verify_phase(campaign,phase);evidence=validate_acquisition(folder,package)
    cfg=read(package/'experiment.json');items_by_id={i['query']['id']:i for i in items}
    refs={r['query_id']:r for r in lines(folder/'references.jsonl')}
    if set(refs)!=set(items_by_id) or {q['query_id'] for q in evidence['queries']}!=set(refs):raise ValueError('Acquired query coverage differs')
    proofs={}
    for p in lines(folder/'proofs.jsonl'):
        key=(p['query_id'],p['family'],p['checkpoint'])
        if key in proofs:raise ValueError('Duplicate stopped proof')
        proofs[key]=p
    samples={};warmups={}
    for name,target in [('pairs.jsonl',samples),('warmups.jsonl',warmups)]:
        for r in lines(folder/name):
            validate_row(r,refs[r['query_id']]);key=(r['query_id'],r['family'],r['checkpoint'],r['regime'])
            if key in target:raise ValueError('Duplicate acquisition pair')
            target[key]=r
    probes={r['query_id']:r for r in lines(folder/'probe-verification.jsonl')}
    original={r['query_id']:r for r in lines(package/'inputs/training-640-light.jsonl')}
    gold=read(package/'inputs/native-results.json');wanted=set();wanted_warm=set();wanted_proofs=set()
    for q in evidence['queries']:
        identifier=q['query_id'];ref=refs[identifier];item=items_by_id[identifier]
        if q['role']!=item['role'] or q['group']!=item['group']:raise ValueError('Role/group differs')
        if q['base_states']!=ref['base_states'] or q['local_states']!=ref['local_states']:raise ValueError('Fitting observations differ')
        if [{**s,'features':{n:s['features'][n] for n in cfg['static_feature_names']}} for s in q['local_states']]!=q['base_states']:raise ValueError('Progress changed static traversal')
        if identifier in original:
            if [{**s,'features':{n:s['features'][n] for n in cfg['base_feature_names']}} for s in q['base_states']]!=original[identifier]['states']:raise ValueError('Original trajectory changed')
            if (ref['native_ids'],ref['native_distances'],ref['native_recall'])!=(gold[identifier]['ids'],gold[identifier]['distances'],gold[identifier]['recall']):raise ValueError('Original native result changed')
        receipt=probes[identifier]
        if not receipt['actual_metadata_and_distance_verified'] or not receipt['static']['actual_metadata_verified']:raise ValueError('Metadata qualification failed')
        progress=receipt['progress']
        if not progress['enabled'] or any(n<0 or n>8 for n in progress['fetches']) or sum(progress['fetches'])>64 or len(progress['rows'])>sum(progress['fetches']):raise ValueError('Progress budget differs')
        threshold=0 if item['query'].get('filter') is None else item['query']['filter']['value']
        for window,identifier2,vote,null,distance in progress['rows']:
            actual_vote,actual_distance=progress['actual_metadata_sql_rows'][str(identifier2)]
            if window not in EARLY or (actual_vote is None)!=null or (not null and actual_vote!=vote) or abs(actual_distance-distance)>1e-6:raise ValueError('Progress metadata does not reproduce')
        for state in q['local_states']:
            expected=expected_progress(progress,state['checkpoint_index'],threshold)
            for name,value in expected.items():
                observed=state['features'][name]
                if type(value) is bool:
                    if type(observed) is not bool or observed!=value:raise ValueError('Boolean observation differs')
                elif not math.isclose(observed,value,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Causal observation differs: '+name)
        for family,is_progress in [('base',False),('local',True)]:
            states=q[family+'_states'];eligible=[cp for cp in EARLY if cp<=len(states)]
            if set(q['labels'][family])!={str(cp) for cp in eligible}:raise ValueError('Unknown/missing stop label')
            for cp in [None,*eligible]:
                ak=(identifier,family,cp,'activation-cold');wk=(identifier,family,cp,'reused-warm')
                wanted.update([ak,wk]);wanted_warm.add(wk);a,w=samples[ak],samples[wk]
                raw=policy('fd-acquire-'+family+'-'+str(cp),cp,progress=is_progress)
                if a['policy_hash']!=validate_policy(raw,profile).policy_hash or w['policy_hash']!=a['policy_hash']:raise ValueError('Acquisition policy differs')
                if cp is None:
                    expected_ids,expected_distances=ref['native_ids'],ref['native_distances']
                else:
                    key=(identifier,family,cp);wanted_proofs.add(key);proof=proofs[key]
                    if proof['observed_prefix_sha256']!=digest(states[:cp]) or proof['policy_hash']!=a['policy_hash']:raise ValueError('Actual stop prefix differs')
                    expected_ids,expected_distances=proof['policy_ids'],proof['policy_distances']
                for r in (a,w,warmups[wk]):
                    if (r['policy_ids'],r['policy_distances'])!=(expected_ids,expected_distances):raise ValueError('Actual outcome differs')
                label={'recall':a['policy_recall'],'valid':a['valid'],'returned_count':a['returned_count'],
                  'layer0_distances':a['work']['layer0_distance_evaluations'],
                  'activation_ms_saved':a['native_ms']-a['policy_ms'],'reuse_ms_saved':w['native_ms']-w['policy_ms']}
                observed=q['continue_costs'][family] if cp is None else q['labels'][family][str(cp)]
                if label!=observed:raise ValueError('Fitting outcome/cost proxy does not reproduce')
    if wanted!=set(samples) or wanted_warm!=set(warmups) or wanted_proofs!=set(proofs) or set(probes)!=set(refs):raise ValueError('Incomplete acquisition coverage')
    getter_calls=sum(r['backend_calls'] for r in read(folder/'qualified-features.json'))
    if getter_calls!=cfg['complete_call_accounting']['qualification_backend_calls_per_database_allocation']:raise ValueError('Getter accounting differs')
    calls=4*len(items)+len(proofs)+2*(len(samples)+len(warmups))+getter_calls+(4*len(items) if evaluation else 0)
    if read(folder/'status.json')['backend_searches']!=calls:raise ValueError('Actual request counts do not reproduce')
    return evidence,{'retained_pairs':len(samples),'warmup_pairs':len(warmups),'actual_stop_proofs':len(proofs),'backend_searches':calls}


def analyze(campaign,package):
    cfg=verify(package);sys.path.insert(0,str(package/'vendor'))
    from fannagent_pgvector.profiles import PROFILE
    from execution import fit_study,validate_fit,arms_for,bypass108
    from policy_tools import predict,replay,assess
    from fannagent.api import validate_policy
    phases=['build','acquire/part-0','acquire/part-1','fit'];verify_phase(campaign,'build')
    built=read(campaign/'build/build.json')
    if built['module_sha256']!=sha(campaign/'build/vector.so') or built['package_manifest_sha256']!=sha(package/'manifest.json'):raise ValueError('Build identity differs')
    acquisition={}
    for i in range(2):
        _,acquisition[str(i)]=reproduce_acquisition(campaign,'acquire/part-'+str(i),package,lines(package/'inputs'/('acquire-'+str(i)+'.jsonl')),PROFILE)
    verify_phase(campaign,'fit');lock=validate_fit(package,campaign/'fit')
    with tempfile.TemporaryDirectory(prefix='feature-data-refit-') as tmp:
        rebuilt=fit_study(package,campaign,Path(tmp),lambda *a,**k:None)
    if rebuilt!=lock:raise ValueError('Calibration fit/selection does not independently reproduce')
    result={'status':'stopped_after_calibration','scope':cfg['scope'],'calibration_selection':{a:{k:p[k] for k in ('risk','nonconstant_selected_stop','policy_hash')} for a,p in lock['policies'].items()},
      'acquisition':acquisition,'evaluation_executed':False,'timing_executed':False,'final_latency_gate':'unmeasured',
      'provider_calls':0,'confirmation_queries':0,'ab_comparison':AB,'final_criteria_unchanged':True,
      'canonical_acceptance_established':False,'deployable_policy_selected':False,'fresh_independent_confirmation_required':True}
    evaluation=None
    if lock['proceed_to_evaluation']:
        phases.append('evaluate');evaluation,counts=reproduce_acquisition(campaign,'evaluate',package,lines(package/'inputs/evaluation.jsonl'),PROFILE,True)
        result.update(evaluation_executed=True,evaluation_counts=counts,status='stopped_after_common_evaluation')
        # Match actual candidate execution order exactly, including floating-point
        # cost-proxy reductions. Acquisition evidence is stored in query-ID order.
        by_id={q['query_id']:q for q in evaluation['queries']}
        ordered_evaluation=[by_id[item['query']['id']] for item in lines(package/'inputs/evaluation.jsonl')]
        records={a:replay(p['policy'],ordered_evaluation,a,PROFILE) for a,p in lock['policies'].items()}
        reports={a:assess(rows,tolerance=.005) for a,rows in records.items()}
        for a,r in reports.items():
            r['nonconstant_stop_cases']=sum(x['checkpoint'] is not None for x in records[a])
            r['eligible_for_timing']=bool(lock['policies'][a]['nonconstant_selected_stop'] and r['recall_pass'] and r['utility']>0)
        screen={'status':'complete','reports':reports,'proceed_to_timing':any(r['eligible_for_timing'] for r in reports.values()),
          'fit_lock_sha256':sha(campaign/'fit/fit-lock.json'),'provider_calls':0,'confirmation_queries':0,'ab_comparison':AB,
          'canonical_acceptance_established':False,'final_latency_gate':'unmeasured'}
        if screen!=read(campaign/'evaluate/screen.json'):raise ValueError('Common evaluation gate does not reproduce')
        actual=lines(campaign/'evaluate/candidate-proofs.jsonl')
        wanted={(a,r['query_id']):r for a,rs in records.items() for r in rs}
        if len(actual)!=720 or len({(r['arm'],r['query_id']) for r in actual})!=720:raise ValueError('Actual locked-candidate coverage differs')
        acquired_proofs={(r['query_id'],r['family'],r['checkpoint']):r for r in lines(campaign/'evaluate/proofs.jsonl')}
        refs={r['query_id']:r for r in lines(campaign/'evaluate/references.jsonl')}
        for r in actual:
            a,q=r['arm'],r['query_id'];w=wanted[(a,q)]
            if r['replay']!=w or r['checkpoint']!=w['checkpoint'] or r['policy_hash']!=lock['policies'][a]['policy_hash']:raise ValueError('Actual candidate replay differs')
            p=refs[q] if w['checkpoint'] is None else acquired_proofs[(q,'local' if CONDITIONS[a]['local_filter'] else 'base',w['checkpoint'])]
            names=('native_ids','native_distances') if w['checkpoint'] is None else ('policy_ids','policy_distances')
            if (r['policy_ids'],r['policy_distances'])!=(p[names[0]],p[names[1]]):raise ValueError('Candidate result differs from proof')
        result['common_evaluation']=screen
        if screen['proceed_to_timing']:
            result.update(status='timing_complete',timing_executed=True,final_latency_gate='measured')
            timed,per_block=timing_report(campaign,package,evaluation,lock,PROFILE)
            result.update(timing=timed,per_block=per_block)
            result['factorial_contrasts']=read(campaign/'analysis/factorial-contrasts.json')
            phases.extend('blocks/block-'+str(i) for i in range(3))
    if not lock['proceed_to_evaluation'] and (campaign/'evaluate').exists():raise ValueError('Evaluation ran after failed calibration')
    if not result['timing_executed'] and (campaign/'blocks').exists():raise ValueError('Timing ran after failed gate')
    out=campaign/'analysis';out.mkdir(exist_ok=True);save(out/'performance.json',result)
    text=['Four-arm feature/data ablation: independently reproduced.','Original agent-generation A/B: INCONCLUSIVE.',
      'Status: '+result['status'],'No canonical acceptance or automatic deployment.',
      'Arm | selected risk | nonconstant calibration selection']
    for a,p in lock['policies'].items():text.append(a+' | '+str(p['risk'])+' | '+str(p['nonconstant_selected_stop']))
    if result['timing_executed']:
        text.append('Arm | activation saved ms | activation saved % | reuse saved ms | reuse saved % | recall delta pp | both final gates')
        for a,modes in result['timing'].items():
            x,y=modes['activation-cold']['overall'],modes['reused-warm']['overall']
            text.append(f"{a} | {x['ms_saved']:+.6f} | {x['percent_saved']:+.3f} | {y['ms_saved']:+.6f} | {y['percent_saved']:+.3f} | {100*x['recall_delta']:+.3f} | {modes['both_final_gates']}")
    save(out/'report.txt','\n'.join(text)+'\n',raw=True)
    save(out/'verification.json',{'status':'verified','package_manifest_sha256':sha(package/'manifest.json'),
      'fit_lock_sha256':sha(campaign/'fit/fit-lock.json'),'independent_fit_reproduction':True,
      'raw_files_sha256':{str(p.relative_to(campaign)):sha(p) for phase in phases for p in sorted((campaign/phase).rglob('*')) if p.is_file()},
      'provider_calls':0,'confirmation_queries':0,'ab_comparison':AB,'canonical_acceptance_established':False})
    print('\n'.join(text));return result


def timing_report(campaign,package,evidence,lock,profile):
    from execution import arms_for,bypass108
    from policy_tools import predict
    from fannagent.api import validate_policy
    from study_stats import with_filters,feasible
    cfg=read(package/'experiment.json');stats_cfg={**cfg,'seed':cfg['bootstrap_seed']};data={q['query_id']:q for q in evidence['queries']}
    items={i['query']['id']:i['query'] for i in lines(package/'inputs/evaluation.jsonl')}
    refs={r['query_id']:r for r in lines(campaign/'evaluate/references.jsonl')};all_rows=[];per_block={}
    for block in range(3):
        f=verify_phase(campaign,'blocks/block-'+str(block));status=read(f/'status.json')
        identity=read(f/'runtime-identity.json')
        if identity['module_sha256']!=lock['module_sha256'] or identity['package_manifest_sha256']!=sha(package/'manifest.json') or read(f/'database-identity.json')!=read(package/'source-index.json'):raise ValueError('Timing runtime/index differs')
        proofs=lines(f/'proofs.jsonl');proofmap={(p['query_id'],p['arm']):p for p in proofs}
        if len(proofs)!=1440 or len(proofmap)!=1440:raise ValueError('Timing proof coverage differs')
        planned={}
        for q in data.values():
            for arm,raw,kind in arms_for(q,lock):
                bypass=kind=='routing-control' and bypass108(items[q['query_id']])
                progress='progress_filter' in raw['feature_groups'];base='local_filter' not in raw['feature_groups']
                names=cfg['base_feature_names'] if base else cfg['static_feature_names']+(EXTRA if progress else [])
                states=q['local_states' if progress else 'base_states']
                if base:states=[{**s,'features':{n:s['features'][n] for n in names}} for s in states]
                cp=None if bypass else predict(raw,states,profile)
                p=proofmap[(q['query_id'],arm)]
                if p['checkpoint']!=cp or p['native_bypass']!=bypass or p['policy_hash']!=(None if bypass else validate_policy(raw,profile).policy_hash):raise ValueError('Timing first-stop plan differs')
                if p['observed_prefix_sha256']!=(None if bypass else digest(states if cp is None else states[:cp])):raise ValueError('Timed prefix differs')
                planned[(q['query_id'],arm)]=(kind,bypass,p)
        rows=lines(f/'pairs.jsonl');warms=lines(f/'warmups.jsonl');seen=set();warmseen=set()
        for rs,keys,warm in [(rows,seen,False),(warms,warmseen,True)]:
            for r in rs:
                validate_row(r,refs[r['query_id']]);kind,bypass,p=planned[(r['query_id'],r['arm'])]
                if r['block']!=block or r['kind']!=kind or r['native_bypass']!=bypass or r['policy_hash']!=p['policy_hash']:raise ValueError('Timing treatment differs')
                if (r['policy_ids'],r['policy_distances'])!=(p['policy_ids'],p['policy_distances']):raise ValueError('Timed result differs from actual proof')
                if kind!='routing-control' and r['routing_ms']!=0:raise ValueError('Unexpected routing cost')
                key=(r['query_id'],r['arm']) if warm else (r['query_id'],r['arm'],r['regime'],r['repetition'])
                if key in keys:raise ValueError('Duplicate timing pair')
                keys.add(key)
        wanted={(q,a,m,rep) for q,source in data.items() for a,_,_ in arms_for(source,lock) for m,n in [('activation-cold',1),('reused-warm',3)] for rep in range(n)}
        if seen!=wanted or warmseen!={(q,a) for q,source in data.items() for a,_,_ in arms_for(source,lock)}:raise ValueError('Incomplete retained/warmup coverage')
        if len(rows)!=5760 or len(warms)!=1440 or status['backend_searches']!=cfg['complete_call_accounting']['timing_backend_calls_per_block']:raise ValueError('Timing request counts differ')
        per_block[str(block)]=summaries(rows,stats_cfg,with_filters,feasible)
        all_rows.extend(rows)
    save(campaign/'analysis/factorial-contrasts.json',{m:contrasts(all_rows,m) for m in ('activation-cold','reused-warm')})
    return summaries(all_rows,stats_cfg,with_filters,feasible),per_block


def contrasts(rows,mode):
    import numpy as np
    weights={'progress_small':{'P100':1,'S100':-1},'progress_large':{'P160':1,'S160':-1},
      'data_static':{'S160':1,'S100':-1},'data_progress':{'P160':1,'P100':-1},
      'interaction':{'P160':1,'P100':-1,'S160':-1,'S100':1}}
    grouped=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in rows:
        if r['regime']==mode and r['arm'] in CONDITIONS:grouped[r['group']][r['arm']].append(r)
    result={}
    for name,w in weights.items():
        matrix=[]
        for group,arms in sorted(grouped.items()):
            if set(arms)!=set(CONDITIONS):raise ValueError('Factorial group coverage differs')
            matrix.append([sum(value*np.mean([r['native_ms']-r['policy_ms'] for r in arms[a]]) for a,value in w.items()),
                           sum(value*np.mean([r['recall_delta'] for r in arms[a]]) for a,value in w.items())])
        matrix=np.asarray(matrix);rng=np.random.default_rng(CONFIG['bootstrap_seed'])
        boot=matrix[rng.integers(0,len(matrix),size=(10000,len(matrix)))].mean(axis=1)
        ci=np.quantile(boot,[.025,.975],axis=0)
        result[name]={'additional_ms_saved':float(matrix[:,0].mean()),'additional_ms_saved_ci95':ci[:,0].tolist(),
          'recall_delta_effect':float(matrix[:,1].mean()),'recall_delta_effect_ci95':ci[:,1].tolist(),
          'independent_vectors':len(matrix),'scope':'Descriptive development contrast, no multiplicity-adjusted discovery claim.'}
    return result


def summaries(rows,cfg,with_filters,feasible):
    result={}
    for arm in sorted({r['arm'] for r in rows}):
        modes={m:with_filters([r for r in rows if r['arm']==arm and r['regime']==m],cfg) for m in ('activation-cold','reused-warm')}
        for m,r in modes.items():
            for f,s in [('overall',r['overall']),*r['per_filter'].items()]:
                s.update(ms_saved=-s['gap_ms'],percent_saved=100*(s['native_ms']-s['policy_ms'])/s['native_ms'])
                selected=[row for row in rows if row['arm']==arm and row['regime']==m and (f=='overall' or row['stratum']==f)]
                if any(not row['work_available'] for row in selected):s['layer0_distances']=None
        modes['both_final_gates']=bool(feasible(modes['activation-cold'],cfg) and feasible(modes['reused-warm'],cfg))
        result[arm]=modes
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--campaign',type=Path,required=True);parser.add_argument('--package',type=Path,required=True)
    args=parser.parse_args();analyze(args.campaign.resolve(),args.package.resolve())
