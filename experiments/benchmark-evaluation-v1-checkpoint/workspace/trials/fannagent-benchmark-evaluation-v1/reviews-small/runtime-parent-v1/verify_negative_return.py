"""Verify the predeclared no-adequate-parent disposition from every saved sweep row."""
import argparse,collections,hashlib,json,math
from pathlib import Path
from common import matches,require,sha,threshold,write

def verify(results,kit):
 for line in (kit/'SHA256SUMS').read_text().splitlines():
  h,name=line.split('  ',1);require(sha(kit/name)==h,'kit member changed: '+name)
 host=json.loads((results/'host-exit.json').read_text());require(host=={'exit_code':3,'job_id':'22643346'},'unexpected job/exit')
 plan=json.loads((kit/'parent-plan.json').read_text());binding=json.loads((kit/'binding.json').read_text())
 require(sha(kit/'parent-plan.json')==binding['parent_plan_sha256'],'plan changed')
 require(sha(kit/'prior-references.jsonl')==binding['prior_references_sha256'],'prior truth changed')
 expected={q['id']:threshold(q) for q in (json.loads(l) for l in (kit/'queries.jsonl').read_text().splitlines())}
 require(len(expected)==3150,'bad development input')
 prior={r['id']:r for r in (json.loads(l) for l in (kit/'prior-references.jsonl').read_text().splitlines())};require(set(prior)==set(expected),'truth inventory differs')
 eligibility={int(t):set(ids) for t,ids in json.loads((results/'eligibility.json').read_text()).items()}
 original=json.loads((results.parents[1]/'job-22635567/results/eligibility.json').read_text());require({str(t):sorted(ids) for t,ids in eligibility.items()}==original,'eligibility changed')
 cells=collections.defaultdict(list);seen=set();focus=[];rows=0;inversions=[]
 for line in (results/'parent-sweep.jsonl').read_text().splitlines():
  r=json.loads(line);qid=r['id'];ef=r['ef_search'];t=r['threshold'];key=(ef,qid)
  require(ef in plan['effort_grid'] and qid in expected and expected[qid]==t and key not in seen,'unexpected/duplicate sweep row');seen.add(key)
  out=r['output'];require(len(out)<=10 and len({i for i,d in out})==len(out),'invalid result count/duplicates')
  require(all(i in eligibility[t] and math.isfinite(d) and -1e-6<=d<=2+1e-6 for i,d in out),'ineligible/nonfinite distance')
  require(all(out[i][1]<=out[i+1][1]+1e-6 for i in range(len(out)-1)),'output order differs beyond frozen tolerance')
  for i in range(len(out)-1):
   if out[i][1]>out[i+1][1]:inversions.append({'id':qid,'ef_search':ef,'delta':out[i][1]-out[i+1][1]})
  boundary=max(d for _,d in prior[qid]['exact']);score=sum(d<=boundary+1e-6 for _,d in out)/10
  require(abs(score-r['recall'])<1e-12 and r['complete']==(len(out)==10),'recall/completeness mismatch')
  require(type(r['request_ns']) is int and r['request_ns']>0,'invalid request timing')
  if ef==640:require(matches(out,prior[qid]['native']),'native640 continuity failed')
  cells[ef,t].append(r);rows+=1
  if t==743 and ef==8192 and not r['complete']:focus.append(qid)
 require(rows==len(expected)*len(plan['effort_grid'])==15750,'incomplete sweep')
 selection=json.loads((results/'parent-selection.json').read_text());require(selection['status']=='no_adequate_parent' and selection['selected_ef_search'] is None and selection['grid']==plan['effort_grid'],'wrong disposition')
 reconstructed={};adequate=[]
 for ef in plan['effort_grid']:
  conditions={}
  for t in plan['filters']:
   group=cells[ef,t];require(len(group)==450,'wrong cell count')
   complete=sum(r['complete'] for r in group);mean=sum(r['recall'] for r in group)/450
   c={'queries':450,'complete':complete,'mean_recall':mean,'adequate':complete==450 and mean>=.95}
   saved=selection['sweep'][str(ef)][str(t)]
   require(all(c[k]==saved[k] for k in ('queries','complete','adequate')) and abs(mean-saved['mean_recall'])<1e-12,'sweep summary differs')
   conditions[str(t)]=c
  reconstructed[str(ef)]=conditions
  if all(c['adequate'] for c in conditions.values()):adequate.append(ef)
 require(not adequate,'negative disposition not justified');require(len(focus)==1,'incomplete query count differs')
 qid=focus[0];history=[r for ef in plan['effort_grid'] for r in cells[ef,743] if r['id']==qid]
 exact=prior[qid]['exact'];final=history[-1]['output'];returned={i for i,d in final};exact_ids={i for i,d in exact}
 require(returned<=exact_ids and len(returned)==8,'incomplete-query interpretation differs')
 details={'id':qid,'exact':exact,'history':history,'missing_exact_neighbors':[[i,d] for i,d in exact if i not in returned],'all_returned_are_exact_top10':True,'evidence_limit':'Only native640 checkpoint traces are available; no checkpoint/local-selectivity trace at8192 and no global candidate ranks. Cannot prove which inner search stage omitted the two neighbors.'}
 write(results/'incomplete-query-inspection.json',details)
 result={'status':'verified_bounded_negative_no_adequate_parent','job_id':host['job_id'],'sweep_rows_verified':rows,'independent_development_groups':450,'effort_settings':5,'conditions':7,'cells_verified':35,'native640_continuity_queries':3150,'eligible_sets_match_original_job':True,'all_recall_scores_and_completeness_reconstructed':True,'selection_reconstructed':True,'distance_order_diagnostics':inversions,'distance_order_tolerance':1e-6,'adequate_parents':adequate,'incomplete_votes743_at8192':focus,'summary':reconstructed,'provider_calls':0,'validation_test_queries':0,'raw_sha256':{p.name:sha(p) for p in results.iterdir() if p.is_file() and p.name not in ('negative-verification.json','incomplete-query-inspection.json')},'limitations':'Negative branch emits no success receipt or new forced-stop qualification. Exit3 agrees with planned disposition and guest finally cleanup/index checks; independent local reconstruction verifies the sweep, not unreturned traversal traces.'}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('results',type=Path);p.add_argument('--kit',type=Path,required=True);a=p.parse_args();r=verify(a.results,a.kit);write(a.results/'negative-verification.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ('summary','raw_sha256')},indent=2))
