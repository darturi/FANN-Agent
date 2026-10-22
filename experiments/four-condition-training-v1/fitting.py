"""Deterministic nested group validation; never fits on an outer test group."""
import math
from types import SimpleNamespace
import numpy as np

from contract import CONDITIONS, CONFIG, EXTRA, GROUPS, RISKS, SEED, digest, folds


def references(node):
    if isinstance(node, dict):
        if 'feature' in node: yield node['feature']
        for v in node.values(): yield from references(v)
    elif isinstance(node, list):
        for v in node: yield from references(v)


def combine(op, items):
    if not items: return {'bool': True}
    if len(items) == 1: return items[0]
    n = len(items) // 2
    return {'op': op, 'args': [combine(op, items[:n]), combine(op, items[n:])]}


def guard(root, checkpoints):
    required = sorted(set(references(root)) | {'checkpoint_index'})
    available = combine('and', [{'op': 'is_available', 'args': [{'feature': n}]} for n in required])
    allowed = combine('or', [{'op': 'eq', 'args': [{'feature': 'checkpoint_index'}, {'int': cp}]} for cp in checkpoints])
    return {'if': {'op': 'and', 'args': [available, allowed]}, 'then': root, 'else': 'continue'}


def predict(raw, states, profile):
    from fannagent.api import PolicyInput, FeatureValue, validate_policy
    from fannagent.api.primitives.interpreter import evaluate_policy
    policy = validate_policy(raw, profile)
    names = sorted(set(references(raw['root'])))
    floats = frozenset(n for n in names if profile.runtime_features[n].kind == 'float')
    for s in states:
        values = s['features']
        inp = PolicyInput(features={n: FeatureValue(available=values.get(n) is not None, value=values.get(n)) for n in names})
        if str(evaluate_policy(policy, inp, float_features=floats)) == 'stop':
            return s['checkpoint_index']
    return None


def fit(rows, condition, risk, profile, base_names, training_groups):
    from cart import _tree
    selected = [q for q in rows if q['group'] in set(training_groups)]
    if len({q['group'] for q in selected}) != len(training_groups): raise ValueError('Fit group coverage differs')
    local = CONDITIONS[condition]['local_filter']
    family = 'local' if local else 'base'
    cps = CONDITIONS[condition]['checkpoints']
    names = sorted(set(base_names) | (set(EXTRA) if local else set()))
    kinds = {n: profile.runtime_features[n].kind for n in names}
    X, y, weights, groups = [], [], [], []
    missing = 0
    for q in selected:
        states = {s['checkpoint_index']: s['features'] for s in q[family + '_states']}
        known = [(cp, q['labels'][family][str(cp)]) for cp in cps if str(cp) in q['labels'][family]]
        for cp, label in known:
            values = states[cp]
            if any(values.get(n) is None for n in names):
                missing += 1
                continue
            loss = max(0.0, q['native_recall'] - label['recall'])
            safe = label['valid'] and label['returned_count'] == 10 and loss == 0
            benefit = max(.005, 1 - label['layer0_distances'] / max(1, q['native_work']))
            penalty = risk * (max(.1, loss) if label['valid'] and label['returned_count'] == 10 else 1)
            X.append([values[n] for n in names]); y.append(float(safe))
            weights.append((benefit if safe else penalty) / (3 * max(1, len(known))))
            groups.append(q['group'])
    if not X: root = 'continue'
    else:
        cfg = SimpleNamespace(depth=CONFIG['fit_depth'], minimum_leaf_groups=CONFIG['minimum_leaf_groups'])
        root = _tree(np.asarray(X, float), np.asarray(y), np.asarray(weights), np.asarray(groups), names, kinds, cfg)
    raw = {'name': 'four-' + condition + '-' + digest([sorted(training_groups), risk])[:12],
        'feature_groups': GROUPS + (['local_filter'] if local else []), 'root': guard(root, cps)}
    from fannagent.api import validate_policy
    artifact = validate_policy(raw, profile)
    return raw, {'training_groups': sorted(training_groups), 'condition': condition, 'risk': risk,
        'policy_hash': artifact.policy_hash, 'fitting_outcomes': len(X), 'missing_feature_outcomes': missing}


def outcome(q, raw, condition, profile):
    family = 'local' if CONDITIONS[condition]['local_filter'] else 'base'
    cp = predict(raw, q[family + '_states'], profile)
    if cp is None:
        label = q['continue_costs'][family]
        recall, valid, count = q['native_recall'], True, 10
    else:
        if str(cp) not in q['labels'][family]: raise ValueError('Unknown actual first stop; acquisition required')
        label = q['labels'][family][str(cp)]
        recall, valid, count = label['recall'], label['valid'], label['returned_count']
    return {'query_id': q['query_id'], 'group': q['group'], 'stratum': q['stratum'],
        'native_recall': q['native_recall'], 'recall_delta': recall - q['native_recall'],
        'valid': bool(valid and count == 10), 'checkpoint': cp,
        'activation_proxy_ms_saved': label['activation_ms_saved'], 'reuse_proxy_ms_saved': label['reuse_ms_saved']}


def assess(rows):
    """Internal margin and actual fixed-stop cost proxies; never final acceptance."""
    reports = {}
    for f in ['overall', *CONFIG['filters']]:
        selected = [r for r in rows if f == 'overall' or r['stratum'] == f]
        grouped = {}
        for r in selected: grouped.setdefault(r['group'], []).append(r)
        values = np.asarray([np.mean([r['recall_delta'] for r in rs]) for _, rs in sorted(grouped.items())])
        if len(values) < 2: raise ValueError('Insufficient inner validation groups')
        rng = np.random.default_rng(SEED)
        boot = values[rng.integers(0, len(values), size=(10000, len(values)))].mean(axis=1)
        lower = float(np.quantile(boot, .025))
        reports[f] = {'groups': len(values), 'recall_delta_lower95': lower,
            'all_valid': all(r['valid'] for r in selected),
            'native_recall': float(np.mean([r['native_recall'] for r in selected]))}
    qualifies = all(s['all_valid'] and s['recall_delta_lower95'] >= -CONFIG['development_recall_margin']
        and (f == 'overall' or s['native_recall'] >= .95) for f, s in reports.items())
    costs = {m: float(np.mean([r[m + '_proxy_ms_saved'] for r in rows])) for m in ('activation', 'reuse')}
    return {'development_recall_pass': qualifies, 'reports': reports, 'cost_proxies': costs,
        'utility': min(costs.values()), 'scope': 'Nested-development selection; fixed-stop cost proxy, not measured fitted-policy latency.'}


def build_lock(evidence, profile, manifest_hash, module_hash):
    rows = evidence['queries']; groups = {q['group'] for q in rows}
    if len(rows) != 300 or len(groups) != 100: raise ValueError('Original learning inventory required')
    outer = folds(groups, 5, 'outer-v1')
    policies = {}; validation = []
    for outer_fold in range(5):
        training = sorted(g for g in groups if outer[g] != outer_fold)
        heldout = sorted(g for g in groups if outer[g] == outer_fold)
        inner = folds(training, 4, 'inner-v1-' + str(outer_fold))
        for condition in CONDITIONS:
            trials = []
            for risk in RISKS:
                results = []; proofs = []
                for inner_fold in range(4):
                    fit_groups = [g for g in training if inner[g] != inner_fold]
                    test_groups = [g for g in training if inner[g] == inner_fold]
                    assert not set(fit_groups) & (set(test_groups) | set(heldout))
                    raw, proof = fit(rows, condition, risk, profile, evidence['base_feature_names'], fit_groups)
                    proofs.append({**proof, 'inner_fold': inner_fold, 'validation_groups': sorted(test_groups)})
                    results.extend(outcome(q, raw, condition, profile) for q in rows if q['group'] in set(test_groups))
                trials.append({'risk': risk, 'assessment': assess(results), 'fit_proofs': proofs})
            eligible = [t for t in trials if t['assessment']['development_recall_pass'] and t['assessment']['utility'] > 0]
            if eligible:
                chosen = sorted(eligible, key=lambda t: (-t['assessment']['utility'], -t['risk']))[0]
                raw, proof = fit(rows, condition, chosen['risk'], profile, evidence['base_feature_names'], training)
                reason = 'Highest positive worst-regime cost proxy among inner-validation recall-margin passes; ties prefer greater risk penalty.'
            else:
                raw = {'name': 'four-' + condition + '-abstain-' + str(outer_fold), 'root': 'continue',
                    'feature_groups': GROUPS + (['local_filter'] if CONDITIONS[condition]['local_filter'] else [])}
                from fannagent.api import validate_policy
                proof = {'training_groups': training, 'condition': condition, 'risk': None,
                    'policy_hash': validate_policy(raw, profile).policy_hash, 'fitting_outcomes': 0}
                reason = 'No inner-validation candidate meets development margin and positive proxy benefit; explicit continue.'
            key = condition + '/' + str(outer_fold)
            policies[key] = {'policy': raw, **proof, 'outer_fold': outer_fold,
                'held_out_groups': heldout, 'selection_reason': reason}
            validation.append({'condition': condition, 'outer_fold': outer_fold, 'trials': trials})
    return {'version': 'four-condition-oof-lock.v1', 'package_manifest_sha256': manifest_hash,
        'module_sha256': module_hash, 'evidence_sha256': digest(evidence), 'folds': outer,
        'policies': policies, 'nested_validation': validation, 'provider_calls': 0,
        'held_out_outcomes_used_for_fitting_or_selection': False,
        'runtime_group_routing': False, 'scope': CONFIG['scope'], 'ab_comparison': CONFIG['ab_comparison'],
        'canonical_acceptance_established': False}
