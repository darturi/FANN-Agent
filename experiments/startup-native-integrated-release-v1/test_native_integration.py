"""Admission/controller/namespace failure boundaries; no real scheduler or network."""

import ctypes
import errno
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import ni_authority as A
import ni_control as C
import ni_site as S
import ni_storage as D
from nh_common import HERE, config, inventory, read, save, sha
from ni_binding import Campaign
from ni_guest_entry import commands, recipe
from ni_native import runtime_seconds


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.root.chmod(0o700)

    def directory(self, name):
        p = self.root / name
        p.mkdir(mode=0o700)
        return p

    def job(self):
        return {
            "JobId": "99999123",
            "UserId": "fixture(501)",
            "Account": "torch_pr_fixture",
            "Comment": "a3-ni-fixture",
            "JobState": "RUNNING",
            "TimeLimit": "01:00:00",
            "NumNodes": "1",
            "NumCPUs": "4",
            "NumTasks": "1",
            "CPUs/Task": "4",
            "MinMemoryNode": "32G",
            "NodeList": "cs621",
            "Requeue": "0",
            "Restarts": "0",
            "RunTime": "00:00:03",
        }

    def approval(self):
        return {
            "schema": "a3.explicit-approval.v1",
            "approval": A.APPROVAL_TEXT,
            "plan_sha256": "a" * 64,
            "uid": 501,
            "nonce": "b" * 32,
            "allocations": 1,
            "ANN_searches": 0,
            "exact_searches": 0,
            "retry": False,
        }

    def ticket(self):
        return {
            "schema": "a3.host-delegation.v1",
            "domain": "local-kernel-test",
            "nonce": "a" * 32,
            "binding_sha256": "b" * 64,
            "code_sha256": "c" * 64,
            "image_sha256": config()["image_sha256"],
            "archive_sha256": config()["original_archive_sha256"],
            "manifest_sha256": config()["original_manifest_sha256"],
            "host_started": 10,
            "latest_ready": 250,
            "maximum_guest_end": 3250,
            "host_post_end": 3490,
            "uid": 501,
            "job_id": "fixture",
            "commands": [["$PYTHON", "fixture"]],
            "budget_inode": 3,
            "budget_device": 4,
            "budget_path": "/work/observer-budget",
            "claims_path": "/work/guest-claims",
            "limits": config()["limits"],
            "host_boot": "fixture-boot",
        }


class ApprovalCases(Base):
    def test_exact_distinct_approval_passes(self):
        self.assertEqual(A.approved(self.approval(), "a" * 64, 501)["allocations"], 1)

    def test_pending_approval_is_not_permission(self):
        r = self.approval()
        r["approval"] = "pending"
        with self.assertRaises(RuntimeError):
            A.approved(r, "a" * 64, 501)

    def test_boolean_allocation_is_rejected(self):
        r = self.approval()
        r["allocations"] = True
        with self.assertRaises(RuntimeError):
            A.approved(r, "a" * 64, 501)

    def test_changed_plan_is_rejected(self):
        with self.assertRaises(RuntimeError):
            A.approved(self.approval(), "d" * 64, 501)

    def test_other_uid_is_rejected(self):
        with self.assertRaises(RuntimeError):
            A.approved(self.approval(), "a" * 64, 502)

    def test_nonzero_search_allowance_is_rejected(self):
        for key in ("ANN_searches", "exact_searches"):
            r = self.approval()
            r[key] = 1
            with self.assertRaises(RuntimeError):
                A.approved(r, "a" * 64, 501)

    def test_retry_is_not_authorized(self):
        r = self.approval()
        r["retry"] = True
        with self.assertRaises(RuntimeError):
            A.approved(r, "a" * 64, 501)

    def test_self_asserted_native_flag_is_rejected(self):
        r = self.approval()
        r["native_release"] = True
        with self.assertRaises(RuntimeError):
            A.approved(r, "a" * 64, 501)

    def test_submit_without_approval_never_queries_or_spawns(self):
        state = self.directory("state")
        with (
            patch.object(C, "verify", return_value={}),
            patch.object(C, "state_root", return_value=state),
            patch.object(C, "site_check") as site,
            patch.object(C, "bounded_command") as spawn,
            self.assertRaises(FileNotFoundError),
        ):
            C.submit(self.root)
        site.assert_not_called()
        spawn.assert_not_called()

    def test_old_reservation_blocks_new_approval(self):
        state = self.directory("state")
        (state.parent / ("." + C.NAME + "-reservation.json")).write_text("{}")
        with (
            patch.object(C, "verify", return_value={}),
            patch.object(C, "state_root", return_value=state),
            self.assertRaises(RuntimeError),
        ):
            C.approve_command(self.root, A.APPROVAL_TEXT)


class SchedulerCases(Base):
    def valid(self, r=None):
        return S.validate_job(
            r or self.job(), "99999123", 501, "torch_pr_fixture", "a3-ni-fixture", "cs621"
        )

    def test_complete_scheduler_record_passes(self):
        self.assertEqual(self.valid()["job_id"], "99999123")

    def test_changed_uid_holds(self):
        r = self.job()
        r["UserId"] = "other(502)"
        with self.assertRaises(ValueError):
            self.valid(r)

    def test_changed_comment_holds(self):
        r = self.job()
        r["Comment"] = "old-plan"
        with self.assertRaises(ValueError):
            self.valid(r)

    def test_nonrunning_state_holds(self):
        r = self.job()
        r["JobState"] = "COMPLETED"
        with self.assertRaises(ValueError):
            self.valid(r)

    def test_wrong_resources_hold(self):
        for key, value in [("NumCPUs", "8"), ("TimeLimit", "02:00:00"), ("MinMemoryNode", "64G")]:
            r = self.job()
            r[key] = value
            with self.assertRaises(ValueError):
                self.valid(r)

    def test_requeue_is_not_an_allowance(self):
        r = self.job()
        r["Requeue"] = "1"
        with self.assertRaises(ValueError):
            self.valid(r)

    def test_restarted_job_is_not_a_fresh_attempt(self):
        r = self.job()
        r["Restarts"] = "1"
        with self.assertRaises(ValueError):
            self.valid(r)

    def test_array_is_rejected(self):
        r = self.job()
        r["ArrayJobId"] = "99999123"
        with self.assertRaises(ValueError):
            self.valid(r)

    def test_all_spent_ids_are_rejected(self):
        for job in S.SPENT:
            r = self.job()
            r["JobId"] = job
            with self.assertRaises(ValueError):
                S.validate_job(r, job, 501, "torch_pr_fixture", "a3-ni-fixture", "cs621")

    def test_duplicate_fields_are_ambiguous(self):
        with self.assertRaises(ValueError):
            S.parse_record("JobId=1 JobId=2")

    def test_oneliner_preserves_slash_field_and_comment(self):
        r = S.parse_record("JobId=3 CPUs/Task=4 Comment=single plan nonce NodeList=cs621")
        self.assertEqual((r["CPUs/Task"], r["Comment"]), ("4", "single plan nonce"))

    def test_oversize_record_holds(self):
        with self.assertRaises(ValueError):
            S.parse_record("x" * 70000)

    def test_invalid_elapsed_time_holds(self):
        with self.assertRaises(ValueError):
            runtime_seconds("unavailable")

    def test_elapsed_time_accounts_for_allocation_start(self):
        self.assertEqual(runtime_seconds("1-00:00:03"), 86403)

    def test_scheduler_config_override_is_rejected(self):
        with patch.dict(os.environ, SLURM_CONF_SERVER="untrusted"), self.assertRaises(ValueError):
            S.clean_environment()

    def test_loader_override_is_rejected(self):
        with patch.dict(os.environ, LD_PRELOAD="/tmp/x"), self.assertRaises(ValueError):
            S.clean_environment()


class ScopeCases(Base):
    def test_v2_job_scope_matches_kernel(self):
        r = S.resolve_scope(
            "0::/system/slurm/job_99999123/step_batch/user/task_0\n",
            "1 0 0:1 / /cg rw - cgroup2 cgroup rw\n",
            "99999123",
        )
        self.assertEqual(r["path"], "/cg/system/slurm/job_99999123")

    def test_v1_memory_scope_matches_kernel(self):
        r = S.resolve_scope(
            "3:memory:/slurm/job_99999123/step_batch\n",
            "1 0 0:1 / /cg rw - cgroup cgroup rw,memory\n",
            "99999123",
        )
        self.assertEqual(r["path"], "/cg/slurm/job_99999123")

    def test_wrong_job_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            S.resolve_scope(
                "0::/job_123/step\n", "1 0 0:1 / /cg rw - cgroup2 cgroup rw\n", "99999123"
            )

    def test_ambiguous_mount_is_rejected(self):
        with self.assertRaises(ValueError):
            S.resolve_scope("0::/job_3\n", "1 0 0:1 / /cg rw - cgroup2 cgroup rw\n" * 2, "3")

    def test_parent_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            S.resolve_scope("0::/../job_3\n", "1 0 0:1 / /cg rw - cgroup2 cgroup rw\n", "3")

    def test_read_write_ticket_mount_is_rejected(self):
        with self.assertRaises(RuntimeError):
            A.readonly_mount("1 0 0:1 / /authority rw - ext4 /dev/x rw\n", "/authority/ticket.json")

    def test_readonly_ticket_mount_is_accepted(self):
        A.readonly_mount("1 0 0:1 / /authority ro - ext4 /dev/x rw\n", "/authority/ticket.json")

    def test_ram_filesystem_is_rejected_for_native_stage(self):
        path = self.directory("job")
        text = f"1 0 0:1 / {path} rw - tmpfs tmpfs rw\n"
        with self.assertRaises(RuntimeError):
            D.node_private(path, text)

    def test_unknown_quota_is_not_unlimited(self):
        fake = Mock()

        def call(*args):
            ctypes.set_errno(errno.EPERM)
            return -1

        fake.quotactl.side_effect = call
        with patch.object(D.ctypes, "CDLL", return_value=fake), self.assertRaises(RuntimeError):
            D.quota_disabled("/dev/x")

    def test_all_three_disabled_quota_types_are_required(self):
        fake = Mock()

        def call(*args):
            ctypes.set_errno(errno.ESRCH)
            return -1

        fake.quotactl.side_effect = call
        with patch.object(D.ctypes, "CDLL", return_value=fake):
            self.assertEqual(len(D.quota_disabled("/dev/x")["kernel_queries"]), 3)


class DelegationCases(Base):
    def valid(self, r=None, now=20):
        return A.validate_ticket(r or self.ticket(), "c" * 64, 501, now)

    def test_complete_fixture_delegation_passes(self):
        self.assertEqual(self.valid()["domain"], "local-kernel-test")

    def test_changed_code_holds(self):
        r = self.ticket()
        r["code_sha256"] = "d" * 64
        with self.assertRaises(RuntimeError):
            self.valid(r)

    def test_extra_outer_time_holds(self):
        r = self.ticket()
        r["host_post_end"] += 1
        with self.assertRaises(ValueError):
            self.valid(r)

    def test_nan_guest_deadline_holds(self):
        r = self.ticket()
        r["maximum_guest_end"] = float("nan")
        with self.assertRaises(ValueError):
            self.valid(r)

    def test_stale_delegation_holds(self):
        with self.assertRaises(ValueError):
            self.valid(now=3250)

    def test_wrong_image_holds(self):
        r = self.ticket()
        r["image_sha256"] = "0" * 64
        with self.assertRaises(RuntimeError):
            self.valid(r)

    def test_boolean_uid_is_not_an_identity(self):
        r = self.ticket()
        r["uid"] = True
        with self.assertRaises(RuntimeError):
            self.valid(r)

    def test_no_stage_authority_rejects_before_native_materialization(self):
        with self.assertRaises(RuntimeError):
            A.require_stage_authority()

    def test_fixture_cannot_grant_native_stage(self):
        with self.assertRaises(RuntimeError), A.stage_authority(SimpleNamespace(native=False)):
            pass

    def test_private_binding_is_not_transferable_to_another_process(self):
        root = self.directory("claim")
        kernel = Mock()
        kernel.snapshot.return_value = {"generation": 1}
        owner = A.BoundOwner(
            root,
            kernel,
            "b" * 64,
            [["/python", "fixture"]],
            time.monotonic() + 30,
            time.monotonic() + 60,
            "a" * 32,
            False,
        )
        with patch.object(A.os, "getpid", return_value=999), self.assertRaises(RuntimeError):
            owner.lease.check()

    def test_unpermitted_command_does_not_refresh_or_spawn(self):
        root = self.directory("claim")
        kernel = Mock()
        kernel.snapshot.return_value = {"generation": 1}
        refresh = Mock()
        owner = A.BoundOwner(
            root,
            kernel,
            "b" * 64,
            [["/python", "fixture"]],
            time.monotonic() + 30,
            time.monotonic() + 60,
            "a" * 32,
            False,
            refresh,
        )
        with self.assertRaises(RuntimeError):
            owner.lease.check(["/foreign"])
        refresh.assert_not_called()

    def test_native_namespace_needs_live_admission(self):
        root = self.directory("native-123")
        with self.assertRaises(RuntimeError):
            Campaign(root, {}, None)


class RecipeCases(Base):
    def context(self):
        return {
            "inner": "/qual",
            "workspace": "/workspace",
            "work": "/work",
            "science": "/results/science",
            "profile": "local",
            "bridge_snapshot": "/sealed",
        }

    def test_exact_seven_science_commands(self):
        self.assertEqual(len(commands(self.context(), "/python")), 7)

    def test_template_does_not_trust_guest_executable_path(self):
        self.assertTrue(all(x[0] == "$PYTHON" for x in recipe(self.context())))

    def test_sealed_commands_use_independent_bridge(self):
        rows = commands(self.context(), "/python")
        self.assertEqual(rows[3][2], "/sealed/ni_bridge.py")
        self.assertEqual(rows[5][2], "/sealed/ni_bridge.py")

    def test_runtime_and_cpu_are_inside_the_same_plan(self):
        rows = commands(self.context(), "/python")
        self.assertTrue(rows[0][2].endswith("ni_runtime.py"))
        self.assertIn("cpu", rows[-1])

    def test_original_source_and_all_tests_are_unchanged(self):
        original = Path(
            "/Users/danielarturi/Developer/JinyangLiWork/agent/experiments/startup-native-authority-ownership-v1"
        )
        if original.exists():
            for name, h in inventory(original).items():
                self.assertEqual(sha(HERE / name), h)


class DispatchCases(Base):
    def prepare_submit(self):
        package = self.directory("package")
        (package / "PLAN.json").write_text("{}")
        (package / "manifest.json").write_text("{}")
        (package / "LAUNCHER.sh").write_text("#!/bin/bash\n")
        state = self.directory("state")
        approval = self.approval()
        approval["uid"] = os.getuid()
        approval["plan_sha256"] = sha(package / "PLAN.json")
        save(state / "approval.json", approval)
        (state / "approval.json").chmod(0o600)
        image = self.root / "image"
        image.write_bytes(b"unchanged-target")
        apptainer = self.root / "apptainer"
        apptainer.write_text("stub")
        apptainer.chmod(0o700)
        return package, state, image, apptainer

    def execute_submit(self, response="99999124", raises=False):
        from contextlib import ExitStack

        package, state, image, apptainer = self.prepare_submit()
        original_sha = C.sha

        def hash_file(path):
            return config()["image_sha256"] if Path(path) == image else original_sha(path)

        calls = []

        def query(argv, **kw):
            calls.append(argv)
            if "--test-only" in argv:
                return "dry-run resources valid"
            if raises:
                raise TimeoutError("uncertain client response")
            return response

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(C, "verify", return_value={"limits": config()["limits"]})
            )
            stack.enter_context(patch.object(C, "state_root", return_value=state))
            stack.enter_context(patch.object(C, "site_check", return_value={"validated": True}))
            stack.enter_context(patch.object(C, "quota", return_value={"finite": True}))
            stack.enter_context(
                patch.object(C, "trusted_binary", return_value={"path": "/trusted/sbatch"})
            )
            stack.enter_context(patch.object(C, "sha", side_effect=hash_file))
            stack.enter_context(
                patch.object(
                    C.os, "uname", return_value=SimpleNamespace(sysname="Linux", machine="x86_64")
                )
            )
            stack.enter_context(
                patch.dict(
                    os.environ,
                    {
                        "TORCH_SLURM_ACCOUNT": "torch_pr_fixture",
                        "TORCH_RUNTIME_IMAGE": str(image),
                        "TORCH_APPTAINER_BIN": str(apptainer),
                    },
                    clear=True,
                )
            )
            stack.enter_context(patch.object(C, "bounded_command", side_effect=query))
            error = None
            try:
                C.submit(package)
            except BaseException as e:
                error = e
            if error is None:
                with self.assertRaises(RuntimeError):
                    C.submit(package)
        return state, calls, error

    def test_exactly_one_actual_submission_after_dry_run(self):
        state, calls, error = self.execute_submit()
        self.assertIsNone(error)
        self.assertEqual(len(calls), 2)
        self.assertIn("--test-only", calls[0])
        self.assertNotIn("--test-only", calls[1])
        self.assertEqual(
            read(state / "submission.json")["dispatch"],
            {"status": "submitted", "job_id": "99999124"},
        )

    def test_uncertain_dispatch_is_durable_and_never_repeated(self):
        state, calls, error = self.execute_submit(raises=True)
        self.assertIsInstance(error, TimeoutError)
        self.assertEqual(len(calls), 2)
        self.assertEqual(read(state / "submission.json")["dispatch"], {"status": "unknown"})
        self.assertTrue((state.parent / ("." + C.NAME + "-reservation.json")).exists())

    def test_malformed_sbatch_response_is_not_success(self):
        state, calls, error = self.execute_submit(response="not-a-job")
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(read(state / "submission.json")["dispatch"], {"status": "unknown"})

    def test_spent_job_response_is_never_adopted(self):
        state, calls, error = self.execute_submit(response="21595967")
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(read(state / "submission.json")["dispatch"], {"status": "unknown"})


class NestedDescriptorCases(unittest.TestCase):
    def test_exited_retained_descriptor_can_be_retired(self):
        import ni_guardian as g

        fake = Mock()
        fake.poll.return_value = [(99, __import__("select").POLLIN)]
        with patch.object(g.select, "poll", return_value=fake):
            g.verify_exited_descriptor(99)

    def test_live_descriptor_conflicting_with_echild_holds(self):
        import ni_guardian as g

        fake = Mock()
        fake.poll.return_value = []
        with patch.object(g.select, "poll", return_value=fake), self.assertRaises(RuntimeError):
            g.verify_exited_descriptor(99)

    def test_invalid_descriptor_does_not_qualify(self):
        import ni_guardian as g

        fake = Mock()
        fake.poll.return_value = [(99, __import__("select").POLLNVAL)]
        with patch.object(g.select, "poll", return_value=fake), self.assertRaises(RuntimeError):
            g.verify_exited_descriptor(99)


class RuntimeCredentialCases(unittest.TestCase):
    def kernel(self):
        k = object.__new__(S.ScopedKernel)
        k.privileged_runtime = True
        return k

    def row(self, uid=501, monitor=False):
        return {
            "pid": 123,
            "start": 100,
            "uid": uid,
            "cgroup": "0::/fixture",
            "monitor_only": monitor,
            "actual_uids": (501, 0, 0, 0) if monitor else (501,) * 4,
        }

    def test_guest_keeps_original_credential_policy(self):
        k = self.kernel()
        k.privileged_runtime = False
        with (
            patch.object(S.LinuxKernel, "process", side_effect=ValueError("mixed UID")),
            self.assertRaises(ValueError),
        ):
            k.process(123)

    def test_root_transition_during_pidfd_pin_remains_monitor_only(self):
        k = self.kernel()
        k.process = Mock(side_effect=[self.row(), self.row(monitor=True)])
        with patch.object(S.os, "pidfd_open", return_value=99, create=True):
            fd, row = k.pin(123)
        self.assertEqual(fd, 99)
        self.assertTrue(row["monitor_only"])

    def test_return_to_user_never_revokes_prior_monitor_marker(self):
        k = self.kernel()
        k.process = Mock(side_effect=[self.row(monitor=True), self.row()])
        with patch.object(S.os, "pidfd_open", return_value=99, create=True):
            _, row = k.pin(123)
        self.assertTrue(row["monitor_only"])

    def test_monitor_descriptor_is_never_signalled(self):
        k = self.kernel()
        k.process = Mock(side_effect=AssertionError("must not inspect monitor"))
        with patch.object(S.LinuxKernel, "send", side_effect=AssertionError("must not signal")):
            k.send(99, self.row(monitor=True), 15)

    def test_new_transition_before_shutdown_blocks_signal(self):
        k = self.kernel()
        k.process = Mock(return_value=self.row(monitor=True))
        row = self.row()
        with patch.object(S.LinuxKernel, "send", side_effect=AssertionError("must not signal")):
            k.send(99, row, 15)
        self.assertTrue(row["monitor_only"])

    def test_foreign_credentials_rejected(self):
        k = self.kernel()
        k.read = Mock(
            side_effect=["123 (x) S 2 3 4 " + "0 " * 15 + "100", "Uid:\t501\t502\t501\t501\n"]
        )
        with (
            patch.object(S.os, "getuid", return_value=501),
            self.assertRaisesRegex(RuntimeError, "Foreign descendant"),
        ):
            k.process(123)

    def test_pid_replacement_is_not_a_credential_transition(self):
        k = self.kernel()
        a = self.row()
        b = {**self.row(monitor=True), "start": 101}
        k.process = Mock(side_effect=[a, b])
        with (
            patch.object(S.os, "pidfd_open", return_value=99, create=True),
            patch.object(S.os, "close") as closed,
            self.assertRaises(RuntimeError),
        ):
            k.pin(123)
        closed.assert_called_once_with(99)


class HostEntrypointCases(unittest.TestCase):
    def test_new_host_entrypoint_loads_original_specification(self):
        import ni_host
        import nh_binding

        self.assertIs(ni_host.specification, nh_binding.specification)
        self.assertIs(ni_host.Campaign, Campaign)


class AdmissionReadBudgetCases(unittest.TestCase):
    def test_large_proc_file_is_rejected_and_closed(self):
        import ni_control_reads as r

        with (
            patch.object(r, "_reads", 0),
            patch.object(r.os, "open", return_value=99),
            patch.object(r.os, "read", return_value=b"x" * 4096),
            patch.object(r.os, "close") as closed,
            self.assertRaises(RuntimeError),
        ):
            r.control_read("self/mountinfo")
        closed.assert_called_once_with(99)

    def test_process_cannot_obtain_ninth_read(self):
        import ni_control_reads as r

        with (
            patch.object(r, "_reads", 8),
            patch.object(r.os, "open") as opened,
            self.assertRaises(RuntimeError),
        ):
            r.control_read("self/cgroup")
        opened.assert_not_called()

    def test_other_proc_files_cannot_use_reserved_slice(self):
        import ni_control_reads as r

        with patch.object(r.os, "open") as opened, self.assertRaises(ValueError):
            r.control_read("../etc/passwd")
        opened.assert_not_called()

    def test_actual_small_text_is_preserved(self):
        import ni_control_reads as r

        with (
            patch.object(r, "_reads", 0),
            patch.object(r.os, "open", return_value=99),
            patch.object(r.os, "read", side_effect=[b"0::/job_123\n", b""]),
            patch.object(r.os, "close"),
        ):
            self.assertEqual(r.control_read("self/cgroup"), "0::/job_123\n")
            self.assertEqual(r._reads, 1)

    def test_original_combined_ledger_is_prepaid_once(self):
        import ni_control_reads as r

        ledger = Mock()
        proof = r.prepay(ledger)
        ledger.reserve.assert_called_once_with(reads=128, bytes=128 * 65537)
        self.assertGreaterEqual(
            proof["reads"], proof["maximum_control_processes"] * proof["per_process_reads"]
        )

    def test_unavailable_shared_budget_holds_before_owned_launch(self):
        import ni_control_reads as r

        ledger = Mock()
        ledger.reserve.side_effect = RuntimeError("original cap exhausted")
        with self.assertRaises(RuntimeError):
            r.prepay(ledger)
