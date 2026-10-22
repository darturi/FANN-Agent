"""Fixed four-condition training protocol; no model or database dependencies."""
import hashlib
import json
from pathlib import Path

NAME = 'torch-four-condition-training-v1'
AB = {'status': 'inconclusive', 'complete_pairs': 0, 'selection_effect_established': False}
SEED = 20261019
FILTERS = ['unfiltered', 'votes32', 'votes108']
LATE = [32, 64, 128]
EARLY = [1, 2, 4, 8, 16, 32, 64, 128]
CONDITIONS = {
    'A': {'local_filter': False, 'checkpoints': LATE},
    'B': {'local_filter': False, 'checkpoints': EARLY},
    'C': {'local_filter': True, 'checkpoints': LATE},
    'D': {'local_filter': True, 'checkpoints': EARLY},
}
EXTRA = ['query_predicate_threshold', 'local_probe_examined', 'local_probe_passed', 'local_probe_pass_ratio']
GROUPS = ['basic', 'work', 'queue', 'distances']
RISKS = [20.0, 80.0, 320.0, 1280.0]
CONFIG = {
    'name': NAME, 'stage': 'training', 'seed': SEED, 'filters': FILTERS,
    'row_count': 247286, 'dimension': 768, 'k': 10, 'ef_search': 640,
    'recall_tolerance': .005, 'minimum_native_recall': .95, 'bootstrap_samples': 10000,
    'blocks': 3, 'warm_passes': 3, 'outer_folds': 5, 'inner_folds': 4,
    'fit_depth': 3, 'minimum_leaf_groups': 8, 'risk_weights': RISKS,
    'development_recall_margin': .0025,
    'development_margin_note': 'Internal selection reserve only. Final recall tolerance remains .005.',
    'local_probe_limit': 64, 'conditions': CONDITIONS,
    'provider_calls_allowed': 0, 'new_fits': 'deterministic conventional fits only',
    'confirmation_queries_allowed': 0, 'calibration_and_final_test_queries_allowed': 0,
    'ab_comparison': AB, 'canonical_acceptance_established': False,
    'maximum_measurement_seconds': 6600, 'maximum_backend_calls': 70000,
    'resources': {'cpus': 4, 'memory_gib': 32, 'wall_hours': 2},
    'source_prepared': '/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286',
    'image_sha256': '7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a',
    'original_module_sha256': '77d38cad937d7c6d561d7f44ce447629ba913495ac732876fb50c9769d99680b',
    'frozen_query_method_sha256': 'c0c7a5b45bc272765110450c72f70eafb0f2a7ab3034c036a18bff0fc049279b',
    'fresh_confirmation_required': True,
    'scope': 'Nested group-validation of four fitting procedures, not qualification of a single deployable policy. Fold assignment is evaluator-only; no query/group identity is a policy input.',
}


def encoded(v):
    return (json.dumps(v, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def save(path, value, raw=False):
    path = Path(path)
    content = value if raw else encoded(value)
    if isinstance(content, str): content = content.encode()
    if path.is_symlink(): raise ValueError('Refuse symlink: ' + str(path))
    if path.exists():
        if path.read_bytes() != content: raise ValueError('Preserve differing output: ' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f: f.write(content)


def lines(path):
    with Path(path).open() as f:
        return [json.loads(s) for s in f]


def folds(groups, count, salt):
    ordered = sorted(set(groups), key=lambda g: digest([SEED, salt, g]))
    return {g: i % count for i, g in enumerate(ordered)}


def accounting():
    # Acquisition: exact/native/base+local references, 8 stop points x 2 profiles,
    # each with activation, discarded warmup and one reuse pair; getter branches.
    acquisition = 300 * (4 + 12 + 8 * 2 * 7) + 3 * (1 + 4 * 19) + 3 * (1 + 4 * 23)
    # Four OOF treatments, four matched controls, two continue controls, two fixed
    # controls and oracle. Every query has one activation and three reused pairs.
    arms = 13
    measurement = 300 * (arms * (2 + 3) * 2 + arms + 4) + 3 * (1 + 4 * 19) + 3 * (1 + 4 * 23)
    assert acquisition < 70000 and measurement < 70000
    return {'acquisition_maximum_backend_calls': acquisition,
        'measurement_maximum_backend_calls_per_block': measurement,
        'measurement_arms': arms, 'retained_pairs_per_block': arms * 300 * 4,
        'retained_pairs_total': arms * 300 * 4 * 3,
        'discarded_warmup_pairs_per_block': arms * 300,
        'acquisition_maximum_retained_pairs': 300 * 9 * 2 * 2,
        'acquisition_maximum_warmup_pairs': 300 * 9 * 2,
        'allocations': 5, 'allocation_layout': ['build', 'acquire-and-fit', 'measure-0', 'measure-1', 'measure-2']}
