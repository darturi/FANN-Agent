"""Torch-only native qualification/measurement on a private verified restore."""

import argparse
import os
import platform
import shutil
import signal
import time
from pathlib import Path

from ef_common import COUNTS, OPERATIONS, bootstrap, digest, read, replace, save, sha, verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=int, required=True)
    args = parser.parse_args()
    package, out, work = Path("/patch"), Path("/results"), Path("/run")
    cfg = verify(package)
    if os.uname().machine != "x86_64" or args.block not in range(COUNTS["allocations"]):
        raise RuntimeError("Requires a declared x86_64 Torch block")
    source_cfg = read(package / "frozen/experiment.json")
    if os.environ.get("TORCH_IMAGE_SHA256") != source_cfg["image_sha256"]:
        raise RuntimeError("Frozen image environment differs")
    bootstrap(package)
    from database import prepare, stop
    from ef_interface import factory
    from ef_measure import measure
    from execution import Budget, load_backend
    from fannagent_pgvector.profiles import PROFILE
    from runtime_base import verify_index

    frozen_path = package / "frozen"
    frozen, Backend = load_backend(frozen_path)
    budget = Budget(COUNTS["searches_per_block"], seconds=cfg["maximum_seconds"])
    started = time.monotonic()
    running, code, readers = False, 1, []

    def notify(phase, **fields):
        value = {"phase": phase, "block": args.block, "provider_calls": 0, **fields}
        replace(out / "progress.json", value)
        print(__import__("json").dumps(value), flush=True)

    def interrupted(number, frame):
        raise InterruptedError("Slurm signal " + str(number))

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGUSR1):
        signal.signal(sig, interrupted)
    try:
        notify("restore_and_verify_index")
        expected = prepare(frozen_path, Path("/bundle"), Path("/prepared"), work, frozen)
        running = True
        save(out / "database-identity.json", expected)
        if sha("/opt/postgresql/lib/vector.so") != source_cfg["module_sha256"]:
            raise RuntimeError("Executed native module differs")
        save(
            out / "runtime-identity.json",
            {
                "module_sha256": sha("/opt/postgresql/lib/vector.so"),
                "runtime_profile_hash": PROFILE.fingerprint,
                "registry_hash": PROFILE.native_registry_hash,
                "package_manifest_sha256": sha(package / "manifest.json"),
                "image_sha256": source_cfg["image_sha256"],
            },
        )
        init_start = time.perf_counter_ns()
        source = Backend(Path("/bundle"), work)
        readers.append(source)
        if source.state["source_manifest"]["settings"] != cfg["source_settings"]:
            raise RuntimeError("Origin settings differ from inspected source")
        snapshot = source.snapshot()
        eligibility = {
            "source_ids": snapshot.source_ids,
            "votes": [r["metadata"]["total_votes"] for r in snapshot.rows],
        }
        if digest(eligibility) != sha(package / "eligibility.json"):
            raise RuntimeError("Restored snapshot metadata/ID ordering differs")
        create = factory(Backend, Path("/bundle"), work, snapshot)
        reference = create(640)
        readers.append(reference)
        reference._connect()
        save(
            out / "shared-initialization.json",
            {
                "outer_ms": (time.perf_counter_ns() - init_start) / 1e6,
                "snapshot_identity": snapshot.identity,
                "eligibility_sha256": digest(eligibility),
                "origin_manifest": source.state["source_manifest"],
                "source_effort": int(cfg["source_settings"]["hnsw.ef_search"]),
                "study_reference_effort": 640,
                "excluded_scope": cfg["measurement_scope"]["shared_state"],
            },
        )
        save(
            out / "host.json",
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "server": source._connect().execute("SELECT version()").fetchone()[0],
                "cpu_affinity": sorted(os.sched_getaffinity(0)),
                "load": os.getloadavg(),
                "job_id": os.environ.get("SLURM_JOB_ID"),
            },
        )
        counts = measure(
            create, reference, source, frozen.score, budget, package, out, args.block, notify
        )
        if create.created + 1 != COUNTS["reader_connections_per_block"]:
            raise RuntimeError("Reader admission count differs")
        verify_index(work, expected)
        if sha("/opt/postgresql/lib/vector.so") != source_cfg["module_sha256"]:
            raise RuntimeError("Module changed during execution")
        if (
            dict(budget.operations) != OPERATIONS
            or time.monotonic() - started > cfg["maximum_seconds"]
        ):
            raise RuntimeError("Operation accounting/deadline differs")
        save(
            out / "status.json",
            {
                "status": "complete",
                "block": args.block,
                "provider_calls": 0,
                "confirmation_queries": 0,
                "new_fits": 0,
                "cases": 600,
                "vectors": 200,
                "backend_searches": budget.calls,
                "operations": dict(budget.operations),
                "elapsed_seconds": time.monotonic() - started,
                "control_installations": budget.control_installations,
                "reader_connections": create.created + 1,
                "index_and_module_after_verified": True,
                **counts,
            },
        )
        code = 0
    except BaseException as error:
        save(
            out / "failure.json",
            {
                "type": type(error).__name__,
                "message": str(error),
                "backend_searches": budget.calls,
                "operations": dict(budget.operations),
            },
        )
        raise
    finally:
        cleanup = 0
        for reader in readers:
            reader.close()
        if running or (work / "pgdata/postmaster.pid").exists():
            try:
                stop(work)
            except BaseException:
                cleanup = 1
        if (work / "server.log").exists():
            shutil.copyfile(work / "server.log", out / "server.log")
        save(out / "job-exit.json", {"exit_code": code or cleanup, "work_directory_retained": True})
        if cleanup:
            raise RuntimeError("Database cleanup failed")
    save(
        out / "LOCK.json",
        {
            "package_manifest_sha256": sha(package / "manifest.json"),
            "files_sha256": {
                p.name: sha(p)
                for p in sorted(out.iterdir())
                if p.is_file() and p.name not in {"LOCK.json", "progress.json"}
            },
        },
    )


if __name__ == "__main__":
    main()
