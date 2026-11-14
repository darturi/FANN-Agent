"""Attribute native steady-state request time with paired logging controls."""

import json
import re
import time
from collections import defaultdict
from contextlib import contextmanager
from itertools import permutations
from pathlib import Path
from statistics import fmean
from types import SimpleNamespace

import numpy as np
import rb_calibration
import rb_persistent
from rb_measure import MAX_RAW_FILE_BYTES, check_timed, collect_session, write_json
from rb_plan import SESSION_LENGTH, file_sha, require
from rb_stats import interval
from rb_verify import check_identity, check_requests

VERDICTS = ("request_attribution_complete",)
LOG_PREFIX = "reviews_diag %p %l "
MAX_LOG_BYTES = 16 * 1024**2
NATIVE_PREFIX = b'SELECT "id", "embedding" <=> $1::vector AS distance FROM "public"."reviews" '
LOG_LINE = re.compile(
    rb"reviews_diag ([0-9]+) ([0-9]+) LOG: +duration: ([0-9]+)\.([0-9]{3}) ms +"
    rb"(parse|bind|execute) ([^:]+): (.+)"
)
CLIENT_SPANS = ("execute_ns", "fetchall_ns")
SERVER_PHASES = ("parse", "bind", "execute")
ARMS = ("native-A", "native-B", "native-C")


class Meter(rb_calibration.Meter):
    reader_limits = {"reference": 1, "timing": rb_persistent.WORKLOADS * len(ARMS)}
    search_limits = {"timing": reader_limits["timing"] * rb_persistent.REQUESTS}
    install_limits = {}

    def reserve(self, operation):
        require(operation == "native", "Request timing permits only ordinary native searches")
        super().reserve(operation)


def schedule(plan, evidence):
    orders = tuple(permutations(ARMS))
    for epoch, session, arm in rb_persistent.schedule(plan, evidence):
        if epoch != 0:
            break
        if arm == "native-A":
            for label in orders[session.block % len(orders)]:
                yield epoch, session, label


def make_backend(runner, base, meter, bundle, work):
    driver = runner.psycopg
    active = None

    class TimingCursor(driver.Cursor):
        def _observe(self, label, call, *args, **kwargs):
            if active is None:
                return call(*args, **kwargs)
            require(label not in active, "Native request repeated a client operation")
            start = meter.clock()
            result = call(*args, **kwargs)
            active[label] = [start, meter.clock()]
            return result

        def execute(self, *args, **kwargs):
            return self._observe("execute_ns", super().execute, *args, **kwargs)

        def fetchall(self):
            return self._observe("fetchall_ns", super().fetchall)

    class DiagnosticReader(base):
        request_spans = None

        def configure_server_log(self):
            with driver.connect(runner.job_connection(work, admin=True), autocommit=True) as conn:
                require(
                    conn.execute(
                        "SELECT current_setting('log_destination') = 'stderr' AND "
                        "current_setting('logging_collector') = 'off'"
                    ).fetchone()[0],
                    "Expected the private server's stderr log",
                )
                conn.execute("ALTER SYSTEM SET log_line_prefix = 'reviews_diag %p %l '")
                require(conn.execute("SELECT pg_reload_conf()").fetchone()[0], "Log reload failed")
                for _ in range(40):
                    if conn.execute(
                        "SELECT current_setting('log_line_prefix') = %s", (LOG_PREFIX,)
                    ).fetchone()[0]:
                        break
                    time.sleep(0.05)
                else:
                    raise ValueError("Diagnostic log prefix was not applied")
                for setting, value in (
                    ("log_parameter_max_length", "0"),
                    ("log_parameter_max_length_on_error", "0"),
                    ("log_min_duration_sample", "-1"),
                    ("log_duration", "off"),
                    ("log_statement", "none"),
                ):
                    conn.execute(
                        "ALTER ROLE torch_reader IN DATABASE torch_reviews "
                        f"SET {setting} = '{value}'"
                    )

        def set_logging(self, enabled):
            require(self.conn is None, "Logging mode must be set before reader admission")
            with driver.connect(runner.job_connection(work, admin=True), autocommit=True) as conn:
                conn.execute(
                    "ALTER ROLE torch_reader IN DATABASE torch_reviews "
                    f"SET log_min_duration_statement = {0 if enabled else -1}"
                )

        @contextmanager
        def trace_client(self):
            require(self.request_spans is None, "Client tracing is already active")
            original = runner.psycopg

            def connect(*args, **kwargs):
                return original.connect(*args, **kwargs, cursor_factory=TimingCursor)

            runner.psycopg = SimpleNamespace(connect=connect)
            self.request_spans = []
            try:
                yield self.request_spans
            finally:
                self.request_spans = None
                runner.psycopg = original

        def execute_probe(self, query, *, mode="native", policy=None, trace=False, audit=False):
            nonlocal active
            require(
                mode == "native"
                and policy is None
                and not trace
                and not audit
                and active is None
                and self.request_spans is not None,
                "Expected one ordinary native probe under client timing",
            )
            active = {}
            try:
                result = super().execute_probe(query, mode=mode)
                require(set(active) == set(CLIENT_SPANS), "Incomplete client request timing")
                self.request_spans.append(active)
                return result
            finally:
                active = None

        def server_log(self):
            with (Path(work) / "server.log").open("rb") as log:
                data = log.read(MAX_LOG_BYTES + 1)
            require(len(data) <= MAX_LOG_BYTES, "Private diagnostic log exceeded its cap")
            return data

    return rb_calibration.make_backend(runner, DiagnosticReader, meter, bundle, work)


def server_timings(log, readers, *, requests_per_reader=rb_persistent.REQUESTS):
    """Read numeric timings only, with one extended-query sequence per native request."""
    events = defaultdict(list)
    pending = {}
    last_line = {}
    for line in log.splitlines():
        match = LOG_LINE.fullmatch(line)
        if match is None or not match[7].startswith(NATIVE_PREFIX):
            continue
        pid, seq, whole, fraction = map(int, match.groups()[:4])
        require(pid in readers and readers[pid], "Unexpected native server timing record")
        phase, name, sql = match.groups()[4:]
        require(seq > last_line.get(pid, 0), "Server log order changed")
        last_line[pid] = seq
        previous, values = pending.setdefault(pid, ((name, sql), {}))
        require(previous == (name, sql) and phase not in values, "Server query sequence changed")
        require(
            (phase == b"parse" and not values)
            or (phase == b"bind" and set(values) <= {b"parse"})
            or (phase == b"execute" and b"bind" in values),
            "Server protocol timing is out of order",
        )
        values[phase] = whole * 1000 + fraction
        if phase == b"execute":
            events[pid].append([values.get(key.encode()) for key in SERVER_PHASES])
            del pending[pid]
    require(not pending, "Incomplete server duration sequence")
    require(
        set(events) == {pid for pid, enabled in readers.items() if enabled}
        and all(len(rows) == requests_per_reader for rows in events.values()),
        "Expected one server timing sequence per logged request",
    )
    return events


def capture(plan, frozen, evidence, backend, meter, output, *, synthetic_only, after_snapshot):
    require(isinstance(meter, Meter), "Request timing requires its own meter")
    require(
        getattr(backend, "synthetic_only", False) is synthetic_only,
        "Request timing backend does not match the execution mode",
    )
    slots = tuple(schedule(plan, evidence))
    output = Path(output)
    output.mkdir(exist_ok=False)
    disposition = "invalid_incomplete"
    try:
        with (output / "timings.jsonl").open("x") as stream:
            with backend.reader("reference"):
                backend.snapshot()
                after_snapshot()
            backend.configure_server_log()
            meter.next_phase("quality")
            meter.next_phase("timing")
            meter.select("timing")
            rows = []
            readers = {}
            for epoch, session, arm in slots:
                enabled = arm != "native-C"
                backend.set_logging(enabled)
                with backend.trace_client() as client, backend.trace_reader_setup() as setup:
                    row = collect_session(
                        plan,
                        frozen,
                        evidence,
                        backend,
                        meter,
                        session,
                        arm,
                        epoch,
                        batch_size=SESSION_LENGTH,
                    )
                pid = row["reader"][0]
                require(pid not in readers, "Reader PID repeated in diagnostic")
                readers[pid] = enabled
                row["reader_setup_ns"] = setup
                for record, spans in zip(row["requests"], client, strict=True):
                    check_timed(evidence, evidence.outcomes, "native", record)
                    record.update(spans)
                rows.append(row)
            timings = server_timings(backend.server_log(), readers)
            for row in rows:
                values = timings.get(row["reader"][0], [None] * rb_persistent.REQUESTS)
                for record, server in zip(row["requests"], values, strict=True):
                    record["server_us"] = server
                line = json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
                require(stream.tell() + len(line.encode()) <= MAX_RAW_FILE_BYTES, "Raw cap")
                stream.write(line)
            meter.check_time()
            disposition = "complete"
    except BaseException as error:
        write_json(output / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        meter.next_phase("final")
        write_json(
            output / "status.json",
            {
                "synthetic_only": synthetic_only,
                "disposition": disposition,
                "candidate": evidence.identities,
                "accounting": meter.receipt(),
            },
        )
        hashes = {path.name: file_sha(path) for path in sorted(output.iterdir())}
        write_json(output / "LOCK.json", {"files_sha256": hashes})


def request_components(record, logged):
    start, end = record["request_ns"]
    sent, received = record["execute_ns"]
    fetch, decoded = record["fetchall_ns"]
    require(
        all(type(value) is int for value in (sent, received, fetch, decoded))
        and start <= sent <= received <= fetch <= decoded <= end,
        "Client timing escaped the request",
    )
    execute, decode = received - sent, decoded - fetch
    components = {
        "request": (end - start) / 1e6,
        "client_execute": execute / 1e6,
        "fetchall_decode": decode / 1e6,
        "outside_execute_and_fetch": (end - start - execute - decode) / 1e6,
    }
    server = record["server_us"]
    if logged:
        require(type(server) is list and len(server) == 3, "Missing server request timings")
        parse, bind, execute_server = server
        require(
            (parse is None or type(parse) is int and parse >= 0)
            and all(type(value) is int and value >= 0 for value in (bind, execute_server)),
            "Invalid PostgreSQL phase timings",
        )
        total = (parse or 0) + bind + execute_server
        require(total * 1000 <= execute + 2000, "Server durations exceeded the client execute span")
        components.update(
            server_parse=(parse or 0) / 1000,
            server_bind=bind / 1000,
            server_execute=execute_server / 1000,
            server_total=total / 1000,
            client_execute_residual=(execute - total * 1000) / 1e6,
        )
    else:
        require(server is None, "Unlogged reader returned server timing")
    return components


def reconstruct(directory, plan, _frozen, evidence, *, synthetic_only):
    rows, accounting = rb_calibration.completed_timing(directory, evidence, synthetic_only)
    seen = set()
    pids = set()
    previous_close = 0
    steady = {}
    logged_requests = []
    for row, (epoch, session, arm) in zip(rows, schedule(plan, evidence), strict=True):
        require(
            (row["epoch"], row["session_id"], row["arm"]) == (epoch, session.id, arm),
            "Request timing schedule changed",
        )
        rb_persistent.measurements(row, previous_close)
        previous_close = row["boundary_ns"][-1]
        check_identity(row, seen)
        pid = row["reader"][0]
        require(pid not in pids, "Reader PID repeated in diagnostic")
        pids.add(pid)
        require(check_requests(session, "native", evidence, row) == 0, "Unexpected installation")
        logged = arm != "native-C"
        components = []
        for record in row["requests"]:
            check_timed(evidence, evidence.outcomes, "native", record)
            components.append(request_components(record, logged))
        warm = components[SESSION_LENGTH:]
        steady[session.id, arm] = {name: fmean(row[name] for row in warm) for name in warm[0]}
        if logged:
            logged_requests.extend(warm)
    rb_calibration.check_accounting(accounting, Meter, 0)
    paired = []
    logging_gaps = []
    for workload in sorted({workload for workload, _ in steady}):
        a, b, unlogged = (steady[workload, arm] for arm in ARMS)
        paired.append({"workload": workload, "gap_ms_per_request": {k: b[k] - a[k] for k in a}})
        logging_gaps.append(fmean((a["request"], b["request"])) - unlogged["request"])
    return {
        "request_attribution": True,
        "synthetic_only": synthetic_only,
        "development_qualifier": False,
        "provisional_verdict": VERDICTS[0],
        "accounting": accounting,
        "logged_steady_request_count": len(logged_requests),
        "logged_ms_quantiles_50_95_100": {
            name: np.quantile([row[name] for row in logged_requests], [0.50, 0.95, 1]).tolist()
            for name in logged_requests[0]
        },
        "logged_b_minus_a_by_workload": paired,
        "logged_minus_unlogged_ms_per_request": {
            "mean": fmean(logging_gaps),
            "ci95": interval(logging_gaps),
            "by_workload": logging_gaps,
        },
    }
