import tempfile
import unittest
from pathlib import Path

import experiment as E
import pc_common as C
import si_stream as H
from test_fixtures import runtime_fixture


class StreamRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.seed = E.build(Path(cls.tmp.name) / "seed", testing=True)

    def run_case(self, fault):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        r = runtime_fixture(Path(tmp.name), self.seed, fault)
        H.assert_restored()
        self.assertIsNotNone(r["error"])
        self.assertEqual(r["status"]["backend_searches"], 0)
        self.assertEqual(r["status"]["search_sql"], 0)
        self.assertTrue(all(c.closed for c in r["opened"]))
        self.assertFalse(C.read(r["out"] / "LOCK.json")["complete"])
        self.assertFalse(any("<=>" in text for c in r["opened"] for text, p in c.executed))
        return r

    def test_actual_encoding_error_cleanup(self):
        r = self.run_case("stream_hash")
        self.assertTrue(C.read(r["out"] / "identity-stream.json")["binding_restored"])
        self.assertEqual(set(r["stopped"]), set(C.CELLS))

    def test_actual_deadline_cleanup(self):
        r = self.run_case("stream_deadline")
        self.assertTrue(C.read(r["out"] / "identity-stream.json")["binding_restored"])

    def test_actual_baseexception_cleanup(self):
        r = self.run_case("stream_interrupt")
        self.assertTrue(C.read(r["out"] / "identity-stream.json")["binding_restored"])

    def test_actual_byte_cap_cleanup(self):
        r = self.run_case("stream_cap")
        self.assertTrue(C.read(r["out"] / "identity-stream.json")["binding_restored"])

    def test_actual_original_constructor_rejection(self):
        r = self.run_case("stream_constructor")
        record = C.read(r["out"] / "identity-stream.json")
        self.assertTrue(record["binding_restored"])
        self.assertEqual(record["invocations"], 0)

    def test_actual_preflight_fails_before_copy_or_SQL(self):
        r = self.run_case("preflight")
        self.assertEqual(r["opened"], [])
        self.assertEqual(set(r["stopped"]), set(C.CELLS))
        self.assertFalse((r["out"] / "copies.json").exists())
