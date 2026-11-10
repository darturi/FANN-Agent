"""Unpaid pricing/availability preflight; never prints or persists a credential."""
import datetime
import html
import json
import os
import re
import ssl
import urllib.request
from contract import digest

URL='https://platform.claude.com/docs/en/models/sonnet-5-5/overview'

def verify(config):
    # The existing agent runtime owns its configured local .env. Importing it
    # loads the same credential reference as earlier runs without exposing it.
    import minisweagent
    import certifi
    context=ssl.create_default_context(cafile=certifi.where())
    if config['model']!='anthropic/claude-sonnet-5-5' or config['max_attempts']!=1 or config['allowance_usd']!='0':raise ValueError('Unexpected provider contract')
    if config['input_token_bound']!=262144 or config['output_token_limit']!=8192 or config['output_limit_parameter']!='max_tokens':raise ValueError('Unexpected verified token bounds')
    if any(os.environ.get(k) for k in ('ANTHROPIC_API_BASE','ANTHROPIC_BASE_URL')):raise ValueError('Unverified provider base-URL override; no paid calls')
    request=urllib.request.Request(URL+'.md',headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(request,timeout=30,context=context) as response:body=response.read(4*1024*1024).decode()
    text=html.unescape(re.sub('<[^>]+>',' ',body));text=re.sub(r'\s+',' ',text)
    # Prefer the page's plain Markdown rendering if provided by the documentation server.
    if 'claude-sonnet-5-5' not in text:raise ValueError('Official model page is unavailable')
    for label,price in [('Input','2'),('Output','10')]:
        pattern=label+r'(?:\s+pricing)?\s*(?::|\|)?\s*\$\s*'+price+r'(?:\.0+)?\s*/\s*(?:MTok|million)'
        if not re.search(pattern,text,re.I):raise ValueError('Cannot verify current official '+label+' rate; no paid calls permitted')
    if config['input_usd_per_million']!='2' or config['output_usd_per_million']!='10':raise ValueError('Configured prices differ')
    key=os.environ.get('ANTHROPIC_API_KEY')
    if not key:raise ValueError('ANTHROPIC_API_KEY is absent in this process; supply it locally, never in a Torch package')
    req=urllib.request.Request('https://api.anthropic.com/v1/models/claude-sonnet-5-5',
        headers={'x-api-key':key,'anthropic-version':'2023-06-01'})
    with urllib.request.urlopen(req,timeout=30,context=context) as response:info=json.load(response)
    if info.get('id')!='claude-sonnet-5-5':raise ValueError('Configured model is not available to this account')
    return {'status':'verified','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'model':info['id'],'pricing_url':URL,'page_sha256':__import__('hashlib').sha256(body.encode()).hexdigest(),
        'input_usd_per_million':'2','output_usd_per_million':'10','maximum_request_usd':'0.606208',
        'paid_requests':0,'cache_control':'none','token_limits':'262144 conservative input, 8192 inclusive output'}
