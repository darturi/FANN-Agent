"""Reconstruct guarded quality, all paired timings, selection and policy proofs."""
import argparse,collections,hashlib,json
from pathlib import Path
from common import THRESHOLDS,matches,require,sha,threshold,write
from experiment import GRID,SEED,validate,chosen_stop
LABELS=('native-A','native-B','noop-A','noop-B')
def lines(path):
    with path.open() as f:
        for line in f:
            if line.strip():yield json.loads(line)
def verify(results,kit):
    for line in (kit/'SHA256SUMS').read_text().splitlines():
        h,name=line.split('  ',1);require(sha(kit/name)==h,'kit checksum differs')
    host=json.loads((results/'host-exit.json').read_text());require(host['exit_code']==0,'host job failed')
    receipt=json.loads((results/'receipt.json').read_text());binding=json.loads((kit/'binding.json').read_text())
    require(receipt['status']=='common_guard_qualified_and_development_timed' and receipt['job_id']==host['job_id'],'wrong status/job')
    for name,h in receipt['raw_sha256'].items():require(sha(results/name)==h,'raw checksum differs: '+name)
    for key in ('split_sha256','module_sha256','guard_plan_sha256','guard_source_sha256'):
        bkey='split_manifest_sha256' if key=='split_sha256' else key
        require(receipt[key]==binding[bkey],'binding differs')
    require(receipt['provider_calls']==receipt['validation_test_queries']==0 and receipt['exported_snapshot_shared'] and receipt['data_index_before_after'] and receipt['cleanup_verified'],'isolation/integrity gate failed')
    queries={q['id']:q for q in lines(kit/'queries.jsonl')};require(len(queries)==3150,'wrong input count')
    prior={q['id']:q for q in lines(kit/'prior-references.jsonl')};require(set(queries)==set(prior),'prior identity differs')
    prior_sweep={(r['ef_search'],r['id']):r for r in lines(kit/'prior-sweep.jsonl')}
    eligible={int(t):set(ids) for t,ids in json.loads((results/'eligibility.json').read_text()).items()}
    cache={};quality=collections.defaultdict(list);expected_counter=collections.Counter()
    for r in lines(results/'quality.jsonl'):
        ef=r['ef'];qid=r['id'];t=r['filter'];key=ef,qid
        require(ef in GRID and qid in queries and threshold(queries[qid])==t and key not in cache,'quality inventory differs')
        a=r['native_guard'];b=r['agent_noop_guard'];truth=prior[qid]['exact'];expected=prior_sweep[key]['output']
        score=validate(a,queries[qid],eligible[t],truth,expected);validate(b,queries[qid],eligible[t],truth,expected)
        require(matches(a['output'],b['output']) and a['fallback_used']==b['fallback_used'] and r['noop_checkpoint']==0,'guarded no-stop differs')
        require(abs(score-r['native_recall'])<1e-12,'quality recall differs')
        cache[key]=a;quality[ef,t].append(score)
        expected_counter['ann']+=2;expected_counter['completion_exact']+=a['fallback_used']+b['fallback_used']
    require(len(cache)==15750,'quality incomplete')
    for ef in GRID:
        for t in THRESHOLDS:require(len(quality[ef,t])==450,'quality cell incomplete')
    seen=set();times=collections.defaultdict(list)
    ordered={}
    for t in THRESHOLDS:
        cases=[q for q in queries.values() if threshold(q)==t];cases.sort(key=lambda q:hashlib.sha256((SEED+':'+q['id'].rsplit('-',1)[0]).encode()).hexdigest());ordered[t]=cases
    for r in lines(results/'timing.jsonl'):
        ef=r['ef'];qid=r['id'];epoch=r['epoch'];label=r['label'];t=r['filter'];key=ef,qid,epoch,label
        require(ef in GRID and qid in queries and threshold(queries[qid])==t and epoch in (0,1) and label in LABELS and key not in seen,'timing inventory differs');seen.add(key)
        cases=ordered[t] if epoch==0 else list(reversed(ordered[t]));j=next(i for i,q in enumerate(cases) if q['id']==qid)
        offset=(j+epoch+THRESHOLDS.index(t)+GRID.index(ef))%4;order=[LABELS[(v+offset)%4] for v in (0,1,3,2)]
        if epoch:order.reverse()
        position=order.index(label);require(r['order']==order and r['position']==position and r['predecessor']==(order[position-1] if position else None),'schedule differs')
        expected=cache[ef,qid]
        require(matches(r['initial'],expected['initial']) and matches(r['output'],expected['output']) and r['fallback_used']==expected['fallback_used'],'timed result differs')
        require(r['required_count']==10 and r['initial_count']==len(r['initial']) and r['request_ns']==r['ann_ns']+r['fallback_ns']+r['guard_and_construction_ns'] and min(r['request_ns'],r['ann_ns'])>0 and min(r['fallback_ns'],r['guard_and_construction_ns'])>=0,'timer accounting differs')
        if not r['fallback_used']:require(r['fallback_ns']==0,'nonfallback exact time')
        expected_counter['ann']+=1;expected_counter['completion_exact']+=r['fallback_used'];times[ef,t,label].append(r['request_ns'])
    require(len(seen)==126000,'timing incomplete')
    for ef in GRID:
        for t in THRESHOLDS:
            for label in LABELS:require(len(times[ef,t,label])==900,'timing cell incomplete')
    # Reconstruct warmup attempt counts from the fixed ten development inputs.
    for epoch in (0,1):
        for ef in GRID:
            for t in THRESHOLDS:
                cases=ordered[t] if epoch==0 else list(reversed(ordered[t]))
                expected_counter['ann']+=40
                expected_counter['completion_exact']+=4*sum(cache[ef,q['id']]['fallback_used'] for q in cases[:10])
    selection=json.loads((results/'selection.json').read_text());candidates=[];costs={};controls={}
    for ef in GRID:
        means={t:sum(times[ef,t,'native-A']+times[ef,t,'native-B'])/1800 for t in THRESHOLDS}
        cost=sum(means[t] for t in THRESHOLDS if t>=0)/6;costs[ef]=cost
        saved=next(x for x in selection['grid'] if x['ef']==ef)
        require(abs(saved['equal_scalar_filter_mean_ns']-cost)<1e-6,'selection mean differs')
        ok=all(sum(quality[ef,t])/450>=.95 for t in THRESHOLDS)
        require(saved['adequate']==ok,'selection eligibility differs')
        if ok:candidates.append(ef)
        controls[ef]={str(t):{family:sum(times[ef,t,family+'-A'])/sum(times[ef,t,family+'-B']) for family in ('native','noop')} for t in THRESHOLDS}
    require(candidates,'no adequate parent');best=min(costs[ef] for ef in candidates);chosen=max(ef for ef in candidates if costs[ef]<=best*1.01)
    require(chosen==selection['selected_ef_search']==receipt['selected_parent_ef_search'],'parent selection differs')
    policy_seen=set();proof_count=0
    for t in THRESHOLDS:
        for r in lines(results/f'policy-qualification-{t}.jsonl'):
            qid=r['id'];require(qid in queries and threshold(queries[qid])==t and qid not in policy_seen and r['ef']==chosen,'policy scope differs');policy_seen.add(qid)
            truth=prior[qid]['exact'];cap={'checkpoints':r['checkpoints']}
            expected_counter['reference_exact']+=1;expected_counter['capture']+=1
            for cp,proof in r['forced'].items():
                obs=next(o for o in r['checkpoints'] if o['checkpoint']==int(cp));require(len(proof['output'])==10 and abs(max(d for _,d in proof['output'])-obs['tenth_distance'])<=1e-6,'forced output differs');proof_count+=1;expected_counter['forced_trace']+=1
            for arm in (1,2,3,4,5):
                p=r['policies'][str(arm)];cp=chosen_stop(cap,arm);require(p['checkpoint']==cp,'policy stop differs')
                initial=r['forced'][str(cp)]['output'] if cp else cache[chosen,qid]['initial']
                score=validate(p,queries[qid],eligible[t],truth,initial);require(abs(score-p['recall'])<1e-12,'policy score differs')
                expected_counter['ann']+=1;expected_counter['completion_exact']+=p['fallback_used']
    require(len(policy_seen)==3150,'policy qualification incomplete');expected_counter['local_capture']=70
    actual=receipt['searches'];require(actual['total']==sum(v for k,v in actual.items() if k!='total')<=225000,'attempt cap/count differs')
    require({k:v for k,v in actual.items() if k!='total'}==dict(expected_counter),'attempt ledger reconstruction differs')
    return {'status':'verified_common_guard_qualification_and_development_timing','job_id':host['job_id'],'groups':450,'quality_rows':15750,'timed_requests':126000,'policy_qualification_requests':3150,'forced_proofs':proof_count,'selected_parent_ef_search':chosen,'native_guard_equal_scalar_mean_ms':{str(ef):ns/1e6 for ef,ns in costs.items()},'identical_code_mean_ratios':controls,'attempts':actual,'provider_calls':0,'validation_test_queries':0,'limitations':'One allocation supports development selection, not confirmatory speed claims. Forced traversal-prefix/local-map/restore checks depend on the pinned native receipt; compact raw outputs are independently replayed.','receipt_sha256':sha(results/'receipt.json')}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('results',type=Path);p.add_argument('--kit',type=Path,required=True);a=p.parse_args();r=verify(a.results,a.kit);write(a.results/'local-verification.json',r);print(json.dumps(r,indent=2))
