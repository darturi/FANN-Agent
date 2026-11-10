"""Bounded inspection, exact references, no actions and transport/replay negatives."""

import copy
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import experiment as E
import inspect_image as I


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        cls.package = E.build(cls.root / "seed", testing=True)

    def copied(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / I.NAME
        shutil.copytree(self.package, out)
        return out

    def test_capsule_and_original_reference_pins(self):
        cfg = I.verify(self.package)
        self.assertFalse(cfg["native_handoff_released"])
        self.assertEqual(cfg["searches"], 0)
        parent = I.read_json(E.SOURCE / "manifest.json")["files"]
        for n, h in cfg["reference_files_sha256"].items():
            self.assertEqual(h, parent[n])
            self.assertEqual(I.file_sha(self.package / "reference" / n), h)

    def test_no_datasets_graphs_or_job_entry_points(self):
        names = I.read_json(self.package / "manifest.json")["files"]
        self.assertFalse(
            any("inputs/" in n or n.endswith("vector.so") or "control.py" in n for n in names)
        )
        self.assertFalse(any(n.endswith(".sbatch") for n in names))

    def test_archive_exact_regular_unique_members(self):
        archive = self.package.parent / (I.NAME + ".tar.gz")
        with tarfile.open(archive) as t:
            members = t.getmembers()
            expected = I.read_json(self.package / "manifest.json")["files"]
            self.assertEqual(len(members), len(expected) + 1)
            self.assertEqual(len({m.name for m in members}), len(members))
            for m in members:
                self.assertTrue(m.isfile())
                self.assertEqual(
                    __import__("hashlib").sha256(t.extractfile(m).read()).hexdigest(),
                    I.file_sha(self.package / Path(m.name).relative_to(I.NAME)),
                )

    def test_existing_capsule_not_overwritten(self):
        with self.assertRaises(FileExistsError):
            E.build(self.package.parent)

    def test_tampered_reference_rejected(self):
        p = self.copied()
        (p / "reference/DRIVER-REFERENCE.json").write_text("{}")
        with self.assertRaises(ValueError):
            I.verify(p)

    def test_extra_file_rejected(self):
        p = self.copied()
        (p / "surprise").write_text("x")
        with self.assertRaises(ValueError):
            I.verify(p)

    def test_missing_file_rejected(self):
        p = self.copied()
        (p / "reference/sa_monitor.py").unlink()
        with self.assertRaises(ValueError):
            I.verify(p)

    def test_symlink_rejected(self):
        p = self.copied()
        (p / "link").symlink_to(p / "README.md")
        with self.assertRaises(ValueError):
            I.verify(p)

    def test_comparison_preserves_every_difference(self):
        actual = dict(python="3.12.15", libpq=180006)
        ref = dict(python="3.12.7", libpq=180005)
        before = copy.deepcopy(ref)
        self.assertEqual(set(I.compare(actual, ref)), {"python", "libpq"})
        self.assertEqual(ref, before)

    def test_unknown_provenance_fields_rejected(self):
        with self.assertRaises(ValueError):
            I.compare(dict(python="3.12.15"), dict(python="3.12.7", libpq=18))

    def test_source_read_limit(self):
        m = I.Meter()
        m.reads = 128
        with self.assertRaises(RuntimeError):
            m.read_file(self.package / "README.md")

    def test_source_byte_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "large"
            p.write_bytes(b"x" * 65537)
            with self.assertRaises(RuntimeError):
                I.Meter().read_file(p)

    def test_callback_limit(self):
        m = I.Meter()
        for _ in range(16):
            m.callback(True)
        with self.assertRaises(RuntimeError):
            m.callback(True)

    def test_actual_source_mapping_literals_and_library_inspection_only(self):
        report = I.collect(self.package)
        self.assertTrue(report["literal_monitoring"]["restored"])
        self.assertTrue(report["original_function_mapping"]["original_bindings_unchanged"])
        self.assertFalse(report["native_handoff_released"])
        self.assertLessEqual(report["accounting"]["literal_callbacks"], 16)
        self.assertEqual(report["snapshot_calls"], 0)
        self.assertEqual(report["database_connections"], 0)
        self.assertEqual(report["slurm_submissions"], 0)
        from sa_monitor import idle

        idle()

    def test_no_external_actions_and_exact_descriptor_restoration(self):
        sys.path.insert(0, str(self.package / "reference"))
        import socket

        import psycopg

        original = psycopg.Connection.__dict__["connect"]
        with self.assertRaisesRegex(RuntimeError, "injected"):
            with I.no_external_actions():
                for fn in [
                    psycopg.connect,
                    psycopg.Connection.connect,
                    psycopg.AsyncConnection.connect,
                    socket.socket,
                    subprocess.Popen,
                ]:
                    with self.assertRaisesRegex(RuntimeError, "prohibits"):
                        fn()
                raise RuntimeError("injected")
        self.assertIs(psycopg.Connection.__dict__["connect"], original)

    def test_patch_mismatch_is_recorded_without_reference_change(self):
        I.collect(self.package)
        import sa_driver

        original = sa_driver.provenance

        def mismatch(reader):
            result = original(reader)
            result["python"] = "3.12.15"
            return result

        before = I.file_sha(self.package / "reference/DRIVER-REFERENCE.json")
        with patch("sa_driver.provenance", side_effect=mismatch):
            report = I.collect(self.package)
        self.assertEqual(report["status"], "inventory_complete_reference_mismatch")
        self.assertEqual(report["A1_reference_differences"]["python"]["actual"], "3.12.15")
        self.assertFalse(report["native_handoff_released"])
        self.assertEqual(I.file_sha(self.package / "reference/DRIVER-REFERENCE.json"), before)

    def test_preexisting_monitor_is_not_stolen(self):
        I.collect(self.package)
        sys.monitoring.use_tool_id(3, "test-existing")
        try:
            with self.assertRaisesRegex(RuntimeError, "Pre-existing"):
                I.collect(self.package)
            self.assertEqual(sys.monitoring.get_tool(3), "test-existing")
        finally:
            sys.monitoring.free_tool_id(3)

    def test_wrapper_syntax_limits_and_no_job(self):
        p = self.package / "run-on-torch.sh"
        subprocess.run(["/bin/bash", "-n", str(p)], check=True)
        text = p.read_text()
        for token in (
            "--containall",
            "/inspect:ro",
            "timeout --signal=TERM",
            "set -C",
            "test ! -e",
            I.IMAGE,
        ):
            self.assertIn(token, text)
        for token in ("sbatch", "srun", "/retained:", "/prepared:"):
            self.assertNotIn(token, text)

    def test_verify_CLI_does_not_inspect_runtime(self):
        result = subprocess.run(
            [sys.executable, str(self.package / "inspect_image.py"), "verify"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no job", result.stdout)

    def returned(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        report = I.collect(self.package)
        report.update(
            image_sha256=I.IMAGE,
            parent_A1_manifest_sha256=I.PARENT,
            capsule_manifest_sha256=I.file_sha(self.package / "manifest.json"),
        )
        (d / "image-capability.json").write_text(json.dumps(report))
        (d / "stderr.log").write_text("")
        (d / "exit-code.txt").write_text("0\n")
        self.checksums(d)
        return d

    def checksums(self, d):
        (d / "SHA256SUMS").write_text(
            "".join(
                I.file_sha(d / n) + "  " + n + "\n"
                for n in ("image-capability.json", "stderr.log", "exit-code.txt")
            )
        )

    def test_data_only_return_check_keeps_gate_closed(self):
        result = E.check_return(self.returned(), self.package)
        self.assertEqual(result["transport_integrity"], "pass")
        self.assertFalse(result["native_handoff_released"])

    def test_return_checksum_tampering(self):
        d = self.returned()
        (d / "stderr.log").write_text("altered")
        with self.assertRaises(ValueError):
            E.check_return(d, self.package)

    def test_return_wrong_capsule_or_image_identity(self):
        for key in ("image_sha256", "capsule_manifest_sha256", "parent_A1_manifest_sha256"):
            with self.subTest(key=key):
                d = self.returned()
                r = I.read_json(d / "image-capability.json")
                r[key] = "bad"
                (d / "image-capability.json").write_text(json.dumps(r))
                self.checksums(d)
                with self.assertRaises(ValueError):
                    E.check_return(d, self.package)

    def test_return_cannot_open_release(self):
        d = self.returned()
        r = I.read_json(d / "image-capability.json")
        r["native_handoff_released"] = True
        (d / "image-capability.json").write_text(json.dumps(r))
        self.checksums(d)
        with self.assertRaises(ValueError):
            E.check_return(d, self.package)

    def test_return_status_must_match_full_identity_comparison(self):
        d = self.returned()
        r = I.read_json(d / "image-capability.json")
        r["status"] = (
            "inventory_complete_reference_mismatch"
            if not r["A1_reference_differences"]
            else "inventory_complete_reference_match"
        )
        (d / "image-capability.json").write_text(json.dumps(r))
        self.checksums(d)
        with self.assertRaises(ValueError):
            E.check_return(d, self.package)

    def test_return_complete_with_failed_exit_rejected(self):
        d = self.returned()
        (d / "exit-code.txt").write_text("1\n")
        self.checksums(d)
        with self.assertRaises(ValueError):
            E.check_return(d, self.package)

    def test_source_failure_preserves_actual_driver_evidence(self):
        I.collect(self.package)
        partial = {}
        with patch(
            "sa_monitor.SnapshotMonitor.validate", side_effect=RuntimeError("source mismatch")
        ):
            with self.assertRaisesRegex(RuntimeError, "source mismatch"):
                I.collect(self.package, partial)
        self.assertIn("actual_driver", partial)
        self.assertIn("A1_reference_differences", partial)

    def transport_case(self, action, fail_auth=False, wrong_binding=False):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        helper = d / "transfer.sh"
        helper.write_text(E.transfer_script(self.package, d))
        for suffix in (".tar.gz", ".tar.gz.sha256"):
            shutil.copyfile(self.package.parent / (I.NAME + suffix), d / (I.NAME + suffix))
        bins = d / "bin"
        bins.mkdir()
        log = d / "calls.jsonl"
        for name in ("ssh", "scp"):
            stub = bins / name
            stub.write_text(
                "#!"
                + sys.executable
                + "\n"
                + """
import os,sys,json
from pathlib import Path
with open(os.environ['PROBE_CALLS'],'a') as f:
    f.write(json.dumps([Path(sys.argv[0]).name,sys.argv[1:]])+'\\n')
if Path(sys.argv[0]).name=='ssh' and '-t' in sys.argv and os.environ['FAIL_AUTH']=='1':sys.exit(1)
if Path(sys.argv[0]).name=='scp' and sys.argv[-2].endswith('binding.json'):
    Path(sys.argv[-1]).write_text(json.dumps(dict(directory='/home/dar579/torch-reviews-results/startup-attribution-image-preflight-v1.ABCD1234',capsule_manifest_sha256=os.environ['BINDING_SHA'])))
"""
            )
            stub.chmod(0o700)
        result = subprocess.run(
            ["/bin/bash", str(helper), action],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PATH": str(bins) + ":" + os.environ["PATH"],
                "PROBE_CALLS": str(log),
                "FAIL_AUTH": str(int(fail_auth)),
                "BINDING_SHA": "wrong"
                if wrong_binding
                else I.file_sha(self.package / "manifest.json"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        calls = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
        return result, calls

    def test_transfer_auth_failure_stops_before_scp(self):
        result, calls = self.transport_case("upload", fail_auth=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c[0] == "scp" for c in calls))

    def test_transfer_upload_auth_precedes_copy_and_remote_hash(self):
        result, calls = self.transport_case("upload")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([c[0] for c in calls], ["ssh", "scp", "ssh", "ssh"])
        self.assertIn("UPLOAD VERIFIED", result.stdout)
        self.assertTrue(any("sha256sum" in arg for arg in calls[2][1]))

    def test_transfer_wrong_download_binding_stops_before_result_copy(self):
        result, calls = self.transport_case("download", wrong_binding=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sum(c[0] == "scp" for c in calls), 1)


if __name__ == "__main__":
    unittest.main()
