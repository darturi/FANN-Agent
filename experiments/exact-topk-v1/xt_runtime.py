"""Torch-only single allocation; conformance, quality-first screen, conditional timing."""

import argparse
import os
import platform
import shutil
import signal
import time
from pathlib import Path

from xt_common import (
    OPERATIONS,
    QUALITY_OPERATIONS,
    Budget,
    bootstrap,
    digest,
    lines,
    read,
    replace,
    save,
    sha,
    verify,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=int, required=True)
    args = parser.parse_args()
    package, out, work = Path("/patch"), Path("/results"), Path("/run")
    cfg = verify(package)
    if os.uname().machine != "x86_64" or args.block != 0 or not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Requires the single declared x86_64 Torch allocation")
    source_cfg = read(package / "frozen/experiment.json")
    if os.environ.get("TORCH_IMAGE_SHA256") != source_cfg["image_sha256"]:
        raise RuntimeError("Frozen image differs")
    bootstrap(package)
    from database import prepare, stop
    from execution import load_backend
    from fannagent_pgvector.profiles import PROFILE
    from runtime_base import verify_index
    from xt_interface import Factory
    from xt_measure import admit, measure

    frozen, Base = load_backend(package / "frozen")
    budget = Budget()
    started = time.monotonic()
    factory = Factory(Base, Path("/bundle"), work)
    running, code, cleanup_code = False, 1, 0
    counts, restore_charge = None, None

    def notify(phase, **fields):
        value = {"phase": phase, "provider_calls": 0, **fields}
        replace(out / "progress.json", value)
        print(__import__("json").dumps(value), flush=True)

    def interrupted(number, frame):
        raise InterruptedError("Slurm signal " + str(number))

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGUSR1):
        signal.signal(sig, interrupted)
    try:
        notify("restore_and_verify")
        begin = time.perf_counter_ns()
        expected = prepare(package / "frozen", Path("/bundle"), Path("/prepared"), work, frozen)
        end = time.perf_counter_ns()
        restore_charge = {"start_ns": begin, "end_ns": end, "outer_ms": (end - begin) / 1e6}
        running = True
        save(out / "database-identity.json", expected)
        if sha("/opt/postgresql/lib/vector.so") != source_cfg["module_sha256"]:
            raise RuntimeError("Native module differs")
        save(
            out / "runtime-identity.json",
            {
                "module_sha256": source_cfg["module_sha256"],
                "runtime_profile_hash": PROFILE.fingerprint,
                "registry_hash": PROFILE.native_registry_hash,
                "package_manifest_sha256": sha(package / "manifest.json"),
                "image_sha256": source_cfg["image_sha256"],
            },
        )
        begin = time.perf_counter_ns()
        reference = factory.create("native640", "initial-reference640")
        if reference.origin["settings"] != cfg["source_settings"]:
            raise RuntimeError("Origin settings changed")
        snapshot = reference.backend.snapshot()
        factory.snapshot = snapshot
        eligibility = {
            "source_ids": snapshot.source_ids,
            "votes": [r["metadata"]["total_votes"] for r in snapshot.rows],
        }
        if (
            digest(eligibility) != sha(package / "eligibility.json")
            or snapshot.identity != cfg["snapshot_identity"]
        ):
            raise RuntimeError("Snapshot/eligibility identity differs")
        items = admit(snapshot, lines(package / "frozen/inputs/queries.jsonl"))
        end = time.perf_counter_ns()
        save(
            out / "shared-initialization.json",
            {
                "start_ns": begin,
                "end_ns": end,
                "outer_ms": (end - begin) / 1e6,
                "snapshot_identity": snapshot.identity,
                "eligibility_sha256": digest(eligibility),
                "origin_manifest": reference.origin,
                "source_effort": 320,
                "study_reference_effort": 640,
                "admitted_requests": len(items),
                "snapshot_load_selects": 1,
            },
        )
        save(
            out / "host.json",
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "server": reference.connection.execute("SELECT version()").fetchone()[0],
                "cpu_affinity": sorted(os.sched_getaffinity(0)),
                "load": os.getloadavg(),
                "job_id": os.environ["SLURM_JOB_ID"],
                "synthetic_mock": False,
            },
        )
        counts = measure(factory, reference, frozen.score, budget, package, out, items, notify)
        passed = counts["quality_pass"]
        expected_operations = OPERATIONS if passed else QUALITY_OPERATIONS
        if dict(budget.operations) != expected_operations or len(factory.readers) != (
            14 if passed else 10
        ):
            raise RuntimeError("Search or reader admission accounting differs")
        verify_index(work, expected)
        if sha("/opt/postgresql/lib/vector.so") != source_cfg["module_sha256"]:
            raise RuntimeError("Native module changed")
        budget.check()
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
        begin = time.perf_counter_ns()
        try:
            factory.close()
            if running or (work / "pgdata/postmaster.pid").exists():
                stop(work)
        except BaseException:
            cleanup_code = 1
        end = time.perf_counter_ns()
        save(
            out / "admissions.json",
            {"readers": factory.admissions, "maximum_live_readers": factory.maximum_live},
        )
        save(
            out / "cleanup.json",
            {
                "start_ns": begin,
                "end_ns": end,
                "outer_ms": (end - begin) / 1e6,
                "all_readers_closed": all(r.closed for r in factory.readers),
                "database_stopped": not (work / "pgdata/postmaster.pid").exists(),
            },
        )
        if (work / "server.log").exists():
            shutil.copyfile(work / "server.log", out / "server.log")
        save(
            out / "job-exit.json",
            {"exit_code": code or cleanup_code, "work_directory_retained": True},
        )
        if cleanup_code:
            raise RuntimeError("Database/reader cleanup failed")
    budget.check()
    save(
        out / "charges.json",
        {
            "searches": budget.calls,
            "operations": dict(budget.operations),
            "restore_import": restore_charge,
            "explicit_reader_startup_execute_calls": 17 * len(factory.readers),
            "exact_internal_non_search_execute_calls": 20
            * (budget.operations["qualification_exact"] + budget.operations["reference_exact"]),
            "snapshot_and_server_selects": 2,
            "qualifier_diagnostic_sql": read(out / "qualification.json")["non_search_sql"],
            "observer": read(out / "metadata.json"),
            "quality_setting_queries": 2,
            "warm_boundary_setting_queries": 24 if counts["quality_pass"] else 0,
            "overlapping_categories_must_not_be_summed": True,
            "phase_details": (
                "Reader SQL counts come from unchanged inherited startup/exact source; "
                "diagnostics and phase boundaries are separately logged. Restore/auth/admin "
                "work remains in restore_import wall charge, not a statement-level profile."
            ),
        },
    )
    save(
        out / "status.json",
        {
            "status": "complete",
            "provider_calls": 0,
            "confirmation_queries": 0,
            "new_fits": 0,
            "cases": 600,
            "vectors": 200,
            "backend_searches": budget.calls,
            "operations": dict(budget.operations),
            "control_installations": 0,
            "reader_connections": len(factory.readers),
            "index_and_module_after_verified": True,
            "elapsed_seconds": time.monotonic() - started,
            "completed_temporal_blocks": 2 if counts["quality_pass"] else 0,
            **counts,
        },
    )
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
    notify("complete", quality_pass=counts["quality_pass"], backend_searches=budget.calls)


if __name__ == "__main__":
    main()
