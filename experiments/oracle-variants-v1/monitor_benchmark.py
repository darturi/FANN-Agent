"""Read-only progress snapshots for the balanced primary timing allocation."""

import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/oracle-variants-v1"
REMOTE = r"""
import json,subprocess,time
from pathlib import Path
s=Path("/scratch/dar579/fannagent-benchmark-evaluation-v1/oracle-variants-benchmark-20261118-v1/oracle-variants-benchmark-v1")
job=(s/'job-id').read_text().strip()
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
out={'job_id':job,'attempts':read(r/'attempts.json'),'freeze':read(r/'policy-freeze.json'),
     'reservation':read(r/'reservation.json'),'reservation_final':read(r/'reservation-final.json'),
     'receipt':read(r/'receipt.json'),'host_exit':read(r/'host-exit.json'),
     'stdout_tail':tail(s/('slurm-'+job+'.out'),5),
     'stderr_tail':tail(s/('slurm-'+job+'.err'),12),
     'archive_exists':(s/('run-'+job)/('oracle-variants-benchmark-'+job+'.tar.gz.sha256')).is_file()}
out['scheduler']=subprocess.check_output(['/opt/slurm/bin/sacct','--local','-n','-P','-j',job,
    '--format=JobIDRaw,State,ExitCode,Elapsed,ElapsedRaw,MaxRSS'],text=True).strip().splitlines()
if out['receipt'] is not None:
    keys=('status','elapsed_seconds','searches','groups','cases','source_elapsed_seconds',
          'fresh_exact_queries','fresh_qualification_queries','timing_allocations')
    out['receipt']={k:out['receipt'][k] for k in keys if k in out['receipt']}
print(json.dumps(out))
"""


def main():
    result = subprocess.run(
        [
            "ssh",
            "-S",
            "/private/tmp/fannagent-oracle-variants-20261118",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "UserKnownHostsFile=" + str(OUTPUT / "connection/known_hosts-b0-v1"),
            "-o",
            "HostKeyAlias=login.torch.hpc.nyu.edu",
            "dar579@10.32.51.120",
            shlex.join(["python3", "-c", REMOTE]),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-2500:])
    value = json.loads(result.stdout)
    value["recorded_utc"] = datetime.now(UTC).isoformat()
    (OUTPUT / "benchmark-latest-snapshot.json").write_text(json.dumps(value, indent=2) + "\n")
    with (OUTPUT / "benchmark-monitor.jsonl").open("a") as handle:
        handle.write(json.dumps(value) + "\n")
    phase = None
    for line in value["stdout_tail"]:
        if line.startswith('{"phase":'):
            phase = json.loads(line)
    state = (value["scheduler"] or ["unavailable"])[0].split("|")
    compact = {
        "job": value["job_id"],
        "state": state[1] if len(state) > 1 else state[0],
        "elapsed": state[3] if len(state) > 3 else None,
        "phase": phase,
        "frozen_cases": (value["freeze"] or {}).get("cases"),
        "reservation": value["reservation"],
        "errors": value["stderr_tail"],
        "receipt": value["receipt"],
        "host_exit": value["host_exit"],
        "archive_ready": value["archive_exists"],
    }
    print(json.dumps(compact, separators=(",", ":")))


if __name__ == "__main__":
    main()
