import json,sys,tarfile
from pathlib import Path
p=Path('/tmp/legacy-load');p.mkdir()
with tarfile.open('/qual/original-package.tar.gz','r:gz') as t:t.extractall(p,filter='data')
package=p/'reviews-persistent-batch-native-v1';sys.path.insert(0,str(package))
from rb_native import load_stage
stage=load_stage(package,'b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc')
runner,backend=stage.frozen.execution.load_backend(stage.source)
print(json.dumps({'status':'legacy_restore_loader_passed','graph':stage.index['index_identity'] if 'index_identity' in stage.index else stage.index,'backend_loaded':backend.__name__},sort_keys=True))
