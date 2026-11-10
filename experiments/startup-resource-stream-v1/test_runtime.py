import tempfile
import unittest
from pathlib import Path

import experiment as E
import pc_common as C
from test_fixtures import runtime_fixture


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.seed = E.build(Path(cls.tmp.name) / "seed", testing=True)

    def run_case(self, fault=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return runtime_fixture(Path(tmp.name), self.seed, fault)

    def test_full_actual_entry_zero_searches(self):
        r = self.run_case()
        self.assertIsNone(
            r["error"],
            (r["out"] / "failure.json").read_text() if (r["out"] / "failure.json").exists() else "",
        )
        self.assertEqual(r["status"]["backend_searches"], 0)
        self.assertEqual(r["status"]["search_sql"], 0)
        self.assertEqual(r["status"]["prohibited_sql_attempts"], 0)
        self.assertEqual(r["status"]["full_scans"], {"snapshot": 1, "data": 4})
        self.assertEqual(r["status"]["reader_connections"], 10)
        self.assertEqual(r["status"]["maximum_live_readers"], 6)
        self.assertTrue(r["status"]["final_integrity_verified"])
        self.assertTrue(all(c.closed for c in r["opened"]))
        self.assertEqual(set(r["stopped"]), set(C.CELLS))
        self.assertEqual(len(C.lines(r["out"] / "lifecycle.jsonl")), 20)
        self.assertNotIn(".memory-health.json.tmp", C.read(r["out"] / "LOCK.json")["files"])
        self.assertTrue(
            all("<=>" not in text for conn in r["opened"] for text, params in conn.executed)
        )

    def check_failure(self, fault):
        r = self.run_case(fault)
        self.assertIsNotNone(r["error"])
        self.assertEqual(r["status"]["status"], "failed")
        self.assertEqual(r["status"]["backend_searches"], 0)
        self.assertTrue(all(c.closed for c in r["opened"]))
        self.assertEqual(
            C.read(r["out"] / "source-before.json"), C.read(r["out"] / "source-after.json")
        )
        self.assertFalse(C.read(r["out"] / "LOCK.json")["complete"])
        return r

    def test_wrong_eligibility_fails_before_search(self):
        self.check_failure("eligibility")

    def test_wrong_snapshot_identity_fails_before_search(self):
        self.check_failure("snapshot_identity")

    def test_second_server_failure_cleanup(self):
        self.check_failure("second_server")

    def test_cleanup_failure_cannot_qualify(self):
        self.check_failure("cleanup")

    def test_sampler_failure_cannot_continue(self):
        self.check_failure("sampler")
