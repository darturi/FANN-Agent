"""Reuse qualified M5 measurement functions with a new bounded, dynamic candidate pool."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from analysis import summarize
from limits import FILTERS, SCREEN_GROUPS, read, sha, write


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    stage, batch = Path("/code"), Path("/batch")
    binding = read(batch / "batch-binding.json")
    source = read(stage / "source-binding.json")
    if sha("/opt/postgresql/lib/vector.so") != binding["module_sha256"]:
        raise ValueError("loaded module differs from this candidate batch")
    if sha(batch / "compiled-programs.json") != binding["programs_sha256"]:
        raise ValueError("compiled policy manifest changed")
    package = Path("/original/reviews-persistent-batch-native-v1")
    sys.path.insert(0, str(package))
    import m5_design as design
    import m5_experiment as measurement
    import rb_native
    from common import publish, require
    from psycopg import connect
    from psycopg.conninfo import make_conninfo
    from startup import install

    frozen = rb_native.load_stage(package, source["original_manifest_sha256"])
    runner, Backend = frozen.frozen.execution.load_backend(frozen.source)
    rb_native.MEMORY_BYTES = 48 * 1024**3
    _, memory_group = rb_native.resource_limits()
    events = rb_native.memory_events(memory_group)
    install(frozen.frozen.restore)
    require(frozen.index == source["graph"], "original graph binding differs")
    require(sha("/bundle/manifest.json") == rb_native.BASE_MANIFEST, "corpus manifest differs")
    require(sha("/opt/torch-reviews/runner.py") == rb_native.RUNNER, "runner differs")
    for name in ("inputs/reviews.parquet", "inputs/local-identity.json", "experiment.json"):
        require(
            sha(Path("/bundle") / name) == read("/bundle/manifest.json")["files"][name],
            "source input differs: " + name,
        )
    require(read("/prepared/database-identity.json") == frozen.index, "prepared graph differs")
    arms = binding["arms"]
    design.ARMS = measurement.ARMS = arms
    design.GROUPS = measurement.GROUPS = (tuple(arms),)
    design.EXPECTED_STOPS = {}  # New policies have no historical expected stop-count inventory.
    design.SEED = "torch-live-screen-v1"
    entries = {e["arm"]: e for e in read(batch / "compiled-programs.json")["bindings"]}
    require(set(entries) == {a for a in arms.values() if a is not None}, "arm pool differs")
    for entry in entries.values():
        require(
            all(
                plan == design.masks(entry["policy"], f)
                for f, plan in entry["observation_plan"].items()
            ),
            "mask dependency differs",
        )
    output = batch / "results"
    output.mkdir(mode=0o700)
    args = SimpleNamespace(
        bundle=Path("/bundle"),
        prepared=Path("/prepared"),
        work=Path("/run"),
        output=output,
        phase="timing",
        ef=640,
        fixture=False,
        previous_attempts=0,
    )
    (args.work / "socket").mkdir(mode=0o700)
    (args.work / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")
    budget = read(batch / "budget.json")
    attempts = {"total": 0}

    def reserve(counter, operation, _args):
        require(
            budget["prior_attempts"] + counter["total"] < budget["attempt_limit"],
            "episode's combined native attempt limit reached",
        )
        counter["total"] += 1
        counter[operation] = counter.get(operation, 0) + 1
        # Reservation precedes each query. Fsync is outside the serving request timer.
        write(batch / "attempts.json", counter)

    measurement.reserve = reserve
    queries = rows(stage / "queries.jsonl")
    require(len(queries) == 3150, "complete development workload required")
    expected = {r["id"]: r for r in rows(stage / "expected.jsonl")}
    prior = {r["id"]: r for r in rows(stage / "prior-references.jsonl")}
    require(set(expected) == set(prior) == {q["id"] for q in queries}, "reference coverage differs")
    restored = False
    result = None
    try:
        identity = frozen.frozen.restore(
            frozen.source,
            args.bundle,
            args.prepared,
            args.work,
            runner,
            extra_sql=(stage / "measurement/functions.sql").read_text(),
        )
        restored = True
        require(identity == frozen.index, "private restore identity differs")
        dsn = make_conninfo(runner.job_connection(args.work, admin=True), dbname="torch_reviews")
        with connect(dsn, autocommit=True) as keeper, keeper.transaction():
            keeper.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            keeper.execute("SET LOCAL idle_in_transaction_session_timeout=0")
            keeper.execute("LOCK TABLE public.reviews IN SHARE MODE NOWAIT")
            args.snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
            heap, index = keeper.execute(
                "SELECT 'public.reviews'::regclass::oid,'public.reviews_hnsw'::regclass::oid"
            ).fetchone()
            corpus = keeper.execute(
                "SELECT ctid::text,total_votes FROM ONLY public.reviews"
            ).fetchall()
            ids = keeper.execute("SELECT id,total_votes FROM ONLY public.reviews").fetchall()
            require(len(ids) == len({i for i, _ in ids}) == 247286, "source ID mapping differs")
            eligible = {
                t: {i for i, v in ids if t < 0 or v is not None and v >= t} for t in FILTERS
            }
            write(
                output / "membership-setup.json",
                [
                    publish(args.work / f"membership-{t}.bin", heap, index, corpus, t)
                    for t in FILTERS
                ],
            )
            # Verified exact references are evaluator-only data. No exact reader is opened.
            truths = {qid: value["exact"] for qid, value in prior.items()}
            quality_ok = True
            try:
                cache, quality_summary = measurement.quality(
                    Backend, args, queries, eligible, truths, expected, attempts, entries
                )
            except RuntimeError as error:
                if str(error) != "M5 quality regression: preserve result, do not time/promote":
                    raise
                quality_ok = False
            quality = rows(output / "quality.jsonl")
            if quality_ok:
                require(
                    quality_summary["prefixes"]["reached"] == 9436
                    and quality_summary["prefixes"]["partial"] == 1496,
                    "qualified prefix inventory differs",
                )
                # Same deterministic vector groups across all filters and every adaptive round.
                import hashlib

                groups = sorted(
                    {q["id"].rsplit("-", 1)[0] for q in queries},
                    key=lambda g: hashlib.sha256(("live-screen-v1:" + g).encode()).hexdigest(),
                )[:SCREEN_GROUPS]
                screen = [q for q in queries if q["id"].rsplit("-", 1)[0] in set(groups)]
                require(
                    len(screen) == SCREEN_GROUPS * len(FILTERS), "screen filter coverage differs"
                )
                measurement.timing(Backend, args, screen, eligible, cache, attempts)
            frozen.frozen.verify_import(runner, args.bundle, args.work)
            result = {
                "status": "measured" if quality_ok else "quality_rejected",
                "request_id": binding["request_id"],
                "job_id": os.environ["SLURM_JOB_ID"],
                "payload_sha256": binding["payload_sha256"],
                "module_sha256": binding["module_sha256"],
                "feedback": summarize(
                    quality, rows(output / "timing.jsonl") if quality_ok else [], tuple(arms)
                ),
                "quality_queries": len(queries),
                "attempts": attempts,
                "validation_test_opened": False,
                "exact_serving_queries": 0,
                "work_counters_measured": False,
                "automatic_retry": False,
            }
    finally:
        write(batch / "attempts.json", attempts)
        frozen.frozen.stop(args.work)
        if restored:
            frozen.frozen.verify_index(args.work, frozen.index)
    require(rb_native.memory_events(memory_group) == events, "memory event during measurement")
    result["private_cleanup_verified"] = True
    result["raw_sha256"] = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    write(batch / "native-response.json", result)


if __name__ == "__main__":
    main()
