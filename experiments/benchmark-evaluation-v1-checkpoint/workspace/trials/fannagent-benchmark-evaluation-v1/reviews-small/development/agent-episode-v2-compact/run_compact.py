"""Versioned compact/tool-assisted continuation: global requests2/3, shared $15 cap."""
import datetime,fcntl,hashlib,json,os,sys
from decimal import Decimal
from pathlib import Path
from data import load,encoded,sha,validate_policy
from compact import focused_bundle,evaluated_feedback
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];OLD=HERE.parent/'agent-episode-v1';ROOT=BASE.parents[2]
sys.path.insert(0,str(ROOT/'trials/reviews-persistent-batch-proposal-v1'))
from proposal import provider_connection
MODEL='claude-sonnet-5-5';CAP=Decimal(15);OUTPUT=6000
SYSTEM='''You are FANNAgent, developing causal filtered-ANN stopping policies using only
450 exposed DEVELOPMENT vector groups. Keep ALL SIX scalar filters plus unfiltered.
Parent is guarded non-iterative native640 on the unchanged original graph: completed
ANN outputs shorter than10 are replaced with exact filtered top10 on every arm.
Goal: zero observed per-query recall losses versus that guarded parent, per-filter
mean recall>=.95, and improved COMPLETE serving latency. No population guarantee.

A previous raw-table request abstained. This version gives compact FILTER-FOCUSED
feature distributions and a bounded local evaluator. Univariate safe/lossy bin counts
are NOT proofs that a conjunction is safe. Use evaluate_policies ONCE with a batch
of at most THREE speculative policies: failures are useful DEVELOPMENT feedback,
not deployed policies. The tool checks all3150 cases at full feature precision and
returns per-filter/fold metrics and bounded counterexamples. There is then ONE final
provider request to refine/export up to THREE policies. No shell, searches or arbitrary
code. Maximum6 scored authored proposals in this continuation, not an open-ended search.

Policy schema (including tool input):
{"name":"short name","rules":{"votes108":[{"cp":32,"conditions":[
["frontier_gap",">=",0.05],["tenth_distance","<=",0.38]]}]},"rationale":"..."}.
Rules keys: unfiltered,votes743,votes527,votes310,votes192,votes108,votes32.
Each filter has at most3 clauses at checkpoints16/32/64 in ascending order, max4
ANDed comparisons per clause. Allowed comparisons >= and <= with finite numbers.
Features ONLY: qualifying_count,tenth_distance,frontier_gap,top10_new_since_previous.
Host requires reached checkpoint and at least10 qualifying candidates. Missing
features make their comparison false. First satisfied clause stops; otherwise native
continuation plus common completion guard. Omitted filters simply continue; they stay
in ALL quality/performance assessments. You do not need to force a stop in every
filter. No anonymous group/fold IDs, outcome labels, future observations, costs or
exact truth may be runtime features. Branches may differ by published filter identity.

The tool's cost is a SURROGATE from measured stop/noop probes, not live timing of your
new program. Final candidates require compilation/live qualification and complete
serving-cost measurement before validation selection. Grouped folds are diagnostic,
not independent holdouts. No validation/test data is available. Guard and recall
criteria cannot be changed. Do not claim failure examples are the whole evaluator.
After tool feedback, output plain JSON {"policies":[POLICY,...],"notes":"..."}.
An empty list is a valid final abstention, but use the bounded evaluator to investigate
plausible conservative clauses first rather than equating uncertainty with impossibility.
'''
TOOL={'name':'evaluate_policies','description':'Replay at most3 bounded causal JSON policies on every frozen development case only. No searches/provider calls or holdout access. Gives exact saved-output recall checks and labeled serving-cost surrogate.','input_schema':{'type':'object','properties':{'policies':{'type':'array','maxItems':3,'items':{'type':'object'}}},'required':['policies'],'additionalProperties':False}}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,value):
    with path.open('xb') as f:f.write(encoded(value)+b'\n');f.flush();os.fsync(f.fileno())
def atom(path,value):
    temp=path.with_suffix('.pending');temp.write_bytes(encoded(value)+b'\n');os.replace(temp,path)
def parse_text(response):
    text=''.join(b['text'] for b in response['content'] if b['type']=='text').strip()
    if text.startswith('```'):text=text.split('\n',1)[1].rsplit('```',1)[0].strip()
    value=json.loads(text);assert isinstance(value,dict) and isinstance(value.get('policies'),list) and len(value['policies'])<=3
    return value['policies']
def score_batch(rows,values,stage):
    assert isinstance(values,list) and len(values)<=3
    records=[];feedback=[]
    for index,p in enumerate(values):
        try:
            validate_policy(p);evaluation=evaluated_feedback(rows,p);semantic=hashlib.sha256(encoded(p['rules'])).hexdigest()
            records.append({'stage':stage,'index':index,'policy':p,'policy_sha256':semantic,'evaluation':evaluation})
            feedback.append({'index':index,'policy_sha256':semantic,**evaluation})
        except (AssertionError,TypeError,ValueError,KeyError,OverflowError) as error:
            feedback.append({'index':index,'rejected':'invalid bounded causal schema','error_type':type(error).__name__})
    return records,feedback

def run():
    lock=(HERE/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not any(p.is_dir() for p in HERE.glob('request-*')),'Already dispatched or reserved; no automatic retry'
    old=json.loads((OLD/'episode-verification.json').read_text());assert old['paid_calls']==1 and old['cost_usd']=='0.561208'
    approval=json.loads((HERE/'continuation-authorization.json').read_text());assert approval['remaining_requests']==2 and approval['original_cap_usd']==15 and approval['destination']=='https://api.anthropic.com/v1/messages'
    parent=json.loads((BASE/'freeze/guarded-parent-selection-v1.json').read_text());assert parent['scheduler_gate']=='passed' and parent['selected_parent_ef_search']==640
    rows=load();compact=focused_bundle(rows);assert hashlib.sha256(encoded(compact)+b'\n').hexdigest()==sha(HERE/'compact-evidence.json')
    ledger={'original_cap_usd':15,'max_total_paid_requests':3,'prior_verification_sha256':sha(OLD/'episode-verification.json'),'calls':[{'global_request':1,'status':'settled','actual_usd':old['cost_usd'],'source':'agent-episode-v1/round-1/settlement.json'}]}
    ledger_path=HERE/'shared-budget-ledger.json';save(ledger_path,ledger)
    initial=encoded({'method':'compact filter-focused evidence and bounded replay tool, revision2','development_evidence':compact,'instruction':'Use your one allowed evaluator batch now for at most3 tentative policies. We will return all-development full-precision checks and counterexamples in the last remaining request.'}).decode()
    messages=[{'role':'user','content':initial}];pool=[]
    for global_request in (2,3):
        request={'model':MODEL,'max_tokens':OUTPUT,'inference_geo':'global','service_tier':'standard_only','thinking':{'type':'between_tools'},'output_config':{'effort':'high'},'system':SYSTEM,'tools':[TOOL],'messages':messages}
        payload=encoded(request);bound=len(payload)+8192;assert bound<=900000
        reservation=(Decimal(bound)*2+Decimal(OUTPUT)*10)/1_000_000
        committed=sum((Decimal(c.get('actual_usd',c.get('reserved_usd','0'))) for c in ledger['calls']),Decimal(0))
        assert len(ledger['calls'])<3 and committed+reservation<=CAP and all(c['status']=='settled' for c in ledger['calls'])
        folder=HERE/f'request-{global_request}';folder.mkdir(mode=0o700);(folder/'request.json').write_bytes(payload)
        call={'global_request':global_request,'status':'reserved','reserved_usd':str(reservation),'input_token_bound':bound,'output_token_bound':OUTPUT,'request_sha256':hashlib.sha256(payload).hexdigest(),'utc':now()};ledger['calls'].append(call);atom(ledger_path,ledger)
        save(folder/'reservation.json',call)
        c,h=provider_connection(180)
        try:
            c.request('POST','/v1/messages',body=payload,headers=h);reply=c.getresponse();raw=reply.read(2*1024*1024+1);assert len(raw)<=2*1024*1024
            (folder/'response.json').write_bytes(raw);assert reply.status==200,f'HTTP{reply.status}'
            response=json.loads(raw);usage=response['usage'];a=usage['input_tokens'];b=usage['output_tokens']
            assert type(a) is int and type(b) is int and 0<=a<=bound and 0<=b<=OUTPUT and response['model']==MODEL
            assert usage.get('inference_geo','global')=='global' and usage.get('service_tier','standard')=='standard' and not usage.get('cache_creation_input_tokens',0) and not usage.get('cache_read_input_tokens',0)
            charge=(Decimal(a)*2+Decimal(b)*10)/1_000_000;assert charge<=reservation
            call.update(status='settled',actual_usd=str(charge),input_tokens=a,output_tokens=b,response_sha256=hashlib.sha256(raw).hexdigest(),stop_reason=response.get('stop_reason'))
            atom(ledger_path,ledger);save(folder/'settlement.json',call)
        except BaseException as error:
            call.update(status='uncertain',reason=str(error));atom(ledger_path,ledger);save(folder/'uncertain.json',call);raise
        finally:c.close()
        tool_uses=[block for block in response['content'] if block['type']=='tool_use'];results=[];feedback=[];records=[]
        if tool_uses:
            # Only the first declared batch is executed; extra tool calls get a limit error.
            for tool_index,block in enumerate(tool_uses):
                try:
                    assert tool_index==0 and block['name']=='evaluate_policies' and isinstance(block['input'],dict) and set(block['input'])=={'policies'}
                    rec,fb=score_batch(rows,block['input']['policies'],f'global-request-{global_request}-tool');records+=rec;feedback+=fb
                    content={'status':'evaluated','candidate_count':len(block['input']['policies']),'all_development_cases':3150,'evaluations':fb,'tool_budget_remaining':0,'no_new_ann_exact_or_provider_calls':True}
                    results.append({'type':'tool_result','tool_use_id':block['id'],'content':encoded(content).decode()})
                except (AssertionError,TypeError,ValueError,KeyError) as error:
                    results.append({'type':'tool_result','tool_use_id':block['id'],'is_error':True,'content':encoded({'error':'single batch of at most3 bounded JSON policies only','error_type':type(error).__name__}).decode()})
        else:
            try:
                values=parse_text(response);records,feedback=score_batch(rows,values,f'global-request-{global_request}-text')
            except (AssertionError,TypeError,ValueError,KeyError) as error:feedback=[{'rejected':'invalid response schema','error_type':type(error).__name__}]
        pool+=records
        save(folder/'evaluated-proposals.json',{'records':records,'feedback':feedback,'tool_uses_requested':len(tool_uses),'max_batches_executed':1 if tool_uses else 0,'no_holdout_access':True})
        print(json.dumps({'global_request':global_request,'tool_uses':len(tool_uses),'valid_authored_policies':len(records),'development_eligible':sum(r['evaluation']['metrics']['quality_eligible_on_development'] and r['evaluation']['metrics']['stops']>0 for r in records),'total_spent_including_first_usd':str(sum(Decimal(x['actual_usd']) for x in ledger['calls']))}),flush=True)
        if global_request==2:
            followup={'type':'text','text':encoded({'remaining_provider_requests_after_this':0,'instruction':'This is the final request under the original3-request cap. Return plain JSON policies (up to3) and notes; do NOT request another evaluator call. Refine against the exact feedback. It is legal to stop on a subset of predicates and continue on all others; all six filters remain in evaluation. No safety relaxation or fabricated live speedup.','feedback_if_no_tool':feedback if not tool_uses else None}).decode()}
            messages=messages+[{'role':'assistant','content':response['content']},{'role':'user','content':results+[followup]}]
    eligible=[r for r in pool if r['evaluation']['metrics']['quality_eligible_on_development'] and r['evaluation']['metrics']['stops']>0]
    total=sum((Decimal(x['actual_usd']) for x in ledger['calls']),Decimal(0));assert len(ledger['calls'])==3 and total<=15 and len(pool)<=6
    save(HERE/'continuation-summary.json',{'status':'candidates_pending_live_qualification' if eligible else 'bounded_continuation_no_development_eligible_policy','method_revision':'compact/filter-focused evidence plus single bounded tool batch, then final refinement','calls_this_revision':2,'total_calls_original_allowance':3,'total_usd_original_allowance':str(total),'original_cap_usd':15,'authored_valid_policy_records':len(pool),'distinct_semantics':len({r['policy_sha256'] for r in pool}),'development_eligible_records':len(eligible),'policies':pool,'validation_test_outcomes_opened':False,'new_policy_live_serving_cost':'not measured; proxy not final selection'})
    save(HERE/'proposal-pool-freeze.json',{'status':'pool frozen before validation','summary_sha256':sha(HERE/'continuation-summary.json'),'all_authored_programs_including_tool_probes_retained':True,'parent_freeze_sha256':sha(BASE/'freeze/guarded-parent-selection-v1.json'),'guard_source_sha256':parent['guard_source_sha256'],'validation_test_outcomes_opened':False,'actual_program_latency_qualification':'pending'})
    print(json.dumps({'status':'continuation_complete','total_paid_requests':3,'total_usd':str(total),'valid_policy_records':len(pool),'development_eligible':len(eligible)}),flush=True)
if __name__=='__main__':run()
