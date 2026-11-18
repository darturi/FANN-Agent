"""Run the explicitly requested full/held-out oracle on a private original-graph copy."""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from time import monotonic, perf_counter_ns

from common import publish, sha, write
from oracle_design import FILTERS, IMAGE, PACKAGE_SHA, require
from oracle_experiment import acquire, offline, timing

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    for name in ("package", "bundle", "prepared", "work", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.fixture = False
    args.ef = 640
    require(
        os.uname().machine == "x86_64" and os.environ.get("SLURM_JOB_ID", "").isdigit(),
        "requires a Torch x86 Slurm allocation",
    )
    sys.path.insert(0, str(args.package))
    from rb_native import (
        BASE_MANIFEST,
        RUNNER,
        load_stage,
        memory_events,
        resource_limits,
        watchdog,
    )

    binding = json.loads((HERE / "binding.json").read_text())
    for name, expected in binding["files"].items():
        require(sha(HERE / name) == expected, "oracle input changed: " + name)
    require(
        sha("/opt/postgresql/lib/vector.so") == sha(HERE / "oracle-module.so"),
        "wrong oracle module",
    )
    require(sha(args.bundle / "images/runtime.sif") == IMAGE, "runtime image changed")
    queries = [json.loads(line) for line in (HERE / "queries.jsonl").read_text().splitlines()]
    args.roles = json.loads((HERE / "query-roles.json").read_text())
    args.prior_native = {
        row["id"]: row["output"]
        for row in (
            json.loads(line) for line in (HERE / "native-reference.jsonl").read_text().splitlines()
        )
    }
    require(len(args.prior_native) == 3150, "qualified native bridge coverage changed")
    require(
        len(queries) == len({q["id"] for q in queries}) == len(args.roles) == 7000,
        "full case coverage changed",
    )
    require(
        Counter(args.roles.values())
        == {"development": 3150, "validation": 1050, "test": 1925, "excluded_historical": 875},
        "split membership changed",
    )
    require(all(len(q["vector"]) == 768 for q in queries), "query dimensions changed")
    stage = load_stage(args.package, PACKAGE_SHA)
    require(
        sha(args.bundle / "manifest.json") == BASE_MANIFEST
        and sha("/opt/torch-reviews/runner.py") == RUNNER,
        "base capsule changed",
    )
    manifest = json.loads((args.bundle / "manifest.json").read_text())["files"]
    for name in (
        "images/runtime.sif",
        "inputs/reviews.parquet",
        "inputs/local-identity.json",
        "experiment.json",
    ):
        require(sha(args.bundle / name) == manifest[name], "base input changed: " + name)
    ready = json.loads((args.prepared / "READY.json").read_text())
    require(
        ready["architecture"] == "x86_64"
        and ready["image_sha256"] == IMAGE
        and json.loads((args.prepared / "database-identity.json").read_text())
        == stage.index
        == binding["graph"],
        "original graph identity changed",
    )
    for folder in (args.package, args.bundle, args.prepared, HERE):
        require(os.statvfs(folder).f_flag & os.ST_RDONLY, "input must be mounted read-only")
    runner, Backend = stage.frozen.execution.load_backend(stage.source)
    from startup import install

    startup = install(stage.frozen.restore)
    for folder in (args.work, args.output):
        require(
            folder.is_dir() and not any(folder.iterdir()) and not folder.stat().st_mode & 0o077,
            "private empty work/output required",
        )
    (args.work / "socket").mkdir(mode=0o700)
    (args.work / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")
    import rb_native

    rb_native.MEMORY_BYTES = 48 * 1024**3
    limits, memory_group = resource_limits()
    events = memory_events(memory_group)
    from psycopg import connect
    from psycopg.conninfo import make_conninfo

    counter = Counter(total=0)
    started = monotonic()
    # Written before first query: this diagnostic exposes the protected outcomes.
    write(
        args.output / "exposure.json",
        {
            "purpose": "user-requested hindsight oracle, full workload and held-out subset",
            "roles": dict(Counter(args.roles.values())),
            "test_outcomes_authorized": True,
            "agent_training_allowed": False,
            "confirmatory_agent_test": False,
            "job_id": os.environ["SLURM_JOB_ID"],
        },
    )
    with watchdog(19500):
        try:
            identity = stage.frozen.restore(
                stage.source,
                args.bundle,
                args.prepared,
                args.work,
                runner,
                extra_sql=(HERE / "functions.sql").read_text(),
            )
            require(identity == binding["graph"], "private restore graph changed")
            dsn = make_conninfo(
                runner.job_connection(args.work, admin=True), dbname="torch_reviews"
            )
            with connect(dsn, autocommit=True) as keeper, keeper.transaction():
                keeper.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                keeper.execute("SET LOCAL idle_in_transaction_session_timeout=0")
                keeper.execute("LOCK TABLE public.reviews IN SHARE MODE NOWAIT")
                args.snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
                heap, index = keeper.execute(
                    "SELECT 'public.reviews'::regclass::oid,'public.reviews_hnsw'::regclass::oid"
                ).fetchone()
                rows = keeper.execute(
                    "SELECT ctid::text,total_votes FROM ONLY public.reviews"
                ).fetchall()
                source = keeper.execute("SELECT id,total_votes FROM ONLY public.reviews").fetchall()
                require(
                    len(source) == len({i for i, _ in source}) == 247286,
                    "source ID inventory differs",
                )
                maps = []
                for t in FILTERS:
                    start = perf_counter_ns()
                    meta = publish(args.work / f"membership-{t}.bin", heap, index, rows, t)
                    maps.append({**meta, "build_ns": perf_counter_ns() - start})
                write(args.output / "membership-setup.json", maps)
                write(args.output / "private-startup.json", startup)
                eligible = {
                    t: {i for i, v in source if t < 0 or v is not None and v >= t} for t in FILTERS
                }
                write(
                    args.output / "eligibility.json",
                    {str(t): sorted(ids) for t, ids in eligible.items()},
                )
                truths = offline(Backend, args, queries, eligible, counter)
                # offline() closes every exact reader before acquisition/timing.
                choices = acquire(Backend, args, queries, eligible, truths, counter)
                timing(Backend, args, queries, eligible, choices, counter)
                stage.frozen.verify_import(runner, args.bundle, args.work)
        finally:
            stage.frozen.stop(args.work)
            for t in FILTERS:
                (args.work / f"membership-{t}.bin").unlink(missing_ok=True)
            stage.frozen.verify_index(args.work, stage.index)
    require(memory_events(memory_group) == events, "memory limit event")
    require(
        counter["timed_ann"] == 7000 * 32 and counter["offline_exact"] == 7000,
        "incomplete acquisition/timing",
    )
    write(
        args.output / "receipt.json",
        {
            "status": "full_workload_oracle_complete",
            "job_id": os.environ["SLURM_JOB_ID"],
            "binding_sha256": sha(HERE / "binding.json"),
            "graph": stage.index,
            "module_sha256": sha(HERE / "oracle-module.so"),
            "searches": dict(counter),
            "groups": 1000,
            "cases": 7000,
            "heldout_groups": 275,
            "heldout_cases": 1925,
            "exact_serving_calls": 0,
            "provider_calls": 0,
            "limits": limits,
            "data_index_before_after": True,
            "elapsed_seconds": monotonic() - started,
            "machine": os.uname().nodename,
            "raw_sha256": {p.name: sha(p) for p in args.output.iterdir() if p.is_file()},
        },
    )
    print("FULL_WORKLOAD_ORACLE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
