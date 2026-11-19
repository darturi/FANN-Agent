"""Reuse qualified M5 measurement functions with a new bounded, dynamic candidate pool."""

import json
import os
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from analysis import summarize
from limits import FILTERS, SCREEN_GROUPS, read, sha, write
from measurement import Ledger, quality, timing


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
    args = SimpleNamespace(
        bundle=Path("/bundle"),
        prepared=Path("/prepared"),
        work=Path("/run"),
        output=batch / "results",
        ef=640,
        fixture=False,
        phase="timing",
        arms=binding["arms"],
        counter=Counter(total=0),
    )
    args.output.mkdir(mode=0o700)
    (args.work / "socket").mkdir(mode=0o700)
    (args.work / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")
    budget = read(batch / "budget.json")
    args.ledger = Ledger(batch, budget["prior_attempts"], budget["attempt_limit"])
    mode = binding["mode"]
    roles = read(stage / "query-roles.json")
    queries = rows(stage / "queries.jsonl")
    if mode != "final":
        queries = [q for q in queries if roles[q["id"]] == "development"]
    if mode == "qualification":
        queries = [
            next(
                q
                for q in queries
                if q["id"].endswith("-" + ("unfiltered" if t < 0 else "votes" + str(t)))
            )
            for t in FILTERS
        ]
    selected = {q["id"] for q in queries}
    cases = {r["id"]: r for r in rows(stage / "source-cases.jsonl") if r["id"] in selected}
    truths = {
        r["id"]: r["output"]
        for r in rows(stage / "source-exact-reference.jsonl")
        if r["id"] in selected
    }
    entries = {r["arm"]: r for r in read(batch / "compiled-programs.json")["bindings"]}
    known = {}
    for name in ("full_workload-choices.jsonl", "heldout_test-choices.jsonl"):
        for r in rows(stage / name):
            if r["id"] in selected:
                known[r["id"], r["checkpoint"]] = r["output"]
    require(set(cases) == set(truths) == selected, "source case coverage differs")
    if mode == "development":
        require(len(queries) == 3150, "all development cases required")
    elif mode == "final":
        require(len(queries) == 7000, "full final workload required")
    restored = False
    try:
        identity = frozen.frozen.restore(
            frozen.source,
            args.bundle,
            args.prepared,
            args.work,
            runner,
            extra_sql=(stage / "functions.sql").read_text(),
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
            require(
                eligible
                == {int(t): set(ids) for t, ids in read(stage / "source-eligibility.json").items()},
                "fresh eligibility differs from qualified source",
            )
            write(
                args.output / "membership-setup.json",
                [
                    publish(args.work / f"membership-{t}.bin", heap, index, corpus, t)
                    for t in FILTERS
                ],
            )
            expected, quality_rows, losses = quality(
                Backend, args, queries, eligible, truths, cases, entries, known
            )
            quality_ok = not any(v for k, v in losses.items() if k.startswith("candidate"))
            timed = []
            if quality_ok or mode == "final":
                import hashlib

                groups = sorted(
                    {q["id"].rsplit("-", 1)[0] for q in queries},
                    key=lambda g: hashlib.sha256(("live-v3-screen:" + g).encode()).hexdigest(),
                )
                if mode == "development":
                    groups = groups[:SCREEN_GROUPS]
                screen = [q for q in queries if q["id"].rsplit("-", 1)[0] in set(groups)]
                write(
                    args.output / "timing-freeze.json",
                    {
                        "policy_hashes": [e["policy_hash"] for e in entries.values()],
                        "quality_sha256": sha(args.output / "quality.jsonl"),
                        "cases": len(screen),
                        "mode": mode,
                    },
                )
                timing(Backend, args, screen, eligible, expected)
                timed = rows(args.output / "timing.jsonl")
            frozen.frozen.verify_import(runner, args.bundle, args.work)
            feedback = None if mode == "final" else summarize(quality_rows, timed, tuple(args.arms))
            result = {
                "status": "final_complete"
                if mode == "final"
                else "measured"
                if quality_ok
                else "quality_rejected",
                "request_id": binding["request_id"],
                "payload_sha256": binding["payload_sha256"],
                "job_id": os.environ["SLURM_JOB_ID"],
                "mode": mode,
                "module_sha256": binding["module_sha256"],
                "feedback": feedback,
                "quality_loss_cases": losses,
                "quality_cases": len(queries),
                "timing_records": len(timed),
                "queries": dict(args.counter),
                "validation_test_opened": mode == "final",
                "fresh_exact_queries": 0,
                "automatic_retry": False,
            }
    finally:
        args.ledger.finish(args.counter)
        frozen.frozen.stop(args.work)
        if restored:
            frozen.frozen.verify_index(args.work, frozen.index)
    require(rb_native.memory_events(memory_group) == events, "memory event during measurement")
    result["private_cleanup_verified"] = True
    result["raw_sha256"] = {p.name: sha(p) for p in args.output.iterdir() if p.is_file()}
    write(batch / "native-response.json", result)


if __name__ == "__main__":
    main()
