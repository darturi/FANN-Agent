"""Predeclared selective-agent engineering study; old A/B remains inconclusive."""
from pathlib import Path
from legacy_contract import read, save, sha, digest, encoded

NAME = 'torch-selective-agent-v1'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2] if len(HERE.parents)>2 else Path('/mac-workspace-unavailable')
if (HERE/'.workspace-root.json').is_file():ROOT=Path(read(HERE/'.workspace-root.json')['root'])
SOURCE = ROOT/'trials/torch-reviews-results/feature-data-ablation-v1/torch-feature-data-ablation-v1'
CAMPAIGN = ROOT/'trials/torch-reviews-results/reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y'
OUTPUT = ROOT/'trials/torch-reviews-selective-agent-v1'
SOURCE_MANIFEST = '3a50e8296bdba9dbb8c018ef742af2b2e868ae80f85172c876511a015fd5838c'
MODULE = 'e7dcace1f4dfd4ea233256d6cdfc17b3190f3f07cccb6406b479b5ebe8b85811'
AB = {'status':'inconclusive','complete_pairs':0,'selection_effect_established':False}
FILTERS = ['unfiltered','votes32','votes108']
EARLY = [1,2,4,8,16,32,64,128]
CONFIG = dict(name=NAME,version='selective-agent.v1',seed=20261022,bootstrap_seed=20261019,
    filters=FILTERS,
    bootstrap_samples=10000,recall_tolerance=.005,development_recall_margin=.0025,
    minimum_native_recall=.95,minimum_groups=30,k=10,ef_search=640,row_count=247286,dimension=768,
    blocks=3,maximum_allocations=9,maximum_backend_calls=70000,maximum_measurement_seconds=6600,
    resources={'cpus':4,'memory_gib':32,'wall_hours':2},
    maximum_initial_exports=3,maximum_revisions=1,maximum_helper_fits=96,
    provider_attempts={'A':8,'B':4},phase_usd={'A':'6','B':'4'},new_provider_cap_usd='10',
    sandbox_commands=120,active_seconds=3600,command_seconds=60,
    source_prepared='/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286',
    image_sha256='7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a',
    module_sha256=MODULE,source_manifest_sha256=SOURCE_MANIFEST,ab_comparison=AB,
    canonical_acceptance_established=False)

def lines(path):
    import json
    return [json.loads(s) for s in Path(path).read_text().splitlines() if s]

def replace(path,value):
    path=Path(path);tmp=path.with_name('.'+path.name+'.tmp')
    tmp.write_bytes(encoded(value));tmp.replace(path)

def accounting(stage,candidates=3,fixture_cases=None):
    if stage not in {'pilot','revision','confirmation'}:raise ValueError('Unknown stage')
    if not 1<=candidates<=(3 if stage=='pilot' else 1):raise ValueError('Candidate count')
    n=(180 if stage=='confirmation' else 600) if fixture_cases is None else fixture_cases
    if type(n) is not int or n<3 or n%3 or n>600:raise ValueError('Case count')
    arms=3 if stage=='confirmation' else 2*candidates+2
    warm=8 if stage=='confirmation' else 3
    profiles=1 if stage=='confirmation' else 3
    calls=921+n*(2+profiles+arms*(1+2*(warm+2)))
    assert calls<=70000
    return {'allocations':3,'cases':n,'independent_vectors':n//3,'arms':arms,
        'getter_searches':921,'qualification_backend_calls_per_database_allocation':921,'profile_references_per_case':profiles,
        'retained_pairs_per_block':n*arms*(warm+1),'discarded_warmup_pairs_per_block':n*arms,
        'backend_searches_per_block_maximum':calls,'warm_passes':warm}

def bootstrap():
    import sys
    vendor=HERE/'vendor' if (HERE/'vendor').exists() else SOURCE/'vendor'
    sys.path[:0]=[str(vendor),str(ROOT/'agent/src'),str(ROOT/'trials/torch-reviews-first/sources')]
