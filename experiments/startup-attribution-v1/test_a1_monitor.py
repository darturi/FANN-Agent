"""Unmodified frozen producer and constructor, <=64 rows x768 only."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pc_common as C
from sa_monitor import SnapshotMonitor, idle, preflight
from sa_observe import Observation

BASE = Path(
    "/Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-startup-resource-stream-v1/torch-startup-resource-stream-v1"
)
BASE = C.HERE if (C.HERE / "frozen").is_dir() else BASE
C.bootstrap(BASE)
sys.path.insert(0, str(C.HERE))
from fannagent_pgvector.backend import NativeBackend  # noqa: E402
from psycopg._cursor_base import BaseCursor  # noqa: E402

from fannagent.snapshot import Snapshot  # noqa: E402

FIELDS = [{"name": "total_votes", "type": "integer", "nullable": False}]
VECTOR = [1.0] + [0.0] * 767


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.obs = Observation(self.tmp.name, "runtime", lambda o: {"fixture": True})
        self.addCleanup(lambda: self.obs.finish(False))

    def produce(self, n=64, probe_error=None, duplicate=False):
        monitor = SnapshotMonitor(NativeBackend.snapshot, Snapshot.__init__, self.obs)
        row_count = n

        class Cursor:
            _closed = False

            def execute(self, statement):
                return self

            def __iter__(self):
                return iter(
                    (0 if duplicate else i, json.dumps(VECTOR), 108) for i in range(row_count)
                )

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return monitor.cursor_close(self, BaseCursor._close)

            def _reset(self, **kwargs):
                pass

        obj = NativeBackend.__new__(NativeBackend)
        obj._snapshot = None
        raw = Cursor()
        obj._connect = lambda: SimpleNamespace(cursor=lambda: raw)
        obj.store = SimpleNamespace(get=lambda _: {"metadata": FIELDS})
        obj.config = SimpleNamespace(
            target=SimpleNamespace(
                id_column="id", vector_column="embedding", schema_name="public", resource="reviews"
            )
        )
        before = NativeBackend.snapshot.__code__, Snapshot.__init__.__code__
        if probe_error:
            self.obs.probe = probe_error
        try:
            with monitor:
                result = obj.snapshot()
        finally:
            idle()
            self.assertEqual(before, (NativeBackend.snapshot.__code__, Snapshot.__init__.__code__))
        return result, monitor, raw

    def test_actual_original_64_rows_and_10_line_points(self):
        result, monitor, cursor = self.produce()
        self.assertEqual(len(result.rows), 64)
        self.assertEqual(result.data.vectors.shape, (64, 768))
        self.assertEqual(len(monitor.seen), 10)
        self.assertEqual(len(self.obs.seen), 12)
        self.assertLessEqual(self.obs.lines, 512)
        self.assertTrue(cursor._closed)
        self.assertIsNone(monitor.cursor)
        self.assertFalse(monitor.active)

    def test_original_duplicate_id_rejection_restores(self):
        with self.assertRaises(Exception):
            self.produce(duplicate=True)
        idle()

    def test_checkpoint_baseexception_restores(self):
        def fail(obs):
            raise KeyboardInterrupt("injected")

        with self.assertRaises(KeyboardInterrupt):
            self.produce(probe_error=fail)
        idle()

    def test_occupied_tool_rejected_without_stealing(self):
        sys.monitoring.use_tool_id(1, "other")
        try:
            with self.assertRaises(RuntimeError):
                preflight(self.obs)
            self.assertEqual(sys.monitoring.get_tool(1), "other")
        finally:
            sys.monitoring.free_tool_id(1)

    def test_literal_preflight_restores_all_masks(self):
        result = preflight(self.obs)
        self.assertTrue(0 < result["events"] <= 16)
        idle()

    def test_source_mismatch_rejected_before_observation(self):
        monitor = SnapshotMonitor(
            NativeBackend.snapshot, Snapshot.__init__, self.obs, source_hashes=("bad", "bad")
        )
        with self.assertRaises(RuntimeError):
            with monitor:
                pass
        idle()

    def test_unrelated_python_function_unobserved(self):
        before = self.obs.lines
        with SnapshotMonitor(NativeBackend.snapshot, Snapshot.__init__, self.obs):
            self.assertEqual(sum(range(10)), 45)
        self.assertEqual(self.obs.lines, before)

    def test_selected_metadata_contains_only_scalars(self):
        self.produce(4)
        self.obs.flush()
        rows = [json.loads(s) for s in self.obs.path.read_text().splitlines()]
        matrix = [r for r in rows if r.get("id") == "S06.matrix_ready"][0]["metadata"]["matrix"]
        self.assertEqual(matrix, dict(shape=[4, 768], dtype="float32", nbytes=4 * 768 * 4))
        self.assertFalse(any("vector" in r.get("metadata", {}) for r in rows))

    def test_stale_callback_not_stolen(self):
        def callback(code, line):
            return None

        sys.monitoring.use_tool_id(4, "prior")
        sys.monitoring.register_callback(4, sys.monitoring.events.LINE, callback)
        sys.monitoring.free_tool_id(4)
        try:
            with self.assertRaises(RuntimeError):
                preflight(self.obs)
            self.assertIsNone(sys.monitoring.get_tool(4))
        finally:
            sys.monitoring.use_tool_id(4, "cleanup")
            prior = sys.monitoring.register_callback(4, sys.monitoring.events.LINE, None)
            self.assertIs(prior, callback)
            sys.monitoring.free_tool_id(4)
