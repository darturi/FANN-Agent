"""Frozen nested offline comparison; new policy timing remains unmeasured."""
import argparse
from collections import Counter
import datetime
import json
from pathlib import Path
import sys
import time

from offline_common import AB, DESIGN, SOURCE, digest, initialize, read, save, sha, verify_inputs


def replay(raw, queries, condition, profile):
    from contract import CONDITIONS
    from fitting import references
    from fannagent.api import FeatureValue, PolicyInput, validate_policy
    from fannagent.api.primitives.interpreter import evaluate_policy
    artifact = validate_policy(raw,profile)
    names = sorted(set(references(raw['root'])))
    floats = frozenset(n for n in names if profile.runtime_features[n].kind == 'float')
    spec = CONDITIONS[condition]; family = 'local' if spec['local_filter'] else 'base'
    result = []
    for q in queries:
        checkpoint = None
        for state in q[family+'_states']:
            # Both fitters have an explicit allowed-checkpoint guard. No other
            # checkpoint can stop; skip its interpreter work only in offline replay.
            if state['checkpoint_index'] not in spec['checkpoints']: continue
            values = state['features']
            inp = PolicyInput(features={n:FeatureValue(available=values.get(n) is not None,value=values.get(n)) for n in names})
            if str(evaluate_policy(artifact,inp,float_features=floats)) == 'stop':
                checkpoint = state['checkpoint_index']; break
        if checkpoint is None:
            label = q['continue_costs'][family]
            recall, valid, count = q['native_recall'],True,10
        else:
            if str(checkpoint) not in q['labels'][family]:
                raise ValueError('Unknown first stop; new measurement required')
            label = q['labels'][family][str(checkpoint)]
            recall,valid,count = label['recall'],label['valid'],label['returned_count']
        result.append({'query_id':q['query_id'],'group':q['group'],'stratum':q['stratum'],
            'native_recall':q['native_recall'],'policy_recall':recall,
            'recall_delta':recall-q['native_recall'],'valid':bool(valid and count==10),
            'returned_count':count,'checkpoint':checkpoint,'native_work':q['native_work'],
            'layer0_distances':label['layer0_distances'],
            'activation_proxy_ms_saved':label['activation_ms_saved'],
            'reuse_proxy_ms_saved':label['reuse_ms_saved']})
    return result


def summarize(rows):
    import numpy as np
    reports = {}
    for f in ['overall','unfiltered','votes32','votes108']:
        selected = [r for r in rows if f == 'overall' or r['stratum'] == f]
        groups = sorted({r['group'] for r in selected})
        matrix = np.asarray([[np.mean([r[k] for r in selected if r['group']==g])
                              for k in ['recall_delta','activation_proxy_ms_saved','reuse_proxy_ms_saved']]
                             for g in groups])
        rng = np.random.default_rng(DESIGN['seed'])
        boot = matrix[rng.integers(0,len(matrix),size=(DESIGN['bootstrap_samples'],len(matrix)))].mean(axis=1)
        ci = np.quantile(boot,[.025,.975],axis=0)
        native = float(np.mean([r['native_recall'] for r in selected]))
        all_valid = all(r['valid'] and r['returned_count']==10 for r in selected)
        reports[f] = {
            'independent_vectors':len(groups),'query_filter_cases':len(selected),
            'native_recall':native,'policy_recall':float(np.mean([r['policy_recall'] for r in selected])),
            'recall_delta':float(matrix[:,0].mean()),'recall_delta_ci95':ci[:,0].tolist(),
            'activation_proxy_ms_saved':float(matrix[:,1].mean()),'activation_proxy_ms_saved_ci95':ci[:,1].tolist(),
            'reuse_proxy_ms_saved':float(matrix[:,2].mean()),'reuse_proxy_ms_saved_ci95':ci[:,2].tolist(),
            'all_valid_complete_top10':all_valid,
            'final_recall_replay_pass':bool(all_valid and ci[0,0]>=-DESIGN['final_recall_tolerance']
                                           and (f=='overall' or native>=DESIGN['minimum_native_recall'])),
            'development_recall_replay_pass':bool(all_valid and ci[0,0]>=-DESIGN['development_recall_margin']
                                                 and (f=='overall' or native>=DESIGN['minimum_native_recall'])),
            'stopped_cases':sum(r['checkpoint'] is not None for r in selected),
            'mean_layer0_work_reduction_fraction':float(np.mean([1-r['layer0_distances']/max(1,r['native_work']) for r in selected])),
        }
    return {'overall':reports.pop('overall'),'per_filter':reports,
            'first_stop_histogram':dict(sorted(Counter('continue' if r['checkpoint'] is None else str(r['checkpoint']) for r in rows).items())),
            'final_latency_gate':'unmeasured','final_combined_acceptance':False}


def nested_first_stop(evidence, baseline, profile, output):
    from first_stop import fit
    from fitting import assess, predict
    from contract import CONDITIONS, GROUPS, folds
    from fannagent.api import validate_policy
    rows = evidence['queries']; groups = {q['group'] for q in rows}
    outer = folds(groups,5,'outer-v1')
    if outer != baseline['folds']: raise ValueError('Original outer folds differ')
    policies = {}; validation = []; out_of_fold = []
    fit_count = 0; score_count = 0; interpreter_checks = 0
    for outer_fold in range(5):
        training = sorted(g for g in groups if outer[g]!=outer_fold)
        heldout = sorted(g for g in groups if outer[g]==outer_fold)
        inner = folds(training,4,'inner-v1-'+str(outer_fold))
        for condition in CONDITIONS:
            trials = []
            for risk in DESIGN['risk_weights']:
                records = []; proofs = []
                for inner_fold in range(4):
                    fit_groups = [g for g in training if inner[g]!=inner_fold]
                    test_groups = [g for g in training if inner[g]==inner_fold]
                    assert not set(fit_groups) & (set(test_groups)|set(heldout))
                    raw,proof = fit(rows,condition,risk,profile,evidence['base_feature_names'],fit_groups)
                    fit_count += 1; score_count += proof['candidate_scores_computed']
                    proofs.append({**proof,'inner_fold':inner_fold,'validation_groups':sorted(test_groups),
                                   'policy':raw})
                    tested = [q for q in rows if q['group'] in set(test_groups)]
                    records.extend(replay(raw,tested,condition,profile))
                trials.append({'risk':risk,'assessment':assess(records),'fit_proofs':proofs})
            eligible = [t for t in trials if t['assessment']['development_recall_pass'] and t['assessment']['utility']>0]
            if eligible:
                chosen = sorted(eligible,key=lambda t:(-t['assessment']['utility'],-t['risk']))[0]
                raw,proof = fit(rows,condition,chosen['risk'],profile,evidence['base_feature_names'],training)
                fit_count += 1; score_count += proof['candidate_scores_computed']
                reason = 'Unchanged inner development reserve and positive cost proxies; best worst-regime utility.'
                # Audit packed-state training scores against the shared interpreter
                # on the complete trajectories of every selected refit's group.
                family = 'local' if CONDITIONS[condition]['local_filter'] else 'base'
                for q in rows:
                    if q['group'] in set(training):
                        actual = predict(raw,q[family+'_states'],profile)
                        if proof['training_first_stops'][q['query_id']] != actual:
                            raise ValueError('Packed first-stop optimizer differs from shared interpreter')
                        interpreter_checks += 1
            else:
                raw = {'name':'offline-first-stop-'+condition+'-abstain-'+str(outer_fold),'root':'continue',
                       'feature_groups':GROUPS+(['local_filter'] if CONDITIONS[condition]['local_filter'] else [])}
                proof = {'condition':condition,'risk':None,'training_groups':training,
                         'policy_hash':validate_policy(raw,profile).policy_hash}
                reason = 'No inner candidate passes unchanged development reserve and positive proxies.'
            key = condition+'/'+str(outer_fold)
            policies[key] = {**proof,'policy':raw,'held_out_groups':heldout,'outer_fold':outer_fold,'selection_reason':reason}
            validation.append({'condition':condition,'outer_fold':outer_fold,'trials':trials})
            tested = [q for q in rows if q['group'] in set(heldout)]
            records = replay(raw,tested,condition,profile)
            family = 'local' if CONDITIONS[condition]['local_filter'] else 'base'
            for q,r in zip(tested,records):
                if predict(raw,q[family+'_states'],profile) != r['checkpoint']:
                    raise ValueError('Sparse replay differs from full shared-interpreter replay')
                interpreter_checks += 1
            out_of_fold.extend({**r,'fitter':'first_stop_beam','condition':condition,'outer_fold':outer_fold,
                                'policy_hash':proof['policy_hash']} for r in records)
            save(output/'folds'/(condition+'-'+str(outer_fold)+'.json'),
                 {'policy':policies[key],'inner_trials':trials,'held_out_replay':records})
            print(json.dumps({'phase':'nested_first_stop','condition':condition,'outer_fold':outer_fold,
                              'risk':proof['risk'],'held_out_stops':sum(r['checkpoint'] is not None for r in records),
                              'conventional_fits_completed':fit_count,'candidate_scores_computed':score_count}),flush=True)
    return {'policies':policies,'nested_validation':validation,'out_of_fold':out_of_fold,
            'conventional_fits':fit_count,'candidate_scores_computed':score_count,
            'shared_interpreter_cross_checks':interpreter_checks}


def run(output):
    pins,package = initialize()
    import numpy as np
    from fannagent_pgvector.profiles import PROFILE
    from fitting import build_lock, predict
    from contract import CONDITIONS
    start = time.monotonic()
    if output.exists(): raise ValueError('Use a fresh output directory; preserve all prior attempts')
    output.mkdir(parents=True)
    source_hashes = {p.name:sha(p) for p in sorted(SOURCE.iterdir()) if p.is_file()}
    plan = {'design':DESIGN,'source_files_sha256':source_hashes,'inputs':pins,
            'python':sys.version,'numpy':np.__version__}
    save(output/'design-lock.json',plan)
    print(json.dumps({'phase':'design_frozen','design_lock_sha256':sha(output/'design-lock.json')}),flush=True)
    campaign = verify_inputs(pins,package)
    evidence = read(campaign/'acquire/evidence.json');baseline = read(campaign/'acquire/fit-lock.json')
    if len(evidence['queries'])!=300 or len({q['group'] for q in evidence['queries']})!=100:
        raise ValueError('Original learning inventory required')
    if evidence['confirmation_queries'] or evidence['model_calls']:
        raise ValueError('Forbidden input provenance')
    print(json.dumps({'phase':'reproducing_original_cart'}),flush=True)
    rebuilt = build_lock(evidence,PROFILE,pins['package_manifest_sha256'],baseline['module_sha256'])
    if rebuilt != baseline: raise ValueError('Original CART lock does not reproduce exactly')
    save(output/'baseline-reproduction.json',{'exact_original_fit_lock_reproduction':True,
                                              'fit_lock_sha256':sha(campaign/'acquire/fit-lock.json')})
    records = []; baseline_checks = 0
    for condition in CONDITIONS:
        for fold in range(5):
            artifact = baseline['policies'][condition+'/'+str(fold)]
            rows = [q for q in evidence['queries'] if q['group'] in set(artifact['held_out_groups'])]
            replayed = replay(artifact['policy'],rows,condition,PROFILE)
            family = 'local' if CONDITIONS[condition]['local_filter'] else 'base'
            for q,r in zip(rows,replayed):
                if predict(artifact['policy'],q[family+'_states'],PROFILE)!=r['checkpoint']:
                    raise ValueError('Baseline replay differs')
                baseline_checks += 1
            records.extend({**r,'fitter':'cart','condition':condition,'outer_fold':fold,
                            'policy_hash':artifact['policy_hash']} for r in replayed)
    fitted = nested_first_stop(evidence,baseline,PROFILE,output)
    records.extend(fitted.pop('out_of_fold'))
    summaries = {}
    for fitter in DESIGN['fitters']:
        summaries[fitter] = {}
        for condition in CONDITIONS:
            subset = [r for r in records if r['fitter']==fitter and r['condition']==condition]
            if len(subset)!=300 or len({r['query_id'] for r in subset})!=300:
                raise ValueError('Incomplete OOF coverage')
            report = summarize(subset)
            selected = baseline['policies'] if fitter=='cart' else fitted['policies']
            report['fold_abstentions'] = sum(p['risk'] is None for k,p in selected.items() if k.startswith(condition+'/'))
            report['selected_risk_by_fold'] = {str(i):selected[condition+'/'+str(i)]['risk'] for i in range(5)}
            summaries[fitter][condition] = report
    # Preserve exact row-level outcomes and fold-specific policies. No full-data fit.
    save(output/'out-of-fold-replay.json',records)
    save(output/'first-stop-fit-lock.json',fitted)
    result = {'status':'offline_development_comparison_complete','design_lock_sha256':sha(output/'design-lock.json'),
              'summary':summaries,'independent_vectors':100,'query_filter_cases_per_procedure':300,
              'new_conventional_fits':fitted['conventional_fits'],
              'original_cart_fits_reproduced':320,'original_cart_lock_exactly_reproduced':True,
              'candidate_scores_computed':fitted['candidate_scores_computed'],
              'shared_interpreter_cross_checks':baseline_checks+fitted['shared_interpreter_cross_checks'],
              'provider_calls':0,'new_backend_calls':0,'confirmation_queries':0,
              'final_recall_criteria_unchanged':True,'final_latency_gate':'unmeasured',
              'canonical_acceptance_established':False,'deployable_policy_selected':False,
              'ab_comparison':AB,'elapsed_seconds':time.monotonic()-start,
              'limitations':['All inputs are previously examined learning data; this is adaptive development.',
                             'Outer folds do not remove prior study/design adaptation or establish independent confirmation.',
                             'Fixed-stop timing proxies do not measure new policy collection, preparation or interpretation costs.',
                             'Bootstrap conditions on fitted OOF decisions; training uncertainty is not independently resampled.',
                             'Finite beam search is not an optimum or an information-theoretic feature ceiling.',
                             'Fold-specific policies are not a globally fitted deployment artifact. Fresh independent confirmation required.']}
    save(output/'comparison.json',result)
    text = ['Offline fitter comparison: adaptive development only.','Original agent-generation A/B: INCONCLUSIVE.',
            'New policies have no measured latency or final combined acceptance.',
            'fitter | condition | selected folds | stops / 300 | recall delta pp | worst recall lower95 pp | activation proxy saved ms | reuse proxy saved ms | final recall REPLAY pass']
    for fitter,reports in summaries.items():
        for condition,r in reports.items():
            a=r['overall'];bounds=[a,*r['per_filter'].values()]
            text.append(f"{fitter} | {condition} | {5-r['fold_abstentions']} | {a['stopped_cases']} | {100*a['recall_delta']:+.6f} | {100*min(s['recall_delta_ci95'][0] for s in bounds):+.6f} | {a['activation_proxy_ms_saved']:+.6f} | {a['reuse_proxy_ms_saved']:+.6f} | {all(s['final_recall_replay_pass'] for s in bounds)}")
    (output/'report.txt').write_text('\n'.join(text)+'\n')
    verify_inputs(pins,package)
    if {p.name:sha(p) for p in sorted(SOURCE.iterdir()) if p.is_file()}!=source_hashes:
        raise ValueError('Comparison source changed during run')
    save(output/'verification.json',{'status':'verified','design_lock_sha256':sha(output/'design-lock.json'),
         'input_and_source_hashes_unchanged':True,'exact_original_cart_reproduction':True,
         'all_oof_cases':len(records),'shared_interpreter_cross_checks':result['shared_interpreter_cross_checks'],
         'provider_calls':0,'new_backend_calls':0,'confirmation_queries':0,
         'ab_comparison':AB,'final_recall_criteria_unchanged':True,
         'output_files_sha256':{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}})
    print('\n'.join(text),flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    try:
        run(args.output.resolve())
    except BaseException as error:
        if args.output.exists():
            save(args.output/'failure.json',{'type':type(error).__name__,'message':str(error)})
        raise
