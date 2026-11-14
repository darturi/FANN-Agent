"""Change only the GUC search-effort ceiling in the qualified all-filter source."""
from pathlib import Path
from shutil import copytree
import hashlib,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'runtime/engine';DEST=HERE/'engine'
copytree(OLD,DEST,ignore=lambda p,n:[name for name in n if name.endswith(('.o','.so','.bc')) or name=='vector--0.8.6.sql'])
changes={}
for name,old,new in [('src/hnsw.h','#define HNSW_MAX_EF_SEARCH\t\t1000','#define HNSW_MAX_EF_SEARCH\t\t8192'),('src/hnsw.c','"Valid range is 1..1000."','"Valid range is 1..8192 (research extended-effort runtime)."')]:
 p=DEST/name;s=p.read_text();assert s.count(old)==1;s=s.replace(old,new);p.write_text(s);changes[name]={'before_sha256':hashlib.sha256((OLD/name).read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
for p in OLD.rglob('*'):
 if p.is_file() and p.suffix in ('.c','.h') and str(p.relative_to(OLD)) not in changes:assert (DEST/p.relative_to(OLD)).read_bytes()==p.read_bytes()
(HERE/'source-change.json').write_text(json.dumps({'only_source_changes':changes,'algorithm_changes':False,'graph_changes':False,'stock_maximum_ef_search':1000,'research_maximum_ef_search':8192},indent=2)+'\n')
