"""Strict composite policies; runtime routing uses actual predicates only."""
from copy import deepcopy
from contract import FILTERS, EARLY, digest
from fd_policy_tools import references, guard, predict

GROUPS={'light19':('basic','work','queue','distances'),
    'static23':('basic','work','queue','distances','local_filter'),
    'progress34':('basic','work','queue','distances','local_filter','progress_filter')}

def names(cfg,profile):
    from fd_contract import EXTRA
    if profile not in GROUPS:raise ValueError('Unknown feature profile')
    return cfg['base_feature_names'] if profile=='light19' else cfg['static_feature_names']+(EXTRA if profile=='progress34' else [])

def route(query):
    f=query.get('filter')
    if f is None:return 'unfiltered'
    if (type(f) is dict and set(f)=={'field','op','value'} and f['field']=='m_000000'
        and f['op']=='gte' and type(f['value']) is int and f['value'] in (32,108)):
        return 'votes'+str(f['value'])
    return 'other'

def validate(raw,cfg):
    from fannagent.api import validate_policy
    from fannagent_pgvector.profiles import PROFILE
    if type(raw) is not dict or set(raw)!={'version','name','eligible','profile','tree'}:
        raise ValueError('Composite requires exactly version,name,eligible,profile,tree')
    if raw['version']!='selective-policy.v1' or not isinstance(raw['name'],str) or not 1<=len(raw['name'])<=160:
        raise ValueError('Invalid version/name')
    eligible=raw['eligible']
    if type(eligible) is not list or not eligible or any(type(s) is not str or s not in FILTERS for s in eligible) or len(set(eligible))!=len(eligible):
        raise ValueError('Choose a nonempty subset of actual query predicates')
    allowed=names(cfg,raw['profile']);tree=raw['tree']
    if type(tree) is not dict or set(tree)!={'name','feature_groups','root'} or tree['feature_groups']!=list(GROUPS[raw['profile']]):
        raise ValueError('Tree fields/groups differ from selected profile')
    artifact=validate_policy(tree,PROFILE)
    if set(references(tree['root']))-set(allowed):raise ValueError('Unqualified runtime feature')
    def depth(n):return 0 if isinstance(n,str) else 1+max(depth(n['then']),depth(n['else']))
    if depth(tree['root'])>4:raise ValueError('Maximum decision depth including guard is four')
    # A canonical outer guard makes unsampled/missing observations continue.
    root=tree['root']
    if not isinstance(root,dict) or root['else']!='continue' or root!=guard(root['then'],EARLY):
        raise ValueError('Use the canonical availability/checkpoint guard')
    owned=deepcopy(raw);owned['eligible']=[s for s in FILTERS if s in eligible]
    identity=digest({'version':owned['version'],'eligible':owned['eligible'],'profile':owned['profile'],
        'root':tree['root'],'feature_groups':tree['feature_groups'],'runtime_profile':PROFILE.fingerprint})
    return owned,identity

def compose(name,root,profile='light19',eligible=None):
    return {'version':'selective-policy.v1','name':name,'eligible':eligible or FILTERS.copy(),
        'profile':profile,'tree':{'name':name,'feature_groups':list(GROUPS[profile]), 'root':guard(root,EARLY)}}

def matched(raw):
    def node(n):return 'continue' if isinstance(n,str) else {'if':n['if'],'then':node(n['then']),'else':node(n['else'])}
    return {**raw,'name':('matched-'+raw['name'])[:160],'tree':{**raw['tree'],'root':node(raw['tree']['root'])}}

def states(q,profile,cfg):
    pool=q['local_states' if profile=='progress34' else 'base_states'];ns=names(cfg,profile)
    return [{**s,'features':{n:s['features'].get(n) for n in ns}} for s in pool]

def first_stop(raw,q,cfg):
    from fannagent_pgvector.profiles import PROFILE
    return None if q['stratum'] not in raw['eligible'] else predict(raw['tree'],states(q,raw['profile'],cfg),PROFILE)
