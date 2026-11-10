"""Exactly one native zero-DB correctness allocation; no automatic retry."""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from common import NAME, PREFIX, read, replace, save, sha, verify


def scheduler(package, r, extra):
    return [
        "sbatch",
        "--parsable",
        "--export=NONE",
        "--hint=nomultithread",
        "--account=" + r["account"],
        "--chdir=" + str(package),
        *extra,
        str(package / "LAUNCHER.sh"),
        str(package),
        r["run"],
        r["scratch"],
        r["image"],
        r["apptainer"],
        r["python"],
    ]


def dispatch(package, campaign, r):
    if r["dispatch"] is not None:
        raise RuntimeError("Known/uncertain dispatch; never repeat")
    manifest = sha(package / "manifest.json")
    persisted = read(campaign / "submission.json")
    if (
        persisted["dispatch"] is not None
        or persisted["package_manifest_sha256"] != manifest
        or r["package_manifest_sha256"] != manifest
    ):
        raise RuntimeError("Durable dispatch already known/uncertain or wrong capsule")
    for item in (
        read(package / "submission-binding.json"),
        read(campaign.parent / ("." + NAME + "-reservation.json")),
    ):
        if item["campaign"] != str(campaign) or item["package_manifest_sha256"] != manifest:
            raise RuntimeError("Durable reservation/binding differs")
    r["dispatch"] = dict(status="dispatching")
    replace(campaign / "submission.json", r)
    try:
        result = subprocess.run(
            scheduler(package, r, ["--output=" + str(campaign / "scheduler-%j.log")]),
            capture_output=True,
            text=True,
        )
    except BaseException:
        r["dispatch"] = dict(status="unknown")
        replace(campaign / "submission.json", r)
        raise
    if result.returncode or not re.fullmatch(r"[1-9][0-9]*(;torch)?", result.stdout.strip()):
        r["dispatch"] = dict(
            status="rejected" if result.returncode else "unknown",
            stdout=result.stdout,
            stderr=result.stderr,
        )
        replace(campaign / "submission.json", r)
        raise RuntimeError("Dispatch failed/uncertain; preserve binding, no retry")
    r["job_id"] = result.stdout.strip().split(";")[0]
    r["dispatch"] = dict(status="submitted", job_id=r["job_id"])
    replace(campaign / "submission.json", r)


def submit(package):
    c = verify(package)
    if (package / "submission-binding.json").exists():
        raise RuntimeError("Already bound; use status/collect")
    results = Path(os.environ["TORCH_RESULTS_ROOT"])
    scratch = Path(os.environ["TORCH_SCRATCH_ROOT"])
    reservation = results / ("." + NAME + "-reservation.json")
    if reservation.exists():
        raise RuntimeError("Allowance already reserved; preserve and reconcile, no resubmit")
    if os.uname().sysname != "Linux" or os.uname().machine != "x86_64":
        raise RuntimeError("Submit on Torch login")
    account = os.environ["TORCH_SLURM_ACCOUNT"]
    if not re.fullmatch(r"torch_pr_[A-Za-z0-9_]+", account):
        raise ValueError("Active Torch account required")
    image = Path("/home/dar579/torch-reviews-first/images/runtime.sif")
    apptainer = Path(os.environ.get("TORCH_APPTAINER_BIN", "/share/apps/apptainer/bin/apptainer"))
    python = Path(sys.executable).resolve()
    for p in (package, results, scratch, image, apptainer, python):
        if not p.is_absolute() or any(x in str(p) for x in (":", ",", "\n")):
            raise ValueError("Unsupported absolute path")
    if not image.is_file() or not os.access(apptainer, os.X_OK) or not os.access(python, os.X_OK):
        raise RuntimeError("Image/launcher unavailable")
    from quota_base import quota_report

    q = subprocess.run(["myquota"], text=True, capture_output=True, check=True, timeout=30)
    quota = quota_report(q.stdout)
    for fs, path, need in [
        ("/scratch", scratch, c["limits"]["scratch_required_bytes"]),
        ("/home", results, c["limits"]["home_return_required_bytes"]),
    ]:
        if min(shutil.disk_usage(path).free, quota[fs]["space_available_lower"]) < need:
            raise RuntimeError("Insufficient conservative quota/free space: " + fs)
        st = os.statvfs(path)
        if min(st.f_favail, quota[fs]["inodes_available_lower"]) < c["storage_headroom_files"][fs]:
            raise RuntimeError("Insufficient conservative file headroom: " + fs)
    r = dict(
        account=account,
        python=str(python),
        image=str(image),
        apptainer=str(apptainer),
        scratch=str(scratch),
        run=str(results / "dry-run"),
    )
    subprocess.run(scheduler(package, r, ["--test-only", "--output=/dev/null"]), check=True)
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    campaign = Path(tempfile.mkdtemp(prefix=PREFIX + stamp + ".", dir=results))
    manifest = sha(package / "manifest.json")
    save(
        reservation,
        dict(
            campaign=str(campaign),
            package_manifest_sha256=manifest,
            allocations=1,
            SQL=0,
            searches=0,
        ),
    )
    (campaign / "run").mkdir()
    r.update(
        run=str(campaign / "run"),
        package=str(package),
        campaign=str(campaign),
        package_manifest_sha256=manifest,
        dispatch=None,
        job_id=None,
    )
    save(campaign / "submission.json", r)
    save(campaign / "quota-preflight.json", dict(stdout=q.stdout, quota=quota))
    save(
        package / "submission-binding.json",
        dict(campaign=str(campaign), package_manifest_sha256=manifest),
    )
    dispatch(package, campaign, r)
    print(json.dumps(r, indent=2))


def bound(package):
    verify(package)
    b = read(package / "submission-binding.json")
    campaign = Path(b["campaign"])
    r = read(campaign / "submission.json")
    if (
        b["package_manifest_sha256"] != sha(package / "manifest.json")
        or r["package_manifest_sha256"] != b["package_manifest_sha256"]
        or r["package"] != str(package)
    ):
        raise ValueError("Binding identity differs")
    return campaign, r


def status(package):
    if not (package / "submission-binding.json").exists():
        print("Not submitted: no bound native compatibility job")
        return
    campaign, r = bound(package)
    print("Campaign: " + str(campaign))
    print(json.dumps(r["dispatch"], indent=2))
    for name in ("status.json", "failure.json", "host-failure.json", "host-exit.json"):
        if (campaign / "run" / name).exists():
            print(name + ": " + json.dumps(read(campaign / "run" / name)))
    if r["job_id"]:
        subprocess.run(
            [
                "sacct",
                "-j",
                r["job_id"],
                "--format=JobID,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS",
            ]
        )
        subprocess.run(["squeue", "-j", r["job_id"]])


def collect(package):
    campaign, r = bound(package)
    archive = Path(str(campaign) + ".tar.gz")
    if archive.exists():
        if Path(str(archive) + ".sha256").read_text().split() != [sha(archive), archive.name]:
            raise RuntimeError("Existing partial/changed archive preserved")
        print(str(archive))
        return
    if not r["job_id"] or r["dispatch"] != dict(status="submitted", job_id=r["job_id"]):
        raise RuntimeError("Unknown submission; inspect before collection")
    queue = subprocess.run(["squeue", "-h", "-j", r["job_id"]], capture_output=True, text=True)
    if queue.returncode == 0 and queue.stdout.strip():
        raise RuntimeError("Still queued/running; use status")
    accounting = subprocess.run(
        ["sacct", "-n", "-P", "-j", r["job_id"], "--format=JobID,State,ExitCode,Elapsed"],
        capture_output=True,
        text=True,
        check=True,
    )
    states = {
        line.split("|")[0]: line.split("|")[1].split()[0].rstrip("+")
        for line in accounting.stdout.splitlines()
        if len(line.split("|")) >= 3
    }
    if states.get(r["job_id"]) not in {
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "TIMEOUT",
        "OUT_OF_MEMORY",
        "NODE_FAIL",
        "BOOT_FAIL",
        "DEADLINE",
        "PREEMPTED",
    }:
        raise RuntimeError("Terminal scheduler state unknown")
    if not (campaign / "scheduler-evidence.json").exists():
        save(
            campaign / "scheduler-evidence.json",
            dict(
                squeue_returncode=queue.returncode,
                squeue_stdout=queue.stdout,
                sacct_stdout=accounting.stdout,
                terminal_verified=True,
            ),
        )
    files = [p for p in sorted(campaign.rglob("*")) if p.is_file()]
    if (
        len(files) > 256
        or any(p.is_symlink() for p in campaign.rglob("*"))
        or sum(p.stat().st_size for p in files) > 32 * 1024**2
    ):
        raise RuntimeError("Return safety/size cap")
    with tarfile.open(archive, "x:gz") as tar:
        for p in files:
            tar.add(p, arcname=campaign.name + "/" + str(p.relative_to(campaign)), recursive=False)
    with Path(str(archive) + ".sha256").open("x") as f:
        f.write(sha(archive) + "  " + archive.name + "\n")
    print("Download archive and checksum: " + str(archive))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["verify", "submit", "status", "collect"])
    a = p.parse_args()
    package = Path(__file__).resolve().parent
    if a.command == "verify":
        print(json.dumps(verify(package)["scope"], indent=2))
    else:
        globals()[a.command](package)


if __name__ == "__main__":
    main()
