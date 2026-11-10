"""Sandbox transport and syntax helpers. No host paths or credentials."""
import json
from pathlib import Path
import subprocess

def call(operation,**args):
    p=subprocess.run(['fannagent-tool',operation,json.dumps(args,allow_nan=False)],capture_output=True,text=True,timeout=55)
    value=json.loads(p.stdout)
    if p.returncode or not value.get('ok'):raise RuntimeError(value)
    return value['result']

def combine(op,x):
    if len(x)==1:return x[0]
    n=len(x)//2;return {'op':op,'args':[combine(op,x[:n]),combine(op,x[n:])]}

def features(x):
    if isinstance(x,dict):return ({x['feature']} if 'feature' in x else set())|set().union(*(features(v) for v in x.values()))
    if isinstance(x,list):return set().union(*(features(v) for v in x))
    return set()

def policy(name,root,profile='light19',eligible=None):
    c=json.loads(Path('/evidence/context.json').read_text());ns=sorted(features(root)|{'checkpoint_index'})
    check=combine('and',[{'op':'is_available','args':[{'feature':n}]} for n in ns])
    allowed=combine('or',[{'op':'eq','args':[{'feature':'checkpoint_index'},{'int':cp}]} for cp in [1,2,4,8,16,32,64,128]])
    return {'version':'selective-policy.v1','name':name,'eligible':eligible or ['unfiltered','votes32','votes108'],
        'profile':profile,'tree':{'name':name,'feature_groups':c['profiles'][profile]['groups'],
        'root':{'if':{'op':'and','args':[check,allowed]},'then':root,'else':'continue'}}}
