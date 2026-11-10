"""Synthetic readiness checks only; no database/index/native/Torch/provider work."""
# ruff: noqa: E402 -- pinned vendor imports must follow the explicit bootstrap.

import copy
import io
import json
import re
import shutil
import tarfile
import tempfile
import unittest
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import experiment
import pa_common as C
import pa_control as control
import pa_interface as interface
import pa_measure as M
import pa_metadata as metadata
import pa_recovery as recovery
import pa_report as report
import pa_resources as resources
import pa_settings as settings
from pa_runtime import Journal
from pa_trace import Connection, Trace

C.bootstrap(experiment.SOURCE)
from fannagent_pgvector.backend import NativeBackend
from reference_backend import ExactReferenceMixin

from fannagent.snapshot import Snapshot

SETTINGS = C.read(experiment.SOURCE / "origin-settings.json")
METADATA = C.read(experiment.SOURCE / "origin-source.json")["metadata"]
VECTOR = [1.0] + [0.0] * 767


class Clock:
    value = 10**9

    def now(self):
        self.value += 1000
        return self.value

    def advance(self, ms):
        self.value += int(ms * 1e6)


CLOCK = Clock()


class SqlFailure(Exception):
    sqlstate = "22012"


def catalog(candidate=False, admin=False):
    base = dict(
        server_version_num="170011",
        vector_version="0.8.6",
        relation=dict(oid="264000", relkind="r", relrowsecurity=False),
        columns=[
            dict(attnum=1, attname="id", typname="int8", attnotnull=True, atttypmod=-1),
            dict(attnum=2, attname="embedding", typname="vector", attnotnull=True, atttypmod=768),
            dict(attnum=3, attname="total_votes", typname="int8", attnotnull=True, atttypmod=-1),
        ],
        indexes=[],
        statistics=[dict(attname="id"), dict(attname="total_votes")],
        environment=dict(
            plan_cache_mode="auto", jit="on", max_parallel_workers_per_gather="2", work_mem="16384"
        ),
    )
    if admin:
        base["environment"] = copy.deepcopy(settings.ADMIN_ENVIRONMENT)
    for name, am, oid, keys, ops, unique, primary, bs in [
        ("reviews_pkey", "btree", "264001", ["id"], ["int8_ops"], True, True, 1024),
        (
            "reviews_hnsw",
            "hnsw",
            "264013",
            ["embedding"],
            ["vector_cosine_ops"],
            False,
            False,
            1012678656,
        ),
    ]:
        base["indexes"].append(
            dict(
                oid=oid,
                relname=name,
                amname=am,
                indisvalid=True,
                indisready=True,
                indisunique=unique,
                indisprimary=primary,
                partial=False,
                expression=False,
                indnatts=1,
                indnkeyatts=1,
                keys=keys,
                opclasses=ops,
                bytes=bs,
                reloptions=["m=16", "ef_construction=64"] if am == "hnsw" else None,
                predicate=None,
                filepath="base/16384/" + oid,
                definition="synthetic",
            )
        )
    if candidate:
        i = copy.deepcopy(base["indexes"][-1])
        i.update(
            oid="270000",
            relname=C.INDEX,
            partial=True,
            predicate="(total_votes >= 108)",
            filepath="base/16384/270000",
            bytes=100000,
        )
        base["indexes"].append(i)
    return base


def snapshot():
    return Snapshot(
        [dict(source_id=i, vector=VECTOR, metadata=dict(total_votes=108)) for i in range(40)],
        METADATA,
    )


class FakeConnection:
    def __init__(self, mode):
        self.adapters = __import__("psycopg").adapters
        self.mode = mode
        self.closed = False
        self.autocommit = True
        self.info = SimpleNamespace(transaction_status=0, user="torch_reader")
        self.pgconn = SimpleNamespace(transaction_status=0)
        self.prepare_threshold = 5
        self.prepared_max = 100
        self.values = {}
        self.rows = []
        self.native_calls = 0
        self.native_sql = ""
        self.generic = False
        self.bad_cache = False

    @property
    def connection(self):
        return None

    @contextmanager
    def transaction(self):
        old = self.values.copy()
        try:
            yield
        finally:
            self.values = old

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def cursor(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter(self.rows)

    def execute(self, statement, params=None, prepare=None):
        text = statement.as_string(self) if hasattr(statement, "as_string") else str(statement)
        if "jsonb_build_object" in text:
            self.rows = [(catalog(self.mode == "partial640"),)]
        elif "pg_prepared_statements" in text:
            self.rows = (
                [
                    (
                        "mock_" + self.mode,
                        self.native_sql,
                        "{vector,smallint,vector,smallint}",
                        self.native_calls if self.generic else 0,
                        0 if self.generic else self.native_calls,
                    )
                ]
                if self.native_calls >= 6
                else []
            )
        elif "EXPLAIN" in text:
            self.rows = [
                (
                    [
                        {
                            "Plan": {
                                "Node Type": "Limit",
                                "Plans": [
                                    {
                                        "Node Type": "Index Scan",
                                        "Relation Name": "reviews",
                                        "Index Name": "reviews_hnsw"
                                        if self.mode == "native640" or self.bad_cache
                                        else C.INDEX,
                                    }
                                ],
                            }
                        }
                    ],
                )
            ]
            if "LIMIT" not in text and "EXECUTE" not in text:
                self.rows = [([{"Plan": {"Node Type": "Seq Scan", "Relation Name": "reviews"}}],)]
        elif "set_config" in text:
            args = re.search(r"set_config\((%s|'[^']*'),\s*(%s|'[^']*')", text).groups()
            it = iter(params or [])
            name, value = [next(it) if a == "%s" else a.strip("'") for a in args]
            self.values[name] = value
            self.rows = [(value,)]
        elif "FROM pg_settings" in text:
            self.rows = [
                (n, self.values[n], "40" if n == "hnsw.ef_search" else self.values[n], "session")
                for n in sorted(params[0])
            ]
        elif "1/0" in text:
            raise SqlFailure()
        elif "bind_target" in text:
            self.rows = [(270000 if self.mode == "partial640" else 264013,)]
        elif "current_database" in text:
            self.rows = [("torch_reviews", "torch_reader", None, False, False)]
        elif text == "SELECT 1":
            self.rows = [(1,)]
        elif text.startswith('SELECT "id", "embedding" <=>'):
            exact = " LIMIT " not in text
            ids = list(range(40 if exact else 10))
            if not exact:
                self.native_calls += 1
                count = iter(range(1, 5))
                self.native_sql = re.sub("%s", lambda m: "$" + str(next(count)), text)
                if self.mode == "partial640" and FakeBase.behavior == "quality":
                    ids[-1] = 10
            self.rows = [(i, i / 20) for i in ids]
            CLOCK.advance(
                1
                if exact
                else (12 if FakeBase.behavior == "futility" else 4)
                if self.mode == "partial640"
                else 5
            )
        else:
            raise AssertionError("Unexpected SQL: " + text[:140])
        return self

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


class FakeBase(ExactReferenceMixin):
    trace = None
    behavior = "good"
    fail = False

    def __init__(self, bundle, work):
        self.work = work
        self.state = dict(
            source_manifest=dict(
                settings=copy.deepcopy(SETTINGS),
                metadata=copy.deepcopy(METADATA),
                index=dict(oid=264013, relname="reviews_hnsw"),
            ),
            prepared=dict(index_identity="original"),
        )
        self.target = SimpleNamespace(
            schema_name="public", resource="reviews", id_column="id", vector_column="embedding"
        )
        self.config = SimpleNamespace(query_timeout_seconds=30)
        self._snapshot = snapshot()
        self.conn = self._binding = self._binding_conn = None

    relation = NativeBackend.relation
    _statement = NativeBackend._statement
    _settings = NativeBackend._settings

    def snapshot(self):
        return self._snapshot

    def _connect(self):
        if self.conn is None or self.conn.closed:
            self.close()
            mode = (
                "partial640"
                if self.state["source_manifest"]["index"]["relname"] == C.INDEX
                else "native640"
            )
            self.conn = Connection(FakeConnection(mode), self.trace)
            self.conn.execute("SELECT current_database()")
            self._bind(self.conn, self.state["source_manifest"])
        return self.conn

    def _bind(self, conn, source):
        conn.execute("SELECT fannagent.bind_target()")
        self._settings(conn, local=False, source=source)
        self._binding = copy.deepcopy(source)
        self._binding_conn = conn

    def close(self):
        if self.conn:
            self.conn.close()
        self.conn = self._binding = self._binding_conn = None

    def execute_probe(self, q, *, mode):
        if self.fail:
            raise RuntimeError("synthetic native failure")
        assert mode == "native"
        statement, params = self._statement(q)
        start = CLOCK.now()
        rows = self._connect().execute(statement, params).fetchall()
        end = CLOCK.now()
        return SimpleNamespace(
            ids=[r[0] for r in rows],
            distances=[r[1] for r in rows],
            latency_ms=(end - start) / 1e6,
            metadata={},
            evidence=None,
        )

    def exact_reference(self, q):
        return self._exact_reference(q)


def rehash(package):
    p = package / "manifest.json"
    m = C.read(p)
    m["files"] = {
        str(f.relative_to(package)): C.sha(f)
        for f in sorted(package.rglob("*"))
        if f.is_file() and f != p
    }
    p.write_bytes(C.encoded(m))


def fixture_package(output):
    p = experiment.build(output, testing=True)
    cfg = C.read(p / "experiment.json")
    snap = snapshot()
    pins = {
        i["query"]["id"]: dict(
            truth_strict=list(range(9)),
            truth_ties=[9],
            truth_k=10,
            original640=dict(
                ids=list(range(10)),
                distances=[i / 20 for i in range(10)],
                recall=1.0,
                valid=True,
                returned_count=10,
                duplicate_count=0,
                predicate_violation_count=0,
            ),
        )
        for i in C.lines(p / "queries.jsonl")
    }
    (p / "baseline-results.json").write_bytes(C.encoded(pins))
    (p / "eligibility.json").write_bytes(
        C.encoded(dict(source_ids=list(range(40)), votes=[108] * 40))
    )
    cfg["snapshot_identity"] = snap.identity
    (p / "experiment.json").write_bytes(C.encoded(cfg))
    rehash(p)
    C.verify(p)
    return p


def finish_lock(out, package):
    (out / "LOCK.json").write_bytes(
        C.encoded(
            dict(
                package_manifest_sha256=C.sha(package / "manifest.json"),
                complete=True,
                files_sha256={
                    p.name: C.sha(p)
                    for p in sorted(out.iterdir())
                    if p.is_file()
                    and p.name
                    not in [
                        "LOCK.json",
                        "progress.json",
                        "host-exit.json",
                        "protected-source-before.json",
                        "protected-source-after.json",
                        "resource-preflight.json",
                    ]
                },
            )
        )
    )


def simulate(package, campaign, behavior="good"):
    cfg = C.verify(package)
    out = campaign / "run"
    out.mkdir(parents=True)
    FakeBase.behavior = behavior
    FakeBase.fail = False
    C.save(
        campaign / "submission.json",
        dict(
            campaign="/home/dar579/torch-reviews-results/" + campaign.name,
            package_manifest_sha256=C.sha(package / "manifest.json"),
            counts=C.COUNTS,
            jobs={"block-0": "12345"},
            dispatch={"block-0": dict(status="submitted", job_id="12345")},
        ),
    )
    for p in [
        campaign / "protected-source-before.json",
        out / "protected-source-before.json",
        out / "protected-source-after.json",
    ]:
        C.save(p, dict(synthetic_mock=True))
    C.save(
        campaign / "scheduler-evidence.json",
        dict(terminal_verified=True, sacct_stdout="12345_0|COMPLETED|0:0|00:10:00\n"),
    )
    budget = C.Budget(clock=lambda: 0)
    budget.enter("build")
    journal = Journal(out, budget)
    trace = Trace(budget, journal.emit)
    FakeBase.trace = trace
    observer = metadata.Observer(budget, journal.emit)
    orig = C.read(package / "frozen/source-index.json")
    g = next(i for i in catalog(True)["indexes"] if i["relname"] == C.INDEX)
    graph = dict(index=g, files_sha256={"270000": "a" * 64})
    graph["index_identity"] = C.digest(graph)
    targets = {
        "native640": dict(
            index=dict(oid=264013, relname="reviews_hnsw"), index_identity=orig["index_identity"]
        ),
        "partial640": dict(
            index=dict(oid=270000, relname=C.INDEX), index_identity=graph["index_identity"]
        ),
    }
    for mode in C.CELLS:
        for phase, candidate in [("before_build", False), ("after_build", mode == "partial640")]:
            v = catalog(candidate, admin=True)
            r = dict(
                copy=mode,
                session_user="torch_owner",
                phase=phase,
                candidate=candidate,
                value=v,
                sha256=C.digest(v),
                charge=dict(start_ns=CLOCK.now(), end_ns=CLOCK.now(), outer_ms=0.001),
            )
            journal.emit("catalogs", r)
    factory = interface.Factory(
        FakeBase,
        None,
        {"native640": Path("/fake/a"), "partial640": Path("/fake/b")},
        targets,
        observer,
        budget,
        journal.emit,
    )
    with patch("time.perf_counter_ns", side_effect=CLOCK.now):
        reference = factory.create("native640", "initial-native-reference")
        factory.snapshot = reference.backend.snapshot()
        items = M.admit(factory.snapshot, C.lines(package / "queries.jsonl"))
        factory.requests = {i["query"]["id"]: i["query"] for i in items}
        result = M.measure(
            factory,
            reference,
            budget,
            package,
            out,
            items,
            lambda *a, **kw: None,
            journal.emit,
            journal.checkpoint,
        )
    for mode in C.CELLS:
        v = catalog(mode == "partial640", admin=True)
        journal.emit(
            "catalogs",
            dict(
                copy=mode,
                session_user="torch_owner",
                phase="final",
                candidate=mode == "partial640",
                value=v,
                sha256=C.digest(v),
                charge=dict(start_ns=CLOCK.now(), end_ns=CLOCK.now(), outer_ms=0.001),
            ),
        )
    factory.close()
    frozen = C.read(package / "frozen/experiment.json")
    C.save(out / "build.json", dict(graph=graph, build_settings=settings.BUILD_SETTINGS))
    C.save(out / "targets.json", targets)
    C.save(out / "database-identity.json", orig)
    C.save(
        out / "final-integrity.json",
        dict(
            native640=dict(original_graph_files=orig["index_files"], data_bits_verified=True),
            partial640=dict(
                original_graph_files=orig["index_files"],
                partial_graph_files=graph["files_sha256"],
                data_bits_verified=True,
            ),
            module_sha256=frozen["module_sha256"],
        ),
    )
    C.save(
        out / "runtime-identity.json",
        dict(
            module_sha256=frozen["module_sha256"],
            image_sha256=frozen["image_sha256"],
            runtime_profile_hash=C.PROFILE_SHA,
            registry_hash=report.REGISTRY,
            synthetic_mock=True,
        ),
    )
    C.save(
        out / "shared-initialization.json",
        dict(
            snapshot_identity=cfg["snapshot_identity"],
            eligibility_sha256=C.sha(package / "eligibility.json"),
            admitted_requests=200,
            source_effort=320,
            reference_effort=640,
            two_private_copies=True,
        ),
    )
    C.save(
        out / "resource-preflight.json",
        dict(
            memory_gib=32,
            quota={
                fs: dict(
                    filesystem_free_bytes=10**12,
                    space_available_lower=10**12,
                    required_bytes=10**10,
                    filesystem_free_inodes=10**6,
                    inodes_available_lower=10**6,
                    required_inodes=1000,
                )
                for fs in ["/scratch", "/home"]
            },
        ),
    )
    C.save(
        out / "memory-preflight.json",
        settings.memory_proof(
            [
                settings.memory_record(mode, (128 * 1024**2, 16, 4 * 1024**2, "64MB", "2"))
                for mode in C.CELLS
            ]
        ),
    )
    C.save(out / "cleanup.json", dict(all_readers_closed=True, databases_stopped=True, errors=[]))
    C.save(
        out / "status.json",
        dict(
            status="complete",
            result=result,
            backend_searches=budget.calls,
            operations=dict(budget.operations),
            sql=dict(budget.sql),
            search_sql=trace.search_sql,
            final_integrity_verified=True,
            reader_connections=len(factory.readers),
            maximum_live_readers=factory.maximum_live,
        ),
    )
    C.save(out / "job-exit.json", dict(exit_code=0))
    journal.close()
    C.save(
        out / "host-exit.json",
        dict(
            exit_code=0,
            protected_sources_unchanged=True,
            job_id="12345",
            array_job_id="12345",
            array_task_id="0",
            provider_calls=0,
        ),
    )
    finish_lock(out, package)
    return result, budget


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="partial-ann-mocks-")
        cls.root = Path(cls.temp.name)
        cls.package = fixture_package(cls.root / "fixture")
        cls.cases = {}
        cls.reports = {}
        for behavior in ["good", "quality", "futility"]:
            campaign = cls.root / (C.PREFIX + "20261026T120000Z." + behavior)
            cls.cases[behavior] = campaign
            simulate(cls.package, campaign, behavior)
            cls.reports[behavior] = report.analyze(
                campaign, cls.package, cls.root / ("report-" + behavior), allow_synthetic=True
            )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_01_full_counts_and_positive_gate(self):
        r = self.reports["good"]
        self.assertEqual(r["searches"], 16802)
        self.assertEqual(r["operations"], C.OPERATIONS)
        self.assertEqual(r["outcome"], "promising_partial_ann_votes108")
        self.assertEqual(r["plan_packets"], 5700)

    def test_02_quality_stop_before_timing(self):
        self.assertEqual(self.reports["quality"]["outcome"], "closed_negative_quality")
        self.assertEqual(self.reports["quality"]["searches"], 802)
        self.assertIsNone(self.reports["quality"]["economics"])

    def test_03_cost_futility_is_resource_only(self):
        self.assertEqual(self.reports["futility"]["searches"], 202)
        self.assertEqual(self.reports["futility"]["outcome"], "closed_cost_futility")
        self.assertFalse(self.reports["futility"]["preview"]["positive_acceptance"])
        self.assertIsNone(self.reports["futility"]["quality"])

    def test_04_never_accept_mock_as_native(self):
        with self.assertRaisesRegex(ValueError, "Synthetic"):
            report.analyze(self.cases["good"], self.package, self.root / "reject-synthetic")

    def test_05_request_predicate_guard(self):
        q = C.lines(self.package / "queries.jsonl")[0]["query"]
        for bad in [
            None,
            {"field": "m_000000", "op": "gte", "value": 32},
            {"field": "m_000001", "op": "gte", "value": 108},
            {"field": "m_000000", "op": "gt", "value": 108},
            {"field": "m_000000", "op": "gte", "value": 108.0},
        ]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                C.context({**q, "filter": bad})

    def test_06_strict_k_and_extra_ast(self):
        q = C.lines(self.package / "queries.jsonl")[0]["query"]
        for k in [True, 10.0, 9]:
            with self.assertRaises(ValueError):
                C.context({**q, "k": k})
        with self.assertRaises(ValueError):
            C.context({**q, "filter": {**q["filter"], "extra": 1}})

    def test_07_immutable_owned_state(self):
        f = interface.freeze(dict(a=[1], b=dict(c=2)))
        with self.assertRaises(TypeError):
            f["x"] = 1
        with self.assertRaises(TypeError):
            f["a"].append(2)
        with self.assertRaises(TypeError):
            f["b"].update(c=3)

    def test_08_catalog_strict_original_oid_type(self):
        for v in [264013, "264014", None]:
            c = catalog()
            c["indexes"][1]["oid"] = v
            with self.assertRaises(ValueError):
                metadata.validate_catalog(c)

    def test_09_catalog_partial_predicate(self):
        for pred in ["(total_votes >= 32)", "(total_votes > 108)", "true", None]:
            c = catalog(True)
            c["indexes"][-1]["predicate"] = pred
            with self.assertRaises(ValueError):
                metadata.validate_catalog(c, True)

    def test_10_additional_index_rejected(self):
        c = catalog(True)
        c["indexes"].append(copy.deepcopy(c["indexes"][0]))
        with self.assertRaises(ValueError):
            metadata.validate_catalog(c, True)

    def test_11_partial_ready_opclass_dimension_bounds(self):
        for key, val in [
            ("indisvalid", False),
            ("expression", True),
            ("opclasses", ["vector_l2_ops"]),
            ("bytes", C.INDEX_BYTES + 1),
            ("oid", 270000),
            ("filepath", "../../bad"),
        ]:
            c = catalog(True)
            c["indexes"][-1][key] = val
            with self.subTest(key=key), self.assertRaises(ValueError):
                metadata.validate_catalog(c, True)

    def test_12_baseline_copy_cannot_contain_candidate(self):
        with self.assertRaises(ValueError):
            metadata.validate_catalog(catalog(True), False)

    def test_13_fresh_plan_must_use_its_target(self):
        value = [
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
        self.assertTrue(metadata.plan_matches(value, "native640"))
        self.assertFalse(metadata.plan_matches(value, "partial640"))

    def test_14_generic_cached_plan_is_checked(self):
        rows = C.lines(self.cases["good"] / "run/plans.jsonl")
        r = next(r for r in rows if r["packet"]["cached"] and r["packet"]["mode"] == "partial640")
        p = copy.deepcopy(r["packet"])
        p["cached"][0]["generic_plans"] = 50
        p["cached"][0]["custom_plans"] = 0
        q = next(
            i["query"]
            for i in C.lines(self.package / "queries.jsonl")
            if i["query"]["id"] == r["query_id"]
        )
        metadata.validate_packet(p, q, "partial640")
        p["cached"][0]["plan"][0]["Plan"]["Plans"][0]["Index Name"] = "reviews_hnsw"
        with self.assertRaises(ValueError):
            metadata.validate_packet(p, q, "partial640")

    def test_15_missing_cache_is_rejected(self):
        row = next(
            r
            for r in C.lines(self.cases["good"] / "run/plans.jsonl")
            if r["packet"]["must_be_cached"]
        )
        p = copy.deepcopy(row["packet"])
        p["cached"] = []
        q = next(
            i["query"]
            for i in C.lines(self.package / "queries.jsonl")
            if i["query"]["id"] == row["query_id"]
        )
        with self.assertRaises(ValueError):
            metadata.validate_packet(p, q, p["mode"])

    def test_16_schedule_balance_complement(self):
        q = C.lines(self.package / "queries.jsonl")[0]["query"]["id"]
        a = list(M.schedule(q, 0))
        b = list(M.schedule(q, 1))
        self.assertEqual(len(a), 8)
        self.assertEqual([x["cell"] for x in a], [x["cell"] for x in b][::-1])
        for c in C.CELLS:
            self.assertEqual(Counter(x["label"] for x in a if x["cell"] == c), {"a": 2, "b": 2})

    def test_17_preview_selection_reproducible_and_disjoint_from_formal(self):
        o = C.read(self.package / "order.json")
        self.assertEqual(len(set(o["preview_order"])), 24)
        self.assertEqual(o, M.order_manifest(C.lines(self.package / "queries.jsonl")))

    def test_18_budget_search_cap_and_no_replay(self):
        b = C.Budget(clock=lambda: 0)
        b.enter("quality")
        b.operations["reference_exact"] = 200
        with self.assertRaises(RuntimeError):
            b.reserve("reference_exact")
        self.assertEqual(b.calls, 0)

    def test_19_stage_reserves_finalization(self):
        now = [0]
        b = C.Budget(clock=lambda: now[0])
        b.enter("restore")
        now[0] = 1171
        with self.assertRaises(RuntimeError):
            b.reserve("qualification_exact")
        now[0] = 9700
        with self.assertRaises(RuntimeError):
            b.enter("build")
        b.enter("final")
        self.assertLessEqual(b.stage_end, b.deadline)

    def test_20_sql_caps(self):
        b = C.Budget(clock=lambda: 0)
        b.enter("quality")
        b.sql["observer"] = 20000
        with self.assertRaises(RuntimeError):
            b.sql_reserve("observer")

    def test_21_preview_all_predicates_required(self):
        rows = [dict(query_id=str(i), native640_ms=1, partial640_ms=2) for i in range(24)]
        self.assertTrue(M.preview_decision(rows)["stop"])
        rows[0]["partial640_ms"] = 0.01
        rows[1]["partial640_ms"] = 0.01
        rows[2]["partial640_ms"] = 0.01
        rows[3]["partial640_ms"] = 0.01
        rows[4]["partial640_ms"] = 0.01
        self.assertFalse(M.preview_decision(rows)["stop"])

    def test_22_incomplete_preview_never_qualifies(self):
        with self.assertRaises(ValueError):
            M.preview_decision([])

    def test_23_quota_official_display_rounding(self):
        q = resources.quota_report(
            "/home $HOME YES/NO 0.05TB/0.03M 0.0TB(0.0%)/1(0%)\n"
            "/scratch $SCRATCH NO/YES 5.0TB/5.0M 0.0TB(0.0%)/1(0%)"
        )
        self.assertGreater(q["/home"]["space_available_lower"], 3 * 1024**3)
        self.assertGreater(q["/scratch"]["inodes_available_lower"], 10**6)

    def test_24_unknown_quota_fails_closed(self):
        with self.assertRaises(ValueError):
            resources.quota_report("some unsupported output")

    def test_25_archive_rejects_traversal_and_symlinks(self):
        for name, typ in [
            (C.PREFIX + "20261026T120000Z.bad/../../escape", tarfile.REGTYPE),
            (C.PREFIX + "20261026T120000Z.bad/link", tarfile.SYMTYPE),
        ]:
            p = self.root / (C.PREFIX + "20261026T120000Z.bad.tar.gz")
            if p.exists():
                p.unlink()
            with tarfile.open(p, "w:gz") as t:
                m = tarfile.TarInfo(name)
                m.type = typ
                t.addfile(m)
            with self.assertRaises(ValueError):
                experiment.extract_data(p, self.root / "unsafe")

    def test_26_duplicate_reservation_is_irrevocable(self):
        out = self.root / "reserve"
        out.mkdir()
        control.reserve(out, self.package, out / "campaign")
        with self.assertRaises(FileExistsError):
            control.reserve(out, self.package, out / "other")

    def test_27_unknown_dispatch_stays_bound(self):
        out = self.root / "dispatch"
        out.mkdir()
        r = dict(dispatch={}, jobs={})
        with (
            patch.object(control, "command", return_value=["fake"]),
            patch.object(control.subprocess, "run", side_effect=OSError("unknown")),
        ):
            with self.assertRaises(OSError):
                control.dispatch(self.package, out, r, 0)
        self.assertEqual(r["dispatch"]["block-0"]["status"], "unknown")
        with self.assertRaises(ValueError):
            control.dispatch(self.package, out, r, 0)

    def test_28_native_method_is_inherited(self):
        for mode in C.CELLS:
            B = interface.bound_class(
                FakeBase, mode, dict(index=dict(oid=1, relname="test"), index_identity="hash")
            )
            self.assertIs(B.execute_probe, FakeBase.execute_probe)

    def test_29_statement_literal_only_candidate_and_preserves_params(self):
        q = C.lines(self.package / "queries.jsonl")[0]["query"]
        base = FakeBase(None, None)
        raw, _ = base._statement(q)
        self.assertEqual(raw.as_string(), metadata.expected_statement(q))
        self.assertIn(' AND "total_votes" >= 108', metadata.expected_statement(q, "partial640"))
        self.assertNotIn("AND", metadata.expected_statement(q, exact=True))

    def test_30_raw_timer_tampering_even_if_rehashed(self):
        p = self.cases["good"] / "run/searches.jsonl"
        old = p.read_bytes()
        rows = C.lines(p)
        rows[-1]["outer_ms"] += 1
        p.write_text("".join(json.dumps(r) + "\n" for r in rows))
        finish_lock(p.parent, self.package)
        try:
            with self.assertRaises(ValueError):
                report.analyze(
                    self.cases["good"],
                    self.package,
                    self.root / "reject-timer",
                    allow_synthetic=True,
                )
        finally:
            p.write_bytes(old)
            finish_lock(p.parent, self.package)

    def test_31_missing_raw_even_if_rehashed(self):
        p = self.cases["good"] / "run/searches.jsonl"
        old = p.read_bytes()
        p.write_bytes(
            old.splitlines(keepends=True)[0] + b"".join(old.splitlines(keepends=True)[2:])
        )
        finish_lock(p.parent, self.package)
        try:
            with self.assertRaises(ValueError):
                report.analyze(
                    self.cases["good"],
                    self.package,
                    self.root / "reject-missing",
                    allow_synthetic=True,
                )
        finally:
            p.write_bytes(old)
            finish_lock(p.parent, self.package)

    def test_32_package_manifest_tamper(self):
        p = self.package / "order.json"
        old = p.read_bytes()
        p.write_text("{}")
        try:
            with self.assertRaises(ValueError):
                C.verify(self.package)
        finally:
            p.write_bytes(old)

    def test_33_no_provider_import(self):
        with self.assertRaises(RuntimeError):
            __import__("openai")

    def test_34_container_bindings_are_readonly(self):
        from pa_job import container_command

        cmd = container_command(
            self.package,
            Path("/bundle"),
            Path("/prepared"),
            Path("/out"),
            Path("/work"),
            "apptainer",
            0,
        )
        self.assertIn(str(self.package) + ":/patch:ro", cmd)
        self.assertIn("/prepared:/prepared:ro", cmd)
        self.assertIn("/patch/pa_runtime.py", cmd)

    def test_35_semantic_invalid_output_is_not_quality_negative(self):
        q = C.lines(self.package / "queries.jsonl")[0]["query"]
        pin = C.read(self.package / "baseline-results.json")[q["id"]]
        r = SimpleNamespace(ids=[0] * 10, distances=[0.0] * 10, metadata={}, evidence=None)
        with self.assertRaises(RuntimeError):
            M.record_result(r, pin, q, C.read(self.package / "eligibility.json"))

    def test_36_tied_order_mapping_equivalence(self):
        a = dict(valid=True, recall=1.0, ids=[1, 2], distances=[0.1, 0.1])
        M.equivalent(a, dict(valid=True, recall=1.0, ids=[2, 1], distances=[0.1, 0.1]))
        with self.assertRaises(RuntimeError):
            M.equivalent(a, {**a, "distances": [0.1, 0.2]})

    def test_37_synthetic_fixture_cannot_submit(self):
        with patch.object(control, "verify", return_value=C.read(self.package / "experiment.json")):
            with self.assertRaisesRegex(ValueError, "Synthetic"):
                control.submit(self.package, Path("/bundle"), Path("/sources"))

    def factory(self, tag):
        b = C.Budget(clock=lambda: 0)
        b.enter("quality")
        directory = self.root / tag
        directory.mkdir()
        journal = Journal(directory, b)
        FakeBase.trace = Trace(b, journal.emit)
        observer = metadata.Observer(b, journal.emit)
        targets = C.read(self.cases["good"] / "run/targets.json")
        f = interface.Factory(
            FakeBase,
            None,
            {"native640": Path("/fake/a"), "partial640": Path("/fake/b")},
            targets,
            observer,
            b,
            journal.emit,
        )
        r = f.create("native640", "test-reference")
        f.snapshot = r.backend.snapshot()
        items = M.admit(f.snapshot, C.lines(self.package / "queries.jsonl"))
        f.requests = {i["query"]["id"]: i["query"] for i in items}
        self.addCleanup(f.close)
        self.addCleanup(journal.close)
        return f, r, items[0]["query"], b, journal

    def test_38_stale_connection_rejected_before_reservation(self):
        f, r, q, b, j = self.factory("stale")
        r.backend.conn = Connection(FakeConnection("native640"), FakeBase.trace)
        with self.assertRaises(RuntimeError):
            r.native(q, b, "reference_native640")
        self.assertEqual(b.calls, 0)

    def test_39_unowned_mutable_request_is_rejected(self):
        f, r, q, b, j = self.factory("unowned")
        with self.assertRaises(RuntimeError):
            r.native(copy.deepcopy(q), b, "reference_native640")
        self.assertEqual(b.calls, 0)

    def test_40_native_error_closes_and_no_replay(self):
        f, r, q, b, j = self.factory("native-failure")
        FakeBase.fail = True
        try:
            with self.assertRaises(RuntimeError):
                r.native(q, b, "reference_native640")
            self.assertTrue(r.closed)
            self.assertEqual(b.calls, 1)
            with self.assertRaises(RuntimeError):
                r.native(q, b, "reference_native640")
            self.assertEqual(b.calls, 1)
        finally:
            FakeBase.fail = False

    def test_41_rejected_catalog_persisted_before_validator(self):
        f, r, q, b, j = self.factory("rejected-catalog")
        bad = catalog()
        bad["indexes"].append(copy.deepcopy(bad["indexes"][0]))
        original = r.connection.raw.execute

        def execute(statement, params=None, **kwargs):
            if "jsonb_build_object" in str(statement):
                r.connection.raw.rows = [(bad,)]
                return r.connection.raw
            return original(statement, params, **kwargs)

        with patch.object(r.connection.raw, "execute", side_effect=execute):
            with self.assertRaises(ValueError):
                f.observer.catalog(r.connection, "native640", "rejected")
        self.assertEqual(C.lines(j.out / "catalogs.jsonl")[0]["value"], bad)

    def test_42_missing_quota_never_dispatches(self):
        with (
            patch.object(resources.shutil, "which", return_value=None),
            patch.object(resources.subprocess, "run") as run,
        ):
            with self.assertRaises(RuntimeError):
                resources.preflight(Path("/prepared"), Path("/scratch/user"), Path("/home/user"))
            run.assert_not_called()

    def test_43_two_distinct_copy_paths_required(self):
        with self.assertRaises(ValueError):
            interface.Factory(
                FakeBase,
                None,
                dict(native640=Path("/same"), partial640=Path("/same")),
                C.read(self.cases["good"] / "run/targets.json"),
                None,
                None,
                None,
            )

    def test_44_AA_failure_cannot_be_rescued_by_large_benefit(self):
        rows = [
            copy.deepcopy(r)
            for r in C.lines(self.cases["good"] / "run/searches.jsonl")
            if r["operation"] == "measurement"
        ]
        for r in rows:
            if r["cell"] == "native640" and r["label"] == "b":
                r["outer_ms"] += 0.30
        g = report.gates(rows)
        self.assertTrue(g["comparison"]["pass"])
        self.assertFalse(g["aa"]["native640"]["pass"])
        self.assertEqual(g["verdict"], "measurement_inconclusive")

    def test_45_recall_reserve_binds_even_when_floors_pass(self):
        refs = C.lines(self.cases["good"] / "run/references.jsonl")
        for r in refs[:10]:
            r["outcomes"]["partial640"]["recall"] = 0.9
        g = M.quality_report(refs)
        self.assertTrue(g["checks"]["both_native_floors"])
        self.assertFalse(g["checks"]["development_reserve"])
        self.assertFalse(g["pass"])

    def test_46_duplicate_cached_shape_is_rejected(self):
        r = next(
            r for r in C.lines(self.cases["good"] / "run/plans.jsonl") if r["packet"]["cached"]
        )
        p = copy.deepcopy(r["packet"])
        p["cached"] *= 2
        q = next(
            i["query"]
            for i in C.lines(self.package / "queries.jsonl")
            if i["query"]["id"] == r["query_id"]
        )
        with self.assertRaises(ValueError):
            metadata.validate_packet(p, q, p["mode"])

    def test_47_incomplete_lock_has_no_performance_verdict(self):
        p = self.cases["good"] / "run/LOCK.json"
        old = p.read_bytes()
        v = C.read(p)
        v["complete"] = False
        p.write_bytes(C.encoded(v))
        try:
            with self.assertRaises(ValueError):
                report.analyze(
                    self.cases["good"],
                    self.package,
                    self.root / "reject-incomplete",
                    allow_synthetic=True,
                )
        finally:
            p.write_bytes(old)

    def test_48_archive_duplicate_member_rejected(self):
        p = self.root / (C.PREFIX + "20261026T120000Z.duplicate.tar.gz")
        name = p.name[:-7] + "/data.json"
        with tarfile.open(p, "w:gz") as t:
            for n in range(2):
                t.addfile(tarfile.TarInfo(name))
        with self.assertRaises(ValueError):
            experiment.extract_data(p, self.root / "duplicate")

    def test_49_wrong_metadata_mapping_rejected(self):
        snap = snapshot()
        snap.field_map = {"m_000000": "other"}
        with self.assertRaises(RuntimeError):
            M.admit(snap, C.lines(self.package / "queries.jsonl"))

    def test_50_transfer_checks_remote_after_scp(self):
        t = experiment.transfer_script(self.package)
        self.assertLess(t.index("Uploading archive"), t.index("REMOTE package checksum"))
        self.assertIn("UPLOAD VERIFIED", t)
        self.assertIn("ssh -t", t)
        self.assertIn(C.PREFIX, t)

    def test_51_host_preflight_failure_is_collectable_evidence(self):
        import pa_job

        campaign = self.root / "host-preflight-fail"
        campaign.mkdir()
        args = [
            "pa_job.py",
            str(self.package),
            "/bundle",
            "/prepared",
            str(campaign),
            "/workspace",
            "/sources",
            "apptainer",
        ]
        with (
            patch.object(pa_job.sys, "argv", args),
            patch.dict(pa_job.os.environ, {"SLURM_JOB_ID": "12345", "SLURM_ARRAY_TASK_ID": "0"}),
            patch.object(
                pa_job.os, "uname", return_value=SimpleNamespace(sysname="Linux", machine="x86_64")
            ),
            patch.object(pa_job.signal, "signal"),
            patch.object(pa_job.signal, "alarm"),
            patch.object(pa_job, "verify", side_effect=ValueError("injected preflight failure")),
            patch.object(pa_job.subprocess, "Popen") as proc,
        ):
            with self.assertRaises(RuntimeError):
                pa_job.main()
            proc.assert_not_called()
        host = C.read(campaign / "run/host-exit.json")
        self.assertEqual(host["exit_code"], 1)
        self.assertFalse(host["protected_sources_unchanged"])
        self.assertIn("preflight", C.read(campaign / "run/host-failure.json")["message"])

    def test_52_failed_terminal_campaign_collects_without_analysis(self):
        campaign = self.root / (C.PREFIX + "20261026T130000Z.failed")
        campaign.mkdir()
        record = dict(
            jobs={"block-0": "12345"},
            dispatch={"block-0": dict(status="submitted", job_id="12345")},
        )
        replies = [
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout="12345_0|FAILED|1:0|00:01:00\n", stderr=""),
        ]
        with (
            patch.object(control, "bound", return_value=(campaign, record)),
            patch.object(control.subprocess, "run", side_effect=replies) as run,
            patch("sys.stdout", io.StringIO()),
        ):
            control.collect(self.package)
        self.assertEqual(run.call_count, 2)
        self.assertTrue(Path(str(campaign) + ".tar.gz").exists())
        self.assertEqual(
            C.read(campaign / "analysis/failure-summary.json")["status"], "incomplete_or_failed"
        )

    def test_53_unknown_scheduler_never_collects_or_retries(self):
        campaign = self.root / (C.PREFIX + "20261026T130000Z.unknown")
        campaign.mkdir()
        record = dict(
            jobs={"block-0": "12345"},
            dispatch={"block-0": dict(status="submitted", job_id="12345")},
        )
        replies = [
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout="", stderr=""),
        ]
        with (
            patch.object(control, "bound", return_value=(campaign, record)),
            patch.object(control.subprocess, "run", side_effect=replies),
        ):
            with self.assertRaises(ValueError):
                control.collect(self.package)
        self.assertFalse(Path(str(campaign) + ".tar.gz").exists())

    def test_54_contract_has_only_the_new_design_and_cells(self):
        cfg = C.read(self.package / "experiment.json")
        self.assertEqual(cfg["cells"], C.CELLS)
        self.assertEqual(cfg["design_sha256"], C.sha(self.package / "DESIGN.md"))
        self.assertEqual(
            cfg["implementation_addendum_sha256"],
            C.sha(self.package / "IMPLEMENTATION-ADDENDUM.md"),
        )
        self.assertEqual(cfg["selected_context"], "votes108")
        self.assertNotIn("failed_original_campaign", cfg)
        self.assertNotIn("quality_operations", cfg)

    def test_55_impossible_sql_timer_rejected_even_if_rehashed(self):
        p = self.cases["good"] / "run/searches.jsonl"
        old = p.read_bytes()
        rows = C.lines(p)
        row = next(r for r in rows if "sql_ms" in r)
        row["sql_ms"] = row["outer_ms"] + 1
        p.write_text("".join(json.dumps(r) + "\n" for r in rows))
        finish_lock(p.parent, self.package)
        try:
            with self.assertRaisesRegex(ValueError, "SQL timer"):
                report.analyze(
                    self.cases["good"],
                    self.package,
                    self.root / "reject-sql-timer",
                    allow_synthetic=True,
                )
        finally:
            p.write_bytes(old)
            finish_lock(p.parent, self.package)

    def test_70_rehashed_admin_role_tamper_rejected(self):
        p = self.cases["good"] / "run/catalogs.jsonl"
        old = p.read_bytes()
        rows = C.lines(p)
        rows[0]["session_user"] = "torch_reader"
        p.write_text("".join(json.dumps(r) + "\n" for r in rows))
        finish_lock(p.parent, self.package)
        try:
            with self.assertRaisesRegex(ValueError, "phase/session"):
                report.analyze(
                    self.cases["good"], self.package, self.root / "bad-role", allow_synthetic=True
                )
        finally:
            p.write_bytes(old)
            finish_lock(p.parent, self.package)

    def test_71_rehashed_memory_bound_tamper_rejected(self):
        p = self.cases["good"] / "run/memory-preflight.json"
        old = p.read_bytes()
        value = C.read(p)
        value["servers"][0]["reader_work_mem_bytes"] = 4 * 1024**2
        p.write_bytes(C.encoded(value))
        finish_lock(p.parent, self.package)
        try:
            with self.assertRaisesRegex(ValueError, "Memory proof"):
                report.analyze(
                    self.cases["good"], self.package, self.root / "bad-memory", allow_synthetic=True
                )
        finally:
            p.write_bytes(old)
            finish_lock(p.parent, self.package)

    def test_72_rehashed_text_build_units_rejected(self):
        p = self.cases["good"] / "run/build.json"
        old = p.read_bytes()
        value = C.read(p)
        value["build_settings"] = ["65536", "0"]
        p.write_bytes(C.encoded(value))
        finish_lock(p.parent, self.package)
        try:
            with self.assertRaisesRegex(ValueError, "Numeric build"):
                report.analyze(
                    self.cases["good"], self.package, self.root / "bad-build", allow_synthetic=True
                )
        finally:
            p.write_bytes(old)
            finish_lock(p.parent, self.package)


CAPTURED_QUOTA = """Quota Information for dar579
Hostname: torch-login-b-1 at 2026-10-26 19:51:09

Filesystem   Environment       Backed up?   Allocation           Current Usage
Space        Variable          /Flushed?    Space / Files        Space(%) / Files(%)

/home        $HOME             YES/NO       50GB/30k             22GB(43.15%)/13987(46.00%)
/scratch     $SCRATCH          NO/YES       5.00TB/5.00M         205GB(4.09%)/139424(2.00%)
/archive     $ARCHIVE          YES/NO       2.00TB/20k           0GB(0.00%)/1(0.00%)
"""


class QuotaRepairChecks(unittest.TestCase):
    def test_56_captured_torch_display_conservative_bounds(self):
        q = resources.quota_report(CAPTURED_QUOTA)
        self.assertEqual(q["/home"]["space_available_lower"], 26988400000)
        self.assertEqual(q["/home"]["inodes_available_lower"], 15013)
        self.assertEqual(q["/scratch"]["space_available_lower"], 4784590000000)
        self.assertEqual(q["/scratch"]["inodes_available_lower"], 4850576)

    def test_57_file_abbreviation_cases_are_equivalent(self):
        expected = resources.quota_report(CAPTURED_QUOTA)
        self.assertEqual(resources.quota_report(CAPTURED_QUOTA.replace("30k", "30K")), expected)
        self.assertEqual(resources.quota_report(CAPTURED_QUOTA.replace("5.00M", "5.00m")), expected)

    def test_58_standard_terminal_colors_preserve_proof(self):
        colored = "\n".join("\x1b[1;32m" + s + "\x1b[0m" for s in CAPTURED_QUOTA.splitlines())
        self.assertEqual(resources.quota_report(colored), resources.quota_report(CAPTURED_QUOTA))

    def test_59_unknown_or_malformed_rows_still_fail_closed(self):
        for value in [
            CAPTURED_QUOTA.replace("30k", "30x"),
            CAPTURED_QUOTA.replace("22GB(43.15%)", "unknown"),
            CAPTURED_QUOTA.replace("/home", "\x1b[2J/home"),
            "\n".join(s for s in CAPTURED_QUOTA.splitlines() if not s.startswith("/home")),
            CAPTURED_QUOTA + "/home $HOME YES/NO 50GB/30k 22GB(43.15%)/13987(46.00%)\n",
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                resources.quota_report(value)

    def test_60_preflight_accepts_captured_quota_and_checks_both_resources(self):
        with (
            patch.object(resources.shutil, "which", return_value="/fake/myquota"),
            patch.object(
                resources.subprocess,
                "run",
                return_value=SimpleNamespace(stdout=CAPTURED_QUOTA, stderr=""),
            ),
            patch.object(resources, "footprint", return_value=(1024**3, 1000)),
            patch.object(
                resources.os,
                "statvfs",
                return_value=SimpleNamespace(f_bavail=10**12, f_frsize=4096, f_favail=10**8),
            ),
        ):
            result = resources.preflight("/prepared", "/scratch/user", "/home/user")
        self.assertEqual(result["myquota_stdout"], CAPTURED_QUOTA)
        for fs in ["/home", "/scratch"]:
            self.assertGreaterEqual(
                result["quota"][fs]["space_available_lower"], result["quota"][fs]["required_bytes"]
            )
            self.assertGreaterEqual(
                result["quota"][fs]["inodes_available_lower"],
                result["quota"][fs]["required_inodes"],
            )

    def test_61_recognized_display_does_not_bypass_insufficient_quota(self):
        with (
            patch.object(resources.shutil, "which", return_value="/fake/myquota"),
            patch.object(
                resources.subprocess,
                "run",
                return_value=SimpleNamespace(
                    stdout=CAPTURED_QUOTA.replace("30k", "20k"), stderr=""
                ),
            ),
            patch.object(resources, "footprint", return_value=(1024**3, 1000)),
            patch.object(
                resources.os,
                "statvfs",
                return_value=SimpleNamespace(f_bavail=10**12, f_frsize=4096, f_favail=10**8),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "Insufficient.*home"):
                resources.preflight("/prepared", "/scratch/user", "/home/user")


class SettingsChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="partial-settings-checks-")
        cls.root = Path(cls.temp.name)
        cls.package = fixture_package(cls.root / "fixture")
        cls.sources = cls.root / "results"
        prior = experiment.ROOT / "trials/torch-reviews-partial-ann-v1-quota-fix"
        shutil.copytree(
            prior / "torch-partial-ann-v1-quota-fix", cls.root / "torch-partial-ann-v1-quota-fix"
        )
        proof = C.read(cls.package / "FAILED-CAMPAIGN.json")
        name = proof["campaign"]
        shutil.copytree(prior / "returned" / name, cls.sources / name)
        for suffix in [".tar.gz", ".tar.gz.sha256"]:
            shutil.copyfile(prior / (name + suffix), cls.sources / (name + suffix))
        binding = dict(
            campaign=str(cls.sources / name),
            package_manifest_sha256=proof["package_manifest_sha256"],
        )
        C.save(cls.root / "torch-partial-ann-v1-quota-fix/submission-binding.json", binding)
        C.save(cls.sources / ".torch-partial-ann-v1-reservation.json", binding)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_62_captured_admin_is_valid_only_as_admin(self):
        value = C.read(self.package / "FAILED-ADMIN-CATALOG.json")
        metadata.validate_catalog(value, session_user="torch_owner")
        with self.assertRaisesRegex(ValueError, "work_mem"):
            metadata.validate_catalog(value)
        self.assertEqual(value["environment"], settings.ADMIN_ENVIRONMENT)

    def test_63_reader_16mib_is_retained_and_admin_4mib_not_borrowed(self):
        metadata.validate_catalog(catalog())
        for user, admin, bad in [("torch_reader", False, "4096"), ("torch_owner", True, "16384")]:
            value = catalog(admin=admin)
            value["environment"]["work_mem"] = bad
            with self.assertRaisesRegex(ValueError, "work_mem"):
                metadata.validate_catalog(value, session_user=user)

    def test_64_admin_other_settings_missing_or_drifted_rejected(self):
        for field in settings.ADMIN_ENVIRONMENT:
            value = catalog(admin=True)
            value["environment"][field] = "unapproved"
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                metadata.validate_catalog(value, session_user="torch_owner")
        value = catalog(admin=True)
        del value["environment"]["jit"]
        with self.assertRaises(ValueError):
            metadata.validate_catalog(value, session_user="torch_owner")

    def test_65_unknown_or_wrong_phase_roles_rejected(self):
        with self.assertRaises(ValueError):
            metadata.validate_catalog(catalog(), session_user="postgres")
        for user, phase in [
            ("torch_reader", "before_build"),
            ("torch_owner", "after_block_0"),
            ("torch_owner", "unknown"),
        ]:
            with self.assertRaises(ValueError):
                settings.validate_phase(user, phase)

    def test_66_runtime_memory_inspection_uses_reader_upper_bound_without_sets(self):
        class Admin:
            def __init__(self):
                self.calls = []

            def execute(self, statement, **kwargs):
                self.calls.append(statement)
                return self

            def fetchone(self):
                return (128 * 1024**2, 16, 4 * 1024**2, "64MB", "2")

        admins = {mode: Admin() for mode in C.CELLS}
        proof = settings.inspect_memory(admins)
        self.assertEqual(proof["conservative_bound_bytes"], 15300820992)
        self.assertEqual(settings.memory_proof(proof["servers"]), proof)
        self.assertTrue(all(a.calls == [settings.MEMORY_SQL] for a in admins.values()))
        for r in proof["servers"]:
            self.assertEqual(r["reader_work_mem_bytes"], r["work_mem_bound_bytes"])
            self.assertEqual(r["admin_work_mem_bytes"], 4 * 1024**2)

    def test_67_wrong_memory_types_or_admin_values_rejected(self):
        for value in [16 * 1024**2, "4194304", True]:
            with self.assertRaises(ValueError):
                settings.memory_record("native640", (128 * 1024**2, 16, value, "64MB", "2"))
        with self.assertRaises(ValueError):
            settings.memory_proof([])

    def test_68_runtime_build_controls_normalize_bytes_and_keep_set_scope(self):
        class Admin:
            def __init__(self):
                self.calls = []

            def execute(self, statement, params=None, **kwargs):
                self.calls.append(statement)
                return self

            def fetchone(self):
                return (64 * 1024**2, 0)

        conn = Admin()
        result = settings.build_controls(conn, SimpleNamespace(remaining=lambda: 600))
        self.assertEqual(result, [67108864, 0])
        self.assertEqual(conn.calls[-1], settings.BUILD_SQL)
        self.assertEqual(len(conn.calls), 4)
        self.assertFalse(any("SET work_mem" in s for s in conn.calls))

    def test_69_wrong_build_units_types_or_values_rejected(self):
        for row in [("64MB", "0"), ("65536", "0"), (67108864, True), (64, 0), (67108864, 1)]:
            with self.assertRaises(ValueError):
                settings.validate_build_settings(row)

    def test_73_failed_prerequisites_pass_with_preserved_spent_reservation(self):
        value = recovery.verify_failed(self.package, self.sources, self.root)
        self.assertTrue(value["terminal_failure_verified"])
        self.assertTrue((self.sources / ".torch-partial-ann-v1-reservation.json").exists())

    def test_74_failed_raw_or_archive_tamper_rejected(self):
        proof = C.read(self.package / "FAILED-CAMPAIGN.json")
        for p in [
            self.sources / proof["campaign"] / "run/cleanup.json",
            self.sources / (proof["campaign"] + ".tar.gz"),
        ]:
            old = p.read_bytes()
            try:
                p.write_bytes(old + b"\n")
                with self.assertRaises(ValueError):
                    recovery.verify_failed(self.package, self.sources, self.root)
            finally:
                p.write_bytes(old)

    def test_75_prior_binding_or_spent_reservation_cannot_be_replaced(self):
        for p in [
            self.root / "torch-partial-ann-v1-quota-fix/submission-binding.json",
            self.sources / ".torch-partial-ann-v1-reservation.json",
        ]:
            old = p.read_bytes()
            try:
                p.write_bytes(C.encoded(dict(campaign="wrong")))
                with self.assertRaises(ValueError):
                    recovery.verify_failed(self.package, self.sources, self.root)
            finally:
                p.write_bytes(old)


if __name__ == "__main__":
    unittest.main()
