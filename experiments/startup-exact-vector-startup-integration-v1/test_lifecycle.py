"""Deterministic exit/read races and cleanup cancellation on actual local entries."""

import json
import runpy
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ev_cleanup
import ev_host
import experiment as E
import pc_common as C
import sr_memory as M
import sr_sampler
from test_fixtures import complete_return, memory_fixture, relock, rewrite, runtime_fixture, stat
from test_host_resource import Process


class ProcessRaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.proc, self.leaf = memory_fixture(self.root)
        self.memory = M.Memory(100, proc=self.proc)
        self.status = self.proc / "200/status"
        self.normal_status = self.status.read_text()

    def missing(self):
        self.status.write_text(
            self.normal_status.replace("VmRSS:\t100 kB\n", "").replace("VmHWM:\t200 kB\n", "")
        )

    def stat_reads(self, values):
        original = self.memory.read.read
        sequence = iter(values)

        def read(path, *a, **kw):
            value = original(path, *a, **kw)
            if Path(path) == self.proc / "200/stat":
                value = next(sequence)
                if isinstance(value, Exception):
                    raise value
            return value

        return patch.object(self.memory.read, "read", side_effect=read)

    def test_missing_live_counters_still_fatal_after_one_confirmation(self):
        self.missing()
        before = self.memory.read.files
        with self.assertRaises(M.ProcessObservationError) as caught:
            self.memory.process(200)
        self.assertEqual(self.memory.read.files - before, 8)
        proof = caught.exception.observation
        self.assertEqual(proof["pid"], 200)
        self.assertEqual(len(proof["attempts"]), 2)
        self.assertLess(len(json.dumps(proof)), 2048)

    def test_exit_transition_requires_same_starttime_and_terminal_stat(self):
        self.missing()
        with self.stat_reads([stat(200, 2000), stat(200, 2000).replace(") S ", ") Z ")]):
            row = self.memory.process(200)
        self.assertEqual(row["availability"], "terminal_during_sample")
        self.assertEqual(row["starttime"], 2000)
        self.assertIsNone(row["VmRSS"])
        self.assertIsNone(row["VmHWM"])

    def test_disappearance_during_identity_bracket_is_explicit(self):
        self.missing()
        with self.stat_reads([stat(200, 2000), FileNotFoundError("gone")]):
            row = self.memory.process(200)
        self.assertEqual(row, dict(pid=200, availability="exited_during_sample"))

    def test_reused_pid_counters_discarded_within_sample(self):
        with self.stat_reads([stat(200, 2000), stat(200, 9999)]):
            row = self.memory.process(200)
        self.assertEqual(row["availability"], "pid_reused_during_sample")
        self.assertNotIn("VmRSS", row)
        self.assertNotIn("starttime", row)

    def test_live_missing_counter_can_recover_on_single_stable_confirmation(self):
        self.missing()
        original = self.memory.read.read
        reads = [0]

        def read(path, *a, **kw):
            value = original(path, *a, **kw)
            if Path(path) == self.status:
                reads[0] += 1
                if reads[0] == 2:
                    return self.normal_status
            return value

        with patch.object(self.memory.read, "read", side_effect=read):
            row = self.memory.process(200)
        self.assertEqual(row["observation_attempts"], 2)
        self.assertEqual(row["VmRSS"], 100)

    def test_pid_reuse_on_confirmation_does_not_merge_observations(self):
        self.missing()
        with self.stat_reads([stat(200, 2000), stat(200, 2000), stat(200, 9999), stat(200, 9999)]):
            row = self.memory.process(200)
        self.assertEqual(row["availability"], "pid_reused_during_sample")
        self.assertNotIn("VmHWM", row)

    def test_terminal_state_cannot_return_to_live_same_identity(self):
        with self.stat_reads([stat(200, 2000).replace(") S ", ") Z "), stat(200, 2000)]):
            with self.assertRaises(M.ProcessObservationError):
                self.memory.process(200)

    def test_missing_live_rss_only_is_not_terminal(self):
        self.status.write_text(self.normal_status.replace("VmRSS:\t100 kB\n", ""))
        with self.assertRaises(M.ProcessObservationError):
            self.memory.process(200)

    def test_bad_rss_units_still_fatal(self):
        self.status.write_text(self.normal_status.replace("100 kB", "100 MB"))
        with self.assertRaises(M.ProcessObservationError):
            self.memory.process(200)

    def test_changed_membership_is_not_an_exit(self):
        (self.proc / "200/cgroup").write_text("0::/other\n")
        with self.assertRaises(RuntimeError):
            self.memory.process(200)

    def test_missing_counter_confirmation_uses_existing_read_cap(self):
        self.missing()
        self.memory.read.files = 499997
        with self.assertRaises(RuntimeError):
            self.memory.process(200)
        self.assertEqual(self.memory.read.files, 500000)

    def test_actual_sampler_failure_retains_structured_observation(self):
        self.missing()
        out = self.root / "out"
        out.mkdir()
        with (
            patch("sr_sampler.signal.signal"),
            patch("sr_sampler.os.sched_getaffinity", side_effect=[{0, 1, 2, 3}, {3}], create=True),
            patch("sr_sampler.os.sched_setaffinity", create=True),
            patch("sr_sampler.select_cores", return_value={"selected": [0, 1, 2, 3]}),
        ):
            with self.assertRaises(RuntimeError):
                sr_sampler.run(out, 100, memory_factory=lambda p: self.memory)
        summary = C.read(out / "memory-summary.json")
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["error"]["observation"]["pid"], 200)
        self.assertEqual(summary, C.read(out / "memory-health.json"))


class CleanupPolicyTests(unittest.TestCase):
    def test_cleanup_transition_is_protected_before_stage_registration(self):
        state = ev_cleanup.CleanupSignals(clock=lambda: 10)
        state.begin()
        state.handle(signal.SIGTERM, "epoch1", 3000)
        self.assertTrue(state.proof()["failed"])
        self.assertEqual(state.records[0]["stage"], "final_cleanup")

    def test_repeated_cancellation_during_cleanup_is_idempotent_and_failed(self):
        state = ev_cleanup.CleanupSignals(clock=lambda: 10)
        for _ in range(20):
            state.handle(signal.SIGTERM, "final_cleanup", 600)
        self.assertTrue(state.proof()["failed"])
        self.assertEqual(state.count, 20)
        self.assertEqual(len(state.records), 8)

    def test_cancellation_before_cleanup_enters_failure_path(self):
        state = ev_cleanup.CleanupSignals(clock=lambda: 10)
        state.handle(signal.SIGTERM, "epoch0", 120)
        with self.assertRaises(InterruptedError):
            state.check("epoch0")

    def test_alarm_still_interrupts_cleanup(self):
        state = ev_cleanup.CleanupSignals(clock=lambda: 10)
        with self.assertRaises(TimeoutError):
            state.handle(signal.SIGALRM, "final_cleanup", 600)

    def test_late_cancellation_cannot_extend_absolute_deadline(self):
        state = ev_cleanup.CleanupSignals(clock=lambda: 600)
        state.handle(signal.SIGTERM, "final_cleanup", 600)
        budget = C.Budget(clock=lambda: 0)
        budget.enter("final_cleanup")
        budget.clock = lambda: 600
        with self.assertRaises(RuntimeError):
            ev_cleanup.arm_remaining(budget, lambda *a: self.fail("Deadline extended"))

    def test_rearming_uses_remaining_time_without_reset(self):
        tick = [0]
        budget = C.Budget(clock=lambda: tick[0])
        budget.enter("final_cleanup")
        calls = []
        tick[0] = 10
        ev_cleanup.arm_remaining(budget, lambda kind, value: calls.append(value))
        tick[0] = 20
        ev_cleanup.arm_remaining(budget, lambda kind, value: calls.append(value))
        self.assertEqual(calls, [590, 580])
        tick[0] = 600
        with self.assertRaises(RuntimeError):
            ev_cleanup.arm_remaining(budget, lambda *a: self.fail("Timer reset after expiry"))

    def monitor(self, phase, deadline=10):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name)
        rewrite(out / "memory-health.json", dict(status="failed"))
        rewrite(out / "progress.json", dict(phase=phase))
        child, sampler = Process(None, True), Process(1)
        tick = [0]

        def sleep(value):
            tick[0] += value
            if tick[0] >= 0.5:
                child.returncode = 1

        with self.assertRaises((RuntimeError, TimeoutError)):
            ev_host.monitor(child, sampler, out, deadline, clock=lambda: tick[0], sleep=sleep)
        return child, C.read(out / "cleanup-request.json")

    def test_host_does_not_interrupt_shutdown_already_in_progress(self):
        child, request = self.monitor("finalize_verify_cleanup")
        self.assertFalse(child.terminated)
        self.assertFalse(request["signal_sent"])
        self.assertEqual(request["reason"], "required_memory_sampler_lost")

    def test_host_requests_cancellation_once_before_cleanup(self):
        child, request = self.monitor("snapshot_load")
        self.assertTrue(child.terminated)
        self.assertTrue(request["signal_sent"])

    def test_host_observer_loss_does_not_extend_runtime_deadline(self):
        child, request = self.monitor("finalize_verify_cleanup", deadline=0.25)
        self.assertFalse(child.terminated)
        self.assertFalse(request["signal_sent"])

    def test_production_build_is_disabled_before_any_output(self):
        with self.assertRaisesRegex(RuntimeError, "production capsule creation is disabled"):
            E.build(Path("/must-not-create-a-native-capsule"))

    def test_native_command_line_entries_are_disabled(self):
        for name in ("pc_control.py", "pc_job.py", "pc_runtime.py", "sr_sampler.py"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(RuntimeError, "Offline A3 correction only"):
                    runpy.run_path(str(E.HERE / name), run_name="__main__")


class RuntimeLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.seed = E.build(Path(cls.tmp.name) / "seed", testing=True)

    def fixture(self, fault=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name), runtime_fixture(Path(tmp.name) / "actual", self.seed, fault)

    def test_actual_cleanup_cancellation_finishes_proofs_but_stays_failed(self):
        root, result = self.fixture("cleanup_cancel")
        out = result["out"]
        self.assertEqual(result["status"]["status"], "failed")
        self.assertTrue(result["status"]["final_integrity_verified"])
        self.assertEqual(
            C.read(out / "cleanup.json"),
            dict(errors=[], all_readers_closed=True, databases_stopped=True),
        )
        self.assertTrue((out / "stopped-copies.json").exists())
        self.assertEqual(C.read(out / "source-before.json"), C.read(out / "source-after.json"))
        self.assertEqual(C.read(out / "ev-cancellation.json")["count"], 4)
        self.assertFalse(C.read(out / "LOCK.json")["complete"])

    def test_actual_cancellation_at_cleanup_entry_keeps_reserved_proofs(self):
        root, result = self.fixture("cleanup_enter_cancel")
        out = result["out"]
        self.assertEqual(result["status"]["status"], "failed")
        self.assertTrue(result["status"]["final_integrity_verified"])
        self.assertTrue((out / "stopped-copies.json").exists())
        self.assertEqual(C.read(out / "cleanup.json")["errors"], [])
        self.assertEqual(C.read(out / "ev-cancellation.json")["count"], 1)

    def test_actual_cancellation_safepoint_rejects_further_sql(self):
        root, result = self.fixture("cancel_before_sql")
        self.assertEqual(result["status"]["status"], "failed")
        # The unchanged trace conservatively reserves a scan before its SQL
        # budget check. Cancellation rejects that attempt before driver execution.
        self.assertEqual(result["status"]["full_scans"], {"data": 1})
        self.assertEqual(result["status"]["reader_connections"], 0)
        self.assertTrue(C.read(result["out"] / "cleanup.json")["databases_stopped"])
        self.assertEqual(set(result["stopped"]), set(C.CELLS))
        from pc_trace import DATA_SQL

        self.assertFalse(any(text == DATA_SQL for c in result["opened"] for text, _ in c.executed))

    def test_actual_observer_cleanup_marker_prevents_completion(self):
        root, result = self.fixture("observer_cleanup")
        self.assertEqual(result["status"]["status"], "failed")
        self.assertTrue((result["out"] / "stopped-copies.json").exists())
        self.assertEqual(C.read(result["out"] / "cleanup.json")["errors"], [])
        self.assertFalse(C.read(result["out"] / "LOCK.json")["complete"])

    def test_actual_expired_cleanup_does_not_start_more_heavy_steps(self):
        root, result = self.fixture("cleanup_deadline")
        self.assertEqual(result["status"]["status"], "failed")
        self.assertEqual(result["stopped"], ["partial640"])
        self.assertFalse((result["out"] / "stopped-copies.json").exists())
        self.assertFalse((result["out"] / "source-after.json").exists())
        self.assertFalse(C.read(result["out"] / "cleanup.json")["databases_stopped"])

    def replay_fixture(self):
        root, actual = self.fixture()
        self.assertIsNone(actual["error"])
        return root, *complete_return(root, actual)

    def test_forged_positive_status_does_not_hide_cancellation(self):
        root, campaign, package = self.replay_fixture()
        rewrite(campaign / "run/ev-cancellation.json", dict(count=1, records=[], failed=True))
        relock(campaign / "run")
        with self.assertRaises(ValueError):
            E.analyze(campaign, root / "analysis", package)
        self.assertFalse((root / "analysis").exists())

    def test_relocked_observer_loss_marker_still_prevents_positive_replay(self):
        root, campaign, package = self.replay_fixture()
        rewrite(campaign / "run/cleanup-request.json", dict(reason="required_memory_sampler_lost"))
        relock(campaign / "run")
        with self.assertRaises(ValueError):
            E.analyze(campaign, root / "analysis", package)

    def test_cancellation_proof_rejects_boolean_float_and_numeric_false_aliases(self):
        root, campaign, package = self.replay_fixture()
        for value in (
            dict(count=False, records=[], failed=False),
            dict(count=0.0, records=[], failed=False),
            dict(count=0, records=[], failed=0),
        ):
            with self.subTest(value=value):
                rewrite(campaign / "run/ev-cancellation.json", value)
                relock(campaign / "run")
                with self.assertRaises(ValueError):
                    E.analyze(campaign, root / "analysis", package)

    def test_missing_cancellation_proof_fails_closed(self):
        root, campaign, package = self.replay_fixture()
        (campaign / "run/ev-cancellation.json").unlink()
        relock(campaign / "run")
        with self.assertRaises(FileNotFoundError):
            E.analyze(campaign, root / "analysis", package)
