"""Upload a sealed kit, preflight the actual backend, and submit exactly once."""

import hashlib
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/oracle-variants-v1"
PARENT = "/scratch/dar579/fannagent-benchmark-evaluation-v1/oracle-variants-benchmark-20261118-v1"
STAGE = PARENT + "/oracle-variants-benchmark-v1"
TARGET = "dar579@10.32.51.120"
OPTIONS = [
    "-o",
    "ControlPath=/private/tmp/fannagent-oracle-variants-20261118",
    "-o",
    "BatchMode=yes",
    "-o",
    "StrictHostKeyChecking=yes",
    "-o",
    "HostKeyAlias=login.torch.hpc.nyu.edu",
    "-o",
    "UserKnownHostsFile=" + str(WORK / "connection/known_hosts-b0-v1"),
]


def main():
    if (WORK / "benchmark-submission.json").exists():
        raise RuntimeError("This comparison has already been submitted")
    kit = WORK / "benchmark-kit-v1"
    plan = json.loads((kit / "timing-plan.json").read_text())
    assert plan["physical_cpus"] == 4 and plan["memory_gib"] == 48
    assert plan["aggregate_max_seconds"] <= plan["aggregate_allocation_cap_seconds"] == 21600
    assert plan["timed_queries"] == 448000 and plan["quality_queries"] == 56000
    for name in ("variants_benchmark.py", "variants_analyse.py"):
        assert (kit / name).read_bytes() == (WORK / "fixture-persistent-v2" / name).read_bytes()
    archive = WORK / "oracle-variants-benchmark-v1.tar.gz"
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert archive.with_suffix(".gz.sha256").read_text().split()[0] == digest
    with (WORK / "benchmark-launch.log").open("x") as log:

        def run(args):
            result = subprocess.run(args, text=True, capture_output=True, timeout=300)
            log.write(result.stdout + result.stderr)
            log.flush()
            if result.returncode:
                raise RuntimeError(result.stderr[-2000:] or result.stdout[-2000:])
            return result.stdout

        run(["ssh", *OPTIONS, TARGET, shlex.join(["mkdir", "-m700", PARENT])])
        run(
            [
                "scp",
                *OPTIONS,
                str(archive),
                str(archive.with_suffix(".gz.sha256")),
                TARGET + ":" + PARENT + "/",
            ]
        )
        script = "\n".join(
            [
                "set -euo pipefail",
                "umask 077",
                "cd " + shlex.quote(PARENT),
                "sha256sum -c oracle-variants-benchmark-v1.tar.gz.sha256",
                "tar -xzf oracle-variants-benchmark-v1.tar.gz",
                "cd oracle-variants-benchmark-v1",
                "bash submit-benchmark.sh --check",
                "bash submit-benchmark.sh --submit",
            ]
        )
        run(["ssh", *OPTIONS, TARGET, shlex.join(["bash", "-c", script])])
        job = run(["ssh", *OPTIONS, TARGET, shlex.join(["cat", STAGE + "/job-id"])]).strip()
        assert job.isdigit()
        probe = json.loads(
            run(
                [
                    "ssh",
                    *OPTIONS,
                    TARGET,
                    shlex.join(["cat", STAGE + "/.startup-preflight/check.json"]),
                ]
            )
        )
        assert probe["status"] == "oracle_native_startup_preflight_passed"
        result = {
            "job_id": job,
            "stage": STAGE,
            "archive_sha256": digest,
            "native_preflight": probe,
            "plan": plan,
        }
        (WORK / "benchmark-submission.json").write_text(json.dumps(result, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "job_id": job,
                    "stage": STAGE,
                    "native_preflight": probe,
                    "aggregate_max_seconds": plan["aggregate_max_seconds"],
                }
            )
        )


if __name__ == "__main__":
    main()
