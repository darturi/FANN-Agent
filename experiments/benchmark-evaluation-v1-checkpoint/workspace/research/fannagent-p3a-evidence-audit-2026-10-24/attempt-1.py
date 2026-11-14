"""Deterministic saved-data coverage audit. No fitting, simulation, DB or network."""
from pathlib import Path
import collections as C
import gc
import hashlib
import json
import math
import resource
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
GRID = [1, 2, 4, 8, 16, 32, 64, 128]
FILTERS = ['unfiltered', 'votes32', 'votes108']
START = time.monotonic()
PINS = {}
READ_BYTES = 0


def guard():
    assert time.monotonic() - START < 3600, 'Local wall ceiling'
    assert READ_BYTES <= 16 * 1024**3, 'Source read ceiling'
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < 4 * 1024**3, 'Memory ceiling'


def sha(path):
    global READ_BYTES
    path = Path(path)
    assert path.is_file() and not path.is_symlink(), path
    guard()
    with path.open('rb') as h:
        value = hashlib.file_digest(h, 'sha256').hexdigest()
    READ_BYTES += path.stat().st_size
    return value


def pin(path, expected=None):
    path = Path(path).resolve()
    value = sha(path)
    if expected is not None:
        assert value == expected, str(path)
    rel = str(path.relative_to(ROOT))
    assert PINS.get(rel, value) == value, rel
    PINS[rel] = value
    return value


def read(path):
    global READ_BYTES
    path = Path(path)
    guard()
    READ_BYTES += path.stat().st_size
    with path.open() as h:
        return json.load(h)


def rows(path):
    global READ_BYTES
    path = Path(path)
    READ_BYTES += path.stat().st_size
    with path.open() as h:
        for line in h:
            if line.strip():
                yield json.loads(line)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def unique(values, key):
    result = {}
    for value in values:
        identity = key(value)
        assert identity not in result, identity
        result[identity] = value
    return result


def verify_manifest(package, expected):
    pin(package / 'manifest.json', expected)
    manifest = read(package / 'manifest.json')
    skipped = []
    for name, value in manifest['files'].items():
        # Preserve protected query values unopened; their historical verification
        # remains in the pinned prior receipt, not a new audit claim.
        if name == 'inputs/evaluation.jsonl':
            skipped.append(name)
            continue
        pin(package / name, value)
    return {'manifest_sha256': expected, 'files_verified': len(manifest['files']) - len(skipped), 'protected_query_files_not_opened': skipped}


def validate_pair(r, ref):
    assert (r['native_ids'], r['native_distances'], r['native_recall']) == (ref['native_ids'], ref['native_distances'], ref['native_recall'])
    assert r['truth_k'] == 10
    for mode in ['native', 'policy']:
        identifiers = r[mode + '_ids']
        distances = r[mode + '_distances']
        assert len(identifiers) == len(distances) <= 10 and len(set(identifiers)) == len(identifiers)
        assert all(math.isfinite(v) for v in distances)
        strict = len(set(identifiers) & set(r['truth_strict']))
        ties = min(10 - len(r['truth_strict']), len(set(identifiers) & set(r['truth_ties'])))
        assert abs((strict + ties) / 10 - r[mode + '_recall']) <= 1e-12
        assert all(math.isfinite(r[mode + tail]) and r[mode + tail] > 0 for tail in ['_ms', '_outer_ms'])
    assert r['valid'] == (len(r['policy_ids']) == 10)
    assert r['returned_count'] == len(r['policy_ids'])
    assert abs(r['recall_delta'] - (r['policy_recall'] - r['native_recall'])) <= 1e-12


def expected_progress(receipt, cp, threshold):
    selected = [r for r in receipt['rows'] if r[0] <= cp]
    window = max((w for w, n in zip(GRID, receipt['fetches']) if w <= cp and n), default=0)
    passed = lambda r: threshold == 0 or (not r[3] and r[2] >= threshold)
    valid = [r for r in selected if passed(r)]
    recent = [r for r in selected if r[0] == window]
    recent_valid = [r for r in recent if passed(r)]
    previous = [r for r in valid if r[0] != window]
    minimum = min((r[4] for r in valid), default=0.)
    return dict(progress_window_checkpoint=window, progress_probe_examined=len(selected), progress_probe_passed=len(valid),
                progress_probe_pass_ratio=len(valid) / len(selected) if selected else 0.,
                progress_recent_examined=len(recent), progress_recent_passed=len(recent_valid),
                progress_recent_pass_ratio=len(recent_valid) / len(recent) if recent else 0.,
                progress_has_valid=bool(valid), progress_valid_distance_min_or_zero=minimum,
                progress_valid_distance_mean_or_zero=sum(r[4] for r in valid) / len(valid) if valid else 0.,
                progress_valid_min_improvement_or_zero=max(0., min(r[4] for r in previous) - minimum) if previous and valid else 0.)


def project(states, names):
    return [{**s, 'features': {n: s['features'][n] for n in names}} for s in states]


def add_feature_features(target, q, states, names, definitions):
    for s in states:
        for name in names:
            x = s['features'].get(name)
            item = target.setdefault(name, dict(kind=definitions[name]['kind'], all_states=0, unavailable_states=0, grid_states=0, unavailable_grid_states=0, invalid_type_or_nonfinite=0))
            item['all_states'] += 1
            item['grid_states'] += int(s['checkpoint_index'] in GRID)
            if x is None:
                item['unavailable_states'] += 1
                item['unavailable_grid_states'] += int(s['checkpoint_index'] in GRID)
                continue
            kind = item['kind']
            good = type(x) is bool if kind == 'bool' else (type(x) is int and abs(x) <= 2**53) if kind == 'int' else type(x) in (int, float) and math.isfinite(x)
            item['invalid_type_or_nonfinite'] += int(not good)
            assert good, (q['query_id'], name)


def coverage(qs, names_by_family, definitions, summary, features, profile_map):
    for q in qs:
        for family, names in names_by_family.items():
            profile = profile_map[family]
            states = q[family + '_states']
            assert [s['checkpoint_index'] for s in states] == list(range(1, len(states) + 1))
            add_feature_features(features.setdefault(profile, {}), q, states, names, definitions)
            for cp in GRID:
                key = profile + '/' + q['stratum'] + '/' + str(cp)
                item = summary.setdefault(key, C.Counter())
                item['cases'] += 1
                reached = cp <= len(states)
                item['reached'] += reached
                item['unreachable_search_finished'] += not reached
                label = q['labels'][family].get(str(cp))
                assert (label is not None) == reached
                if not reached:
                    continue
                item['actual_stop_labels'] += 1
                item['all_features_available'] += all(states[cp - 1]['features'].get(n) is not None for n in names)
                item['valid_top10'] += label['valid'] and label['returned_count'] == 10
                item['recall_not_below_native'] += label['recall'] >= q['native_recall']
                item['recall_below_native'] += label['recall'] < q['native_recall']
                item['positive_activation_proxy'] += label['activation_ms_saved'] > 0
                item['positive_reuse_proxy'] += label['reuse_ms_saved'] > 0
                item['both_fixed_stop_proxies_positive'] += min(label['activation_ms_saved'], label['reuse_ms_saved']) > 0


def acquisition(folder, items, names, definitions, label, summary, features):
    lock = read(folder / 'LOCK.json')
    locked = lock.get('files_sha256', lock.get('raw_files_sha256'))
    for file, value in locked.items():
        pin(folder / file, value)
    data = read(folder / 'evidence.json')
    refs = unique(rows(folder / 'references.jsonl'), lambda r: r['query_id'])
    proofs = unique(rows(folder / 'proofs.jsonl'), lambda r: (r['query_id'], r['family'], r['checkpoint']))
    samples = unique(rows(folder / 'pairs.jsonl'), lambda r: (r['query_id'], r['family'], r['checkpoint'], r['regime']))
    qs = data['queries']
    assert set(refs) == {q['query_id'] for q in qs} == set(items)
    profiles = {'base': 'static23', 'local': 'progress34'} if label.startswith('feature') else {'base': 'light19_old_binary', 'local': 'static23_old_binary'}
    coverage(qs, names, definitions, summary, features, profiles)
    compact = {}
    expected_proofs = set()
    expected_samples = set()
    for q in qs:
        identifier = q['query_id']
        ref = refs[identifier]
        assert q['group'] == items[identifier]['group'] == identifier.rsplit('-', 1)[0]
        assert q['stratum'] == identifier.rsplit('-', 1)[1] and q['stratum'] in FILTERS
        assert q['native_recall'] == ref['native_recall']
        assert q['base_states'] == ref['base_states'] and q['local_states'] == ref['local_states']
        assert project(q['local_states'], names['base']) == q['base_states']
        actual = {}
        for family in ['base', 'local']:
            states = q[family + '_states']
            expected_cps = [cp for cp in GRID if cp <= len(states)]
            assert set(q['labels'][family]) == {str(cp) for cp in expected_cps}
            for cp in [None, *expected_cps]:
                a, w = [samples[(identifier, family, cp, regime)] for regime in ['activation-cold', 'reused-warm']]
                for r in [a, w]:
                    validate_pair(r, ref)
                    expected_samples.add((identifier, family, cp, r['regime']))
                assert a['policy_hash'] == w['policy_hash']
                if cp is None:
                    ids, distances = ref['native_ids'], ref['native_distances']
                    known = q['continue_costs'][family]
                else:
                    proof = proofs[(identifier, family, cp)]
                    expected_proofs.add((identifier, family, cp))
                    if 'observed_prefix_sha256' in proof:
                        assert proof['observed_prefix_sha256'] == digest(states[:cp])
                    else:
                        assert proof['observed_prefix'] == states[:cp]
                    assert proof['policy_hash'] == a['policy_hash']
                    ids, distances = proof['policy_ids'], proof['policy_distances']
                    known = q['labels'][family][str(cp)]
                    assert all(r['stop_reason'] == 'policy_stop' and r['checkpoint_count'] == cp for r in [a, w])
                    actual[(family, cp)] = {'ids': ids, 'distances': distances, 'recall': known['recall'], 'valid': known['valid']}
                assert all((r['policy_ids'], r['policy_distances']) == (ids, distances) for r in [a, w])
                assert known['recall'] == a['policy_recall'] == w['policy_recall']
                assert known['valid'] == a['valid'] and known['returned_count'] == a['returned_count']
                assert known['layer0_distances'] == a['work']['layer0_distance_evaluations']
                assert abs(known['activation_ms_saved'] - (a['native_ms'] - a['policy_ms'])) <= 1e-12
                assert abs(known['reuse_ms_saved'] - (w['native_ms'] - w['policy_ms'])) <= 1e-12
        compact[identifier] = {'group': q['group'], 'stratum': q['stratum'], 'role': q.get('role', 'original_learning'),
            'query_digest': digest(q), 'lengths': {f: len(q[f + '_states']) for f in ['base', 'local']},
            'light19_states_digest': digest(project(q['base_states'], BASE_NAMES)),
            'static23_states_digest': digest(project(q['local_states'], STATIC_NAMES)),
            'native_ids': ref['native_ids'], 'native_distances': ref['native_distances'], 'native_recall': q['native_recall'],
            'actual': actual}
    assert set(proofs) == expected_proofs and set(samples) == expected_samples
    probe_checks = 0
    if label.startswith('feature'):
        probes = unique(rows(folder / 'probe-verification.jsonl'), lambda r: r['query_id'])
        assert set(probes) == set(refs)
        for q in qs:
            p = probes[q['query_id']]
            assert p['actual_metadata_and_distance_verified'] and p['static']['actual_metadata_verified']
            assert p['static']['causal_prefix_feature_checks'] == len(q['base_states'])
            receipt = p['progress']
            assert receipt['enabled'] and len(receipt['fetches']) == 8
            assert all(0 <= n <= 8 for n in receipt['fetches']) and sum(receipt['fetches']) <= 64
            assert len(receipt['rows']) <= sum(receipt['fetches'])
            for window, row_id, vote, null, distance in receipt['rows']:
                v, d = receipt['actual_metadata_sql_rows'][str(row_id)]
                assert window in GRID and (v is None) == null and (null or v == vote) and abs(d - distance) <= 1e-6
            threshold = 0 if items[q['query_id']]['query'].get('filter') is None else items[q['query_id']]['query']['filter']['value']
            static_receipt = p['static']['receipt']
            static_rows = static_receipt['rows']
            assert static_receipt['enabled'] and static_receipt['examined'] <= 64
            # Progress observations use only rows/window data already observed at cp.
            for state in q['local_states']:
                for name, expected in expected_progress(receipt, state['checkpoint_index'], threshold).items():
                    observed = state['features'][name]
                    assert (type(observed) is bool and observed == expected) if type(expected) is bool else math.isclose(observed, expected, rel_tol=1e-12, abs_tol=1e-12)
                probe_checks += 1
    qualification = read(folder / 'qualified-features.json')
    assert all(r['status'] == 'passed' for r in qualification)
    result = {'cases': len(qs), 'vectors': len({q['group'] for q in qs}), 'actual_stop_proofs': len(proofs), 'retained_fixed_stop_and_continue_pairs': len(samples),
        'full_trajectory_states_per_family': sum(len(q['base_states']) for q in qs), 'causal_progress_states_reconstructed': probe_checks,
        'qualification': qualification, 'runtime': read(folder / 'runtime-identity.json'), 'database': read(folder / 'database-identity.json')}
    del data, refs, proofs, samples, qs
    gc.collect()
    return compact, result


def main():
    global BASE_NAMES, STATIC_NAMES
    assert not (HERE / 'audit.json').exists(), 'Preserve previous audit; choose a separately reviewed destination'
    contract_path = HERE / 'contract.json'
    pin(contract_path, 'e5570d5023bab53b37046d206ceec86c04aadfe298d8c465c863fff7bc5a31cf')
    contract = read(contract_path)
    receipts = {}
    for rel, value in contract['source_receipt_sha256'].items():
        pin(ROOT / rel, value)
        receipts[Path(rel).name.removesuffix('-postrun.json')] = read(ROOT / rel)
    fa = ROOT / 'trials/torch-reviews-results/feature-data-ablation-v1/torch-feature-data-ablation-v1'
    four = ROOT / 'trials/torch-reviews-results/four-condition-training-v1/torch-four-condition-training-v1'
    p2c = ROOT / 'trials/torch-reviews-activation-timing-calibration-v1/torch-activation-timing-calibration-v1'
    package_checks = {'feature_data': verify_manifest(fa, receipts['feature-data-ablation-v1']['package_manifest_sha256']),
        'four_condition': verify_manifest(four, receipts['four-condition-training-v1']['sealed_local_package_manifest_sha256']),
        'p2c': verify_manifest(p2c, receipts['activation-timing-calibration-v1']['package_manifest_sha256'])}
    # P2c manifest also pins the original selective development package.
    frozen = p2c / 'frozen'
    package_checks['selective_pilot'] = verify_manifest(frozen, receipts['selective-agent-v1-pilot']['package_manifest_sha256'])
    cfg = read(fa / 'experiment.json')
    BASE_NAMES, STATIC_NAMES = cfg['base_feature_names'], cfg['static_feature_names']
    run = ROOT / 'trials/torch-reviews-selective-agent-v1/runs/20261022T192817Z-66ed81d6'
    pin(run / 'evidence/context.json')
    context = read(run / 'evidence/context.json')
    definitions = context['features']
    assert context['profiles']['light19']['features'] == BASE_NAMES and context['profiles']['static23']['features'] == STATIC_NAMES
    progress_names = context['profiles']['progress34']['features']
    assert len(BASE_NAMES) == 19 and len(STATIC_NAMES) == 23 and len(progress_names) == 34
    assert all(d['stage'] == 'runtime' and d['provenance'] == 'server_observed' for d in definitions.values())
    rawfa = Path(receipts['feature-data-ablation-v1']['root'])
    rawfour = Path(receipts['four-condition-training-v1']['campaign'])
    for rec, verification, raw in [
        (receipts['feature-data-ablation-v1'], rawfa / 'analysis/verification.json', rawfa),
        (receipts['four-condition-training-v1'], Path(receipts['four-condition-training-v1']['analysis_directory']) / 'verification.json', rawfour)]:
        pin(verification, rec['analysis_files_sha256']['verification.json'])
        for name, value in read(verification)['raw_files_sha256'].items():
            pin(raw / name, value)
    print('Package and prior raw hashes verified; auditing saved labels and causal prefixes.', flush=True)
    feature_summary, feature_features, feature_rows, acquisitions = {}, {}, {}, {}
    all_items = {}
    for part in [0, 1]:
        inputs = fa / f'inputs/acquire-{part}.jsonl'
        items = unique(rows(inputs), lambda r: r['query']['id'])
        all_items.update(items)
        compact, info = acquisition(rawfa / f'acquire/part-{part}', items,
            {'base': STATIC_NAMES, 'local': progress_names}, definitions, f'feature-{part}', feature_summary, feature_features)
        assert not set(compact) & set(feature_rows)
        feature_rows.update(compact)
        acquisitions[f'feature-{part}'] = info
        print('Acquisition partition verified:', part, flush=True)
    inputs4 = unique(rows(four / 'inputs/queries.jsonl'), lambda r: r['query']['id'])
    old_summary, old_features = {}, {}
    old_rows, acquisitions['four_condition'] = acquisition(rawfour / 'acquire', inputs4,
        {'base': BASE_NAMES, 'local': STATIC_NAMES}, definitions, 'four', old_summary, old_features)
    assert set(old_rows) <= set(feature_rows)
    overlap = C.Counter()
    for identifier, old in old_rows.items():
        new = feature_rows[identifier]
        overlap['cases'] += 1
        overlap['native_outputs_equal'] += (old['native_ids'], old['native_distances'], old['native_recall']) == (new['native_ids'], new['native_distances'], new['native_recall'])
        overlap['light19_projected_trajectories_equal'] += old['light19_states_digest'] == new['light19_states_digest']
        overlap['static23_trajectories_equal'] += old['static23_states_digest'] == new['static23_states_digest']
        for (family, cp), outcome in old['actual'].items():
            overlap['old_actual_stops'] += 1
            overlap['old_stop_outputs_match_new_static23'] += outcome == new['actual'][('base', cp)]
    corpus_path = run / 'evidence/corpus.json'
    expected_corpus = read(frozen / 'manifest.json')['files']['inputs/development-evidence.json']
    pin(corpus_path, expected_corpus)
    corpus = read(corpus_path)
    assert len(corpus['queries']) == 600 and len(corpus['folds']) == 200
    assert set(corpus['folds']) == {q['group'] for q in feature_rows.values()}
    for q in corpus['queries']:
        assert digest(q) == feature_rows[q['query_id']]['query_digest']
    fold_counts = C.Counter(corpus['folds'].values())
    del corpus
    gc.collect()
    vector_groups = {}
    for identifier, item in all_items.items():
        q = item['query']
        assert item['role'] in {'original_learning', 'additional_learning', 'calibration'}
        assert len(q['vector']) == 768 and q['k'] == 10
        vector = hashlib.sha256(struct.pack('<768f', *q['vector'])).hexdigest()
        group = item['group']
        if group in vector_groups:
            assert vector_groups[group]['vector_sha256'] == vector
        else:
            vector_groups[group] = {'vector_sha256': vector, 'role': item['role'], 'filters': []}
        assert vector_groups[group]['role'] == item['role']
        vector_groups[group]['filters'].append(identifier.rsplit('-', 1)[1])
    assert len(vector_groups) == len({r['vector_sha256'] for r in vector_groups.values()}) == 200
    assert all(sorted(r['filters']) == sorted(FILTERS) for r in vector_groups.values())
    assert len({r['group'] for r in old_rows.values()}) == 100
    for identifier, item in inputs4.items():
        assert item['query'] == all_items[identifier]['query']
    split = read(fa / 'inputs/ablation-split.json')
    exposed_hashes = {r['vector_sha256'] for r in vector_groups.values()}
    excluded_counts = {}
    for role in ['evaluation', 'reserved']:
        hashes = {split['vector_hash_by_catalog_group'][str(g)] for g in split['selected_catalog_groups'][role]}
        assert len(hashes) == len(split['selected_catalog_groups'][role])
        assert not hashes & exposed_hashes
        excluded_counts[role] = len(hashes)
    print('Feature data, original subset, corpus and group/exposure identities verified.', flush=True)
    # Repeated execution campaigns provide light19 traces and selected actual stops,
    # never a complete all-checkpoint light19 outcome/cost matrix.
    light_stops = {}
    execution_sources = {}
    pilot_raw = run / 'returned/pilot/reviews-selective-agent-v1-pilot-20261022T202240Z.j9ackcxc'
    families = [('pilot', pilot_raw, receipts['selective-agent-v1-pilot']['raw_files_verified'])]
    for key in ['execution-cost-attribution-v1', 'prepared-policy-lifecycle-v1', 'admission-profile-identity-v1', 'activation-timing-calibration-v1']:
        r = receipts[key]
        raw = Path(r.get('raw_campaign', r.get('campaign_raw_directory', '')))
        hashes = r.get('raw_files_sha256', r.get('raw_files_verified'))
        if type(hashes) is not dict:
            performance = read(Path(r['local_analysis']) / 'performance.json')
            hashes = performance.get('raw_files_sha256', {})
        families.append((key, raw, hashes))
    for label, raw, hashes in families:
        source_count = C.Counter()
        for rel, expected in hashes.items():
            if Path(rel).name not in {'references.jsonl', 'proofs.jsonl', 'qualified-features.json', 'runtime-identity.json', 'database-identity.json'}:
                continue
            pin(raw / rel, expected)
            if Path(rel).name == 'references.jsonl':
                for q in rows(raw / rel):
                    assert q['query_id'] in feature_rows
                    source_count['reference_rows'] += 1
                    if 'states' in q:
                        assert digest(q['states']) == feature_rows[q['query_id']]['light19_states_digest']
                        source_count['light19_full_trajectories_matching_projection'] += 1
            if Path(rel).name == 'proofs.jsonl':
                for proof in rows(raw / rel):
                    source_count['proof_rows'] += 1
                    cp = proof.get('checkpoint', proof.get('predicted_checkpoint'))
                    if cp is None:
                        continue
                    identifier = proof['query_id']
                    assert identifier in feature_rows and cp in GRID
                    actual = feature_rows[identifier]['actual'][('base', cp)]
                    assert (proof['policy_ids'], proof['policy_distances']) == (actual['ids'], actual['distances'])
                    light_stops[(identifier, cp)] = True
                    source_count['stop_proofs_matching_static23_output'] += 1
        execution_sources[label] = dict(source_count)
    # Keep only aggregate/digested inventories: no vectors or protected identifiers.
    result = {
        'version': 'p3a-existing-evidence-audit.v1', 'status': 'verified_restricted_modeling_supported',
        'contract_sha256': PINS[str(contract_path.relative_to(ROOT))], 'audit_script_sha256': sha(Path(__file__)),
        'package_checks': package_checks, 'acquisitions': acquisitions, 'feature_definitions': definitions,
        'coverage_by_profile_filter_checkpoint': feature_summary, 'feature_availability': feature_features,
        'old_binary_coverage': old_summary, 'old_binary_feature_availability': old_features,
        'overlap_old100_with_new200': dict(overlap), 'exposure': {'independent_vectors': 200, 'cases': 600,
            'role_vectors': dict(C.Counter(r['role'] for r in vector_groups.values())), 'fold_vectors': dict(fold_counts),
            'group_inventory_sha256': digest(sorted(vector_groups)), 'float32_vector_inventory_sha256': digest(sorted(exposed_hashes)),
            'group_vector_binding_sha256': digest(sorted((k, r['vector_sha256']) for k, r in vector_groups.items())),
            'reserved_and_unexecuted_confirmation_hash_sets_disjoint': True, 'excluded_counts': excluded_counts,
            'old100_are_subset_not_new_independent_data': True, 'all_filters_share_vector_and_fold': True,
            'all_200_previously_exposed': True, 'protected_query_values_opened': False},
        'execution_sources': execution_sources,
        'current_binary_light19_unique_actual_stop_cells': len(light_stops),
        'current_binary_light19_unique_actual_stop_cells_by_filter': dict(C.Counter(feature_rows[q]['stratum'] for q, cp in light_stops)),
        'current_binary_light19_unique_actual_stop_cells_by_checkpoint': dict(C.Counter(cp for q, cp in light_stops)),
        'current_binary_light19_complete_grid_required_cells': sum(len([cp for cp in GRID if cp <= q['lengths']['base']]) for q in feature_rows.values()),
        'source_input_hashes': PINS,
        'read_bytes_before_preservation_check': READ_BYTES,
        'new_model_fits': 0, 'new_policy_search_or_simulation': 0, 'database_calls': 0, 'provider_calls': 0, 'torch_allocations': 0,
        'decision': {'can_prepare_restricted_modeling_contract': True,
            'supported_scope': 'Static23 versus progress34, original execution, current e7dc binary and fixed index, 200 exposed vectors, eight ordinal stop checkpoints plus continue. Outcomes complete wherever reached; use grouped adaptive-development evaluation only.',
            'unsupported_without_new_measurement': ['Arbitrary checkpoint stops outside the eight-point grid', 'Complete light19 quality/cost matrix on the current binary across 200 vectors', 'End-to-end latency of any newly fitted policy or new model/feature/observation path', 'Independent confirmation or cross-workload claims'],
            'immediate_targeted_torch_acquisition_required_for_supported_scope': False,
            'next': 'Freeze a bounded grouped flexible-versus-shallow development modeling contract on supported existing outcomes; do not fit during P3a. Preserve fixed-stop costs as proxies. Require targeted native qualification/timing only for a justified new policy or unsupported information/action/cost scope.'}}
    for rel, expected in list(PINS.items()):
        assert sha(ROOT / rel) == expected, 'Source changed during audit: ' + rel
    result['source_preservation'] = {'checked_files': len(PINS), 'before_after_sha256_identical': True}
    result['elapsed_seconds'] = time.monotonic() - START
    result['total_source_bytes_read'] = READ_BYTES
    result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    guard()
    with (HERE / 'audit.json').open('x') as h:
        json.dump(result, h, indent=2, sort_keys=True, allow_nan=False)
        h.write('\n')
    print(json.dumps({'status': result['status'], 'files_preserved': len(PINS), 'light19_current_unique_stops': len(light_stops), 'elapsed_seconds': result['elapsed_seconds']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
