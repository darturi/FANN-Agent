import hashlib
import io
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
import pc_common as C
import pc_control as control


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        cls.package = E.build(cls.root / "seed", testing=True)

    def test_seal_verifies_resource_protocol(self):
        self.assertEqual(C.verify(self.package)["resource_contract_sha256"], C.RESOURCE_SHA)
        self.assertEqual(C.verify(self.package)["counts"]["searches_total"], 0)

    def test_synthetic_cannot_submit(self):
        with patch("pc_control.subprocess.run") as run:
            with self.assertRaises(ValueError):
                control.submit(self.package, Path("/bundle"), Path("/results"))
            run.assert_not_called()

    def test_archive_all_members_match(self):
        archive = self.package.parent / (C.NAME + ".tar.gz")
        manifest = C.read(self.package / "manifest.json")
        with tarfile.open(archive) as tar:
            members = tar.getmembers()
            self.assertEqual(len(members), len(manifest["files"]) + 1)
            for m in members:
                self.assertTrue(m.isfile())
                self.assertEqual(
                    hashlib.sha256(tar.extractfile(m).read()).hexdigest(),
                    C.sha(self.package / Path(m.name).relative_to(C.NAME)),
                )

    def test_native_frozen_files_byte_identical(self):
        for n, h in C.read(self.package / "frozen/manifest.json")["files"].items():
            self.assertEqual(C.sha(self.package / "frozen" / n), h)

    def test_new_design_and_old_design_separate(self):
        self.assertEqual(C.sha(self.package / "DESIGN.md"), C.STREAM_DESIGN_SHA)
        self.assertEqual(C.sha(self.package / "B2F-DESIGN.md"), C.CONTRACT["design_sha256"])

    def test_code_tamper_rejected(self):
        old = C.sha
        with patch(
            "pc_common.sha",
            side_effect=lambda p: "bad" if Path(p).name == "pc_runtime.py" else old(p),
        ):
            with self.assertRaises(ValueError):
                C.verify(self.package)

    def test_archive_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            name = C.PREFIX + "20261028T010000Z.bad"
            archive = p / (name + ".tar.gz")
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo(name + "/../outside")
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
            with self.assertRaises(ValueError):
                E.extract_data(archive, p / "out")
            self.assertFalse((p / "out/outside").exists())

    def test_symlink_member_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            name = C.PREFIX + "20261028T010000Z.bad"
            archive = p / (name + ".tar.gz")
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo(name + "/x")
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc/passwd"
                tar.addfile(info)
            with self.assertRaises(ValueError):
                E.extract_data(archive, p / "out")

    def test_wrong_archive_prefix_rejected(self):
        with self.assertRaises(ValueError):
            E.extract_data(Path("/tmp/wrong.tar.gz"), self.root / "out")

    def test_no_remote_python_execution_in_analysis(self):
        self.assertNotIn("exec(", Path(E.__file__).read_text())
        self.assertNotIn("importlib", Path(E.__file__).read_text())

    def test_failed_raw_collect_does_not_analyze_performance(self):
        self.assertNotIn("bootstrap(", Path(control.__file__).read_text())
        self.assertNotIn("sr_report", Path(control.__file__).read_text())

    def test_exact_commands_state_zero_search_and_additional_allocation(self):
        commands = E.commands()
        self.assertIn("ONE ADDITIONAL", commands)
        self.assertIn("zero ANN/exact", commands)


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        cls.package = E.build(cls.root / "seed", testing=True)

    def upload(self, failure):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            binary = root / "bin"
            binary.mkdir()
            remote = root / "remote"
            remote.mkdir()
            log = root / "log"
            for n in [C.NAME + ".tar.gz", C.NAME + ".tar.gz.sha256"]:
                shutil.copyfile(self.package.parent / n, root / n)
            script = E.transfer_script(self.package).replace(str(E.OUTPUT), str(root))
            (root / "transfer.sh").write_text(script)
            ssh = """#!PYTHON
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['LOG'],'a') as h:h.write('ssh '+json.dumps(args)+'\\n')
if '-O' in args:raise SystemExit(0)
if '-t' in args:raise SystemExit(1 if os.environ['FAIL']=='auth' else 0)
if os.environ['FAIL']=='remotehash':raise SystemExit(1)
for name in ['NAME.tar.gz','NAME.tar.gz.sha256']:
 path=Path(os.environ['REMOTE'])/name
 if not path.exists():raise SystemExit(1)
raise SystemExit(0)
""".replace("PYTHON", sys.executable).replace("NAME", C.NAME)
            scp = """#!PYTHON
import json,os,shutil,sys
from pathlib import Path
with open(os.environ['LOG'],'a') as h:h.write('scp '+json.dumps(sys.argv[1:])+'\\n')
if os.environ['FAIL']=='scp':raise SystemExit(1)
for n in ['NAME.tar.gz','NAME.tar.gz.sha256']:shutil.copyfile(n,Path(os.environ['REMOTE'])/n)
""".replace("PYTHON", sys.executable).replace("NAME", C.NAME)
            for name, text in [("ssh", ssh), ("scp", scp)]:
                p = binary / name
                p.write_text(text)
                p.chmod(0o700)
            result = subprocess.run(
                ["/bin/bash", str(root / "transfer.sh"), "upload"],
                env={
                    **os.environ,
                    "PATH": str(binary) + ":/usr/bin:/bin",
                    "FAIL": failure,
                    "REMOTE": str(remote),
                    "LOG": str(log),
                },
                capture_output=True,
                text=True,
            )
            return result, log.read_text() if log.exists() else "", list(remote.iterdir())

    def test_upload_mfa_failure_never_scp_or_success(self):
        r, log, remote = self.upload("auth")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("scp ", log)
        self.assertNotIn("UPLOAD VERIFIED", r.stdout)

    def test_upload_scp_failure_never_claims_success(self):
        r, log, remote = self.upload("scp")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("UPLOAD VERIFIED", r.stdout)

    def test_upload_remote_hash_failure_never_claims_success(self):
        r, log, remote = self.upload("remotehash")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("UPLOAD VERIFIED", r.stdout)

    def test_upload_success_requires_both_remote_files(self):
        r, log, remote = self.upload("")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(remote), 2)
        self.assertIn("UPLOAD VERIFIED", r.stdout)
