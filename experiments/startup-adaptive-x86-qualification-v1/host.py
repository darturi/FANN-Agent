"""One new native qualification allocation; all existing source/image inputs read-only."""

import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from budget import phase
from common import IMAGE, ROOT, read, save, sha, verify


def command(package, out, work, image, apptainer, deadline):
    p = Path(package)
    workspace = p / "workspace"
    frozen = (
        workspace
        / "trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1/frozen"
    )
    cmd = [str(apptainer), "exec", "--cleanenv", "--containall", "--no-home", "--pwd", "/work"]
    binds = [
        (p, Path("/qual"), "ro"),
        (workspace, ROOT, "ro"),
        (out, Path("/results"), "rw"),
        (work, Path("/work"), "rw"),
    ]
    for rel in read(p / "ASSET-PLAN.json")["frozen_aliases"]:
        binds.append((frozen, ROOT / rel / "frozen", "ro"))
    for src, dest, mode in binds:
        cmd += ["--bind", str(src) + ":" + str(dest) + ":" + mode]
    for k, v in {
        "PYTHONPATH": "/qual:/opt/torch-reviews/vendor",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "TMPDIR": "/work/tmp",
        "QX_DEADLINE": str(deadline),
    }.items():
        cmd += ["--env", k + "=" + v]
    return cmd + [str(image), "python", "/qual/guest.py"]


def main():
    package, out, scratch, image, apptainer, python = map(Path, sys.argv[1:])
    start = time.monotonic()
    guest_end = start + 3240
    post_end = start + 3480
    ledger = []
    child = None
    code = 1
    error = None
    before = None
    log = None
    if (
        not re.fullmatch(r"[1-9][0-9]*", os.environ.get("SLURM_JOB_ID", ""))
        or python.resolve() != Path(sys.executable).resolve()
    ):
        raise RuntimeError("Declared Torch job and absolute Python required")

    def interrupt(n, f):
        raise TimeoutError("Qualification host signal/deadline " + str(n))

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGALRM):
        signal.signal(sig, interrupt)
    try:
        with phase("host_preflight", 240, guest_end, ledger):
            verify(package)
            from hardware import capture

            hardware = capture()
            if sha(image) != IMAGE:
                raise RuntimeError("Exact original SIF required")
            before = sha(package / "manifest.json")
            work = Path(
                tempfile.mkdtemp(
                    prefix="adaptive-x86-" + os.environ["SLURM_JOB_ID"] + ".", dir=scratch
                )
            )
            work.chmod(0o700)
            (work / "tmp").mkdir(mode=0o700)
            save(
                out / "host-launch.json",
                dict(
                    job_id=os.environ["SLURM_JOB_ID"],
                    host_python=str(python),
                    hardware=hardware,
                    image_sha256=IMAGE,
                    manifest_sha256=before,
                    guest_deadline=guest_end,
                    post_deadline=post_end,
                ),
            )
            argv = command(package, out, work, image, apptainer, guest_end)
            save(out / "host-command.json", dict(argv=argv))
        log = (out / "host-native.log").open("x")
        child = subprocess.Popen(
            argv,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        while child.poll() is None:
            if time.monotonic() >= guest_end:
                raise TimeoutError("Guest absolute runtime deadline")
            time.sleep(0.25)
        if child.returncode or read(out / "status.json")["status"] != "complete":
            raise RuntimeError("Native qualification incomplete/failed")
        code = 0
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:2048])
    finally:
        signal.alarm(0)
        try:
            with phase("host_postflight", 240, post_end, ledger):
                if child and child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=5)
                if log:
                    log.close()
                verify(package)
                if (
                    before is None
                    or sha(package / "manifest.json") != before
                    or sha(image) != IMAGE
                ):
                    raise RuntimeError("Final protected capsule/SIF proof failed")
                guest = read(out / "GUEST-LOCK.json")
                for name, h in guest["files"].items():
                    if sha(out / name) != h:
                        raise RuntimeError("Guest lock mismatch")
                if code == 0 and not guest["complete"]:
                    raise RuntimeError("Guest completion proof missing")
                save(
                    out / "host-integrity.json",
                    dict(
                        status="pass",
                        image_sha256=IMAGE,
                        manifest_sha256=before,
                        children_stopped=True,
                    ),
                )
        except BaseException as exc:
            code = 1
            error = dict(type=type(exc).__name__, message=str(exc)[:2048])
            # Insufficient full postflight reserve never grants qualification.
            # Still stop the owned process before the fixed post endpoint.
            if child and child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=max(0.1, min(5, post_end - time.monotonic())))
            if log and not log.closed:
                log.close()
        finally:
            signal.alarm(0)
        if time.monotonic() < post_end:
            if error:
                save(out / "host-failure.json", error)
            save(
                out / "host-exit.json",
                dict(
                    exit_code=code,
                    error=error,
                    job_id=os.environ["SLURM_JOB_ID"],
                    elapsed_seconds=time.monotonic() - start,
                ),
            )
            save(
                out / "host-timing.json",
                dict(
                    started=start,
                    guest_deadline=guest_end,
                    post_deadline=post_end,
                    finished=time.monotonic(),
                    phases=ledger,
                ),
            )
            save(
                out / "HOST-LOCK.json",
                dict(
                    complete=code == 0,
                    files={
                        str(p.relative_to(out)): sha(p)
                        for p in out.rglob("*")
                        if p.is_file() and p.name != "HOST-LOCK.json"
                    },
                ),
            )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
