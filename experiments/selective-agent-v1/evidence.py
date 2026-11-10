"""Verified development-only learner view, with private vector entitlements."""
import copy
import json
import sqlite3
from pathlib import Path
from contract import SOURCE,CAMPAIGN,SOURCE_MANIFEST,MODULE,CONFIG,FILTERS,read,sha,save,digest,lines,HERE,ROOT

def historical_state():
    ledger=ROOT/'trials/torch-reviews-results/reviews-policy-learning-20261019T145148Z.EJ34ct-agent/state.sqlite3'
    db=sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True)
    try:
        return {t:digest([list(r) for r in db.execute('SELECT * FROM '+t+' ORDER BY 1')]) for t in ('charges','state')}
    finally:db.close()

def source_config():
    if sha(SOURCE/'manifest.json')!=SOURCE_MANIFEST:raise ValueError('Sealed feature/data source changed')
    for name,h in read(SOURCE/'manifest.json')['files'].items():
        p=SOURCE/name
        if p.is_symlink() or sha(p)!=h:raise ValueError('Source file changed: '+name)
    if sha(CAMPAIGN/'build/vector.so')!=MODULE:raise ValueError('Verified x86 module changed')
    return read(SOURCE/'experiment.json')

def verified_rows():
    cfg=source_config();rows=[];pins={}
    post=read(ROOT/'agent/docs/verification/feature-data-ablation-v1-postrun.json')
    verification=CAMPAIGN/'analysis/verification.json'
    if sha(verification)!=post['analysis_files_sha256']['verification.json']:raise ValueError('Postrun verification changed')
    for name,h in read(verification)['raw_files_sha256'].items():
        if sha(CAMPAIGN/name)!=h:raise ValueError('Verified prior evidence changed: '+name)
    for part in range(2):
        folder=CAMPAIGN/'acquire'/('part-'+str(part))
        for name in ('host-exit.json','job-exit.json'):
            if read(folder/name)['exit_code']:raise ValueError('Failed acquisition')
        lock=read(folder/'LOCK.json')
        if lock['package_manifest_sha256']!=SOURCE_MANIFEST:raise ValueError('Different acquisition source')
        for name,h in lock['files_sha256'].items():
            if sha(folder/name)!=h:raise ValueError('Returned raw data changed: '+name)
            pins[str((folder/name).relative_to(CAMPAIGN))]=h
        data=read(folder/'evidence.json');refs={r['query_id']:r for r in lines(folder/'references.jsonl')}
        proofs={(r['query_id'],r['family'],r['checkpoint']):r for r in lines(folder/'proofs.jsonl')}
        for q in data['queries']:
            if q['role'] not in {'original_learning','additional_learning','calibration'}:raise ValueError('Nondevelopment evidence')
            ref=refs[q['query_id']]
            if q['base_states']!=ref['base_states'] or q['local_states']!=ref['local_states']:raise ValueError('Unproven observations')
            for family in ('base','local'):
                ss=q[family+'_states']
                for cp,label in q['labels'][family].items():
                    p=proofs[(q['query_id'],family,int(cp))]
                    if p['observed_prefix_sha256']!=digest(ss[:int(cp)]) or label['returned_count']!=len(p['policy_ids']):raise ValueError('Unproven actual stop')
            rows.append(copy.deepcopy(q))
    items=sum((lines(SOURCE/'inputs'/('acquire-'+str(i)+'.jsonl')) for i in range(2)),[])
    by_id={i['query']['id']:i for i in items}
    if len(rows)!=600 or len(by_id)!=600 or {q['query_id'] for q in rows}!=set(by_id):raise ValueError('Development inventory')
    groups={q['group'] for q in rows}
    if len(groups)!=200 or any({q['stratum'] for q in rows if q['group']==g}!=set(FILTERS) for g in groups):raise ValueError('Grouped filter inventory')
    for q in rows:
        if q['group']!=by_id[q['query_id']]['group']:raise ValueError('Vector group mismatch')
    split=read(SOURCE/'inputs/ablation-split.json')
    if len(split['selected_catalog_groups']['evaluation'])!=60 or len(split['selected_catalog_groups']['reserved'])!=37:raise ValueError('Reserved inventory changed')
    return cfg,sorted(rows,key=lambda q:q['query_id']),items,pins

def seeds(cfg):
    from policy import compose,references
    lock=read(CAMPAIGN/'fit/fit-lock.json');s=next(c for c in lock['trials']['S160'] if c['risk']==1280.)
    result={'S160-risk1280':{'policy':compose('reference-S160-risk1280',s['policy']['root']['then']),
        'origin':'Conventional first-stop fitter; selected reference only, not an agent discovery',
        'note':'Originally costed as static23; references only light19. Light19 execution cost unmeasured.'}}
    # Find the earlier frozen agent export in its sealed input inventory.
    root=ROOT/'trials/torch-reviews-results/frozen-proposals-timing-v1-runtime-fix/torch-frozen-proposals-timing-v1-runtime-fix-training/cohorts'
    def visit(x):
        if isinstance(x,dict):
            if isinstance(x.get('name'),str) and x['name']=='cons_S32_64_128_t002' and 'root' in x:yield x
            for v in x.values():yield from visit(v)
        elif isinstance(x,list):
            for v in x:yield from visit(v)
    for path in sorted(root.glob('*/inputs/*.json')):
        for raw in visit(read(path)):
            # The existing outer guard is retained as part of the reference tree;
            # normalise to one canonical guard without altering its predicate.
            body=raw['root']
            if isinstance(body,dict) and body.get('else')=='continue' and not any(s in json.dumps(body['if']) for s in ('"gte"','"lte"','"eq"','"gt"','"lt"')):
                body=body['then']
            result['cons_S32_64_128_t002']={'policy':compose('reference-cons-S32-64-128-t002',body),
                'origin':'Earlier agent-generated frozen proposal',
                'note':'Passed earlier training timing; failed consumed independent confirmation recall. Old raw confirmation excluded.'}
            return result
    raise ValueError('Earlier frozen agent seed not found')

def prepare(run):
    from policy import names,validate
    from fannagent_pgvector.profiles import PROFILE
    before=historical_state();cfg,rows,items,pins=verified_rows()
    run=Path(run);(run/'evidence').mkdir(parents=True);(run/'private').mkdir()
    groups=sorted({q['group'] for q in rows},key=lambda g:digest([20261022,'selective-agent-v1/development-folds',g]))
    folds={g:i%5 for i,g in enumerate(groups)}
    costs={}
    for part in range(2):
        for r in lines(CAMPAIGN/'acquire'/('part-'+str(part))/'pairs.jsonl'):
            if r['checkpoint'] is not None:continue
            profile='static23' if r['family']=='base' else 'progress34';key=profile+'/'+r['regime']
            s=costs.setdefault(key,{'pairs':0,'sum_native_ms':0.,'sum_policy_ms':0.,'sum_collection_ms':0.})
            s['pairs']+=1;s['sum_native_ms']+=r['native_ms'];s['sum_policy_ms']+=r['policy_ms'];s['sum_collection_ms']+=r['work']['feature_collection_ns']/1e6
    context={'version':'selective-evidence.v1','development_vectors':200,'development_cases':600,
        'confirmation_vectors_sealed':60,'reserved_vectors_sealed':37,
        'profiles':{p:{'features':names(cfg,p),'groups':__import__('policy').GROUPS[p]} for p in ('light19','static23','progress34')},
        'features':{n:PROFILE.runtime_features[n].model_dump(mode='json') for n in names(cfg,'progress34')},
        'objective':CONFIG,'folds':'All three filters stay together. Existing exposed data, not independent validation.',
        'costs':'static23/progress34 fixed-stop proxies; light19 costs unmeasured. Routing cost unmeasured until pilot.',
        'measured_continue_costs':{k:{'pairs':v['pairs'],'native_ms':v['sum_native_ms']/v['pairs'],
            'policy_ms':v['sum_policy_ms']/v['pairs'],'feature_collection_ms':v['sum_collection_ms']/v['pairs']} for k,v in costs.items()},
        'unknown_stops':'Unknown, never interpolated; missing checkpoint means native search finished before it.'}
    save(run/'evidence/context.json',context);save(run/'evidence/corpus.json',{'queries':rows,'folds':folds})
    refs=seeds(cfg)
    for r in refs.values():validate(r['policy'],cfg)
    save(run/'evidence/seeds.json',refs)
    save(run/'private/development.jsonl',''.join(json.dumps(i,sort_keys=True)+'\n' for i in items),raw=True)
    save(run/'private/source-config.json',cfg)
    save(run/'private/source-pins.json',{'source_manifest':SOURCE_MANIFEST,'module_sha256':MODULE,'raw':pins,
        'split_sha256':sha(SOURCE/'inputs/ablation-split.json'),'historical_state':before})
    for n in ('TOOLS.md','policy_tools.py'):
        save(run/'evidence'/n,(HERE/n).read_bytes(),raw=True)
    if before!=historical_state():raise ValueError('Historical ledger changed')
    return {'files':{p.name:sha(p) for p in (run/'evidence').iterdir()},'historical_state':before,
        'development_queries_sha256':sha(run/'private/development.jsonl'),'source_manifest':SOURCE_MANIFEST,
        'private_input_files':{p.name:sha(p) for p in (run/'private').iterdir() if p.is_file()}}
