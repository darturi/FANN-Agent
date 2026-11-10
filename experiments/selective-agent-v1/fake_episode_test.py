"""Actual Docker/broker pause/resume with a fake provider. Zero paid requests."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from contract import bootstrap,OUTPUT,read,save,sha,replace
bootstrap()

def main():
    from study import prepare,episode,check_run,status
    from fannagent.store import Store
    from evidence import historical_state
    from package import selection,build
    before=historical_state();out=OUTPUT/'validation';out.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='fake-episode-',dir=out));run=prepare(temp,synthetic=True)
    commands=["""python - <<'PY'
import json,sys
sys.path.insert(0,'/evidence')
from policy_tools import call
seed=json.load(open('/evidence/seeds.json'))['cons_S32_64_128_t002']['policy']
r=call('export',policy=seed,origin='Synthetic harness reuses credited seed')
print(call('pause',reason='Synthetic test explicit pause'))
PY""","""python - <<'PY'
import sys
sys.path.insert(0,'/evidence')
from policy_tools import call,policy
p=policy('synthetic-only-revision','continue',eligible=['unfiltered'])
r=call('export',policy=p,origin='Synthetic-only revision')
print(call('finish',decision=r['semantic_hash'],reason='Synthetic-only explicit final choice'))
PY"""]
    attempts=[]
    def provider(**kwargs):
        assert kwargs['num_retries']==kwargs['max_retries']==0
        attempts.append(kwargs['messages']);i=len(attempts)-1
        raw={'choices':[{'message':{'role':'assistant','content':None,'tool_calls':[{'id':'fake-'+str(i),
            'type':'function','function':{'name':'bash','arguments':json.dumps({'command':commands[i]})}}]}}],
            'usage':{'prompt_tokens':0,'completion_tokens':0}}
        return SimpleNamespace(model_dump=lambda **kw:raw)
    episode(run,'A',dispatch=provider)
    store=Store(run);assert store.get('phase_done_A') and not store.get('phase_done_B')
    package=build(run,store,'pilot');assert (package/'manifest.json').exists()
    from control import submit
    with patch('control.verify',return_value={'synthetic_only':True}):
        try:submit(package,Path('/unused'),Path('/unused'))
        except ValueError:pass
        else:raise AssertionError('Synthetic package could submit')
    initial=store.get('exports_A');h=next(iter(initial))
    feedback={'candidate_qualification':{h:{'development_qualifies':False}},'reports':{},'ab_comparison':__import__('contract').AB,
        'scope':'Development only; no holdout executed','initial_exports':list(initial)}
    (run/'feedback').mkdir();save(run/'feedback/summary.json',feedback)
    save(run/'evidence/pilot-performance.json',{'synthetic_only':True,'no_actual_measurements':True})
    store.set_many({'episode_status':'awaiting_feedback','feedback_sha256':sha(run/'evidence/pilot-performance.json')})
    simulated={'candidate_qualification':feedback['candidate_qualification'],'reports':{}}
    with patch('package.verified_measurement',return_value=simulated):episode(run,'B',dispatch=provider)
    assert store.get('phase_done_B') and store.get('episode_status')=='awaiting_revision_measurement'
    assert len(store.get('exports_B'))==1 and len(attempts)==2
    assert len(attempts[1])>len(attempts[0]) # same persisted transcript, not another episode
    assert store.get('commands_used')==2
    result=status(run);assert result['budget']['committed_usd']=='0'
    try:selection(run,store,'confirmation')
    except ValueError:pass
    else:raise AssertionError('Unmeasured revision reached confirmation')
    assert historical_state()==before
    record={'status':'passed','synthetic_only':True,'provider_dispatches_simulated':2,'paid_provider_requests':0,
        'explicit_pause_resume_finish':True,'same_transcript':True,'same_ledger':True,'actual_Docker_broker':True,
        'revision_without_measurement_cannot_confirm':True,'synthetic_cannot_submit':True,'run':str(run)}
    replace(out/'fake-episode-checks.json',record);print(json.dumps(record,indent=2))

if __name__=='__main__':main()
