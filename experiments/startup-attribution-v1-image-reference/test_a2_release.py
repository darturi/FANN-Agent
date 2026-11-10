"""Strict image binding, pre-restore rejection and finite controller mechanics."""

import copy
import io
import os
import platform
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import experiment as E
import pc_common as C
import pc_control as P
from sa_driver import Driver
from sa_fixtures import runtime_fixture
from sa_observe import Observation
from sa_preflight import EXPECTED_PROOF, original_mapping
from sa_test_support import reference


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        cls.package = E.build(cls.root / "seed", testing=True)

    def observation(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        obs = Observation(tmp.name, "runtime", lambda o: {"synthetic": True})
        self.addCleanup(lambda: obs.finish(False) if not obs.closed else None)
        return obs

    def proofs(self):
        p = self.package
        common = dict(
            status="pass",
            tests_run=120,
            baseline_regression_pass=True,
            source_files_sha256={f.name: C.sha(f) for f in p.glob("*.py")},
            recipe_files_sha256={n: C.sha(p / n) for n in C.read(p / "RECIPE-FILES.json")["files"]},
        )
        source = copy.deepcopy(common)
        target = copy.deepcopy(common)
        target.update(
            python="3.12.15",
            target_image_config_sha256=C.read(p / "IMAGE-CORRECTION.json")["docker_config_sha256"],
            actual_provenance=C.read(p / "IMAGE-REFERENCE.json"),
        )
        return source, target

    def proof_context(self, source=None, target=None, native=False):
        left, right = self.proofs()
        if source is not None:
            left = source
        if target is not None:
            right = target
        read = C.read
        cfg = read(self.package / "experiment.json")
        if native:
            cfg.update(synthetic_fixture=False, local_readiness="source_and_target_checks_passed")

        def values(path):
            path = Path(path)
            if path == self.package / "LOCAL_CHECKS.json":
                return left
            if path == self.package / "TARGET_CHECKS.json":
                return right
            if path == self.package / "experiment.json":
                return cfg
            return read(path)

        return patch("pc_common.read", side_effect=values)

    def test_exact_local_and_image_references_differ_only_python(self):
        local = C.read(self.package / "DRIVER-REFERENCE.json")
        target = C.read(self.package / "IMAGE-REFERENCE.json")
        self.assertEqual(
            {k: (local[k], target[k]) for k in local if local[k] != target[k]},
            {"python": ("3.12.7", "3.12.15")},
        )
        self.assertEqual(
            C.sha(self.package / "DRIVER-REFERENCE.json"),
            "707fc1fd7eb52a22e00535d9d06ad51c48a3a674620f8c145724e58f86edb409",
        )

    def test_default_native_reference_is_always_exact_image(self):
        driver = Driver(self.observation())
        self.assertEqual(driver.reference, C.read(self.package / "IMAGE-REFERENCE.json"))
        if platform.python_version() == "3.12.15":
            try:
                driver.install()
                self.assertEqual(len(driver.originals), 9)
            finally:
                driver.restore()
        else:
            with self.assertRaisesRegex(RuntimeError, "provenance mismatch: python"):
                driver.install()
            self.assertEqual(driver.originals, [])

    def test_environment_cannot_select_a_local_native_reference(self):
        with patch.dict(os.environ, SA_REFERENCE="local", SA_FIXTURE="1", PYTHON_VERSION="3.12.7"):
            self.assertEqual(
                Driver(self.observation()).reference, C.read(self.package / "IMAGE-REFERENCE.json")
            )

    def test_unqualified_patch_rejected_by_fixture_selector(self):
        actual = reference()
        actual["python"] = "3.12.8"
        with patch("sa_test_support.provenance", return_value=actual):
            with self.assertRaisesRegex(RuntimeError, "unqualified"):
                reference()

    def test_all_driver_identity_fields_remain_strict(self):
        actual = reference()
        for key in actual:
            with self.subTest(key=key):
                bad = copy.deepcopy(actual)
                if key == "hooks":
                    bad[key][0]["file_sha256"] = "wrong"
                elif key == "query_parser":
                    bad[key]["function_sha256"] = "wrong"
                else:
                    bad[key] = "unexpected"
                driver = Driver(self.observation(), reference=bad)
                with self.assertRaises(RuntimeError):
                    driver.install()
                self.assertFalse(driver.installed)
                self.assertEqual(driver.originals, [])

    def test_pre_restore_original_source_proof_is_exact(self):
        self.assertEqual(original_mapping(self.observation()), EXPECTED_PROOF)

    def test_original_mapping_mismatch_rejects_before_restore(self):
        with tempfile.TemporaryDirectory() as d:
            result = runtime_fixture(Path(d), self.package, "source_mapping")
            self.assertIsNotNone(result["error"])
            self.assertEqual(result["opened"], [])
            # Original teardown attempts both cells even when restore never began.
            self.assertEqual(set(result["stopped"]), set(C.CELLS))
            self.assertFalse((result["out"] / "copies.json").exists())
            self.assertFalse((result["out"] / "source-before.json").exists())
            failure = C.read(result["out"] / "instrument-capability-failure.json")
            self.assertIn("source mapping mismatch", failure["message"])
            self.assertEqual(result["status"]["backend_searches"], 0)

    def test_occupied_monitor_is_preserved_at_pre_restore_gate(self):
        import sys

        sys.monitoring.use_tool_id(2, "existing-check")
        try:
            with self.assertRaisesRegex(RuntimeError, "Pre-existing"):
                original_mapping(self.observation())
            self.assertEqual(sys.monitoring.get_tool(2), "existing-check")
        finally:
            sys.monitoring.free_tool_id(2)

    def test_mock_readiness_requires_source_and_exact_target(self):
        with self.proof_context(native=True):
            C.require_native_release(self.package)

    def test_target_python_mismatch_cannot_be_waived(self):
        left, right = self.proofs()
        right["python"] = "3.12.7"
        with self.proof_context(left, right, native=True), self.assertRaises(RuntimeError):
            C.require_native_release(self.package)

    def test_target_image_id_mismatch_rejects(self):
        left, right = self.proofs()
        right["target_image_config_sha256"] = "wrong"
        with self.proof_context(left, right, native=True), self.assertRaises(RuntimeError):
            C.require_native_release(self.package)

    def test_target_provenance_mismatch_rejects(self):
        left, right = self.proofs()
        right["actual_provenance"]["libpq_version"] += 1
        with self.proof_context(left, right, native=True), self.assertRaises(RuntimeError):
            C.require_native_release(self.package)

    def test_stale_source_receipt_rejects(self):
        left, right = self.proofs()
        left["source_files_sha256"]["sa_driver.py"] = "wrong"
        with self.proof_context(left, right, native=True), self.assertRaises(RuntimeError):
            C.require_native_release(self.package)

    def test_stale_target_recipe_rejects(self):
        left, right = self.proofs()
        right["recipe_files_sha256"]["IMAGE-REFERENCE.json"] = "wrong"
        with self.proof_context(left, right, native=True), self.assertRaises(RuntimeError):
            C.require_native_release(self.package)

    def test_failed_target_checks_reject(self):
        left, right = self.proofs()
        right["status"] = "fail"
        with self.proof_context(left, right, native=True), self.assertRaises(RuntimeError):
            C.require_native_release(self.package)

    def test_synthetic_package_rejects_even_with_mock_readiness(self):
        with self.proof_context(), self.assertRaises(RuntimeError):
            C.require_native_release(self.package)

    def test_missing_exact_target_receipt_rejects(self):
        with self.assertRaises(FileNotFoundError):
            C.readiness(self.package)


class ControllerTests(unittest.TestCase):
    def case(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        package = root / "package"
        package.mkdir()
        campaign = root / "campaign"
        campaign.mkdir()
        results = root / "results"
        results.mkdir()
        (campaign / "logs").mkdir()
        C.save(package / "manifest.json", {})
        manifest = C.sha(package / "manifest.json")
        record = dict(
            package=str(package),
            campaign=str(campaign),
            sources=str(results),
            package_manifest_sha256=manifest,
            counts=C.COUNTS,
            status="submitting",
            jobs={},
            dispatch={},
            account="torch_pr_288_courant",
            bundle="/bundle",
            prepared="/prepared",
            workspace="/scratch",
            apptainer="/apptainer",
            host_python="/usr/bin/python3",
        )
        C.save(campaign / "submission.json", record)
        C.save(
            package / "submission-binding.json",
            dict(campaign=str(campaign), package_manifest_sha256=manifest),
        )
        P.reserve(results, package, campaign)
        return package, campaign, results, record

    def test_shared_reservation_blocks_overwrite(self):
        package, campaign, results, record = self.case()
        self.assertTrue((results / ".torch-startup-attribution-v1-reservation.json").exists())
        with self.assertRaises(FileExistsError):
            P.reserve(results, package, campaign)

    def test_successful_dispatch_is_recorded_and_never_repeated(self):
        package, campaign, results, record = self.case()
        with (
            patch("pc_control.require_native_release"),
            patch(
                "pc_control.subprocess.run",
                return_value=Mock(returncode=0, stdout="12345;torch\n", stderr=""),
            ) as run,
        ):
            self.assertEqual(P.dispatch(package, campaign, record, 0), "12345")
            with self.assertRaises(ValueError):
                P.dispatch(package, campaign, record, 0)
            self.assertEqual(run.call_count, 1)
        self.assertEqual(
            C.read(campaign / "submission.json")["dispatch"]["block-0"]["status"], "submitted"
        )

    def test_uncertain_dispatch_is_not_replayed(self):
        package, campaign, results, record = self.case()
        with (
            patch("pc_control.require_native_release"),
            patch("pc_control.subprocess.run", side_effect=OSError("unknown transport")) as run,
        ):
            with self.assertRaises(OSError):
                P.dispatch(package, campaign, record, 0)
            with self.assertRaises(ValueError):
                P.dispatch(package, campaign, record, 0)
            self.assertEqual(run.call_count, 1)
        self.assertEqual(
            C.read(campaign / "submission.json")["dispatch"]["block-0"]["status"], "unknown"
        )

    def test_unparseable_success_is_uncertain_not_retryable(self):
        package, campaign, results, record = self.case()
        with (
            patch("pc_control.require_native_release"),
            patch(
                "pc_control.subprocess.run",
                return_value=Mock(returncode=0, stdout="not a job id", stderr=""),
            ),
        ):
            with self.assertRaises(RuntimeError):
                P.dispatch(package, campaign, record, 0)
        self.assertEqual(record["dispatch"]["block-0"]["status"], "unknown")

    def test_scheduler_rejection_is_retained(self):
        package, campaign, results, record = self.case()
        with (
            patch("pc_control.require_native_release"),
            patch(
                "pc_control.subprocess.run",
                return_value=Mock(returncode=1, stdout="", stderr="rejected"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                P.dispatch(package, campaign, record, 0)
        self.assertEqual(record["dispatch"]["block-0"]["status"], "rejected")

    def test_other_block_or_dependency_never_calls_scheduler(self):
        package, campaign, results, record = self.case()
        with patch("pc_control.require_native_release"), patch("pc_control.subprocess.run") as run:
            for block, dependency in ((1, None), (0, "12")):
                with self.assertRaises(ValueError):
                    P.dispatch(package, campaign, record, block, dependency)
            run.assert_not_called()

    def test_wrong_reservation_never_calls_scheduler(self):
        package, campaign, results, record = self.case()
        path = results / ".torch-startup-attribution-v1-reservation.json"
        item = C.read(path)
        item["campaign"] = "/wrong"
        C.replace(path, item)
        with patch("pc_control.require_native_release"), patch("pc_control.subprocess.run") as run:
            with self.assertRaises(ValueError):
                P.dispatch(package, campaign, record, 0)
            run.assert_not_called()

    def test_status_before_submission_is_clear_and_read_only(self):
        package, campaign, results, record = self.case()
        (package / "submission-binding.json").unlink()
        with (
            patch("pc_control.verify"),
            patch("pc_control.subprocess.run") as run,
            redirect_stdout(io.StringIO()) as output,
        ):
            P.status(package)
        self.assertIn("Not submitted", output.getvalue())
        run.assert_not_called()

    def terminal(self, complete=False):
        package, campaign, results, record = self.case()
        record["jobs"] = {"block-0": "12345"}
        record["dispatch"] = {"block-0": dict(status="submitted", job_id="12345")}
        C.replace(campaign / "submission.json", record)
        if complete:
            (campaign / "run").mkdir()
            C.save(campaign / "run/host-exit.json", dict(exit_code=0))
        return package, campaign, record

    def test_terminal_failed_prefix_is_collectible(self):
        package, campaign, record = self.terminal()
        replies = [
            Mock(returncode=0, stdout="", stderr=""),
            Mock(returncode=0, stdout="12345_0|FAILED|1:0|00:01|4|32G|100K\n", stderr=""),
        ]
        with (
            patch("pc_control.verify"),
            patch("pc_control.subprocess.run", side_effect=replies),
            redirect_stdout(io.StringIO()),
        ):
            P.collect(package)
        self.assertTrue(Path(str(campaign) + ".tar.gz").exists())
        self.assertEqual(
            C.read(campaign / "analysis/failure-summary.json")["status"], "incomplete_or_failed"
        )

    def test_queued_job_cannot_be_collected(self):
        package, campaign, record = self.terminal()
        with (
            patch("pc_control.verify"),
            patch(
                "pc_control.subprocess.run",
                return_value=Mock(returncode=0, stdout="12345", stderr=""),
            ),
        ):
            with self.assertRaisesRegex(ValueError, "still queued"):
                P.collect(package)
        self.assertFalse(Path(str(campaign) + ".tar.gz").exists())

    def test_unknown_accounting_cannot_be_collected(self):
        package, campaign, record = self.terminal()
        with (
            patch("pc_control.verify"),
            patch(
                "pc_control.subprocess.run",
                side_effect=[
                    Mock(returncode=0, stdout="", stderr=""),
                    Mock(returncode=0, stdout="", stderr=""),
                ],
            ),
        ):
            with self.assertRaisesRegex(ValueError, "completion unknown"):
                P.collect(package)


if __name__ == "__main__":
    unittest.main()
