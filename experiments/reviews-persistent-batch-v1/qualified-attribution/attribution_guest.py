"""Capture native request wall time, PostgreSQL timing, and backend scheduling counters."""

import json
import os
import time
from contextlib import contextmanager
from functools import partial
from pathlib import Path

from analyze import SIZE
from attribution_plan import schedule
from attribution_report import PRIOR_QUALITY_SHA, reconstruct
from rb_plan import pinned, require
from rb_request_timing import LOG_PREFIX, MAX_LOG_BYTES, server_timings
from run_guest import ANN, cli_args, params, qualify, reader, run

HERE = Path(__file__).resolve().parent
SQL = " ".join(ANN.split())
PROC = Path("/proc")
SCHEDSTATS = PROC / "sys/kernel/sched_schedstats"


def configure_logging(admin):
    require(
        admin.execute(
            "SELECT current_setting('log_destination') = 'stderr' "
            "AND current_setting('logging_collector') = 'off'"
        ).fetchone()
        == (True,),
        "Unexpected private PostgreSQL log destination",
    )
    admin.execute(f"ALTER SYSTEM SET log_line_prefix = '{LOG_PREFIX}'")
    require(admin.execute("SELECT pg_reload_conf()").fetchone() == (True,), "Log reload failed")
    for _ in range(40):
        if admin.execute("SHOW log_line_prefix").fetchone() == (LOG_PREFIX,):
            break
        time.sleep(0.05)
    else:
        raise ValueError("Diagnostic log prefix did not take effect")
    for setting, value in (
        ("log_parameter_max_length", "0"),
        ("log_parameter_max_length_on_error", "0"),
        ("log_min_duration_sample", "-1"),
        ("log_min_duration_statement", "-1"),
        ("log_duration", "off"),
        ("log_statement", "none"),
    ):
        admin.execute(
            f"ALTER ROLE torch_reader IN DATABASE torch_reviews SET {setting} = '{value}'"
        )
    admin.execute("GRANT SET ON PARAMETER log_min_duration_statement TO torch_reader")


@contextmanager
def session(runner, backend_type, args):
    from psycopg import connect
    from psycopg.conninfo import make_conninfo

    dsn = make_conninfo(runner.job_connection(args.work, admin=True), dbname="torch_reviews")
    with connect(dsn, autocommit=True) as admin:
        configure_logging(admin)

    def open_reader(arm):
        return reader(backend_type, args, arm)

    yield open_reader, None


def read_schedstat(pid):
    try:
        fields = [int(v) for v in (PROC / str(pid) / "schedstat").read_text().split()]
    except (OSError, ValueError):
        return None
    require(len(fields) == 3 and min(fields) >= 0, "Unexpected backend schedstat format")
    return fields


def cpu_timer(pid):
    try:
        clock = time.clock_getcpuclockid(pid)
        time.clock_gettime_ns(clock)
    except (AttributeError, OSError):
        schedstat = read_schedstat(pid)
        if schedstat and schedstat[0]:
            return "schedstat", lambda: read_schedstat(pid)[0]
        ticks_per_second = os.sysconf("SC_CLK_TCK")

        def proc_cpu():
            stat = (PROC / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
            return (int(stat[11]) + int(stat[12])) * 10**9 // ticks_per_second

        return "proc_stat_ticks", proc_cpu
    return "process_cpu_clock", lambda: time.clock_gettime_ns(clock)


def snapshot(pid, cpu):
    start = time.perf_counter_ns()
    cpu_ns = cpu()
    schedstat = read_schedstat(pid)
    return {"sample_ns": [start, time.perf_counter_ns()], "cpu_ns": cpu_ns, "schedstat": schedstat}


def timed_request(conn, query, pid, cpu):
    before = snapshot(pid, cpu)
    start = time.perf_counter_ns()
    args = params(query)
    sent = time.perf_counter_ns()
    cursor = conn.execute(SQL, (*args, SIZE), prepare=False)
    received = time.perf_counter_ns()
    rows = cursor.fetchall()
    decoded = time.perf_counter_ns()
    output = [[i, float(d)] for i, d in rows]
    end = time.perf_counter_ns()
    after = snapshot(pid, cpu)
    return {
        "id": query["id"],
        "output": output,
        "request_ns": [start, end],
        "execute_ns": [sent, received],
        "fetchall_ns": [received, decoded],
        "backend": [before, after],
    }


def measure(queries, reader_for, directory, *, before_timing=None, work):
    require(before_timing is None, "Unexpected diagnostic session callback")
    prior = pinned(HERE / "prior-quality.jsonl", PRIOR_QUALITY_SHA)
    require(
        [q["id"] for q in queries] == [json.loads(line)["id"] for line in prior.splitlines()],
        "Diagnostic query cohort or order differs",
    )
    (directory / "quality.jsonl").write_bytes(prior)
    readers = {}
    rows = []
    for epoch, batch, arm, order in schedule():
        enabled = arm != "native-C"
        start = time.perf_counter_ns()
        with reader_for("native") as conn:
            value = "0" if enabled else "-1"
            require(
                conn.execute(
                    "SELECT set_config('log_min_duration_statement', %s, false)", (value,)
                ).fetchone()
                == (value,),
                "Reader statement logging mode differs",
            )
            pid = conn.info.backend_pid
            require(pid > 0 and pid not in readers, "Duplicate backend PID")
            readers[pid] = enabled
            cpu_source, cpu = cpu_timer(pid)
            ready = time.perf_counter_ns()
            requests = [timed_request(conn, queries[i], pid, cpu) for i in order]
        closed = time.perf_counter_ns()
        rows.append(
            {
                "epoch": epoch,
                "batch": batch,
                "arm": arm,
                "pid": pid,
                "cpu_source": cpu_source,
                "session_ns": [start, ready, closed],
                "requests": requests,
            }
        )

    with (work / "server.log").open("rb") as stream:
        log = stream.read(MAX_LOG_BYTES + 1)
    require(len(log) <= MAX_LOG_BYTES, "Private diagnostic log exceeded its cap")
    phases = server_timings(log, readers, requests_per_reader=SIZE)
    with (directory / "timing.jsonl").open("x") as stream:
        for row in rows:
            server = phases.get(row["pid"], [None] * SIZE)
            for request, durations in zip(row["requests"], server, strict=True):
                request["server_us"] = durations
            stream.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")
    try:
        setting = int(SCHEDSTATS.read_text())
    except (OSError, ValueError):
        setting = None
    (directory / "counters.json").write_text(
        json.dumps({"kernel_sched_schedstats": setting}) + "\n"
    )


if __name__ == "__main__":
    args = cli_args()
    run(
        args,
        reader_session=session,
        qualify_fn=partial(qualify, families=("native",)),
        measure_fn=partial(measure, work=args.work),
        analysis_fn=reconstruct,
        extra_raw_files=("counters.json",),
    )
