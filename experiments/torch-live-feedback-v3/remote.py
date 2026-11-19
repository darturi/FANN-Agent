"""Explicit single submission, read-only recovery, final comparison and collection."""

import argparse
import json
import os
import shlex
import subprocess
import tarfile
from pathlib import Path

from client import TorchClient
from limits import read, sha, write

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-live-feedback-v3/run-v1"
HOST = "dar579@10.32.51.120"
PARENT = "/scratch/dar579/fannagent-benchmark-evaluation-v1/agent-v3-20261119-v1"
STAGE = PARENT + "/kit"
CONTROL = os.environ.get("FANNAGENT_SSH_CONTROL_PATH", "/private/tmp/fannagent-agent-v3-20261119")
KNOWN = ROOT / (
    "trials/fannagent-benchmark-evaluation-v1/reviews-small/"
    "oracle-variants-v1/connection/known_hosts-b0-v1"
)
OPTIONS = [
    "-o",
    "ControlPath=" + CONTROL,
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=10",
    "-o",
    "StrictHostKeyChecking=yes",
    "-o",
    "HostKeyAlias=login.torch.hpc.nyu.edu",
    "-o",
    "UserKnownHostsFile=" + str(KNOWN),
]


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True, check=False, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] + result.stdout[-3000:])
    return result.stdout


def ssh(command, timeout=60):
    return run(["ssh", *OPTIONS, HOST, shlex.join(command)], timeout=timeout)


def client():
    return TorchClient(HOST, STAGE, WORK / "client", control_path=CONTROL, known_hosts=KNOWN)


def launch():
    if (WORK / "submission-intent.json").exists():
        raise ValueError(
            "submission already attempted; inspect job-id and accounting, never resubmit"
        )
    archive = WORK / "kit.tar.gz"
    if archive.with_suffix(".gz.sha256").read_text().split()[0] != sha(archive):
        raise ValueError("archive digest differs")
    # A new stage is required; existing paths are never reused.
    ssh(["mkdir", "-m", "700", PARENT])
    run(
        [
            "scp",
            *OPTIONS,
            str(archive),
            str(archive.with_suffix(".gz.sha256")),
            HOST + ":" + PARENT + "/",
        ],
        timeout=600,
    )
    if ssh(["sha256sum", PARENT + "/kit.tar.gz"]).split()[0] != sha(archive):
        raise ValueError("uploaded archive differs")
    ssh(["tar", "-xzf", PARENT + "/kit.tar.gz", "-C", PARENT], timeout=180)
    # Host readiness checks precede the permanent submission-intent marker.
    ssh(["test", "-x", "/share/apps/apptainer/bin/apptainer"])
    ssh(["bash", STAGE + "/submit.sh", "--check"], timeout=120)
    write(
        WORK / "submission-intent.json",
        {
            "host": HOST,
            "stage": STAGE,
            "archive_sha256": sha(archive),
            "user_request": (
                "Update the agent controller to use the broader v3 policy language, "
                "then run an agent experiment and compare its latency savings "
                "with oracle_feasible."
            ),
            "allocation_limit": 1,
            "wall_seconds": 21600,
            "attempt_limit": 300000,
            "automatic_retry": False,
        },
    )
    output = ssh(["bash", STAGE + "/submit.sh", "--submit"], timeout=120)
    (WORK / "submission-output.txt").write_text(output)
    job = ssh(["cat", STAGE + "/job-id"]).strip()
    if not job.isdigit():
        raise ValueError("unknown submission outcome; audit without retry")
    write(
        WORK / "submission.json",
        {
            "job_id": job,
            "host": HOST,
            "stage": STAGE,
            "kit_sha256": sha(WORK / "kit/SHA256SUMS"),
            "automatic_retry": False,
        },
    )
    return read(WORK / "submission.json")


def finalize():
    folder = WORK / "agent-packet/live"
    state = read(folder / "tools.json")
    ids = state.get("nominees", [])
    if state["terminal"] == "development_candidate_frozen" and len(ids) == 1:
        record = state["registry"][ids[0]]
        policy = record["policy"]
        reason = "agent-selected frozen development candidate"
    else:
        policy = {
            "schema": "fannagent.broad-stop.v3",
            "name": "agent-native-outcome",
            "rationale": (
                "Agent abstained or ended without a submission; native remains the outcome."
            ),
            "fuel": 2000000,
            "state_slots": 0,
            "programs": {},
        }
        reason = "native outcome; no researcher fallback candidate"
    freeze = WORK / "final-freeze.json"
    if freeze.exists():
        raise ValueError("final comparison already attempted; recover its existing request")
    write(
        freeze,
        {
            "policy": policy,
            "agent_state_sha256": sha(folder / "tools.json"),
            "agent_disposition_sha256": sha(folder / "disposition.json"),
            "reason": reason,
            "test_results_seen_by_agent": False,
            "automatic_retry": False,
        },
    )
    # TorchClient saves the identity before delivery; uncertain requests are not retried.
    result = client().evaluate([policy], mode="final")
    write(WORK / "final-response.json", result)
    return result


def collect():
    job = read(WORK / "submission.json")["job_id"]
    accounting = ssh(
        [
            "/opt/slurm/bin/sacct",
            "-j",
            job,
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State,ExitCode,Elapsed,ElapsedRaw,MaxRSS",
        ]
    )
    if not accounting.strip() or accounting.splitlines()[0].split("|")[1] in (
        "RUNNING",
        "PENDING",
        "COMPLETING",
    ):
        raise ValueError("job not terminal; collect later without resubmitting")
    target = WORK / ("return-" + job)
    target.mkdir()
    archive = f"return-{job}.tar.gz"
    run(
        [
            "scp",
            *OPTIONS,
            HOST + ":" + STAGE + "/" + archive,
            HOST + ":" + STAGE + "/" + archive + ".sha256",
            str(target) + "/",
        ],
        timeout=600,
    )
    if sha(target / archive) != (target / (archive + ".sha256")).read_text().split()[0]:
        raise ValueError("return archive differs")
    with tarfile.open(target / archive) as f:
        f.extractall(target, filter="data")
    (target / "accounting.psv").write_text(accounting)
    for suffix in ("out", "err"):
        (target / ("slurm-" + job + "." + suffix)).write_text(
            ssh(["cat", STAGE + "/slurm-" + job + "." + suffix])
        )
    return {"return": str(target), "accounting": accounting.splitlines()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=("launch", "status", "qualify", "final", "collect"))
    a = p.parse_args()
    if a.operation == "launch":
        result = launch()
    elif a.operation == "status":
        result = client().call("status")
    elif a.operation == "qualify":
        result = client().evaluate(
            read(WORK / "kit/diagnostic-policies.json"), mode="qualification"
        )
        write(WORK / "qualification.json", result)
    elif a.operation == "final":
        result = finalize()
    else:
        result = collect()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
