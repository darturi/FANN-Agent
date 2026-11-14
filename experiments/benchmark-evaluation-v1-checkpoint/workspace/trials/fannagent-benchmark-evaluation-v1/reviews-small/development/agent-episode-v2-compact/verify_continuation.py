"""Independent receipt reconciliation and explicit single-fence envelope recovery.
No provider calls or parameter edits. Original strict-parser disposition is retained.
"""
import json,re,hashlib
from decimal import Decimal
from pathlib import Path
from data import load,sha,encoded,FILTERS
from compact import evaluated_feedback
from run_compact import score_batch
HERE=Path(__file__).resolve().parent

def main():
    pre=json.loads((HERE/'preflight.json').read_text())
    for n,h in pre['sha256'].items():assert sha(HERE/n)==h
    rows=load();ledger=json.loads((HERE/'shared-budget-ledger.json').read_text());assert len(ledger['calls'])==3
    total=Decimal('0.561208');pool=[];checks=[]
    for index in (2,3):
        folder=HERE/f'request-{index}';call=ledger['calls'][index-1];reservation=json.loads((folder/'reservation.json').read_text());settlement=json.loads((folder/'settlement.json').read_text())
        assert call==settlement and call['status']=='settled' and sha(folder/'request.json')==call['request_sha256']==reservation['request_sha256'] and sha(folder/'response.json')==call['response_sha256']
        request=json.loads((folder/'request.json').read_text());response=json.loads((folder/'response.json').read_text());usage=response['usage']
        assert request['model']==response['model']=='claude-sonnet-5-5' and response['stop_reason'] in ('end_turn','tool_use')
        charge=(Decimal(usage['input_tokens'])*2+Decimal(usage['output_tokens'])*10)/1_000_000
        assert charge==Decimal(call['actual_usd'])<=Decimal(reservation['reserved_usd']) and usage['output_tokens']<=6000
        total+=charge
        if index==2:
            tools=[b for b in response['content'] if b['type']=='tool_use'];assert len(tools)==1 and tools[0]['name']=='evaluate_policies'
            values=tools[0]['input']['policies'];stage='global-request-2-tool'
        else:
            text=''.join(b['text'] for b in response['content'] if b['type']=='text')
            blocks=re.findall(r'```json\s*\n(.*?)\n```',text,re.S);assert len(blocks)==1
            final=json.loads(blocks[0]);assert set(final)=={'policies','notes'}
            values=final['policies'];stage='global-request-3-fenced-json-envelope-recovery'
            (folder/'recovered-json.json').write_bytes(encoded(final)+b'\n')
        records,feedback=score_batch(rows,values,stage);assert len(records)==len(values)==3 and len(feedback)==3
        for r in records:
            assert r['evaluation']==evaluated_feedback(rows,r['policy'])
            m=r['evaluation']['metrics'];assert set(m['per_filter'])==set(FILTERS) and all(v['queries']==450 for v in m['per_filter'].values())
        if index==2:
            original=json.loads((folder/'evaluated-proposals.json').read_text());assert records==original['records'] and feedback==original['feedback']
        else:
            (folder/'recovered-evaluated-proposals.json').write_bytes(encoded({'records':records,'feedback':feedback,'method':'Extract exactly one JSON fenced block from saved response. No policy edits, no new generation; original strict-parser rejection retained.','response_sha256':sha(folder/'response.json')})+b'\n')
        pool+=records;checks.append({'global_request':index,'input_tokens':usage['input_tokens'],'output_tokens':usage['output_tokens'],'usd':str(charge),'request_response_hashes':'passed','authored_records':len(records)})
    assert total<=15 and len(pool)==6
    unique={}
    for r in pool:
        unique.setdefault(r['policy_sha256'],r)
    eligible=[r for r in unique.values() if r['evaluation']['metrics']['quality_eligible_on_development'] and r['evaluation']['metrics']['stops']>0]
    verification={'status':'verified_with_explicit_final_response_envelope_recovery','original_driver_summary_retained':True,'no_additional_provider_calls':True,'paid_requests_this_revision':2,'total_paid_requests':3,'total_usd':str(total),'original_cap_usd':15,'calls':checks,'all_record_replays':'passed','development_cases_per_policy':3150,'development_groups':450,'condition_count':7,'authored_policy_records':6,'distinct_policy_semantics':len(unique),'eligible_distinct_policies':len(eligible),'validation_test_outcomes_opened':False,'live_new_policy_timing':'pending','parser_amendment':'Original parser rejected leading prose plus a JSON fence. Recovery accepts exactly one explicitly fenced JSON object and validates unchanged bounded policy programs. No further model request or threshold editing.'}
    (HERE/'continuation-verification.json').write_bytes(encoded(verification)+b'\n')
    final={'status':'verified_candidates_pending_live_qualification','verification_sha256':sha(HERE/'continuation-verification.json'),'original_driver_summary_sha256':sha(HERE/'continuation-summary.json'),'total_paid_requests':3,'total_usd_original_allowance':str(total),'original_cap_usd':15,'all_authored_policy_records':pool,'distinct_semantics':len(unique),'eligible_distinct_policies':[{'policy_sha256':r['policy_sha256'],'policy':r['policy'],'evaluation':r['evaluation']} for r in eligible],'validation_test_outcomes_opened':False,'final_policy_selected':False,'new_policy_live_serving_cost':'not measured; proxy not final selection'}
    (HERE/'reconciled-summary.json').write_bytes(encoded(final)+b'\n')
    (HERE/'reconciled-pool-freeze.json').write_bytes(encoded({'status':'all authored programs frozen before validation','summary_sha256':sha(HERE/'reconciled-summary.json'),'verification_sha256':sha(HERE/'continuation-verification.json'),'parent_freeze_sha256':sha(HERE.parents[1]/'freeze/guarded-parent-selection-v1.json'),'six_authored_records_including_tool_probes':True,'all_failures_and_duplicate_retained':True,'final_json_envelope_recovery_recorded':True,'validation_test_outcomes_opened':False})+b'\n')
    print(json.dumps(verification,indent=2))
    for r in unique.values():
        m=r['evaluation']['metrics'];print(json.dumps({'name':r['policy']['name'],'losses':m['loss_count'],'stops':m['stops'],'eligible':m['quality_eligible_on_development'],'surrogate_ratio':m['cost_proxy_ratio'],'per_filter_stops':{f:v['stops'] for f,v in m['per_filter'].items()}}))
if __name__=='__main__':main()
