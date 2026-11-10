"""Actual host/controller entry under fake scheduler/process transport."""

import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import ev_host
import pc_common as C
import pc_control as control
import pc_job as job


class Process:
    def __init__(self, code=0, stubborn=False):
        self.returncode, self.stubborn = code, stubborn
        self.terminated = self.killed = False
        self.waits = []

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        if not self.stubborn:
            self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout):
        self.waits.append(timeout)
        if self.returncode is None:
            raise subprocess.TimeoutExpired("owned-fake-child", timeout)
        return self.returncode


class EnvelopeTests(unittest.TestCase):
    def test_worst_case_preserves_entire_outer_margin(self):
        tick = [100.0]
        e = ev_host.Envelope(clock=lambda: tick[0])
        tick[0] += 239.99
        end = e.runtime()
        self.assertEqual(end, tick[0] + 3000)
        tick[0] = end
        post = e.post()
        self.assertLessEqual(post, e.started + 3480)
        tick[0] = post - 0.001
        proof = e.proof()
        self.assertGreater(3600 - (proof["finished"] - proof["started"]), 120)

    def test_exhausted_pre_phase_cannot_launch(self):
        tick = [0]
        e = ev_host.Envelope(clock=lambda: tick[0])
        tick[0] = 240
        with self.assertRaises(TimeoutError):
            e.runtime()

    def test_exhausted_post_phase_cannot_qualify(self):
        tick = [0]
        e = ev_host.Envelope(clock=lambda: tick[0])
        e.runtime()
        e.post()
        tick[0] = 240
        with self.assertRaises(TimeoutError):
            e.proof()

    def test_guest_reserves_cleanup_and_search_reservation_rejected(self):
        tick = [0]
        with patch.dict(os.environ, EV_RUNTIME_DEADLINE="3000"):
            budget = C.Budget(clock=lambda: tick[0])
        budget.enter("restore_identity")
        tick[0] = 1499
        budget.enter("snapshot_admission")
        self.assertLessEqual(budget.stage_end, 2400)
        with self.assertRaises(RuntimeError):
            budget.reserve("exact")
        tick[0] = 2400
        budget.enter("final_cleanup")
        self.assertEqual(budget.stage_end, 3000)

    def test_monitor_sampler_loss_terminates_then_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            C.save(out / "memory-health.json", dict(status="failed", last_ns=time.monotonic_ns()))
            child, sampler = Process(None), Process(1)
            tick = [0]

            def sleep(value):
                tick[0] += value

            with self.assertRaises(RuntimeError):
                ev_host.monitor(child, sampler, out, 3000, clock=lambda: tick[0], sleep=sleep)
            self.assertTrue(child.terminated)

    def test_monitor_deadline_leaves_reaping_in_post_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            C.save(out / "memory-health.json", dict(status="running", last_ns=time.monotonic_ns()))
            child, sampler = Process(None, True), Process(None)
            with self.assertRaises(TimeoutError):
                ev_host.monitor(child, sampler, out, 10, clock=lambda: 10, sleep=lambda n: None)
            ev_host.stop_child(child, 250, clock=lambda: 10)
            self.assertTrue(child.terminated and child.killed)
            self.assertTrue(all(t <= 10 for t in child.waits))

    def test_stop_child_never_appends_a_cleanup_envelope(self):
        child = Process(None, True)
        ev_host.stop_child(child, 11, clock=lambda: 10)
        self.assertEqual(child.waits, [1, 1])

    def test_expired_post_kills_without_another_wait_budget(self):
        child = Process(None, True)
        with self.assertRaises(TimeoutError):
            ev_host.stop_child(child, 10, clock=lambda: 10)
        self.assertTrue(child.killed)
        self.assertEqual(child.waits, [0])


class HostEntryTests(unittest.TestCase):
    def run_host(self, fault=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        package, bundle, prepared, campaign, workspace, sources = [
            root / n for n in ("package", "bundle", "prepared", "campaign", "workspace", "sources")
        ]
        for path in (package, bundle, prepared, campaign, workspace, sources):
            path.mkdir()
        (package / "frozen").mkdir()
        (package / "reference").mkdir()
        (bundle / "images").mkdir()
        (bundle / "images/runtime.sif").write_bytes(b"fake-sif")
        C.save(package / "manifest.json", {"files": {}})
        C.save(package / "reference/manifest.json", {"files": {}})
        C.save(package / "frozen/source-index.json", {"index": "fixed"})
        C.save(prepared / "database-identity.json", {"index": "fixed"})
        C.save(campaign / "protected-source-before.json", {"protected": "fixed"})
        child, sampler = Process(0), Process(None)
        ticks = [time.monotonic()]

        def stop_child(process, deadline):
            ev_host.stop_child(process, deadline, clock=lambda: ticks[0])
            if fault == "post_expired" and process is child:
                ticks[0] = deadline

        def popen(command):
            C.save(campaign / "run/job-exit.json", {"exit_code": 1 if fault == "guest" else 0})
            self.assertIn("--no-home", command)
            self.assertIn("/patch/pc_runtime.py", command)
            self.assertTrue(any(str(x).startswith("EV_RUNTIME_DEADLINE=") for x in command))
            return child

        real_sha = C.sha
        checks = [0]

        def verify(*a):
            checks[0] += 1
            if fault == "pre_verify" or fault == "post_verify" and checks[0] == 2:
                raise ValueError("Injected capsule/source failure")
            return {}

        with ExitStack() as stack:
            for name, kwargs in [
                (
                    "pc_job.Envelope",
                    dict(side_effect=lambda: ev_host.Envelope(clock=lambda: ticks[0])),
                ),
                ("pc_job.stop_child", dict(side_effect=stop_child)),
                (
                    "pc_job.os.uname",
                    dict(return_value=SimpleNamespace(sysname="Linux", machine="x86_64")),
                ),
                ("pc_job.require_native_release", dict(return_value={})),
                ("pc_job.verify", dict(side_effect=verify)),
                (
                    "pc_job.sha",
                    dict(
                        side_effect=lambda p: (
                            C.CONTRACT["runtime"]["image_sha256"]
                            if Path(p).name == "runtime.sif"
                            else real_sha(p)
                        )
                    ),
                ),
                (
                    "pc_job.protected",
                    dict(
                        side_effect=[
                            {"protected": "fixed"},
                            {"protected": "changed" if fault == "source" else "fixed"},
                        ]
                    ),
                ),
                ("pc_resources.preflight", dict(return_value={})),
                ("sr_host.start_sampler", dict(return_value=sampler)),
                (
                    "sr_host.stop_sampler",
                    dict(
                        side_effect=RuntimeError("Injected sampler stop")
                        if fault == "sampler_stop"
                        else None
                    ),
                ),
                ("pc_job.subprocess.Popen", dict(side_effect=popen)),
                ("pc_job.signal.signal", dict()),
                ("pc_job.signal.setitimer", dict()),
                (
                    "sys.argv",
                    dict(
                        new=[
                            "pc_job.py",
                            *map(str, (package, bundle, prepared, campaign, workspace, sources)),
                            "/fake/apptainer",
                            sys.executable,
                        ]
                    ),
                ),
            ]:
                stack.enter_context(patch(name, **kwargs))
            stack.enter_context(
                patch.dict(
                    os.environ,
                    SLURM_JOB_ID="42_0",
                    SLURM_ARRAY_JOB_ID="42",
                    SLURM_ARRAY_TASK_ID="0",
                    SLURM_CPUS_PER_TASK="4",
                    SLURM_EXPORT_ENV="ALL",
                    PYTHONDONTWRITEBYTECODE="1",
                )
            )
            error = None
            try:
                job.main()
            except (RuntimeError, TimeoutError) as exc:
                error = exc
        self.last_verify_calls = checks[0]
        return campaign / "run", error

    def test_actual_host_entry_success_final_lock_and_integrity(self):
        run, error = self.run_host()
        self.assertIsNone(error)
        self.assertEqual(C.read(run / "host-exit.json")["exit_code"], 0)
        lock = C.read(run / "HOST-LOCK.json")
        self.assertTrue(lock["complete"])
        self.assertEqual(
            set(lock["files"]),
            {str(p.relative_to(run)) for p in run.iterdir() if p.name != "HOST-LOCK.json"},
        )
        for name, expected in lock["files"].items():
            self.assertEqual(C.sha(run / name), expected)

    def test_actual_host_guest_failure_is_collectible(self):
        run, error = self.run_host("guest")
        self.assertIsNotNone(error)
        self.assertFalse(C.read(run / "HOST-LOCK.json")["complete"])

    def test_actual_host_preflight_failure_still_finalizes_sampler(self):
        run, error = self.run_host("pre_verify")
        self.assertIsNotNone(error)
        self.assertEqual(C.read(run / "host-exit.json")["exit_code"], 1)

    def test_actual_host_final_source_change_fails(self):
        run, error = self.run_host("source")
        self.assertIsNotNone(error)
        self.assertFalse(C.read(run / "host-exit.json")["protected_sources_unchanged"])

    def test_actual_host_final_capsule_failure_fails(self):
        run, error = self.run_host("post_verify")
        self.assertIsNotNone(error)
        self.assertTrue((run / "host-failure.json").exists())

    def test_actual_host_sampler_finalization_failure_fails(self):
        run, error = self.run_host("sampler_stop")
        self.assertIsNotNone(error)
        self.assertEqual(C.read(run / "host-exit.json")["exit_code"], 1)

    def test_actual_expired_post_skips_heavy_verification_and_kills_sampler(self):
        run, error = self.run_host("post_expired")
        self.assertIsInstance(error, TimeoutError)
        self.assertEqual(self.last_verify_calls, 1)
        self.assertEqual(C.read(run / "host-exit.json")["exit_code"], 1)
        self.assertFalse((run / "HOST-LOCK.json").exists())


class ControllerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.package, self.sources, self.campaign = [
            self.root / n for n in ("package", "sources", "campaign")
        ]
        for path in (self.package, self.sources, self.campaign):
            path.mkdir()
        (self.campaign / "logs").mkdir()
        C.save(self.package / "manifest.json", {"files": {}})
        self.record = dict(
            package=str(self.package),
            sources=str(self.sources),
            campaign=str(self.campaign),
            package_manifest_sha256=C.sha(self.package / "manifest.json"),
            counts=C.COUNTS,
            account="torch_pr_288_courant",
            bundle="/bundle",
            prepared="/prepared",
            workspace="/workspace",
            host_python="/usr/bin/python3.12",
            apptainer="/apptainer",
            dispatch={},
            jobs={},
        )
        C.save(self.campaign / "submission.json", self.record)
        C.save(
            self.package / "submission-binding.json",
            {k: self.record[k] for k in ("campaign", "package_manifest_sha256")},
        )
        control.reserve(self.sources, self.package, self.campaign)

    def test_successful_dispatch_is_once_and_uses_exact_host_interpreter(self):
        with (
            patch("pc_control.require_native_release"),
            patch(
                "pc_control.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stdout="12345\n", stderr=""),
            ) as run,
        ):
            control.dispatch(self.package, self.campaign, self.record, 0)
            command = run.call_args.args[0]
            self.assertIn("--export=NONE", command)
            self.assertIn("--array=0", command)
            self.assertEqual(command[-1], "/usr/bin/python3.12")
            with self.assertRaises(ValueError):
                control.dispatch(self.package, self.campaign, self.record, 0)
            self.assertEqual(run.call_count, 1)

    def test_unknown_dispatch_blocks_retry(self):
        with (
            patch("pc_control.require_native_release"),
            patch("pc_control.subprocess.run", side_effect=InterruptedError("unknown")) as run,
        ):
            with self.assertRaises(InterruptedError):
                control.dispatch(self.package, self.campaign, self.record, 0)
            self.assertEqual(self.record["dispatch"]["block-0"]["status"], "unknown")
            with self.assertRaises(ValueError):
                control.dispatch(self.package, self.campaign, self.record, 0)
            self.assertEqual(run.call_count, 1)

    def test_malformed_scheduler_success_blocks_retry(self):
        with (
            patch("pc_control.require_native_release"),
            patch(
                "pc_control.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stdout="not-a-job", stderr=""),
            ),
        ):
            with self.assertRaises(RuntimeError):
                control.dispatch(self.package, self.campaign, self.record, 0)
            self.assertEqual(self.record["dispatch"]["block-0"]["status"], "unknown")

    def test_wrong_block_and_dependency_cannot_dispatch(self):
        with patch("pc_control.require_native_release"), patch("pc_control.subprocess.run") as run:
            for block, dependency in ((1, None), (0, "other")):
                with self.assertRaises(ValueError):
                    control.dispatch(self.package, self.campaign, self.record, block, dependency)
            run.assert_not_called()

    def test_shared_reservation_exclusive_across_reuploads(self):
        with self.assertRaises(FileExistsError):
            control.reserve(self.sources, self.package, self.campaign)

    def test_failed_terminal_collect_preserves_all_raw(self):
        self.record.update(
            jobs={"block-0": "12345"},
            dispatch={"block-0": dict(status="submitted", job_id="12345")},
        )
        C.replace(self.campaign / "submission.json", self.record)
        (self.campaign / "partial.txt").write_text("preserve partial evidence")
        responses = [
            SimpleNamespace(returncode=1, stdout="", stderr="Invalid job id"),
            SimpleNamespace(
                returncode=0, stdout="12345_0|TIMEOUT|0:15|01:00:00|4|32G|\n", stderr=""
            ),
        ]
        with (
            patch("pc_control.verify", return_value={}),
            patch("pc_control.subprocess.run", side_effect=responses),
            patch("sys.stdout", io.StringIO()),
        ):
            control.collect(self.package)
        self.assertTrue(Path(str(self.campaign) + ".tar.gz").exists())
        self.assertEqual(
            C.read(self.campaign / "analysis/failure-summary.json")["status"],
            "incomplete_or_failed",
        )

    def test_unknown_scheduler_completion_cannot_collect(self):
        self.record.update(
            jobs={"block-0": "12345"},
            dispatch={"block-0": dict(status="submitted", job_id="12345")},
        )
        C.replace(self.campaign / "submission.json", self.record)
        responses = [
            SimpleNamespace(returncode=1, stdout="", stderr="unknown"),
            SimpleNamespace(returncode=0, stdout="", stderr=""),
        ]
        with (
            patch("pc_control.verify", return_value={}),
            patch("pc_control.subprocess.run", side_effect=responses),
        ):
            with self.assertRaises(ValueError):
                control.collect(self.package)
        self.assertFalse(Path(str(self.campaign) + ".tar.gz").exists())


class SubmitEntryTests(unittest.TestCase):
    def fixture(self, fault=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        package, bundle, prepared, scratch, results = [
            root / name for name in ("package", "bundle", "prepared", "scratch", "results")
        ]
        for path in (package, bundle, prepared, scratch, results):
            path.mkdir()
        (package / "frozen").mkdir()
        C.save(package / "manifest.json", dict(files={}))
        image = C.CONTRACT["runtime"]["image_sha256"]
        C.save(
            package / "frozen/experiment.json",
            dict(source_prepared=str(prepared), image_sha256=image),
        )
        C.save(package / "frozen/source-index.json", dict(fixed="graph"))
        C.save(prepared / "READY.json", dict(architecture="x86_64", image_sha256=image))
        C.save(prepared / "database-identity.json", dict(fixed="graph"))
        apptainer = root / "apptainer"
        apptainer.write_text("synthetic executable; never run\n")
        apptainer.chmod(0o700)
        if fault == "reserved":
            C.save(
                results / ("." + C.NAME + "-reservation.json"),
                dict(preserve="existing reservation"),
            )
        cfg = dict(synthetic_fixture=False, local_readiness="source_and_target_checks_passed")
        calls = []

        def run(command, **kw):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="12345\n", stderr="")

        with ExitStack() as stack:
            for name, kwargs in [
                ("pc_control.require_native_release", dict(return_value=cfg)),
                ("pc_control.verify", dict(return_value=cfg)),
                ("pc_control.protected", dict(return_value={"fixed": "protected"})),
                (
                    "pc_control.os.uname",
                    dict(return_value=SimpleNamespace(sysname="Linux", machine="x86_64")),
                ),
                (
                    "pc_resources.preflight",
                    dict(
                        side_effect=RuntimeError("Insufficient conservative quota")
                        if fault == "quota"
                        else None,
                        return_value={"quota": "synthetic"},
                    ),
                ),
                ("pc_control.subprocess.run", dict(side_effect=run)),
                ("sys.stdout", dict(new=io.StringIO())),
            ]:
                stack.enter_context(patch(name, **kwargs))
            stack.enter_context(
                patch.dict(
                    os.environ,
                    TORCH_RESULTS_ROOT=str(results),
                    TORCH_SCRATCH_ROOT=str(scratch),
                    TORCH_SLURM_ACCOUNT="torch_pr_288_courant",
                    TORCH_APPTAINER_BIN=str(apptainer),
                )
            )
            error = None
            try:
                control.submit(package, bundle, results)
                if fault is None:
                    with self.assertRaises(ValueError):
                        control.submit(package, bundle, results)
            except (RuntimeError, ValueError) as exc:
                error = exc
        return package, results, calls, error

    def test_actual_submit_reserves_once_after_scheduler_preflight(self):
        package, results, calls, error = self.fixture()
        self.assertIsNone(error)
        self.assertEqual(len(calls), 2)
        self.assertIn("--test-only", calls[0])
        self.assertNotIn("--test-only", calls[1])
        self.assertEqual(
            C.read(package / "submission-binding.json")["package_manifest_sha256"],
            C.sha(package / "manifest.json"),
        )
        reservation = C.read(results / ("." + C.NAME + "-reservation.json"))
        self.assertEqual(reservation["maximum_searches"], 0)
        self.assertEqual(reservation["allocations"], 1)
        self.assertFalse((results / ".torch-startup-attribution-v1-reservation.json").exists())

    def test_actual_quota_failure_does_not_spend_allowance(self):
        package, results, calls, error = self.fixture("quota")
        self.assertIsNotNone(error)
        self.assertEqual(calls, [])
        self.assertFalse((package / "submission-binding.json").exists())
        self.assertFalse((results / ("." + C.NAME + "-reservation.json")).exists())

    def test_existing_reservation_is_preserved_without_dispatch(self):
        package, results, calls, error = self.fixture("reserved")
        self.assertIsNotNone(error)
        self.assertEqual(calls, [])
        self.assertEqual(
            C.read(results / ("." + C.NAME + "-reservation.json")),
            dict(preserve="existing reservation"),
        )
