"""Small trusted broker with explicit agent-owned exports and decisions."""
from pathlib import Path
from contract import CONFIG,read,save,digest
from policy import validate
from screen import screen

class Tools:
    def __init__(self,run,store,phase):
        from fannagent.submission import SubmissionTracker
        self.run=Path(run);self.store=store;self.phase=phase;self.submissions=SubmissionTracker()
        self.cfg=read(self.run/'private/source-config.json');self.data=read(self.run/'evidence/corpus.json')
        self.status_provider=lambda:{}

    def exports(self):return self.store.get('exports_A' if self.phase=='A' else 'exports_B',{})

    def call(self,operation,args):
        from fannagent.submission import InvalidSubmission
        try:return self._call(operation,args)
        except (ValueError,TypeError,KeyError) as error:
            raise InvalidSubmission('invalid_arguments',str(error),hint='See /evidence/TOOLS.md for the exact operation schema.') from None

    def _call(self,operation,args):
        if self.store.get('phase_done_'+self.phase):raise ValueError('Episode phase already completed')
        if type(args) is not dict:raise ValueError('Arguments must be an object')
        if operation=='inspect':
            if args:raise ValueError('inspect takes no arguments')
            return {'context':read(self.run/'evidence/context.json'),'research_status':self.status_provider(),
                'exports':list(self.exports()),'helper_fits_used':self.store.get('helper_fits',0)}
        if operation in {'screen','diagnose','export'}:
            if set(args)-{'policy','origin'} or 'policy' not in args:raise ValueError('Supply policy and optional origin')
            raw,identity=validate(args['policy'],self.cfg);report=screen(raw,self.data['queries'],self.cfg)
            if self.phase=='B' and self.store.get('measurement_pilot'):
                from package import verified_measurement
                measured=verified_measurement(self.run,self.store,'pilot')
                if identity in measured['candidate_qualification']:
                    report.update(timing_status='Actual verified initial pilot; this semantic policy was measured',
                        measured_qualification=measured['candidate_qualification'][identity],measured_timing=measured['reports'][identity])
            artifact=self.store.put('development_screen',report,scope='development')
            if operation=='export':
                if not isinstance(args.get('origin','agent-authored'),str) or len(args.get('origin',''))>2048:raise ValueError('origin must be a short authorship statement')
                exports=self.exports();limit=3 if self.phase=='A' else 1
                if identity not in exports and len(exports)>=limit:raise ValueError('Export limit; exports cannot be replaced')
                if self.phase=='B' and identity in self.store.get('exports_A',{}):raise ValueError('Use finish selection for an unchanged initial candidate')
                receipt={'policy':raw,'semantic_hash':identity,'screen_artifact':artifact,'origin':args.get('origin','agent-authored'),
                    'phase':self.phase,'request_count':self.status_provider().get('provider_attempts_used',0),
                    'run_contract_sha256':__import__('contract').sha(self.run/'contract.json'),
                    'exact_seed_tree_reuse':[name for name,s in read(self.run/'evidence/seeds.json').items() if s['policy']['tree']['root']==raw['tree']['root']],
                    'exact_helper_behavior_reuse':[key for key,h in self.store.get('fit_cache',{}).items()
                        if validate(self.store.read(h,agent=True)['policy'],self.cfg)[1]==identity]}
                exports.setdefault(identity,receipt);self.store.set('exports_'+self.phase,exports)
                return {'semantic_hash':identity,'exported':True,'research_status':self.status_provider()}
            compact={k:v for k,v in report.items() if k not in {'first_stops','losses','unknown'}}
            compact.update(loss_count=len(report['losses']),losses=report['losses'][:12],unknown_count=len(report['unknown']),
                unknown=report['unknown'][:12],full_report_artifact=artifact)
            return compact
        if operation=='fit':
            from fitting import fit
            if set(args)!={'profile','eligible','risk'}:raise ValueError('fit requires profile,eligible,risk')
            key=digest(args);cache=self.store.get('fit_cache',{})
            if key in cache:
                result=self.store.read(cache[key],agent=True)
                return {'policy':result['policy'],'proof':{k:v for k,v in result['proof'].items() if k not in {'training_groups','training_first_stops'}},'screen':{k:v for k,v in result['screen'].items() if k not in {'first_stops','losses','unknown'}},'full_fit_artifact':cache[key],'cached':True}
            used=self.store.get('helper_fits',0)
            if used+6>96:raise ValueError('Trusted helper fit cap')
            self.store.set('helper_fits',used+6)  # reserve before computation; failures still consume it
            result=fit(self.data['queries'],self.cfg,self.data['folds'],**args)
            artifact=self.store.put('helper_fit',result,scope='development');cache[key]=artifact;self.store.set('fit_cache',cache)
            return {'policy':result['policy'],'proof':{k:v for k,v in result['proof'].items() if k not in {'training_groups','training_first_stops'}},'screen':{k:v for k,v in result['screen'].items() if k not in {'first_stops','losses','unknown'}},
                'full_fit_artifact':artifact,'primitive_fits_used':used+6}
        if operation=='artifact':
            if set(args)!={'hash'}:raise ValueError('artifact requires hash')
            return self.store.read(args['hash'],agent=True)
        if operation=='pause':
            if self.phase!='A' or set(args)!={'reason'} or not isinstance(args['reason'],str) or not self.exports():raise ValueError('Phase A pause requires reason and 1-3 exports')
            lock={'exports':self.exports(),'reason':args['reason'],'evidence':self.store.get('contract'),
                'helper_fits':self.store.get('helper_fits',0)}
            save(self.run/'proposal-lock.json',lock)
            self.store.set_many({'phase_done_A':True,'episode_status':'awaiting_pilot'})
            return {'status':'awaiting_pilot','proposal_lock_sha256':__import__('contract').sha(self.run/'proposal-lock.json')}
        if operation=='finish':
            if self.phase!='B' or set(args)!={'decision','reason'} or not isinstance(args['reason'],str):raise ValueError('Phase B finish requires decision and reason')
            decision=args['decision'];initial=self.store.get('exports_A',{});revised=self.exports()
            if decision=='abstain':selection=None;status='abstained'
            elif decision in initial and not revised:selection=initial[decision];status='selected_initial'
            elif decision in revised:selection=revised[decision];status='awaiting_revision_measurement'
            else:raise ValueError('Select an exported hash, or abstain. A revision is the sole final candidate.')
            save(self.run/'agent-final.json',{'status':status,'selection':selection,'reason':args['reason']})
            self.store.set_many({'phase_done_B':True,'episode_status':status})
            return {'status':status,'provider_calls_finished':True}
        raise ValueError('Operations: inspect,fit,screen,diagnose,export,artifact,pause,finish')
