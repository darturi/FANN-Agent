"""Additional aggregate consistency checks on the same pinned saved data only."""
from pathlib import Path
import collections as C
import csv
import hashlib
import json
import math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
r=json.loads((HERE/'audit.json').read_text())
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
corpus=ROOT/'trials/torch-reviews-selective-agent-v1/runs/20261022T192817Z-66ed81d6/evidence/corpus.json'
assert sha(corpus)==r['source_input_hashes'][str(corpus.relative_to(ROOT))]
qs=json.loads(corpus.read_text())['queries']
base_names=[n for n,d in r['feature_definitions'].items() if d['group'] in {'basic','work','queue','distances'}]
static_probe=['local_probe_examined','local_probe_passed','local_probe_pass_ratio']
progress=[n for n,d in r['feature_definitions'].items() if d['group']=='progress_filter']
digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
by_group={};static_unchanged=0;progress_changes=0;progress_grid_changes=0
native={f:[] for f in ['unfiltered','votes32','votes108']}
for q in qs:
 states=q['base_states'];pstates=q['local_states'];native[q['stratum']].append(q['native_recall'])
 a=[tuple(s['features'][n] for n in static_probe) for s in states]
 static_unchanged+=len(set(a))==1
 a=[tuple(s['features'][n] for n in progress) for s in pstates]
 progress_changes+=len(set(a))>1
 b=[tuple(s['features'][n] for n in progress) for s in pstates if s['checkpoint_index'] in [1,2,4,8,16,32,64,128]]
 progress_grid_changes+=len(set(b))>1
 by_group.setdefault(q['group'],set()).add(digest([{**s,'features':{n:s['features'][n] for n in base_names}} for s in states]))
outputs={};matched=0
for part in [0,1]:
 p=ROOT/f'trials/torch-reviews-results/reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y/acquire/part-{part}/proofs.jsonl'
 assert sha(p)==r['source_input_hashes'][str(p.relative_to(ROOT))]
 with p.open() as h:
  for line in h:
   v=json.loads(line);k=(v['query_id'],v['checkpoint']);out=(v['policy_ids'],v['policy_distances'])
   if k in outputs:
    assert outputs[k]==out
    matched+=1
   else:outputs[k]=out
assert matched==4695 and len(outputs)==4695
summary={'version':'p3a-coverage-summary.v1','audit_sha256':sha(HERE/'audit.json'),'static_progress_actual_stop_ID_distance_matches':matched,
 'light19_projected_trajectories_identical_across_all_three_filters_vectors':sum(len(v)==1 for v in by_group.values()),
 'static_probe_unchanged_throughout_full_trajectory_cases':static_unchanged,'progress_features_change_through_full_trajectory_cases':progress_changes,
 'progress_features_change_between_allowed_grid_states_cases':progress_grid_changes,
 'native_mean_recall_per_filter':{f:sum(v)/len(v) for f,v in native.items()},'new_fits_or_searches':0,'new_database_provider_or_Torch_calls':0,
 'profile_totals':{},'unrestricted_state_coverage':{},'restricted_grid': [1,2,4,8,16,32,64,128],
 'incomplete_top10_cells':{k:v['actual_stop_labels']-v['valid_top10'] for k,v in r['coverage_by_profile_filter_checkpoint'].items() if v['actual_stop_labels']!=v['valid_top10']}}
for profile in ['static23','progress34']:
 t=C.Counter()
 for k,v in r['coverage_by_profile_filter_checkpoint'].items():
  if k.startswith(profile+'/'):t.update(v)
 summary['profile_totals'][profile]=dict(t)
 total=sum(v['full_trajectory_states_per_family'] for k,v in r['acquisitions'].items() if k.startswith('feature-'))
 summary['unrestricted_state_coverage'][profile]={'observed_states':total,'measured_grid_stops':t['actual_stop_labels'],'outside_grid_unknown_outcomes':total-t['actual_stop_labels']}
summary['current_light19']={'required_reachable_grid_cells':r['current_binary_light19_complete_grid_required_cells'],'unique_observed_stop_cells':r['current_binary_light19_unique_actual_stop_cells'],'missing_actual_stop_cells':r['current_binary_light19_complete_grid_required_cells']-r['current_binary_light19_unique_actual_stop_cells'],'full_fixed_stop_cost_matrix_complete':False,'old_binary_light19_observed_stop_cells':sum(v['actual_stop_labels'] for k,v in r['old_binary_coverage'].items() if k.startswith('light19_old_binary/'))}
with (HERE/'coverage-summary.json').open('x') as h:json.dump(summary,h,indent=2,sort_keys=True);h.write('\n')
fields=['profile','filter','checkpoint','cases','reached','unreachable_search_finished','actual_stop_labels','all_features_available','valid_top10','recall_below_native','recall_not_below_native','positive_activation_proxy','positive_reuse_proxy','both_fixed_stop_proxies_positive']
with (HERE/'coverage.csv').open('x',newline='') as h:
 w=csv.DictWriter(h,fields);w.writeheader()
 for key,v in sorted(r['coverage_by_profile_filter_checkpoint'].items(),key=lambda kv:(kv[0].split('/')[0],kv[0].split('/')[1],int(kv[0].split('/')[2]))):
  profile,filt,cp=key.split('/');w.writerow({'profile':profile,'filter':filt,'checkpoint':cp,**v})
print(json.dumps(summary,indent=2))
