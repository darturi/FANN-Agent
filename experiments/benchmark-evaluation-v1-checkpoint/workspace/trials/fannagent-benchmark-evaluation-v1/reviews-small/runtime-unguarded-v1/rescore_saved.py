"""Rescore only the saved pre-fallback search outputs. No searches or timing claims."""
import collections,json
from pathlib import Path
from common import sha,write,THRESHOLDS
from support import valid
HERE=Path(__file__).resolve().parent;STUDY=HERE.parent;RESULTS=STUDY/'returns/job-22928562/results';OLD=STUDY/'kits/agent-policy-qualification-v1'
def main():
 receipt=json.loads((RESULTS/'receipt.json').read_text())
 for n,h in receipt['raw_sha256'].items():assert sha(RESULTS/n)==h
 q={r['id']:r for r in (json.loads(l) for l in (OLD/'queries.jsonl').read_text().splitlines())};eligible={int(t):set(ids) for t,ids in json.loads((RESULTS/'eligibility.json').read_text()).items()};expected=[];metrics=collections.defaultdict(lambda:collections.Counter())
 for line in (RESULTS/'quality.jsonl').read_text().splitlines():
  r=json.loads(line);qid=r['id'];t=r['filter'];e={'id':qid,'checkpoints':r['checkpoints'],'exact':r['exact'],'results':{}}
  baseline=valid(r['results']['native']['initial'],q[qid],eligible[t],r['exact'])
  for old,v in r['results'].items():
   name='native640' if old=='native' else old;out=v['initial'];score=valid(out,q[qid],eligible[t],r['exact']);e['results'][name]={'output':out,'checkpoint':v['checkpoint'],'recall':score}
   c=metrics[t,name];c['queries']+=1;c['recall_sum']+=score;c['short']+=len(out)<10;c['returned']+=len(out);c['losses']+=score<baseline-1e-12;c['stops']+=v['checkpoint']>0
  e['results']['noop640']=e['results']['native640'].copy();expected.append(e)
 assert len(expected)==3150
 (HERE/'expected.jsonl').write_text(''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in expected))
 report={'status':'saved_pre_guard_outputs_rescored','development_groups':450,'cases_per_family':3150,'exact_reference':'offline scoring only; not returned as query output','latency':'NOT inferred by subtracting fallback cost; fresh unguarded measurement required','provenance':'Three policies were generated using guarded development labels. Reused unchanged, not a fresh unguarded-trained agent episode.','metrics':{name:{str(t):{'queries':metrics[t,name]['queries'],'mean_recall':metrics[t,name]['recall_sum']/450,'short_outputs':metrics[t,name]['short'],'mean_returned_count':metrics[t,name]['returned']/450,'recall_losses_to_raw_native640':metrics[t,name]['losses'],'stops':metrics[t,name]['stops']} for t in THRESHOLDS} for name in ('native640','conservative_a','moderate_b_fixed','broad_c_fixed')},'source_receipt_sha256':sha(RESULTS/'receipt.json'),'validation_test_outcomes_opened':False,'provider_calls':0}
 assert all(c['recall_losses_to_raw_native640']==0 for v in report['metrics'].values() for c in v.values())
 write(HERE/'checks/saved-output-rescore.json',report)
 print(json.dumps({'status':report['status'],'raw_native':report['metrics']['native640'],'all_three_zero_query_losses':True},indent=2))
if __name__=='__main__':main()
