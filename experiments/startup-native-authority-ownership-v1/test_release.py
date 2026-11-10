"""Release-specific fault injection; no native executable or signal is used."""

import signal
import sys
import time
import unittest
from unittest.mock import Mock, patch

import nh_binding as B
import nh_common as C
import nh_guest as G
import nh_host as H
import nh_lifecycle as L
import nh_retention as R
import release_policy as P
import test_integration as old


class ReleaseHost(old.Base):
    def scenario(
        self, receipt=0.0, began=0.0, delay=0, operation="seal", fail_signal=None, shared=None
    ):
        now = [0.0]
        known = self.known()
        work = self.directory("work")
        (work / "diagnostic").write_text("preserve")
        root = self.directory("local-release")
        ctx = {
            "original": str(known),
            "inner": "/stage",
            "workspace": "/workspace",
            "work": str(work),
        }
        observed = []

        def prepare(*a):
            return ctx

        def guest(ctx, ready, store):
            now[0] = receipt
            ready(ctx["binding_sha256"], began)
            if shared is not None:
                ctx["_host_post_started"] = shared
            return {"status": "complete"}

        def control(store, result):
            if "publication_started" in result:
                observed.append(
                    (
                        "control",
                        signal.getsignal(signal.SIGTERM),
                        signal.getitimer(signal.ITIMER_REAL)[0],
                    )
                )
                if operation == "control":
                    now[0] += delay
                    if fail_signal:
                        signal.getsignal(fail_signal)(fail_signal, None)
            original_control(store, result)

        def seal(store, complete):
            observed.append(
                ("seal", signal.getsignal(signal.SIGALRM), signal.getitimer(signal.ITIMER_REAL)[0])
            )
            if operation == "seal":
                now[0] += delay
                if fail_signal:
                    signal.getsignal(fail_signal)(fail_signal, None)
            original_seal(store, complete)

        original_control, original_seal = R.RawStore.control, R.RawStore.seal
        with patch.object(R.RawStore, "control", control), patch.object(R.RawStore, "seal", seal):
            result = H.execute(
                root, prepare, guest, lambda *a: None, clock=lambda: now[0], initial_context=ctx
            )
        return result, root, observed, now[0]

    def test_late_arrival_rejects_stale_timely_start(self):
        r, root, seen, now = self.scenario(241, 200)
        self.assertEqual(r["status"], "failed")
        self.assertIsNone(r["ready_admission"])
        self.assertTrue(r["retention_complete"])

    def test_arrival_boundary240_is_admitted(self):
        r, root, seen, now = self.scenario(240, 200)
        self.assertEqual(r["status"], "pass")
        self.assertEqual(C.read(root / "readiness.json")["received"], 240)

    def test_future_guest_start_rejected(self):
        self.assertEqual(self.scenario(200, 201)[0]["status"], "failed")

    def test_nan_guest_start_rejected(self):
        self.assertEqual(self.scenario(200, float("nan"))[0]["status"], "failed")

    def test_boolean_guest_start_rejected(self):
        self.assertEqual(self.scenario(200, True)[0]["status"], "failed")

    def test_returned_finished_includes_seal(self):
        r, root, seen, now = self.scenario(delay=5)
        self.assertEqual(r["finished"], now)
        self.assertEqual(r["finished"] - r["publication_started"], 5)

    def test_returned_finished_includes_control(self):
        r, root, seen, now = self.scenario(delay=7, operation="control")
        self.assertEqual(r["finished"], 7)

    def test_control_explicitly_precedes_publication(self):
        r, root, seen, now = self.scenario(delay=1)
        record = C.read(root / "CONTROL.json")["record"]
        self.assertNotIn("finished", record)
        self.assertTrue(record["completion_requires_successful_exit"])

    def test_late_seal_cannot_return_pass(self):
        with self.assertRaises(TimeoutError):
            self.scenario(delay=241)

    def test_late_control_cannot_return_pass(self):
        with self.assertRaises(TimeoutError):
            self.scenario(delay=241, operation="control")

    def test_term_handler_active_during_seal(self):
        with self.assertRaises(TimeoutError):
            self.scenario(fail_signal=signal.SIGTERM)

    def test_alarm_handler_active_during_control(self):
        with self.assertRaises(TimeoutError):
            self.scenario(operation="control", fail_signal=signal.SIGALRM)

    def test_publication_alarm_is_armed(self):
        r, root, seen, now = self.scenario()
        self.assertTrue(all(callable(h) and seconds > 0 for name, h, seconds in seen))

    def test_host_restores_all_four_handlers(self):
        before = {s: signal.getsignal(s) for s in L.INTERRUPTS}
        self.scenario()
        self.assertEqual(before, {s: signal.getsignal(s) for s in L.INTERRUPTS})

    def test_shared_post_is_not_reset_after_adapter_cleanup(self):
        r, root, seen, now = self.scenario(200, 200, shared=190)
        self.assertEqual(r["post_started"], 190)
        self.assertEqual(r["post_deadline"], 430)

    def test_existing_campaign_preserved_before_any_control_write(self):
        root = self.directory("local-existing")
        (root / "evidence").write_bytes(b"prior")
        with self.assertRaises(FileExistsError):
            H.execute(root, Mock(), Mock(), Mock())
        self.assertEqual(C.inventory(root), {"evidence": C.sha(root / "evidence")})


class InterruptionTests(old.Base):
    def test_all_original_signals_raise_into_cleanup(self):
        for number in L.INTERRUPTS:
            with L.interruptions():
                with self.assertRaises(TimeoutError):
                    signal.getsignal(number)(number, None)

    def test_nested_scope_restores_outer_handlers(self):
        with L.interruptions():
            outer = {s: signal.getsignal(s) for s in L.INTERRUPTS}
            with L.interruptions():
                self.assertNotEqual(outer, {s: signal.getsignal(s) for s in L.INTERRUPTS})
            self.assertEqual(outer, {s: signal.getsignal(s) for s in L.INTERRUPTS})

    def test_standalone_guest_installs_handlers_before_core_access(self):
        before = {s: signal.getsignal(s) for s in L.INTERRUPTS}
        seen = []

        def core(path):
            seen.extend(signal.getsignal(s) for s in L.INTERRUPTS)
            raise ValueError("synthetic core failure")

        with patch.object(G, "core", core), self.assertRaises(ValueError):
            G.run(
                {"inner": "/a", "workspace": "/b", "work": "/c", "science": "/d", "original": "/e"},
                None,
                None,
                None,
            )
        self.assertTrue(all(callable(s) for s in seen))
        self.assertEqual(before, {s: signal.getsignal(s) for s in L.INTERRUPTS})

    def test_expired_publication_does_not_start_io(self):
        performed = []
        with self.assertRaises(TimeoutError), L.endpoint(1, lambda: 1):
            performed.append(True)
        self.assertFalse(performed)

    def test_publication_overrun_detected_and_alarm_cancelled(self):
        now = [0]
        with self.assertRaises(TimeoutError), L.endpoint(5, lambda: now[0]):
            now[0] = 5
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL)[0], 0)

    def test_guest_publication_uses_cleanup_endpoint(self):
        # Exercise the real guest flow with original budget.phase and tiny mocked
        # science adapters; full real science is independently replayed.
        sys.path.insert(0, str(C.INNER))
        import proofs

        now = [0.0]
        store = Mock()
        runner = Mock()

        def publish(name, status):
            self.assertEqual(name, "guest-status.json")
            self.assertEqual(status["cleanup_deadline"], 600)
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)
            now[0] = 601

        store.json.side_effect = publish
        context = {
            "inner": "/inner",
            "workspace": "/workspace",
            "work": "/work",
            "science": "/raw",
            "original": str(C.INNER),
            "binding_sha256": "key",
        }

        def read(path):
            return {"candidate": "/candidate", "source_inventory": {}}

        with (
            patch.object(G, "core", return_value=Mock()),
            patch.object(G, "read", read),
            patch.object(G, "inventory", return_value={}),
            patch.object(G.shutil, "copytree"),
            patch.object(proofs, "validate", return_value={}),
            patch.object(time, "monotonic", lambda: now[0]),
            self.assertRaises(TimeoutError),
        ):
            G.run(context, runner, lambda *a: {"guest_end": 3000}, store)
        runner.stop.assert_called_once_with(600)


class FakeGroups(L.OwnedGroups):
    def __init__(self, members=(11, 12), term_stops=True, kill_stops=True):
        self.live, self.term_stops, self.kill_stops = members, term_stops, kill_stops
        self.sent = []

    def validate(self, ctx):
        return True

    def members(self, handle):
        if handle != "owned":
            raise RuntimeError("Foreign ownership")
        return self.live

    def send(self, handle, number):
        self.members(handle)
        self.sent.append(number)
        if (number == signal.SIGTERM and self.term_stops) or (
            number == signal.SIGKILL and self.kill_stops
        ):
            self.live = ()


class GroupTests(old.Base):
    def run_stop(self, groups, end=20, child=None, handle="owned"):
        now = [0.0]

        def pause(seconds):
            now[0] += seconds

        child = child or Mock(poll=Mock(return_value=0))
        return L.stop_owned(groups, handle, child, end, lambda: now[0], pause)

    def test_exited_leader_does_not_hide_descendant(self):
        group = FakeGroups((12,))
        self.assertTrue(self.run_stop(group)["whole_group_absent"])
        self.assertEqual(group.sent, [signal.SIGTERM])

    def test_term_escalates_to_kill_within_same_endpoint(self):
        group = FakeGroups(term_stops=False)
        self.assertTrue(self.run_stop(group)["direct_child_reaped"])
        self.assertEqual(group.sent, [signal.SIGTERM, signal.SIGKILL])

    def test_live_group_after_kill_fails(self):
        with self.assertRaises(RuntimeError):
            self.run_stop(FakeGroups(term_stops=False, kill_stops=False))

    def test_unknown_membership_fails_without_signals(self):
        group = FakeGroups(None)
        with self.assertRaises(RuntimeError):
            self.run_stop(group)
        self.assertEqual(group.sent, [])

    def test_foreign_handle_fails_without_signals(self):
        group = FakeGroups()
        with self.assertRaises(RuntimeError):
            self.run_stop(group, handle="foreign")
        self.assertEqual(group.sent, [])

    def test_expired_endpoint_prevents_signal(self):
        group = FakeGroups()
        with self.assertRaises(TimeoutError):
            self.run_stop(group, end=0)
        self.assertEqual(group.sent, [])

    def test_term_cannot_borrow_kill_time_past_endpoint(self):
        group = FakeGroups(term_stops=False)
        with self.assertRaises(TimeoutError):
            self.run_stop(group, end=1)
        self.assertEqual(group.sent, [signal.SIGTERM])

    def test_empty_group_still_reaps_direct_child(self):
        child = Mock(poll=Mock(return_value=0))
        self.run_stop(FakeGroups(()), child=child)
        child.wait.assert_called_once()

    def test_unreaped_child_is_failure(self):
        with self.assertRaises(RuntimeError):
            self.run_stop(FakeGroups(()), child=Mock(poll=Mock(return_value=None)))

    def test_process_count_bound_is_unchanged(self):
        group = FakeGroups(tuple(range(1, 34)))
        with self.assertRaises(RuntimeError):
            self.run_stop(group)
        self.assertFalse(group.sent)

    def test_missing_controller_rejected_before_spawn(self):
        with self.assertRaises(RuntimeError):
            L.require_groups({})

    def test_default_controller_has_no_native_backend(self):
        with self.assertRaises(RuntimeError):
            L.require_groups({"process_control": L.OwnedGroups()})

    def test_native_runner_requires_admission_below_first_gate(self):
        import nh_runner as runner

        with (
            patch.object(runner, "closed_native"),
            self.assertRaisesRegex(RuntimeError, "admission HOLD"),
        ):
            runner.NativeRunner({"process_control": FakeGroups()}, None, "/missing")


class BindingReleaseTests(old.Base):
    def test_valid_full_binding_is_shared_validator_input(self):
        binding = self.binding()
        self.assertEqual(B.validate_binding(binding), C.digest(binding))

    def test_self_hashed_changed_limits_cannot_enter_guest(self):
        binding = self.binding()
        binding["limits"]["wall_seconds"] += 1
        with self.assertRaises(ValueError):
            B.validate_target_binding({"binding": binding, "sha256": C.digest(binding)}, self.root)

    def test_self_hashed_changed_phase_cannot_enter_guest(self):
        binding = self.binding()
        binding["phase_seconds"]["cpu"] = True
        with self.assertRaises(ValueError):
            B.validate_binding(binding)

    def test_binding_paths_revalidated_on_import(self):
        binding = self.binding()
        binding["paths"]["inner"] = "/input:rw"
        with self.assertRaises(ValueError):
            B.validate_binding(binding)

    def test_exact_manifest_not_just_envelope_digest_required(self):
        binding = self.binding()
        (self.root / "manifest.json").write_text("{}")
        with self.assertRaises(ValueError):
            B.validate_target_binding({"binding": binding, "sha256": C.digest(binding)}, self.root)

    def test_site_verified_label_cannot_grant_authority(self):
        with self.assertRaises(RuntimeError):
            B.require_native_admission(
                {"authority": "site_verified", "job_id": "99999999", "native_release": True}
            )

    def test_all_prior_jobs_stay_spent(self):
        for job in P.SPENT:
            with self.assertRaises(RuntimeError):
                B.require_native_admission({"job_id": job, "allowance": "reuse"})


class ReviewPolicyTests(unittest.TestCase):
    def good(self):
        return {
            "status": "pass",
            "started": 0,
            "post_started": 200,
            "publication_started": 210,
            "finished": 215,
            "post_deadline": 440,
        }

    def test_control_and_lock_success_without_exit_is_insufficient(self):
        self.assertFalse(P.completed(None, self.good()))

    def test_failed_exit_overrides_artifact_success(self):
        self.assertFalse(P.completed({"exit_code": 1, "observed_finished": 216}, self.good()))

    def test_late_independent_exit_cannot_qualify(self):
        self.assertFalse(P.completed({"exit_code": 0, "observed_finished": 441}, self.good()))

    def test_successful_exit_must_follow_publication(self):
        self.assertFalse(P.completed({"exit_code": 0, "observed_finished": 214}, self.good()))

    def test_completion_consistency_does_not_grant_authority(self):
        r = P.review(
            {
                "host_result": self.good(),
                "exit_observation": {"exit_code": 0, "observed_finished": 216},
            }
        )
        self.assertTrue(r["local_completion_consistent"])
        self.assertEqual(r["status"], "HOLD")
        self.assertFalse(r["native_release"])

    def test_synthetic_all_positive_claims_still_hold(self):
        r = P.review(
            {"native_release": True, "site_verified": True, "allowance": "fresh", "all_pass": True}
        )
        self.assertEqual(r["qualification_handoff"]["status"], "HOLD")
        self.assertEqual(r["resource_and_B2f"]["status"], "HOLD")

    def test_qualification_and_downstream_missing_facts_are_distinct(self):
        r = P.review({})
        self.assertFalse(
            set(r["qualification_handoff"]["missing"]) & set(r["resource_and_B2f"]["missing"])
        )
        self.assertFalse(r["fresh_allowance_issued"])

    def test_boolean_exit_code_cannot_alias_zero(self):
        self.assertFalse(P.completed({"exit_code": False, "observed_finished": 216}, self.good()))


class AdditionalReleaseTests(old.Base):
    def test_host_native_still_checks_admission_below_closed_gate(self):
        import nh_native

        store = self.store()
        C.save(store.root / "binding.json", {"binding": {}, "sha256": "key"})
        ctx = {"inner": "/stage", "binding_sha256": "key"}
        with (
            patch.dict(nh_native.os.environ, SLURM_JOB_ID="99999999"),
            patch.object(nh_native, "closed_native"),
            patch.object(nh_native, "validate_target_binding", return_value="key") as validate,
            patch.object(nh_native, "validate_host_context") as mounts,
            self.assertRaisesRegex(RuntimeError, "admission HOLD"),
        ):
            nh_native.launch(ctx, None, store)
        validate.assert_called_once()
        mounts.assert_called_once()

    def test_host_context_cannot_substitute_mount_source(self):
        b = self.binding()
        ctx = {
            "original": "/different",
            "inner": "/stage",
            "workspace": "/workspace",
            "integration": str(C.HERE),
            "image": "/missing",
        }
        with self.assertRaises(ValueError):
            B.validate_host_context(b, ctx, "/result")

    def test_host_context_requires_image_digest(self):
        b = self.binding()
        ctx = {
            "original": "/input",
            "inner": "/stage",
            "workspace": "/workspace",
            "integration": str(C.HERE),
            "image": "/image",
        }
        with patch.object(B, "sha", return_value="0" * 64), self.assertRaises(ValueError):
            B.validate_host_context(b, ctx, "/result")

    def test_native_runner_preserves_handle_when_group_stop_fails(self):
        import nh_runner

        runner = nh_runner.NativeRunner.__new__(nh_runner.NativeRunner)
        runner.child = Mock(poll=Mock(return_value=0))
        runner.owned_handle = "owned"
        runner.process_control = FakeGroups(None)
        with self.assertRaises(RuntimeError):
            runner.stop(time.monotonic() + 1)
        self.assertIsNotNone(runner.child)
        self.assertEqual(runner.owned_handle, "owned")

    def test_original_tests_and_retention_bytes_unchanged(self):
        prior = C.ROOT / "agent/experiments/startup-native-harness-integration-v1"
        for name in ("test_integration.py", "nh_retention.py", "nh_materialize.py"):
            self.assertEqual(C.sha(C.HERE / name), C.sha(prior / name))
