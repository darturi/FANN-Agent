"""Slurm host wrapper: read-only original inputs, private restored database."""

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from pc_common import CONTRACT, protected, read, save, verify


def container_command(package, bundle, prepared, out, work, apptainer, block):
    cmd = [apptainer, "exec", "--cleanenv", "--containall", "--no-home", "--pwd", "/run"]
    bindings = [
        (package, "/patch", "ro"),
        (bundle, "/bundle", "ro"),
        (prepared, "/prepared", "ro"),
        (Path(CONTRACT["retained_source_work"]), "/retained", "ro"),
        (out, "/results", "rw"),
        (work, "/run", "rw"),
        (package / "frozen/modules/vector.so", "/opt/postgresql/lib/vector.so", "ro"),
    ]
    for host, container, mode in bindings:
        cmd += ["--bind", str(host) + ":" + container + ":" + mode]
    for key, value in {
        "PYTHONPATH": "/patch:/patch/frozen:/patch/frozen/vendor:/opt/torch-reviews/vendor",
        "PYTHONDONTWRITEBYTECODE": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "TMPDIR": "/run/tmp",
        "TORCH_IMAGE_SHA256": read(package / "frozen/experiment.json")["image_sha256"],
        "SLURM_JOB_ID": os.environ.get("SLURM_JOB_ID", ""),
        "SLURM_CPUS_PER_TASK": os.environ.get("SLURM_CPUS_PER_TASK", ""),
        "SLURM_ARRAY_JOB_ID": os.environ.get("SLURM_ARRAY_JOB_ID", ""),
        "SLURM_ARRAY_TASK_ID": os.environ.get("SLURM_ARRAY_TASK_ID", ""),
    }.items():
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
        raise ValueError("Expected seven job arguments plus absolute host Python")
    host_python = Path(sys.argv[8])
    if not host_python.is_absolute() or host_python.resolve() != Path(sys.executable).resolve():
        raise ValueError("Host Python identity differs from submission")
    package, bundle, prepared, campaign, workspace, sources = map(Path, sys.argv[1:7])
    apptainer = sys.argv[7]
    if (
        os.uname().sysname != "Linux"
        or os.uname().machine != "x86_64"
        or not os.environ.get("SLURM_JOB_ID")
    ):
        raise RuntimeError("Use the declared x86_64 Torch allocation")
    block = int(os.environ["SLURM_ARRAY_TASK_ID"])
    if block != 0:
        raise RuntimeError("Unknown block")
    out = campaign / "run"
    out.mkdir(parents=True, exist_ok=False)
    save(
        out / "host-launch.json",
        dict(
            host_python=str(host_python),
            actual_executable=sys.executable,
            python_version=sys.version,
            step_export=os.environ.get("SLURM_EXPORT_ENV"),
            python_no_bytecode=os.environ.get("PYTHONDONTWRITEBYTECODE"),
        ),
    )
    before = after = None
    process = sampler = work = None
    code = 1

    def interrupted(number, frame):
        raise InterruptedError("Host signal/deadline " + str(number))

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGUSR1, signal.SIGALRM):
        signal.signal(sig, interrupted)
    signal.alarm(240)
    try:
        from pc_resources import preflight
        from sr_host import monitor, start_sampler

        sampler = start_sampler(package, out, host_python, os.getpid())
        verify(package, bundle)
        resources = preflight(Path(CONTRACT["retained_source_work"]), workspace, sources)
        save(out / "resource-preflight.json", resources)
        before = protected(package, sources)
        if before != read(campaign / "protected-source-before.json"):
            raise RuntimeError("Protected sources changed since submission")
        if read(prepared / "database-identity.json") != read(package / "frozen/source-index.json"):
            raise RuntimeError("Prepared graph differs")
        save(out / "protected-source-before.json", before)
        work = Path(
            tempfile.mkdtemp(
                prefix="startup-resource-" + os.environ["SLURM_JOB_ID"] + ".", dir=workspace
            )
        )
        work.chmod(0o700)
        for name in ("socket", "tmp"):
            (work / name).mkdir(mode=0o700)
        (work / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")
        cmd = container_command(package, bundle, prepared, out, work, apptainer, block)
        signal.alarm(0)
        runtime_deadline = time.monotonic() + 3030
        try:
            process = subprocess.Popen(cmd)
            result = monitor(process, sampler, out)
            process = None
            if result or read(out / "job-exit.json")["exit_code"]:
                raise RuntimeError("Runtime or cleanup failed")
            code = 0
        finally:
            if process:
                process.terminate()
                try:
                    process.wait(timeout=max(1, min(600, runtime_deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
    except BaseException as error:
        save(out / "host-failure.json", {"type": type(error).__name__, "message": str(error)})
    finally:
        signal.alarm(240)
        try:
            if before is not None:
                after = protected(package, sources)
                save(out / "protected-source-after.json", after)
        except BaseException as error:
            code = 1
            if not (out / "host-failure.json").exists():
                save(
                    out / "host-failure.json", {"type": type(error).__name__, "message": str(error)}
                )
        finally:
            try:
                from sr_host import stop_sampler

                stop_sampler(sampler, out)
            except BaseException as error:
                code = 1
                if not (out / "host-failure.json").exists():
                    save(
                        out / "host-failure.json",
                        dict(type=type(error).__name__, message=str(error)),
                    )
            signal.alarm(0)
            same = before is not None and before == after
            save(
                out / "host-exit.json",
                dict(
                    exit_code=code or int(not same),
                    job_id=os.environ["SLURM_JOB_ID"],
                    array_job_id=os.environ.get("SLURM_ARRAY_JOB_ID", os.environ["SLURM_JOB_ID"]),
                    array_task_id="0",
                    protected_sources_unchanged=same,
                    work_directory=str(work) if work else None,
                    provider_calls=0,
                ),
            )
            save(
                out / "HOST-LOCK.json",
                dict(
                    complete=code == 0 and same,
                    files={
                        str(p.relative_to(out)): __import__("pc_common").sha(p)
                        for p in sorted(out.rglob("*"))
                        if p.is_file() and p.name != "HOST-LOCK.json"
                    },
                ),
            )
    if code or before is None or before != after:
        raise RuntimeError("Failed host/native campaign preserved for collection")


if __name__ == "__main__":
    main()
