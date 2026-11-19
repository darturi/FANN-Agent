"""Single-submit launch, read-only monitoring and verified result collection."""

import argparse
import json
import os
import shlex
import subprocess
import tarfile

from prepare_capture import WORK, sha

TARGET = "dar579@10.32.51.120"
OPTIONS = [
    "-o",
    "ControlPath="
    + os.environ.get(
        "FANNAGENT_SSH_CONTROL_PATH", "/private/tmp/fannagent-broad-oracle-20261118-v4"
    ),
    "-o",
    "BatchMode=yes",
    "-o",
    "StrictHostKeyChecking=yes",
    "-o",
    "HostKeyAlias=login.torch.hpc.nyu.edu",
    "-o",
    "UserKnownHostsFile=" + str(WORK.parent / "oracle-variants-v1/connection/known_hosts-b0-v1"),
]


def run(args, timeout=1500):
    result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr[-4000:] + result.stdout[-2000:])
    return result.stdout


def remote(command):
    return run(["ssh", *OPTIONS, TARGET, command])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("launch", "adopt", "monitor", "collect", "collect_failed")
    )
    parser.add_argument("stage", choices=("capture", "benchmark"))
    parser.add_argument("--record", help="Existing submission record name within the work folder")
    args = parser.parse_args()
    record = WORK / (args.record or args.stage + "-submission.json")
    if args.action == "adopt":
        # Reconnect to a completed submission after a client-side staging timeout.
        # This action is read-only on Torch and never submits or retries a job.
        if record.exists():
            raise RuntimeError("submission already recorded")
        name = "broad-oracle-" + args.stage + "-v1"
        parent = "/scratch/dar579/fannagent-benchmark-evaluation-v1/" + name + "-20261118"
        stage = parent + "/" + name
        job = remote(shlex.join(["cat", stage + "/job-id"])).strip()
        assert job.isdigit()
        probe = json.loads(remote(shlex.join(["cat", stage + "/.startup-preflight/check.json"])))
        assert probe["status"] == "oracle_native_startup_preflight_passed"
        archive = WORK / (name + ".tar.gz")
        assert remote(shlex.join(["sha256sum", parent + "/" + archive.name])).split()[0] == sha(
            archive
        )
        value = {
            "stage": stage,
            "job_id": job,
            "archive_sha256": sha(archive),
            "preflight": probe,
            "adopted_after_client_timeout": True,
        }
        record.write_text(json.dumps(value, indent=2) + "\n")
        print(json.dumps(value))
        return
    if args.action == "launch":
        if record.exists():
            raise RuntimeError("stage already submitted; no automatic retry")
        name = "broad-oracle-" + args.stage + "-v1"
        parent = "/scratch/dar579/fannagent-benchmark-evaluation-v1/" + name + "-20261118"
        archive = WORK / (name + ".tar.gz")
        digest = sha(archive)
        assert archive.with_suffix(".gz.sha256").read_text().split()[0] == digest
        remote(shlex.join(["mkdir", "-m700", parent]))
        run(
            [
                "scp",
                *OPTIONS,
                str(archive),
                str(archive.with_suffix(".gz.sha256")),
                TARGET + ":" + parent + "/",
            ]
        )
        command = "\n".join(
            [
                "set -euo pipefail",
                "umask 077",
                "cd " + shlex.quote(parent),
                "sha256sum -c " + name + ".tar.gz.sha256",
                "tar -xzf " + name + ".tar.gz",
                "cd " + name,
                "bash submit-" + args.stage + ".sh --submit",
            ]
        )
        log = remote(shlex.join(["bash", "-c", command]))
        (WORK / (args.stage + "-launch.log")).write_text(log)
        stage = parent + "/" + name
        job = remote(shlex.join(["cat", stage + "/job-id"])).strip()
        assert job.isdigit()
        probe = json.loads(remote(shlex.join(["cat", stage + "/.startup-preflight/check.json"])))
        assert probe["status"] == "oracle_native_startup_preflight_passed"
        value = {"stage": stage, "job_id": job, "archive_sha256": digest, "preflight": probe}
        record.write_text(json.dumps(value, indent=2) + "\n")
        print(json.dumps(value))
        return
    submission = json.loads(record.read_text())
    stage, job = submission["stage"], submission["job_id"]
    accounting = remote(
        shlex.join(
            [
                "/opt/slurm/bin/sacct",
                "--local",
                "-n",
                "-P",
                "-j",
                job,
                "--format=JobIDRaw,State,ExitCode,Elapsed,ElapsedRaw,MaxRSS",
            ]
        )
    )
    if args.action == "monitor":
        script = (
            "from pathlib import Path; import json; s=Path("
            + repr(stage)
            + "); logs={n:(s/n).read_text().splitlines()[-8:] "
            + "if (s/n).exists() else [] for n in "
            + repr(["slurm-" + job + ".out", "slurm-" + job + ".err"])
            + "}; r=s/"
            + repr("run-" + job)
            + "/'results'; p=r/'reservation.json'; "
            + "logs['reservation']=json.loads(p.read_text()) if p.exists() else None; "
            + "logs['files']={n:(r/n).stat().st_size for n in "
            + "('quality.jsonl','timing.jsonl','frontier-qualification.json','receipt.json') "
            + "if (r/n).exists()}; print(json.dumps(logs))"
        )
        value = {
            "accounting": accounting.strip().splitlines(),
            "logs": json.loads(remote(shlex.join(["python3", "-c", script]))),
        }
        (WORK / (args.stage + "-latest.json")).write_text(json.dumps(value, indent=2) + "\n")
        print(json.dumps(value))
        return
    failed_evidence = args.action == "collect_failed"
    if failed_evidence:
        assert (
            accounting.splitlines()[0].split("|")[1].startswith(("FAILED", "CANCELLED", "TIMEOUT"))
        ), accounting
    else:
        assert accounting.splitlines()[0].split("|")[1:3] == ["COMPLETED", "0:0"], accounting
    target = WORK / ("return-" + job)
    target.mkdir()
    archive = "broad-oracle-" + args.stage + "-" + job + ".tar.gz"
    remote_path = stage + "/run-" + job + "/"
    run(
        [
            "scp",
            *OPTIONS,
            TARGET + ":" + remote_path + archive,
            TARGET + ":" + remote_path + archive + ".sha256",
            str(target) + "/",
        ],
        timeout=600,
    )
    assert sha(target / archive) == (target / (archive + ".sha256")).read_text().split()[0]
    with tarfile.open(target / archive) as handle:
        handle.extractall(target, filter="data")
    (target / "accounting.psv").write_text(accounting)
    if failed_evidence:
        for suffix in ("out", "err"):
            name = "slurm-" + job + "." + suffix
            (target / name).write_text(remote(shlex.join(["cat", stage + "/" + name])))
        print(
            json.dumps(
                {
                    "return": str(target),
                    "status": "failed_evidence_preserved",
                    "inventory": sorted(p.name for p in (target / "results").iterdir()),
                }
            )
        )
        return
    receipt = json.loads((target / "results/receipt.json").read_text())
    assert json.loads((target / "results/host-exit.json").read_text()) == {
        "job_id": job,
        "exit_code": 0,
    }
    for name, digest in receipt["raw_sha256"].items():
        assert sha(target / "results" / name) == digest, name
    print(
        json.dumps(
            {
                "return": str(target),
                "status": receipt["status"],
                "elapsed": accounting.splitlines()[0].split("|")[4],
            }
        )
    )


if __name__ == "__main__":
    main()
