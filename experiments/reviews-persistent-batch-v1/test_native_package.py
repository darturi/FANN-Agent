"""Local held-package and native lifecycle checks using only test doubles."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import rb_native
from rb_seal import (
    PACKAGE_NAME,
    make_archive,
    seal_directory,
    sha_bytes,
    verify_archive,
    verify_directory,
)


class NativePackageTests(unittest.TestCase):
    def test_relocated_guest_defaults_to_its_own_inputs(self):
        with tempfile.TemporaryDirectory() as scratch:
            package = Path(scratch).resolve() / "patch"
            package.mkdir()
            (package / "inputs").mkdir()
            shutil.copyfile(Path(__file__).with_name("rb_plan.py"), package / "rb_plan.py")
            subprocess.run(
                [
                    sys.executable,
                    "-EsB",
                    "-c",
                    "from pathlib import Path; import rb_plan; "
                    "assert rb_plan.ROOT == Path.cwd() / 'inputs'",
                ],
                cwd=package,
                check=True,
                timeout=10,
            )

    def test_seal_archive_parity_and_changed_directory_rejection(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            package = root / PACKAGE_NAME
            package.mkdir()
            item = package / "candidate.json"
            item.write_bytes(b"fixture")
            checksum = seal_directory(package)
            archive = root / f"{PACKAGE_NAME}.tar.gz"
            make_archive(package, archive, checksum)
            self.assertEqual(verify_archive(archive, checksum), verify_directory(package, checksum))
            item.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "sealed inventory"):
                verify_directory(package, checksum)

    def test_unlisted_symlink_and_unsafe_archive_are_rejected(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            package = root / PACKAGE_NAME
            package.mkdir()
            (package / "file").write_bytes(b"test")
            checksum = seal_directory(package)
            (package / "linked").symlink_to(package / "file")
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                verify_directory(package, checksum)
            archive = root / "unsafe.tar.gz"
            with tarfile.open(archive, "x:gz") as tar:
                member = tarfile.TarInfo(f"{PACKAGE_NAME}/../outside")
                member.size = 1
                tar.addfile(member, io.BytesIO(b"x"))
            with self.assertRaisesRegex(ValueError, "Unsafe path"):
                verify_archive(archive, checksum)

    def test_admission_needs_the_exact_job_and_package(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "admission.json"
            record = {
                "schema": "reviews-persistent-batch.single-approved-allocation.v1",
                "package_manifest_sha256": "a" * 64,
                "candidate": rb_native.CANDIDATE,
                "job_id": "12345",
                "uid": 501,
            }
            data = json.dumps(record).encode()
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "digest differs"):
                rb_native.admission(path, "b" * 64, "a" * 64)
            with (
                patch.object(
                    rb_native.os,
                    "uname",
                    return_value=SimpleNamespace(sysname="Linux", machine="x86_64"),
                ),
                patch.object(rb_native.os, "getuid", return_value=501),
            ):
                with patch.dict(rb_native.os.environ, {"SLURM_JOB_ID": "999"}):
                    with self.assertRaisesRegex(ValueError, "named native"):
                        rb_native.admission(path, sha_bytes(data), "a" * 64)
                with patch.dict(rb_native.os.environ, {"SLURM_JOB_ID": "12345"}):
                    self.assertEqual(rb_native.admission(path, sha_bytes(data), "a" * 64), record)

    def test_guest_preserves_restore_failure_and_always_cleans_up(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            work = root / "work"
            work.mkdir()
            (work / "socket").mkdir()
            output = root / "guest"
            events = []

            def fail_restore(*_args):
                events.append("restore")
                raise RuntimeError("fixture restore failure")

            def stop(folder):
                self.assertEqual(folder, work)
                events.append("stop")

            stage = SimpleNamespace(
                manifest_sha="a" * 64,
                source=root,
                frozen=SimpleNamespace(
                    profile=SimpleNamespace(fingerprint="b", native_registry_hash="c"),
                    execution=SimpleNamespace(load_backend=lambda _: (None, None)),
                    restore=fail_restore,
                    stop=stop,
                ),
            )
            with (
                patch.object(rb_native, "watchdog", side_effect=lambda _: nullcontext()),
                patch.object(rb_native, "resource_limits", return_value=({}, root)),
                patch.object(rb_native, "memory_events", return_value={"max": 0}),
                patch.object(rb_native, "check_native_inputs", return_value={"verified": True}),
            ):
                code = rb_native.run_guest(
                    stage, {"job_id": "12345"}, root, root, work, output, time.monotonic_ns()
                )
            self.assertEqual(code, 1)
            self.assertEqual(events, ["restore", "stop"])
            result = json.loads((output / "guest-exit.json").read_bytes())
            self.assertFalse(result["development_qualifier"])
            self.assertTrue((output / "guest-lock.json").is_file())
            self.assertFalse((output / "capture").exists())


if __name__ == "__main__":
    unittest.main()
