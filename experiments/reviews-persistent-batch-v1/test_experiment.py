"""Full-size local fixtures. All driver calls below are in-memory test doubles."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from itertools import count
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import rb_calibration
import rb_conditioned
import rb_interleave
import rb_native
import rb_oracle
import rb_persistent
import rb_switch
from rb_evidence import Evidence, load_frozen
from rb_measure import Meter, capture_local, guarded_backend
from rb_plan import ARMS, FILTERS, PROFILES, SEARCHES, digest, file_sha, load_plan
from rb_verify import verify_local


class Clock:
    def __init__(self):
        self.ns = 0

    def __call__(self):
        self.ns += 1000
        return self.ns

    def advance(self, ns):
        self.ns += ns


class FixtureConnection:
    def __init__(self, pid, settings, clock):
        self.pid = pid
        self.settings = settings
        self.clock = clock
        self.closed = False

    def execute(self, sql, params):
        if not sql.startswith("SELECT pg_backend_pid()") or self.closed:
            raise AssertionError("Only the fixture startup observation is supported")
        if set(params[0]) != set(self.settings):
            raise AssertionError("Wrong settings observation")
        self.clock.advance(100_000)
        return SimpleNamespace(fetchone=lambda: (self.pid, f"fixture-{self.pid}", self.settings))


class FixtureBackend:
    synthetic_only = True

    def __init__(self, frozen, plan, evidence, traces, clock, fault=None):
        from fannagent.api import FeatureValue, PolicyInput, validate_policy
        from fannagent.api.primitives.interpreter import evaluate_policy

        self.inputs = (FeatureValue, PolicyInput, evaluate_policy)
        self.validate = validate_policy
        self.frozen, self.plan, self.evidence, self.traces = frozen, plan, evidence, traces
        self.clock, self.fault = clock, fault
        self.conn = self._snapshot = self._installed = self._binding_conn = None
        self._policies = SimpleNamespace(entries={}, bytes=0)
        self._operation_lock = threading.RLock()
        self.config = SimpleNamespace(query_timeout_seconds=30)
        settings = {f"fixture-setting-{i}": "1" for i in range(13)}
        settings["hnsw.ef_search"] = "640"
        self.state = {"source_manifest": {"settings": settings}}
        self.pid = 0
        self.snapshot_loads = 0
        self.artifacts = {}
        self.slow_readers = {
            122 + index for index, (_, _, arm) in enumerate(plan.timed()) if arm == "native-B"
        }

    def _connect(self):
        if self.conn is None or self.conn.closed:
            self.close()
            self.pid += 1
            settings = {**self.state["source_manifest"]["settings"], "statement_timeout": "30000"}
            if self.fault == "settings":
                settings["hnsw.ef_search"] = "320"
            self.conn = self._binding_conn = FixtureConnection(self.pid, settings, self.clock)
            self.clock.advance(1_000_000)
        return self.conn

    def close(self):
        if self.conn is not None:
            self.conn.closed = True
            self.clock.advance(100_000)
        self.conn = self._installed = self._binding_conn = None
        self._policies.entries.clear()
        self._policies.bytes = 0

    def snapshot(self):
        if self._snapshot is None:
            self._snapshot = SimpleNamespace(query=deepcopy)
            self.snapshot_loads += 1
        return self._snapshot

    def exact_reference(self, query):
        if self.fault == "reconnect":
            self.conn.closed = True
        self._connect()
        from rb_plan import filter_of
        from rb_stats import exact_truth

        return exact_truth(
            self.frozen,
            self.evidence.references[query["id"]],
            self.evidence.eligible[filter_of(query)],
        )

    def validate_policy(self, raw):
        key = digest(raw)
        if key not in self.artifacts:
            self.artifacts[key] = self.validate(raw, self.frozen.profile)
        return self.artifacts[key]

    def _install_policy(self, policy):
        self._installed = policy.policy_hash
        self.clock.advance(200_000)

    def execute_probe(self, query, *, mode="native", policy=None, trace=False):
        self._connect()
        reference = self.evidence.references[query["id"]]
        ids, distances = reference["native"]
        if mode == "native":
            delay = 2_000_000 if self.fault == "aa" and self.pid in self.slow_readers else 0
            self.clock.advance(7_000_000 + delay)
            return SimpleNamespace(
                ids=ids,
                distances=distances,
                latency_ms=7,
                metadata={"ordinary_default": True},
                evidence=None,
            )
        artifact = self.validate_policy(policy) if isinstance(policy, dict) else policy
        if self._installed != artifact.policy_hash or (
            self.fault == "reinstall" and artifact.name == "fixture-candidate"
        ):
            self._install_policy(artifact)
        profile = next(
            name
            for name in PROFILES
            if list(self.frozen.policy.GROUPS[name]) == artifact.feature_groups
        )
        states = self.traces[profile]
        FeatureValue, PolicyInput, evaluate = self.inputs
        checkpoint = None
        for state in states:
            inp = PolicyInput(
                features={
                    name: FeatureValue(available=True, value=value)
                    for name, value in state["features"].items()
                }
            )
            floats = frozenset(
                n
                for n in state["features"]
                if self.frozen.profile.runtime_features[n].kind == "float"
            )
            if str(evaluate(artifact, inp, float_features=floats)) == "stop":
                checkpoint = state["checkpoint_index"]
                break
        if (
            checkpoint is not None
            and self.fault == "quality"
            and artifact.name == "fixture-candidate"
        ):
            ids = [*ids[:9], 11]  # Valid top-10, with one fewer tie-aware hit.
        selected = states if checkpoint is None else states[:checkpoint]
        trace_value = (
            {
                "truncated": False,
                "checkpoints": [
                    {
                        "index": state["checkpoint_index"],
                        "features": state["features"],
                    }
                    for state in selected
                ],
            }
            if trace
            else None
        )
        latency = 5 if artifact.name == "fixture-candidate" else 6
        self.clock.advance(latency * 1_000_000)
        return SimpleNamespace(
            ids=ids,
            distances=distances,
            latency_ms=latency,
            evidence=trace_value,
            metadata={
                "policy_applied": True,
                "checkpoint_count": len(selected),
                "stop_reason": "policy_stop" if checkpoint else "native",
            },
        )


def fixtures(plan, frozen):
    traces = {}
    for profile in PROFILES:
        traces[profile] = []
        for cp in range(1, 4):
            features = {}
            for name in frozen.policy.names(plan.config, profile):
                kind = frozen.profile.runtime_features[name].kind
                features[name] = {"bool": False, "int": 0, "float": 0.0}[kind]
            features["checkpoint_index"] = cp
            traces[profile].append({"checkpoint_index": cp, "features": features})
    policies, identities, expected = {}, {}, {}
    for family, cp in (("seed", 1), ("candidate", 2)):
        raw = frozen.policy.compose(
            f"fixture-{family}",
            {
                "if": {"op": "eq", "args": [{"feature": "checkpoint_index"}, {"int": cp}]},
                "then": "stop",
                "else": "continue",
            },
            "light19",
            ["unfiltered", "votes32"],
        )
        policies[family], identities[family] = frozen.policy.validate(raw, plan.config)
        expected[family] = {}
    refs = {}
    output = [list(range(10)), [float(i) / 10 for i in range(10)]]
    for case in plan.cases.values():
        refs[case.id] = {
            "query_id": case.id,
            "native": output,
            "truth": {"strict": list(range(9)), "ties": [9, 10], "k": 10},
            "continues": {p: {"length": len(v), "digest": digest(v)} for p, v in traces.items()},
        }
        for family, cp in (("seed", 1), ("candidate", 2)):
            active = case.stratum in policies[family]["eligible"]
            expected[family][case.id] = {
                "bypass": not active,
                "stop": active,
                "checkpoint_count": cp if active else None,
                "prefix": digest(traces["light19"][:cp]) if active else None,
                "output": output,
            }
    return Evidence(
        refs, {f: frozenset(range(12)) for f in FILTERS}, policies, identities, expected
    ), traces


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = load_plan()
        cls.frozen = load_frozen()
        cls.evidence, cls.traces = fixtures(cls.plan, cls.frozen)

    def test_interleaved_calibration_replays_full_schedule(self):
        stage = SimpleNamespace(evidence=self.evidence)
        rb_interleave.attach(stage)
        evidence = stage.evidence
        clock = Clock()
        meter = rb_interleave.Meter(clock)
        pids = count(100)
        live_counts = set()

        class Backend(FixtureBackend):
            def __init__(backend, _bundle, _work):
                super().__init__(self.frozen, self.plan, evidence, self.traces, clock)

            def _connect(backend):
                if backend.conn is None or backend.conn.closed:
                    backend.pid = next(pids) - 1
                return super()._connect()

            def execute_probe(backend, *args, **kwargs):
                live_counts.add(meter.live_readers)
                return super().execute_probe(*args, **kwargs)

        backend = rb_interleave.make_backend(None, Backend, meter, None, None)
        observer = SimpleNamespace(
            before=lambda _pid: None,
            after=lambda _pid, _before: {
                "server_command_us": 1000,
                "server_commands": 2,
                **{name: 0 for name in rb_interleave.COUNTERS},
            },
        )
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / "capture"
            with patch.object(type(backend), "diagnostics", return_value=observer):
                rb_interleave.capture(
                    self.plan,
                    self.frozen,
                    evidence,
                    backend,
                    meter,
                    output,
                    synthetic_only=True,
                    after_snapshot=lambda: None,
                )
            replay = rb_interleave.reconstruct(
                output,
                self.plan,
                self.frozen,
                evidence,
                synthetic_only=True,
            )
            self.assertEqual(live_counts, {2})
            self.assertIsNone(meter.live)
            self.assertEqual(meter.opens, meter.closes)
            self.assertEqual(backend.snapshot_loads, 1)
            self.assertEqual(replay["provisional_verdict"], "timing_controls_pass")
            self.assertFalse(replay["development_qualifier"])
            self.assertEqual(replay["accounting"]["searches"], {"timing": 7680})
            self.assertEqual(replay["accounting"]["installations"], {"timing": 64})
            for family in ("native", "seed"):
                subset = replay["instrumented_subset"][family]
                self.assertEqual(set(subset), {"reader-workload-02", "reader-workload-03"})
                for row in subset.values():
                    self.assertEqual(row["matched_requests"], 50)
                    self.assertEqual(row["counter_coverage"]["server_command_us"], 50)
            rows, _ = rb_calibration.completed_timing(output, evidence, True)
            rows[0]["chunks"][1]["span_ns"][0] = rows[0]["chunks"][0]["span_ns"][0]
            with self.assertRaisesRegex(ValueError, "Chunks overlap"):
                rb_interleave.verify_pair(
                    rows[0], next(rb_interleave.schedule(self.plan, evidence)), evidence, set(), 0
                )

    def test_interleaved_log_retains_only_numeric_durations_for_its_reader(self):
        raw = (
            b"reviews_aa 22 LOG:  duration: 2.003 ms\n"
            b"reviews_aa 23 LOG:  duration: 9.000 ms\n"
            b"reviews_aa 22 LOG:  duration: 0.132 ms\n"
            b"reviews_aa 22 LOG:  duration: 1.000 ms  statement: SELECT 1\n"
        )
        self.assertEqual(rb_interleave.duration_records(raw, 22), [2003, 132])

    def test_conditioned_calibration_binds_each_warmup_to_its_timed_reader(self):
        stage = SimpleNamespace(evidence=self.evidence)
        rb_conditioned.attach(stage)
        evidence = stage.evidence
        clock = Clock()
        meter = rb_conditioned.Meter(clock)
        pids = count(100)

        class Backend(FixtureBackend):
            def __init__(backend, _bundle, _work):
                super().__init__(self.frozen, self.plan, evidence, self.traces, clock)

            def _connect(backend):
                if backend.conn is None or backend.conn.closed:
                    backend.pid = next(pids) - 1
                return super()._connect()

            def execute_probe(backend, *args, **kwargs):
                self.assertEqual(meter.live_readers, 2)
                return super().execute_probe(*args, **kwargs)

        backend = rb_conditioned.make_backend(None, Backend, meter, None, None)
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / "capture"
            rb_conditioned.capture(
                self.plan,
                self.frozen,
                evidence,
                backend,
                meter,
                output,
                synthetic_only=True,
                after_snapshot=lambda: None,
            )
            replay = rb_conditioned.reconstruct(
                output, self.plan, self.frozen, evidence, synthetic_only=True
            )
            self.assertEqual(replay["provisional_verdict"], "timing_controls_pass")
            self.assertFalse(replay["development_qualifier"])
            self.assertEqual(replay["accounting"]["searches"], {"timing": 13200})
            self.assertEqual(replay["accounting"]["installations"], {"timing": 60})
            self.assertEqual(meter.opens, meter.closes)

            rows, _ = rb_calibration.completed_timing(output, evidence, True)
            row = rows[0]
            item = next(rb_conditioned.schedule(self.plan, evidence))
            session = item[2]
            _, measured, _, _ = rb_interleave.verify_pair(
                row, item, evidence, set(), 0, conditioned=True
            )
            blocks = row["chunks"][4:]
            self.assertEqual(len(blocks), 40)
            elapsed = dict.fromkeys(rb_interleave.LABELS, 0)
            for warmup, timed in zip(blocks[::2], blocks[1::2], strict=True):
                self.assertIs(warmup["conditioning"], True)
                self.assertNotIn("conditioning", timed)
                self.assertEqual(warmup["label"], timed["label"])
                self.assertEqual(warmup["chunk"], timed["chunk"])
                offset = timed["chunk"] * rb_interleave.CHUNK
                self.assertEqual(
                    [record["query_id"] for record in warmup["requests"]],
                    [case.id for case in session.cases[offset - rb_interleave.CHUNK : offset]],
                )
                start, end = timed["span_ns"]
                elapsed[timed["label"]] += end - start
            self.assertEqual(measured, elapsed)
            blocks[0]["label"] = "wrong"
            with self.assertRaisesRegex(ValueError, "Chunk or conditioning order"):
                rb_interleave.verify_pair(row, item, evidence, set(), 0, conditioned=True)

    def test_reader_switch_diagnostic_recovers_injected_first_request_cost(self):
        stage = SimpleNamespace(evidence=self.evidence)
        rb_switch.attach(stage)
        evidence = stage.evidence
        clock = Clock()
        meter = rb_switch.Meter(clock)
        pids = count(100)
        last_pid = None
        costs = {}

        class Backend(FixtureBackend):
            def __init__(backend, _bundle, _work):
                super().__init__(self.frozen, self.plan, evidence, self.traces, clock)

            def _connect(backend):
                if backend.conn is None or backend.conn.closed:
                    backend.pid = next(pids) - 1
                return super()._connect()

            def execute_probe(backend, *args, **kwargs):
                nonlocal last_pid
                self.assertEqual(meter.live_readers, 2)
                switched = backend.pid != last_pid
                last_pid = backend.pid
                costs[backend.pid] = 1_000_000 + 1_250_000 * switched
                return super().execute_probe(*args, **kwargs)

        class Observer:
            @contextmanager
            def monitor(self, _pid):
                yield "errno_13"

            def before(self, _pid):
                return None

            def after(self, pid, _before):
                return {
                    **dict.fromkeys(rb_interleave.COUNTERS),
                    "cpu_ns": costs[pid],
                    "server_command_us": costs[pid] // 1000,
                    "server_commands": 2,
                    "last_cpu_before": pid % 2,
                    "last_cpu_after": pid % 2,
                    "perf": None,
                }

        backend = rb_switch.make_backend(None, Backend, meter, None, None)
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / "capture"
            with patch.object(type(backend), "diagnostics", return_value=Observer()):
                rb_switch.capture(
                    self.plan,
                    self.frozen,
                    evidence,
                    backend,
                    meter,
                    output,
                    synthetic_only=True,
                    after_snapshot=lambda: None,
                )
            replay = rb_switch.reconstruct(
                output,
                self.plan,
                self.frozen,
                evidence,
                synthetic_only=True,
            )
            self.assertEqual(replay["accounting"]["searches"], {"timing": 4880})
            self.assertEqual(replay["accounting"]["installations"], {"timing": 4})
            self.assertEqual(meter.opens, meter.closes)
            self.assertIsNone(meter.live)
            self.assertFalse(replay["development_qualifier"])
            for family in ("native", "seed"):
                subset = replay["workloads"][family]
                self.assertEqual(set(subset), {"reader-workload-02", "reader-workload-03"})
                for row in subset.values():
                    contrasts = row["matched_contrasts_by_request_position"]
                    first = contrasts["1"]["cpu_ns"]
                    self.assertEqual(first["complete_matched_chunks"], 10)
                    self.assertEqual(
                        first["effects"],
                        {
                            "switch_cost_first": 1_250_000,
                            "switch_cost_second": 1_250_000,
                            "repeat_cost_stay": 0,
                            "repeat_cost_switch": 0,
                            "interaction": 0,
                        },
                    )
                    self.assertEqual(contrasts["2"]["cpu_ns"]["effects"]["switch_cost_first"], 0)
                    self.assertNotIn("cycles", contrasts["1"])
            rows, _ = rb_calibration.completed_timing(output, evidence, True)
            rows[0]["chunks"][2]["step"][0] = "invalid"
            with self.assertRaisesRegex(ValueError, "Switch condition order"):
                rb_switch.verify_pair(
                    rows[0], next(rb_switch.schedule(self.plan, evidence)), evidence, set(), 0
                )

    def test_oracle_distance_budget_respects_checkpoint_overshoot(self):
        states = [
            {
                "checkpoint_index": i,
                "features": {
                    "checkpoint_target": target,
                    "layer0_distance_evaluations": actual,
                    "checkpoint_overshoot": actual - target,
                },
            }
            for i, (target, actual) in enumerate(((64, 131), (192, 196)), 1)
        ]
        self.assertEqual(
            rb_oracle.checkpoint_budget(states, 2),
            {
                "budget": 192,
                "checkpoint_count": 2,
                "last_checkpoint_distances": 196,
                "max_final_distances": 196,
            },
        )
        self.assertEqual(rb_oracle.checkpoint_budget(states, None)["max_final_distances"], 255)
        states[1]["features"]["checkpoint_target"] = 128
        with self.assertRaisesRegex(ValueError, "checkpoint recurrence"):
            rb_oracle.checkpoint_budget(states, 2)

    def test_oracle_retained_transport_binds_budget_without_policy(self):
        from fannagent_pgvector.native import sequential

        calls = []
        query = {"id": "fixture", "k": 10, "filter": {"op": "gte", "value": 108}}

        def execute(statement, params):
            calls.append(("query", statement, params))
            return SimpleNamespace(fetchall=lambda: [(101, 0.25)])

        def begin(conn, statement, params):
            calls.append(("begin", conn, statement, params))
            return params[3]

        def complete(conn, nonce, count):
            calls.append(("complete", conn, nonce, count))
            return json.dumps({"request_nonce": nonce, "target_index_oid": 42})

        conn = SimpleNamespace(execute=execute)
        backend = SimpleNamespace(
            _operation_lock=threading.RLock(),
            _connect=lambda: conn,
            snapshot=lambda: SimpleNamespace(query=lambda value: value, source_to_id={"101": 7}),
            _statement=lambda value: ("frozen-nearest-sql", (value["id"],)),
            config=SimpleNamespace(copy=SimpleNamespace(trace_max_bytes=4096)),
            state={"source_manifest": {"index": {"oid": 42}}},
            _batch_ready=lambda actual: actual is conn,
            _combined_query_batch=False,
        )
        with (
            patch.object(sequential, "begin_execution_batch", begin),
            patch.object(sequential, "complete_execution_batch", complete),
        ):
            result = rb_oracle.fixed_budget_query(backend, query, 192, "f" * 64)
        self.assertEqual([event[0] for event in calls], ["begin", "query", "complete"])
        params = calls[0][3]
        self.assertEqual(params[:3], ("fixed_budget", None, 192))
        self.assertEqual(params[4:8], (10, 1, "off", 4096))
        self.assertEqual(calls[2][2:], (params[3], 1))
        self.assertEqual((result.ids, result.distances), ([7], [0.25]))

    def test_oracle_comparison_has_one_seed_install_and_no_oracle_installs(self):
        base = self.evidence
        oracle_rows = {}
        for qid, case in self.plan.cases.items():
            stop = case.stratum != "votes108"
            oracle_rows[qid] = {
                "stop": stop,
                "bypass": False,
                "checkpoint_count": 2,
                "budget": 128 if stop else rb_oracle.CONTINUE,
                "last_checkpoint_distances": 130,
                "max_final_distances": 130 if stop else 191,
                "output": base.references[qid]["native"],
            }
        evidence = Evidence(
            base.references,
            base.eligible,
            {"seed": base.policies["seed"]},
            {"seed": base.identities["seed"], "oracle": digest(oracle_rows)},
            {"seed": base.outcomes["seed"], "oracle": oracle_rows},
        )
        clock = Clock()
        meter = rb_oracle.Meter(clock)
        driver = SimpleNamespace(connect=lambda open_reader: open_reader())
        runner = SimpleNamespace(psycopg=driver)

        class Reader(FixtureBackend):
            def __init__(reader, _bundle, _work):
                super().__init__(self.frozen, self.plan, evidence, self.traces, clock)

            def _connect(reader):
                if reader.conn is None or reader.conn.closed:
                    conn = runner.psycopg.connect(super()._connect)
                    reader._bind(conn, reader.state["source_manifest"])
                    return conn
                return super()._connect()

            def _bind(reader, _conn, _source):
                clock.advance(200_000)

            def oracle_fixture(reader, _query, want):
                reader._connect()
                clock.advance(3_000_000)
                return SimpleNamespace(
                    ids=want["output"][0],
                    distances=want["output"][1],
                    metadata={
                        "protocol": "same_execution_v4",
                        "effective_mode": "fixed_budget",
                        "executed_path": "postgresql_pgvector_hnsw",
                        "stop_scope": "hnsw_scan",
                        "stop_reason": "fixed_budget_stop" if want["stop"] else "native_limit",
                        "returned_count": 10,
                        "returned_count_source": "client_reported",
                        "policy_hash": None,
                        "policy_fallback": False,
                        "policy_runtime_error": None,
                        "trace_descriptor": None,
                        "policy_applied": False,
                        "checkpoint_count": 2,
                        "work_counters": {
                            "layer0_distance_evaluations": 130,
                            "policy_evaluation_count": 0,
                        },
                    },
                )

        backend = rb_oracle.make_backend(runner, Reader, meter, None, None)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "oracle"
            rb_oracle.capture(
                self.plan,
                self.frozen,
                evidence,
                backend,
                meter,
                output,
                synthetic_only=True,
                after_snapshot=lambda: None,
            )
            report = rb_oracle.reconstruct(
                output, self.plan, self.frozen, evidence, synthetic_only=True
            )
            self.assertTrue(report["aa_pass"])
            self.assertFalse(report["development_qualifier"])
            self.assertEqual(report["provisional_verdict"], "material_oracle_headroom")
            self.assertEqual(report["accounting"]["installations"], {"timing": 60})
            self.assertEqual(report["accounting"]["searches"], {"timing": 10800})
            self.assertEqual(report["accounting"]["reader_opens"], {"reference": 1, "timing": 180})
            rows, _ = rb_calibration.completed_timing(output, evidence, True)
            record = next(row["requests"][0] for row in rows if row["arm"] == "oracle-A")
            record["oracle"]["layer0_distances"] = 200
            with self.assertRaisesRegex(ValueError, "Oracle stop, budget"):
                rb_oracle.check_oracle_request(evidence, record)

    def test_guest_checks_memory_after_snapshot_before_qualifying_getters(self):
        for max_events in (0, 1):
            with self.subTest(max_events=max_events), tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                work, output = root / "work", root / "guest"
                (work / "socket").mkdir(parents=True)
                snapshots = []

                class Backend(FixtureBackend):
                    def __init__(backend, _bundle, _work):
                        super().__init__(
                            self.frozen, self.plan, self.evidence, self.traces, Clock()
                        )

                    def snapshot(backend):
                        result = super().snapshot()
                        snapshots.append(result)
                        return result

                before = {"max": 0, "oom": 0, "oom_kill": 0}
                after = {**before, "max": max_events}

                def observe_memory(_group):
                    return after if snapshots else before

                def qualify(*_args):
                    raise RuntimeError("Reached getter qualification fixture")

                index = object()
                stage = SimpleNamespace(
                    manifest_sha="fixture",
                    source=root,
                    plan=self.plan,
                    evidence=self.evidence,
                    index=index,
                    frozen=SimpleNamespace(
                        profile=self.frozen.profile,
                        execution=SimpleNamespace(load_backend=lambda _: (None, Backend)),
                        restore=lambda *_: index,
                        stop=lambda _: None,
                        qualify=qualify,
                    ),
                )
                with (
                    patch.object(rb_native, "resource_limits", return_value=({}, root)),
                    patch.object(rb_native, "memory_events", side_effect=observe_memory),
                    patch.object(rb_native, "check_native_inputs", return_value={}),
                ):
                    code = rb_native.run_guest(
                        stage, {"job_id": "12345"}, root, root, work, output, time.monotonic_ns()
                    )
                self.assertEqual(code, 1)
                self.assertEqual(len(snapshots), 1)
                self.assertEqual(
                    json.loads((output / "startup-memory.json").read_bytes()),
                    {"memory_events_after_snapshot": after, "search_attempts": 0},
                )
                failure = json.loads((output / "guest-failure.json").read_bytes())
                self.assertEqual(
                    failure["message"],
                    "Job recorded a limit or OOM event before the first search"
                    if max_events
                    else "Reached getter qualification fixture",
                )

    def capture(self, directory, fault=None):
        clock = Clock()
        meter = Meter(clock)
        backend = guarded_backend(FixtureBackend, meter)(
            self.frozen, self.plan, self.evidence, self.traces, clock, fault
        )
        capture_local(self.plan, self.frozen, self.evidence, backend, meter, directory)
        self.assertEqual(backend.snapshot_loads, 1)
        self.assertIsNone(backend.conn)
        return verify_local(directory, self.plan, self.frozen, self.evidence)

    def test_frozen_schedule_balances_positions_and_predecessors(self):
        positions, predecessors = Counter(), Counter()
        order = {}
        for epoch, session, arm in self.plan.timed():
            key = (epoch, session.id)
            position = len(order.setdefault(key, []))
            positions[epoch, position, arm] += 1
            if position:
                predecessors[epoch, order[key][-1], arm] += 1
            order[key].append(arm)
        self.assertEqual(len(positions), 72)
        self.assertEqual(len(predecessors), 60)
        self.assertEqual(set(positions.values()), {10})
        self.assertEqual(set(predecessors.values()), {10})
        for session in self.plan.sessions:
            self.assertEqual(order[0, session.id], order[1, session.id][::-1])
            self.assertEqual(set(order[0, session.id]), set(ARMS))

    def test_full_capture_and_reconstruction_reject_relocked_changes(self):
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch) / "run"
            report = self.capture(folder)
            self.assertEqual(report["fixture_verdict"], "would_pass")
            self.assertFalse(report["development_qualifier"])
            self.assertEqual(report["accounting"]["searches"], SEARCHES)
            self.assertEqual(
                report["accounting"]["reader_opens"], {"reference": 1, "proof": 120, "timing": 720}
            )
            self.assertEqual(report["accounting"]["installations"]["timing"], 480)
            rows = (folder / "timings.jsonl").read_text().splitlines()
            row = json.loads(rows[0])
            row["requests"][0]["output"][1][0] = 2.0
            rows[0] = json.dumps(row)
            (folder / "timings.jsonl").write_text("\n".join(rows) + "\n")
            with self.assertRaisesRegex(ValueError, "digest changed"):
                verify_local(folder, self.plan, self.frozen, self.evidence)
            lock = json.loads((folder / "LOCK.json").read_bytes())
            lock["files_sha256"]["timings.jsonl"] = file_sha(folder / "timings.jsonl")
            (folder / "LOCK.json").write_text(json.dumps(lock))
            with self.assertRaisesRegex(ValueError, "Timed proof parity"):
                verify_local(folder, self.plan, self.frozen, self.evidence)

    def test_quality_failure_stops_before_timing(self):
        with tempfile.TemporaryDirectory() as scratch:
            folder = Path(scratch) / "run"
            report = self.capture(folder, "quality")
            self.assertEqual(report["fixture_verdict"], "closed_negative_quality")
            self.assertEqual(sum(report["accounting"]["searches"].values()), 5121)
            self.assertIsNone(report["timing"])
            self.assertEqual((folder / "timings.jsonl").stat().st_size, 0)

    def test_failed_aa_overrides_favorable_candidate_latency(self):
        with tempfile.TemporaryDirectory() as scratch:
            report = self.capture(Path(scratch) / "run", "aa")
            self.assertEqual(report["fixture_verdict"], "measurement_inconclusive")
            self.assertTrue(report["timing"]["latency_pass"])
            self.assertFalse(report["timing"]["aa_per_request"]["native"]["passes"])
            self.assertFalse(report["development_qualifier"])

    def test_calibration_replays_full_aa_only_schedule_and_checks_setup_spans(self):
        for delayed in (False, True):
            with self.subTest(delayed=delayed), tempfile.TemporaryDirectory() as scratch:
                clock = Clock()
                meter = rb_calibration.Meter(clock)
                slow_readers = {
                    index + 2
                    for index, (_, _, arm) in enumerate(self.plan.timed())
                    if arm == "native-B"
                }
                driver = SimpleNamespace(connect=lambda open_reader: open_reader())
                runner = SimpleNamespace(psycopg=driver)

                class Reader(FixtureBackend):
                    def __init__(reader, _bundle, _work):
                        super().__init__(self.frozen, self.plan, self.evidence, self.traces, clock)

                    def _connect(reader):
                        if reader.conn is None or reader.conn.closed:
                            conn = runner.psycopg.connect(super()._connect)
                            reader._bind(conn, reader.state["source_manifest"])
                            return conn
                        return super()._connect()

                    def _bind(reader, _conn, _source):
                        clock.advance(200_000)
                        if delayed and reader.pid in slow_readers:
                            clock.advance(2_000_000)

                backend = rb_calibration.make_backend(runner, Reader, meter, None, None)
                output = Path(scratch) / "calibration"
                calls_at_snapshot = []
                rb_calibration.capture(
                    self.plan,
                    self.frozen,
                    self.evidence,
                    backend,
                    meter,
                    output,
                    synthetic_only=True,
                    after_snapshot=lambda: calls_at_snapshot.append(meter.calls),
                )
                report = rb_calibration.reconstruct(
                    output, self.plan, self.frozen, self.evidence, synthetic_only=True
                )
                self.assertEqual(calls_at_snapshot, [0])
                self.assertIs(runner.psycopg, driver)
                self.assertEqual(backend.snapshot_loads, 1)
                self.assertEqual(report["accounting"]["searches"], {"timing": 7200})
                self.assertEqual(report["aa_pass"], not delayed)
                self.assertFalse(report["development_qualifier"])
                self.assertNotIn("session_contrasts", report)
                self.assertGreater(
                    report["reader_setup_ms_quantiles_50_95_100"]["native"]["connect"][0], 1
                )
                if not delayed:
                    continue
                timings = output / "timings.jsonl"
                rows = timings.read_text().splitlines()
                row = json.loads(rows[0])
                row["reader_setup_ns"]["verify_settings"][1] = row["boundary_ns"][1] + 1
                rows[0] = json.dumps(row)
                timings.write_text("\n".join(rows) + "\n")
                lock = output / "LOCK.json"
                hashes = json.loads(lock.read_bytes())
                hashes["files_sha256"]["timings.jsonl"] = file_sha(timings)
                lock.write_text(json.dumps(hashes))
                with self.assertRaisesRegex(ValueError, "escaped the session boundary"):
                    rb_calibration.reconstruct(
                        output, self.plan, self.frozen, self.evidence, synthetic_only=True
                    )

    def test_persistent_reuses_readers_and_gates_the_steady_window(self):
        slots = tuple(rb_persistent.schedule(self.plan, self.evidence))
        order = {}
        for epoch, session, arm in slots:
            order.setdefault((epoch, session.id), []).append(arm)
        positions = Counter(
            (index, arm) for arms in order.values() for index, arm in enumerate(arms)
        )
        predecessors = Counter(pair for arms in order.values() for pair in zip(arms, arms[1:]))
        self.assertEqual((len(positions), set(positions.values())), (36, {5}))
        self.assertEqual((len(predecessors), set(predecessors.values())), (30, {5}))
        for delay_requests in (False, True):
            with self.subTest(delay_requests=delay_requests), tempfile.TemporaryDirectory() as tmp:
                clock = Clock()
                meter = rb_persistent.Meter(clock)
                slow = {index + 2 for index, (_, _, arm) in enumerate(slots) if arm == "native-B"}
                driver = SimpleNamespace(connect=lambda open_reader: open_reader())
                runner = SimpleNamespace(psycopg=driver)

                class Reader(FixtureBackend):
                    def __init__(reader, _bundle, _work):
                        super().__init__(self.frozen, self.plan, self.evidence, self.traces, clock)

                    def _connect(reader):
                        if reader.conn is None or reader.conn.closed:
                            conn = runner.psycopg.connect(super()._connect)
                            reader._bind(conn, reader.state["source_manifest"])
                            return conn
                        return super()._connect()

                    def _bind(reader, _conn, _source):
                        clock.advance(200_000_000 if reader.pid in slow else 200_000)

                    def execute_probe(reader, *args, **kwargs):
                        result = super().execute_probe(*args, **kwargs)
                        if delay_requests and reader.pid in slow:
                            clock.advance(2_000_000)
                        return result

                backend = rb_persistent.make_backend(runner, Reader, meter, None, None)
                output = Path(tmp) / "persistent"
                before_searches = []
                rb_persistent.capture(
                    self.plan,
                    self.frozen,
                    self.evidence,
                    backend,
                    meter,
                    output,
                    synthetic_only=True,
                    after_snapshot=lambda: before_searches.append(meter.calls),
                )
                report = rb_persistent.reconstruct(
                    output, self.plan, self.frozen, self.evidence, synthetic_only=True
                )
                self.assertEqual(before_searches, [0])
                self.assertEqual(backend.snapshot_loads, 1)
                self.assertIsNone(backend.conn)
                self.assertIs(runner.psycopg, driver)
                self.assertEqual(meter.opens, meter.closes)
                self.assertEqual(
                    report["accounting"]["reader_opens"], {"reference": 1, "timing": 180}
                )
                self.assertEqual(report["accounting"]["searches"], {"timing": 10800})
                self.assertEqual(report["accounting"]["installations"], {"timing": 120})
                self.assertEqual(report["aa_pass"], not delay_requests)
                self.assertFalse(report["development_qualifier"])
                if delay_requests:
                    self.assertEqual(report["provisional_verdict"], "measurement_inconclusive")
                    self.assertEqual(report["steady_contrasts_per_request"], {})
                else:
                    self.assertEqual(report["provisional_verdict"], "would_pass")
                    self.assertTrue(
                        report["steady_contrasts_per_request"]["candidate_vs_seed"]["passes"]
                    )

    def test_local_entry_refuses_a_nonsynthetic_backend_before_output(self):
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / "run"
            with self.assertRaisesRegex(ValueError, "requires a synthetic backend"):
                capture_local(
                    self.plan, self.frozen, self.evidence, object(), Meter(Clock()), output
                )
            self.assertFalse(output.exists())

    def test_failure_keeps_partial_return_and_never_reconnects(self):
        cases = {
            "settings": "settings did not verify",
            "reconnect": "Reader changed",
            "reinstall": "installation missed first eligibility or repeated",
        }
        for fault, message in cases.items():
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as scratch:
                clock = Clock()
                meter = Meter(clock)
                backend = guarded_backend(FixtureBackend, meter)(
                    self.frozen, self.plan, self.evidence, self.traces, clock, fault
                )
                folder = Path(scratch) / "run"
                with self.assertRaisesRegex(ValueError, message):
                    capture_local(self.plan, self.frozen, self.evidence, backend, meter, folder)
                report = verify_local(folder, self.plan, self.frozen, self.evidence)
                self.assertEqual(report["disposition"], "invalid_incomplete")
                self.assertFalse(report["development_qualifier"])
                self.assertIsNone(backend.conn)
                self.assertIsNone(meter.live)
                self.assertEqual(meter.opens, meter.closes)
                if fault == "reconnect":
                    self.assertEqual(backend.pid, 1)

    def test_attempt_and_time_caps_fail_before_another_call(self):
        clock = Clock()
        meter = Meter(clock)
        meter.begin_reader("reference")
        meter.next_phase("quality")
        meter.select("getter")
        for _ in range(SEARCHES["getter"]):
            meter.reserve("policy")
        with self.assertRaisesRegex(ValueError, "Search cap"):
            meter.reserve("policy")
        with self.assertRaisesRegex(ValueError, "Reader-open cap"):
            meter.begin_reader("proof")
        clock.advance(2700 * 10**9)
        with self.assertRaisesRegex(ValueError, "quality deadline"):
            meter.next_phase("timing")


if __name__ == "__main__":
    unittest.main()
