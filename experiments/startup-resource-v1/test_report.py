import copy
import tempfile
import unittest
from pathlib import Path

import sr_report as R
from test_fixtures import complete_return, runtime_fixture


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        result = runtime_fixture(cls.root)
        if result["error"]:
            raise AssertionError((result["out"] / "failure.json").read_text())
        cls.campaign, cls.package = complete_return(cls.root, result)

    def test_complete_independent_zero_search_reconstruction(self):
        result = R.analyze(self.campaign, self.package, self.root / "positive")
        self.assertEqual(result["outcome"], "startup_resource_margin_pass_scoped")
        self.assertEqual(result["searches"], 0)
        self.assertFalse(result["calibration_qualified"])
        self.assertFalse(result["treatment_speed_qualified"])

    def test_raw_tamper_rejected(self):
        with __import__("unittest").mock.patch("sr_report.sha", return_value="bad"):
            with self.assertRaises(ValueError):
                R.analyze(self.campaign, self.package, self.root / "bad-lock")

    def altered(self, name, change):
        from unittest.mock import patch

        original = R.read

        def read(p):
            value = original(p)
            if Path(p).name == name:
                value = copy.deepcopy(value)
                change(value)
            return value

        with patch("sr_report.read", side_effect=read):
            with self.assertRaises(ValueError):
                R.analyze(self.campaign, self.package, self.root / ("bad-" + name))

    def test_nonzero_search_rejected(self):
        self.altered("status.json", lambda r: r.update(backend_searches=1))

    def test_prohibited_attempt_rejected(self):
        self.altered("status.json", lambda r: r.update(prohibited_sql_attempts=1))

    def test_scan_count_rejected(self):
        self.altered("status.json", lambda r: r["full_scans"].update(snapshot=2))

    def test_missing_reader_rejected(self):
        self.altered("status.json", lambda r: r.update(reader_connections=9))

    def test_snapshot_proof_rejected(self):
        self.altered("snapshot-qualified.json", lambda r: r.update(snapshot_identity="bad"))

    def test_source_mutation_rejected(self):
        self.altered("source-after.json", lambda r: r.update(bytes=-1))

    def test_cleanup_error_rejected(self):
        self.altered("cleanup.json", lambda r: r["errors"].append("failure"))

    def test_unfinished_final_integrity_rejected(self):
        self.altered("status.json", lambda r: r.update(final_integrity_verified=False))

    def test_wrong_package_rejected(self):
        with __import__("unittest").mock.patch("pc_common.sha", return_value="bad"):
            with self.assertRaises(ValueError):
                R.analyze(self.campaign, self.package, self.root / "bad-seal")

    def test_zero_data_only_not_performance_report(self):
        self.assertNotIn("timing(", Path(R.__file__).read_text())
        self.assertNotIn("bootstrap(", Path(R.__file__).read_text())
