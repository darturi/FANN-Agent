"""Actual runtime entry and all scopes; synthetic files/transports/counts only."""

import tempfile
import unittest
from pathlib import Path

import experiment as E
import pc_common as C
from sa_fixtures import runtime_fixture
from sa_monitor import idle


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.seed = E.build(Path(cls.tmp.name) / "seed", testing=True)

    def run_case(self, fault=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        value = runtime_fixture(Path(tmp.name), self.seed, fault)
        idle()
        return value

    def test_complete_real_runtime_and_all_90_runtime_checkpoints(self):
        r = self.run_case()
        self.assertIsNone(r["error"], (r["out"] / "failure.json").read_text() if r["error"] else "")
        rows = C.lines(r["out"] / "attribution-runtime.jsonl")
        points = [x for x in rows if x["kind"] == "checkpoint"]
        capability = C.read(r["out"] / "instrument-capability.json")
        self.assertEqual(len(capability["bindings"]), 9)
        self.assertTrue(
            all(b["binding_active"] and b["original_link_intact"] for b in capability["bindings"])
        )
        self.assertEqual(len(points), 90)
        self.assertEqual(len({p["id"] for p in points}), 90)
        self.assertEqual(r["status"]["backend_searches"], 0)
        self.assertEqual(r["status"]["reader_connections"], 10)
        self.assertTrue(all(c.closed for c in r["opened"]))
        self.assertEqual(
            C.read(r["out"] / "driver-summary.json")["counts"]["verification_fetch"], 9892
        )
        self.assertTrue(C.read(r["out"] / "LOCK.json")["complete"])
        self.assertTrue(
            all(
                p["metadata"]["snapshot_aliases"]["retained"]
                for p in points
                if "snapshot_aliases" in p["metadata"]
            )
        )
        self.assertNotIn("attribution-host.jsonl", C.read(r["out"] / "LOCK.json")["files"])

    def test_constructor_error_restores_and_stops(self):
        r = self.run_case("stream_constructor")
        self.assertIsNotNone(r["error"])
        self.assertTrue(all(c.closed for c in r["opened"]))
        self.assertEqual(set(r["stopped"]), set(C.CELLS))
        self.assertFalse(C.read(r["out"] / "LOCK.json")["complete"])

    def test_identity_baseexception_restores_and_stops(self):
        r = self.run_case("stream_interrupt")
        self.assertIsNotNone(r["error"])
        self.assertTrue(all(c.closed for c in r["opened"]))
        self.assertEqual(set(r["stopped"]), set(C.CELLS))

    def test_sampler_failure_cannot_qualify(self):
        r = self.run_case("sampler")
        self.assertIsNotNone(r["error"])
        self.assertFalse(C.read(r["out"] / "LOCK.json")["complete"])

    def test_all_four_signal_handlers_restore_and_cleanup(self):
        for sig in ("ALRM", "TERM", "USR1", "INT"):
            with self.subTest(signal=sig):
                r = self.run_case("signal_" + sig)
                self.assertIsNotNone(r["error"])
                self.assertTrue(all(c.closed for c in r["opened"]))
                self.assertEqual(set(r["stopped"]), set(C.CELLS))
                self.assertFalse(C.read(r["out"] / "LOCK.json")["complete"])
