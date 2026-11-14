"""One serving completion guard for native, no-stop and agent-policy execution."""
import math
from time import perf_counter_ns
from common import require,statement

def fallback_statement(query,*,fixture=False):
    sql,params=statement(query,fixture=fixture)
    require(sql.endswith(' LIMIT 10'),'unexpected fallback statement')
    return sql[:-len(' LIMIT 10')]+', id LIMIT 10',params

def decode(rows):
    return [[identifier,float(distance)] for identifier,distance in rows]

def validate_shape(output,required):
    require(len(output)<=required and len({i for i,_ in output})==len(output),'duplicate/oversized output')
    require(all(math.isfinite(d) and -1e-6<=d<=2+1e-6 for _,d in output),'invalid distance')

def guarded_request(ann_conn,exact_conn,query,eligible_count,reserve,*,fixture=False,clock=perf_counter_ns):
    """Both readers must share the exported snapshot; exact reader must force Seq Scan.

    reserve counts actual ANN/exact attempts and may abort before dispatch.
    Timer includes query construction, both SQL calls, decoding and guard logic.
    No output file, checkpoint receipt or heavyweight recall check is inside it.
    """
    begin=clock()
    required=min(query['k'],eligible_count)
    require(query['k']==10 and eligible_count>=0,'invalid serving request')
    sql,params=statement(query,fixture=fixture)
    ann_begin=clock();reserve('ann')
    initial=decode(ann_conn.execute(sql,params,prepare=False).fetchall())
    ann_end=clock()
    validate_shape(initial,required)
    fallback=len(initial)<required
    fallback_ns=0
    if fallback:
        sql,params=fallback_statement(query,fixture=fixture)
        exact_begin=clock();reserve('completion_exact')
        final=decode(exact_conn.execute(sql,params,prepare=False).fetchall())
        exact_end=clock();fallback_ns=exact_end-exact_begin
        validate_shape(final,required)
        require(len(final)==required,'exact completion did not produce required count')
    else:
        final=initial
    end=clock()
    request_ns=end-begin
    return {'initial':initial,'output':final,'required_count':required,
            'initial_count':len(initial),'fallback_used':fallback,
            'request_ns':request_ns,'ann_ns':ann_end-ann_begin,
            'fallback_ns':fallback_ns,
            'guard_and_construction_ns':request_ns-(ann_end-ann_begin)-fallback_ns}
