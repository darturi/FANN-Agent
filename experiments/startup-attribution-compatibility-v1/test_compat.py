"""Capsule/controller/guard/host safety checks; no DB, scheduler or native image."""

import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import cc_control as C
import common as K
import guest as G
import host as H
import package as P


class CapsuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.package = P.build(Path(cls.tmp.name), testing=True)

    def test_exact_main_recipe_and_parent_verify(self):
        contract = K.verify(self.package)
        self.assertEqual(contract["scope"]["tests_per_suite"], 128)
        self.assertEqual(contract["scope"]["SQL"], 0)
        self.assertEqual(contract["limits"]["allocations"], 1)

    def test_archive_regular_unique_exact_bytes(self):
        with tarfile.open(self.package.parent / (K.NAME + ".tar.gz")) as t:
            mem = t.getmembers()
            self.assertEqual(len(mem), len(K.read(self.package / "manifest.json")["files"]) + 1)
            self.assertEqual(len(mem), len({m.name for m in mem}))
            for m in mem:
                self.assertTrue(m.isfile())
                self.assertEqual(
                    __import__("hashlib").sha256(t.extractfile(m).read()).hexdigest(),
                    K.sha(self.package / Path(m.name).relative_to(K.NAME)),
                )

    def test_existing_capsule_never_overwritten(self):
        with self.assertRaises(FileExistsError):
            P.build(self.package.parent, testing=True)

    def test_sealed_builder_does_not_copy_prior_manifest(self):
        with tempfile.TemporaryDirectory() as d, patch("package.HERE", self.package):
            rebuilt = P.build(Path(d), testing=True)
            self.assertEqual(K.verify(rebuilt)["name"], K.NAME)

    def test_package_tamper_rejected(self):
        real = K.sha
        with (
            patch(
                "common.sha",
                side_effect=lambda p: "wrong" if Path(p).name == "guest.py" else real(p),
            ),
            self.assertRaises(ValueError),
        ):
            K.verify(self.package)

    def test_container_binds_no_real_database(self):
        args = H.command(
            Path("/package"),
            Path("/results-host"),
            Path("/private"),
            Path("/image"),
            Path("/apptainer"),
            100,
        )
        text = " ".join(args)
        self.assertIn("/package:/compat:ro", text)
        self.assertIn("--containall", args)
        self.assertIn("/private:/work:rw", text)
        self.assertNotIn("/retained:", text)
        self.assertNotIn("/prepared:", text)
        self.assertIn("CC_DEADLINE=100", args)

    def test_batch_absolute_python_export_and_limits(self):
        text = (self.package / "LAUNCHER.sh").read_text()
        for field in (
            "--cpus-per-task=2",
            "--mem=4G",
            "--time=00:15:00",
            "SLURM_EXPORT_ENV=ALL",
            "srun --export=ALL",
        ):
            self.assertIn(field, text)
        subprocess.run(["/bin/bash", "-n", str(self.package / "LAUNCHER.sh")], check=True)

    def test_missing_launcher_python_stops_before_srun(self):
        r = subprocess.run(
            ["/bin/bash", str(self.package / "LAUNCHER.sh"), *["/x"] * 5, "/absent/python"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(r.returncode, 0)

    def test_connection_guard_restores_real_descriptors(self):
        script = """
import json,psycopg
from check_child import guard
before=psycopg.Connection.__dict__['connect']
with guard() as stats:
    try:psycopg.connect()
    except RuntimeError:pass
assert psycopg.Connection.__dict__['connect'] is before
assert stats['denied_connections']==1 and stats['connection_bindings_restored']
print(json.dumps(stats))
"""
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(P.HERE), "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["denied_connections"], 1)

    def test_guard_blocks_non_fixture_process(self):
        script = """
import subprocess
from check_child import guard
with guard() as stats:
    try:subprocess.run(['/bin/sh','-c','true'])
    except RuntimeError:pass
assert stats['denied_subprocesses']==1
"""
        r = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(P.HERE), "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)


class ControllerTests(unittest.TestCase):
    def case(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        pkg = root / "p"
        pkg.mkdir()
        campaign = root / "campaign"
        campaign.mkdir()
        K.save(pkg / "manifest.json", {})
        b = dict(campaign=str(campaign), package_manifest_sha256=K.sha(pkg / "manifest.json"))
        K.save(pkg / "submission-binding.json", b)
        K.save(root / ("." + K.NAME + "-reservation.json"), b)
        r = dict(
            package=str(pkg),
            campaign=str(campaign),
            package_manifest_sha256=b["package_manifest_sha256"],
            dispatch=None,
            job_id=None,
            account="torch_pr_288_courant",
            python="/usr/bin/python3.12",
            scratch="/scratch",
            run=str(campaign / "run"),
            image="/image",
            apptainer="/apptainer",
        )
        (campaign / "run").mkdir()
        K.save(campaign / "submission.json", r)
        return pkg, campaign, r

    def test_dispatch_recorded_exactly_once(self):
        pkg, campaign, r = self.case()
        with patch(
            "cc_control.subprocess.run",
            return_value=Mock(returncode=0, stdout="12345;torch\n", stderr=""),
        ) as run:
            C.dispatch(pkg, campaign, r)
            with self.assertRaises(RuntimeError):
                C.dispatch(pkg, campaign, r)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(r["job_id"], "12345")

    def test_unknown_dispatch_never_replayed(self):
        pkg, campaign, r = self.case()
        with patch("cc_control.subprocess.run", side_effect=OSError("uncertain")) as run:
            with self.assertRaises(OSError):
                C.dispatch(pkg, campaign, r)
            with self.assertRaises(RuntimeError):
                C.dispatch(pkg, campaign, r)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(r["dispatch"]["status"], "unknown")

    def test_unparseable_id_preserves_unknown(self):
        pkg, campaign, r = self.case()
        with patch(
            "cc_control.subprocess.run",
            return_value=Mock(returncode=0, stdout="unknown", stderr=""),
        ):
            with self.assertRaises(RuntimeError):
                C.dispatch(pkg, campaign, r)
        self.assertEqual(r["dispatch"]["status"], "unknown")

    def test_wrong_binding_blocks_scheduler(self):
        pkg, campaign, r = self.case()
        b = K.read(pkg / "submission-binding.json")
        b["campaign"] = "/wrong"
        K.replace(pkg / "submission-binding.json", b)
        with patch("cc_control.subprocess.run") as run:
            with self.assertRaises(RuntimeError):
                C.dispatch(pkg, campaign, r)
            run.assert_not_called()

    def test_absent_submission_status_is_clear(self):
        pkg, campaign, r = self.case()
        (pkg / "submission-binding.json").unlink()
        with redirect_stdout(io.StringIO()) as out:
            C.status(pkg)
        self.assertIn("Not submitted", out.getvalue())

    def terminal(self):
        pkg, campaign, r = self.case()
        r.update(job_id="12345", dispatch=dict(status="submitted", job_id="12345"))
        K.replace(campaign / "submission.json", r)
        return pkg, campaign, r

    def test_failed_prefix_collects_terminal_raw(self):
        pkg, campaign, r = self.terminal()
        replies = [
            Mock(returncode=0, stdout="", stderr=""),
            Mock(returncode=0, stdout="12345|FAILED|1:0|00:10\n", stderr=""),
        ]
        with (
            patch("cc_control.verify"),
            patch("cc_control.subprocess.run", side_effect=replies),
            redirect_stdout(io.StringIO()),
        ):
            C.collect(pkg)
        self.assertTrue(Path(str(campaign) + ".tar.gz").exists())

    def test_active_job_cannot_be_collected(self):
        pkg, campaign, r = self.terminal()
        with (
            patch("cc_control.verify"),
            patch(
                "cc_control.subprocess.run",
                return_value=Mock(returncode=0, stdout="12345", stderr=""),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "Still queued"):
                C.collect(pkg)

    def test_unknown_scheduler_state_cannot_be_collected(self):
        pkg, campaign, r = self.terminal()
        with (
            patch("cc_control.verify"),
            patch(
                "cc_control.subprocess.run",
                side_effect=[
                    Mock(returncode=0, stdout="", stderr=""),
                    Mock(returncode=0, stdout="", stderr=""),
                ],
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "state unknown"):
                C.collect(pkg)


class EntryTests(unittest.TestCase):
    def guest_case(self, wrong_python=False, fail_suite=False):
        from contextlib import ExitStack
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "results"
            work = root / "work"
            out.mkdir()
            work.mkdir()
            contract = K.read(P.HERE / "COMPATIBILITY-CONTRACT.json")
            target = K.read(K.MAIN / "IMAGE-REFERENCE.json")

            def build(folder, testing):
                candidate = folder / "candidate"
                candidate.mkdir(parents=True)
                K.save(candidate / "experiment.json", dict(synthetic_fixture=True))
                K.save(
                    candidate / "manifest.json", dict(files=contract["main_recipe_files_sha256"])
                )
                return candidate

            def child(args, **kw):
                receipt = Path(args[args.index("--receipt") + 1])
                guard = Path(args[args.index("--guard-receipt") + 1])
                K.save(
                    receipt,
                    dict(
                        status="fail" if fail_suite else "pass",
                        tests_run=128,
                        python="3.12.15",
                        recipe_files_sha256=contract["main_recipe_files_sha256"],
                    ),
                )
                K.save(
                    guard,
                    dict(
                        denied_connections=0,
                        denied_subprocesses=0,
                        connection_bindings_restored=True,
                    ),
                )
                proc = Mock()
                proc.poll.return_value = 0
                proc.returncode = 0
                return proc

            actual_read = K.read
            with ExitStack() as stack:
                stack.enter_context(
                    patch.dict(os.environ, CC_DEADLINE=str(__import__("time").monotonic() + 720))
                )
                stack.enter_context(
                    patch(
                        "guest.Path",
                        side_effect=lambda p: {"/results": out, "/work": work}.get(str(p), Path(p)),
                    )
                )
                stack.enter_context(
                    patch(
                        "guest.read",
                        side_effect=lambda p: (
                            contract
                            if str(p) == "/compat/COMPATIBILITY-CONTRACT.json"
                            else actual_read(p)
                        ),
                    )
                )
                stack.enter_context(
                    patch(
                        "guest.platform.python_version",
                        return_value="3.12.7" if wrong_python else "3.12.15",
                    )
                )
                stack.enter_context(patch("guest.platform.system", return_value="Linux"))
                stack.enter_context(patch("guest.platform.machine", return_value="x86_64"))
                stack.enter_context(patch("guest.signal.signal"))
                stack.enter_context(patch("guest.signal.alarm"))
                stack.enter_context(patch("guest.subprocess.Popen", side_effect=child))
                stack.enter_context(
                    patch.dict(
                        sys.modules,
                        {
                            "experiment": SimpleNamespace(
                                __file__=str(K.MAIN / "experiment.py"), build=build
                            )
                        },
                    )
                )
                import sys as actual_sys

                actual_sys.path.insert(0, str(K.MAIN))
                import sa_driver

                stack.enter_context(patch.object(sa_driver, "provenance", return_value=target))
                with self.assertRaises(SystemExit) as exit_result:
                    G.main()
            return exit_result.exception.code, K.read(out / "status.json")

    def test_guest_complete_two_suites_and_sealed_candidate(self):
        code, status = self.guest_case()
        self.assertEqual(code, 0)
        self.assertEqual(status["status"], "complete")
        self.assertEqual(set(status["result"]), {"source", "sealed", "candidate_manifest_sha256"})
        self.assertFalse(status["main_A2_launched"])

    def test_guest_wrong_target_stops_before_tests(self):
        code, status = self.guest_case(wrong_python=True)
        self.assertEqual(code, 1)
        self.assertEqual(status["result"], {})

    def test_guest_failed_source_prevents_sealed_progress(self):
        code, status = self.guest_case(fail_suite=True)
        self.assertEqual(code, 1)
        self.assertNotIn("sealed", status["result"])

    def host_case(self, fail=False):
        from contextlib import ExitStack
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            package = root / "p"
            package.mkdir()
            out = root / "out"
            out.mkdir()
            scratch = root / "scratch"
            scratch.mkdir()
            K.save(package / "manifest.json", {})

            def launch(*a, **kw):
                K.save(out / "status.json", dict(status="failed" if fail else "complete"))
                proc = Mock()
                proc.wait.return_value = 1 if fail else 0
                proc.poll.return_value = proc.wait.return_value
                return proc

            with ExitStack() as stack:
                stack.enter_context(
                    patch(
                        "sys.argv",
                        [
                            "host.py",
                            str(package),
                            str(out),
                            str(scratch),
                            "/image",
                            "/apptainer",
                            sys.executable,
                        ],
                    )
                )
                stack.enter_context(patch.dict(os.environ, SLURM_JOB_ID="12345"))
                stack.enter_context(
                    patch("host.os.uname", return_value=SimpleNamespace(sysname="Linux"))
                )
                stack.enter_context(patch("host.verify"))
                stack.enter_context(
                    patch(
                        "host.sha",
                        side_effect=lambda p: K.IMAGE if str(p) == "/image" else K.sha(p),
                    )
                )
                stack.enter_context(patch("host.signal.signal"))
                stack.enter_context(patch("host.signal.alarm"))
                stack.enter_context(patch("host.subprocess.Popen", side_effect=launch))
                with self.assertRaises(SystemExit) as e:
                    H.main()
            return e.exception.code, K.read(out / "LOCK.json"), K.read(out / "host-exit.json")

    def test_actual_host_entry_completes_with_lock(self):
        code, lock, host = self.host_case()
        self.assertEqual(code, 0)
        self.assertTrue(lock["complete"])
        self.assertEqual(host["exit_code"], 0)

    def test_actual_host_entry_failure_keeps_incomplete_lock(self):
        code, lock, host = self.host_case(True)
        self.assertEqual(code, 1)
        self.assertFalse(lock["complete"])
        self.assertEqual(host["exit_code"], 1)


if __name__ == "__main__":
    unittest.main()
