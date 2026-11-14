"""Time fresh connections under both warm-up conditions with mirrored labels."""

import json
from functools import partial
from pathlib import Path
from time import perf_counter_ns

from run_guest import cli_args, execute, measure, run
from shared_guest import session
from warmup_plan import schedule
from warmup_report import reconstruct

HERE = Path(__file__).resolve().parent


def timed_query(conn, query):
    start = perf_counter_ns()
    output = execute(conn, query)
    end = perf_counter_ns()
    return {"id": query["id"], "request_ns": [start, end], "output": output}


def record_timing(queries, reader_for, directory):
    with (directory / "timing.jsonl").open("x") as stream:
        for batch, count, mirror, slot, arm, warmup, scored in schedule():
            family = arm.rsplit("-", 1)[0]
            start = perf_counter_ns()
            with reader_for(family) as conn:
                ready = perf_counter_ns()
                warming = [timed_query(conn, queries[i]) for i in warmup]
                warmed = perf_counter_ns() if count else ready
                output = [timed_query(conn, queries[i]) for i in scored]
            closed = perf_counter_ns()
            stream.write(
                json.dumps(
                    {
                        "batch": batch,
                        "warmup_count": count,
                        "mirror": mirror,
                        "slot": slot,
                        "arm": arm,
                        "session_ns": [start, ready, warmed, closed],
                        "warmup": warming,
                        "queries": output,
                    },
                    allow_nan=False,
                )
                + "\n"
            )


if __name__ == "__main__":
    run(
        cli_args(),
        extra_sql=(HERE / "shared.sql").read_text(),
        reader_session=session,
        measure_fn=partial(measure, timing_recorder=record_timing),
        analysis_fn=reconstruct,
        extra_raw_files=("lookup.json",),
    )
