"""Allowlisted development-only policy evidence and exact rule replay."""
import collections,hashlib,json,math,re
from pathlib import Path
BASE=Path(__file__).resolve().parents[2]
RESULTS=BASE/'returns/job-22684501/results'
FILTERS=('unfiltered','votes743','votes527','votes310','votes192','votes108','votes32')
FEATURES=('qualifying_count','tenth_distance','frontier_gap','top10_new_since_previous')
POINTS=(16,32,64)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encoded(o):return json.dumps(o,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def load():
    verification=json.loads((RESULTS/'local-verification.json').read_text());assert verification['selected_parent_ef_search']==640 and verification['timed_requests']==126000
    receipt=json.loads((RESULTS/'receipt.json').read_text())
    for name,h in receipt['raw_sha256'].items():assert sha(RESULTS/name)==h
    allowed={r['source_index'] for r in (json.loads(l) for l in (BASE/'splits/development.jsonl').read_text().splitlines())};assert len(allowed)==450
    fold={i:int(f) for f,indices in json.loads((BASE/'protocol/development-folds.json').read_text())['folds'].items() for i in indices};assert set(fold)==allowed
    ordinals={i:k for k,i in enumerate(sorted(allowed))};rows={}
    for line in (RESULTS/'quality.jsonl').read_text().splitlines():
        r=json.loads(line)
        if r['ef']!=640:continue
        qid=r['id'];i=int(re.fullmatch(r'reviews-clean-v(\d+)-(?:unfiltered|votes\d+)',qid)[1]);assert i in allowed
        rows[qid]={'group':ordinals[i],'fold':fold[i],'filter':qid.rsplit('-',1)[1],'baseline_recall':r['native_recall'],'fallback':r['native_guard']['fallback_used']}
    times=collections.defaultdict(list)
    with (RESULTS/'timing.jsonl').open() as f:
        for line in f:
            r=json.loads(line)
            if r['ef']==640:times[r['id'],'noop' if r['label'].startswith('noop') else 'native'].append(r['request_ns'])
    for qid,row in rows.items():
        assert len(times[qid,'native'])==len(times[qid,'noop'])==4
        row['native_ns']=sum(times[qid,'native'])/4;row['noop_ns']=sum(times[qid,'noop'])/4
    for t in (-1,743,527,310,192,108,32):
        with (RESULTS/f'policy-qualification-{t}.jsonl').open() as f:
            for line in f:
                r=json.loads(line);row=rows[r['id']];row['observations']={o['checkpoint']:o for o in r['checkpoints']};row['proofs']=r['forced'];row['stop_ns']={}
                for cp in POINTS:
                    if str(cp) not in r['forced']:continue
                    p=r['policies'][str(POINTS.index(cp)+3)]
                    assert p['checkpoint']==cp and not p['fallback_used'];row['stop_ns'][cp]=p['request_ns']
    assert len(rows)==3150 and set(r['filter'] for r in rows.values())==set(FILTERS)
    return rows

def validate_policy(p):
    assert isinstance(p,dict) and set(p)=={'name','rules','rationale'}
    assert isinstance(p['name'],str) and 1<=len(p['name'])<=80 and isinstance(p['rationale'],str)
    assert isinstance(p['rules'],dict) and set(p['rules'])<=set(FILTERS)
    for filter_,clauses in p['rules'].items():
        assert isinstance(clauses,list) and len(clauses)<=3
        previous=0
        for clause in clauses:
            assert set(clause)=={'cp','conditions'} and type(clause['cp']) is int and clause['cp'] in POINTS and clause['cp']>previous;previous=clause['cp']
            assert isinstance(clause['conditions'],list) and len(clause['conditions'])<=4
            for c in clause['conditions']:
                assert isinstance(c,list) and len(c)==3 and c[0] in FEATURES and c[1] in ('>=','<=') and type(c[2]) in (int,float) and math.isfinite(c[2])
    return p

def choose(row,p):
    for clause in p['rules'].get(row['filter'],[]):
        cp=clause['cp'];o=row['observations'].get(cp)
        if o is None or o['qualifying_count']<10:continue
        if all(o.get(f) is not None and (o[f]>=v if op=='>=' else o[f]<=v) for f,op,v in clause['conditions']):
            assert str(cp) in row['proofs'];return cp
    return None

def evaluate(rows,p):
    validate_policy(p);groups=collections.defaultdict(list);folds=collections.defaultdict(list);losses=[];stops=0
    for qid,row in rows.items():
        cp=choose(row,p);recall=row['proofs'][str(cp)]['recall'] if cp else row['baseline_recall'];cost=row['stop_ns'][cp] if cp else row['noop_ns'];delta=recall-row['baseline_recall']
        if delta < -1e-12:losses.append({'anonymous_group':row['group'],'fold':row['fold'],'filter':row['filter'],'checkpoint':cp,'delta':delta})
        stops+=cp is not None;groups[row['filter']].append((recall,delta,cost,row['native_ns'],cp));folds[row['fold']].append((recall,delta,cp))
    per={f:{'queries':len(v),'recall':sum(x[0] for x in v)/len(v),'recall_losses':sum(x[1]<-1e-12 for x in v),'stops':sum(x[4] is not None for x in v),'cost_proxy_ms':sum(x[2] for x in v)/len(v)/1e6,'baseline_measured_ms':sum(x[3] for x in v)/len(v)/1e6} for f,v in groups.items()}
    proxy=sum(per[f]['cost_proxy_ms'] for f in FILTERS if f!='unfiltered')/6;native=sum(per[f]['baseline_measured_ms'] for f in FILTERS if f!='unfiltered')/6
    return {'quality_eligible_on_development':not losses and all(x['recall']>=.95-1e-12 for x in per.values()),'stops':stops,'loss_count':len(losses),'loss_examples':losses[:20],'per_filter':per,'fold_diagnostics':{str(f):{'queries':len(v),'losses':sum(x[1]<-1e-12 for x in v),'stops':sum(x[2] is not None for x in v)} for f,v in folds.items()},'cost_proxy_mean_ms':proxy,'parent_measured_mean_ms':native,'cost_proxy_ratio':proxy/native,'cost_limit':'Forced-stop and no-op serving times are from different qualification/timing phases. This is only a development surrogate, not measured new-policy latency or final selection evidence.'}

def bundle(rows):
    def number(x):return None if x is None else float(format(x,'.8g'))
    cases=[]
    for row in sorted(rows.values(),key=lambda x:(x['group'],FILTERS.index(x['filter']))):
        observations=[]
        for cp in POINTS:
            o=row['observations'].get(cp)
            if o is None:observations.append(None);continue
            proof=row['proofs'].get(str(cp))
            observations.append([o['qualifying_count'],number(o['tenth_distance']),number(o['frontier_gap']),o['top10_new_since_previous'],None if proof is None else round(proof['recall']*10),None if proof is None else round(row['stop_ns'][cp]/1000,2)])
        cases.append([row['group'],row['fold'],FILTERS.index(row['filter']),round(row['baseline_recall']*10),round(row['native_ns']/1000,2),round(row['noop_ns']/1000,2),*observations])
    return {'parent':'guarded non-iterative native640 on same original graph; exact top10 replacement on short outputs on all arms','objective':'zero observed per-query recall loss against guarded parent; >=.95 recall per filter; lower COMPLETE serving time including feature/no-stop and exact fallback cost','filters':FILTERS,'case_columns':['anonymous_development_group','development_fold','filter_index','guarded_parent_hits_of10','parent_measured_us','noop_measured_us','cp16','cp32','cp64'],'checkpoint_columns':['qualifying_count','tenth_distance','frontier_gap','top10_new_since_previous','forced_stop_hits_of10_or_null','forced_stop_measured_us_or_null'],'notes':['Null observation means unreached. Null proof forbids that stop. Features rounded in prompt; evaluator uses full saved precision.','No-stop time includes actual policy feature overhead and common guard. Stop times are real forced-rule serving costs but only a proxy for a new compiled rule.','All450 groups are exposed development. Five folds are grouped diagnostics, not independent validation.','Anonymous group/fold, future observations, proof hits and cost labels are evaluator information, never runtime features.','Do not identify or special-case individual queries. No text, vectors, source IDs or held-out cases are provided.'],'cases':cases}
