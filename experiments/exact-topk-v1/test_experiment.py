"""Synthetic correctness checks only; no database/native/provider/Torch runs."""

import copy
import io
import json
import tarfile
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import experiment
import xt_common as common
import xt_control as control
import xt_interface as interface
import xt_measure as measure
import xt_metadata as metadata
import xt_report as report
from xt_control import dispatch, reserve
from xt_job import container_command
from xt_stats import equivalent

common.bootstrap(experiment.SOURCE)
from fannagent_pgvector.backend import NativeBackend  # noqa: E402

from fannagent.evaluation import score  # noqa: E402
from fannagent.snapshot import Snapshot  # noqa: E402

SOURCE_SETTINGS = common.read(experiment.SOURCE / "origin-settings.json")
SOURCE_METADATA = common.read(experiment.SOURCE / "origin-source.json")["metadata"]


class Clock:
    value = 1000000000

    def now(self):
        self.value += 1000
        return self.value

    def advance(self, ms):
        self.value += int(ms * 1e6)


CLOCK = Clock()


class SqlFailure(Exception):
    sqlstate = "22012"


class FakeConnection:
    def __init__(self):
        self.closed = False
        self.autocommit = True
        self.info = SimpleNamespace(transaction_status=0)
        self.values = {}
        self.rows = []
        self.prepare_threshold = 5
        self.prepared_max = 100
        self.connection = None
        self.native_calls = 0
        self.native_sql = ""

    @contextmanager
    def transaction(self):
        old = self.values.copy()
        try:
            yield
        finally:
            self.values = old

    def execute(self, statement, params=None, prepare=None):
        text = str(statement)
        if "jsonb_build_object" in text:
            self.rows = [(fake_catalog(),)]
        elif "pg_prepared_statements" in text:
            self.rows = (
                [
                    (
                        "mock_native",
                        self.native_sql,
                        "{vector,smallint,vector,smallint}",
                        0,
                        self.native_calls,
                    )
                ]
                if self.native_calls >= 6
                else []
            )
        elif "set_config" in text:
            self.values[params[0]] = params[1]
            self.rows = [(params[1],)]
        elif "FROM pg_settings" in text:
            self.rows = [
                (
                    n,
                    self.values[n],
                    None,
                    "40" if n == "hnsw.ef_search" else self.values[n],
                    self.values[n],
                    "session",
                    "user",
                    "string",
                    None,
                    None,
                )
                for n in sorted(params[0])
            ]
        elif "EXPLAIN" in text:
            scan = (
                {"Node Type": "Seq Scan", "Relation Name": "reviews"}
                if self.values.get("enable_seqscan") == "on"
                else {
                    "Node Type": "Index Scan",
                    "Index Name": "reviews_hnsw",
                    "Relation Name": "reviews",
                }
            )
            self.rows = [([{"Plan": {"Node Type": "Limit", "Plan Rows": 10, "Plans": [scan]}}],)]
        elif "1/0" in text:
            raise SqlFailure()
        elif "SELECT 1" in text:
            self.rows = [(1,)]
        else:
            raise AssertionError("Unexpected diagnostic SQL")
        return self

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


def fake_catalog():
    return {
        "server_version_num": "170011",
        "vector_version": "0.8.6",
        "relation": {
            "oid": 264000,
            "relkind": "r",
            "relrowsecurity": False,
            "relfilenode": 264000,
            "relpages": 100,
            "reltuples": 247286,
            "relallvisible": 100,
        },
        "columns": [
            {"attnum": 1, "attname": "id", "typname": "int8", "attnotnull": True, "atttypmod": -1},
            {
                "attnum": 2,
                "attname": "embedding",
                "typname": "vector",
                "attnotnull": True,
                "atttypmod": 768,
            },
            {
                "attnum": 3,
                "attname": "total_votes",
                "typname": "int8",
                "attnotnull": True,
                "atttypmod": -1,
            },
        ],
        "indexes": [
            {
                "oid": 264001,
                "relname": "reviews_pkey",
                "amname": "btree",
                "indisvalid": True,
                "indisready": True,
                "indisunique": True,
                "indisprimary": True,
                "partial": False,
                "expression": False,
                "indnatts": 1,
                "indnkeyatts": 1,
                "reloptions": None,
                "bytes": 1024,
                "definition": "mock-primary",
                "keys": ["id"],
                "opclasses": ["int8_ops"],
            },
            {
                "oid": 264013,
                "relname": "reviews_hnsw",
                "amname": "hnsw",
                "indisvalid": True,
                "indisready": True,
                "indisunique": False,
                "indisprimary": False,
                "partial": False,
                "expression": False,
                "indnatts": 1,
                "indnkeyatts": 1,
                "reloptions": ["m=16", "ef_construction=64"],
                "bytes": 1012678656,
                "definition": "mock-hnsw",
                "keys": ["embedding"],
                "opclasses": ["vector_cosine_ops"],
            },
        ],
        "statistics": [{"attname": "id"}, {"attname": "total_votes"}],
        "environment": {
            "plan_cache_mode": "auto",
            "jit": "on",
            "max_parallel_workers_per_gather": "2",
            "work_mem": "16384",
        },
    }


@lru_cache(maxsize=1)
def strict_snapshot():
    return Snapshot(
        [{"source_id": 0, "vector": [1.0, *([0.0] * 767)], "metadata": {"total_votes": 1000}}],
        [{"name": "total_votes", "type": "integer", "nullable": False}],
    )


class FakeBase:
    pins = None
    instances = []
    bad = False

    def __init__(self, bundle=None, work=None):
        self.state = {
            "source_manifest": {
                "settings": copy.deepcopy(SOURCE_SETTINGS),
                "metadata": copy.deepcopy(SOURCE_METADATA),
                "index": {"oid": 264013, "relname": "reviews_hnsw"},
            }
        }
        self.config = SimpleNamespace(query_timeout_seconds=30)
        self._snapshot = strict_snapshot()
        self.conn = self._binding = self._binding_conn = None
        self.calls = 0
        self.exact_calls = 0
        self.instances.append(self)

    def _settings(self, conn, *, local=True, source=None):
        for key, value in (source or self.state["source_manifest"])["settings"].items():
            conn.execute("set_config", (key, value, local))
        conn.execute("set_config", ("statement_timeout", "30000", local))

    def _bind(self, conn, source):
        self._settings(conn, source=source, local=False)
        self._binding, self._binding_conn = copy.deepcopy(source), conn

    def _connect(self):
        if self.conn is None or self.conn.closed:
            self.conn = FakeConnection()
            self._bind(self.conn, self.state["source_manifest"])
        return self.conn

    def close(self):
        if self.conn:
            self.conn.closed = True
        self.conn = self._binding = self._binding_conn = None

    def snapshot(self):
        return self._snapshot

    def _statement(self, query):
        from psycopg import sql

        text = metadata.expected_statement(query)
        counter = iter(range(1, len(metadata.parameters(query)) + 1))
        import re

        self._connect().native_sql = re.sub(r"%s", lambda m: "$" + str(next(counter)), text)
        return sql.SQL(text), metadata.parameters(query)

    def execute_probe(self, query, *, mode, **kwargs):
        assert mode == "native" and not kwargs
        self._connect()
        self.calls += 1
        if self.pins is None:
            ids, distances = list(range(10)), [i / 20 for i in range(10)]
        else:
            v = self.pins[query["id"]]["original640"]
            ids, distances = v["ids"], v["distances"]
        exact = self._binding["settings"]["enable_seqscan"] == "on"
        self.conn.native_calls += 1
        if exact and self.pins is not None:
            pin = self.pins[query["id"]]
            ids = (
                sorted(pin["truth_strict"])
                + sorted(pin["truth_ties"])[: 10 - len(pin["truth_strict"])]
            )
            distances = [i / 20 for i in range(10)]
        ms = (6 if self.bad else 4) if exact else 5
        CLOCK.advance(ms)
        ids = list(ids)
        return SimpleNamespace(
            ids=ids, distances=list(distances), latency_ms=ms - 0.001, metadata={}, evidence=None
        )

    def exact_reference(self, query):
        pin = self.pins[query["id"]]
        self.exact_calls += 1
        CLOCK.advance(1)
        return SimpleNamespace(
            strictly_better=frozenset(pin["truth_strict"]),
            boundary_ties=frozenset(pin["truth_ties"]),
            effective_k=pin["truth_k"],
            eligible_ids=frozenset(pin["original640"]["ids"])
            | frozenset(pin["truth_strict"])
            | frozenset(pin["truth_ties"])
            | frozenset({self.bad_id(query)}),
        )

    def bad_id(self, query):
        pin = self.pins[query["id"]]
        excluded = (
            set(pin["truth_strict"]) | set(pin["truth_ties"]) | set(pin["original640"]["ids"])
        )
        return next(i for i in self.eligible_replacements if i not in excluded)


def simulate(package, campaign, bad=False):
    """Write fake native results/clock data; never call a real backend."""
    FakeBase.instances, FakeBase.bad = [], bad
    FakeBase.pins = common.read(package / "baseline-results.json")
    eligibility = common.read(package / "eligibility.json")
    FakeBase.eligible_replacements = [
        i for i, v in enumerate(eligibility["votes"]) if v is not None and v >= 108
    ][:40]
    cfg = common.verify(package)
    out = campaign / "run"
    out.mkdir(parents=True)
    canonical = "/home/dar579/torch-reviews-results/" + campaign.name
    common.save(
        campaign / "submission.json",
        {
            "campaign": canonical,
            "package_manifest_sha256": common.sha(package / "manifest.json"),
            "counts": common.COUNTS,
            "jobs": {"block-0": "12345"},
            "dispatch": {"block-0": {"status": "submitted", "job_id": "12345"}},
        },
    )
    before = {"synthetic_mock": True}
    for p in (
        campaign / "protected-source-before.json",
        out / "protected-source-before.json",
        out / "protected-source-after.json",
    ):
        common.save(p, before)
    clock = CLOCK
    with patch("xt_measure.time.perf_counter_ns", side_effect=clock.now):
        factory = interface.Factory(FakeBase, None, None)
        begin = clock.now()
        reference = factory.create("native640", "initial-reference640")
        factory.snapshot = reference.backend.snapshot()
        items = measure.admit(
            factory.snapshot, common.lines(package / "frozen/inputs/queries.jsonl")
        )
        end = clock.now()
        common.save(
            out / "shared-initialization.json",
            {
                "start_ns": begin,
                "end_ns": end,
                "outer_ms": (end - begin) / 1e6,
                "origin_manifest": reference.origin,
                "source_effort": 320,
                "study_reference_effort": 640,
                "eligibility_sha256": common.sha(package / "eligibility.json"),
                "snapshot_identity": cfg["snapshot_identity"],
            },
        )
        budget = common.Budget()
        counts = measure.measure(
            factory, reference, score, budget, package, out, items, lambda *a, **k: None
        )
        begin = clock.now()
        factory.close()
        end = clock.now()
        common.save(
            out / "cleanup.json",
            {
                "start_ns": begin,
                "end_ns": end,
                "outer_ms": (end - begin) / 1e6,
                "all_readers_closed": True,
                "database_stopped": True,
            },
        )
    assert sum(r.calls + r.exact_calls for r in FakeBase.instances) == budget.calls
    passed = counts["quality_pass"]
    common.save(
        out / "admissions.json",
        {"readers": factory.admissions, "maximum_live_readers": factory.maximum_live},
    )
    source_cfg = common.read(package / "frozen/experiment.json")
    common.save(
        out / "runtime-identity.json",
        {
            "module_sha256": source_cfg["module_sha256"],
            "image_sha256": source_cfg["image_sha256"],
            "runtime_profile_hash": common.PROFILE_SHA,
            "registry_hash": "fc42b1fb1441518b15123ed30ba2a0d0c96e9c74d4f0727ab9eb391597cdbf37",
            "package_manifest_sha256": common.sha(package / "manifest.json"),
        },
    )
    common.save(out / "database-identity.json", common.read(package / "frozen/source-index.json"))
    common.save(out / "job-exit.json", {"exit_code": 0})
    common.save(out / "host.json", {"platform": "synthetic-local-check", "synthetic_mock": True})
    common.save(
        out / "charges.json",
        {
            "searches": budget.calls,
            "operations": dict(budget.operations),
            "explicit_reader_startup_execute_calls": 17 * len(factory.readers),
            "exact_internal_non_search_execute_calls": 12120,
            "restore_import": {"start_ns": 1, "end_ns": 1001, "outer_ms": 0.001},
            "overlapping_categories_must_not_be_summed": True,
            "observer": common.read(out / "metadata.json"),
        },
    )
    common.save(
        out / "status.json",
        {
            "status": "complete",
            "provider_calls": 0,
            "confirmation_queries": 0,
            "new_fits": 0,
            "cases": 600,
            "vectors": 200,
            "backend_searches": budget.calls,
            "operations": dict(budget.operations),
            "control_installations": 0,
            "index_and_module_after_verified": True,
            "reader_connections": len(factory.readers),
            "elapsed_seconds": 1.0,
            "completed_temporal_blocks": 2 if passed else 0,
            **counts,
        },
    )
    common.save(
        out / "LOCK.json",
        {
            "package_manifest_sha256": common.sha(package / "manifest.json"),
            "files_sha256": {p.name: common.sha(p) for p in sorted(out.iterdir()) if p.is_file()},
        },
    )
    common.save(
        out / "host-exit.json",
        {
            "exit_code": 0,
            "protected_sources_unchanged": True,
            "array_job_id": "12345",
            "array_task_id": "0",
        },
    )
    return counts, budget


class CorrectnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="fann-midpoint-mocks-")
        cls.root = Path(cls.temp.name)
        with redirect_stdout(io.StringIO()):
            cls.package = experiment.build(cls.root / "build")
        cls.full = cls.root / (common.PREFIX + "20261025T120000Z.mock")
        cls.counts, cls.budget = simulate(cls.package, cls.full)
        cls.full_report = report.analyze(cls.full, cls.package, cls.root / "report-full")
        cls.negative = cls.root / (common.PREFIX + "20261025T120000Z.negative")
        cls.negative_counts, cls.negative_budget = simulate(cls.package, cls.negative, bad=True)
        cls.negative_report = report.analyze(
            cls.negative, cls.package, cls.root / "report-quality-fail"
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_full600_case_two_block_mock_replay(self):
        self.assertEqual(self.budget.calls, 40230)
        self.assertEqual(dict(self.budget.operations), common.OPERATIONS)
        self.assertEqual(self.counts["retained_executions"], 19200)
        self.assertEqual(self.full_report["gate"]["status"], "promising_warm_context_frontier")
        self.assertFalse(self.full_report["gate"]["activation_qualified"])
        self.assertEqual(self.full_report["gate"]["aa"]["interval_checks"], 16)

    def test_valid_negative_economics_is_distinct_from_failed_semantics(self):
        self.assertEqual(self.negative_budget.calls, 40230)
        self.assertEqual(self.negative_report["gate"]["status"], "closed_negative_economics")
        self.assertTrue(self.negative_report["quality"]["pass"])
        self.assertEqual(self.negative_report["gate"]["aa"]["status"], "pass")
        self.assertFalse(self.negative_report["gate"]["qualifying_contexts"])

    def test_container_mount_alias_has_identical_report(self):
        alias = self.root / "results"
        alias.symlink_to(self.full, target_is_directory=True)
        # Same raw campaign through another mount-like root: no report normalization.
        replay = report.analyze(alias, self.package, self.root / "report-alias")
        common.parity(self.full_report, replay)
        self.assertEqual(replay["campaign"], common.PREFIX + "20261025T120000Z.mock")

    def test_negative_collect_archive_extract_sealed_replay(self):
        campaign = self.negative
        record = common.read(campaign / "submission.json")
        record.update(apptainer="apptainer-mock", bundle="/bundle-mock")

        def data_only_collect(cmd, **kwargs):
            self.assertIn("/patch/xt_report.py", cmd)
            self.assertEqual(cmd[-4:-2], ["/results", "/patch"])
            report.analyze(campaign, self.package, campaign / "analysis")
            return SimpleNamespace(returncode=0)

        with (
            patch("xt_control.bound", return_value=(campaign, record)),
            patch("xt_control.subprocess.run", side_effect=data_only_collect) as run,
            redirect_stdout(io.StringIO()),
        ):
            control.collect(self.package)
            self.assertEqual(run.call_count, 1)
        archive = Path(str(campaign) + ".tar.gz")
        self.assertEqual(common.sha(archive), Path(str(archive) + ".sha256").read_text().split()[0])
        returned = experiment.extract_data(archive, self.root / "returned")
        replay = report.analyze(returned, self.package, self.root / "report-returned")
        common.parity(replay, common.read(returned / "analysis/performance.json"))
        self.assertEqual(replay["gate"]["status"], "closed_negative_economics")

    def test_container_carries_slurm_identity_and_readonly_native_bindings(self):
        with patch.dict(
            "os.environ",
            {"SLURM_JOB_ID": "12345", "SLURM_ARRAY_JOB_ID": "12345", "SLURM_ARRAY_TASK_ID": "0"},
        ):
            cmd = container_command(
                self.package,
                Path("/bundle"),
                Path("/prepared"),
                Path("/out"),
                Path("/work"),
                "apptainer",
                0,
            )
        self.assertIn("SLURM_JOB_ID=12345", cmd)
        self.assertIn("SLURM_ARRAY_TASK_ID=0", cmd)
        self.assertIn(
            str(self.package / "frozen/modules/vector.so") + ":/opt/postgresql/lib/vector.so:ro",
            cmd,
        )
        self.assertEqual(cmd[-3:], ["/patch/xt_runtime.py", "--block", "0"])

    def test_frozen_metadata_works_with_real_snapshot_validator(self):
        snapshot = Snapshot(
            [{"source_id": 0, "vector": [1.0, *([0.0] * 767)], "metadata": {"total_votes": 108}}],
            interface.freeze(SOURCE_METADATA),
        )
        q = {
            "id": "test",
            "vector": [1.0, *([0.0] * 767)],
            "k": 10,
            "filter": {"field": "m_000000", "op": "gte", "value": 108},
        }
        admitted = measure.admit(snapshot, [{"group": "test", "query": q}])
        self.assertEqual(common.context(admitted[0]["query"]), "votes108")

    def test_provider_import_is_blocked(self):
        with self.assertRaises(RuntimeError):
            __import__("openai")

    def test_unrelated_campaign_or_gate_parity_change_rejected(self):
        changed = copy.deepcopy(self.full_report)
        changed["campaign"] = "results"
        with self.assertRaises(ValueError):
            common.parity(self.full_report, changed)
        changed = copy.deepcopy(self.full_report)
        changed["gate"]["status"] = "closed_negative_quality"
        with self.assertRaises(ValueError):
            common.parity(self.full_report, changed)

    def test_changed_job_submission_proof_rejected(self):
        p = self.full / "submission.json"
        old = p.read_bytes()
        try:
            row = json.loads(old)
            row["dispatch"]["block-0"]["job_id"] = "999"
            p.write_bytes(common.encoded(row))
            with self.assertRaises(ValueError):
                common.campaign_identity(self.full, self.package)
        finally:
            p.write_bytes(old)

    def test_ordinary_native_methods_inherited_unchanged(self):
        for level in ("exact10", "native640"):
            cls = interface.bound_class(NativeBackend, level)
            for name in (
                "_statement",
                "_execute_probe",
                "execute_probe",
                "_exact_reference",
                "exact_reference",
            ):
                self.assertIs(getattr(cls, name), getattr(NativeBackend, name))

    def test_immutable_origin_effective_and_admitted_queries(self):
        f = interface.Factory(FakeBase, None, None)
        r = f.create("exact10", "test")
        try:
            self.assertEqual(r.origin["settings"]["hnsw.ef_search"], "320")
            self.assertEqual(r.binding["settings"]["hnsw.ef_search"], "640")
            self.assertEqual(r.binding["settings"]["enable_indexscan"], "off")
            with self.assertRaises(TypeError):
                r.binding["settings"]["hnsw.ef_search"] = "640"
            with self.assertRaises(TypeError):
                r.origin["metadata"].append({})
            q = interface.freeze({"vector": [1.0, 0.0]})
            with self.assertRaises(TypeError):
                q["vector"][0] = 2.0
            mutable = copy.deepcopy(r.origin)
            mutable["settings"]["hnsw.ef_search"] = "999"
            self.assertEqual(r.origin["settings"]["hnsw.ef_search"], "320")
        finally:
            f.close()

    def test_stale_closed_and_replaced_connection_rejected_before_reservation(self):
        for change in (
            lambda r: r.close(),
            lambda r: setattr(r.backend, "conn", FakeConnection()),
            lambda r: setattr(r.backend, "_binding", copy.deepcopy(r.binding)),
        ):
            f = interface.Factory(FakeBase, None, None)
            r = f.create("native640", "test")
            budget = common.Budget()
            change(r)
            with self.assertRaises(RuntimeError):
                r.native({}, budget, "measurement")
            self.assertEqual(budget.calls, 0)
            f.close()

    def test_native_error_closes_and_never_replays(self):
        f = interface.Factory(FakeBase, None, None)
        r = f.create("native640", "test")
        budget = common.Budget()
        with patch.object(
            r.backend, "execute_probe", side_effect=RuntimeError("SQL failure")
        ) as call:
            with self.assertRaises(RuntimeError):
                r.native({}, budget, "measurement")
            with self.assertRaises(RuntimeError):
                r.native({}, budget, "measurement")
            self.assertEqual(call.call_count, 1)
        self.assertEqual(budget.calls, 1)
        self.assertTrue(r.closed)

    def test_invalid_effort_context_and_strict_query_rejected(self):
        for level in (True, 480.0, "480", None, 320, 640, "auto"):
            with self.assertRaises(ValueError):
                interface.bound_class(FakeBase, level)
        raw = common.lines(self.package / "frozen/inputs/queries.jsonl")[:1]
        for delta in (
            {"k": 9},
            {"filter": {"field": "m_000000", "op": "gte", "value": 33}},
            {"vector": [float("nan")] * 768},
            {"vector": [1.0]},
            {"vector": [2.0] * 768},
            {"mode": 480},
        ):
            changed = copy.deepcopy(raw)
            changed[0]["query"].update(delta)
            with self.assertRaises(Exception):
                measure.admit(strict_snapshot(), changed)

    def test_budget_and_live_reader_limits(self):
        budget = common.Budget()
        budget.operations["qualification_exact"] = 6
        with self.assertRaises(RuntimeError):
            budget.reserve("qualification_exact")
        budget.calls = 40230
        with self.assertRaises(RuntimeError):
            budget.reserve("measurement")
        f = interface.Factory(FakeBase, None, None)
        try:
            for i in range(5):
                f.create("exact10", str(i))
            with self.assertRaises(ValueError):
                f.create("native640", "six")
        finally:
            f.close()
        for i in range(9):
            f.create("native640", "closed" + str(i)).close()
        with self.assertRaises(ValueError):
            f.create("native640", "fifteen")

    def test_schedule_complements_without_more_independent_vectors(self):
        qid = "vector-unfiltered"
        a, b = list(measure.schedule(qid, 0)), list(measure.schedule(qid, 1))
        self.assertEqual(len(a), 8)
        self.assertEqual([x["cell"] for x in a[:4]], [x["cell"] for x in b[4:]])
        for cell in common.CELLS:
            first = [x["label"] for x in a if x["cell"] == cell]
            second = [x["label"] for x in b if x["cell"] == cell]
            self.assertIn(first, [["a", "b", "b", "a"], ["b", "a", "a", "b"]])
            self.assertEqual(second, [{"a": "b", "b": "a"}[x] for x in first])
        for stat in self.full_report["comparison"].values():
            self.assertEqual(stat["independent_vectors"], 200)

    def test_precision_and_economics_gate_failures_are_distinct(self):
        q, aa, comparison = (
            copy.deepcopy(self.full_report[k]) for k in ("quality", "aa", "comparison")
        )
        aa["exact10"]["overall"]["gap_ci95"] = [-0.01, 0.1001]
        self.assertEqual(report.gates(q, aa, comparison)["status"], "measurement_inconclusive")
        aa = copy.deepcopy(self.full_report["aa"])

        for stat in comparison.values():
            stat["gap_upper_adjusted"] = -0.09
        self.assertEqual(report.gates(q, aa, comparison)["status"], "closed_negative_economics")

    def test_rehashed_primary_timer_tamper_rejected(self):
        p, lock = self.full / "run/executions.jsonl", self.full / "run/LOCK.json"
        old, old_lock = p.read_bytes(), lock.read_bytes()
        try:
            line, rest = old.split(b"\n", 1)
            row = json.loads(line)
            row["outer_ms"] += 1
            p.write_bytes(json.dumps(row).encode() + b"\n" + rest)
            value = json.loads(old_lock)
            value["files_sha256"]["executions.jsonl"] = common.sha(p)
            lock.write_bytes(common.encoded(value))
            with self.assertRaises(ValueError):
                report.validate_run(self.full, self.package, common.verify(self.package))
        finally:
            p.write_bytes(old)
            lock.write_bytes(old_lock)

    def test_missing_execution_rejected_even_with_rehashed_lock(self):
        p, lock = self.full / "run/executions.jsonl", self.full / "run/LOCK.json"
        old, old_lock = p.read_bytes(), lock.read_bytes()
        try:
            p.write_bytes(old.split(b"\n", 1)[1])
            value = json.loads(old_lock)
            value["files_sha256"]["executions.jsonl"] = common.sha(p)
            lock.write_bytes(common.encoded(value))
            with self.assertRaises(ValueError):
                report.validate_run(self.full, self.package, common.verify(self.package))
        finally:
            p.write_bytes(old)
            lock.write_bytes(old_lock)

    def test_duplicate_reservation_and_unknown_dispatch_never_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reserve(root, self.package, root / "campaign")
            with self.assertRaises(FileExistsError):
                reserve(root, self.package, root / "other")
            campaign = root / "campaign"
            campaign.mkdir()
            record = {
                "dispatch": {},
                "jobs": {},
                "account": "torch_pr_mock",
                "bundle": "bundle",
                "prepared": "prepared",
                "campaign": str(campaign),
                "workspace": "work",
                "sources": "sources",
                "apptainer": "apptainer",
            }
            with patch(
                "xt_control.subprocess.run", side_effect=OSError("mock unavailable")
            ) as call:
                with self.assertRaises(OSError):
                    dispatch(self.package, campaign, record, 0)
                with self.assertRaises(ValueError):
                    dispatch(self.package, campaign, record, 0)
                self.assertEqual(call.call_count, 1)
            self.assertEqual(record["dispatch"]["block-0"]["status"], "unknown")

    def test_sealed_manifest_and_order_tamper_rejected(self):
        p = self.package / "order.json"
        old = p.read_bytes()
        try:
            p.write_bytes(old + b" ")
            with self.assertRaises(ValueError):
                common.verify(self.package)
        finally:
            p.write_bytes(old)

    def test_unsafe_archive_member_rejected(self):
        archive = self.root / (common.PREFIX + "20261025T120000Z.unsafe.tar.gz")
        with tarfile.open(archive, "w:gz") as tar:
            entry = tarfile.TarInfo(archive.name[:-7] + "/../../escape")
            entry.size = 1
            tar.addfile(entry, io.BytesIO(b"x"))
        with self.assertRaises(ValueError):
            experiment.extract_data(archive, self.root / "unsafe-extract")

    def test_actual_native_statement_and_vector_format_are_preserved(self):
        from psycopg import sql

        base = FakeBase()
        base.target = SimpleNamespace(id_column="id", vector_column="embedding")
        base.relation = sql.Identifier("public", "reviews")
        for item in common.lines(self.package / "frozen/inputs/queries.jsonl")[:12]:
            q = item["query"]
            stmt, params = NativeBackend._statement(base, q)
            self.assertEqual(stmt.as_string(None), metadata.expected_statement(q))
            self.assertEqual(params, metadata.parameters(q))

    def test_catalog_rejects_new_index_partial_graph_and_tuning(self):
        for change in [
            lambda x: x["indexes"].append(copy.deepcopy(x["indexes"][0])),
            lambda x: x["indexes"][1].update(partial=True),
            lambda x: x["environment"].update(jit="off"),
        ]:
            value = fake_catalog()
            change(value)
            with self.assertRaises(ValueError):
                metadata.validate_catalog(value)

    def test_exact_and_cached_plan_shape_rejects_ann_and_missing_cache(self):
        row = common.lines(self.full / "run/plan-audits.jsonl")[-1]
        q = next(
            i["query"]
            for i in common.lines(self.package / "frozen/inputs/queries.jsonl")
            if i["query"]["id"] == row["query_id"]
        )
        packet = copy.deepcopy(row["packet"])
        self.assertEqual(packet["mode"], "exact10")
        packet["fresh"] = [
            {
                "Plan": {
                    "Node Type": "Limit",
                    "Plans": [
                        {
                            "Node Type": "Index Scan",
                            "Relation Name": "reviews",
                            "Index Name": "reviews_hnsw",
                        }
                    ],
                }
            }
        ]
        with self.assertRaises(ValueError):
            metadata.validate_packet(packet, q, "exact10")
        packet = copy.deepcopy(row["packet"])
        packet["cached"] = []
        with self.assertRaises(ValueError):
            metadata.validate_packet(packet, q, "exact10")

    def test_metadata_plan_and_catalog_coverage_are_strict(self):
        self.assertEqual(common.read(self.full / "run/metadata.json")["plan_packets"], 12012)
        p = self.full / "run/metadata.json"
        old = p.read_bytes()
        lock = self.full / "run/LOCK.json"
        old_lock = lock.read_bytes()
        try:
            v = json.loads(old)
            v["catalogs"][-1]["value"]["statistics"] = [{"attname": "id"}]
            p.write_bytes(common.encoded(v))
            changed_lock = json.loads(old_lock)
            changed_lock["files_sha256"][p.name] = common.sha(p)
            lock.write_bytes(common.encoded(changed_lock))
            with self.assertRaises(ValueError):
                report.validate_run(self.full, self.package, common.verify(self.package))
        finally:
            p.write_bytes(old)
            lock.write_bytes(old_lock)

    def test_exact_tie_semantics_accept_reordering_reject_wrong_distance_or_missing_strict(self):
        value = {
            "ids": list(range(10)),
            "distances": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            "valid": True,
            "recall": 1.0,
            "returned_count": 10,
            "duplicate_count": 0,
            "predicate_violation_count": 0,
        }
        truth = {"truth_strict": list(range(9)), "truth_ties": [9, 10], "truth_k": 10}
        changed = copy.deepcopy(value)
        changed["ids"][-1] = 10
        equivalent(changed, value, truth, "exact10")
        changed["distances"][-1] = 0.91
        with self.assertRaises(ValueError):
            equivalent(changed, value, truth, "exact10")
        changed = copy.deepcopy(value)
        changed["ids"][0] = 10
        with self.assertRaises(ValueError):
            equivalent(changed, value, truth, "exact10")

    def test_adjusted_benefit_bound_prevents_pointwise_context_rescue(self):
        q, aa, c = (copy.deepcopy(self.full_report[k]) for k in ("quality", "aa", "comparison"))
        for stat in c.values():
            stat["gap_upper_adjusted"] = -0.09
        gate = report.gates(q, aa, c)
        self.assertEqual(gate["status"], "closed_negative_economics")
        self.assertFalse(gate["qualifying_contexts"])
        c["votes108"]["gap_upper_adjusted"] = -0.2
        gate = report.gates(q, aa, c)
        self.assertEqual(gate["qualifying_contexts"], ["votes108"])
        self.assertFalse(gate["router_selected"])

    def test_injected_quality_gate_stops_before_timing(self):
        # Control-flow injection only, not a pseudo-native quality finding.
        original = measure.quality_report

        def fail(refs):
            v = original(refs)
            v["pass"] = False
            return v

        campaign = self.root / (common.PREFIX + "20261025T120000Z.injectedgate")
        with patch("xt_measure.quality_report", side_effect=fail):
            counts, budget = simulate(self.package, campaign)
        self.assertEqual(budget.calls, 1830)
        self.assertFalse((campaign / "run/executions.jsonl").exists())
        self.assertEqual(common.read(campaign / "run/metadata.json")["plan_packets"], 2412)

    def test_exact_semantic_failure_aborts_before_quality_verdict(self):
        FakeBase.bad = False
        FakeBase.pins = common.read(self.package / "baseline-results.json")
        FakeBase.eligible_replacements = [
            i
            for i, v in enumerate(common.read(self.package / "eligibility.json")["votes"])
            if v >= 108
        ][:40]
        original = FakeBase.execute_probe

        def wrong(base, query, **kwargs):
            result = original(base, query, **kwargs)
            if base._binding["settings"]["enable_seqscan"] == "on":
                result.ids[0] = base.bad_id(query)
            return result

        f = interface.Factory(FakeBase, None, None)
        reference = f.create("native640", "initial-reference640")
        items = measure.admit(
            reference.backend.snapshot(), common.lines(self.package / "frozen/inputs/queries.jsonl")
        )
        with patch.object(FakeBase, "execute_probe", new=wrong):
            with self.assertRaises((ValueError, RuntimeError)):
                measure.qualify(f, reference, items, FakeBase.pins, common.Budget(), score)
        f.close()

    def test_failed_native_campaign_collects_with_terminal_accounting(self):
        campaign = self.root / (common.PREFIX + "20261025T120000Z.failed")
        campaign.mkdir()
        record = {
            "jobs": {"block-0": "777"},
            "dispatch": {"block-0": {"status": "submitted", "job_id": "777"}},
        }
        calls = []

        def scheduler(cmd, **kwargs):
            calls.append(cmd[0])
            if cmd[0] == "squeue":
                return SimpleNamespace(returncode=1, stdout="", stderr="invalid job id")
            return SimpleNamespace(returncode=0, stdout="777_0|TIMEOUT|0:0|\n", stderr="")

        with (
            patch("xt_control.bound", return_value=(campaign, record)),
            patch("xt_control.subprocess.run", side_effect=scheduler),
            redirect_stdout(io.StringIO()),
        ):
            control.collect(self.package)
        self.assertEqual(calls, ["squeue", "sacct"])
        self.assertTrue(Path(str(campaign) + ".tar.gz").exists())
        self.assertEqual(
            common.read(campaign / "analysis/failure-summary.json")["status"],
            "incomplete_or_failed",
        )

    def test_plan_literal_redaction_rejects_changed_query(self):
        q = {"vector": [1.0, *([0.0] * 767)]}
        text = "(embedding <=> '[" + ",".join(str(x) for x in q["vector"]) + "]'::vector)"
        self.assertIn("sealed_vector", metadata.compact_plan(text, q))
        with self.assertRaises(RuntimeError):
            metadata.compact_plan(text.replace("[1.0,", "[0.0,"), q)

    def test_observer_diagnostic_sql_ceiling_and_rehashed_plan_timer(self):
        observer = metadata.Observer()
        observer.operations["fresh_explain"] = 40000
        with self.assertRaises(RuntimeError):
            observer.execute(FakeConnection(), "fresh_explain", "SELECT 1")
        p = self.full / "run/plan-audits.jsonl"
        lock = self.full / "run/LOCK.json"
        old = p.read_bytes()
        old_lock = lock.read_bytes()
        try:
            line, rest = old.split(b"\n", 1)
            row = json.loads(line)
            row["packet"]["charge"]["outer_ms"] += 1
            p.write_bytes(json.dumps(row).encode() + b"\n" + rest)
            value = json.loads(old_lock)
            value["files_sha256"][p.name] = common.sha(p)
            lock.write_bytes(common.encoded(value))
            with self.assertRaises(ValueError):
                report.validate_run(self.full, self.package, common.verify(self.package))
        finally:
            p.write_bytes(old)
            lock.write_bytes(old_lock)


if __name__ == "__main__":
    unittest.main()
