"""Development-only guarded qualification, paired timing and parent selection."""
import hashlib,json
from contextlib import ExitStack
from time import perf_counter_ns
from common import THRESHOLDS,CHECKPOINTS,capture,matches,require,sha,threshold,write
from guard import guarded_request,fallback_statement
from support import reader,count_search,valid,check_plan
GRID=(640,1000,2048,4096,8192)
SEED='reviews-common-guard-development-v1'

def perform(counter,ann,exact,q,passing):
    def reserve(operation):
        require(counter['total']<225000,'guard experiment attempt cap')
        counter['total']+=1;counter[operation]=counter.get(operation,0)+1
    return guarded_request(ann,exact,q,passing,reserve)

def validate(result,q,eligible,truth,initial_expected=None):
    require(result['required_count']==min(10,len(eligible)),'wrong required count')
    require(result['fallback_used']==(len(result['initial'])<result['required_count']),'guard decision differs')
    if initial_expected is not None:require(matches(result['initial'],initial_expected),'initial ANN changed')
    valid(result['initial'],q,eligible,truth)
    score=valid(result['output'],q,eligible,truth)
    require(len(result['output'])==result['required_count'],'guarded result incomplete')
    if result['fallback_used']:
        exact=dict(truth)
        require(all(i in exact and abs(d-exact[i])<=1e-6 for i,d in result['output']),'fallback differs from exact reference')
        require(score==1,'fallback recall differs')
    else:require(matches(result['output'],result['initial']),'nonfallback changed result')
    require(result['request_ns']==result['ann_ns']+result['fallback_ns']+result['guard_and_construction_ns'] and min(result['request_ns'],result['ann_ns'])>0 and result['guard_and_construction_ns']>=0,'invalid timer accounting')
    if not result['fallback_used']:require(result['fallback_ns']==0,'unexpected exact time')
    return score

def exact_plan(conn,q):
    sql,params=fallback_statement(q)
    plan=conn.execute('EXPLAIN (FORMAT JSON) '+sql,params,prepare=False).fetchone()[0][0]['Plan']
    scans=[]
    def visit(n):
        if 'Scan' in n['Node Type']:scans.append(n)
        for child in n.get('Plans',[]):visit(child)
    visit(plan);require(len(scans)==1 and scans[0]['Node Type']=='Seq Scan' and scans[0]['Relation Name']=='reviews','fallback is not exact Seq Scan')
    return plan

def run_grid(Backend,args,queries,eligible,prior,prior_sweep,counter):
    cache={};quality={};timing={};setup=[]
    with (args.output/'quality.jsonl').open('x') as out:
        for ef in GRID:
            args.parent_ef=ef;conditions={}
            for t in THRESHOLDS:
                cases=[q for q in queries if threshold(q)==t];passing=len(eligible[t]);scores=[];fallbacks=0
                started=perf_counter_ns()
                with reader(Backend,args,t,passing,exact=True) as exact,reader(Backend,args,t,passing) as native,reader(Backend,args,t,passing,6) as noop:
                    setup.append({'phase':'quality','ef':ef,'filter':t,'connections':3,'open_attach_ns':perf_counter_ns()-started})
                    plans={'ann':check_plan(native,cases[0]),'exact_guard':exact_plan(exact,cases[0])};write(args.output/f'plans-{ef}-{t}.json',plans)
                    require(native.execute("SELECT current_setting('hnsw.ef_search'),current_setting('hnsw.iterative_scan')").fetchone()==(str(ef),'off'),'wrong ANN settings')
                    for j,q in enumerate(cases):
                        ref=prior[q['id']]['exact'];expected=prior_sweep[ef,q['id']]['output']
                        a=perform(counter,native,exact,q,passing);b=perform(counter,noop,exact,q,passing)
                        cp=noop.execute('SELECT fannagent.confirm_last()').fetchone()[0]
                        score=validate(a,q,eligible[t],ref,expected);validate(b,q,eligible[t],ref,expected)
                        require(cp==0 and matches(a['output'],b['output']) and a['fallback_used']==b['fallback_used'],'native/agent-noop guarded parity differs')
                        cache[ef,q['id']]=a;scores.append(score);fallbacks+=a['fallback_used']
                        out.write(json.dumps({'id':q['id'],'ef':ef,'filter':t,'native_guard':a,'agent_noop_guard':b,'native_recall':score,'noop_checkpoint':cp},allow_nan=False)+'\n')
                    out.flush();closing=perf_counter_ns()
                setup[-1]['close_ns']=perf_counter_ns()-closing
                conditions[str(t)]={'queries':450,'mean_recall':sum(scores)/450,'complete':450,'fallbacks':fallbacks,'adequate':sum(scores)/450>=.95}
                print(json.dumps({'phase':'guard_quality','ef':ef,'filter':t,**conditions[str(t)],'attempts':counter['total']}),flush=True)
            quality[str(ef)]=conditions
    # Two mirrored epochs, four reader labels, balanced predecessor/query order.
    labels=('native-A','native-B','noop-A','noop-B');base=(0,1,3,2)
    with (args.output/'timing.jsonl').open('x') as out:
        for epoch in range(2):
            for ef in GRID if epoch==0 else reversed(GRID):
                args.parent_ef=ef;ei=GRID.index(ef);filters=list(THRESHOLDS);rotation=(ei+epoch)%7;filters=filters[rotation:]+filters[:rotation]
                for t in filters:
                    ti=THRESHOLDS.index(t);cases=[q for q in queries if threshold(q)==t]
                    cases.sort(key=lambda q:hashlib.sha256((SEED+':'+q['id'].rsplit('-',1)[0]).encode()).hexdigest())
                    if epoch:cases.reverse()
                    passing=len(eligible[t]);started=perf_counter_ns()
                    with ExitStack() as stack:
                        exact=stack.enter_context(reader(Backend,args,t,passing,exact=True))
                        readers={label:stack.enter_context(reader(Backend,args,t,passing,6 if label.startswith('noop') else None)) for label in labels}
                        opened=perf_counter_ns();warm_begin=opened
                        for label,c in readers.items():
                            for q in cases[:10]:
                                result=perform(counter,c,exact,q,passing)
                                require(matches(result['output'],cache[ef,q['id']]['output']),'warmup output differs')
                        warm_end=perf_counter_ns()
                        setup.append({'phase':'timing','ef':ef,'filter':t,'epoch':epoch,'connections':5,'open_attach_ns':opened-started,'warmup_ns':warm_end-warm_begin,'warmup_requests':40})
                        for j,q in enumerate(cases):
                            offset=(j+epoch+ti+ei)%4;order=[labels[(v+offset)%4] for v in base]
                            if epoch:order.reverse()
                            for position,label in enumerate(order):
                                result=perform(counter,readers[label],exact,q,passing)
                                expected=cache[ef,q['id']]
                                require(matches(result['initial'],expected['initial']) and matches(result['output'],expected['output']) and result['fallback_used']==expected['fallback_used'],'timed output/guard identity differs')
                                out.write(json.dumps({'id':q['id'],'ef':ef,'filter':t,'epoch':epoch,'label':label,'order':order,'position':position,'predecessor':order[position-1] if position else None,**result},allow_nan=False)+'\n')
                                stats=timing.setdefault((ef,t,label),[]);stats.append(result['request_ns'])
                        out.flush();closing=perf_counter_ns()
                    setup[-1]['close_ns']=perf_counter_ns()-closing
                    print(json.dumps({'phase':'guard_timing','epoch':epoch,'ef':ef,'filter':t,'attempts':counter['total']}),flush=True)
    grid=[]
    for ef in GRID:
        eligible_parent=all(c['adequate'] for c in quality[str(ef)].values())
        means={str(t):sum(timing[ef,t,'native-A']+timing[ef,t,'native-B'])/(450*2*2) for t in THRESHOLDS}
        score=sum(means[str(t)] for t in THRESHOLDS if t>=0)/6
        controls={str(t):{family:sum(timing[ef,t,family+'-A'])/sum(timing[ef,t,family+'-B']) for family in ('native','noop')} for t in THRESHOLDS}
        grid.append({'ef':ef,'adequate':eligible_parent,'equal_scalar_filter_mean_ns':score,'per_condition_native_mean_ns':means,'identical_code_mean_ratios':controls,'quality':quality[str(ef)]})
    candidates=[r for r in grid if r['adequate']]
    chosen=None
    if candidates:
        best=min(c['equal_scalar_filter_mean_ns'] for c in candidates)
        chosen=max(c['ef'] for c in candidates if c['equal_scalar_filter_mean_ns']<=best*1.01)
    selection={'status':'selected' if chosen else 'no_adequate_guarded_parent','selected_ef_search':chosen,'grid':grid,'selection':'lowest measured native guard equal-six-filter mean; within1% choose larger ef','timing_claim':'development selection on one allocation, not confirmatory causal inference','independent_groups':450,'setup':setup,'provider_calls':0,'validation_test_queries':0}
    write(args.output/'selection.json',selection)
    return chosen,cache

def chosen_stop(cap,arm):
    if arm in (3,4,5):
        target=CHECKPOINTS[arm-3]
        return target if any(o['checkpoint']==target and o['qualifying_count']>=10 for o in cap['checkpoints']) else 0
    for o in cap['checkpoints']:
        cp=o['checkpoint'];gap=o['frontier_gap'];tenth=o['tenth_distance']
        if o['qualifying_count']<10 or gap is None:continue
        if arm==1 and cp==32 and gap>=.05:return cp
        if arm==2 and ((cp==16 and gap>=.02 and tenth<=.44) or(cp==32 and gap>=.025 and tenth<=.38) or(cp==64 and gap>=.05)):return cp
    return 0

def qualify_selected(Backend,args,queries,eligible,prior,counter,cache):
    from common import search
    ef=args.parent_ef;summary={}
    for t in THRESHOLDS:
        cases=[q for q in queries if threshold(q)==t];passing=len(eligible[t]);proof_count=local_count=0
        with ExitStack() as stack:
            exact=stack.enter_context(reader(Backend,args,t,passing,exact=True));shadow=stack.enter_context(reader(Backend,args,t,passing,0));local=stack.enter_context(reader(Backend,args,t,passing,local=True))
            live={arm:stack.enter_context(reader(Backend,args,t,passing,arm)) for arm in (1,2,3,4,5)}
            with (args.output/f'policy-qualification-{t}.jsonl').open('x') as out:
                for j,q in enumerate(cases):
                    truth,_=count_search(counter,'reference_exact',search,exact,q,exact=True)
                    require(matches(truth,prior[q['id']]['exact']),'exact truth changed')
                    cap=count_search(counter,'capture',capture,shadow,q,f'guard-capture-{t}-{j}')
                    require(matches(cap['output'],cache[ef,q['id']]['initial']),'capture changed ANN')
                    if j<10:
                        lc=count_search(counter,'local_capture',capture,local,q,f'guard-local-{t}-{j}')
                        require(matches(lc['output'],cap['output']),'local/shared output differs')
                        for a,b in zip(lc['checkpoints'],cap['checkpoints'],strict=True):require({k:v for k,v in a.items() if k!='collection_ns'}=={k:v for k,v in b.items() if k!='collection_ns'},'local/shared features differ')
                        local_count+=1
                    proofs={}
                    for obs in cap['checkpoints']:
                        cp=obs['checkpoint']
                        if obs['qualifying_count']<10:continue
                        f=count_search(counter,'forced_trace',capture,shadow,q,f'guard-forced-{t}-{j}-{cp}',budget=obs['budget'])
                        prefix=lambda c:[(e['index'],e['features']) for k,e in sorted(c['states'].items()) if k<=cp]
                        require(prefix(f)==prefix(cap),'forced prefix differs')
                        require(len(f['output'])==10 and abs(max(d for _,d in f['output'])-obs['tenth_distance'])<=1e-6,'forced checkpoint output differs')
                        proofs[str(cp)]={'output':f['output'],'recall':valid(f['output'],q,eligible[t],truth)};proof_count+=1
                    guarded={}
                    for arm,c in live.items():
                        result=perform(counter,c,exact,q,passing);cp=c.execute('SELECT fannagent.confirm_last()').fetchone()[0]
                        expected_cp=chosen_stop(cap,arm);require(cp==expected_cp,'policy first stop differs')
                        expected_initial=proofs[str(cp)]['output'] if cp else cap['output']
                        score=validate(result,q,eligible[t],truth,expected_initial)
                        if cp:require(not result['fallback_used'],'full policy stop unexpectedly triggered guard')
                        else:require(matches(result['output'],cache[ef,q['id']]['output']),'declined policy guard differs from native')
                        guarded[str(arm)]={'checkpoint':cp,'recall':score,**result}
                    out.write(json.dumps({'id':q['id'],'filter':t,'ef':ef,'checkpoints':cap['checkpoints'],'forced':proofs,'policies':guarded},allow_nan=False)+'\n');out.flush()
        summary[str(t)]={'queries':450,'local_shared_checks':local_count,'forced_proofs':proof_count,'policy_paths_verified':2250}
        print(json.dumps({'phase':'selected_policy_qualification','ef':ef,'filter':t,'attempts':counter['total']}),flush=True)
    return summary
