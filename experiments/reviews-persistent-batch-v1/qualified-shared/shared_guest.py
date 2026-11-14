"""Repeat confirmation on the same vectors with one shared membership lookup."""

import json
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter_ns

from analyze import FAMILIES, matches
from lookup import FILENAME, ROWS, publish
from rb_plan import pinned_lines, require
from run_guest import cli_args, reader, run
from shared_report import write_receipt

HERE = Path(__file__).resolve().parent
PRIOR_JOB = "22560903"
PRIOR_QUALITY_SHA = "4be2898ad8da3aa3a89c22f418cf66f5a860aa451d8d5a5c6d72b91e6ff65c1c"
ATTACH = "SELECT fannagent.confirm_attach('public.reviews','public.reviews_hnsw',%s)"


def prior_parity(rows):
    prior = pinned_lines(HERE / "prior-quality.jsonl", PRIOR_QUALITY_SHA)
    for row, saved in zip(rows, prior, strict=True):
        require(
            row["id"] == saved["id"] and matches(row["exact"], saved["exact"]),
            "Original exact reference differs",
        )
        for arm in FAMILIES:
            require(
                row[arm]["checkpoint"] == saved[arm]["checkpoint"]
                and matches(row[arm]["output"], saved[arm]["output"]),
                f"Shared lookup changed {arm} output for {row['id']}",
            )


@contextmanager
def session(runner, backend_type, args):
    from psycopg import connect
    from psycopg.conninfo import make_conninfo

    attach_times = []

    def activate(conn, arm, value):
        start = perf_counter_ns()
        response = conn.execute(ATTACH, (value,)).fetchone()
        elapsed = perf_counter_ns() - start
        require(response == (ROWS,), "Shared lookup attachment failed")
        attach_times.append({"family": arm, "attach_ns": elapsed})

    def open_reader(arm):
        return reader(backend_type, args, arm, activate=activate)

    def before_timing(rows):
        prior_parity(rows)
        attach_times.clear()
        print(f"All recall outputs and stop decisions matched job {PRIOR_JOB}", flush=True)

    path = args.work / FILENAME
    start = perf_counter_ns()
    dsn = make_conninfo(runner.job_connection(args.work, admin=True), dbname="torch_reviews")
    with connect(dsn, autocommit=True) as keeper, keeper.transaction():
        keeper.execute("SET LOCAL statement_timeout = '60s'")
        keeper.execute("SET LOCAL idle_in_transaction_session_timeout = 0")
        # Prevent writers and table/index rewrites across the build and all later snapshots.
        keeper.execute("LOCK TABLE public.reviews IN SHARE MODE NOWAIT")
        locked = perf_counter_ns()
        heap, index = keeper.execute(
            "SELECT 'public.reviews'::regclass::oid, 'public.reviews_hnsw'::regclass::oid"
        ).fetchone()
        rows = keeper.execute(
            "SELECT ctid::text,coalesce(total_votes >= 108,false) FROM ONLY public.reviews"
        ).fetchall()
        fetched = perf_counter_ns()
        metadata = publish(path, heap, index, rows)
        built = perf_counter_ns()
        del rows
        build = {
            **metadata,
            "open_and_lock_ns": locked - start,
            "fetch_ns": fetched - locked,
            "pack_publish_ns": built - fetched,
            "total_ns": built - start,
        }
        print(f"Built and published one shared lookup: {build}", flush=True)
        try:
            yield open_reader, before_timing
            with (args.output / "lookup.json").open("x") as f:
                json.dump(
                    {
                        "build": build,
                        "timed_attaches": attach_times,
                        "prior_job": PRIOR_JOB,
                        "prior_quality_sha256": PRIOR_QUALITY_SHA,
                    },
                    f,
                )
        finally:
            path.unlink()


if __name__ == "__main__":
    args = cli_args()
    run(args, extra_sql=(HERE / "shared.sql").read_text(), reader_session=session)
    write_receipt(args.output)
