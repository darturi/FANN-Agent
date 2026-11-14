"""Reconstruct a qualification return from raw development records; no SQL/provider calls."""
import argparse,json,re
from pathlib import Path
from common import CHECKPOINTS,THRESHOLDS,matches,require,sha,write

def verify(results,kit):
 require(json.loads((results/'host-exit.json').read_text())['exit_code']==0,'host execution failed')
 binding=json.loads((kit/'binding.json').read_text());receipt=json.loads((results/'receipt.json').read_text())
 require(receipt['status']=='runtime_qualified' and receipt['provider_calls']==receipt['validation_queries']==receipt['test_queries']==0,'qualification did not complete cleanly')
 require(receipt['split_sha256']==binding['split_manifest_sha256'] and receipt['module_sha256']==binding['module_sha256'] and receipt['protocol_sha256']==binding['protocol_sha256'],'qualification identity differs')
 for name,h in receipt['raw_sha256'].items():require(sha(results/name)==h,'raw file checksum changed')
 eligibility={t:set(ids) for t,ids in json.loads((results/'eligibility.json').read_text()).items()}
 expected={q['id'] for q in (json.loads(l) for l in (kit/'queries.jsonl').read_text().splitlines())};observed=set();counts={}
 for t in THRESHOLDS:
  rows=[json.loads(l) for l in (results/f'qualification-{t}.jsonl').read_text().splitlines()];require(len(rows)==450,'incomplete filter');counts[t]=len(rows)
  for row in rows:
   qid=row['id'];require(qid in expected and qid not in observed and row['threshold']==t,'unexpected/duplicate query');observed.add(qid)
   require(matches(row['live']['6']['output'],row['native']) and row['live']['6']['checkpoint']==0,'no-stop output mismatch')
   native=row['native'];require(len(native)<=10 and len({i for i,_ in native})==len(native),'native invalid')
   require(row['native_complete']==(len(native)==10),'native completeness flag differs')
   for output in [native,*[v['output'] for v in row['live'].values()]]:
    require(len(output)<=10 and len({i for i,_ in output})==len(output) and all(i in eligibility[str(t)] for i,_ in output),'ineligible/duplicate output')
   boundary=max(d for _,d in row['exact']);score=lambda out:sum(d<=boundary+1e-6 for _,d in out)/10
   require(abs(score(native)-row['native_recall'])<1e-12,'native score mismatch')
   for cp,proof in row['forced'].items():
    require(int(cp) in CHECKPOINTS and len(proof['output'])==10,'invalid forced result');obs=next(o for o in row['checkpoints'] if o['checkpoint']==int(cp));require(abs(max(d for _,d in proof['output'])-obs['tenth_distance'])<=1e-6,'forced distance mismatch')
    live=row['live'][str(CHECKPOINTS.index(int(cp))+3)];require(live['checkpoint']==int(cp) and matches(live['output'],proof['output']),'live forced mismatch')
   for arm in ('1','2'):
    live=row['live'][arm];cp=live['checkpoint'];require(matches(live['output'],row['forced'][str(cp)]['output'] if cp else native),'adaptive output mismatch')
   for live in row['live'].values():require(abs(score(live['output'])-live['recall'])<1e-12,'live recall mismatch')
 require(observed==expected and len(observed)==3150,'query inventory differs')
 require(receipt['searches']['total']<=60000 and receipt['data_index_before_after'],'resource/integrity gate failed')
 selection=json.loads((results/'parent-selection.json').read_text());require(selection['status']=='selected','no adequate parent selected')
 prior={r['id']:r for r in (json.loads(line) for line in (kit/'prior-references.jsonl').read_text().splitlines())}
 accum={};seen_sweep=set()
 for line in (results/'parent-sweep.jsonl').read_text().splitlines():
  row=json.loads(line);ef=row['ef_search'];t=row['threshold'];qid=row['id'];require(qid in expected and (ef,qid) not in seen_sweep,'sweep query mismatch');seen_sweep.add((ef,qid))
  require(ef in (640,1000,2048,4096,8192) and t in THRESHOLDS,'undeclared effort/filter')
  output=row['output'];require(len(output)<=10 and len({i for i,_ in output})==len(output) and all(i in eligibility[str(t)] and 0<=d<=2 for i,d in output),'invalid sweep output')
  boundary=max(d for _,d in prior[qid]['exact']);score=sum(d<=boundary+1e-6 for _,d in output)/10
  require(abs(score-row['recall'])<1e-12 and row['complete']==(len(output)==10),'sweep score/count mismatch')
  if ef==640:require(matches(output,prior[qid]['native']),'native640 continuity mismatch')
  bucket=accum.setdefault((ef,t),[]);bucket.append((score,len(output)==10))
 require(len(seen_sweep)==3150*5,'sweep incomplete')
 adequate=[]
 for ef in (640,1000,2048,4096,8192):
  ok=True
  for t in THRESHOLDS:
   bucket=accum[(ef,t)];require(len(bucket)==450,'sweep group coverage mismatch')
   mean=sum(v for v,_ in bucket)/450;complete=sum(c for _,c in bucket);record=selection['sweep'][str(ef)][str(t)]
   require(abs(record['mean_recall']-mean)<1e-12 and record['complete']==complete,'sweep summary differs')
   ok &= mean>=.95 and complete==450
  if ok:adequate.append(ef)
 require(adequate and selection['selected_ef_search']==min(adequate)==receipt['selected_parent_ef_search'],'parent selection differs')
 result={'status':'verified_original_graph_development_qualification','queries':len(observed),'groups':450,'per_filter':counts,'provider_calls':0,'test_queries':0,'selected_parent_ef_search':selection['selected_ef_search'],'sweep_queries_verified':len(seen_sweep),'receipt_sha256':sha(results/'receipt.json'),'module_sha256':binding['module_sha256'],'protocol_sha256':binding['protocol_sha256'],'limitations':'Raw replay checks output identities/scores and receipts; actual forced-prefix/schema/eligibility/data/index checks are performed by the pinned native guest.'}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('results',type=Path);p.add_argument('--kit',type=Path,required=True);a=p.parse_args();r=verify(a.results,a.kit);write(a.results/'local-verification.json',r);print(json.dumps(r,indent=2))
