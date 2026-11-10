"""Local offline tests. Native database is synthetic; no provider calls or Torch jobs."""
import argparse
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from contract import HERE,ROOT,SOURCE,OUTPUT,sha,digest,replace

FIXTURE='sha256:a05358202e42cc093848b563db8b15ec376060d4a1f2fb0e1970522bc1f5dcd6'
COMPILER='sha256:ae86d11d19bbf9f78caa716df09a4e4bce2539810322b2e1c5248c6d28ae2eef'

def native():
    from contract import bootstrap,SOURCE_MANIFEST
    bootstrap()
    from evidence import source_config
    source_config()
    from study import source_hashes,native_source_hashes
    source_before=native_source_hashes()
    validation=OUTPUT/'validation';validation.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='native-',dir=validation));out.chmod(0o777)
    bundle=out/'bundle';bundle.mkdir();(bundle/'inputs').mkdir()
    shutil.copyfile(ROOT/'trials/torch-reviews-first/runner.py',bundle/'runner.py')
    shutil.copyfile(ROOT/'trials/torch-reviews-first/inputs/local-identity.json',bundle/'inputs/local-identity.json')
    shutil.copytree(SOURCE/'vendor',bundle/'vendor')
    shutil.copytree(ROOT/'agent/src/fannagent',bundle/'vendor/fannagent',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    previous=ROOT/'trials/torch-reviews-results/feature-data-ablation-v1/validation/previous-static-arm64-vector.so'
    build=['docker','run','--rm','--network','none','--read-only','--cpus','2','--memory','4g','--tmpfs','/tmp:rw,size=2g',
        '--mount','type=bind,source='+str(SOURCE/'engine')+',target=/engine,readonly',
        '--mount','type=bind,source='+str(out)+',target=/output',COMPILER,'sh','-c',
        'set -eu\ncp -R /engine /tmp/engine\nmake -C /tmp/engine clean PG_CONFIG=/usr/bin/pg_config\nmake -C /tmp/engine -j2 OPTFLAGS= PG_CONFIG=/usr/bin/pg_config\ncp /tmp/engine/vector.so /output/vector.so']
    cache=validation/'compiler-cache.json'
    pin=json.loads(cache.read_text()) if cache.exists() else None
    if pin and pin['source_manifest_sha256']==SOURCE_MANIFEST and pin['compiler']==COMPILER and sha(pin['path'])==pin['module_sha256']:
        shutil.copyfile(pin['path'],out/'vector.so')
        (out/'build.log').write_text('Reused verified unchanged local fixture module: '+pin['module_sha256']+'\n')
    else:
        with (out/'build.log').open('w') as log:subprocess.run(build,check=True,stdout=log,stderr=subprocess.STDOUT)
        replace(cache,{'source_manifest_sha256':SOURCE_MANIFEST,'compiler':COMPILER,'path':str(out/'vector.so'),'module_sha256':sha(out/'vector.so')})
    cmd=['docker','run','--rm','--network','none','--read-only','--cpus','2','--memory','4g',
        '--tmpfs','/tmp:rw,size=2g','--tmpfs','/usr/lib/postgresql/17/lib:rw,exec,mode=1777,size=256m']
    for source,target,ro in [(HERE,'/study',True),(SOURCE,'/patch',True),(bundle,'/opt/torch-reviews',True),
        (out,'/output',False),(out,'/candidate',True),(previous,'/previous/vector.so',True)]:
        cmd+=['--mount','type=bind,source='+str(source)+',target='+target+(',readonly' if ro else '')]
    cmd+=[FIXTURE,'runuser','-u','postgres','--','env','PATH=/usr/lib/postgresql/17/bin:/opt/size-fixture-python/bin:/usr/bin:/bin',
        'PYTHONPATH=/study:/patch/vendor','PYTHONDONTWRITEBYTECODE=1','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1',
        '/opt/size-fixture-python/bin/python','/study/native_check.py']
    with (out/'native.log').open('w') as log:subprocess.run(cmd,check=True,stdout=log,stderr=subprocess.STDOUT)
    result=json.loads((out/'native-checks.json').read_text())
    if source_before!=native_source_hashes():raise RuntimeError('Native sources changed during validation; rerun the final source state')
    result.update(study_source_sha256=digest(source_hashes()),native_source_sha256=digest(source_before),fixture_image=FIXTURE,compiler_image=COMPILER,
        checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),logs=str(out),
        x86_Torch_module_rebuilt=False,real_Reviews_measurements=0)
    replace(validation/'native-checks.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['unit','native']);a=p.parse_args()
    if a.command=='native':native()
    else:subprocess.run([sys.executable,str(HERE/'test_study.py')],check=True)
