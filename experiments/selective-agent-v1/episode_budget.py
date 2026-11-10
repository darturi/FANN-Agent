"""Independent atomic $6/$4 phase ledger; never touches historical charges."""
import json
import uuid
from decimal import Decimal
from fannagent.budget import Budget,SCALE,units
from fannagent.errors import AgentError,BudgetExceeded
from contract import CONFIG

class EpisodeBudget(Budget):
    def __init__(self,store,config,phase):
        super().__init__(store,config)
        if phase not in {'A','B'}:raise AgentError('Unknown episode phase')
        self.phase=phase

    def calls(self):return self.summary()['calls']

    def reserve(self,maximum,metadata=None):
        if self.store.get('provider_bound_failed'):raise AgentError('Provider contract failed')
        amount=units(maximum)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows=[dict(r) for r in db.execute('SELECT * FROM charges')]
            if any(r['status'] in {'reserved','bound_violation'} for r in rows):raise AgentError('Unresolved request; do not redispatch')
            selected=[r for r in rows if json.loads(r['metadata'])['phase']==self.phase]
            spent=lambda rr:sum(r['actual'] if r['actual'] is not None else r['reserved'] for r in rr)
            if len(rows)>=12 or len(selected)>=CONFIG['provider_attempts'][self.phase]:raise BudgetExceeded('Provider attempt limit')
            if spent(rows)+amount>units(Decimal('10')) or spent(selected)+amount>units(Decimal(CONFIG['phase_usd'][self.phase])):
                raise BudgetExceeded('Global/phase allowance cannot reserve next request')
            identity=uuid.uuid4().hex
            db.execute('INSERT INTO charges VALUES (?,?,NULL,?,?)',(identity,amount,'reserved',json.dumps({**(metadata or {}),'phase':self.phase})))
        return identity

    def settle(self,identity,actual,metadata):
        with self.store.connect() as db:
            row=db.execute('SELECT metadata FROM charges WHERE id=?',(identity,)).fetchone()
        return super().settle(identity,actual,{**json.loads(row[0]),**metadata})

    def uncertain(self,identity,reason):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT metadata FROM charges WHERE id=?',(identity,)).fetchone()
            db.execute("UPDATE charges SET status='uncertain',metadata=? WHERE id=? AND status='reserved'",
                (json.dumps({**json.loads(row[0]),'reason':reason}),identity))

    def status(self):
        s=self.summary();rows=s.pop('calls');s['phase']=self.phase
        selected=[r for r in rows if json.loads(r['metadata'])['phase']==self.phase]
        committed=lambda rr:Decimal(sum(r['actual'] if r['actual'] is not None else r['reserved'] for r in rr))/SCALE
        s.update(provider_attempts_used=len(rows),provider_attempt_limit=12,
            phase_attempts_used=len(selected),phase_attempt_limit=CONFIG['provider_attempts'][self.phase],
            phase_requests_remaining=CONFIG['provider_attempts'][self.phase]-len(selected),
            phase_cap_usd=CONFIG['phase_usd'][self.phase],phase_committed_usd=str(committed(selected)),
            phase_remaining_usd=str(Decimal(CONFIG['phase_usd'][self.phase])-committed(selected)),
            settled_usd=str(committed([r for r in rows if r['status']=='settled'])),
            uncertain_reserved_usd=str(committed([r for r in rows if r['status'] in {'uncertain','reserved'}])),
            maximum_next_reservation_usd=str(self.maximum_call()))
        return s
