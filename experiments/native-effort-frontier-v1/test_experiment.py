"""Local protocol simulations only; no database, ANN, provider or model run."""

import ast
import copy
import io
import itertools
import json
import shutil
import sys
import tarfile
import tempfile
import unittest
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import ef_common as common
import ef_interface as interface
import ef_measure as measure
import ef_report as report
import experiment
from ef_control import dispatch, reserve

sys.path[:0] = [str(experiment.SOURCE / "frozen"), str(experiment.SOURCE / "frozen/vendor")]
from no_models import enforce  # noqa: E402

enforce()
from execution import Budget  # noqa: E402
from fannagent_pgvector.profiles import PROFILE  # noqa: E402

from fannagent.evaluation import score  # noqa: E402
from fannagent.snapshot import Snapshot  # noqa: E402

SOURCE_SETTINGS = common.read(
    experiment.ROOT / "trials/torch-reviews-first/inputs/local-identity.json"
)["settings"]
SOURCE_METADATA = common.read(
    experiment.ROOT / "trials/torch-reviews-first/inputs/local-identity.json"
)["binding"]["metadata"]


class SqlFailure(Exception):
    sqlstate = "22012"


class FakeConnection:
    def __init__(self):
        self.closed = False
        self.values = {}
        self.rows = []

    @contextmanager
    def transaction(self):
        old = self.values.copy()
        try:
            yield
        finally:
            self.values = old

    def execute(self, statement, params=None):
        text = str(statement)
        if "set_config" in text:
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
            self.rows = [([{"Plan": {"Node Type": "Index Scan", "Index Name": "reviews_hnsw"}}],)]
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


@lru_cache(maxsize=1)
def strict_snapshot():
    return Snapshot(
        [{"source_id": 0, "vector": [1.0, *([0.0] * 767)], "metadata": {"total_votes": 1000}}],
        [{"name": "total_votes", "type": "integer", "nullable": False}],
    )


class FakeBase:
    pins = None
    instances = []

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

        return sql.SQL("SELECT fake"), []

    def execute_probe(self, query, *, mode, **kwargs):
        assert mode == "native" and not kwargs
        self._connect()
        self.calls += 1
        if self.pins is None:
            ids, distances = list(range(10)), [i / 20 for i in range(10)]
        else:
            v = self.pins[query["id"]]["original640"]
            ids, distances = v["ids"], v["distances"]
        return SimpleNamespace(ids=ids, distances=distances, latency_ms=0.000001, metadata={})

    def exact_reference(self, query):
        pin = self.pins[query["id"]]
        return SimpleNamespace(
            strictly_better=frozenset(pin["truth_strict"]),
            boundary_ties=frozenset(pin["truth_ties"]),
            effective_k=pin["truth_k"],
            eligible_ids=frozenset(pin["original640"]["ids"])
            | frozenset(pin["truth_strict"])
            | frozenset(pin["truth_ties"]),
        )


def create(level=None):
    return (FakeBase if level is None else interface.bound_class(FakeBase, level))()


def query():
    return {
        "schema_version": 2,
        "id": "misleading-votes108",
        "vector": [1.0, *([0.0] * 767)],
        "k": 10,
        "filter": None,
    }


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        FakeBase.pins, FakeBase.instances = None, []

    def test_binding_view_origin_and_same_native_method(self):
        pool = interface.Pool(create)
        try:
            a, b = pool._readers[320], pool._readers[640]
            self.assertEqual(a.state["source_manifest"]["settings"], SOURCE_SETTINGS)
            self.assertEqual(a._binding["settings"]["hnsw.ef_search"], "320")
            self.assertEqual(b._binding["settings"]["hnsw.ef_search"], "640")
            self.assertIs(type(a).execute_probe, FakeBase.execute_probe)
            self.assertIs(a._snapshot, b._snapshot)
            pool.audit()
        finally:
            pool.close()
        self.assertTrue(all(r.conn is None for r in pool._readers.values()))

    def test_actual_predicate_not_id_and_conservative_fallback(self):
        pool = interface.Pool(create)
        budget = Budget(20)
        try:
            q = query()
            _, route = pool.query(interface.envelope(q, 320), budget)
            self.assertEqual(route["context"], "unfiltered")
            for threshold in (32, 108, 0, 31):
                q["filter"] = {"field": "m_000000", "op": "gte", "value": threshold}
                _, route = pool.query(interface.envelope(q, 320), budget)
                self.assertEqual(route["effective_effort"], 320 if threshold in (32, 108) else 640)
            q["filter"], q["k"] = None, 9
            _, route = pool.query(interface.envelope(q, 320), budget)
            self.assertTrue(route["fallback_to640"])
        finally:
            pool.close()

    def test_allowlist_and_strict_query_rejection_before_search(self):
        for level in (True, False, 319, 641, 320.0, "320", None):
            pool = interface.Pool(create)
            budget = Budget(1)
            with self.assertRaises(ValueError):
                pool.query(interface.envelope(query(), level), budget)
            self.assertEqual(budget.calls, 0)
            self.assertTrue(pool._closed)
        for change in (
            {"effort": 320},
            {"vector": [float("nan")] * 768},
            {"filter": {"field": "bogus", "op": "gte", "value": 32}},
        ):
            pool = interface.Pool(create)
            q = {**query(), **change}
            with self.assertRaises(Exception):
                pool.query(interface.envelope(q, 320), Budget(1))
            self.assertTrue(pool._closed)

    def test_connection_binding_and_origin_mutation_poison_without_retry(self):
        for mutate in (
            lambda p: setattr(p._connections[320], "closed", True),
            lambda p: setattr(p._readers[640], "conn", FakeConnection()),
            lambda p: p._readers[320]._binding["settings"].update({"hnsw.ef_search": "640"}),
            lambda p: p._readers[640].state["source_manifest"]["settings"].update({"jit": "off"}),
        ):
            pool = interface.Pool(create)
            count = len(FakeBase.instances)
            mutate(pool)
            with self.assertRaises(RuntimeError):
                pool.query(interface.envelope(query(), 320), Budget(1))
            self.assertEqual(len(FakeBase.instances), count)
            self.assertTrue(pool._closed)

    def test_partial_admission_and_execution_error_close_both_readers(self):
        admitted = []

        def broken(level):
            if level == 640:
                raise RuntimeError("second admission failed")
            r = create(level)
            admitted.append(r)
            return r

        with self.assertRaises(RuntimeError):
            interface.Pool(broken)
        self.assertIsNone(admitted[0].conn)
        pool = interface.Pool(create)
        with patch.object(
            pool._readers[320], "execute_probe", side_effect=RuntimeError("query failed")
        ):
            with self.assertRaises(RuntimeError):
                pool.query(interface.envelope(query(), 320), Budget(1))
        self.assertTrue(pool._closed)

    def test_actual_settings_mismatch_rejected(self):
        pool = interface.Pool(create)
        try:
            pool._connections[320].values["hnsw.ef_search"] = "640"
            with self.assertRaises(RuntimeError):
                pool.audit()
        finally:
            pool.close()

    def test_native_execution_method_not_redefined(self):
        tree = ast.parse(Path(interface.__file__).read_text())
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertFalse(
            names & {"execute_probe", "_execute_probe", "_statement", "_exact_reference"}
        )

    def test_original_and_source_are_direct_backends_without_query_reporting_wrapper(self):
        for cell in ("original640", "source"):
            reader = interface.session(create, cell)
            try:
                self.assertIsInstance(reader, FakeBase)
                self.assertIs(type(reader).execute_probe, FakeBase.execute_probe)
                self.assertNotIsInstance(reader, interface.Pool)
                with self.assertRaisesRegex(ValueError, "directly"):
                    interface.execute(reader, cell, query(), Budget(1))
                audit = interface.audit_session(reader, cell)
                self.assertEqual(audit["plain"]["origin"]["settings"], SOURCE_SETTINGS)
            finally:
                reader.close()


class ProtocolTests(unittest.TestCase):
    def test_complete_schedule_balance_and_search_arithmetic(self):
        items = common.lines(experiment.SOURCE / "frozen/inputs/queries.jsonl")
        common.inventory(items)
        for item in items:
            a, b = (
                list(measure.schedule(item["query"]["id"], 0)),
                list(measure.schedule(item["query"]["id"], 1)),
            )
            self.assertEqual(len(a), 16)
            self.assertEqual([r["cell"] for r in a[::4]], [r["cell"] for r in b[::4]][::-1])
            for cell in common.CELLS:
                aa = [r["label"] for r in a if r["cell"] == cell]
                bb = [r["label"] for r in b if r["cell"] == cell]
                self.assertIn(aa, (["a", "b", "b", "a"], ["b", "a", "a", "b"]))
                self.assertEqual(aa, [{"a": "b", "b": "a"}[v] for v in bb])
        self.assertEqual(36 + 600 * (4 + 16 * (2 + 5)), common.COUNTS["searches_per_block"])
        self.assertEqual(sum(common.OPERATIONS.values()), 69636)

    def test_full_mock_driver_accounting_timers_and_native_qualification(self):
        """Execute the real full600-case schedule against stubs, retaining sample rows."""
        raw = (
            experiment.SOURCE.parent
            / "returned"
            / common.P2C_CAMPAIGN
            / "blocks/block-0/references.jsonl"
        )
        refs = common.lines(raw)
        pins = {
            r["query_id"]: {
                **{k: r[k] for k in ("truth_strict", "truth_ties", "truth_k")},
                "original640": {
                    "ids": r["native_ids"],
                    "distances": r["native_distances"],
                    "recall": r["native_recall"],
                    "valid": True,
                    "returned_count": 10,
                    "duplicate_count": 0,
                    "predicate_violation_count": 0,
                },
            }
            for r in refs
        }
        FakeBase.pins, FakeBase.instances = pins, []
        captured, all_counts = defaultdict_list(), {}
        original_read = measure.read

        def read(path):
            return pins if Path(path).name == "baseline-results.json" else original_read(path)

        def write(handle, row):
            name = Path(handle.name).stem
            all_counts[name] = all_counts.get(name, 0) + 1
            if len(captured[name]) < 32:
                captured[name].append(copy.deepcopy(row))

        reference, source = create(640), create()
        reference._connect()
        source._connect()
        try:
            with (
                tempfile.TemporaryDirectory() as tmp,
                patch.object(measure, "read", side_effect=read),
                patch.object(measure, "write", side_effect=write),
            ):
                budget = Budget(69636, seconds=6600)
                counts = measure.measure(
                    create,
                    reference,
                    source,
                    score,
                    budget,
                    experiment.SOURCE,
                    Path(tmp),
                    0,
                    lambda *a, **k: None,
                )
                self.assertEqual(budget.calls, 69636)
                self.assertEqual(dict(budget.operations), common.OPERATIONS)
                self.assertEqual(counts["slots"], 9600)
                self.assertEqual(
                    all_counts,
                    {"references": 600, "executions": 48000, "slots": 9600, "conditioning": 19200},
                )
                qualification = common.read(Path(tmp) / "qualification.json")
                self.assertEqual(qualification["backend_searches"], 36)
                for row in captured["executions"]:
                    report.near(row["outer_ms"], row["query_outer_ms"] + row["preparation_ms"])
                    self.assertEqual(row["retained"], row["repetition"] != 1)
                for slot in captured["slots"]:
                    n = slot["slot_index"]
                    first = captured["executions"][n * 5] if n < 6 else None
                    if first is not None and first["query_id"] == slot["query_id"]:
                        self.assertEqual(first["preparation_ms"], slot["preparation_ms"])
                    self.assertLessEqual(slot["conditioning_end_ns"], slot["preparation_start_ns"])
        finally:
            source.close()
            reference.close()
            FakeBase.pins = None

    def test_two_block_raw_roundtrip_and_rehashed_tamper_rejection(self):
        """Real serialization/verifier/statistics, synthetic readers and deterministic clock."""
        import pyarrow.parquet as pq

        prior = experiment.SOURCE.parent / "returned" / common.P2C_CAMPAIGN
        pins = {}
        for r in common.lines(prior / "blocks/block-0/references.jsonl"):
            pins[r["query_id"]] = {
                **{k: r[k] for k in ("truth_strict", "truth_ties", "truth_k")},
                "original640": {
                    "ids": r["native_ids"],
                    "distances": r["native_distances"],
                    "recall": r["native_recall"],
                    "valid": True,
                    "returned_count": 10,
                    "duplicate_count": 0,
                    "predicate_violation_count": 0,
                },
            }
        metadata = pq.read_table(
            experiment.ROOT / "trials/torch-reviews-first/inputs/reviews.parquet",
            columns=["source_id", "metadata"],
        ).to_pylist()
        metadata.sort(key=lambda r: r["source_id"])
        eligibility = {
            "source_ids": [r["source_id"] for r in metadata],
            "votes": [r["metadata"]["total_votes"] for r in metadata],
        }
        cfg = {**common.protocol(), "source_settings": SOURCE_SETTINGS}
        FakeBase.pins, FakeBase.instances = pins, []
        clock = itertools.count(1_000_000, 1_000_000)
        with tempfile.TemporaryDirectory(prefix="b1b-mock-replay-") as tmp:
            root = Path(tmp)
            package, campaign = root / "package", root / "reviews-native-effort-v1-mock"
            (package / "frozen/inputs").mkdir(parents=True)
            campaign.mkdir()
            for name in ("experiment.json", "source-index.json", "inputs/queries.jsonl"):
                shutil.copyfile(experiment.SOURCE / "frozen" / name, package / "frozen" / name)
            for name, value in (
                ("manifest.json", {"mock": True}),
                ("baseline-results.json", pins),
                ("eligibility.json", eligibility),
                ("origin-source.json", create().state["source_manifest"]),
            ):
                common.save(package / name, value)
            preserved = {"mock_source": "unchanged"}
            common.save(campaign / "protected-source-before.json", preserved)
            source_cfg = common.read(package / "frozen/experiment.json")
            for block in range(2):
                out = campaign / "blocks" / ("block-" + str(block))
                out.mkdir(parents=True)
                make_reader = interface.factory(FakeBase, None, None, strict_snapshot())
                source, reference = FakeBase(), make_reader(640)
                source._connect()
                reference._connect()
                try:
                    with patch.object(
                        measure.time, "perf_counter_ns", side_effect=lambda: next(clock)
                    ):
                        budget = Budget(69636)
                        counts = measure.measure(
                            make_reader,
                            reference,
                            source,
                            score,
                            budget,
                            package,
                            out,
                            block,
                            lambda *a, **k: None,
                        )
                    self.assertEqual(budget.calls, 69636)
                    self.assertEqual(make_reader.created + 1, 14416)
                    common.save(
                        out / "status.json",
                        {
                            "status": "complete",
                            "block": block,
                            "provider_calls": 0,
                            "confirmation_queries": 0,
                            "new_fits": 0,
                            "cases": 600,
                            "vectors": 200,
                            "backend_searches": budget.calls,
                            "operations": dict(budget.operations),
                            "control_installations": 0,
                            "index_and_module_after_verified": True,
                            "reader_connections": 14416,
                            "elapsed_seconds": 1.0,
                            **counts,
                        },
                    )
                    common.save(out / "job-exit.json", {"exit_code": 0})
                    common.save(
                        out / "host-exit.json",
                        {"exit_code": 0, "protected_sources_unchanged": True},
                    )
                    common.save(out / "protected-source-before.json", preserved)
                    common.save(out / "protected-source-after.json", preserved)
                    common.save(
                        out / "database-identity.json",
                        common.read(package / "frozen/source-index.json"),
                    )
                    common.save(
                        out / "runtime-identity.json",
                        {
                            "module_sha256": source_cfg["module_sha256"],
                            "runtime_profile_hash": PROFILE.fingerprint,
                            "registry_hash": PROFILE.native_registry_hash,
                            "package_manifest_sha256": common.sha(package / "manifest.json"),
                            "image_sha256": source_cfg["image_sha256"],
                        },
                    )
                    common.save(
                        out / "shared-initialization.json",
                        {
                            "origin_manifest": source.state["source_manifest"],
                            "eligibility_sha256": common.sha(package / "eligibility.json"),
                            "study_reference_effort": 640,
                            "source_effort": 320,
                        },
                    )
                    common.save(out / "host.json", {"mock": True})
                    common.save(
                        out / "LOCK.json",
                        {
                            "package_manifest_sha256": common.sha(package / "manifest.json"),
                            "files_sha256": {
                                p.name: common.sha(p)
                                for p in out.iterdir()
                                if p.is_file() and p.name != "LOCK.json"
                            },
                        },
                    )
                finally:
                    source.close()
                    reference.close()
            # Only the artificial package identity is stubbed. All raw lock,
            # schedule, output, score, settings, timer and statistics checks run.
            with patch.object(report, "verify", return_value=cfg):
                result = report.analyze(campaign, package, root / "analysis")
            self.assertEqual(result["gate"]["status"], "closed_negative_bounded_frontier")
            self.assertTrue(all(r["status"] == "pass" for r in result["gate"]["aa"].values()))
            self.assertEqual(result["counts"]["searches_total"], 139272)
            # Rehash an altered raw timer: a hash match must not bypass semantics.
            folder = campaign / "blocks/block-0"
            path = folder / "executions.jsonl"
            rows = path.read_text().splitlines()
            first = json.loads(rows[0])
            first["outer_ms"] += 1.0
            rows[0] = json.dumps(first)
            path.write_text("\n".join(rows) + "\n")
            lock = common.read(folder / "LOCK.json")
            lock["files_sha256"]["executions.jsonl"] = common.sha(path)
            common.replace(folder / "LOCK.json", lock)
            items = common.lines(package / "frozen/inputs/queries.jsonl")
            with self.assertRaisesRegex(ValueError, "timer arithmetic"):
                report.validate_block(folder, package, cfg, 0, items, eligibility, pins)
        FakeBase.pins = None

    def test_vector_bootstrap_no_pseudoreplication(self):
        rows = [
            {
                "group": str(g),
                "treatment_ms": 1.0,
                "baseline_ms": 2.0,
                "recall_delta": 0.0,
                "sql_gap_ms": -0.5,
                "reference_recall": 0.98,
                "treatment_recall": 0.98,
                "all_valid": True,
                "block": b,
            }
            for g in range(200)
            for b in range(2)
            for _ in range(4)
        ]
        summary = report.summary(rows)
        self.assertEqual(summary["independent_vectors"], 200)
        self.assertEqual(summary["gap_ci95"], [-1.0, -1.0])
        self.assertEqual(summary["recall_delta_ci95"], [0.0, 0.0])

    def test_gates_reject_quality_missing_controls_and_precision(self):
        stat = {"gap_ci95": [-0.01, 0.01], "log_ratio_ci95": [-0.001, 0.001]}
        aa = {
            cell: {
                r: {f: copy.deepcopy(stat) for f in ["overall", *common.FILTERS]}
                for r in common.REGIMES
            }
            for cell in common.CELLS
        }
        overhead = {"gap_ci95": [0, 0.02], "log_ratio_ci95": [0, 0.002]}
        lower = {
            "gap_ci95": [-1, -0.9],
            "log_ratio_ci95": [-0.3, -0.2],
            "all_valid": True,
            "reference_recall": 0.99,
            "recall_delta_ci95": [0, 0],
            "block_gap_ms": {"0": -1, "1": -1},
        }
        comparisons = {
            "wrapped640_vs_original640": {
                r: {f: copy.deepcopy(overhead) for f in common.FILTERS} for r in common.REGIMES
            },
            "wrapped320_vs_original640": {
                r: {f: copy.deepcopy(lower) for f in common.FILTERS} for r in common.REGIMES
            },
        }
        self.assertEqual(len(report.gates(aa, comparisons)["supported_context_regimes"]), 6)
        for r in common.REGIMES:
            for f in common.FILTERS:
                comparisons["wrapped320_vs_original640"][r][f]["recall_delta_ci95"] = [
                    -0.006,
                    -0.005,
                ]
        self.assertEqual(
            report.gates(aa, comparisons)["status"], "closed_negative_bounded_frontier"
        )
        aa["source"]["activation"]["votes108"]["gap_ci95"] = [-0.2, 0.2]
        self.assertEqual(report.gates(aa, comparisons)["status"], "measurement_inconclusive")
        del aa["source"]
        with self.assertRaises(ValueError):
            report.gates(aa, comparisons)

    def test_independent_membership_recall_and_distance_tamper(self):
        truth = {"truth_strict": list(range(9)), "truth_ties": [9], "truth_k": 10}
        value = {
            "ids": list(range(10)),
            "distances": [i / 20 for i in range(10)],
            "recall": 1.0,
            "valid": True,
            "returned_count": 10,
            "duplicate_count": 0,
            "predicate_violation_count": 0,
        }
        report.score_result(value, truth, query(), {"votes": [100] * 10})
        for key, change in (("recall", 0.9), ("ids", [0] * 10), ("distances", [float("nan")] * 10)):
            with self.assertRaises(ValueError):
                report.score_result({**value, key: change}, truth, query(), {"votes": [100] * 10})
        filtered = {**query(), "filter": {"field": "m_000000", "op": "gte", "value": 108}}
        with self.assertRaises(ValueError):
            report.score_result(value, truth, filtered, {"votes": [100] * 10})

    def test_dispatch_unknown_not_retried_and_reservation_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text("{}")
            reserve(root, root, root / "campaign")
            with self.assertRaises(FileExistsError):
                reserve(root, root, root / "other")
            record = {
                "dispatch": {},
                "jobs": {},
                "account": "torch_pr_test",
                "bundle": "/b",
                "prepared": "/p",
                "campaign": "/c",
                "workspace": "/w",
                "sources": "/s",
                "apptainer": "/a",
            }
            with patch(
                "ef_control.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stdout="unknown", stderr=""),
            ) as run:
                with self.assertRaises(RuntimeError):
                    dispatch(root, root, record, 0)
                self.assertEqual(record["dispatch"]["block-0"]["status"], "unknown")
                with self.assertRaises(ValueError):
                    dispatch(root, root, record, 0)
                self.assertEqual(run.call_count, 1)

    def test_archive_traversal_symlink_duplicate_rejected(self):
        for kind in ("traversal", "symlink", "duplicate"):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                archive = root / (common.PREFIX + "fake.tar.gz")
                name = archive.name[:-7]
                with tarfile.open(archive, "w:gz") as tar:
                    item = tarfile.TarInfo(
                        name + ("/../escape" if kind == "traversal" else "/data")
                    )
                    if kind == "symlink":
                        item.type, item.linkname = tarfile.SYMTYPE, "/tmp/escape"
                        tar.addfile(item)
                    else:
                        item.size = 2
                        tar.addfile(item, io.BytesIO(b"{}"))
                        if kind == "duplicate":
                            tar.addfile(item, io.BytesIO(b"{}"))
                with self.assertRaises(ValueError):
                    experiment.extract_data(archive, root / "returned")
                self.assertFalse((root / "escape").exists())

    def test_remote_local_parity_rejects_nonfinite_or_discrete_change(self):
        experiment.parity({"x": [1, 0.1]}, {"x": [1, 0.1 + 1e-13]})
        for a, b in ((1, True), (0.1, float("nan")), ({"x": 1}, {"x": 2})):
            with self.assertRaises(ValueError):
                experiment.parity(a, b)


def defaultdict_list():
    from collections import defaultdict

    return defaultdict(list)


if __name__ == "__main__":
    unittest.main()
