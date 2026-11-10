"""Pending-approval single-use control, live site checks, status and terminal return."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from ni_control_reads import control_read

from nh_common import config, core, private, read, save, sha
from ni_authority import APPROVAL_TEXT, approved, stage_authority
from ni_package import NAME, verify
from ni_site import SiteClient, bounded_command, trusted_binary


def replace(path, value):
    p = Path(path)
    temporary = p.with_name(p.name + ".next")
    save(temporary, value)
    os.replace(temporary, p)
    fd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def state_root(package):
    root = Path(os.environ["TORCH_RESULTS_ROOT"])
    if not root.is_absolute() or root.is_symlink() or root.stat().st_uid != os.getuid():
        raise ValueError("Owned persistent result root required")
    child = root / ("native-integrated-" + sha(Path(package) / "PLAN.json")[:24])
    child.mkdir(mode=0o700, exist_ok=True)
    return private(child)


def site_check(package):
    verify(package)
    client = SiteClient(shutil.which("scontrol") or "/usr/bin/scontrol")
    proof = client.probe()
    path = state_root(package) / "site-check.json"
    if path.exists():
        previous = read(path)
        if previous != proof:
            raise RuntimeError("Site changed; preserve old proof and review")
    else:
        save(path, proof)
    print(
        json.dumps(
            {
                "site_check": proof,
                "allocations": 0,
                "searches": 0,
                "approval": "not issued by this command",
            },
            indent=2,
        )
    )
    return proof


def approve_command(package, text):
    verify(package)
    if text != APPROVAL_TEXT:
        raise RuntimeError("Exact distinct-allocation authorization required")
    state = state_root(package)
    reservation = state.parent / ("." + NAME + "-reservation.json")
    if reservation.exists() or (state / "submission.json").exists():
        raise RuntimeError("A prior known/uncertain allowance cannot be reopened")
    value = {
        "schema": "a3.explicit-approval.v1",
        "approval": text,
        "plan_sha256": sha(Path(package) / "PLAN.json"),
        "uid": os.getuid(),
        "nonce": os.urandom(16).hex(),
        "allocations": 1,
        "ANN_searches": 0,
        "exact_searches": 0,
        "retry": False,
    }
    path = state / "approval.json"
    save(path, value)
    path.chmod(0o600)
    print("Distinct approval recorded; nothing submitted")


def quota(package):
    plan = verify(package)
    ref = Path(package) / "reference" / plan["reference_name"]
    core(ref)
    from quota_base import quota_report

    text = bounded_command([shutil.which("myquota") or "/usr/local/bin/myquota"], timeout=30)
    report = quota_report(text)
    for fs, path, need, files in [
        ("/home", Path(os.environ["TORCH_RESULTS_ROOT"]), 128 * 1024**2, 1000),
        ("/scratch", Path(os.environ["TORCH_SCRATCH_ROOT"]), 8 * 1024**3, 30000),
    ]:
        s = os.statvfs(path)
        if (
            min(s.f_bavail * s.f_frsize, report[fs]["space_available_lower"]) < need
            or min(s.f_favail, report[fs]["inodes_available_lower"]) < files
        ):
            raise RuntimeError("Original conservative quota/headroom unavailable: " + fs)
    return {"text": text, "quota": report}


def submit(package):
    p = Path(package)
    verify(p)
    state = state_root(p)
    approved(read(state / "approval.json"), sha(p / "PLAN.json"), os.getuid())
    if (state / "submission.json").exists():
        raise RuntimeError("Known/uncertain dispatch cannot be repeated")
    reservation = state.parent / ("." + NAME + "-reservation.json")
    if reservation.exists():
        raise RuntimeError("Allocation already reserved; no reuse")
    if (
        os.uname().sysname != "Linux"
        or os.uname().machine != "x86_64"
        or os.environ.get("SLURM_JOB_ID")
    ):
        raise RuntimeError("Submit only from Torch x86 login")
    site_check(p)
    capacity = quota(p)
    account = os.environ["TORCH_SLURM_ACCOUNT"]
    if not re.fullmatch("[A-Za-z0-9_]+", account):
        raise ValueError("Explicit active project account required")
    image = Path(
        os.environ.get("TORCH_RUNTIME_IMAGE", "/home/dar579/torch-reviews-first/images/runtime.sif")
    )
    apptainer = Path(
        os.environ.get("TORCH_APPTAINER_BIN", "/share/apps/apptainer/bin/apptainer")
    ).resolve(strict=True)
    if sha(image) != config()["image_sha256"] or not os.access(apptainer, os.X_OK):
        raise RuntimeError("Exact retained image/launcher required")
    sbatch = trusted_binary(shutil.which("sbatch") or "/usr/bin/sbatch")["path"]
    comment = "a3-ni-" + sha(p / "PLAN.json")[:24]
    base = [
        sbatch,
        "--parsable",
        "--export=NONE",
        "--account=" + account,
        "--comment=" + comment,
        "--chdir=" + str(p),
    ]
    launcher = [str(p / "LAUNCHER.sh"), str(Path(sys.executable).resolve()), str(p), str(state)]
    bounded_command(base + ["--test-only", "--output=/dev/null"] + launcher, timeout=30)
    save(
        reservation,
        {
            "plan_sha256": sha(p / "PLAN.json"),
            "approval_sha256": sha(state / "approval.json"),
            "allocations": 1,
            "state": str(state),
            "status": "reserved_no_retry",
        },
    )
    record = {
        "plan_sha256": sha(p / "PLAN.json"),
        "package_manifest_sha256": sha(p / "manifest.json"),
        "approval_sha256": sha(state / "approval.json"),
        "package": str(p),
        "account": account,
        "comment": comment,
        "image": str(image),
        "apptainer": str(apptainer),
        "python": str(Path(sys.executable).resolve()),
        "dispatch": {"status": "dispatching"},
        "job_id": None,
    }
    save(state / "submission.json", record)
    save(state / "quota-preflight.json", capacity)
    try:
        response = bounded_command(
            base + ["--output=" + str(state / "scheduler-%j.log")] + launcher, timeout=30
        )
        if not re.fullmatch("[1-9][0-9]*(;[A-Za-z0-9_-]+)?", response.strip()):
            raise RuntimeError("Unknown submission response")
        job = response.strip().split(";")[0]
        from release_policy import SPENT

        if job in SPENT:
            raise RuntimeError("Spent job cannot be reused")
        record["job_id"] = job
        record["dispatch"] = {"status": "submitted", "job_id": job}
    except BaseException:
        record["dispatch"] = {"status": "unknown"}
        replace(state / "submission.json", record)
        raise
    replace(state / "submission.json", record)
    print(json.dumps(record, indent=2))


def status(package):
    verify(package)
    state = state_root(package)
    if not (state / "submission.json").exists():
        print("Not submitted; no allocation spent by this package")
        return
    r = read(state / "submission.json")
    print(json.dumps(r, indent=2))
    run = state / ("native-" + r["job_id"]) if r["job_id"] else None
    if run and run.exists():
        for name in (
            "CONTROL.json",
            "guest-status.json",
            "host-owned-proof.json",
            "preflight-failure.json",
        ):
            if (run / name).exists():
                print(name + ": " + json.dumps(read(run / name)))
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
    verify(package)
    state = state_root(package)
    r = read(state / "submission.json")
    if r["dispatch"] != {"status": "submitted", "job_id": r["job_id"]}:
        raise RuntimeError("Uncertain submission; inspect without retry")
    accounting = bounded_command(
        [
            shutil.which("sacct") or "/usr/bin/sacct",
            "-n",
            "-P",
            "-j",
            r["job_id"],
            "--format=JobID,State,ExitCode,Elapsed",
        ]
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
    rows = [
        line.split("|") for line in accounting.splitlines() if line.split("|")[0] == r["job_id"]
    ]
    if len(rows) != 1 or rows[0][1].split()[0].rstrip("+") not in terminal:
        raise RuntimeError("Terminal scheduler state not verified")
    archive = Path(str(state) + ".tar.gz")
    if archive.exists():
        if Path(str(archive) + ".sha256").read_text().split() != [sha(archive), archive.name]:
            raise RuntimeError("Preserve partial collection")
        print(archive)
        return
    proof = state / "scheduler-terminal.json"
    if not proof.exists():
        save(proof, {"text": accounting, "job_id": r["job_id"], "terminal_verified": True})
    files = []
    for path in state.rglob("*"):
        if path.is_symlink():
            raise ValueError("Returned links prohibited")
        if path.is_file():
            files.append(path)
    if len(files) > 256 or sum(p.stat().st_size for p in files) > 32 * 1024**2:
        raise RuntimeError("Whole return32MiB/256file cap exhausted")
    with tarfile.open(archive, "x:gz") as t:
        for path in sorted(files):
            t.add(path, arcname=state.name + "/" + str(path.relative_to(state)), recursive=False)
    Path(str(archive) + ".sha256").write_text(sha(archive) + "  " + archive.name + "\n")
    print(archive)


def host(package, state):
    p = Path(package)
    state = private(Path(state))
    waiting = time.monotonic() + 30
    job = os.environ.get("SLURM_JOB_ID", "")
    if not re.fullmatch("[1-9][0-9]*", job):
        raise RuntimeError("Actual Slurm allocation required")
    while True:
        record = read(state / "submission.json")
        if record["dispatch"] == {"status": "submitted", "job_id": job} and record["job_id"] == job:
            break
        if record["dispatch"].get("status") != "dispatching" or time.monotonic() >= waiting:
            raise RuntimeError("Submission not independently committed; no self-adoption or retry")
        time.sleep(0.1)
    out = state / ("native-" + str(job))
    out.mkdir(mode=0o700)
    try:
        plan = verify(p)
        from ni_host import execute
        from ni_materialize import stage_exact
        from ni_native import Allocation, launch
        from ni_package import verify as verify_bundle
        from ni_storage import node_private

        authority = Allocation(p, state, record, plan)
        ref = p / "reference" / plan["reference_name"]
        original = core(ref)
        context = {
            "profile": "target",
            "authority": authority,
            "original": str(ref),
            "image": record["image"],
            "apptainer": record["apptainer"],
            "host_python": record["python"],
            "host_clock_started": authority.started,
            "bridge_snapshot": str(p / "integration-sealed"),
        }

        def prepare(start, store):
            authority.refresh()
            mounts = control_read("self/mountinfo")
            base = Path(os.environ["SLURM_TMPDIR"])
            if not base.is_absolute() or base.is_symlink() or not base.exists():
                raise RuntimeError("Actual Slurm job-local directory unavailable")
            jobroot = Path(tempfile.mkdtemp(prefix="a3-ni-" + job + ".", dir=base))
            jobroot.chmod(0o700)
            context["capture_root"] = str(jobroot)
            context["work"] = str(jobroot / "work")
            Path(context["work"]).mkdir(mode=0o700)
            (Path(context["work"]) / "tmp").mkdir(mode=0o700)
            context["storage_evidence"] = node_private(jobroot, mounts)
            from hardware import capture

            context["hardware"] = capture()
            if sha(record["image"]) != config()["image_sha256"]:
                raise RuntimeError("Retained exact SIF changed")
            with stage_authority(authority):
                stage = stage_exact(
                    p / "original.tar.gz",
                    ref,
                    jobroot / "exact-stage",
                    config()["original_archive_sha256"],
                    config()["original_manifest_sha256"],
                    original.verify,
                )
            context["inner"] = str(stage)
            context["workspace"] = str(stage / "workspace")
            context["science"] = str(out / "science")
            Path(context["science"]).mkdir(mode=0o700)
            context["persistent_references"] = {
                "sealed-archive": {
                    "path": str(p / "original.tar.gz"),
                    "sha256": config()["original_archive_sha256"],
                }
            }
            return context

        def final(ctx, end):
            from nh_common import check_time

            check_time(end)
            from nh_lifecycle import stop_owned
            from ni_groups import OwnedProcess

            if ctx and ctx.get("host_groups") and ctx["host_groups"].active is not None:
                groups = ctx["host_groups"]
                child = OwnedProcess(groups)
                stop_owned(groups, groups.active, child, end)
                groups.finish(groups.active)
            original.verify(ref)
            if ctx and ctx.get("inner"):
                original.verify(Path(ctx["inner"]))
            verify_bundle(p)
            if (
                ctx
                and ctx.get("science")
                and (Path(ctx["science"]).parent / "guest-status.json").exists()
            ):
                guest_status = read(Path(ctx["science"]).parent / "guest-status.json")
                if guest_status["status"] == "complete":
                    from proofs import validate

                    science = validate(
                        Path(ctx["science"]),
                        Path(ctx["inner"]) / "workspace",
                        read(Path(ctx["inner"]) / "QUALIFICATION-CONTRACT.json"),
                        "target",
                    )
                    from nh_retention import RawStore

                    RawStore.existing(Path(ctx["science"]).parent).json(
                        "host-science-validation.json", science
                    )
            if sha(record["image"]) != config()["image_sha256"]:
                raise RuntimeError("Final exact image differs")
            check_time(end)

        result = execute(out, prepare, launch, final, initial_context=context)
        from nh_lifecycle import endpoint, interruptions

        with interruptions(), endpoint(result["post_deadline"]):
            save(state / "host-process-result.json", result)
        raise SystemExit(0 if result["status"] == "pass" else 1)
    except SystemExit:
        raise
    except BaseException as exc:
        if not (out / "preflight-failure.json").exists():
            save(
                out / "preflight-failure.json",
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "native_qualification": False,
                    "searches": 0,
                },
            )
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("verify", "site-check", "approve", "submit", "status", "collect", "host"),
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("state", nargs="?", type=Path)
    parser.add_argument("--approval-text")
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(verify(args.package)["limits"], indent=2))
    elif args.command == "approve":
        approve_command(args.package, args.approval_text)
    elif args.command == "host":
        host(args.package, args.state)
    else:
        globals()[args.command.replace("-", "_")](args.package)


if __name__ == "__main__":
    main()
