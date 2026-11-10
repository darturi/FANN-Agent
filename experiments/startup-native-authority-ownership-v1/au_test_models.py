"""Identity and shutdown fault models; real Linux cases are separate."""

import os
import signal
import unittest
from unittest.mock import Mock, patch

import au_backend as B
import au_guardian as G
import au_kernel as K
from au_wire import Pipe


class OwnershipModels(unittest.TestCase):
    def test_descendant_walk_includes_adopted_and_session_detached(self):
        rows = {2: {"ppid": 1}, 3: {"ppid": 2, "sid": 3}, 4: {"ppid": 1, "sid": 4}, 8: {"ppid": 9}}
        self.assertEqual(set(G.owned(rows, 1)), {2, 3, 4})

    def test_foreign_process_is_excluded(self):
        self.assertEqual(G.owned({3: {"ppid": 99}}, 1), {})

    def test_original_process_bound_is_strict(self):
        with self.assertRaises(RuntimeError):
            G.owned({n: {"ppid": 1} for n in range(2, 34)}, 1)

    def test_pid_replacement_across_open_is_rejected_and_fd_closed(self):
        kernel = K.LinuxKernel.__new__(K.LinuxKernel)
        a = {"pid": 10, "start": 1, "uid": 2, "cgroup": "x"}
        b = {**a, "start": 2}
        kernel.process = Mock(side_effect=[a, b])
        with (
            patch.object(os, "pidfd_open", return_value=99, create=True),
            patch.object(os, "close") as close,
            self.assertRaises(RuntimeError),
        ):
            kernel.pin(10)
        close.assert_called_once_with(99)

    def test_changed_identity_cannot_be_signalled(self):
        kernel = K.LinuxKernel.__new__(K.LinuxKernel)
        row = {"pid": 10, "start": 1, "uid": 2, "cgroup": "x"}
        kernel.process = Mock(return_value={**row, "start": 2})
        with (
            patch.object(signal, "pidfd_send_signal", create=True) as send,
            self.assertRaises(RuntimeError),
        ):
            kernel.send(99, row, signal.SIGTERM)
        send.assert_not_called()

    def test_missing_process_does_not_fall_back_to_kill(self):
        kernel = K.LinuxKernel.__new__(K.LinuxKernel)
        kernel.process = Mock(side_effect=FileNotFoundError)
        with patch.object(os, "kill") as numeric:
            kernel.send(99, {"pid": 10}, signal.SIGTERM)
        numeric.assert_not_called()

    def test_disallowed_signal_is_rejected(self):
        with self.assertRaises(ValueError):
            K.LinuxKernel.__new__(K.LinuxKernel).send(99, {"pid": 10}, signal.SIGINT)

    def controller(self, code, proof=None):
        b = B.LinuxGroups.__new__(B.LinuxGroups)
        b.active = object()
        b.process = Mock(poll=Mock(return_value=code))
        b.lease = Mock()
        b.store = Mock()
        b.channel = Mock()
        b.proof = proof
        b.failures = []
        b.cleanup_end = 100
        b.drain = Mock()
        return b

    def test_leader_exit_without_terminal_proof_cannot_clear_handle(self):
        b = self.controller(0)
        with self.assertRaises(RuntimeError):
            b.members(b.active)
        self.assertIsNotNone(b.active)

    def test_failed_guardian_cannot_qualify(self):
        b = self.controller(
            1, {"complete": True, "kernel_ECHILD": True, "tracked_live": 0, "finished": 10}
        )
        with self.assertRaises(RuntimeError):
            b.members(b.active)

    def test_empty_census_without_ECHILD_is_insufficient(self):
        b = self.controller(
            0, {"complete": True, "kernel_ECHILD": False, "tracked_live": 0, "finished": 10}
        )
        with self.assertRaises(RuntimeError):
            b.members(b.active)

    def test_nonzero_tracked_live_is_failure(self):
        b = self.controller(
            0, {"complete": True, "kernel_ECHILD": True, "tracked_live": 1, "finished": 10}
        )
        with self.assertRaises(RuntimeError):
            b.members(b.active)

    def test_late_terminal_proof_is_failure(self):
        b = self.controller(
            0, {"complete": True, "kernel_ECHILD": True, "tracked_live": 0, "finished": 100}
        )
        with self.assertRaises(RuntimeError):
            b.members(b.active)

    def test_foreign_handle_is_rejected_before_action(self):
        b = self.controller(None)
        with self.assertRaises(RuntimeError):
            b.send(object(), signal.SIGTERM)

    def test_guardian_race_is_drained_after_successful_exit(self):
        b = self.controller(0)

        def drain():
            b.proof = {"complete": True, "kernel_ECHILD": True, "tracked_live": 0, "finished": 10}

        calls = [0]

        def receive():
            calls[0] += 1
            if calls[0] == 2:
                drain()

        b.drain.side_effect = receive
        # The second drain must consume the final frame after poll proves exit.
        self.assertEqual(b.members(b.active), ())

    def test_nan_endpoints_cannot_create_controller(self):
        with self.assertRaises(RuntimeError):
            B.LinuxGroups(None, None, float("nan"), float("nan"))

    def test_pipe_frame_size_is_bounded(self):
        channel = Pipe.__new__(Pipe)
        with self.assertRaises(ValueError):
            channel.send({"blob": "x" * 40000}, 100)


class ReadLedgerModels(unittest.TestCase):
    def budget(self, reads=0, bytes=0):
        import struct
        import tempfile

        from au_budget import ReadBudget

        file = tempfile.TemporaryFile()
        self.addCleanup(file.close)
        file.write(struct.pack("!QQ", reads, bytes))
        file.flush()
        return ReadBudget(file.fileno())

    def test_read_attempt_budget_cannot_extend(self):
        b = self.budget(reads=500000)
        with self.assertRaises(RuntimeError):
            b.reserve(reads=1)
        self.assertEqual(b.usage()["reads"], 500000)

    def test_byte_reservation_prevents_overrun(self):
        b = self.budget(bytes=512 * 1024**2)
        with self.assertRaises(RuntimeError):
            b.reserve(bytes=1)

    def test_unused_byte_reservation_is_refunded(self):
        b = self.budget()
        b.reserve(reads=1, bytes=4096)
        b.reserve(bytes=-4000)
        self.assertEqual((b.usage()["reads"], b.usage()["bytes"]), (1, 96))

    def test_refund_cannot_create_negative_usage(self):
        b = self.budget()
        with self.assertRaises(RuntimeError):
            b.reserve(bytes=-1)

    def test_two_instances_share_the_same_budget(self):
        from au_budget import ReadBudget

        a = self.budget()
        b = ReadBudget(a.fd)
        a.reserve(reads=2, bytes=20)
        b.reserve(reads=3, bytes=30)
        self.assertEqual((a.usage()["reads"], a.usage()["bytes"]), (5, 50))

    def test_boolean_attempt_counter_is_rejected(self):
        with self.assertRaises(ValueError):
            self.budget().reserve(reads=True)

    def test_foreign_numeric_pid_never_enters_owned_subtree(self):
        self.assertEqual(G.owned({400: {"ppid": 999, "uid": 999, "start": 1}}, 1), {})

    def test_changed_cgroup_blocks_pidfd_signal(self):
        kernel = K.LinuxKernel.__new__(K.LinuxKernel)
        row = {"pid": 10, "start": 1, "uid": 2, "cgroup": "a"}
        kernel.process = Mock(return_value={**row, "cgroup": "foreign"})
        with (
            patch.object(signal, "pidfd_send_signal", create=True) as send,
            self.assertRaises(RuntimeError),
        ):
            kernel.send(5, row, signal.SIGKILL)
        send.assert_not_called()

    def test_changed_uid_blocks_pidfd_signal(self):
        kernel = K.LinuxKernel.__new__(K.LinuxKernel)
        row = {"pid": 10, "start": 1, "uid": 2, "cgroup": "a"}
        kernel.process = Mock(return_value={**row, "uid": 3})
        with (
            patch.object(signal, "pidfd_send_signal", create=True) as send,
            self.assertRaises(RuntimeError),
        ):
            kernel.send(5, row, signal.SIGKILL)
        send.assert_not_called()

    def test_guardian_success_does_not_mask_science_failure(self):
        c = Mock()
        c.process.pid = 10
        c.members.return_value = ()
        c.proof = {"direct_exit_code": 42}
        self.assertEqual(B.OwnedProcess(c).poll(), 42)


class AncestryModels(unittest.TestCase):
    def test_missing_parent_cannot_attach_foreign_grandchild(self):
        k = Mock()
        k.process.side_effect = [
            FileNotFoundError,
            {"pid": 3, "ppid": 2, "start": 30, "uid": 5, "cgroup": "own"},
        ]
        with self.assertRaises(RuntimeError):
            G.fresh_owned(k, {2: {"start": 20}, 3: {"start": 30}}, 1, {"uid": 5, "cgroup": "own"})

    def test_reparented_orphan_is_owned_by_subreaper(self):
        k = Mock()
        k.process.return_value = {"pid": 3, "ppid": 1, "start": 30, "uid": 5, "cgroup": "own"}
        self.assertEqual(
            set(G.fresh_owned(k, {3: {"start": 30}}, 1, {"uid": 5, "cgroup": "own"})), {3}
        )

    def test_foreign_ancestry_is_rejected_even_with_same_uid_and_scope(self):
        k = Mock()
        k.process.return_value = {"pid": 3, "ppid": 999, "start": 30, "uid": 5, "cgroup": "own"}
        with self.assertRaises(RuntimeError):
            G.fresh_owned(k, {3: {"start": 30}}, 1, {"uid": 5, "cgroup": "own"})

    def test_new_pid_generation_is_not_merged(self):
        k = Mock()
        k.process.return_value = {"pid": 3, "ppid": 1, "start": 31, "uid": 5, "cgroup": "own"}
        with self.assertRaises(RuntimeError):
            G.fresh_owned(k, {3: {"start": 30}}, 1, {"uid": 5, "cgroup": "own"})


class ProcessHandleModels(unittest.TestCase):
    def test_terminal_process_status_is_not_replaced_by_next_child(self):
        c = Mock()
        c.process.pid = 10
        c.cleanup_end = 100
        c.active = object()
        c.members.return_value = ()
        c.proof = {"direct_exit_code": 42}
        proc = B.OwnedProcess(c)
        self.assertEqual(proc.poll(), 42)
        c.active = object()
        c.proof = {"direct_exit_code": 0}
        self.assertEqual(proc.poll(), 42)

    def test_unobserved_stale_process_cannot_read_next_child(self):
        c = Mock()
        c.process.pid = 10
        c.cleanup_end = 100
        c.active = object()
        proc = B.OwnedProcess(c)
        c.active = object()
        with self.assertRaises(RuntimeError):
            proc.poll()


class PublicationModels(unittest.TestCase):
    def test_late_terminal_journal_cannot_clear_owned_handle(self):
        b = B.LinuxGroups.__new__(B.LinuxGroups)
        handle = object()
        b.active = handle
        b.members = Mock(return_value=())
        b.cleanup_end = 100
        b.process = Mock()
        b.process.returncode = 0
        b.proof = {"complete": True}
        b.store = Mock()
        b.channel = Mock()
        b.fd = 99
        b.identity = {"action": "a" * 64}
        now = [90.0]

        def publish(*args):
            now[0] = 101

        b.store.json.side_effect = publish
        with patch.object(B.time, "monotonic", lambda: now[0]), self.assertRaises(TimeoutError):
            b.finish(handle)
        self.assertIs(b.active, handle)
        b.channel.close.assert_not_called()
