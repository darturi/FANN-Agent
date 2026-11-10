"""Slurm host wrapper: read-only original inputs, private restored database."""

import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from mid_common import COUNTS, protected, read, save, verify


def container_command(package, bundle, prepared, out, work, apptainer, block):
    cmd = [apptainer, "exec", "--cleanenv", "--containall", "--no-home", "--pwd", "/run"]
    bindings = [
        (package, "/patch", "ro"),
        (bundle, "/bundle", "ro"),
        (prepared, "/prepared", "ro"),
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
        "SLURM_ARRAY_JOB_ID": os.environ.get("SLURM_ARRAY_JOB_ID", ""),
        "SLURM_ARRAY_TASK_ID": os.environ.get("SLURM_ARRAY_TASK_ID", ""),
    }.items():
        cmd += ["--env", key + "=" + value]
    return cmd + [
        str(bundle / "images/runtime.sif"),
        "python",
        "/patch/mid_runtime.py",
        "--block",
        str(block),
    ]


def main():
    package, bundle, prepared, campaign, workspace, sources = map(Path, sys.argv[1:7])
    apptainer = sys.argv[7]
    verify(package, bundle)
    if (
        os.uname().sysname != "Linux"
        or os.uname().machine != "x86_64"
        or not os.environ.get("SLURM_JOB_ID")
    ):
        raise RuntimeError("Use an x86_64 Torch allocation")
    block = int(os.environ["SLURM_ARRAY_TASK_ID"])
    if block not in range(COUNTS["allocations"]):
        raise RuntimeError("Unknown block")
    before = protected(package, sources)
    if before != read(campaign / "protected-source-before.json"):
        raise RuntimeError("Protected sources changed since submission")
    if read(prepared / "database-identity.json") != read(package / "frozen/source-index.json"):
        raise RuntimeError("Prepared physical index differs")
    out = campaign / "run"
    out.mkdir(parents=True, exist_ok=False)
    save(out / "protected-source-before.json", before)
    work = Path(tempfile.mkdtemp(prefix="cost-" + os.environ["SLURM_JOB_ID"] + ".", dir=workspace))
    work.chmod(0o700)
    for name in ("socket", "tmp"):
        (work / name).mkdir(mode=0o700)
    (work / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")
    cmd = container_command(package, bundle, prepared, out, work, apptainer, block)
    process = None
    code = 1

    def interrupted(number, frame):
        if process:
            process.terminate()
        raise InterruptedError("Slurm signal " + str(number))

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGUSR1):
        signal.signal(sig, interrupted)
    try:
        process = subprocess.Popen(cmd)
        result = process.wait()
        process = None
        if result or read(out / "job-exit.json")["exit_code"]:
            raise RuntimeError("Runtime or cleanup failed")
        code = 0
    except BaseException as error:
        save(out / "host-failure.json", {"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        after = protected(package, sources)
        save(out / "protected-source-after.json", after)
        save(
            out / "host-exit.json",
            {
                "exit_code": code or int(before != after),
                "job_id": os.environ["SLURM_JOB_ID"],
                "array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID", os.environ["SLURM_JOB_ID"]),
                "array_task_id": os.environ["SLURM_ARRAY_TASK_ID"],
                "protected_sources_unchanged": before == after,
                "work_directory": str(work),
                "provider_calls": 0,
            },
        )
        if before != after:
            raise RuntimeError("Protected sources changed")


if __name__ == "__main__":
    main()
