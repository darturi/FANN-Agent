"""Pinned read-only inputs and fixed offline comparison design."""
import hashlib
import json
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[2]
AB = {'status': 'inconclusive', 'complete_pairs': 0, 'selection_effect_established': False}
DESIGN = {
    'version': 'offline-first-stop-fitter.v1',
    'conditions': ['A', 'B', 'C', 'D'],
    'fitters': ['cart', 'first_stop_beam'],
    'risk_weights': [20., 80., 320., 1280.],
    'outer_folds': 5, 'inner_folds': 4, 'seed': 20261019,
    'tree_depth': 3, 'minimum_leaf_groups': 8,
    'beam_width': 4, 'growth_rounds': 7,
    'threshold_quantiles': [.05 + .9*i/12 for i in range(13)],
    'threshold_scope': 'All eligible measured states in fitting groups only; fixed pool per fit.',
    'search': 'Start continue and stop roots; expand one leaf into either orientation of a stop/continue split; retain best four distinct training decision masks each round; carry incumbents; deterministic complexity/lexical ties.',
    'training_objective': 'min(mean activation proxy ms saved, mean reuse proxy ms saved) minus risk_weight * max(nonnegative mean recall deficit across overall and each filter); incomplete/invalid first stops infeasible.',
    'development_recall_margin': .0025,
    'final_recall_tolerance': .005, 'minimum_native_recall': .95,
    'bootstrap_samples': 10000,
    'selection': 'Unchanged inner-development reserve and positive worst-regime cost proxy; greatest utility, larger risk weight on ties. No eligible candidate means explicit continue.',
    'minimum_selection_change_note': 'Final gates, development reserve, baseline, features, eligible checkpoints, folds and selection rule remain fixed. New fitter changes tree search/objective only; its threshold pool is global within each fitting subset.',
    'timing_status': 'New policy latency UNMEASURED. Fixed-stop acquisition timings are proxies only; no final latency or combined acceptance.',
    'provider_calls_allowed': 0, 'new_backend_calls_allowed': 0,
    'confirmation_queries_allowed': 0,
    'ab_comparison': AB, 'canonical_acceptance_established': False,
    'scope': 'Adaptive offline development on previously examined 100 learning vectors; not independent confirmation or a selected global deployment policy.',
}


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def save(path, value):
    path = Path(path)
    text = json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n'
    if path.exists():
        if path.read_text() != text:
            raise ValueError('Preserve differing output: '+str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x') as stream:
            stream.write(text)


def initialize():
    pins = read(SOURCE/'input-pins.json')
    package = ROOT/pins['package']
    if sha(package/'manifest.json') != pins['package_manifest_sha256']:
        raise ValueError('Sealed local package manifest changed')
    sys.path[:0] = [str(package), str(package/'vendor'), str(ROOT/'trials/torch-reviews-first/sources')]
    from no_models import enforce
    enforce()
    # Computation only: neither child processes nor network connections allowed.
    def audit(event, args):
        if event in ('socket.connect', 'socket.connect_ex', 'subprocess.Popen', 'os.system'):
            raise RuntimeError('Offline comparison forbids '+event)
    sys.addaudithook(audit)
    return pins, package


def verify_inputs(pins, package):
    campaign = ROOT/pins['campaign']
    if sha(campaign.with_name(campaign.name+'.tar.gz')) != pins['archive_sha256']:
        raise ValueError('Source archive changed')
    for name, expected in pins['raw_files_sha256'].items():
        if sha(campaign/name) != expected:
            raise ValueError('Source measurement changed: '+name)
    for name, expected in read(package/'manifest.json')['files'].items():
        if sha(package/name) != expected:
            raise ValueError('Sealed local source changed: '+name)
    for name, expected in pins['core_files_sha256'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Core source changed: '+name)
    from control import verify
    verify(package)
    return campaign
