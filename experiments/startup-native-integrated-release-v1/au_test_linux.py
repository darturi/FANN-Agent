"""Actual local Linux PID-descriptor/subreaper tests; no Torch authority claim."""

import hashlib
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from au_authority import Authority, Roots, code_identity
from au_backend import LinuxGroups
from au_kernel import LinuxKernel, canonical
from nh_common import HERE, config
from nh_lifecycle import stop_owned
from nh_retention import RawStore

OBSERVATIONS = []


class LinuxCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/run/a3-authority")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.kernel = LinuxKernel()
        self.addCleanup(self.kernel.close)
        self.command = None

    def controller(self, mode, work=3, cleanup=18, commands=None):
        began = time.monotonic()
        self.command = [sys.executable, "-B", str(HERE / "au_fixture.py"), mode]
        limits = config()["limits"]
        snapshot = self.kernel.snapshot()
        site = {
            "schema": "a3.site.v1",
            "domain": "offline-kernel-test",
            "job_id": "99999123",
            "kernel": snapshot,
            "expires": began + 180,
            "limits": limits,
        }
        sitefile = self.root / "site.json"
        sitefile.write_bytes(canonical(site))
        sitefile.chmod(0o600)
        site_sha = hashlib.sha256(sitefile.read_bytes()).hexdigest()
        grant = {
            "schema": "a3.permission.v1",
            "domain": "offline-kernel-test",
            "nonce": os.urandom(16).hex(),
            "job_id": "99999123",
            "binding_sha256": "b" * 64,
            "code_sha256": code_identity(),
            "image_sha256": config()["image_sha256"],
            "limits": limits,
            "host_started": began,
            "work_deadline": began + work,
            "cleanup_deadline": began + cleanup,
            "commands": [
                [sys.executable, "-B", str(HERE / "au_fixture.py"), m] for m in (commands or [mode])
            ],
            "site_sha256": site_sha,
        }
        release = self.root / "release.json"
        release.write_bytes(canonical(grant))
        release.chmod(0o600)
        claims = self.root / "claims"
        claims.mkdir(mode=0o700)
        authority = Authority(
            Roots(
                hashlib.sha256(release.read_bytes()).hexdigest(), site_sha, "offline-kernel-test"
            ),
            release,
            sitefile,
            claims,
            self.kernel,
        )
        lease = authority.claim("b" * 64, code_identity())
        raw = self.root / "raw"
        raw.mkdir(mode=0o700)
        store = RawStore(raw)
        self.groups = LinuxGroups(lease, store, began + work, began + cleanup)
        self.log = (self.root / "child.log").open("x")
        self.addCleanup(self.log.close)
        proc, handle = self.groups.spawn(
            self.command, stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True
        )
        self.proc, self.handle = proc, handle
        return proc, handle

    def finish(self):
        stop_owned(self.groups, self.handle, self.proc, self.groups.cleanup_end)
        proof = self.groups.finish(self.handle)
        self.assertTrue(proof["kernel_ECHILD"])
        self.assertEqual(proof["tracked_live"], 0)
        self.assertLess(proof["finished"], self.groups.cleanup_end)
        self.assertEqual(self.groups.process.returncode, 0)
        budget = self.kernel.budget.usage()
        self.assertLessEqual(budget["reads"], 500000)
        self.assertLessEqual(budget["bytes"], 512 * 1024**2)
        OBSERVATIONS.append(
            {
                "test": self.id(),
                "proof": proof,
                "independent_guardian_exit": self.groups.process.returncode,
                "blocked_child": self.groups.child,
                "actual_combined_budget": budget,
            }
        )
        return proof

    def test_normal_exit_and_atomic_registration(self):
        proc, handle = self.controller("normal")
        self.assertEqual(proc.wait(timeout=5), 0)
        proof = self.finish()
        self.assertEqual(proof["direct_exit_code"], 0)

    def test_scientific_nonzero_exit_is_preserved(self):
        proc, handle = self.controller("nonzero")
        self.assertEqual(proc.wait(timeout=5), 42)
        self.assertEqual(self.finish()["direct_exit_code"], 42)

    def test_live_child_is_stopped_and_reaped(self):
        self.controller("linger")
        time.sleep(0.15)
        self.assertLess(self.finish()["direct_exit_code"], 0)

    def test_exited_leader_does_not_hide_live_orphan(self):
        self.controller("orphan")
        time.sleep(0.2)
        self.assertIsNone(self.proc.poll())
        proof = self.finish()
        self.assertEqual(proof["direct_exit_code"], 0)
        self.assertGreaterEqual(len(proof["reaped"]), 2)

    def test_new_session_descendant_remains_owned(self):
        self.controller("setsid")
        time.sleep(0.2)
        self.assertIsNone(self.proc.poll())
        self.assertGreaterEqual(len(self.finish()["reaped"]), 2)

    def test_double_fork_descendant_is_adopted(self):
        self.controller("doublefork")
        time.sleep(0.2)
        self.assertIsNone(self.proc.poll())
        self.assertGreaterEqual(len(self.finish()["reaped"]), 2)

    def test_thread_created_descendant_is_discovered(self):
        self.controller("threadfork")
        time.sleep(0.2)
        self.assertGreaterEqual(len(self.finish()["reaped"]), 2)

    def test_term_resistance_escalates_within_original_endpoint(self):
        self.controller("ignore")
        time.sleep(0.2)
        began = time.monotonic()
        proof = self.finish()
        self.assertEqual(proof["direct_exit_code"], -signal.SIGKILL)
        self.assertLess(time.monotonic() - began, 15)

    def test_work_deadline_enters_same_cleanup_budget(self):
        proc, handle = self.controller("linger", work=0.8, cleanup=16)
        self.assertIsNotNone(proc.wait(timeout=4))
        proof = self.finish()
        self.assertTrue(proof["stopping"])

    def test_foreign_process_survives_owned_tree_shutdown(self):
        foreign = subprocess.Popen([sys.executable, "-B", str(HERE / "au_fixture.py"), "linger"])
        fd, row = self.kernel.pin(foreign.pid)
        try:
            self.controller("setsid")
            time.sleep(0.2)
            self.finish()
            self.assertIsNone(foreign.poll())
            OBSERVATIONS[-1]["foreign_process_survived"] = True
        finally:
            self.kernel.send(fd, row, signal.SIGKILL)
            foreign.wait(timeout=5)
            os.close(fd)

    def test_uncertain_command_cannot_be_spawned_twice(self):
        self.controller("normal")
        self.proc.wait(timeout=5)
        self.finish()
        with self.assertRaises(FileExistsError):
            self.groups.spawn(self.command, stdout=self.log)

    def test_parent_pipe_eof_triggers_bounded_cleanup(self):
        self.controller("setsid")
        time.sleep(0.2)
        child = self.groups.child
        fd, row = (
            self.kernel.pin(child["pid"])
            if Path("/proc/" + str(child["pid"])).exists()
            else (None, None)
        )
        self.groups.channel.close()
        try:
            self.assertIn(self.groups.process.wait(timeout=15), (0, 1))
            # A lost terminal pipe is intentionally unqualified even if the
            # guardian reaped everything before exiting.
            with self.assertRaises((RuntimeError, OSError, EOFError)):
                self.groups.members(self.handle)
            OBSERVATIONS.append(
                {
                    "test": self.id(),
                    "pipe_loss_held": True,
                    "guardian_exit": self.groups.process.returncode,
                    "qualified_completion": False,
                }
            )
        finally:
            if fd is not None:
                os.close(fd)
            os.close(self.groups.fd)

    def test_root_anchor_group_writable_file_is_rejected(self):
        from au_kernel import trusted_json

        path = self.root / "unsafe.json"
        path.write_bytes(b"{}")
        path.chmod(0o660)
        with self.assertRaises(ValueError):
            trusted_json(path, hashlib.sha256(b"{}").hexdigest())
        OBSERVATIONS.append({"test": self.id(), "unsafe_anchor_held": True})

    def test_root_anchor_duplicate_json_keys_are_rejected(self):
        from au_kernel import trusted_json

        path = self.root / "duplicate.json"
        data = b'{"x":1,"x":2}'
        path.write_bytes(data)
        path.chmod(0o600)
        with self.assertRaises(ValueError):
            trusted_json(path, hashlib.sha256(data).hexdigest())
        OBSERVATIONS.append({"test": self.id(), "ambiguous_anchor_held": True})

    def test_sequential_guardians_share_one_combined_read_ledger(self):
        self.controller("normal", commands=["normal", "nonzero"])
        self.proc.wait(timeout=5)
        first = self.finish()
        used = self.kernel.budget.usage()["reads"]
        self.proc, self.handle = self.groups.spawn(
            [sys.executable, "-B", str(HERE / "au_fixture.py"), "nonzero"],
            stdout=self.log,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(self.proc.wait(timeout=5), 42)
        second = self.finish()
        self.assertGreater(second["read_budget"]["reads"], used)
        self.assertLess(first["read_budget"]["reads"], used)

    def test_exhausted_observer_budget_still_cleans_registered_descriptors(self):
        self.controller("setsid")
        time.sleep(0.5)
        usage = self.kernel.budget.usage()
        self.kernel.budget.reserve(reads=500000 - usage["reads"])
        self.assertEqual(self.groups.process.wait(timeout=15), 1)
        self.groups.drain()
        self.assertTrue(self.groups.failures[-1]["cleanup"]["kernel_ECHILD"])
        OBSERVATIONS.append(
            {
                "test": self.id(),
                "observer_loss_held": True,
                "guardian_exit": 1,
                "cleanup": self.groups.failures[-1]["cleanup"],
            }
        )
        self.groups.channel.close()
        os.close(self.groups.fd)

    def test_revoked_site_authority_closes_pipe_and_holds(self):
        self.controller("linger")
        time.sleep(0.2)
        site = self.root / "site.json"
        site.write_bytes(b"{}")
        with self.assertRaises(ValueError):
            self.groups.members(self.handle)
        self.assertIsNotNone(self.groups.process.poll())
        OBSERVATIONS.append(
            {
                "test": self.id(),
                "site_revocation_held": True,
                "guardian_exit": self.groups.process.returncode,
                "active_handle_retained": self.groups.active is self.handle,
            }
        )
        os.close(self.groups.fd)
