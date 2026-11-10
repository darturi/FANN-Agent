"""Mac controller for one fresh episode, one feedback response and sealed stages."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import tarfile
import time
import uuid
os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP','True')
from contract import HERE,ROOT,OUTPUT,CONFIG,AB,read,save,sha,digest,replace,bootstrap
bootstrap()

def source_hashes():
    core=HERE/'vendor/fannagent' if (HERE/'vendor/fannagent').is_dir() else ROOT/'agent/src/fannagent'
    return {'workspace-root':digest(str(ROOT)),
        **{p.name:sha(p) for p in sorted(HERE.iterdir()) if p.suffix in {'.py','.md','.json'} and p.name!='.workspace-root.json'},
        **{'core/'+str(p.relative_to(core)):sha(p) for p in sorted(core.rglob('*.py'))}}

def native_source_hashes():
    from package import RUNTIME_FILES
    allowed=set(RUNTIME_FILES)|{'native_check.py','native_selective.py','validate.py'}
    return {k:v for k,v in source_hashes().items() if k in allowed or k.startswith('core/')}

def check_run(run,store):
    from evidence import historical_state
    c=read(run/'contract.json')
    if c!=store.get('contract') or c['source_files']!=source_hashes():raise ValueError('Run contract/source changed')
    for name,h in c['evidence']['files'].items():
        if sha(run/'evidence'/name)!=h:raise ValueError('Learner evidence changed')
    if historical_state()!=c['evidence']['historical_state']:raise ValueError('Historical ledger changed')
    if sha(run/'private/development.jsonl')!=c['evidence']['development_queries_sha256']:raise ValueError('Development entitlements changed')
    for name,h in c['evidence']['private_input_files'].items():
        if sha(run/'private'/name)!=h:raise ValueError('Private input changed: '+name)
    if store.get('feedback_sha256') and sha(run/'evidence/pilot-performance.json')!=store.get('feedback_sha256'):raise ValueError('Feedback changed')
    return c

def prepare(output=OUTPUT,synthetic=False):
    from evidence import prepare as build_evidence
    from fannagent.store import Store
    output=Path(output);output.mkdir(parents=True,exist_ok=True);binding=output/'binding.json'
    if binding.exists():
        run=Path(read(binding)['run']);store=Store(run);check_run(run,store);return run
    episode=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    run=output/'runs'/episode;run.mkdir(parents=True,mode=0o700)
    store=Store(run,create=True);evidence=build_evidence(run)
    model=read(ROOT/'trials/torch-reviews-aggressive-proposals-v2/model.json')
    model.update(ceiling_usd='10',allowance_usd='0',pricing_revision='anthropic-sonnet-5-5-standard-global-2026-10-22',max_attempts=1)
    sandbox=read(ROOT/'trials/torch-reviews-aggressive-proposals-v2/local-runtime.json')
    contract={'episode_id':episode,'version':CONFIG['version'],'protocol':CONFIG,'model':model,'sandbox':sandbox,
        'evidence':evidence,'source_files':source_hashes(),'synthetic_only':synthetic,'original_ab':AB}
    # Preserve the local controller and its core dependencies through the Torch wait.
    import shutil
    controller=run/'controller';controller.mkdir()
    for p in HERE.iterdir():
        if p.suffix in {'.py','.md','.json'} and p.name!='.workspace-root.json':shutil.copyfile(p,controller/p.name)
    save(controller/'.workspace-root.json',{'root':str(ROOT)})
    shutil.copytree(__import__('contract').SOURCE/'vendor',controller/'vendor',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(ROOT/'agent/src/fannagent',controller/'vendor/fannagent',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    save(run/'contract.json',contract);store.set_many({'contract':contract,'episode_id':episode,
        'episode_status':'prepared','synthetic_only':synthetic,'commands_used':0,'active_seconds_used':0.,'helper_fits':0})
    save(binding,{'run':str(run),'episode_id':episode,'contract_sha256':sha(run/'contract.json')})
    return run

def active_run(value):
    return Path(value).resolve() if value else Path(read(OUTPUT/'binding.json')['run'])

def feedback_for(pilot,exports):
    reports={}
    fields={'native_ms','policy_ms','gap_ms','gap_ci95','recall_delta','recall_delta_ci95','log_latency_ratio_ci95','native_recall','all_valid'}
    for arm,modes in pilot['reports'].items():
        reports[arm]={}
        for regime,m in modes.items():
            reports[arm][regime]={k:v for k,v in m.items() if k!='report'}|{'overall':{k:v for k,v in m['report']['overall'].items() if k in fields},
                'per_filter':{f:{k:v for k,v in s.items() if k in fields} for f,s in m['report']['per_filter'].items()}}
    return {'candidate_qualification':pilot['candidate_qualification'],'reports':reports,'ab_comparison':AB,
        'scope':'Development only; no holdout executed','initial_exports':list(exports)}

def native_receipt(run=None):
    p=Path(run)/'private/native-validation.json' if run and (Path(run)/'private/native-validation.json').exists() else OUTPUT/'validation/native-checks.json'
    if not p.exists():raise ValueError('Run native validation before paid generation')
    r=read(p)
    if r['status']!='passed' or not r['synthetic_only'] or r.get('native_source_sha256')!=digest(native_source_hashes()):raise ValueError('Native validation is stale or failed')
    return r

def episode(run,phase,dispatch=None):
    from fannagent.store import Store
    from fannagent.config import ModelConfig
    from fannagent.model import BudgetedModel
    from fannagent.broker import FileBroker
    from fannagent.errors import AgentError
    from minisweagent.exceptions import FormatError
    from episode_budget import EpisodeBudget
    from tools import Tools
    from sandbox import Sandbox
    from prompts import SYSTEM
    store=Store(run);c=check_run(run,store)
    if store.get('phase_done_'+phase):return status(run)
    expected='prepared' if phase=='A' else 'awaiting_feedback'
    if store.get('episode_status')!=expected:raise ValueError('Unexpected or interrupted state; do not silently resume/replay requests')
    if phase=='B':
        from package import verified_measurement
        pilot=verified_measurement(run,store,'pilot')
        expected_feedback=feedback_for(pilot,store.get('exports_A'))
        if read(run/'feedback/summary.json')!=expected_feedback:raise ValueError('Feedback summary changed')
    if dispatch is None:
        from provider_preflight import verify
        nr=native_receipt(run);save(run/'private/native-validation.json',nr)
        receipt=verify(c['model']);save(run/('provider-preflight-'+phase+'.json'),receipt)
        import litellm
        dispatch=litellm.completion
    elif not c['synthetic_only']:raise ValueError('Fake provider only permitted in synthetic validation runs')
    with store.lease('run'):
        if store.get('phase_done_'+phase) or store.get('episode_status')!=expected:raise ValueError('Phase state changed during preflight; do not redispatch')
        budget=EpisodeBudget(store,ModelConfig.model_validate(c['model']),phase);tools=Tools(run,store,phase)
        work=run/'workspace';work.mkdir(exist_ok=True)
        if phase=='A':
            messages=[{'role':'system','content':SYSTEM},{'role':'user','content':
                'Phase A. Read /evidence/TOOLS.md and the small context/seeds files. Develop 1-3 proposals and call pause explicitly.'}]
        else:
            messages=store.get('messages');messages.append({'role':'user','content':
                'Phase B, your only real feedback response. Verified initial pilot summary:\n'+json.dumps(read(run/'feedback/summary.json'))+
                '\nFull performance is /evidence/pilot-performance.json. Select an unchanged export, export one sole revision, or abstain; call finish.'})
        store.set_many({'episode_status':'running_'+phase,'messages':messages})
        started=time.monotonic();previous=store.get('active_seconds_used',0.);env=None
        def provider(**kwargs):
            if previous+time.monotonic()-started>=3600:raise TimeoutError('Active analysis deadline')
            return dispatch(**{**kwargs,'timeout':min(120,3600-previous-(time.monotonic()-started))})
        model=BudgetedModel(ModelConfig.model_validate(c['model']),budget,dispatch=provider)
        try:
            with FileBroker(tools,work/'.broker') as broker:
                env=Sandbox(run/'evidence',work,broker,c['sandbox']['sandbox_image_id'],store)
                def research_status():
                    return {**budget.status(),'exports_used':len(tools.exports()),'helper_fits_used':store.get('helper_fits',0),
                        'commands_used':env.commands,'commands_remaining':120-env.commands,
                        'active_seconds_remaining':max(0,3600-previous-(time.monotonic()-started))}
                tools.status_provider=research_status
                while not store.get('phase_done_'+phase):
                    check_run(run,store)
                    s=research_status();print(json.dumps(s),flush=True)
                    if s['phase_requests_remaining']<=0:raise AgentError('Request limit without explicit completion: censored')
                    if s['active_seconds_remaining']<=0:raise AgentError('Active time exhausted: censored')
                    messages.append({'role':'user','content':json.dumps({'research_status':s,
                        'instruction':'Pause/finish explicitly in this response; no later request remains.' if s['phase_requests_remaining']==1 else 'Use concise tools and preserve requests for explicit completion.'})})
                    env.turn_id=tools.submissions.begin_turn()
                    try:
                        message=model.query(messages);messages.append(message);outputs=[]
                        for action in message['extra']['actions']:
                            outputs.append({'returncode':1,'output':'Phase already completed'} if store.get('phase_done_'+phase) else env.execute(action))
                        messages.extend(model.format_observation_messages(message,outputs))
                    except FormatError as e:messages.extend(e.messages)
                    finally:
                        tools.submissions.finish_turn();store.set('messages',messages)
        except BaseException as e:
            # Paid requests and completed exports remain durable. No automatic continuation.
            if not store.get('phase_done_'+phase):store.set_many({'episode_status':'censored_'+phase,'failure':{'type':type(e).__name__,'message':str(e)}})
            raise
        finally:
            if env:env.close()
            store.set('active_seconds_used',previous+time.monotonic()-started)
    if phase=='B' and read(run/'agent-final.json')['status']=='selected_initial':
        from package import verified_measurement
        final=read(run/'agent-final.json');pilot=verified_measurement(run,store,'pilot')
        passed=pilot['candidate_qualification'][final['selection']['semantic_hash']]['development_qualifies']
        store.set('episode_status','development_qualified' if passed else 'no_qualified_candidate')
    return status(run)

def ingest(run,stage,archive):
    from fannagent.store import Store
    from report import analyze
    from package import verified_measurement
    store=Store(run);check_run(run,store);packages=store.get('packages',{})
    if stage not in packages:raise ValueError('No frozen package for this stage')
    if store.get('measurement_'+stage):
        binding=store.get('measurement_'+stage);path=run/'measurements'/stage/'performance.json'
        if sha(path)!=binding['performance_sha256']:raise ValueError('Imported measurements changed')
        return verified_measurement(run,store,stage) if read(path)['status']=='verified' else read(path)
    archive=Path(archive).resolve();checksum=Path(str(archive)+'.sha256')
    if sha(archive)!=checksum.read_text().split()[0]:raise ValueError('Archive checksum failed')
    dest=run/'returned'/stage;dest.mkdir(parents=True,exist_ok=False)
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers()
        if len(members)>5000 or sum(m.size for m in members)>4*1024**3:raise ValueError('Returned archive exceeds declared envelope')
        roots={Path(m.name).parts[0] for m in members if Path(m.name).parts}
        if len(roots)!=1:raise ValueError('Expected one campaign root')
        for m in members:
            p=Path(m.name)
            if p.is_absolute() or '..' in p.parts or m.issym() or m.islnk() or not (m.isfile() or m.isdir()):raise ValueError('Unsafe archive member')
            # Extract data only. Returned code is never executed or imported.
            if m.isdir():continue
            if p.suffix not in {'.json','.jsonl','.txt','.log'}:continue
            target=dest/p;target.parent.mkdir(parents=True,exist_ok=True)
            import shutil
            with target.open('xb') as handle:shutil.copyfileobj(tar.extractfile(m),handle,1024*1024)
    campaign=dest/next(iter(roots));package=Path(packages[stage]['path']);out=run/'measurements'/stage
    exits=[campaign/'blocks'/('block-'+str(i))/'host-exit.json' for i in range(3)]
    if any(not p.exists() or read(p)['exit_code'] for p in exits):
        from control import verify
        cfg=verify(package);out.mkdir(parents=True,exist_ok=True)
        result={'status':'incomplete_or_failed','stage':stage,'episode_id':cfg['episode_id'],
            'candidate_qualification':{},'blocks':{str(i):read(p) if p.exists() else {'status':'missing/cancelled'} for i,p in enumerate(exits)},
            'provider_calls':0,'canonical_acceptance_established':False,'ab_comparison':AB,
            'diagnostic':'No model feedback or confirmation follows incomplete/failed measurements.'}
        save(out/'performance.json',result)
        store.set_many({'measurement_'+stage:{'performance_sha256':sha(out/'performance.json'),'archive_sha256':sha(archive)},
            'episode_status':'measurement_failed_'+stage})
        print(json.dumps(result,indent=2));return result
    result=analyze(campaign,package,out)
    binding={'performance_sha256':sha(out/'performance.json'),'archive_sha256':sha(archive),
        'package_manifest_sha256':sha(package/'manifest.json'),'raw_root':str(campaign)}
    store.set('measurement_'+stage,binding)
    if stage=='pilot':
        (run/'feedback').mkdir()
        summary=feedback_for(result,store.get('exports_A'))
        save(run/'feedback/summary.json',summary)
        save(run/'evidence/pilot-performance.json',result)
        # Pilot feedback is a separately sealed addition; original evidence hashes remain unchanged.
        store.set_many({'episode_status':'awaiting_feedback','feedback_sha256':sha(run/'evidence/pilot-performance.json')})
    elif stage=='revision':
        eligible=any(q['development_qualifies'] for q in result['candidate_qualification'].values())
        store.set('episode_status','development_qualified' if eligible else 'no_qualified_candidate')
    else:
        success=any(q['final_qualifies'] for q in result['candidate_qualification'].values())
        store.set('episode_status','confirmed_on_this_workload' if success else 'failed_confirmation')
    print(json.dumps(result['candidate_qualification'],indent=2));return result

def status(run):
    from fannagent.store import ReadOnlyStore
    from fannagent.config import ModelConfig
    from episode_budget import EpisodeBudget
    store=ReadOnlyStore(run);phase='B' if store.get('phase_done_A') else 'A'
    from fannagent.budget import Budget,SCALE
    from decimal import Decimal
    budget=Budget(store,ModelConfig.model_validate(read(run/'contract.json')['model']),readonly=True).summary();rows=budget.pop('calls')
    budget.update(provider_attempts_used=len(rows),provider_attempt_limit=12,
        phase_attempts_used=sum(json.loads(r['metadata'])['phase']==phase for r in rows),phase_attempt_limit=CONFIG['provider_attempts'][phase],
        settled_usd=str(Decimal(sum(r['actual'] for r in rows if r['status']=='settled'))/SCALE),
        uncertain_reserved_usd=str(Decimal(sum(r['reserved'] for r in rows if r['status'] in {'uncertain','reserved'}))/SCALE))
    selected=[r for r in rows if json.loads(r['metadata'])['phase']==phase]
    committed=Decimal(sum(r['actual'] if r['actual'] is not None else r['reserved'] for r in selected))/SCALE
    budget.update(phase=phase,phase_cap_usd=CONFIG['phase_usd'][phase],phase_committed_usd=str(committed),
        phase_remaining_usd=str(Decimal(CONFIG['phase_usd'][phase])-committed),
        phase_requests_remaining=CONFIG['provider_attempts'][phase]-len(selected))
    result={'run':str(run),'status':store.get('episode_status'),'budget':budget,
        'initial_exports':list(store.get('exports_A',{})),'revision_exports':list(store.get('exports_B',{})),
        'commands_used':store.get('commands_used',0),'helper_fits_used':store.get('helper_fits',0),
        'packages':store.get('packages',{}),'ab_comparison':AB,'canonical_acceptance_established':False}
    print(json.dumps(result,indent=2));return result

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','propose','resume','package','ingest','status','preflight']);p.add_argument('--run',type=Path)
    p.add_argument('--stage',choices=['pilot','revision','confirmation']);p.add_argument('--archive',type=Path);a=p.parse_args()
    if a.command=='prepare':print(prepare());return
    run=active_run(a.run)
    frozen=run/'controller/study.py'
    if frozen.is_file() and frozen.resolve()!=Path(__file__).resolve():
        os.execv(sys.executable,[sys.executable,str(frozen),*sys.argv[1:]])
    if a.command in {'propose','resume'}:episode(run,'A' if a.command=='propose' else 'B')
    elif a.command=='status':status(run)
    elif a.command=='package':
        if not a.stage:p.error('--stage is required')
        from fannagent.store import Store
        from package import build
        store=Store(run);check_run(run,store)
        with store.lease('prepare'):target=build(run,store,a.stage)
        print(json.dumps(store.get('packages')[a.stage],indent=2))
    elif a.command=='ingest':
        if not a.stage or not a.archive:p.error('--stage and --archive are required')
        ingest(run,a.stage,a.archive)
    else:
        from provider_preflight import verify
        from fannagent.store import Store
        check_run(run,Store(run));native_receipt(run);print(json.dumps(verify(read(run/'contract.json')['model']),indent=2))

if __name__=='__main__':main()
