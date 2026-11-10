"""Pinned isolated learner; immutable evidence and a private writable analysis mount."""
import json
import os
import subprocess
import time
import uuid

from contract import save as once
from fannagent.environment import docker
from fannagent.submission import validate_action


class SandboxLimit(RuntimeError):
    pass


class Sandbox:
    def __init__(self, evidence, work, broker, image, store):
        self.store,self.broker=store,broker
        self.name='fannagent-proposals-'+uuid.uuid4().hex[:12]
        self.turn_id=None;self.commands=store.get('commands_used',0);self.started=time.monotonic()-store.get('active_seconds_used',0.)
        from fannagent.build_workspace import client_hash
        info=json.loads(docker('image','inspect',image))[0]
        if (info['Config'].get('Labels') or {}).get('io.fannagent.tool_client')!=client_hash():
            raise ValueError('Pinned sandbox client differs')
        store.set('sandbox_container',self.name)
        docker('run','-d','--name',self.name,'--label','io.fannagent.proposal_run='+str(store.root),
            '--read-only','--user',str(os.getuid())+':'+str(os.getgid()),'--cap-drop=ALL',
            '--security-opt=no-new-privileges','--pids-limit=128','--memory=4g','--cpus=2',
            '--tmpfs','/tmp:rw,size=256m','--network=none',
            '--mount','type=bind,source='+str(evidence)+',target=/evidence,readonly',
            '--mount','type=bind,source='+str(work)+',target=/workspace',
            '-e','FANNAGENT_QUEUE=/workspace/.broker','-e','FANNAGENT_TOKEN='+broker.token,
            '-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1','-w','/workspace',image,'sleep','infinity')
        state=json.loads(docker('inspect',self.name))[0]
        if state['HostConfig']['NetworkMode']!='none' or not state['HostConfig']['ReadonlyRootfs']:
            self.close();raise ValueError('Isolation differs')
        mounts={m['Destination']:m for m in state['Mounts']}
        if mounts['/evidence']['RW'] or set(mounts)-{'/workspace','/evidence','/tmp'}:
            self.close();raise ValueError('Unexpected sandbox mount')

    def execute(self, action):
        if self.commands>=120 or time.monotonic()-self.started>=3600:
            raise SandboxLimit('command or wall-time cap')
        command=validate_action(action);self.commands+=1;self.store.set('commands_used',self.commands)
        begin=time.monotonic()
        record={'index':self.commands,'command':command,'started_unix':time.time()}
        try:
            result=subprocess.run(['docker','exec','-e','FANNAGENT_TURN_ID='+str(self.turn_id),
                self.name,'bash','-lc',command],text=True,capture_output=True,
                timeout=min(60,3600-(time.monotonic()-self.started)))
            record.update(returncode=result.returncode,output=(result.stdout+result.stderr)[-64000:])
            self.broker.tools.submissions.record(self.turn_id,success=result.returncode==0)
            # CPU time is cumulative cgroup accounting, including child Python/NumPy.
            cpu=subprocess.run(['docker','exec',self.name,'cat','/sys/fs/cgroup/cpu.stat'],
                text=True,capture_output=True,timeout=10)
            record['cgroup_cpu_stat']=cpu.stdout
        except subprocess.TimeoutExpired:
            record.update(returncode=124,output='Command timed out; sandbox stopped')
            self.close()
            raise SandboxLimit('command timeout') from None
        finally:
            record['elapsed_seconds']=time.monotonic()-begin
            once(self.store.root/'commands'/('%03d.json'%self.commands),record)
        return {'returncode':record['returncode'],'output':record['output']}

    def close(self):
        if self.name:
            docker('rm','-f',self.name);self.name=None
            self.store.set('sandbox_container',None)
