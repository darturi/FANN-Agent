"""One approximate query only. Deliberately has no exact connection or truth input."""
from time import perf_counter_ns
from common import statement

def request(ann_conn,query,reserve,*,fixture=False,clock=perf_counter_ns):
 reserve('ann')
 begin=clock();sql,params=statement(query,fixture=fixture);dispatch=clock()
 rows=ann_conn.execute(sql,params,prepare=False).fetchall()
 output=[[identifier,float(distance)] for identifier,distance in rows]
 end=clock()
 return {'output':output,'returned_count':len(output),'request_ns':end-begin,'construction_ns':dispatch-begin,'sql_fetch_decode_ns':end-dispatch}
