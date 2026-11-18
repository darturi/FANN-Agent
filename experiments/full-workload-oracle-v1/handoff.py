"""Inspect or signal only this job's owned Python interpreter, using its cleanup handler."""

import argparse
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1"
REMOTE = r"""
import json,os,signal,socket,sys,time
from pathlib import Path
job="23544718"
mode=sys.argv[1]
source=Path("/scratch/dar579/fannagent-benchmark-evaluation-v1/oracle-headroom-20261117-v1/full-workload-oracle-v1")
marker=source.parent/"handoff-signal.json"
if mode=="signal" and marker.exists():
    saved=json.loads(marker.read_text())
    assert saved.get("signal_sent") is True,"uncertain previous handoff; do not repeat"
    print(json.dumps(saved));sys.exit(0)
found=[]
for p in Path("/proc").iterdir():
    if not p.name.isdigit():continue
    try:
        if p.stat().st_uid!=os.getuid():continue
        argv=[a.decode(errors="replace") for a in (p/"cmdline").read_bytes().split(b"\0") if a]
        if "/qual/oracle_run.py" not in argv:continue
        exe=Path(os.readlink(p/"exe")).name
        group=(p/"cgroup").read_text()
        if exe.startswith("python") and job in group:
            found.append({"pid":int(p.name),"uid":os.getuid(),"executable":exe,"cgroup":group})
    except (OSError,ProcessLookupError):pass
assert len(found)==1,"need exactly one owned source interpreter"
usage=json.loads((source/("run-"+job)/"results/attempts.json").read_text())
assert usage.get("timed_ann",0)==usage.get("warmup_ann",0)==0,"source timing already started"
record={"job_id":job,"mode":mode,"target":found[0],"node":socket.gethostname(),
        "source_attempts_before_signal":usage,"recorded_epoch":time.time(),
        "signal":"SIGALRM","signal_sent":False,
        "purpose":("graceful acquisition handoff to batched durable reservations; "
                   "all raw results retained")}
if mode=="signal":
    assert marker.parent.stat().st_uid==os.getuid()
    marker.write_text(json.dumps(record,indent=2)+"\n")
    os.kill(found[0]["pid"],signal.SIGALRM)
    record["signal_sent"]=True
    marker.write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record))
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("inspect", "signal"))
    args = parser.parse_args()
    command = [
        "/opt/slurm/bin/srun",
        "--jobid=23544718",
        "--overlap",
        "--exact",
        "--ntasks=1",
        "--cpus-per-task=1",
        "--mem=256M",
        "--time=00:01:00",
        "python3",
        "-c",
        REMOTE,
        args.mode,
    ]
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
            shlex.join(command),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-2500:] + result.stdout[-1000:])
    value = json.loads(result.stdout)
    (OUTPUT / ("handoff-" + args.mode + ".json")).write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
