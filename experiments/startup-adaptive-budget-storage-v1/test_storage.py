"""Archive preservation, strict storage evidence and complete-budget boundaries."""

import io
import json
import os
import sys
import tarfile
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import policy as P
import staging as S
from lifetime import observe


class BudgetTests(unittest.TestCase):
    def test_launch_exact_latest_boundary(self):
        self.assertEqual(P.launch_admission(100, 310)["guest_ready_deadline"], 340)

    def test_launch_cannot_use_startup_reserve(self):
        with self.assertRaises(RuntimeError):
            P.launch_admission(100, 310.001)

    def test_ready_exact_boundary_preserves_every_reserve(self):
        value = P.ready_admission(100, 340)
        self.assertEqual(value["guest_end"], 3340)
        self.assertEqual(value["post_deadline"], 3580)
        self.assertEqual(value["whole_deadline"], 3700)
        self.assertFalse(value["native_release"])

    def test_late_ready_cannot_borrow_outer_or_post(self):
        with self.assertRaises(RuntimeError):
            P.ready_admission(0, 240.001)

    def test_nonfinite_boolean_and_negative_times_rejected(self):
        for value in (True, float("nan"), float("inf"), -1):
            for fn in (P.launch_admission, P.ready_admission):
                with self.subTest(value=value, fn=fn), self.assertRaises(RuntimeError):
                    fn(0, value)

    def test_clock_before_start_rejected(self):
        for fn in (P.launch_admission, P.ready_admission):
            with self.assertRaises(RuntimeError):
                fn(100, 99)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.plan = {"planned_bytes": 7379306398, "planned_inodes": 22498}
        self.obs = dict(
            path="/job/private",
            filesystem="ext4",
            device="8:1",
            mount_device="8:1",
            uid=os.getuid(),
            mode=0o700,
            free_bytes=P.FREE_BYTES,
            free_inodes=P.FREE_INODES,
            allocation_block_bytes=4096,
            ram_backed=False,
            shared=False,
            quota_status="finite_verified",
            quota_free_bytes=P.FREE_BYTES,
            quota_free_inodes=P.FREE_INODES,
            synthetic=True,
        )

    def rejected(self, **changes):
        value = {**self.obs, **changes}
        with self.assertRaises((ValueError, TypeError)):
            P.assess_storage(value, self.plan, os.getuid())

    def test_synthetic_fit_cannot_qualify_native(self):
        result = P.assess_storage(self.obs, self.plan, os.getuid())
        self.assertTrue(result["conditional_capacity_policy_pass"])
        self.assertFalse(result["native_storage_qualified"])
        self.assertFalse(result["native_release"])

    def test_unknown_quota_rejected(self):
        self.rejected(quota_status="unknown", quota_free_bytes=None)

    def test_global_space_cannot_hide_user_quota(self):
        self.rejected(free_bytes=100 * P.FREE_BYTES, quota_free_bytes=P.FREE_BYTES - 1)

    def test_global_inodes_cannot_hide_user_inode_quota(self):
        self.rejected(free_inodes=100 * P.FREE_INODES, quota_free_inodes=P.FREE_INODES - 1)

    def test_verified_no_quota_is_explicit(self):
        value = {
            **self.obs,
            "quota_status": "not_applicable_verified",
            "quota_free_bytes": None,
            "quota_free_inodes": None,
        }
        self.assertFalse(P.assess_storage(value, self.plan, os.getuid())["native_release"])

    def test_ram_and_network_filesystems_rejected(self):
        for name in ("tmpfs", "ramfs", "nfs", "nfs4", "lustre", "overlay", "unknown"):
            self.rejected(filesystem=name)
        self.rejected(ram_backed=True)
        self.rejected(shared=True)

    def test_private_owner_and_mode_required(self):
        self.rejected(uid=os.getuid() + 1)
        self.rejected(mode=0o755)

    def test_device_identity_mismatch_rejected(self):
        self.rejected(mount_device="8:2")
        self.rejected(device=True, mount_device=True)

    def test_allocation_plan_cannot_silently_change(self):
        for value in (8192, 3000, 1):
            self.rejected(allocation_block_bytes=value)

    def test_unknown_missing_fields_rejected(self):
        value = dict(self.obs)
        value.pop("device")
        with self.assertRaises(ValueError):
            P.assess_storage(value, self.plan, os.getuid())

    def test_strict_counter_types(self):
        for name in (
            "free_bytes",
            "free_inodes",
            "allocation_block_bytes",
            "quota_free_bytes",
            "quota_free_inodes",
        ):
            for value in (True, 1.0, -1):
                self.rejected(**{name: value})

    def test_plan_cannot_exceed_original_guards(self):
        for key, value in (
            ("planned_bytes", P.FREE_BYTES + 1),
            ("planned_inodes", P.FREE_INODES + 1),
            ("planned_bytes", True),
        ):
            with self.assertRaises(ValueError):
                P.assess_storage(self.obs, {**self.plan, key: value}, os.getuid())


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / "pkg"
        self.source.mkdir()
        (self.source / "file").write_bytes(b"known")
        (self.source / "manifest.json").write_text(
            json.dumps({"files": {"file": S.sha(self.source / "file")}})
        )
        self.manifest = S.sha(self.source / "manifest.json")
        self.archive = self.root / "input.tar.gz"
        self.destination = self.root / "stage"
        # Parser/byte-copy unit cases use explicit synthetic capacity. The real
        # Mac admission is recorded separately and must never be overridden.
        self.capacity = types.SimpleNamespace(
            f_bavail=P.FREE_BYTES // 4096, f_frsize=4096, f_favail=P.FREE_INODES
        )
        capacity_patch = patch.object(S.os, "statvfs", return_value=self.capacity)
        capacity_patch.start()
        self.addCleanup(capacity_patch.stop)

    def pack(self, extra=None, bad_bytes=None, unsafe_mode=False):
        with tarfile.open(self.archive, "w:gz") as archive:
            for name in ("file", "manifest.json"):
                value = (self.source / name).read_bytes()
                if name == "file" and bad_bytes is not None:
                    value = bad_bytes
                info = tarfile.TarInfo("pkg/" + name)
                info.size = len(value)
                info.mode = 0o4755 if unsafe_mode else 0o640
                archive.addfile(info, io.BytesIO(value))
            if extra:
                archive.addfile(extra, io.BytesIO(b""))

    def stage(self, digest=None, verifier=None):
        return S.stage_exact(
            self.archive,
            self.source,
            self.destination,
            digest or S.sha(self.archive),
            self.manifest,
            verifier,
        )

    def test_exact_stage_preserves_source_and_mode(self):
        self.pack()
        root = self.stage()
        self.assertEqual((root / "file").read_bytes(), b"known")
        self.assertEqual((root / "file").stat().st_mode & 0o777, 0o640)
        self.assertEqual(S.sha(self.source / "manifest.json"), self.manifest)
        self.assertFalse(
            json.loads((self.destination / "stage-receipt.json").read_text())["native_release"]
        )

    def test_real_verifier_is_delegated_for_original_and_copy(self):
        self.pack()
        calls = []
        root = self.stage(verifier=lambda p: calls.append(Path(p)))
        self.assertEqual(calls, [self.source, root, self.source])

    def test_wrong_archive_digest_rejected_before_output(self):
        self.pack()
        with self.assertRaises(ValueError):
            self.stage("0" * 64)
        self.assertFalse(self.destination.exists())

    def test_wrong_manifest_rejected(self):
        self.pack()
        self.manifest = "0" * 64
        with self.assertRaises(ValueError):
            self.stage()

    def test_existing_output_preserved(self):
        self.pack()
        self.destination.mkdir()
        (self.destination / "keep").write_bytes(b"preserve")
        with self.assertRaises(FileExistsError):
            self.stage()
        self.assertEqual((self.destination / "keep").read_bytes(), b"preserve")

    def test_member_hash_failure_keeps_partial(self):
        self.pack(bad_bytes=b"wrong")
        with self.assertRaises(ValueError):
            self.stage()
        self.assertEqual((self.destination / "pkg/file").read_bytes(), b"wrong")
        self.assertEqual((self.source / "file").read_bytes(), b"known")

    def test_duplicate_missing_and_extra_members_rejected(self):
        for name in ("pkg/file", "pkg/extra", "other/file"):
            self.pack(extra=tarfile.TarInfo(name))
            with self.assertRaises(ValueError):
                self.stage()

    def test_symlink_hardlink_and_traversal_rejected(self):
        for kind, name in (
            (tarfile.SYMTYPE, "pkg/file"),
            (tarfile.LNKTYPE, "pkg/file"),
            (tarfile.REGTYPE, "../escape"),
        ):
            with tarfile.open(self.archive, "w:gz") as archive:
                info = tarfile.TarInfo(name)
                info.type = kind
                info.mode = 0o640
                info.linkname = "file"
                info.size = 5 if kind == tarfile.REGTYPE else 0
                archive.addfile(info, io.BytesIO(b"known") if info.isfile() else None)
                data = (self.source / "manifest.json").read_bytes()
                manifest = tarfile.TarInfo("pkg/manifest.json")
                manifest.size = len(data)
                archive.addfile(manifest, io.BytesIO(data))
            with self.assertRaises(ValueError):
                self.stage()

    def test_elevated_mode_rejected(self):
        self.pack(unsafe_mode=True)
        with self.assertRaises(ValueError):
            self.stage()

    def test_source_symlink_rejected(self):
        self.pack()
        (self.source / "file").unlink()
        (self.source / "file").symlink_to(self.root / "missing")
        with self.assertRaises(ValueError):
            self.stage()

    def test_native_environment_rejected(self):
        self.pack()
        with patch.dict(os.environ, SLURM_JOB_ID="21595967"), self.assertRaises(RuntimeError):
            self.stage()

    def test_insufficient_actual_shape_capacity_stops_before_output(self):
        self.pack()
        self.capacity.f_bavail = 4315873280 // 4096
        with self.assertRaisesRegex(ValueError, "headroom"):
            self.stage()
        self.assertFalse(self.destination.exists())

    def test_same_count_duplicate_member_rejected(self):
        with tarfile.open(self.archive, "w:gz") as archive:
            for _ in range(2):
                info = tarfile.TarInfo("pkg/file")
                info.size = 5
                archive.addfile(info, io.BytesIO(b"known"))
        with self.assertRaises(ValueError):
            self.stage()


class BindingTests(unittest.TestCase):
    def test_all_input_destinations_stay_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / "ASSET-PLAN.json").write_text(
                json.dumps({"frozen_aliases": {"trials/reference": {}, "trials/stream": {}}})
            )
            value = S.binding_layout(root, Path("/original"))
            self.assertEqual(len(value["bindings"]), 4)
            self.assertTrue(all(v["mode"] == "ro" for v in value["bindings"]))
            self.assertEqual(value["bindings"][1]["destination"], "/original")
            self.assertFalse(value["executed"])

    def test_escaping_alias_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            (root / "ASSET-PLAN.json").write_text(json.dumps({"frozen_aliases": {"../escape": {}}}))
            with self.assertRaises(ValueError):
                S.binding_layout(root, Path("/original"))


class LifetimeTests(unittest.TestCase):
    def test_delegate_identity_and_restoration(self):
        module = types.ModuleType("offline_storage_lifetime")
        result = {"package": Path(__file__).parent / "placeholder"}

        def original(*args, **kwargs):
            return result

        module.runtime_fixture = original
        sys.modules[module.__name__] = module
        self.addCleanup(sys.modules.pop, module.__name__, None)
        data = {}
        with observe(module, data):
            self.assertIs(module.runtime_fixture(), result)
        self.assertIs(module.runtime_fixture, original)
        self.assertTrue(data["restored"])

    def test_exception_preserves_original_binding(self):
        module = types.SimpleNamespace(
            runtime_fixture=lambda: (_ for _ in ()).throw(ValueError("fault"))
        )
        original = module.runtime_fixture
        # Register a real module so the same alias-installation path is exercised.
        registered = types.ModuleType("offline_storage_failure")
        registered.runtime_fixture = original
        sys.modules[registered.__name__] = registered
        self.addCleanup(sys.modules.pop, registered.__name__, None)
        with self.assertRaises(ValueError), observe(registered, {}):
            registered.runtime_fixture()
        self.assertIs(registered.runtime_fixture, original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
