"""Durable exactly-one-allocation submission; no retries after unknown dispatch."""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from pc_common import (
    CONTRACT,
    COUNTS,
    NAME,
    PREFIX,
    protected,
    read,
    replace,
    save,
    sha,
    verify,
)


def command(package, record, extra):
    result = [
        "sbatch",
        "--parsable",
        "--account=" + record["account"],
        "--export=NONE",
        "--hint=nomultithread",
        "--kill-on-invalid-dep=yes",
        "--chdir=" + str(package),
    ]
    if record.get("constraint"):
        result += ["--constraint=" + record["constraint"]]
    return (
        result
        + extra
        + [
            str(package / "slurm/measure.sbatch"),
            str(package),
            record["bundle"],
            record["prepared"],
            record["campaign"],
            record["workspace"],
            record["sources"],
            record["apptainer"],
            record["host_python"],
        ]
    )


def reserve(results, package, campaign):
    # One fixed protocol identity covers accidental reuploads as well as retries.
    save(
        results / ("." + NAME + "-reservation.json"),
        {
            "campaign": str(campaign),
            "package_manifest_sha256": sha(package / "manifest.json"),
            "allocations": COUNTS["allocations"],
            "maximum_searches": COUNTS["searches_total"],
            "confirmation_queries": 0,
        },
    )


def dispatch(package, campaign, record, block, dependency=None):
    key = "block-" + str(block)
    if key in record["dispatch"]:
        raise ValueError("Known or uncertain dispatch already exists; do not repeat")
    record["dispatch"][key] = {"status": "dispatching"}
    replace(campaign / "submission.json", record)
    extra = ["--array=" + str(block), "--output=" + str(campaign / "logs" / (key + "-%A-%a.log"))]
    if dependency:
        extra += ["--dependency=afterok:" + dependency]
    try:
        result = subprocess.run(command(package, record, extra), capture_output=True, text=True)
    except BaseException:
        record["dispatch"][key] = {"status": "unknown"}
        replace(campaign / "submission.json", record)
        raise
    if result.returncode or not re.fullmatch(r"[1-9][0-9]*(;torch)?", result.stdout.strip()):
        record["dispatch"][key] = {
            "status": "rejected" if result.returncode else "unknown",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        replace(campaign / "submission.json", record)
        raise RuntimeError("Dispatch failed/uncertain; inspect this campaign, do not resubmit")
    job = result.stdout.strip().split(";")[0]
    record["jobs"][key] = job
    record["dispatch"][key] = {"status": "submitted", "job_id": job}
    replace(campaign / "submission.json", record)
    return job


def submit(package, bundle, sources):
    if (package / "submission-binding.json").exists():
        raise ValueError("Already bound; use status/collect")
    reservation = Path(
        os.environ.get("TORCH_RESULTS_ROOT", "/home/dar579/torch-reviews-results")
    ) / ("." + NAME + "-reservation.json")
    if reservation.exists():
        raise ValueError(
            "Allocation already reserved; preserve it and reconcile status; never resubmit"
        )
    cfg = verify(package)
    if cfg["synthetic_fixture"] or cfg["local_readiness"] != "source_checks_passed":
        raise ValueError("Synthetic/unready package cannot submit")
    verify(package, bundle)
    if os.uname().sysname != "Linux" or os.uname().machine != "x86_64":
        raise ValueError("Submit from Torch login, not a Mac")
    before = protected(package, sources)
    original = read(package / "frozen/experiment.json")
    prepared = Path(original["source_prepared"])
    scratch = Path(os.environ["TORCH_SCRATCH_ROOT"])
    results = Path(os.environ["TORCH_RESULTS_ROOT"])
    apptainer = Path(os.environ.get("TORCH_APPTAINER_BIN", "/share/apps/apptainer/bin/apptainer"))
    account = os.environ["TORCH_SLURM_ACCOUNT"]
    if not re.fullmatch(r"torch_pr_[A-Za-z0-9_]+", account):
        raise ValueError("Set an active Torch Slurm account")
    for path in (package, bundle, sources, prepared, scratch, results, apptainer):
        if not path.is_absolute() or any(c in str(path) for c in (":", ",", "\n")):
            raise ValueError("Unsupported Apptainer path")
    ready = read(prepared / "READY.json")
    if ready["architecture"] != "x86_64" or ready["image_sha256"] != original["image_sha256"]:
        raise ValueError("Prepared image/architecture differs")
    if read(prepared / "database-identity.json") != read(package / "frozen/source-index.json"):
        raise ValueError("Prepared index differs; do not rebuild it for this comparison")
    if not os.access(apptainer, os.X_OK):
        raise ValueError("Apptainer unavailable")
    scratch.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    from pc_resources import preflight

    resources = preflight(Path(CONTRACT["retained_source_work"]), scratch, results)
    host_python = Path(sys.executable).resolve()
    if not host_python.is_absolute() or not os.access(host_python, os.X_OK):
        raise ValueError("Cannot resolve executable absolute host Python")
    record = {
        "host_python": str(host_python),
        "account": account,
        "constraint": os.environ.get("TORCH_CPU_CONSTRAINT"),
        "bundle": str(bundle),
        "prepared": str(prepared),
        "sources": str(sources),
        "workspace": str(scratch),
        "campaign": str(results / "dry-run"),
        "apptainer": str(apptainer),
    }
    subprocess.run(
        command(package, record, ["--test-only", "--array=0", "--output=/dev/null"]), check=True
    )
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    campaign = Path(tempfile.mkdtemp(prefix=PREFIX + stamp + ".", dir=results))
    reserve(results, package, campaign)
    (campaign / "logs").mkdir()
    workspace = Path(tempfile.mkdtemp(prefix="partial-calibration-v1-launch-fix.", dir=scratch))
    record.update(
        package=str(package),
        campaign=str(campaign),
        workspace=str(workspace),
        status="submitting",
        jobs={},
        dispatch={},
        counts=COUNTS,
        package_manifest_sha256=sha(package / "manifest.json"),
        provider_calls=0,
        confirmation_queries=0,
    )
    save(campaign / "resource-preflight-login.json", resources)
    save(campaign / "protected-source-before.json", before)
    save(campaign / "submission.json", record)
    save(
        package / "submission-binding.json",
        {"campaign": str(campaign), "package_manifest_sha256": sha(package / "manifest.json")},
    )
    jobs = []
    try:
        for block in range(COUNTS["allocations"]):
            jobs.append(dispatch(package, campaign, record, block, jobs[-1] if jobs else None))
        record["status"] = "submitted"
        replace(campaign / "submission.json", record)
    except BaseException:
        if jobs:
            subprocess.run(["scancel", *jobs], capture_output=True, text=True)
        record["status"] = "submission_incomplete"
        replace(campaign / "submission.json", record)
        raise
    print(json.dumps(record, indent=2))


def bound(package):
    verify(package)
    binding = read(package / "submission-binding.json")
    if binding["package_manifest_sha256"] != sha(package / "manifest.json"):
        raise ValueError("Binding differs")
    campaign = Path(binding["campaign"])
    record = read(campaign / "submission.json")
    if record["package"] != str(package):
        raise ValueError("Campaign belongs to another package")
    return campaign, record


def status(package):
    campaign, record = bound(package)
    print("Campaign: " + str(campaign))
    print(
        json.dumps(
            {"dispatch": record["dispatch"], "limits": COUNTS, "provider_calls": 0}, indent=2
        )
    )
    for block in range(COUNTS["allocations"]):
        for name in (
            "progress.json",
            "status.json",
            "failure.json",
            "host-failure.json",
            "host-exit.json",
        ):
            path = campaign / "run" / name
            if path.exists():
                print(str(block) + " " + name + ": " + json.dumps(read(path)))
    if record["jobs"]:
        jobs = ",".join(record["jobs"].values())
        subprocess.run(
            ["sacct", "-j", jobs, "--format=JobID,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS"]
        )
        subprocess.run(["squeue", "-j", jobs])


def collect(package):
    campaign, record = bound(package)
    archive = Path(str(campaign) + ".tar.gz")
    if archive.exists():
        if sha(archive) != Path(str(archive) + ".sha256").read_text().split()[0]:
            raise ValueError("Existing archive differs")
        print(str(archive))
        return
    exits = [campaign / "run" / "host-exit.json" for i in range(COUNTS["allocations"])]
    complete = all(p.exists() and read(p)["exit_code"] == 0 for p in exits)
    if len(record["jobs"]) != COUNTS["allocations"] or any(
        d["status"] != "submitted" for d in record["dispatch"].values()
    ):
        raise ValueError("Unknown/partial submission; inspect status before collecting")
    queued = subprocess.run(
        ["squeue", "-h", "-j", ",".join(record["jobs"].values())],
        capture_output=True,
        text=True,
    )
    if queued.returncode == 0 and queued.stdout.strip():
        raise ValueError("Jobs are still queued/running; use status")
    accounting = subprocess.run(
        [
            "sacct",
            "-n",
            "-P",
            "-j",
            ",".join(record["jobs"].values()),
            "--format=JobID,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    terminal = {
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "TIMEOUT",
        "OUT_OF_MEMORY",
        "NODE_FAIL",
        "BOOT_FAIL",
        "DEADLINE",
        "PREEMPTED",
    }
    states = {}
    for line in accounting.stdout.splitlines():
        parts = line.split("|")
        if len(parts) >= 3:
            states[parts[0]] = parts[1].split()[0].rstrip("+")
    for job in record["jobs"].values():
        if states.get(job + "_0", states.get(job)) not in terminal:
            raise ValueError("Scheduler completion unknown; preserve binding and inspect status")
    if not (campaign / "scheduler-evidence.json").exists():
        save(
            campaign / "scheduler-evidence.json",
            {
                "squeue_returncode": queued.returncode,
                "squeue_stdout": queued.stdout,
                "squeue_stderr": queued.stderr,
                "sacct_stdout": accounting.stdout,
                "terminal_verified": True,
            },
        )
    if not complete:
        (campaign / "analysis").mkdir(exist_ok=True)
        save(
            campaign / "analysis/failure-summary.json",
            {
                "status": "incomplete_or_failed",
                "provider_calls": 0,
                "confirmation_queries": 0,
                "canonical_acceptance_established": False,
                "note": (
                    "All known jobs left the queue; successful raw blocks are incomplete. "
                    "No performance analysis."
                ),
            },
        )
    else:
        (campaign / "analysis").mkdir(exist_ok=True)
        save(
            campaign / "analysis/acquisition-summary.json",
            dict(
                scope="raw_only_no_remote_timing_verdict",
                complete_acquisition=True,
                provider_calls=0,
                confirmation_queries=0,
            ),
        )
    with tarfile.open(archive, "x:gz") as tar:
        for path in sorted(campaign.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlink in returned data")
            if path.is_file():
                tar.add(
                    path,
                    arcname=campaign.name + "/" + str(path.relative_to(campaign)),
                    recursive=False,
                )
    with Path(str(archive) + ".sha256").open("x") as handle:
        handle.write(sha(archive) + "  " + archive.name + "\n")
    print("Download archive and checksum: " + str(archive))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["verify", "submit", "status", "collect"])
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    if args.command == "submit":
        if len(args.paths) != 2:
            parser.error("submit ORIGINAL_BUNDLE SOURCE_RESULTS_ROOT")
        submit(package, *[Path(p).resolve() for p in args.paths])
    elif args.paths:
        parser.error("This command uses the durable package binding and takes no paths")
    elif args.command == "verify":
        print(json.dumps(verify(package)["counts"], indent=2))
    elif args.command == "status":
        status(package)
    else:
        collect(package)
