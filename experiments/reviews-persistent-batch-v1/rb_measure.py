"""Batch acquisition and lifecycle guards. This module has no dispatch entry point."""

from __future__ import annotations

import json
import time
from collections import Counter
from contextlib import ExitStack, contextmanager
from pathlib import Path

from rb_evidence import Evidence
from rb_plan import (
    INSTALLATIONS,
    PHASE_SEARCHES,
    PHASE_SECONDS,
    PROFILES,
    READER_OPENS,
    SEARCHES,
    digest,
    file_sha,
    require,
)
from rb_stats import quality_reports

STREAMS = ("references", "proofs", "timings")
MAX_RAW_FILE_BYTES = 256 * 1024**2
READER_SETTINGS = 14
READER_SQL_LIMIT = 18
READER_SECTION = {"restore": {"reference"}, "quality": {"proof"}, "timing": {"timing"}}


class Meter:
    search_limits = SEARCHES
    install_limits = INSTALLATIONS
    reader_limits = READER_OPENS
    timing_reader_capacity = 1

    def __init__(self, clock=time.monotonic_ns):
        self.clock = clock
        self.started = self.phase_start = clock()
        self.phase = "restore"
        self.section = None
        self.searches = Counter()
        self.installs = Counter()
        self.opens = Counter()
        self.closes = Counter()
        self.reader_sql = 0
        self.live = None
        self.live_readers = 0

    def check_time(self):
        now = self.clock()
        require(
            now - self.phase_start < PHASE_SECONDS[self.phase] * 10**9,
            f"{self.phase} deadline exhausted",
        )
        internal = 6600 if self.phase == "final" else 6000
        require(now - self.started < internal * 10**9, "Internal deadline exhausted")

    def next_phase(self, phase):
        if phase != "final":
            self.check_time()
            require(
                (self.phase, phase) in (("restore", "quality"), ("quality", "timing")),
                "Invalid phase transition",
            )
        self.phase, self.phase_start, self.section = phase, self.clock(), None

    def select(self, section):
        require(section in PHASE_SEARCHES.get(self.phase, ()), "Search section is out of phase")
        self.section = section

    @property
    def calls(self):
        return sum(self.searches.values())

    def reserve(self, operation):
        self.check_time()
        require(
            self.live is not None and self.section in PHASE_SEARCHES.get(self.phase, ()),
            "Search outside an admitted reader or phase",
        )
        allowed = {
            "getter": ("policy", "policy_trace"),
            "exact": ("exact_reference",),
            "native": ("native",),
            "continue": ("policy_trace",),
            "proof": ("policy_trace", "native_bypass"),
            "timing": ("native", "policy", "native_bypass"),
        }
        require(operation in allowed[self.section], "Unexpected search operation")
        require(
            self.searches[self.section] < self.search_limits[self.section], "Search cap exhausted"
        )
        self.searches[self.section] += 1

    def installation(self):
        self.check_time()
        require(
            self.section in self.install_limits
            and self.installs[self.section] < self.install_limits[self.section],
            "Unexpected or over-budget installation",
        )
        self.installs[self.section] += 1

    def begin_reader(self, section):
        self.check_time()
        require(
            section in READER_SECTION.get(self.phase, ())
            and (
                self.live is None
                or (
                    self.live == section == "timing"
                    and self.live_readers < self.timing_reader_capacity
                )
            )
            and self.opens[section] < self.reader_limits[section],
            "Reader-open cap or phase",
        )
        self.opens[section] += 1
        self.live = section
        self.live_readers += 1

    def charge_reader_sql(self):
        # Charge the pinned startup sequence before attempting any of its dispatches.
        require(self.live is not None, "Startup outside reader reservation")
        self.reader_sql += READER_SQL_LIMIT

    def end_reader(self, closed):
        require(self.live is not None and self.live_readers > 0, "Reader close without admission")
        if closed:
            self.closes[self.live] += 1
        self.live_readers -= 1
        if self.live_readers == 0:
            self.live = None

    def receipt(self):
        return {
            "searches": dict(self.searches),
            "installations": dict(self.installs),
            "reader_opens": dict(self.opens),
            "reader_closes": dict(self.closes),
            "reader_startup_sql_reserved": self.reader_sql,
        }


def guarded_backend(base, meter):
    """Keep the pinned backend body, wrapping only admission and installation."""

    class BoundReader(base):
        _admitting = False
        _reader = None
        _identity = None

        def _connect(self):
            if not self._admitting:
                require(
                    self._reader is not None
                    and self.conn is self._reader
                    and not self._reader.closed,
                    "Reader changed inside a session",
                )
            return super()._connect()

        def _install_policy(self, policy):
            self._connect()
            meter.installation()
            return super()._install_policy(policy)

        def snapshot(self):
            require(
                self._snapshot is not None or meter.phase == "restore",
                "Unexpected snapshot rebuild",
            )
            return super().snapshot()

        def _verify_reader(self, expected):
            return self._reader.execute(
                "SELECT pg_backend_pid(), (SELECT backend_start::text FROM pg_stat_activity "
                "WHERE pid=pg_backend_pid()), (SELECT json_object_agg(name,setting) "
                "FROM pg_settings WHERE name=ANY(%s))",
                (list(expected),),
            ).fetchone()

        @contextmanager
        def reader(self, section):
            require(
                self.conn is None
                and self._reader is None
                and self._installed is None
                and not self._policies.entries
                and not self._policies.bytes,
                "Reader or policy state leaked into a fresh session",
            )
            meter.begin_reader(section)
            closed = False
            try:
                settings = self.state["source_manifest"]["settings"]
                require(
                    len(settings) == READER_SETTINGS
                    and settings["hnsw.ef_search"] == "640"
                    and self.config.query_timeout_seconds == 30,
                    "Reader settings changed",
                )
                expected = {**settings, "statement_timeout": "30000"}
                self._admitting = True
                meter.charge_reader_sql()
                self._reader = self._connect()
                self._admitting = False
                pid, started, actual = self._verify_reader(expected)
                require(
                    type(pid) is int
                    and pid > 0
                    and type(started) is str
                    and bool(started)
                    and actual == expected
                    and self._binding_conn is self._reader,
                    "Fresh reader identity or settings did not verify",
                )
                self._identity = [pid, started]
                meter.check_time()
                yield self
                self._connect()
            finally:
                try:
                    original = self._reader
                    self.close()
                    closed = self.conn is None and (original is None or original.closed)
                    require(
                        closed
                        and self._installed is None
                        and self._binding_conn is None
                        and not self._policies.entries,
                        "Reader cleanup or cache reset failed",
                    )
                finally:
                    self._admitting = False
                    self._reader = self._identity = None
                    meter.end_reader(closed)

    return BoundReader


def outputs(result):
    return [list(result.ids), list(result.distances)]


def actual_reference(case, backend, frozen, plan, evidence, meter):
    meter.select("exact")
    meter.reserve("exact_reference")
    truth = backend.exact_reference(case.query)
    require(
        truth.eligible_ids == evidence.eligible[case.stratum]
        and truth.eligible_count == len(truth.eligible_ids),
        "Exact eligible set changed",
    )
    meter.select("native")
    native = frozen.native(backend, meter, case.query)
    row = {
        "query_id": case.id,
        "truth": {
            "strict": sorted(truth.strictly_better),
            "ties": sorted(truth.boundary_ties),
            "k": truth.effective_k,
        },
        "native": outputs(native),
        "continues": {},
    }
    meter.select("continue")
    for profile in PROFILES:
        raw = frozen.policy.compose("profile-reference", "continue", profile)
        session = frozen.execution.session(backend, raw, plan.config)
        result = session.query(case.query, meter, trace=True)
        require(
            outputs(result) == row["native"] and result.metadata["stop_reason"] != "policy_stop",
            "Continue reference differs from native",
        )
        states = frozen.prefix(result, frozen.policy.names(plan.config, profile))
        row["continues"][profile] = {"length": len(states), "digest": digest(states)}
    require(digest(row) == digest(evidence.references[case.id]), "Fresh reference differs from pin")
    return row


def request_record(evidence, family, qid, result, installs):
    meta = result.metadata
    policy = evidence.policies.get(family)
    bypass = meta.get("native_bypass", False)
    require(type(bypass) is bool, "Invalid bypass acknowledgement")
    if policy is not None:
        require(
            meta.get("requested_composite_hash") == evidence.identities[family],
            "Composite acknowledgement changed",
        )
    active = policy is not None and not bypass
    require(
        meta.get("ordinary_default") is True
        if not active
        else meta.get("policy_applied") is True
        and not meta.get("policy_fallback")
        and not meta.get("policy_runtime_error"),
        "Unexpected execution acknowledgement",
    )
    return {
        "query_id": qid,
        "output": outputs(result),
        "bypass": bypass,
        "checkpoint_count": meta["checkpoint_count"] if active else None,
        "stop": active and meta.get("stop_reason") == "policy_stop",
        "installations": installs,
        "composite": meta.get("requested_composite_hash"),
        "ordinary_default": meta.get("ordinary_default") is True,
        "policy_applied": meta.get("policy_applied") is True,
    }


def collect_session(
    plan,
    frozen,
    evidence,
    backend,
    meter,
    session,
    arm,
    epoch=None,
    *,
    batch_size=None,
    diagnostic=None,
):
    """Record admission through close, with raw proof checks after the timed endpoint."""
    timed = epoch is not None
    family = arm.split("-")[0]
    clock = meter.clock
    batch_ends = []
    start = clock()
    with backend.reader("timing" if timed else "proof"):
        opened = clock()
        policy = evidence.policies.get(family)
        require(diagnostic is None or (timed and policy is None), "Invalid diagnostic arm")
        bound = frozen.execution.session(backend, policy, plan.config) if policy else None
        admitted = clock()
        identity = backend._identity
        seen_install = False
        results = []
        for case in session.cases:
            meter.check_time()
            before = meter.installs[meter.section]
            req_start = clock()
            if diagnostic is not None:
                result = diagnostic.query(case, backend, meter)
            elif bound is None:
                result = frozen.native(backend, meter, case.query)
            else:
                result = bound.query(case.query, meter, trace=not timed)
            req_end = clock()
            installations = meter.installs[meter.section] - before
            eligible = policy is not None and frozen.policy.route(case.query) in policy["eligible"]
            require(
                installations == int(eligible and not seen_install),
                "Policy installation missed first eligibility or repeated inside a session",
            )
            seen_install |= eligible
            backend._connect()
            results.append((case.id, result, installations, [req_start, req_end]))
            if batch_size is not None and len(results) % batch_size == 0:
                batch_ends.append(clock())
        closing = clock()
    closed = clock()
    meter.check_time()

    records = []
    for qid, result, installs, request_ns in results:
        if diagnostic is not None:
            records.append(diagnostic.record(qid, result, installs, request_ns))
            continue
        record = request_record(evidence, family, qid, result, installs)
        if timed:
            record["request_ns"] = request_ns
        else:
            record["prefix"] = (
                digest(frozen.prefix(result, frozen.policy.names(plan.config, policy["profile"])))
                if policy is not None and not record["bypass"]
                else None
            )
        records.append(record)
    row = {"session_id": session.id, "arm": arm, "reader": identity, "requests": records}
    if timed:
        row.update(epoch=epoch, boundary_ns=[start, opened, admitted, closing, closed])
    if batch_size is not None:
        row["batch_end_ns"] = batch_ends
    return row


def proof_outcome(evidence, family, record):
    qid = record["query_id"]
    expected = evidence.outcomes[family][qid]
    for field in ("bypass", "checkpoint_count", "stop", "prefix"):
        require(digest(record[field]) == digest(expected[field]), f"Actual route or trace: {qid}")
    if not expected["stop"]:
        require(
            digest(record["output"]) == digest(evidence.references[qid]["native"]),
            f"Bypass or continue changed native outputs: {qid}",
        )
    return {key: record[key] for key in expected}


def check_timed(evidence, proof, family, record):
    qid = record["query_id"]
    expected = (
        proof[family][qid]
        if family != "native"
        else {
            "output": evidence.references[qid]["native"],
            "bypass": False,
            "checkpoint_count": None,
            "stop": False,
        }
    )
    for field in ("output", "bypass", "checkpoint_count", "stop"):
        require(digest(record[field]) == digest(expected[field]), f"Timed proof parity: {qid}")


def write_json(path, value):
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def capture_local(plan, frozen, evidence, backend, meter, output):
    """Exercise the whole data path against a local fixture, with locked partial failures."""
    require(
        getattr(backend, "synthetic_only", False) is True,
        "Local capture requires a synthetic backend",
    )
    return _capture(plan, frozen, evidence, backend, meter, output, synthetic_only=True)


def _capture(
    plan, frozen, evidence, backend, meter, output, *, synthetic_only, after_snapshot=None
):
    require(set(evidence.policies) == {"seed", "candidate"}, "Exactly one candidate is required")
    output = Path(output)
    output.mkdir(exist_ok=False)
    disposition = "invalid_incomplete"
    try:
        with ExitStack() as stack:
            streams = {
                name: stack.enter_context((output / f"{name}.jsonl").open("x")) for name in STREAMS
            }

            def emit(stream, row):
                data = json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
                handle = streams[stream]
                require(handle.tell() + len(data.encode()) <= MAX_RAW_FILE_BYTES, "Raw cap")
                handle.write(data)
                handle.flush()

            refs = {}
            with backend.reader("reference"):
                backend.snapshot()
                if after_snapshot is not None:
                    after_snapshot()
                meter.next_phase("quality")
                meter.select("getter")
                getters = frozen.qualify(backend, meter, plan.qualification, plan.config)
                require(meter.searches["getter"] == SEARCHES["getter"], "Incomplete getters")
                write_json(
                    output / "getters.json", {"reader": backend._identity, "reports": getters}
                )
                for case in plan.cases.values():
                    row = actual_reference(case, backend, frozen, plan, evidence, meter)
                    refs[case.id] = row
                    emit("references", row)
            proof = {family: {} for family in evidence.policies}
            meter.select("proof")
            for family in ("seed", "candidate"):
                for session in plan.sessions:
                    row = collect_session(plan, frozen, evidence, backend, meter, session, family)
                    for record in row["requests"]:
                        proof[family][record["query_id"]] = proof_outcome(evidence, family, record)
                    emit("proofs", row)
            actual = Evidence(
                refs, evidence.eligible, evidence.policies, evidence.identities, proof
            )
            passed = quality_reports(plan, frozen, actual)["passes"]
            meter.check_time()
            if not passed:
                disposition = "closed_negative_quality"
                return
            meter.next_phase("timing")
            meter.select("timing")
            for epoch, session, arm in plan.timed():
                row = collect_session(plan, frozen, evidence, backend, meter, session, arm, epoch)
                for record in row["requests"]:
                    check_timed(evidence, proof, arm.split("-")[0], record)
                emit("timings", row)
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
