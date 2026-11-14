"""Three bounded, serial fresh Anthropic proposal rounds; development only."""
import datetime,hashlib,json,os,sys
from decimal import Decimal
from pathlib import Path
from data import load,bundle,evaluate,validate_policy,encoded,sha,FILTERS
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
sys.path.insert(0,str(ROOT/'trials/reviews-persistent-batch-proposal-v1'))
from proposal import provider_connection
MODEL='claude-sonnet-5-5';LIMIT=6000;CAP=Decimal(15)
SYSTEM='''You are FANNAgent proposing new executable early-stopping policies for filtered ANN.
Use only supplied DEVELOPMENT evidence. Goal: preserve every query's measured recall
against the GUARDED native640 parent and reduce complete request cost. All six scalar
filters remain; unfiltered is a control. An identical exact-completion guard wraps all
arms: short completed ANN results are replaced by exact filtered top10. Its cost matters.
Generate up to THREE different policies, or abstain, using only current causal features.
Return plain JSON: {"policies":[{"name":"...","rules":{"votes743":[{"cp":32,
"conditions":[["frontier_gap",">=",0.05]]}]},"rationale":"..."}],"notes":"..."}.
The example schema's rationale belongs inside each policy object, alongside name/rules.
Allowed rules keys: unfiltered,votes743,votes527,votes310,votes192,votes108,votes32.
Omitted filters continue. Each filter has at most3 clauses at cp16,32,64 in ascending
order, each with up to4 ANDed [feature,operator,finite-number] comparisons. Operators
are >= or <=. Features: qualifying_count,tenth_distance,frontier_gap,
top10_new_since_previous. A missing feature makes its comparison false. The host
always requires a reached checkpoint and >=10 qualifying candidates before any stop.
First satisfied clause stops; otherwise native continuation and completion guard.
No source IDs, anonymous group/fold IDs, result labels, future observations, time labels,
exact truth, or arbitrary code may be runtime features. No tools or extra requests.
All 450 vector groups are exposed development; fold scores are grouped diagnostics,
not independent validation. Policies must preserve recall query by query in ALL seven
conditions and have per-condition recall>=.95. At least one stop is needed to advance.
You may share similar clauses across filters, but return explicit predicate branches.
Stop/noop timings are real measured probes, only surrogates for a NEW compiled program;
fresh live serving measurements will decide final eligibility. Do not optimize distance
work as if it were latency. Be conservative around rounded prompt values: evaluator
uses full saved precision. You may return fewer than3 policies or an empty list to abstain.
'''
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,o):
    with p.open('xb') as f:f.write(encoded(o)+b'\n');f.flush();os.fsync(f.fileno())
def preflight():
    c,h=provider_connection(30)
    try:
        c.request('GET','/v1/models/'+MODEL,headers=h);r=c.getresponse();body=r.read(262144)
        assert r.status==200,'unavailable provider model';model=json.loads(body);assert model['id']==MODEL
        return {'utc':now(),'model':model['id'],'paid_requests':0,'pricing_url':'https://platform.claude.com/docs/en/models/sonnet-5-5/overview','input_usd_per_million':2,'output_usd_per_million':10,'credential':'existing local mini-swe-agent configuration, never persisted'}
    finally:c.close()
def run():
    scheduler=json.loads((BASE/'returns/job-22684501/scheduler-reported.json').read_text());assert scheduler['state']=='COMPLETED' and scheduler['exit_code']=='0:0'
    parent=json.loads((BASE/'freeze/guarded-parent-selection-v1.json').read_text());assert parent['scheduler_gate']=='passed' and parent['selected_parent_ef_search']==640
    approval=json.loads((HERE/'external-payload-approval.json').read_text())
    assert approval['approved'] is True and approval['destination']=='https://api.anthropic.com/v1/messages' and approval['max_rounds']==3 and approval['max_usd']==15
    rows=load();evidence=bundle(rows)
    if not (HERE/'provider-preflight.json').exists():save(HERE/'provider-preflight.json',preflight())
    spent=Decimal(0);policies=[];feedback=[];calls=0
    # No resume/retry: any existing attempt means this episode is already consumed.
    assert not any(path.is_dir() for path in HERE.glob('round-*')),'episode already started; inspect saved state instead of redispatching'
    for n in range(1,4):
        request={'model':MODEL,'max_tokens':LIMIT,'inference_geo':'global','service_tier':'standard_only','thinking':{'type':'between_tools'},'output_config':{'effort':'high'},'system':SYSTEM,'messages':[{'role':'user','content':encoded({'round':n,'evidence':evidence,'previous_development_feedback':feedback,'previous_proposals':policies}).decode()}]}
        payload=encoded(request);input_bound=len(payload)+8192;assert input_bound<=900000
        if n==1:assert hashlib.sha256(payload).hexdigest()==approval['first_round_payload_sha256']
        reserve=(Decimal(input_bound)*2+Decimal(LIMIT)*10)/1_000_000;assert spent+reserve<=CAP
        folder=HERE/f'round-{n}';folder.mkdir(mode=0o700)
        (folder/'request.json').write_bytes(payload)
        save(folder/'reservation.json',{'utc':now(),'round':n,'maximum_usd':str(reserve),'input_token_bound':input_bound,'output_token_bound':LIMIT,'request_sha256':hashlib.sha256(payload).hexdigest(),'parent_freeze_sha256':sha(BASE/'freeze/guarded-parent-selection-v1.json'),'driver_sha256':sha(Path(__file__))})
        c,h=provider_connection(180)
        try:
            c.request('POST','/v1/messages',body=payload,headers=h);reply=c.getresponse();raw=reply.read(2*1024*1024+1)
            assert len(raw)<=2*1024*1024
            (folder/'response.json').write_bytes(raw)
            assert reply.status==200,f'HTTP {reply.status}'
            response=json.loads(raw);usage=response['usage'];a=usage['input_tokens'];b=usage['output_tokens']
            assert type(a) is int and type(b) is int and 0<=a<=input_bound and 0<=b<=LIMIT and response['model']==MODEL
            assert usage.get('inference_geo','global')=='global' and usage.get('service_tier','standard')=='standard' and not usage.get('cache_creation_input_tokens',0) and not usage.get('cache_read_input_tokens',0)
            charge=(Decimal(a)*2+Decimal(b)*10)/1_000_000;assert charge<=reserve;spent+=charge;calls+=1
            save(folder/'settlement.json',{'utc':now(),'model':response['model'],'input_tokens':a,'output_tokens':b,'actual_usd':str(charge),'response_sha256':hashlib.sha256(raw).hexdigest(),'stop_reason':response.get('stop_reason')})
        except BaseException as exc:
            save(folder/'uncertain.json',{'utc':now(),'reason':str(exc),'reserved_usd':str(reserve),'retry':False})
            raise
        finally:c.close()
        text=''.join(x['text'] for x in response['content'] if x['type']=='text').strip()
        if text.startswith('```'):text=text.split('\n',1)[1].rsplit('```',1)[0].strip()
        evaluations=[];proposed=[]
        try:
            value=json.loads(text);assert isinstance(value,dict) and isinstance(value.get('policies'),list) and len(value['policies'])<=3
            for j,p in enumerate(value['policies']):
                try:
                    validate_policy(p);metrics=evaluate(rows,p);semantic=hashlib.sha256(encoded(p['rules'])).hexdigest()
                    record={'round':n,'index':j,'policy_sha256':semantic,'policy':p,'metrics':metrics};proposed.append(record);evaluations.append({'index':j,'policy_sha256':semantic,'metrics':metrics})
                except (AssertionError,ValueError,TypeError,KeyError,OverflowError) as error:evaluations.append({'index':j,'rejected':'invalid executable schema','error_type':type(error).__name__})
            notes=value.get('notes','')
        except (AssertionError,ValueError,TypeError,KeyError) as error:
            value={'policies':None};notes='Invalid response schema';evaluations=[{'rejected':'invalid response schema','error_type':type(error).__name__}]
        save(folder/'parsed-proposals.json',{'policies':proposed,'notes':notes})
        save(folder/'development-feedback.json',{'round':n,'evaluations':evaluations,'feedback_scope':'development only; no held-out outcomes','final_live_latency_available':False})
        policies.extend(p['policy'] for p in proposed);feedback.append({'round':n,'evaluations':evaluations})
        print(json.dumps({'round':n,'paid_calls':calls,'spent_usd':str(spent),'valid_policies':len(proposed),'quality_eligible':sum(p['metrics']['quality_eligible_on_development'] and p['metrics']['stops']>0 for p in proposed),'loss_counts':[p['metrics']['loss_count'] for p in proposed]}),flush=True)
        if value.get('policies')==[]:break
    all_proposals=[]
    for p in sorted(HERE.glob('round-*/parsed-proposals.json')):all_proposals+=json.loads(p.read_text())['policies']
    feasible=[p for p in all_proposals if p['metrics']['quality_eligible_on_development'] and p['metrics']['stops']>0]
    save(HERE/'episode-summary.json',{'status':'generation_complete_pending_live_candidate_measurement' if feasible else 'bounded_generation_no_development_eligible_policy','model':MODEL,'paid_calls':calls,'spent_usd':str(spent),'cap_usd':str(CAP),'proposals':len(all_proposals),'distinct_semantics':len({p['policy_sha256'] for p in all_proposals}),'development_eligible':len(feasible),'policies':all_proposals,'validation_test_outcomes_opened':False,'final_policy_selected':False,'next':'compile and qualify new programs; measure complete serving cost on development, then freeze candidate/baseline pool before one validation batch'})
    save(HERE/'proposal-pool-freeze.json',{'status':'generated pool frozen before validation','episode_summary_sha256':sha(HERE/'episode-summary.json'),'rounds':{p.parent.name:sha(p) for p in sorted(HERE.glob('round-*/parsed-proposals.json'))},'parent_freeze_sha256':sha(BASE/'freeze/guarded-parent-selection-v1.json'),'validation_test_outcomes_opened':False,'actual_new_policy_serving_cost':'pending live qualification/measurement; surrogate is not final selection'})
    print(json.dumps({'status':'episode_completed','calls':calls,'spent_usd':str(spent),'proposals':len(all_proposals),'development_eligible':len(feasible)}),flush=True)
if __name__=='__main__':run()
