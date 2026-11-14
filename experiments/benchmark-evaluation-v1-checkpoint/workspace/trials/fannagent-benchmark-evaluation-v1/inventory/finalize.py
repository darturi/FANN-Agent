"""Produce conservative roles from the metadata audit, without opening query outcomes."""
from pathlib import Path
if (Path(__file__).resolve().parents[1]/'reviews-small/freeze/split-freeze.json').exists():
    raise SystemExit('Provisional finalizer superseded by frozen reviews-small split; do not overwrite historical inputs')
exec(compile((__import__('pathlib').Path(__file__).with_name('audit.py')).read_text().split('inventory=[]')[0], 'audit-definitions', 'exec'))
# The definition prefix loads only source query vectors and identities.
files=json.loads((OUT/'historical-query-files.json').read_text())
evidence=json.loads((OUT/'group-evidence.json').read_text())
by_path={x['path']:x for x in files}
def groups(path): return set(by_path[path]['groups'])
manifest_path=ROOT/'research/fannagent-controlled-reviews-batch-manifest-2026-11-08.json'
m=json.loads(manifest_path.read_text()); development=set()
for block in m['blocks']:
 for g in block['vector_groups']:
  hits=lookup[g['vector_sha256']]; assert len(hits)==1; development.update(hits)
consumed=set()
for x in files:
 if ('feature-data-ablation' in x['path'] and Path(x['path']).name=='evaluation.jsonl') or ('confirmation/cohorts/' in x['path'] and Path(x['path']).name=='queries.jsonl'):
  consumed.update(x['groups'])
assert len(development)==200 and not development.intersection(consumed)
# Preserve explicit old 37-group reservations, even if their query vectors appeared in catalogs.
ap=ROOT/'trials/torch-reviews-results/feature-data-ablation-v1/torch-feature-data-ablation-v1/inputs/ablation-split.json'
a=json.loads(ap.read_text()); reserved=set()
for g in a['selected_catalog_groups']['reserved']:
 reserved.update(lookup[a['vector_hash_by_catalog_group'][g]])
assert len(reserved)==37
available=set(range(1000))-set(map(int,evidence))
seed='fannagent-benchmark-evaluation-v1:phase0:20261110'
ordered=sorted(available,key=lambda i:sha((seed+':'+key(f32[i])).encode()))
# Bounded validation pool; retain the remainder for the test, without asserting sufficient power.
nvalidation=min(25,len(ordered)//5)
validation=set(ordered[:nvalidation]); test=set(ordered[nvalidation:])
roles={}
for i in range(1000):
 roles[i]=('development' if i in development else 'consumed_evaluation_development' if i in consumed else 'historical_reserved' if i in reserved else 'historical_uncertain_excluded' if str(i) in evidence else 'validation' if i in validation else 'test')
counts=dict(collections.Counter(roles.values()))
assert set(roles)==set(range(1000)) and validation.isdisjoint(test)
assert not (validation|test).intersection(map(int,evidence))
with h5py.File(SOURCE/'filters/reviews_filters_0.hdf5') as f: filters=[x.decode() for x in f['filters'][:]]
with (OUT/'query-catalog.jsonl').open('w') as out:
 for i in range(1000):
  for fi,predicate in enumerate(filters):
   row={'dataset':'MoReVec Reviews Small','vector_group':'reviews-small-sha256:'+key(f32[i]),'source_index':i,'source_query_id':ids[i],'importer_id':f'reviews-f{fi:03d}-q{i:04d}','filter_id':fi,'filter':predicate,'raw_float64_sha256':sha(np.asarray(raw[i],dtype='<f8').tobytes()),'float32_sha256':key(f32[i]),'normalized_float32_sha256':key(norm[i]),'source_path':f'harness/downloads/morevec/MoRe_small/queries/queries_flex_reviews_sim_0_{fi}.hdf5','proposed_role':roles[i],'exposure_evidence_ref':f'group-evidence.json#/{i}' if str(i) in evidence else None}
   out.write(json.dumps(row,sort_keys=True)+'\n')
precision={str(n):{'zero_loss_one_sided_95pct_upper_probability':1-0.05**(1/n)} for n in (len(available),len(test)) if n}
dump('split-manifest.json',{'status':'provisional; Phase 1 must accept precision and local-history assumptions before use','seed':seed,'algorithm':'sort available groups by sha256(seed + colon + float32_sha256); first min(25,floor(n/5)) validation; remainder test','scope':'All seven predicates share one vector-group role; propagate these identities to overlapping scales','counts':counts,'assignments':[{'source_index':i,'group':key(f32[i]),'role':roles[i]} for i in range(1000)],'overlap_checks':'passed; validation/test disjoint and neither appears in historical JSONL inventory','precision':precision,'limitations':['No universal recall guarantee','No complete remote/chat access log exists in this local audit','Historical reservation does not itself prove exposure','Test size may not establish proposed 0.25 percentage point population noninferiority'],'input_hashes':{p.name:file_sha(p) for p in (OUT/'source-inventory.json',OUT/'historical-query-files.json',manifest_path,ap)}})
dump('audit-summary.json',{'counts':counts,'available_before_split':len(available),'precision':precision,'jsonl_files':len(files),'unique_jsonl_contents':len({x['sha256'] for x in files})})
print(json.dumps({'counts':counts,'available':len(available),'precision':precision},indent=2))
