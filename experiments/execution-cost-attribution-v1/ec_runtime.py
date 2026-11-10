"""Torch-only private database execution, zero models and zero confirmation."""

import argparse
import os
import shutil
import signal
import time
from pathlib import Path

from ec_common import COUNTS, bootstrap, read, replace, save, sha, verify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=int, required=True)
    args = parser.parse_args()
    package, out, work = Path("/patch"), Path("/results"), Path("/run")
    cfg = verify(package)
    if os.uname().machine != "x86_64" or args.block not in range(3):
        raise RuntimeError("Requires a declared x86_64 Torch block")
    if (
        os.environ.get("TORCH_IMAGE_SHA256")
        != read(package / "frozen/experiment.json")["image_sha256"]
    ):
        raise RuntimeError("Frozen runner image environment differs")
    bootstrap(package)
    from database import prepare, stop
    from ec_measure import measure
    from execution import Budget, load_backend
    from fannagent_pgvector.profiles import PROFILE
    from runtime_base import verify_index

    source = package / "frozen"
    frozen, Backend = load_backend(source)
    budget = Budget(COUNTS["searches_per_block"], seconds=cfg["maximum_seconds"])
    started = time.monotonic()
    running = False
    backend = None
    code = 1

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
        expected = prepare(source, Path("/bundle"), Path("/prepared"), work, frozen)
        running = True
        save(out / "database-identity.json", expected)
        source_cfg = read(source / "experiment.json")
        if sha("/opt/postgresql/lib/vector.so") != source_cfg["module_sha256"]:
            raise RuntimeError("Executed binary differs")
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
        backend = Backend(Path("/bundle"), work)
        backend.state["source_manifest"]["settings"]["hnsw.ef_search"] = "640"
        counts = measure(backend, frozen, budget, package, out, args.block, notify)
        verify_index(work, expected)
        if time.monotonic() - started > cfg["maximum_seconds"]:
            raise RuntimeError("Work deadline exceeded")
        save(
            out / "status.json",
            {
                "status": "complete",
                "block": args.block,
                "provider_calls": 0,
                "confirmation_queries": 0,
                "development_cases": 600,
                "independent_vectors": 200,
                "diagnostic_cases": 180,
                "backend_searches": budget.calls,
                "operations": dict(budget.operations),
                "control_installations": budget.control_installations,
                "control_sql_note": (
                    "Eviction installs counted separately; other SQL statements are not counted."
                ),
                "elapsed_seconds": time.monotonic() - started,
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
        if backend:
            backend.close()
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
