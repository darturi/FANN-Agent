import unittest
from guard import guarded_request
class Result:
    def __init__(self,rows):self.rows=rows
    def fetchall(self):return self.rows
class Connection:
    def __init__(self,rows):self.rows=rows;self.calls=[]
    def execute(self,sql,params,**kwargs):self.calls.append((sql,params));return Result(self.rows)
class GuardTests(unittest.TestCase):
    def setUp(self):self.q={'k':10,'vector':[.1]*8,'filter':{'field':'totalvotes','op':'gte','value':743}};self.attempts=[]
    def run_guard(self,initial,exact,n=2475):
        a=Connection(initial);e=Connection(exact)
        r=guarded_request(a,e,self.q,n,self.attempts.append)
        self.assertEqual(r['request_ns'],r['ann_ns']+r['fallback_ns']+r['guard_and_construction_ns'])
        return r,a,e
    def test_full_output_never_calls_exact(self):
        rows=[(i,.1) for i in range(10)];r,_,e=self.run_guard(rows,[])
        self.assertFalse(r['fallback_used']);self.assertEqual(e.calls,[]);self.assertEqual(self.attempts,['ann'])
    def test_short_is_replaced_not_appended(self):
        r,a,e=self.run_guard([(999,.2)],[(i,.1) for i in range(10)])
        self.assertTrue(r['fallback_used']);self.assertNotIn(999,[i for i,_ in r['output']]);self.assertEqual(self.attempts,['ann','completion_exact'])
        self.assertIn('total_votes >= %s',e.calls[0][0]);self.assertIn(', id LIMIT 10',e.calls[0][0]);self.assertEqual(a.calls[0][1],e.calls[0][1])
    def test_empty_eligible_population(self):
        r,_,e=self.run_guard([],[],0);self.assertEqual(r['output'],[]);self.assertEqual(e.calls,[])
    def test_fewer_than_k_eligible(self):
        r,_,_=self.run_guard([],[(0,.1),(1,.2)],2);self.assertEqual(len(r['output']),2)
    def test_corruption_is_not_hidden_by_fallback(self):
        for rows in ([(1,.1),(1,.2)],[(1,float('nan'))]):
            e=Connection([])
            with self.assertRaises(RuntimeError):guarded_request(Connection(rows),e,self.q,2475,self.attempts.append)
            self.assertEqual(e.calls,[])
    def test_failed_exact_completion_rejected(self):
        with self.assertRaises(RuntimeError):self.run_guard([],[(0,.1)])
    def test_budget_prevents_second_dispatch(self):
        e=Connection([(i,.1) for i in range(10)])
        def reserve(operation):
            if operation=='completion_exact':raise RuntimeError('cap')
        with self.assertRaises(RuntimeError):guarded_request(Connection([]),e,self.q,2475,reserve)
        self.assertEqual(e.calls,[])
if __name__=='__main__':unittest.main(verbosity=2)
