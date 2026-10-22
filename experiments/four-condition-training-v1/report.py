"""Reproduce native data, nested fits, complete coverage and fixed final gates."""
import argparse
from collections import defaultdict
import math
from pathlib import Path
import sys

from no_models import enforce
enforce()

import numpy as np
from contract import AB,CONFIG,CONDITIONS,EARLY,EXTRA,SEED,digest,lines,read,save,sha
from control import verify


def validate_row(row,expected):
    q=row['query_id'];reference=expected[q]
    if (row['native_ids'],row['native_distances'])!=(reference['ids'],reference['distances']):raise ValueError('Original native result changed')
    if row['native_recall']!=reference['recall']:raise ValueError('Original native recall changed')
    if row['truth_k']!=10 or row['group']!=q.rsplit('-',1)[0] or row['stratum']!=q.rsplit('-',1)[1]:raise ValueError('Invalid query/group identity')
    for mode in ('native','policy'):
        ids=row[mode+'_ids'];ds=row[mode+'_distances']
        if len(set(ids))!=len(ids) or len(ids)!=len(ds) or len(ids)>10 or any(not math.isfinite(v) for v in ds):raise ValueError('Invalid result IDs/distances')
        strict=len(set(ids)&set(row['truth_strict']));ties=min(10-len(row['truth_strict']),len(set(ids)&set(row['truth_ties'])))
        if abs((strict+ties)/10-row[mode+'_recall'])>1e-12:raise ValueError('Raw recall does not reproduce')
        for field in (mode+'_ms',mode+'_outer_ms'):
            if not math.isfinite(row[field]) or row[field]<=0:raise ValueError('Invalid latency')
    if row['returned_count']!=len(row['policy_ids']) or row['valid']!=(row['returned_count']==10):raise ValueError('Completeness flag differs')
    if abs(row['recall_delta']-(row['policy_recall']-row['native_recall']))>1e-12:raise ValueError('Recall difference differs')
    if row['policy_already_activated']!=(row['regime']=='reused-warm'):raise ValueError('Activation state differs')
    if row['work']['frontier_snapshot_count'] or row['work']['frontier_sort_count']:raise ValueError('Untimed/full statistics treatment differs')


def label_from(a,w):
    return {'recall':a['policy_recall'],'valid':a['valid'],'returned_count':a['returned_count'],
        'layer0_distances':a['work']['layer0_distance_evaluations'],
        'activation_ms_saved':a['native_ms']-a['policy_ms'],'reuse_ms_saved':w['native_ms']-w['policy_ms']}


def acquisition_verify(package,gate,profile):
    from execution import validate_lock,policy
    from fitting import build_lock
    lock,evidence=validate_lock(package,gate);expected=read(package/'inputs/native-results.json')
    cfg=read(package/'experiment.json');original={q['query_id']:q for q in lines(package/'inputs/training-640-light.jsonl')}
    refs={q['query_id']:q for q in lines(gate/'references.jsonl')};proofs={}
    if set(refs)!=set(expected):raise ValueError('Acquisition reference coverage differs')
    for p in lines(gate/'proofs.jsonl'):
        key=(p['query_id'],p['family'],p['checkpoint'])
        if key in proofs:raise ValueError('Duplicate stop proof')
        proofs[key]=p
    samples={};warmups={}
    for filename,target in [('pairs.jsonl',samples),('warmups.jsonl',warmups)]:
        for row in lines(gate/filename):
            validate_row(row,expected)
            key=(row['query_id'],row['family'],row['checkpoint'],row['regime'])
            if key in target:raise ValueError('Duplicate acquisition pair')
            target[key]=row
    from fannagent.api import validate_policy
    wanted=set();wanted_warm=set();wanted_proof=set();reconstructed=[]
    for q in evidence['queries']:
        identifier=q['query_id'];ref=refs[identifier]
        if ref['base_states']!=original[identifier]['states']:raise ValueError('Original base trajectory changed')
        if [{**s,'features':{n:s['features'][n] for n in cfg['base_feature_names']}} for s in ref['local_states']]!=ref['base_states']:raise ValueError('Local instrumentation changed traversal')
        item={k:q[k] for k in ('query_id','group','stratum','native_recall','native_work')}
        item.update(base_states=ref['base_states'],local_states=ref['local_states'],labels={'base':{},'local':{}},continue_costs={})
        for family in ('base','local'):
            cps=[None,*[cp for cp in EARLY if cp<=len(q[family+'_states'])]]
            for cp in cps:
                akey=(identifier,family,cp,'activation-cold');wkey=(identifier,family,cp,'reused-warm')
                wanted.update([akey,wkey]);wanted_warm.add(wkey)
                a,w=samples[akey],samples[wkey]
                raw=policy('four-acquire-'+family+'-'+str(cp),cp,family=='local')
                if a['policy_hash']!=validate_policy(raw,profile).policy_hash or w['policy_hash']!=a['policy_hash']:raise ValueError('Acquisition policy changed')
                if cp is None:
                    if a['policy_ids']!=a['native_ids'] or w['policy_ids']!=w['native_ids']:raise ValueError('Continue differs')
                    item['continue_costs'][family]=label_from(a,w)
                else:
                    key=(identifier,family,cp);wanted_proof.add(key);p=proofs[key]
                    if p['observed_prefix']!=q[family+'_states'][:cp] or p['policy_hash']!=a['policy_hash']:raise ValueError('Stop proof changed')
                    for row in (a,w,warmups[wkey]):
                        if row['policy_ids']!=p['policy_ids'] or row['policy_distances']!=p['policy_distances']:raise ValueError('Timed outcome differs from native proof')
                    item['labels'][family][str(cp)]=label_from(a,w)
        reconstructed.append(item)
    if wanted!=set(samples) or wanted_warm!=set(warmups) or wanted_proof!=set(proofs):raise ValueError('Incomplete acquisition coverage')
    if reconstructed!=evidence['queries']:raise ValueError('Fit evidence does not reproduce from raw data')
    receipts=lines(gate/'probe-verification.jsonl')
    if {r['query_id'] for r in receipts}!=set(expected) or len(receipts)!=300:raise ValueError('Incomplete local-probe verification')
    for r in receipts:
        if not r['actual_metadata_verified'] or not 0<r['receipt']['nodes']<=64 or not 0<r['receipt']['examined']<=64:raise ValueError('Local metadata verification failed')
        ref=refs[r['query_id']];qs=next(q for q in evidence['queries'] if q['query_id']==r['query_id'])
        threshold=ref['local_states'][0]['features']['query_predicate_threshold']
        for s in ref['local_states']:
            f=s['features'];n=f['local_probe_examined'];passed=sum(qs['stratum']=='unfiltered' or (not null and vote>=threshold) for _,vote,null in r['receipt']['rows'][:n])
            if passed!=f['local_probe_passed'] or (n and abs(f['local_probe_pass_ratio']-passed/n)>1e-12):raise ValueError('Local feature prefix differs')
    getter_calls=sum(r['backend_calls'] for r in read(gate/'qualified-features.json'))
    expected_calls=4*300+len(proofs)+2*(len(samples)+len(warmups))+getter_calls
    if read(gate/'status.json')['backend_searches']!=expected_calls:raise ValueError('Acquisition call accounting differs')
    rebuilt=build_lock(evidence,profile,sha(package/'manifest.json'),lock['module_sha256'])
    if rebuilt!=lock:raise ValueError('Nested fitting/selection lock does not independently reproduce')
    return lock,evidence,{'retained_pairs':len(samples),'discarded_warmup_pairs':len(warmups),'actual_stop_proofs':len(proofs),'backend_calls':expected_calls}


def contrasts(rows,mode):
    # Positive ms = additional saving from the first condition in the contrast.
    selected=[r for r in rows if r['regime']==mode and r['arm'] in CONDITIONS]
    grouped=defaultdict(lambda:defaultdict(list))
    for r in selected:grouped[r['group']][r['arm']].append(r)
    names={'local_late_C_minus_A':{'C':1,'A':-1},'local_early_D_minus_B':{'D':1,'B':-1},
        'earlier_base_B_minus_A':{'B':1,'A':-1},'earlier_local_D_minus_C':{'D':1,'C':-1},
        'interaction_D_minus_C_minus_B_plus_A':{'D':1,'C':-1,'B':-1,'A':1}}
    reports={}
    for name,weights in names.items():
        matrix=[]
        for group,arms in sorted(grouped.items()):
            if set(arms)!=set(CONDITIONS):raise ValueError('Incomplete factorial group')
            matrix.append([sum(w*np.mean([r['native_ms']-r['policy_ms'] for r in arms[a]]) for a,w in weights.items()),
                sum(w*np.mean([r['recall_delta'] for r in arms[a]]) for a,w in weights.items())])
        matrix=np.asarray(matrix);rng=np.random.default_rng(SEED)
        boot=matrix[rng.integers(0,len(matrix),size=(10000,len(matrix)))].mean(axis=1)
        ci=np.quantile(boot,[.025,.975],axis=0)
        reports[name]={'additional_ms_saved':float(matrix[:,0].mean()),'additional_ms_saved_ci95':ci[:,0].tolist(),
            'recall_delta_effect':float(matrix[:,1].mean()),'recall_delta_effect_ci95':ci[:,1].tolist(),
            'independent_vectors':len(matrix),'interpretation':'Descriptive training contrast, no multiplicity-adjusted discovery claim.'}
    return reports


def analyze(campaign,package):
    cfg=verify(package);sys.path.insert(0,str(package/'vendor'))
    from fannagent_pgvector.profiles import PROFILE
    from fannagent.api import validate_policy
    from execution import arms_for
    from fitting import predict
    from study_stats import with_filters,feasible
    phases=['build','acquire',*[f'blocks/block-{i}' for i in range(3)]]
    for phase in phases:
        f=campaign/phase
        if read(f/'host-exit.json')['exit_code'] or read(f/'protected-source-before.json')!=read(f/'protected-source-after.json'):raise ValueError('Allocation/source preservation failed: '+phase)
        if phase!='build' and (read(f/'job-exit.json')['exit_code'] or read(f/'status.json')['status']!='complete'):raise ValueError('Incomplete allocation: '+phase)
    build=read(campaign/'build/build.json')
    if build['module_sha256']!=sha(campaign/'build/vector.so') or build['package_manifest_sha256']!=sha(package/'manifest.json'):raise ValueError('Build identity differs')
    lock,evidence,acquisition=acquisition_verify(package,campaign/'acquire',PROFILE)
    data={q['query_id']:q for q in evidence['queries']};expected=read(package/'inputs/native-results.json')
    planned={}
    for q in data.values():
        for arm,raw,kind in arms_for(q,lock):
            family='local' if 'local_filter' in raw['feature_groups'] else 'base'
            cp=predict(raw,q[family+'_states'],PROFILE)
            states=q[family+'_states'] if cp is None else q[family+'_states'][:cp]
            planned[(q['query_id'],arm)]={'policy_hash':validate_policy(raw,PROFILE).policy_hash,
                'checkpoint':cp,'prefix_sha256':digest(states),'kind':kind}
    all_rows=[];per_block={};warmup_count=0
    for block in range(3):
        f=campaign/'blocks'/('block-'+str(block));status=read(f/'status.json');identity=read(f/'runtime-identity.json')
        if identity['module_sha256']!=lock['module_sha256'] or identity['package_manifest_sha256']!=sha(package/'manifest.json') or identity['query_file_sha256']!=sha(package/'inputs/queries.jsonl'):raise ValueError('Measured runtime differs')
        if read(f/'database-identity.json')!=read(package/'source-index.json'):raise ValueError('Measured index differs')
        rows=lines(f/'pairs.jsonl');warmups=lines(f/'warmups.jsonl');proofs=lines(f/'proofs.jsonl')
        proof_map={(r['query_id'],r['arm']):r for r in proofs}
        if len(proof_map)!=3900 or len(proofs)!=3900:raise ValueError('Incomplete actual-stop proof coverage')
        seen=set();warm_seen=set()
        for raw_rows,observed,warm in [(rows,seen,False),(warmups,warm_seen,True)]:
            for r in raw_rows:
                validate_row(r,expected);q=data[r['query_id']];plan=planned[(r['query_id'],r['arm'])];cp=plan['checkpoint']
                if r['policy_hash']!=plan['policy_hash'] or r['fold']!=lock['folds'][q['group']] or r['kind']!=plan['kind']:raise ValueError('Wrong held-out fold policy')
                proof=proof_map[(r['query_id'],r['arm'])]
                if proof['predicted_checkpoint']!=cp or proof['observed_prefix_sha256']!=plan['prefix_sha256'] or proof['policy_hash']!=r['policy_hash']:raise ValueError('First-stop proof differs')
                if r['policy_ids']!=proof['policy_ids'] or r['policy_distances']!=proof['policy_distances']:raise ValueError('Timed result differs from proof')
                if r['kind'] in ('continue','matched-continue') and (r['policy_ids'],r['policy_distances'])!=(r['native_ids'],r['native_distances']):raise ValueError('Matched/native outputs differ')
                if r['block']!=block:raise ValueError('Wrong block')
                key=(r['query_id'],r['arm']) if warm else (r['query_id'],r['arm'],r['regime'],r['repetition'])
                if key in observed:raise ValueError('Duplicate pair')
                observed.add(key)
        want={(q,a,m,rep) for q,source in data.items() for a,_,_ in arms_for(source,lock) for m,n in [('activation-cold',1),('reused-warm',3)] for rep in range(n)}
        want_warm={(q,a) for q,source in data.items() for a,_,_ in arms_for(source,lock)}
        if seen!=want or warm_seen!=want_warm or len(rows)!=15600 or status['retained_pairs']!=len(rows):raise ValueError('Incomplete retained/warmup coverage')
        if status['backend_searches']!=cfg['complete_call_accounting']['measurement_maximum_backend_calls_per_block']:raise ValueError('Measurement call accounting differs')
        if status['confirmation_queries'] or status['provider_calls']:raise ValueError('Forbidden query/model use')
        per_block[str(block)]={arm:{m:with_filters([r for r in rows if r['arm']==arm and r['regime']==m],cfg) for m in ('activation-cold','reused-warm')} for arm in sorted({r['arm'] for r in rows})}
        all_rows.extend(rows);warmup_count+=len(warmups)
    overall={arm:{m:with_filters([r for r in all_rows if r['arm']==arm and r['regime']==m],cfg) for m in ('activation-cold','reused-warm')} for arm in sorted({r['arm'] for r in all_rows})}
    for blocks in [overall,*per_block.values()]:
        for modes in blocks.values():
            for r in modes.values():
                for s in [r['overall'],*r['per_filter'].values()]:
                    s.update(ms_saved=-s['gap_ms'],percent_saved=100*(s['native_ms']-s['policy_ms'])/s['native_ms'])
    condition_reports={c:{'activation_gate_pass':bool(feasible(overall[c]['activation-cold'],cfg)),
        'reuse_gate_pass':bool(feasible(overall[c]['reused-warm'],cfg)),
        'fold_abstentions':sum(p['risk'] is None for k,p in lock['policies'].items() if k.startswith(c+'/'))} for c in CONDITIONS}
    result={'scope':cfg['scope'],'status':'verified_training_procedure_comparison','conditions':condition_reports,
        'overall':overall,'per_block':per_block,'factorial_contrasts':{m:contrasts(all_rows,m) for m in ('activation-cold','reused-warm')},
        'acquisition':acquisition,'retained_pairs':len(all_rows),'discarded_warmup_pairs':warmup_count,'independent_vector_groups':100,
        'provider_calls':0,'confirmation_queries':0,'final_criteria_unchanged':True,'ab_comparison':AB,'canonical_acceptance_established':False,
        'deployable_policy_selected':False,'fresh_independent_confirmation_required':True,
        'limitations':['OOF procedure comparison on the original learning groups, not independent confirmation.',
            'Bootstrap conditions on these fitted OOF outputs; training-process uncertainty is not independently bootstrapped.',
            'Factorial contrasts are descriptive, without multiplicity correction.','Oracle uses hindsight and is not a deployable policy.']}
    out=campaign/'analysis';out.mkdir(exist_ok=True);save(out/'performance.json',result)
    text=['Four-condition training study: independently reproduced','Original agent-generation A/B comparison: INCONCLUSIVE.',
        'No deployable policy selected; fresh independent confirmation is required.',
        'condition | activation saved ms | activation saved % | reuse saved ms | reuse saved % | recall delta pp | activation gate | reuse gate']
    for c,r in condition_reports.items():
        a=overall[c]['activation-cold']['overall'];w=overall[c]['reused-warm']['overall']
        text.append(f"{c} | {a['ms_saved']:+.6f} | {a['percent_saved']:+.3f} | {w['ms_saved']:+.6f} | {w['percent_saved']:+.3f} | {100*a['recall_delta']:+.3f} | {r['activation_gate_pass']} | {r['reuse_gate_pass']}")
    save(out/'report.txt','\n'.join(text)+'\n',raw=True)
    save(out/'verification.json',{'status':'verified','package_manifest_sha256':sha(package/'manifest.json'),
        'fit_lock_sha256':sha(campaign/'acquire/fit-lock.json'),'raw_files_sha256':{str(p.relative_to(campaign)):sha(p) for phase in phases for p in sorted((campaign/phase).rglob('*')) if p.is_file()},
        'nested_fit_reproduction':True,'retained_pairs':46800,'ab_comparison':AB,'provider_calls':0,'confirmation_queries':0})
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--campaign',type=Path,required=True);parser.add_argument('--package',type=Path,required=True)
    args=parser.parse_args();p=analyze(args.campaign.resolve(),args.package.resolve())
    print(__import__('json').dumps({'status':p['status'],'conditions':p['conditions'],'retained_pairs':p['retained_pairs'],'ab_comparison':AB},indent=2))


if __name__=='__main__':main()
