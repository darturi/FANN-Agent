"""Held native and seed A/A calibration with two open readers and serial chunks."""

import json
import os
import re
import time
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from statistics import fmean

import rb_calibration
import rb_persistent
from rb_measure import MAX_RAW_FILE_BYTES, check_timed, guarded_backend, request_record, write_json
from rb_plan import SESSION_LENGTH, digest, file_sha, require
from rb_stats import aa_equivalent, quality
from rb_verify import check_identity, check_requests

FAMILIES = ("native", "seed")
LABELS = ("A", "B")
CHUNK = 5
PROBE_BLOCKS = (1, 2)  # Workloads 02 and 03 had the largest saved reader gaps.
MAIN_PAIRS = rb_persistent.WORKLOADS * rb_persistent.EPOCHS * len(FAMILIES)
PROBE_PAIRS = len(PROBE_BLOCKS) * len(FAMILIES)
PAIR_COUNT = MAIN_PAIRS + PROBE_PAIRS
VERDICTS = ("timing_controls_pass", "measurement_inconclusive", "closed_negative_quality")
LOG_PREFIX = "reviews_aa %p "
DURATION = re.compile(rb"reviews_aa ([0-9]+) LOG: +duration: ([0-9]+)\.([0-9]{3}) ms")
COUNTERS = ("cpu_ns", "runqueue_ns", "voluntary_switches", "involuntary_switches", "read_bytes")


class Meter(rb_calibration.Meter):
    timing_reader_capacity = 2
    reader_limits = {"reference": 1, "timing": 2 * PAIR_COUNT}
    search_limits = {"timing": reader_limits["timing"] * rb_persistent.REQUESTS}
    install_limits = {"timing": PAIR_COUNT}


def attach(stage):
    stage.evidence = replace(
        stage.evidence,
        policies={"seed": stage.evidence.policies["seed"]},
        identities={"seed": stage.evidence.identities["seed"]},
        outcomes={"seed": stage.evidence.outcomes["seed"]},
    )
    stage.study_identity = digest(
        {
            "schema": "reviews-persistent-batch.interleaved-aa.v1",
            "seed": stage.evidence.identities["seed"],
            "chunk_requests": CHUNK,
            "instrumented_workload_blocks": PROBE_BLOCKS,
            "pairs": PAIR_COUNT,
        }
    )


def schedule(plan, evidence):
    probe_sessions = []
    for epoch, session, arm in rb_persistent.schedule(plan, evidence):
        if arm != "native-A":
            continue
        if epoch == 0 and session.block in PROBE_BLOCKS:
            probe_sessions.append(session)
        for family in family_order(epoch, session.block):
            yield False, epoch, session, family
    for session in probe_sessions:
        for family in family_order(1, session.block):
            yield True, 0, session, family


def family_order(epoch, block):
    return FAMILIES if (epoch + block) % 2 == 0 else FAMILIES[::-1]


def label_order(instrumented, epoch, block, family, chunk):
    parity = instrumented + epoch + block + FAMILIES.index(family) + chunk
    return LABELS if parity % 2 == 0 else LABELS[::-1]


def process_counters(pid, schedstats):
    """Sample the PostgreSQL backend in the guest PID namespace."""
    base = Path("/proc") / str(pid)
    values = dict.fromkeys(COUNTERS)
    try:
        cpu, queue, _ = map(int, (base / "schedstat").read_text().split())
        values["cpu_ns"] = cpu
        if schedstats:
            values["runqueue_ns"] = queue
    except OSError:
        # Tick-level CPU accounting is coarser, but still measures the backend only.
        try:
            fields = (base / "stat").read_text().rsplit(")", 1)[1].split()
            ticks = int(fields[11]) + int(fields[12])
            values["cpu_ns"] = ticks * 1_000_000_000 // os.sysconf("SC_CLK_TCK")
        except OSError:
            pass
    try:
        fields = dict(line.split(":", 1) for line in (base / "status").read_text().splitlines())
        values["voluntary_switches"] = int(fields["voluntary_ctxt_switches"])
        values["involuntary_switches"] = int(fields["nonvoluntary_ctxt_switches"])
    except (OSError, KeyError):
        pass
    try:
        fields = dict(line.split(":", 1) for line in (base / "io").read_text().splitlines())
        values["read_bytes"] = int(fields["read_bytes"])
    except (OSError, KeyError):
        pass
    return values


def duration_records(raw, pid):
    values = []
    for line in raw.splitlines():
        match = DURATION.fullmatch(line)
        if match and int(match[1]) == pid:
            values.append(int(match[2]) * 1000 + int(match[3]))
    return values


class Diagnostics:
    """Return numeric server durations only. Log collection runs after the primary phase."""

    def __init__(self, runner, work):
        self.log_path = Path(work) / "server.log"
        schedstats = Path("/proc/sys/kernel/sched_schedstats")
        try:
            self.schedstats = schedstats.read_text().strip() == "1"
        except OSError:
            self.schedstats = False
        with runner.psycopg.connect(
            runner.job_connection(work, admin=True), autocommit=True
        ) as conn:
            require(
                conn.execute(
                    "SELECT current_setting('log_destination') = 'stderr' AND "
                    "current_setting('logging_collector') = 'off'"
                ).fetchone()[0],
                "Expected the private server stderr log",
            )
            conn.execute("ALTER SYSTEM SET log_line_prefix = 'reviews_aa %p '")
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
                ("log_statement", "none"),
                ("log_min_duration_statement", "-1"),
                ("log_min_duration_sample", "-1"),
                ("log_parameter_max_length", "0"),
                ("log_parameter_max_length_on_error", "0"),
                ("log_duration", "on"),
            ):
                conn.execute(
                    f"ALTER ROLE torch_reader IN DATABASE torch_reviews SET {setting} = '{value}'"
                )

    def before(self, pid):
        return self.log_path.stat().st_size, process_counters(pid, self.schedstats)

    def after(self, pid, before):
        offset, counters = before
        end = process_counters(pid, self.schedstats)
        with self.log_path.open("rb") as log:
            log.seek(offset)
            raw = log.read(65537)
        require(len(raw) <= 65536, "Diagnostic request log span exceeds cap")
        values = duration_records(raw, pid)
        deltas = {
            key: end[key] - counters[key]
            if end[key] is not None and counters[key] is not None
            else None
            for key in COUNTERS
        }
        return {
            "server_command_us": sum(values) if values else None,
            "server_commands": len(values),
            **deltas,
        }


def make_backend(runner, base, meter, bundle, work, *, diagnostics_class=Diagnostics):
    class Reader(guarded_backend(base, meter)):
        def partner(self):
            require(self._snapshot is not None, "Expected a shared frozen snapshot")
            other = Reader(bundle, work)
            other._snapshot = self._snapshot
            other.state["source_manifest"]["settings"]["hnsw.ef_search"] = "640"
            return other

        def diagnostics(self):
            return diagnostics_class(runner, work)

    return Reader(bundle, work)


def collect_chunk(frozen, evidence, reader, bound, meter, family, cases, diagnostics):
    clock = meter.clock
    pid = reader._identity[0]
    results = []
    chunk_start = clock()
    for case in cases:
        meter.check_time()
        installs = meter.installs[meter.section]
        before = diagnostics.before(pid) if diagnostics is not None else None
        begin = clock()
        result = (
            bound.query(case.query, meter, trace=False)
            if bound is not None
            else frozen.native(reader, meter, case.query)
        )
        end = clock()
        diagnostic = diagnostics.after(pid, before) if diagnostics is not None else None
        reader._connect()
        results.append(
            (case.id, result, meter.installs[meter.section] - installs, [begin, end], diagnostic)
        )
    chunk_end = clock()
    records = []
    for qid, result, installs, span, diagnostic in results:
        record = request_record(evidence, family, qid, result, installs)
        record.update(request_ns=span, diagnostics=diagnostic)
        check_timed(evidence, evidence.outcomes, family, record)
        records.append(record)
    return {"span_ns": [chunk_start, chunk_end], "requests": records}


def pair_steps(item, *, conditioned):
    instrumented, epoch, session, family = item
    require(len(session.cases) == rb_persistent.REQUESTS, "Reader workload size changed")
    for chunk, offset in enumerate(range(0, len(session.cases), CHUNK)):
        for label in label_order(instrumented, epoch, session.block, family, chunk):
            if conditioned and offset >= SESSION_LENGTH:
                yield chunk, label, offset - CHUNK, True
            yield chunk, label, offset, False


def collect_pair(plan, frozen, evidence, readers, meter, item, diagnostics, *, conditioned=False):
    instrumented, epoch, session, family = item
    clock = meter.clock
    policy = evidence.policies.get(family)
    started = clock()
    chunks = []
    initial_order = label_order(instrumented, epoch, session.block, family, 0)
    with ExitStack() as stack:
        for label in initial_order:
            stack.enter_context(readers[label].reader("timing"))
        require(meter.live_readers == 2, "Both readers must be admitted")
        identities = {label: readers[label]._identity for label in LABELS}
        require(identities["A"] != identities["B"], "Reader connections are not distinct")
        bound = (
            {
                label: frozen.execution.session(readers[label], policy, plan.config)
                for label in LABELS
            }
            if policy
            else {}
        )
        admitted = clock()
        for chunk, label, offset, conditioning in pair_steps(item, conditioned=conditioned):
            probe = diagnostics if not conditioning and offset >= SESSION_LENGTH else None
            block = collect_chunk(
                frozen,
                evidence,
                readers[label],
                bound.get(label),
                meter,
                family,
                session.cases[offset : offset + CHUNK],
                probe,
            )
            if conditioning:
                block["conditioning"] = True
            chunks.append({"label": label, "chunk": chunk, **block})
        closing = clock()
    return {
        "instrumented": instrumented,
        "epoch": epoch,
        "session_id": session.id,
        "family": family,
        "identities": identities,
        "boundary_ns": [started, admitted, closing, clock()],
        "chunks": chunks,
    }


def capture(
    plan,
    frozen,
    evidence,
    backend,
    meter,
    output,
    *,
    synthetic_only,
    after_snapshot,
    run_schedule=schedule,
    collector=collect_pair,
):
    require(
        isinstance(meter, Meter) and getattr(backend, "synthetic_only", False) is synthetic_only,
        "Calibration backend does not match the execution mode",
    )
    output = Path(output)
    output.mkdir(exist_ok=False)
    disposition = "invalid_incomplete"
    try:
        with (output / "timings.jsonl").open("x") as stream:
            with backend.reader("reference"):
                backend.snapshot()
                after_snapshot()
            readers = {"A": backend, "B": backend.partner()}
            meter.next_phase("quality")
            meter.next_phase("timing")
            meter.select("timing")
            diagnostics = None
            for item in run_schedule(plan, evidence):
                if item[0] and diagnostics is None:
                    diagnostics = backend.diagnostics()
                row = collector(plan, frozen, evidence, readers, meter, item, diagnostics)
                line = json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
                require(stream.tell() + len(line) <= MAX_RAW_FILE_BYTES, "Raw cap")
                stream.write(line)
                stream.flush()
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
        write_json(
            output / "LOCK.json",
            {
                "files_sha256": {path.name: file_sha(path) for path in sorted(output.iterdir())},
            },
        )


def verify_diagnostic(record, active):
    observed = record["diagnostics"]
    if not active:
        require(observed is None, "Unexpected instrumentation in primary timing")
        return
    require(
        set(observed) == {"server_command_us", "server_commands", *COUNTERS},
        "Diagnostic fields changed",
    )
    commands = observed["server_commands"]
    duration = observed["server_command_us"]
    require(type(commands) is int and 0 <= commands <= 64, "Invalid server command count")
    require(
        (commands == 0 and duration is None)
        or (
            commands > 0
            and type(duration) is int
            and 0 <= duration <= (record["request_ns"][1] - record["request_ns"][0]) / 1000 + 1000
        ),
        "Invalid server duration",
    )
    for key in COUNTERS:
        value = observed[key]
        require(value is None or (type(value) is int and value >= 0), "Invalid process delta")


def verify_pair(row, item, evidence, seen, previous, *, conditioned=False):
    instrumented, epoch, session, family = item
    require(
        (row["instrumented"], row["epoch"], row["session_id"], row["family"])
        == (instrumented, epoch, session.id, family),
        "Calibration pair schedule changed",
    )
    start, admitted, closing, closed = row["boundary_ns"]
    require(previous <= start <= admitted < closing <= closed, "Pair boundaries changed")
    require(set(row["identities"]) == set(LABELS), "Pair reader identities changed")
    records = {label: [] for label in LABELS}
    cases = {label: [] for label in LABELS}
    steady = dict.fromkeys(LABELS, 0)
    for label in LABELS:
        check_identity({"reader": row["identities"][label]}, seen)
    previous_chunk = admitted
    expected = pair_steps(item, conditioned=conditioned)
    for entry, (chunk, label, offset, conditioning) in zip(row["chunks"], expected, strict=True):
        require(
            (entry["chunk"], entry["label"]) == (chunk, label)
            and entry.get("conditioning", False) is conditioning,
            "Chunk or conditioning order changed",
        )
        begin, end = entry["span_ns"]
        require(previous_chunk <= begin < end <= closing, "Chunks overlap or escape pair")
        if not conditioning and offset >= SESSION_LENGTH:
            steady[label] += end - begin
        for case, record in zip(
            session.cases[offset : offset + CHUNK], entry["requests"], strict=True
        ):
            request_begin, request_end = record["request_ns"]
            require(
                begin <= request_begin < request_end <= end and record["query_id"] == case.id,
                "Request order or timing changed",
            )
            check_timed(evidence, evidence.outcomes, family, record)
            verify_diagnostic(
                record, instrumented and not conditioning and offset >= SESSION_LENGTH
            )
            cases[label].append(case)
            records[label].append(record)
            begin = request_end
        previous_chunk = end
    installs = sum(
        check_requests(
            replace(session, cases=tuple(cases[label])),
            family,
            evidence,
            {"requests": records[label]},
        )
        for label in LABELS
    )
    require(
        all(r["installations"] == 0 for rows in records.values() for r in rows[SESSION_LENGTH:]),
        "Policy install entered conditioning or steady timing",
    )
    return closed, steady, installs, records


def diagnostic_summary(pairs):
    summary = {}
    for family in FAMILIES:
        summary[family] = {}
        for session_id, records in pairs[family]:
            values = defaultdict(list)
            pairs_count = 0
            for a, b in zip(
                records["A"][SESSION_LENGTH:], records["B"][SESSION_LENGTH:], strict=True
            ):
                pairs_count += 1
                values["request_wall_ns"].append(
                    (b["request_ns"][1] - b["request_ns"][0])
                    - (a["request_ns"][1] - a["request_ns"][0])
                )
                for key in ("server_command_us", *COUNTERS):
                    left, right = a["diagnostics"][key], b["diagnostics"][key]
                    if left is not None and right is not None:
                        values[key].append(right - left)
            summary[family][session_id] = {
                "matched_requests": pairs_count,
                "counter_coverage": {
                    key: len(values.get(key, ())) for key in ("server_command_us", *COUNTERS)
                },
                "mean_b_minus_a": {key: fmean(data) for key, data in sorted(values.items())},
            }
    return summary


def reconstruct(
    directory,
    plan,
    frozen,
    evidence,
    *,
    synthetic_only,
    run_schedule=schedule,
    meter_type=Meter,
    conditioned=False,
):
    rows, accounting = rb_calibration.completed_timing(directory, evidence, synthetic_only)
    cells, probes, seen = {}, defaultdict(list), set()
    installs = previous = 0
    for row, item in zip(rows, run_schedule(plan, evidence), strict=True):
        previous, steady, pair_installs, records = verify_pair(
            row, item, evidence, seen, previous, conditioned=conditioned
        )
        installs += pair_installs
        instrumented, epoch, session, family = item
        if instrumented:
            probes[family].append((session.id, records))
        else:
            for label in LABELS:
                cells[epoch, session.block, f"{family}-{label}"] = {
                    "steady_ms": steady[label] / 1e6
                }
    rb_calibration.check_accounting(accounting, meter_type, installs)
    controls = {}
    for family in FAMILIES:
        cell = rb_persistent.paired(cells, (f"{family}-B",), (f"{family}-A",))
        cell["passes"] = aa_equivalent(cell)
        controls[family] = cell
    aa_pass = all(cell["passes"] for cell in controls.values())
    recall = quality(plan, frozen, evidence, "seed")
    verdict = "measurement_inconclusive"
    if not recall["passes"]:
        verdict = "closed_negative_quality"
    elif aa_pass:
        verdict = "timing_controls_pass"
    return {
        "provisional_verdict": verdict,
        "development_qualifier": False,
        "interleaved_calibration": True,
        "synthetic_only": synthetic_only,
        "aa_pass": aa_pass,
        "aa_per_steady_request": controls,
        "quality": {"seed": recall},
        "accounting": accounting,
        "instrumented_subset": diagnostic_summary(probes),
    }
