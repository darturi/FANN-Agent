"""One Slurm allocation, finite idle/work clocks, no provider or scheduler client."""

import argparse
import os
import shutil
import signal
import subprocess
import tarfile
import time
from pathlib import Path

from limits import (
    ATTEMPT_LIMIT,
    FINAL_RESERVED_ATTEMPTS,
    IDLE_SECONDS,
    SCREEN_GROUPS,
    Deadline,
    digest,
    read,
    sha,
    write,
)

APPTAINER = "/share/apps/apptainer/bin/apptainer"


def unpack_sources(archive_path, destination):
    """Portable host-Python extraction of the pinned, regular-file-only source archive."""
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        if sum(m.size for m in members) > 256 * 1024**2:
            raise ValueError("source archive exceeds bounded size")
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError("unsafe source archive member")
        for member in members:
            target = destination / member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True, mode=0o700)
            else:
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with archive.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                    os.fchmod(output.fileno(), member.mode & 0o777)


def execute(command, log, timeout):
    """Terminate the entire container process group if its work budget expires."""
    with log.open("wb") as output:
        process = subprocess.Popen(
            command, stdout=output, stderr=subprocess.STDOUT, start_new_session=True
        )
        try:
            return process.wait(timeout=max(1, timeout))
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            raise


def container(stage, config, batch, run, program, *, module=False):
    args = [
        APPTAINER,
        "exec",
        "--cleanenv",
        "--containall",
        "--no-home",
        "--pwd",
        "/tmp",
        "--bind",
        f"{stage}:/code:ro",
        "--bind",
        f"{batch}:/batch:rw",
        "--bind",
        f"{run / 'original'}:/original:ro",
        "--bind",
        f"{config['bundle']}:/bundle:ro",
        "--bind",
        f"{config['prepared']}:/prepared:ro",
        "--env",
        "PYTHONPATH=/code:/code/helpers:/opt/torch-reviews/vendor",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "OPENBLAS_NUM_THREADS=1",
        "--env",
        "OMP_NUM_THREADS=1",
        "--env",
        f"SLURM_JOB_ID={os.environ['SLURM_JOB_ID']}",
    ]
    if module:
        args += [
            "--bind",
            f"{batch / 'timing-module.so'}:/opt/postgresql/lib/vector.so:ro",
            "--bind",
            f"{batch / 'work'}:/run:rw",
        ]
    return args + [config["image"], "python", "-B", "/code/" + program]


def serve(
    stage, run, deadline, config, *, execute_fn=execute, sleep=time.sleep, clock=time.monotonic
):
    state = {
        "status": "running",
        "job_id": os.environ["SLURM_JOB_ID"],
        "started_epoch": time.time() - (deadline.clock() - deadline.start),
        "kit_sha256": sha(stage / "SHA256SUMS") if (stage / "SHA256SUMS").exists() else None,
        "qualified": False,
        "attempts": config.get("prior_attempts", 0),
        "completed_batches": 0,
        "wall_seconds": config.get("wall_seconds", 21600),
        "admission_seconds": deadline.admission_seconds,
        "work_seconds": deadline.work_seconds,
        "development_seconds": config.get("development_seconds", 10800),
        "idle_seconds": IDLE_SECONDS,
        "development_attempt_limit": ATTEMPT_LIMIT - FINAL_RESERVED_ATTEMPTS,
        "final_attempts_reserved": FINAL_RESERVED_ATTEMPTS,
        "prior_allocated_seconds": config.get("prior_allocated_seconds", 0),
    }
    write(run / "state.json", state)
    last_active = clock()
    try:
        while True:
            deadline.admit()
            requests = sorted((run / "requests").glob("*/ready"))
            if not requests:
                heartbeat = run / "controller-heartbeat.json"
                active = False
                if heartbeat.exists():
                    record = read(heartbeat)
                    age = time.time() - record["epoch"]
                    active = record["job_id"] == state["job_id"] and -30 <= age < IDLE_SECONDS
                if clock() - last_active >= IDLE_SECONDS and not active:
                    state["status"] = "stopped_idle"
                    break
                sleep(2)
                continue
            batch = requests[0].parent
            # Claim before any side effect. A restarted job cannot redispatch a claimed batch.
            (batch / "ready").rename(batch / "claimed")
            request = read(batch / "request.json")
            if (
                request["job_id"] != state["job_id"]
                or digest(request["payload"]) != request["payload_sha256"]
            ):
                raise ValueError("request/job binding changed")
            mode = request["payload"]["mode"]
            count = len(request["payload"]["policies"])
            families = 2 * count + 2
            # Full quality, forced prefixes, four timing samples, warmups and ledger window.
            worst = (
                3150 * families
                + 3150 * count
                + SCREEN_GROUPS * 7 * families * 4
                + families * 4 * 7 * 2
                + 32
            )
            if mode == "final":
                worst = FINAL_RESERVED_ATTEMPTS
                if state.get("final_started"):
                    raise ValueError("final comparison already started; no retry")
                state["final_started"] = True
                state["frozen_policy_sha256"] = digest(request["payload"]["policies"][0])
                state["accepting_requests"] = False
                write(run / "state.json", state)
            ceiling = ATTEMPT_LIMIT if mode == "final" else ATTEMPT_LIMIT - FINAL_RESERVED_ATTEMPTS
            if mode != "qualification" and state["attempts"] + worst > ceiling:
                write(
                    batch / "response.json",
                    {
                        "status": "budget_rejected",
                        "request_id": request["request_id"],
                        "remaining": ceiling - state["attempts"],
                        "worst_case": worst,
                        "final_budget_preserved": True,
                    },
                )
                last_active = clock()
                continue
            write(
                batch / "budget.json",
                {"prior_attempts": state["attempts"], "attempt_limit": ceiling},
            )
            result = None
            try:
                (batch / "work").mkdir(mode=0o700)
                compile_cmd = container(stage, config, batch, run, "compile_batch.py") + [
                    "--stage",
                    "/code",
                    "--batch",
                    "/batch",
                ]
                rc = execute_fn(compile_cmd, batch / "compile-host.log", deadline.remaining())
                if rc:
                    raise RuntimeError("build failed; see compile-host.log")
                native_cmd = container(stage, config, batch, run, "native_batch.py", module=True)
                rc = execute_fn(native_cmd, batch / "native-host.log", deadline.remaining())
                if rc or not (batch / "native-response.json").is_file():
                    raise RuntimeError("native batch incomplete; preserve logs and partial data")
                result = read(batch / "native-response.json")
                if result["status"] not in ("measured", "quality_rejected", "final_complete"):
                    raise RuntimeError("native result did not complete")
                if not result.get("private_cleanup_verified"):
                    raise RuntimeError("private database cleanup did not verify")
                work = batch / "work"
                if (work / ".torch-owned").read_text().strip() != state["job_id"] or (
                    work / "pgdata/postmaster.pid"
                ).exists():
                    raise RuntimeError("private database ownership/stopped-state differs")
                if (work / "server.log").is_file():
                    shutil.copyfile(work / "server.log", batch / "results/server.log")
                shutil.rmtree(work)
                if (
                    request["payload_sha256"] == config.get("qualification_payload_sha256")
                    and result["status"] == "measured"
                ):
                    state["qualified"] = True
                    state["qualification_feedback"] = result.get("feedback")
                if mode == "final":
                    state["status"] = "completed_frozen_comparison"
            except Exception as error:
                result = {
                    "status": "failed",
                    "request_id": request["request_id"],
                    "error": str(error),
                    "automatic_retry": False,
                }
                state["status"] = "stopped_batch_failure"
            finally:
                if (batch / "attempts.json").is_file():
                    state["attempts"] += read(batch / "attempts.json")["total"]
                state["completed_batches"] += 1
                write(run / "state.json", state)
            # Publish only after cleanup, attempts and readiness state are durable.
            write(batch / "response.json", result)
            if state["status"] != "running":
                break
            if state["attempts"] >= ATTEMPT_LIMIT:
                state["status"] = "stopped_attempt_limit"
                break
            last_active = clock()
    except TimeoutError:
        state["status"] = "stopped_deadline"
    except BaseException:
        state["status"] = "stopped_interrupted"
        raise
    finally:
        write(run / "state.json", state)
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()

    def stop(_signum, _frame):
        raise TimeoutError("worker termination requested")

    signal.signal(signal.SIGTERM, stop)
    stage = args.stage.resolve()
    # Starts before image verification or extraction, so setup consumes the same clock.
    config = read(stage / "config.json")
    deadline = Deadline(
        work_seconds=config["work_seconds"], admission_seconds=config["admission_seconds"]
    )
    job = os.environ["SLURM_JOB_ID"]
    if not job.isdigit() or os.environ.get("SLURM_RESTART_COUNT", "0") != "0":
        raise ValueError("fresh Slurm allocation required; no restart/requeue")
    run = stage / ("run-" + job)
    run.mkdir(mode=0o700)  # Existing run means refuse all execution, including forced requeues.
    (run / "requests").mkdir(mode=0o700)
    if sha(config["image"]) != config["image_sha256"]:
        raise ValueError("runtime image changed")
    # The sealed original archive contains only immutable helper sources; never shell out to it.
    (run / "original").mkdir(mode=0o700)
    unpack_sources(stage / "original-package.tar.gz", run / "original")
    serve(stage, run, deadline, config)


if __name__ == "__main__":
    main()
