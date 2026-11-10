import hashlib
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import experiment as E
import pc_common as C
import pc_control
import sa_control
from sa_driver import Driver
from sa_observe import Observation


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        cls.package = E.build(cls.root / "seed", testing=True)

    def test_all_frozen_A0_and_original_boundaries_verify(self):
        cfg = C.verify(self.package)
        self.assertEqual(cfg["version"], "startup-attribution.v1")
        self.assertTrue(cfg["native_handoff_released"])
        self.assertEqual(cfg["counts"]["searches_total"], 0)
        self.assertEqual(C.read(self.package / "ATTRIBUTION-SOURCE-PINS.json")["files"], 246)

    def test_archive_members_match_sealed_files(self):
        manifest = C.read(self.package / "manifest.json")
        with tarfile.open(self.package.parent / (C.NAME + ".tar.gz")) as tar:
            members = tar.getmembers()
            self.assertEqual(len(members), len(manifest["files"]) + 1)
            self.assertEqual(len({m.name for m in members}), len(members))
            for m in members:
                self.assertTrue(m.isfile())
                self.assertEqual(
                    hashlib.sha256(tar.extractfile(m).read()).hexdigest(),
                    C.sha(self.package / Path(m.name).relative_to(C.NAME)),
                )

    def test_original_producer_constructor_and_native_files_byte_identical(self):
        for name, expected in C.read(self.package / "frozen/manifest.json")["files"].items():
            self.assertEqual(C.sha(self.package / "frozen" / name), expected)

    def test_identity_stream_helper_unchanged(self):
        self.assertEqual(C.sha(self.package / "si_stream.py"), C.sha(E.SOURCE / "si_stream.py"))

    def test_native_entry_gate_closed(self):
        with self.assertRaises(RuntimeError):
            C.require_native_release(self.package)

    def test_both_submit_routes_block_before_external_call(self):
        with patch("pc_control.subprocess.run") as run:
            with self.assertRaises(RuntimeError):
                pc_control.submit(self.package, Path("/bundle"), Path("/results"))
            with self.assertRaises(RuntimeError):
                pc_control.dispatch(self.package, Path("/campaign"), {}, 0)
            run.assert_not_called()
        with patch("sys.argv", ["sa_control.py", "unexpected"]):
            with self.assertRaises(SystemExit):
                sa_control.main()

    def test_A0_catalog_tampering_rejected(self):
        original = C.sha
        with patch(
            "pc_common.sha",
            side_effect=lambda p: "bad" if Path(p).name == "CHECKPOINTS.json" else original(p),
        ):
            with self.assertRaises(ValueError):
                C.verify(self.package)

    def test_driver_source_mismatch_rejected_before_wrappers(self):
        with tempfile.TemporaryDirectory() as d:
            obs = Observation(d, "runtime", lambda o: {"synthetic": True})
            from sa_test_support import reference as fixture_reference

            reference = fixture_reference()
            reference["hooks"][0]["file_sha256"] = "bad"
            driver = Driver(obs, reference)
            try:
                with self.assertRaises(RuntimeError):
                    driver.install()
                self.assertFalse(driver.installed)
                self.assertEqual(driver.originals, [])
            finally:
                driver.restore()
                obs.finish(False)

    def test_latest_completed_native_evidence_in_protected_contract(self):
        cfg = C.read(self.package / "experiment.json")
        name = "reviews-startup-resource-stream-v1-20261028T151219Z.hmj9cwut"
        evidence = C.read(self.package / "BASELINE-STREAM-VERIFICATION.json")
        self.assertEqual(cfg["prior_raw_files"][name], evidence["raw_files_sha256"])
        self.assertEqual(
            C.sha(self.package / "prior-stream-manifest.json"),
            "26a7d66b67137e77d5208d7b851b19d980a8a64060defc25cbe418db17190354",
        )
