"""Build a self-contained Torch upload from pinned local sources, without models."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile

from contract import CONFIG, NAME, accounting, digest, encoded, lines, read, save, sha
from native_patch import patch_adapter, patch_engine

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
OLD = WORKSPACE / 'trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix'
OUTPUT = WORKSPACE / 'trials/torch-reviews-results/four-condition-training-v1'
TRAINING = WORKSPACE / 'trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-training-20261021T044854Z.l3c__b58'
CONFIRMATION = WORKSPACE / 'trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-confirmation-20261021T160807Z.n5yrz2mk'


def query_method_hash(path):
    text=Path(path).read_text();tree=ast.parse(text)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeBackend')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_execute_probe')
    return hashlib.sha256(''.join(text.splitlines(keepends=True)[method.lineno-1:method.end_lineno]).encode()).hexdigest()


def check_sources():
    sys.path.insert(0, str(OLD))
    from build import check_sources as previous_check
    source_hash, lineage, charges = previous_check()
    pins = read(HERE / 'input-pins.json')
    for name, expected in pins['files'].items():
        p = WORKSPACE / name
        if p.is_symlink() or sha(p) != expected: raise ValueError('Pinned study input changed: ' + name)
    if query_method_hash(WORKSPACE/'trials/torch-reviews-first/sources/fannagent_pgvector/backend.py')!=CONFIG['frozen_query_method_sha256']:
        raise ValueError('Original ANN timing-method provenance differs')
    return {'previous_source_manifest_sha256': source_hash, 'ledger_charge_records': len(charges),
        'ledger_charges_sha256': digest(charges), 'scientific_state_sha256': lineage['ledger_scientific_state_sha256']}


def build(output=OUTPUT):
    before = check_sources()
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=True)
    target = output / NAME
    if target.exists(): raise ValueError('Preserve existing package; use a fresh output directory')
    target.mkdir()
    original = WORKSPACE / 'trials/torch-reviews-first'
    reference = OLD / 'reference'
    # No original mixed-split file or confirmation result enters the upload.
    query_source = TRAINING / 'packages/cohort-0/inputs/queries.jsonl'
    qs = lines(query_source)
    if len(qs) != 300 or any(q['split'] != 'learning' for q in qs): raise ValueError('Training-only inventory required')
    if len({q['group'] for q in qs}) != 100: raise ValueError('100 independent learning groups required')
    for path in HERE.glob('*.py'):
        if path.name not in {'package.py', 'test_study.py'}: save(target / path.name, path.read_bytes(), raw=True)
    for name in ('design.py', 'runtime_base.py', 'reference_backend.py', 'preservation.py', 'prior_protected.py', 'integrity.py', 'verify_patch.py', 'protected-campaigns.json'):
        save(target / name, (reference / name).read_bytes(), raw=True)
    save(target / 'legacy_protected.py', (reference / 'protected.py').read_bytes(), raw=True)
    save(target / 'database.py', (WORKSPACE / 'trials/torch-reviews-dispatch-overhead-v1/database.py').read_bytes(), raw=True)
    save(target / 'study_stats.py', (reference / 'study_stats.py').read_bytes(), raw=True)
    for name in ('original-learning-receipt.json', 'split-provenance.json', 'budget-receipt.json', 'training-640-light.jsonl'):
        save(target / 'inputs' / name, (reference / 'inputs' / name).read_bytes(), raw=True)
    save(target / 'inputs/queries.jsonl', query_source.read_bytes(), raw=True)
    source_rows = lines(reference / 'inputs/training-640-light.jsonl')
    names = read(reference / 'inputs/original-learning-receipt.json')['qualified_features']['640/light']
    assert len(names) == 19 and len(source_rows) == 300
    native_results = {}
    for row in lines(TRAINING / 'cohorts/cohort-0/blocks/block-0/pairs.jsonl'):
        key = row['query_id']
        value = {'ids': row['native_ids'], 'distances': row['native_distances'], 'recall': row['native_recall']}
        if key in native_results: assert native_results[key] == value
        else: native_results[key] = value
    assert set(native_results) == {q['query']['id'] for q in qs}
    save(target / 'inputs/native-results.json', native_results)
    save(target / 'source-index.json', read(reference / 'source-index.json'))
    cfg = {**CONFIG, 'base_feature_names': names, 'complete_call_accounting': accounting(),
        'source_learning_campaign': 'reviews-policy-learning-20261019T145148Z.EJ34ct',
        'collector_campaign': 'reviews-collector-ab-20261019T052849Z.Us5why',
        'source_checkpoint': read(HERE / 'input-pins.json')['checkpoint'], 'source_preservation': before}
    extra_protected = {}
    for campaign in (TRAINING, CONFIRMATION):
        # Hashes only: no consumed confirmation queries/outcomes are copied.
        pin = read(campaign / 'collection-verification.json')['raw_files_sha256']
        root_files = ['selection.json', 'schedule.json', 'study-performance.json', 'collection-verification.json']
        extra_protected[campaign.name] = {**pin, **{n: sha(campaign / n) for n in root_files}}
    save(target / 'additional-protected.json', extra_protected)
    engine = target / 'engine'
    shutil.copytree(original / 'sources/pgvector', engine,
        ignore=shutil.ignore_patterns('.git', '*.o', '*.so', '*.bc', '__pycache__'))
    context = WORKSPACE / 'trials/torch-reviews-predicate-context/validation/engine-source/src'
    for name in ('fannbench.c', 'fannbench.h'): shutil.copyfile(context / name, engine / 'src' / name)
    patch_engine(engine)
    adapter = target / 'vendor/fannagent_pgvector'
    shutil.copytree(original / 'sources/fannagent_pgvector', adapter,
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'engine'))
    patch_adapter(adapter)
    cfg.update(source_query_method_sha256=CONFIG['frozen_query_method_sha256'],
        adapted_query_method_sha256=query_method_hash(adapter/'backend.py'),
        query_method_change='Explicit local-filter request binding inside the original policy timer; native timer boundary unchanged.')
    save(target/'experiment.json',cfg)
    # Reuse exactly the existing CART split algorithm, isolated from agent clients.
    cart_source = (WORKSPACE / 'agent/src/fannagent/learning/fit.py').read_text()
    module = ast.parse(cart_source)
    tree = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == '_tree')
    save(target / 'cart.py', '"""Pinned existing deterministic CART split algorithm."""\nimport math\nimport numpy as np\n\n' + ast.get_source_segment(cart_source, tree) + '\n', raw=True)
    for phase in ('build', 'acquire', 'measure'):
        script = f'''#!/usr/bin/env bash
#SBATCH --job-name=four-{phase}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
umask 077
exec python3 "$1/job.py" {phase} "$@"
'''
        save(target / 'slurm' / (phase + '.sbatch'), script, raw=True)
    save(target / 'README.md', (HERE / 'README.md').read_bytes(), raw=True)
    manifest = {'version': NAME, 'original_manifest_sha256': read(reference / 'manifest.json')['original_manifest_sha256'],
        'files': {str(p.relative_to(target)): sha(p) for p in sorted(target.rglob('*')) if p.is_file()},
        'provider_calls_allowed': 0, 'confirmation_queries_allowed': 0}
    save(target / 'manifest.json', manifest)
    archive = output / (NAME + '.tar.gz')
    with tarfile.open(archive, 'x:gz') as tar:
        for p in sorted(target.rglob('*')):
            if p.is_file(): tar.add(p, arcname=NAME + '/' + str(p.relative_to(target)), recursive=False)
    save(Path(str(archive) + '.sha256'), sha(archive) + '  ' + archive.name + '\n', raw=True)
    if before != check_sources(): raise ValueError('Original financial/scientific state changed')
    print(json.dumps({'package': str(target), 'archive': str(archive), 'archive_sha256': sha(archive),
        'archive_bytes': archive.stat().st_size, 'accounting': accounting(), 'source_preservation': before,
        'provider_calls': 0, 'confirmation_queries': 0}, indent=2))
    return target


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args(); build(args.output)
