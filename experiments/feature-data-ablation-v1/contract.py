"""Fixed four-arm development feature/data study. No model calls."""
from legacy_contract import encoded, read, save, sha, digest, lines, folds

NAME='torch-feature-data-ablation-v1'
SEED=20261022
AB={'status':'inconclusive','complete_pairs':0,'selection_effect_established':False}
EARLY=[1,2,4,8,16,32,64,128]
LEGACY_EXTRA=['query_predicate_threshold','local_probe_examined','local_probe_passed','local_probe_pass_ratio']
EXTRA=['progress_window_checkpoint','progress_probe_examined','progress_probe_passed',
       'progress_probe_pass_ratio','progress_recent_examined','progress_recent_passed',
       'progress_recent_pass_ratio','progress_has_valid','progress_valid_distance_min_or_zero',
       'progress_valid_distance_mean_or_zero','progress_valid_min_improvement_or_zero']
GROUPS=['basic','work','queue','distances','local_filter']
CONDITIONS={a:{'local_filter':a.startswith('P'),'checkpoints':EARLY,'training_vectors':n}
            for a,n in [('S100',100),('S160',160),('P100',100),('P160',160)]}
SEARCH={'tree_depth':3,'minimum_leaf_groups':8,'beam_width':4,'growth_rounds':7,
        'threshold_quantiles':[.05+.9*i/12 for i in range(13)]}
CONFIG={
 'name':NAME,'stage':'development-feature-data-ablation','seed':SEED,
 'conditions':CONDITIONS,'search':SEARCH,'risk_weights':[20.,80.,320.,1280.],
 'original_learning_vectors':100,'additional_learning_vectors':60,'calibration_vectors':40,
 'evaluation_vectors':60,'reserved_development_vectors':37,'acquisition_shards':2,
 'filters':['unfiltered','votes32','votes108'],'k':10,'row_count':247286,'dimension':768,
 'ef_search':640,'recall_tolerance':.005,'minimum_native_recall':.95,
 'development_recall_margin':.0025,'bootstrap_samples':10000,'bootstrap_seed':20261019,
 'progress_fetch_budget':64,'progress_fetches_per_window':8,'progress_windows':EARLY,
 'progress_population':'visible heap tuples of already loaded, scored layer-zero HNSW candidates; no upper-layer observations',
 'progress_zero_convention':'Enabled ratios and distance summaries are zero with no sampled valid rows; counts and progress_has_valid expose emptiness. No unknown stopped outcome is imputed.',
 'provider_calls_allowed':0,'confirmation_queries_allowed':0,'new_fits':'conventional first-stop beam search only',
 'ab_comparison':AB,'canonical_acceptance_established':False,'fresh_confirmation_required':True,
 'maximum_backend_calls':70000,'maximum_measurement_seconds':6600,
 'resources':{'cpus':4,'memory_gib':32,'wall_hours':2},'blocks':3,'warm_passes':3,
 'source_prepared':'/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286',
 'image_sha256':'7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a',
 'original_module_sha256':'77d38cad937d7c6d561d7f44ce447629ba913495ac732876fb50c9769d99680b',
 'frozen_query_method_sha256':'c0c7a5b45bc272765110450c72f70eafb0f2a7ab3034c036a18bff0fc049279b',
 'collector_campaign':'reviews-collector-ab-20261019T052849Z.Us5why',
 'source_learning_campaign':'reviews-policy-learning-20261019T145148Z.EJ34ct',
 'scope':'Four fixed training procedures, common disjoint development calibration/evaluation; no canonical confirmation or automatic deployment.',
}

def accounting():
    getters=3*(3+4*(19+23+34))
    acquire=300*128+getters
    evaluate=180*(128+4)+getters
    measure=180*(4+8*11)+getters
    return {'initial_allocations':4,'maximum_allocations':8,'acquisition_shards':2,
      'qualification_backend_calls_per_database_allocation':getters,
      'acquisition_backend_calls_per_shard_maximum':acquire,
      'evaluation_backend_calls_maximum':evaluate,'timing_backend_calls_per_block':measure,
      'maximum_campaign_backend_calls':2*acquire+evaluate+3*measure,
      'acquisition_retained_pairs_maximum':600*36,'acquisition_discarded_warmup_pairs_maximum':600*18,
      'evaluation_acquisition_retained_pairs_maximum':180*36,
      'evaluation_actual_candidate_trace_calls':180*4,
      'timing_arms':8,'timing_retained_pairs_per_block':180*8*4,
      'timing_retained_pairs_total':3*180*8*4,'timing_discarded_warmup_pairs_per_block':180*8,
      'metadata_receipt_sql_reads_per_query':2,'metadata_verification_sql_reads_per_query':2,
      'zero_provider_calls':True,'confirmation_queries':0}
