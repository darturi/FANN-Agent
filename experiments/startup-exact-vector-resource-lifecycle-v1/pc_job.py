"""Bounded Slurm host entry; all source/image/input access is read-only."""

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ev_host import Envelope, monitor, stop_child
from pc_common import CONTRACT, protected, read, require_native_release, save, sha, verify


def container_command(package, bundle, prepared, out, work, apptainer, block, deadline):
    cmd = [str(apptainer), "exec", "--cleanenv", "--containall", "--no-home", "--pwd", "/run"]
    for host, container, mode in [
        (package, "/patch", "ro"),
        (bundle, "/bundle", "ro"),
        (prepared, "/prepared", "ro"),
        (Path(CONTRACT["retained_source_work"]), "/retained", "ro"),
        (out, "/results", "rw"),
        (work, "/run", "rw"),
        (package / "frozen/modules/vector.so", "/opt/postgresql/lib/vector.so", "ro"),
    ]:
        cmd += ["--bind", str(host) + ":" + container + ":" + mode]
    environment = {
        "PYTHONPATH": (
            "/patch:/patch/frozen:/patch/reference/frozen/vendor:/opt/torch-reviews/vendor"
        ),
        "PYTHONDONTWRITEBYTECODE": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "TMPDIR": "/run/tmp",
        "TORCH_IMAGE_SHA256": CONTRACT["runtime"]["image_sha256"],
        "EV_RUNTIME_DEADLINE": format(deadline, ".17g"),
        **{
            key: os.environ.get(key, "")
            for key in (
                "SLURM_JOB_ID",
                "SLURM_CPUS_PER_TASK",
                "SLURM_ARRAY_JOB_ID",
                "SLURM_ARRAY_TASK_ID",
            )
        },
    }
    for key, value in environment.items():
        cmd += ["--env", key + "=" + value]
    return cmd + [
        str(bundle / "images/runtime.sif"),
        "python",
        "/patch/pc_runtime.py",
        "--block",
        str(block),
    ]


def main():
    if len(sys.argv) != 9:
        raise ValueError("Eight job arguments, including absolute host Python, required")
    package, bundle, prepared, campaign, workspace, sources = map(Path, sys.argv[1:7])
    apptainer, python = sys.argv[7], Path(sys.argv[8])
    if not python.is_absolute() or python.resolve() != Path(sys.executable).resolve():
        raise ValueError("Submitted absolute host interpreter differs")
    if (
        os.uname().sysname != "Linux"
        or os.uname().machine != "x86_64"
        or not os.environ.get("SLURM_JOB_ID")
        or os.environ.get("SLURM_CPUS_PER_TASK") != "4"
        or os.environ.get("SLURM_ARRAY_TASK_ID") != "0"
    ):
        raise RuntimeError("Exactly the declared Torch block-0 allocation is required")
    envelope = Envelope()
    out = campaign / "run"
    out.mkdir(parents=True, exist_ok=False)
    process = sampler = work = before = after = None
    code = 1
    error = None
    cleanup_errors = []
    image = bundle / "images/runtime.sif"

    def interrupted(number, frame):
        raise InterruptedError("Host signal/deadline " + str(number))

    def arm(deadline):
        envelope.check(deadline)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline - time.monotonic()))

    def failure(exc):
        return dict(type=type(exc).__name__, message=str(exc)[:4096])

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGUSR1, signal.SIGALRM):
        signal.signal(sig, interrupted)
    try:
        from pc_resources import preflight
        from sr_host import start_sampler

        arm(envelope.pre_deadline)
        sampler = start_sampler(package, out, python, os.getpid())
        require_native_release(package)
        verify(package, bundle)
        save(
            out / "resource-preflight.json",
            preflight(Path(CONTRACT["retained_source_work"]), workspace, sources),
        )
        before = protected(package, sources)
        if before != read(campaign / "protected-source-before.json"):
            raise RuntimeError("Protected sources changed since submission")
        if read(prepared / "database-identity.json") != read(package / "frozen/source-index.json"):
            raise RuntimeError("Prepared graph identity differs")
        save(out / "protected-source-before.json", before)
        if sha(image) != CONTRACT["runtime"]["image_sha256"]:
            raise RuntimeError("Exact SIF hash differs")
        work = Path(
            tempfile.mkdtemp(
                prefix="startup-exact-vector-" + os.environ["SLURM_JOB_ID"] + ".", dir=workspace
            )
        )
        work.chmod(0o700)
        for name in ("socket", "tmp"):
            (work / name).mkdir(mode=0o700)
        (work / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")
        deadline = envelope.runtime()
        save(
            out / "host-launch.json",
            dict(
                host_python=str(python),
                actual_executable=sys.executable,
                python_version=sys.version,
                step_export=os.environ.get("SLURM_EXPORT_ENV"),
                python_no_bytecode=os.environ.get("PYTHONDONTWRITEBYTECODE"),
                package_manifest_sha256=sha(package / "manifest.json"),
                runtime_deadline=deadline,
                image_sha256=CONTRACT["runtime"]["image_sha256"],
            ),
        )
        arm(deadline)
        process = subprocess.Popen(
            container_command(package, bundle, prepared, out, work, apptainer, 0, deadline)
        )
        result = monitor(process, sampler, out, deadline)
        if result or read(out / "job-exit.json")["exit_code"]:
            raise RuntimeError("Native runtime or cleanup failed")
        code = 0
    except BaseException as exc:
        error = failure(exc)
    finally:
        # Termination/reaping and sampler stop consume this existing post phase.
        post = envelope.post()
        arm(post)
        try:
            stop_child(process, post)
        except BaseException as exc:
            cleanup_errors.append(failure(exc))
            code = 1
        try:
            arm(post)
            if before is not None:
                after = protected(package, sources)
                save(out / "protected-source-after.json", after)
            verify(package, bundle)
            if sha(image) != CONTRACT["runtime"]["image_sha256"]:
                raise RuntimeError("Final exact SIF hash differs")
            save(
                out / "ev-host-integrity.json",
                dict(
                    status="pass",
                    package_manifest_sha256=sha(package / "manifest.json"),
                    image_sha256=CONTRACT["runtime"]["image_sha256"],
                    reference_manifest_sha256=sha(package / "reference/manifest.json"),
                ),
            )
        except BaseException as exc:
            cleanup_errors.append(failure(exc))
            code = 1
        finally:
            try:
                from sr_host import stop_sampler

                arm(post)
                stop_sampler(sampler, out)
            except BaseException as exc:
                cleanup_errors.append(failure(exc))
                code = 1
                try:
                    stop_child(sampler, post)
                except BaseException as stop_error:
                    cleanup_errors.append(failure(stop_error))
        same = before is not None and before == after
        code = code or int(not same) or int(error is not None)
        if error or cleanup_errors:
            save(out / "host-failure.json", dict(primary=error, cleanup=cleanup_errors))
        save(
            out / "host-exit.json",
            dict(
                exit_code=code,
                job_id=os.environ["SLURM_JOB_ID"],
                array_job_id=os.environ.get("SLURM_ARRAY_JOB_ID", os.environ["SLURM_JOB_ID"]),
                array_task_id="0",
                protected_sources_unchanged=same,
                work_directory=str(work) if work else None,
                provider_calls=0,
            ),
        )
        save(out / "ev-host-timing.json", envelope.proof())
        save(
            out / "HOST-LOCK.json",
            dict(
                complete=code == 0,
                files={
                    str(p.relative_to(out)): sha(p)
                    for p in sorted(out.rglob("*"))
                    if p.is_file() and p.name != "HOST-LOCK.json"
                },
            ),
        )
        envelope.check(post)
        signal.setitimer(signal.ITIMER_REAL, 0)
    if code:
        raise RuntimeError("Failed/incomplete startup-memory acquisition preserved; no retry")


if __name__ == "__main__":
    raise RuntimeError("Offline A3 correction only; no native execution or spent-allowance reuse")
    main()
