"""Durable exactly-one-allocation submission; no retries after unknown dispatch."""

import argparse
import json
import subprocess
import tarfile
from pathlib import Path

from pc_common import (
    COUNTS,
    NAME,
    read,
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
    raise ValueError("A1 only: A2 native dispatch is unreleased")


def submit(package, bundle, sources):
    raise ValueError("A1 only: A2 native handoff is unreleased")


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
