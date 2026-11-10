"""One native correctness job; original SIF/source read-only, private scratch only."""

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

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
    end = started + 900
    child = None
    work = None
    code = 1
    manifest_before = None

    def stop(n, f):
        raise TimeoutError("Compatibility host signal " + str(n))

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGALRM):
        signal.signal(sig, stop)
    signal.alarm(90)
    try:
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
                package_manifest_sha256=sha(package / "manifest.json"),
            ),
        )
        work = Path(
            tempfile.mkdtemp(prefix="compat-" + os.environ["SLURM_JOB_ID"] + ".", dir=scratch)
        )
        work.chmod(0o700)
        (work / "tmp").mkdir(mode=0o700)
        deadline = min(time.monotonic() + 720, end - 90)
        if deadline - time.monotonic() < 690:
            raise TimeoutError("Insufficient complete-suite/cleanup reserve")
        signal.alarm(max(1, int(deadline - time.monotonic())))
        with (out / "native.log").open("x") as log:
            child = subprocess.Popen(
                command(package, out, work, image, apptainer, deadline - 15),
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                rc = child.wait(timeout=max(1, deadline - time.monotonic()))
            finally:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
        child = None
        if rc or read(out / "status.json")["status"] != "complete":
            raise RuntimeError("Native correctness failed; preserve raw")
        code = 0
    except BaseException as e:
        code = 1
        save(out / "host-failure.json", dict(type=type(e).__name__, message=str(e)[:2048]))
    finally:
        signal.alarm(max(1, int(min(60, end - time.monotonic() - 30))))
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        try:
            verify(package)
            if (
                manifest_before is None
                or sha(package / "manifest.json") != manifest_before
                or sha(image) != IMAGE
            ):
                raise RuntimeError("Protected capsule/image changed or startup unverified")
            save(
                out / "host-integrity.json",
                dict(status="pass", package_manifest_sha256=manifest_before, image_sha256=IMAGE),
            )
        except BaseException as e:
            code = 1
            save(
                out / "host-integrity.json",
                dict(status="failed", error_type=type(e).__name__, message=str(e)[:2048]),
            )
            if not (out / "host-failure.json").exists():
                save(out / "host-failure.json", dict(type=type(e).__name__, message=str(e)[:2048]))
        signal.alarm(0)
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
        save(
            out / "LOCK.json",
            dict(
                complete=code == 0,
                files={p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()},
            ),
        )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
