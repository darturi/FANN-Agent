"""Qualify the live rules on the original graph, then time a frozen fresh cohort."""

import argparse
import json
import math
import os
from contextlib import contextmanager, nullcontext
from pathlib import Path
from time import perf_counter_ns

from analyze import BATCHES, FAMILIES, SIZE, matches, report, schedule
from rb_native import IMAGE, load_stage, memory_events, resource_limits, watchdog
from rb_plan import file_sha, pinned, pinned_lines, require

HERE = Path(__file__).resolve().parent
MODULE = Path("/opt/postgresql/lib/vector.so")
FREEZE_SHA = "97356451b79ee0fbfec82018efb8e39fca38d4bf384741a03d63d0938e212c31"
FRESH_SHA = "e02218ae29e9ddac0e68049a5b96720b3345789cf6ed615f1f936a8979d3597f"
PREDICATE = {"field": "m_000000", "op": "gte", "value": 108}
QUERY = """
SELECT "id", "embedding" <=> %s::vector AS distance
FROM "public"."reviews" WHERE "total_votes" >= %s
ORDER BY "embedding" <=> %s::vector
"""
ANN = QUERY + " LIMIT %s"
EXACT = QUERY + " FETCH FIRST 10 ROWS WITH TIES"
CONFIRM_BIND = "SELECT fannagent.confirm_bind('public.reviews','public.reviews_hnsw',%s)"


def params(query):
    require(
        query["k"] == SIZE and query["filter"] == PREDICATE and len(query["vector"]) == 768,
        "Unexpected votes108 request",
    )
    vector = "[" + ",".join(format(float(v), ".9g") for v in query["vector"]) + "]"
    return (vector, 108, vector)


def execute(conn, query, *, exact=False):
    args = params(query)
    rows = conn.execute(
        EXACT if exact else ANN, args if exact else (*args, SIZE), prepare=False
    ).fetchall()
    return [[i, float(d)] for i, d in rows]


def plan_scans(node):
    if "Scan" in node["Node Type"]:
        yield node
    for child in node.get("Plans", []):
        yield from plan_scans(child)


def check_plan(conn, query, expected_index):
    stmt = ANN if expected_index else EXACT
    args = params(query)
    root = conn.execute(
        "EXPLAIN (FORMAT JSON) " + stmt, (*args, SIZE) if expected_index else args, prepare=False
    ).fetchone()[0][0]["Plan"]
    scans = list(plan_scans(root))
    require(
        len(scans) == 1
        and scans[0].get("Relation Name") == "reviews"
        and (
            scans[0].get("Index Name") == "reviews_hnsw"
            if expected_index
            else scans[0]["Node Type"] == "Seq Scan"
        ),
        "Query plan does not use the intended Reviews search path",
    )


@contextmanager
def reader(backend_type, args, arm, *, activate=None):
    backend = backend_type(args.bundle, args.work)
    backend.state["source_manifest"]["settings"]["hnsw.ef_search"] = "640"
    try:
        conn = backend._connect()
        with conn.transaction() if arm != "native" else nullcontext():
            if arm != "native":
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            if arm in ("baseline", "candidate"):
                value = FAMILIES.index(arm)
                if activate is None:
                    require(
                        conn.execute(CONFIRM_BIND, (value,)).fetchone() == (247286,),
                        "Policy activation failed",
                    )
                else:
                    activate(conn, arm, value)
            if arm == "exact":
                conn.execute("SET LOCAL enable_seqscan = on")
                conn.execute("SET LOCAL enable_indexscan = off")
                conn.execute("SET LOCAL enable_indexonlyscan = off")
                conn.execute("SET LOCAL enable_bitmapscan = off")
                conn.execute("SET LOCAL max_parallel_workers_per_gather = 0")
            yield conn
    finally:
        backend.close()


def qualify(stage, reader_for, pins, *, families=FAMILIES):
    ids = {c.id for c in stage.plan.cases.values() if c.stratum == "votes108"}
    require(
        len(pins) == len(ids) == 200 and {p["id"] for p in pins} == ids, "Invalid parity inventory"
    )
    first = stage.plan.cases[pins[0]["id"]].query
    with reader_for("native") as conn:
        metadata = conn.execute("SELECT id,total_votes FROM public.reviews").fetchall()
        require(
            conn.execute(
                "SELECT current_setting('hnsw.ef_search'),current_setting('hnsw.iterative_scan')"
            ).fetchone()
            == ("640", "off"),
            "Native HNSW settings changed",
        )
    metadata.sort(key=lambda r: (type(r[0]).__name__, r[0]))
    source_ids = [r[0] for r in metadata]
    eligible = {i for i, (_, votes) in enumerate(metadata) if votes is not None and votes >= 108}
    require(
        len(source_ids) == len(set(source_ids)) == 247286
        and eligible == stage.evidence.eligible["votes108"],
        "Restored source IDs or eligibility differ",
    )
    parity = {}
    expected_stops = {"native": 0, "baseline": 21, "candidate": 56}
    for arm in families:
        stops = 0
        with reader_for(arm) as conn:
            check_plan(conn, first, expected_index=True)
            for pin in pins:
                qid = pin["id"]
                actual = execute(conn, stage.plan.cases[qid].query)
                cp = (
                    conn.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                    if arm != "native"
                    else 0
                )
                expected_cp, (expected_ids, distances) = pin["expected"][arm]
                expected = [
                    [source_ids[i], d] for i, d in zip(expected_ids, distances, strict=True)
                ]
                require(
                    cp == expected_cp and matches(actual, expected),
                    f"Live {arm} differs from saved original-graph output for {qid}: "
                    f"checkpoint {cp}, expected {expected_cp}",
                )
                stops += bool(cp)
        parity[arm] = {"queries": len(pins), "stops": stops}
    require(
        all(p["stops"] == expected_stops[arm] for arm, p in parity.items()),
        "Development stop inventory changed",
    )
    return parity, sorted(source_ids[i] for i in eligible)


def measure(fresh, reader_for, directory, *, before_timing=None, timing_recorder=None):
    quality = [{"id": query["id"]} for query in fresh]
    with reader_for("exact") as conn:
        check_plan(conn, fresh[0], expected_index=False)
        for row, query in zip(quality, fresh, strict=True):
            row["exact"] = execute(conn, query, exact=True)
    for arm in FAMILIES:
        with reader_for(arm) as conn:
            check_plan(conn, fresh[0], expected_index=True)
            for row, query in zip(quality, fresh, strict=True):
                out = execute(conn, query)
                cp = (
                    conn.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                    if arm != "native"
                    else 0
                )
                row[arm] = {"checkpoint": cp, "output": out}
    with (directory / "quality.jsonl").open("x") as f:
        for row in quality:
            f.write(json.dumps(row, allow_nan=False) + "\n")
    print("Recorded complete fresh-query recall evidence", flush=True)
    if before_timing is not None:
        before_timing(quality)
    if timing_recorder is not None:
        return timing_recorder(fresh, reader_for, directory)

    with (directory / "timing.jsonl").open("x") as f:
        for epoch, batch, arm, order in schedule():
            cases = [fresh[batch * SIZE + i] for i in order]
            family = arm.rsplit("-", 1)[0]
            output = []
            start = perf_counter_ns()
            with reader_for(family) as conn:
                ready = perf_counter_ns()
                for query in cases:
                    begin = perf_counter_ns()
                    result = execute(conn, query)
                    end = perf_counter_ns()
                    output.append({"id": query["id"], "request_ns": [begin, end], "output": result})
            closed = perf_counter_ns()
            f.write(
                json.dumps(
                    {
                        "epoch": epoch,
                        "batch": batch,
                        "arm": arm,
                        "session_ns": [start, ready, closed],
                        "queries": output,
                    },
                    allow_nan=False,
                )
                + "\n"
            )


def run(
    args,
    *,
    extra_sql="",
    reader_session=None,
    qualify_fn=qualify,
    measure_fn=measure,
    analysis_fn=report,
    extra_raw_files=(),
):
    require(
        os.uname().sysname == "Linux"
        and os.uname().machine == "x86_64"
        and os.environ.get("SLURM_JOB_ID", "").isdigit()
        and os.environ.get("TORCH_IMAGE_SHA256") == IMAGE,
        "Confirmation requires the original x86_64 Torch runtime",
    )
    stage = load_stage(args.package, args.package_sha)
    require(file_sha(args.bundle / "images/runtime.sif") == IMAGE, "Original runtime image differs")
    require(file_sha(MODULE) == args.module_sha, "Confirmation module differs")
    pinned(HERE / "freeze.json", FREEZE_SHA)
    pins = list(pinned_lines(HERE / "qualification.jsonl", args.qualification_sha))
    for directory in (args.work, args.output):
        require(
            directory.is_dir()
            and not any(directory.iterdir())
            and directory.stat().st_uid == os.getuid()
            and not directory.stat().st_mode & 0o077,
            "Use a new private job directory",
        )
    limits, memory_group = resource_limits()
    before = memory_events(memory_group)
    runner, backend_type = stage.frozen.execution.load_backend(stage.source)
    (args.work / "socket").mkdir(mode=0o700)
    (args.work / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")

    def reader_for(arm):
        return reader(backend_type, args, arm)

    with watchdog(6600):
        try:
            restored = stage.frozen.restore(
                stage.source,
                args.bundle,
                args.prepared,
                args.work,
                runner,
                extra_sql=(HERE / "functions.sql").read_text() + extra_sql,
            )
            require(restored == stage.index, "Restored physical index differs")
            session = (
                reader_session(runner, backend_type, args)
                if reader_session is not None
                else nullcontext((reader_for, None))
            )
            with session as (active_reader, before_timing):
                parity, eligible = qualify_fn(stage, active_reader, pins)
                print(f"Original-graph parity passed: {parity}", flush=True)
                fresh = list(pinned_lines(HERE / "fresh.jsonl", FRESH_SHA))
                require(
                    len(fresh) == len({q["id"] for q in fresh}) == BATCHES * SIZE
                    and not any(q["id"] in stage.plan.cases for q in fresh)
                    and all(all(math.isfinite(v) for v in q["vector"]) for q in fresh),
                    "Fresh query inventory differs",
                )
                measure_fn(fresh, active_reader, args.output, before_timing=before_timing)
            stage.frozen.verify_import(runner, args.bundle, args.work)
        finally:
            stage.frozen.stop(args.work)
        stage.frozen.verify_index(args.work, stage.index)
    require(memory_events(memory_group) == before, "Memory limit event during confirmation")
    (args.output / "eligible.json").write_text(json.dumps(eligible) + "\n")
    hashes = {
        name: file_sha(args.output / name)
        for name in ("quality.jsonl", "timing.jsonl", "eligible.json", *extra_raw_files)
    }
    receipt = {
        "job_id": os.environ["SLURM_JOB_ID"],
        "freeze_sha256": FREEZE_SHA,
        "fresh_queries_sha256": FRESH_SHA,
        "qualification_sha256": args.qualification_sha,
        "package_manifest_sha256": args.package_sha,
        "module_sha256": args.module_sha,
        "runtime_sha256": IMAGE,
        "resources": limits,
        "data_and_index_verified_before_and_after": True,
        "development_parity": parity,
        "raw_sha256": hashes,
        "analysis": analysis_fn(args.output, hashes),
    }
    with (args.output / "receipt.json").open("x") as f:
        json.dump(receipt, f, sort_keys=True, indent=2, allow_nan=False)


def cli_args():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("package", "bundle", "prepared", "work", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    for name in ("package-sha", "module-sha", "qualification-sha"):
        parser.add_argument(f"--{name}", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    run(cli_args())
