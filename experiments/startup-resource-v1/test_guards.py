import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pc_common as C
import pc_trace as T
from pc_snapshot import validate_snapshot
from sr_interface import startup_class
from test_fixtures import frozen_backend, rewrite, snapshot


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.b = C.Budget(clock=lambda: 0)
        self.b.enter("restore_identity")
        self.trace = T.Trace(self.b, lambda *a: None)

    def blocked(self, text, params=None):
        target = Mock()
        target.connection = None
        with self.assertRaises(RuntimeError):
            self.trace.call(target, text, params, {})
        target.execute.assert_not_called()

    def test_ann_sql_blocked(self):
        self.blocked("SELECT id FROM public.reviews ORDER BY embedding <=> %s LIMIT 10")

    def test_exact_sql_blocked(self):
        self.blocked("SELECT id FROM public.reviews ORDER BY embedding <=> %s")

    def test_explain_blocked(self):
        self.blocked("EXPLAIN SELECT * FROM public.reviews")

    def test_ddl_blocked(self):
        self.blocked("CREATE INDEX another ON reviews(id)")

    def test_unknown_select_blocked(self):
        self.blocked("SELECT 1")

    def test_multi_statement_blocked(self):
        self.blocked(T.SNAPSHOT_SQL + "; SELECT 1")

    def test_settings_change_blocked(self):
        self.blocked(T.SET_SQL, ("hnsw.ef_search", "1280", False))

    def test_local_setting_change_blocked(self):
        self.blocked(T.SET_SQL, ("hnsw.ef_search", "640", True))

    def test_timeout_change_blocked(self):
        self.blocked(T.TIMEOUT_SQL, ("99999", False))

    def test_new_target_binding_blocked(self):
        self.blocked(T.BIND_SQL, ('"public"."reviews"', "id", "embedding", '"public"."other"'))

    def test_source_snapshot_allowed(self):
        target = Mock()
        target.connection = None
        self.trace.call(target, T.SNAPSHOT_SQL, None, {})
        target.execute.assert_called_once()
        self.assertEqual(self.trace.scans["snapshot"], 1)

    def test_second_snapshot_rejected(self):
        target = Mock()
        target.connection = None
        self.trace.call(target, T.SNAPSHOT_SQL, None, {})
        with self.assertRaises(RuntimeError):
            self.trace.call(target, T.SNAPSHOT_SQL, None, {})
        self.assertEqual(target.execute.call_count, 1)

    def test_four_data_scans_only(self):
        target = Mock()
        target.connection = None
        for _ in range(4):
            self.trace.call(target, T.DATA_SQL, None, {})
        with self.assertRaises(RuntimeError):
            self.trace.call(target, T.DATA_SQL, None, {})
        self.assertEqual(target.execute.call_count, 4)

    def test_operation_budget_always_zero(self):
        for operation in ["measurement", "reference_exact", "unknown"]:
            with self.subTest(operation=operation), self.assertRaises(RuntimeError):
                self.b.reserve(operation)
        self.assertEqual(self.b.calls, 0)

    def test_expected_search_context_rejected_even_for_scan(self):
        with T.category("startup", T.SNAPSHOT_SQL):
            self.blocked(T.SNAPSHOT_SQL)

    def test_truth_helper_budget_zero(self):
        with self.assertRaises(RuntimeError):
            self.b.sql_reserve("truth_helper")

    def test_stage_deadline_enforced(self):
        t = [0]
        budget = C.Budget(clock=lambda: t[0])
        budget.enter("restore_identity")
        t[0] = 1501
        with self.assertRaises(RuntimeError):
            budget.check()

    def test_cleanup_reserve_enforced(self):
        t = [0]
        budget = C.Budget(clock=lambda: t[0])
        t[0] = 2401
        with self.assertRaises(RuntimeError):
            budget.enter("epoch0")
        budget.enter("final_cleanup")
        budget.check()

    def test_repeated_stage_rejected(self):
        with self.assertRaises(RuntimeError):
            self.b.enter("restore_identity")

    def test_actual_native_entry_points_blocked(self):
        _, base = frozen_backend()
        cls = startup_class(base, "native640", C.CONTRACT["targets"]["native640"])
        obj = cls.__new__(cls)
        for method in [
            "_statement",
            "execute_probe",
            "exact_reference",
            "_exact_reference",
            "_qualify",
            "execute",
            "prepare",
        ]:
            with self.subTest(method=method), self.assertRaisesRegex(RuntimeError, "prohibited"):
                getattr(obj, method)({})


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        self.s = snapshot()
        (self.p / "eligibility.json").write_bytes(
            C.encoded(dict(source_ids=self.s.source_ids, votes=[108] * 40))
        )
        rewrite(self.p / "experiment.json", dict(snapshot_identity=self.s.identity))

    def test_real_snapshot_passes(self):
        self.assertEqual(validate_snapshot(self.s, self.p)["rows"], 40)

    def test_previous_extra_field_hash_fails(self):
        self.assertNotEqual(
            C.digest(
                dict(field_map=self.s.field_map, source_ids=self.s.source_ids, votes=[108] * 40)
            ),
            C.sha(self.p / "eligibility.json"),
        )

    def test_field_map_changed(self):
        self.s.field_map["m_000000"] = "bad"
        with self.assertRaises(RuntimeError):
            validate_snapshot(self.s, self.p)

    def test_ids_changed(self):
        self.s.source_ids[0] = -1
        with self.assertRaises(RuntimeError):
            validate_snapshot(self.s, self.p)

    def test_votes_changed(self):
        self.s.rows[0]["metadata"]["total_votes"] = 1
        with self.assertRaises(RuntimeError):
            validate_snapshot(self.s, self.p)

    def test_snapshot_identity_changed(self):
        self.s.identity = "bad"
        with self.assertRaises(RuntimeError):
            validate_snapshot(self.s, self.p)

    def test_full_pinned_eligibility_without_vectors(self):
        import experiment as E

        pinned = C.read(E.SOURCE / "eligibility.json")

        class Rows:
            def __len__(self):
                return len(pinned["votes"])

            def __iter__(self):
                return (dict(metadata=dict(total_votes=v)) for v in pinned["votes"])

        s = SimpleNamespace(
            source_ids=pinned["source_ids"],
            rows=Rows(),
            field_map={"m_000000": "total_votes"},
            identity=C.read(E.SOURCE / "experiment.json")["snapshot_identity"],
        )
        self.assertEqual(validate_snapshot(s, E.SOURCE)["rows"], 247286)


class RestoreRegressionTests(unittest.TestCase):
    def setUp(self):
        import pc_restore
        from test_fixtures import source_cell

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.src = self.root / "source"
        source_cell(self.src)
        self.dst = self.root / "work"
        self.restore = pc_restore

    def test_missing_sidecar_stops_before_copy(self):
        (self.src / "database-identity.json").unlink()
        with self.assertRaises(FileNotFoundError):
            self.restore.clone(self.src, self.dst)
        self.assertFalse(self.dst.exists())

    def test_changed_sidecar_stops_before_copy(self):
        (self.src / "database-identity.json").write_text("{}")
        with self.assertRaises(ValueError):
            self.restore.clone(self.src, self.dst)
        self.assertFalse(self.dst.exists())

    def test_symlink_sidecar_stops_before_copy(self):
        p = self.src / "database-identity.json"
        original = self.root / "identity"
        p.rename(original)
        p.symlink_to(original)
        with self.assertRaises(ValueError):
            self.restore.clone(self.src, self.dst)
        self.assertFalse(self.dst.exists())

    def test_valid_copy_reaches_actual_constructor(self):
        from test_fixtures import frozen_backend

        with patch.dict(__import__("os").environ, SLURM_JOB_ID="fixture"):
            proof = self.restore.clone(self.src, self.dst)
        _, base = frozen_backend()
        backend = startup_class(base, "native640", C.CONTRACT["targets"]["native640"])(
            __import__("experiment").ROOT / "trials/torch-reviews-first", self.dst
        )
        self.assertEqual(proof["database_identity_sha256"], self.restore.IDENTITY_SHA)
        self.assertIsNone(backend.conn)

    def test_copy_inode_independence(self):
        with patch.dict(__import__("os").environ, SLURM_JOB_ID="fixture"):
            self.restore.clone(self.src, self.dst)
        self.assertNotEqual(
            (self.src / "pgdata/x").stat().st_ino, (self.dst / "pgdata/x").stat().st_ino
        )
