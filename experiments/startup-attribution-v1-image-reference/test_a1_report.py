import copy
import tempfile
import unittest
from pathlib import Path

import experiment as E
import pc_common as C
from sa_fixtures import runtime_fixture
from sa_observe import CATALOG
from sa_report import replay


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        root = Path(cls.tmp.name)
        seed = E.build(root / "seed", testing=True)
        result = runtime_fixture(root, seed)
        if result["error"]:
            raise AssertionError((result["out"] / "failure.json").read_text())
        cls.runtime = C.lines(result["out"] / "attribution-runtime.jsonl")
        cls.driver = C.read(result["out"] / "driver-summary.json")
        first = next(r["start_ns"] for r in cls.runtime if r["kind"] == "checkpoint")
        last = max(r["end_ns"] for r in cls.runtime if r["kind"] == "checkpoint")
        cls.host = []
        for n, name in enumerate(k for k, s in CATALOG.items() if s == "host"):
            when = first - 1000000 + n * 100 if n < 8 else last + 1000000 + n * 100
            cls.host.append(
                dict(
                    kind="checkpoint",
                    id=name,
                    seq=n,
                    start_ns=when,
                    end_ns=when + 1,
                    sample={"synthetic": True},
                    metadata={},
                )
            )
        for role in (
            "package_bundle_image_verification",
            "protected_prior_inputs",
            "host_final_protection",
        ):
            cls.host.append(dict(kind="role", role=role, entries=0))
        cls.host.append(
            dict(
                kind="summary",
                complete=True,
                invalid=[],
                cpu_seconds=0.01,
                wall_seconds=0.01,
                line_callbacks=0,
                callbacks=0,
                file_reads=0,
                read_bytes=0,
            )
        )
        cls.sampler = dict(cpu_seconds=1, file_reads=100, bytes_read=1000)

    def run_replay(self, host=None, runtime=None, driver=None, sampler=None):
        return replay(
            self.host if host is None else host,
            self.runtime if runtime is None else runtime,
            self.sampler if sampler is None else sampler,
            self.driver if driver is None else driver,
            synthetic=True,
        )

    def test_exact_full_metadata_ledger_replays(self):
        result = self.run_replay()
        self.assertEqual(result["checkpoints"], 102)
        self.assertEqual(result["fetches"], 9892)
        self.assertEqual(result["outcome"], "attribution_complete_unresolved")
        self.assertFalse(result["causal_savings_claim"])
        self.assertTrue(result["synthetic_fixture"])

    def test_each_required_checkpoint_removal_rejected(self):
        for scope in ("host", "runtime"):
            original = getattr(self, scope)
            for row in original:
                if row["kind"] == "checkpoint":
                    with self.subTest(point=row["id"]), self.assertRaises(ValueError):
                        self.run_replay(**{scope: [r for r in original if r is not row]})

    def test_page_count_tamper_rejected(self):
        changed = copy.deepcopy(self.runtime)
        row = next(r for r in changed if r.get("family") == "verification_fetch")
        row["rows"] = 99
        with self.assertRaises(ValueError):
            self.run_replay(runtime=changed)

    def test_pending_dispatch_rejected(self):
        with self.assertRaises(ValueError):
            self.run_replay(driver={**self.driver, "pending": 1})

    def test_transaction_tamper_rejected(self):
        changed = copy.deepcopy(self.runtime)
        row = next(r for r in changed if r.get("operation") == "COMMIT")
        row["operation"] = "ROLLBACK"
        with self.assertRaises(ValueError):
            self.run_replay(runtime=changed)

    def test_duplicate_command_rejected(self):
        changed = copy.deepcopy(self.runtime)
        row = next(r for r in changed if r.get("family") == "verification_fetch")
        changed.append(copy.deepcopy(row))
        with self.assertRaises(ValueError):
            self.run_replay(runtime=changed)

    def test_combined_sampler_budget_rejected(self):
        with self.assertRaises(ValueError):
            self.run_replay(sampler={**self.sampler, "cpu_seconds": 60})

    def test_summary_only_cannot_qualify(self):
        with self.assertRaises(ValueError):
            self.run_replay(runtime=[r for r in self.runtime if r["kind"] != "command"])

    def test_non_synthetic_cannot_use_fixture_samples(self):
        with self.assertRaises((ValueError, KeyError)):
            replay(self.host, self.runtime, self.sampler, self.driver)
