"""Real nested host/guest lifecycle with shared budget and exact delegation."""

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from au_authority import code_identity
from nh_common import HERE, config, read, save, sha
from nh_lifecycle import stop_owned
from nh_retention import RawStore
from ni_authority import BoundOwner
from ni_groups import LinuxGroups
from ni_site import ScopedKernel

OBSERVATIONS = []


class KernelIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/run/a3-authority")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.chmod(0o700)
        self.raw = self.root / "raw"
        self.raw.mkdir(mode=0o700)
        self.store = RawStore(self.raw)
        self.budget = self.root / "budget"
        fd = os.open(self.budget, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.write(fd, b"\0" * 16)
        self.kernel = ScopedKernel(fd, None)
        self.addCleanup(self.kernel.close)

    def launch(self, mode="normal", tamper=False):
        start = time.monotonic()
        guestclaims = self.root / "guest"
        guestclaims.mkdir(mode=0o700)
        hostclaims = self.root / "host"
        hostclaims.mkdir(mode=0o700)
        st = self.budget.stat()
        ticket = {
            "schema": "a3.host-delegation.v1",
            "domain": "local-kernel-test",
            "nonce": os.urandom(16).hex(),
            "binding_sha256": "b" * 64,
            "code_sha256": code_identity(),
            "image_sha256": config()["image_sha256"],
            "archive_sha256": config()["original_archive_sha256"],
            "manifest_sha256": config()["original_manifest_sha256"],
            "host_started": start,
            "latest_ready": start + 240,
            "maximum_guest_end": start + 3240,
            "host_post_end": start + 3480,
            "uid": os.getuid(),
            "job_id": "fixture",
            "commands": [[sys.executable, "-B", str(HERE / "au_fixture.py"), mode]],
            "budget_inode": st.st_ino,
            "budget_device": st.st_dev,
            "budget_path": str(self.budget),
            "claims_path": str(guestclaims),
            "limits": config()["limits"],
            "host_boot": self.kernel.snapshot()["boot"],
        }
        path = self.root / "ticket.json"
        save(path, ticket)
        expected = sha(path)
        if tamper:
            path.write_text("{}")
        command = [
            sys.executable,
            "-B",
            str(HERE / "ni_probe_guest.py"),
            str(path),
            expected,
            str(self.raw),
        ]
        self.owner = BoundOwner(
            hostclaims,
            self.kernel,
            "b" * 64,
            [command],
            start + 20,
            start + 30,
            ticket["nonce"],
            False,
        )
        self.groups = LinuxGroups(self.owner.lease, self.store, start + 20, start + 30)
        self.log = (self.raw / "host-fixture.log").open("x")
        self.addCleanup(self.log.close)
        self.proc, self.handle = self.groups.spawn(
            command, stdout=self.log, stderr=subprocess.STDOUT
        )
        return self.proc

    def finish(self):
        stop_owned(self.groups, self.handle, self.proc, self.groups.cleanup_end)
        proof = self.groups.finish(self.handle)
        OBSERVATIONS.append(
            {
                "test": self.id(),
                "outer": proof,
                "outer_exit": self.groups.process.returncode,
                "budget": self.kernel.budget.usage(),
                "nested": read(self.raw / "delegated-fixture-proof.json")
                if (self.raw / "delegated-fixture-proof.json").exists()
                else None,
            }
        )
        self.assertTrue(proof["kernel_ECHILD"])
        self.assertEqual(proof["tracked_live"], 0)
        return proof

    def test_full_nested_success_and_shared_budget(self):
        self.launch()
        self.assertEqual(self.proc.wait(timeout=8), 0)
        self.finish()
        r = OBSERVATIONS[-1]
        self.assertTrue(r["nested"]["proof"]["kernel_ECHILD"])
        self.assertGreater(r["budget"]["reads"], r["nested"]["budget"]["reads"])

    def test_nested_nonzero_exit_is_not_masked(self):
        self.launch("nonzero")
        self.assertEqual(self.proc.wait(timeout=8), 42)
        self.finish()

    def test_detached_descendant_cannot_finish_a_phase_early(self):
        self.launch("setsid")
        self.assertNotEqual(self.proc.wait(timeout=10), 0)
        self.finish()

    def test_tampered_delegation_stops_before_science(self):
        self.launch(tamper=True)
        self.assertNotEqual(self.proc.wait(timeout=8), 0)
        self.finish()
        self.assertIsNone(OBSERVATIONS[-1]["nested"])

    def test_outer_cancellation_stops_nested_tree(self):
        self.launch("linger")
        time.sleep(0.5)
        self.groups.send(self.handle, __import__("signal").SIGTERM)
        self.assertNotEqual(self.proc.wait(timeout=15), 0)
        self.finish()

    def test_revoked_outer_claim_preserves_uncertainty(self):
        self.launch("linger")
        time.sleep(0.5)
        (self.owner.root / "lease.json").write_text("{}")
        with self.assertRaises(RuntimeError):
            self.proc.poll()
        self.assertIsNotNone(self.groups.process.poll())
        self.assertIs(self.groups.active, self.handle)
        OBSERVATIONS.append(
            {
                "test": self.id(),
                "authority_loss_held": True,
                "outer_guardian_exit": self.groups.process.returncode,
            }
        )
        os.close(self.groups.fd)
