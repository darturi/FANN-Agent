"""Read-only snapshots of the single original-graph oracle job."""

import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1"
REMOTE = r"""
import json,subprocess,time
from pathlib import Path
s=Path("/scratch/dar579/fannagent-benchmark-evaluation-v1/oracle-headroom-20261117-v1/full-workload-oracle-v1")
job="23544718"
r=s/('run-'+job)/'results'
def read(p):
    for attempt in range(4):
        try:return json.loads(p.read_text())
        except FileNotFoundError:return None
        except json.JSONDecodeError:
            if attempt==3:raise
            time.sleep(.1)
        except OSError as e:
            if e.errno!=116 or attempt==3:raise
            time.sleep(.1)
def tail(p,n):
    try:return p.read_text().splitlines()[-n:]
    except FileNotFoundError:return []
out={'job_id':job,'attempts':read(r/'attempts.json'),'receipt':read(r/'receipt.json'),
     'host_exit':read(r/'host-exit.json'),'exposure':read(r/'exposure.json'),
     'stdout_tail':tail(s/('slurm-'+job+'.out'),5),
     'stderr_tail':tail(s/('slurm-'+job+'.err'),12),
     'archive_exists':(s/('run-'+job)/('oracle-'+job+'.tar.gz.sha256')).is_file()}
out['scheduler']=subprocess.check_output(['/opt/slurm/bin/sacct','--local','-n','-P','-j',job,
    '--format=JobIDRaw,State,ExitCode,Elapsed,MaxRSS'],text=True).strip().splitlines()
if out['receipt'] is not None:
    keys=('status','elapsed_seconds','searches','groups','cases')
    out['receipt']={k:out['receipt'][k] for k in keys}
print(json.dumps(out))
"""


def snapshot():
    result = subprocess.run(
        [
            "ssh",
            "-S",
            "/private/tmp/fannagent-oracle-20261117",
            "-o",
            "BatchMode=yes",
            "-o",
            "HostKeyAlias=login.torch.hpc.nyu.edu",
            "dar579@10.32.51.133",
            shlex.join(["python3", "-c", REMOTE]),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        error = {"returncode": result.returncode, "stderr": result.stderr[-4000:]}
        (OUTPUT / "monitor-error.json").write_text(json.dumps(error, indent=2) + "\n")
        raise RuntimeError(result.stderr[-2500:])
    value = json.loads(result.stdout)
    value["recorded_utc"] = datetime.now(UTC).isoformat()
    (OUTPUT / "latest-snapshot.json").write_text(json.dumps(value, indent=2) + "\n")
    with (OUTPUT / "monitor.jsonl").open("a") as handle:
        handle.write(json.dumps(value) + "\n")
    attempts = value["attempts"] or {}
    state = (value["scheduler"] or ["unavailable"])[0].split("|")
    compact = {
        "job": value["job_id"],
        "state": state[1] if len(state) > 1 else state[0],
        "elapsed": state[3] if len(state) > 3 else None,
        "references": attempts.get("offline_exact", 0),
        "cases": attempts.get("matched_quality", 0),
        "stops": attempts.get("forced_prefix", 0),
        "timed": attempts.get("timed_ann", 0),
        "errors": value["stderr_tail"],
        "receipt": value["receipt"],
        "host_exit": value["host_exit"],
        "archive_ready": value["archive_exists"],
    }
    print(json.dumps(compact, separators=(",", ":")))


if __name__ == "__main__":
    snapshot()
