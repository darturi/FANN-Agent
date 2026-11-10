"""One native correctness job; original SIF/source read-only, private scratch only."""

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from budget import phase, validate
from common import IMAGE, ROOT, read, save, sha, verify


def command(package, out, work, image, apptainer, deadline):
    base = package / "workspace"
    parent = base / "trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1"
    alias = (
        ROOT / "trials/torch-reviews-startup-resource-stream-v1/torch-startup-resource-stream-v1"
    )
    cmd = [str(apptainer), "exec", "--cleanenv", "--containall", "--no-home", "--pwd", "/work"]
    for a, b, mode in (
        (package, Path("/compat"), "ro"),
        (base, ROOT, "ro"),
        (parent, alias, "ro"),
        (out, Path("/results"), "rw"),
        (work, Path("/work"), "rw"),
    ):
        cmd += ["--bind", str(a) + ":" + str(b) + ":" + mode]
    for k, v in dict(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH="/compat:/opt/torch-reviews/vendor",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        TMPDIR="/work/tmp",
        CC_DEADLINE=str(deadline),
    ).items():
        cmd += ["--env", k + "=" + v]
    return cmd + [str(image), "python", "/compat/guest.py"]


def main():
    package, out, scratch, image, apptainer, python = map(Path, sys.argv[1:])
    if (
        python.resolve() != Path(sys.executable).resolve()
        or os.uname().sysname != "Linux"
        or not os.environ.get("SLURM_JOB_ID")
    ):
        raise RuntimeError("Declared native job/absolute Python required")
    started = time.monotonic()
    limits = validate(read(package / "COMPATIBILITY-CONTRACT.json")["limits"])
    # Fixed host endpoints: unused startup reserve covers container launch, not extra suites.
    guest_end = started + limits["host_startup_seconds"] + limits["guest_seconds"]
    termination_end = guest_end + limits["termination_seconds"]
    cleanup_end = termination_end + limits["host_cleanup_seconds"]
    assert cleanup_end == started + limits["wall_seconds"] - limits["outer_margin_seconds"]
    child = None
    work = None
    code = 1
    manifest_before = None
    ledger = []
    cleanup_error = None

    def interrupt(n, f):
        raise TimeoutError("Compatibility host signal/deadline " + str(n))

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGALRM):
        signal.signal(sig, interrupt)
    try:
        with phase("host_startup", limits["host_startup_seconds"], guest_end, ledger):
            verify(package)
            manifest_before = sha(package / "manifest.json")
            if sha(image) != IMAGE:
                raise RuntimeError("Original SIF differs")
            save(
                out / "host-launch.json",
                dict(
                    job_id=os.environ["SLURM_JOB_ID"],
                    host_python=str(python),
                    actual_python=sys.executable,
                    image_sha256=IMAGE,
                    package_manifest_sha256=manifest_before,
                    guest_deadline_monotonic=guest_end,
                ),
            )
            work = Path(
                tempfile.mkdtemp(prefix="compat-" + os.environ["SLURM_JOB_ID"] + ".", dir=scratch)
            )
            work.chmod(0o700)
            (work / "tmp").mkdir(mode=0o700)
            log = (out / "native.log").open("x")
            try:
                child = subprocess.Popen(
                    command(package, out, work, image, apptainer, guest_end),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            finally:
                log.close()
        # Container launch consumes the explicit host startup window. Guest independently
        # rejects a late start without its full990s. Parent enforces the fixed endpoint.
        wait_start = time.monotonic()
        remaining = guest_end - wait_start
        if remaining <= 0:
            raise TimeoutError("No complete guest reserve")
        with phase("native_guest_wait", remaining, guest_end, ledger, began=wait_start):
            rc = child.wait(timeout=remaining)
        if rc or read(out / "status.json")["status"] != "complete":
            raise RuntimeError("Native correctness failed; preserve raw")
        code = 0
    except BaseException as e:
        code = 1
        save(out / "host-failure.json", dict(type=type(e).__name__, message=str(e)[:2048]))
    finally:
        signal.alarm(0)
        try:
            with phase(
                "container_termination", limits["termination_seconds"], termination_end, ledger
            ):
                if child and child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
                if child and child.poll() is None:
                    raise RuntimeError("Owned container process remains live")
        except BaseException as e:
            code = 1
            cleanup_error = dict(type=type(e).__name__, message=str(e)[:2048])
        try:
            with phase("host_cleanup", limits["host_cleanup_seconds"], cleanup_end, ledger):
                verify(package)
                if (
                    manifest_before is None
                    or sha(package / "manifest.json") != manifest_before
                    or sha(image) != IMAGE
                ):
                    raise RuntimeError("Protected capsule/image changed or startup unverified")
                if cleanup_error:
                    raise RuntimeError(
                        "Container termination incomplete: " + cleanup_error["message"]
                    )
                save(
                    out / "host-integrity.json",
                    dict(
                        status="pass", package_manifest_sha256=manifest_before, image_sha256=IMAGE
                    ),
                )
        except BaseException as e:
            code = 1
            cleanup_error = dict(type=type(e).__name__, message=str(e)[:2048])
            # A phase overrun after writing success must never leave a pass receipt.
            from common import replace

            replace(
                out / "host-integrity.json",
                dict(status="failed", error_type=type(e).__name__, message=str(e)[:2048]),
            )
            if not (out / "host-failure.json").exists():
                save(out / "host-failure.json", cleanup_error)
        finally:
            signal.alarm(0)
        # Terminal publication shares the cleanup endpoint, preserving105s scheduler margin.
        publish_end = min(cleanup_end, ledger[-1]["deadline_monotonic"]) if ledger else cleanup_end
        try:
            import math

            left = publish_end - time.monotonic()
            if left <= 0:
                raise TimeoutError("Host publication reserve exhausted")
            signal.alarm(max(1, math.ceil(left)))
            save(
                out / "host-phase-timing.json",
                dict(
                    limits=limits,
                    phases=ledger,
                    guest_deadline_monotonic=guest_end,
                    cleanup_deadline_monotonic=cleanup_end,
                    cleanup_error=cleanup_error,
                    scratch_policy=(
                        "Owned synthetic scratch retained for diagnosis; capsule/SIF read-only"
                    ),
                ),
            )
            save(
                out / "host-exit.json",
                dict(
                    exit_code=code,
                    job_id=os.environ["SLURM_JOB_ID"],
                    work_directory=str(work) if work else None,
                    main_A2_launched=False,
                    SQL=0,
                    searches=0,
                    elapsed_seconds=time.monotonic() - started,
                ),
            )
            if time.monotonic() >= publish_end:
                raise TimeoutError("Host terminal publication deadline")
            save(
                out / "LOCK.json",
                dict(
                    complete=code == 0,
                    files={p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()},
                ),
            )
            if time.monotonic() >= publish_end:
                raise TimeoutError("Host lock publication deadline")
        except BaseException as e:
            # Preserve partial evidence. Never promote an over-budget finalization.
            from common import replace

            code = 1
            signal.alarm(0)
            if not (out / "host-failure.json").exists():
                save(out / "host-failure.json", dict(type=type(e).__name__, message=str(e)[:2048]))
            replace(
                out / "host-exit.json",
                dict(
                    exit_code=1,
                    job_id=os.environ["SLURM_JOB_ID"],
                    main_A2_launched=False,
                    SQL=0,
                    searches=0,
                    elapsed_seconds=time.monotonic() - started,
                ),
            )
            replace(
                out / "LOCK.json",
                dict(
                    complete=False,
                    files={
                        p.name: sha(p)
                        for p in sorted(out.iterdir())
                        if p.is_file() and p.name != "LOCK.json"
                    },
                ),
            )
        finally:
            signal.alarm(0)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
