import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import experiment as E
import pc_common as C
import pc_control as control
import pc_job as J
import sr_host as H
from test_fixtures import rewrite


class HostTests(unittest.TestCase):
    def test_container_read_only_sources(self):
        with patch.dict(os.environ, SLURM_JOB_ID="42", SLURM_CPUS_PER_TASK="4"):
            with patch("pc_job.read", return_value={"image_sha256": "pinned"}):
                cmd = J.container_command(
                    Path("/package"),
                    Path("/bundle"),
                    Path("/prepared"),
                    Path("/out"),
                    Path("/work"),
                    "/apptainer",
                    0,
                )
        self.assertIn("/package:/patch:ro", cmd)
        self.assertIn("/prepared:/prepared:ro", cmd)
        self.assertIn("--cleanenv", cmd)
        self.assertIn("/patch/pc_runtime.py", cmd)
        self.assertTrue(any(v.endswith(":/retained:ro") for v in cmd))
        self.assertNotIn("pc_measure.py", " ".join(cmd))

    def test_absolute_python_in_batch(self):
        record = dict(
            account="torch_pr_288_courant",
            bundle="/bundle",
            prepared="/prepared",
            campaign="/campaign",
            workspace="/scratch",
            sources="/results",
            apptainer="/apptainer",
            host_python="/usr/bin/python3.12",
        )
        cmd = control.command(Path("/package"), record, [])
        self.assertEqual(cmd[-1], "/usr/bin/python3.12")
        self.assertIn("--export=NONE", cmd)

    def test_sampler_readiness_failure_reaped(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rewrite(out / "memory-health.json", {"status": "failed"})
            proc = Mock()
            proc.poll.return_value = None
            with self.assertRaises(RuntimeError):
                H.start_sampler(Path("/package"), out, Path("/python"), 123, run=lambda *a: proc)
            proc.terminate.assert_called_once()
            proc.wait.assert_called_once()

    def test_sampler_lost_requests_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rewrite(out / "memory-health.json", {"status": "failed"})
            proc = Mock()
            proc.poll.side_effect = [None, 1]
            proc.returncode = 1
            sampler = Mock()
            sampler.poll.return_value = 1
            with self.assertRaises(RuntimeError):
                H.monitor(proc, sampler, out, sleep=lambda n: None)
            proc.terminate.assert_called_once()

    def test_complete_sampler_stopped_and_joined(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rewrite(out / "memory-summary.json", {"status": "complete"})
            proc = Mock()
            proc.poll.return_value = 0
            proc.returncode = 0
            H.stop_sampler(proc, out)
            self.assertTrue((out / "memory-stop.json").exists())

    def test_failed_sampler_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as d:
            proc = Mock()
            proc.poll.return_value = 1
            proc.returncode = 1
            with self.assertRaises(RuntimeError):
                H.stop_sampler(proc, Path(d))

    def test_launcher_actual_shell_argument_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            binary = root / "bin"
            binary.mkdir()
            capture = root / "args.json"
            stub = binary / "srun"
            stub.write_text(
                "#!"
                + sys.executable
                + '\nimport json,os,sys\njson.dump(dict(args=sys.argv[1:],export=os.environ.get("SLURM_EXPORT_ENV"),bytecode=os.environ.get("PYTHONDONTWRITEBYTECODE")),open(os.environ["CAPTURE"],"w"))\n'  # noqa: E501
            )
            stub.chmod(0o700)
            args = [
                "/package with space",
                "/bundle",
                "/prepared",
                "/campaign",
                "/scratch",
                "/results",
                "/apptainer",
                sys.executable,
            ]
            result = subprocess.run(
                ["/bin/bash", str(E.HERE / "LAUNCHER.sh"), *args],
                env={
                    **os.environ,
                    "PATH": str(binary),
                    "CAPTURE": str(capture),
                    "SLURM_EXPORT_ENV": "NONE",
                },
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            r = json.loads(capture.read_text())
            self.assertEqual(r["export"], "ALL")
            self.assertEqual(r["bytecode"], "1")
            self.assertEqual(r["args"][-10:], [sys.executable, args[0] + "/pc_job.py", *args])

    def test_launcher_missing_interpreter_fails_before_srun(self):
        result = subprocess.run(
            ["/bin/bash", str(E.HERE / "LAUNCHER.sh"), *(["/x"] * 7), "/absent/python"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unavailable", result.stderr)

    def test_launcher_relative_interpreter_fails(self):
        result = subprocess.run(
            ["/bin/bash", str(E.HERE / "LAUNCHER.sh"), *(["/x"] * 7), "python3"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)

    def test_launcher_resource_ceiling(self):
        text = (E.HERE / "LAUNCHER.sh").read_text()
        for wanted in ["--time=01:00:00", "--mem=32G", "--cpus-per-task=4", "srun --export=ALL"]:
            self.assertIn(wanted, text)

    def test_reservation_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            package = root / "p"
            package.mkdir()
            rewrite(package / "manifest.json", {})
            control.reserve(root, package, root / "campaign")
            with self.assertRaises(FileExistsError):
                control.reserve(root, package, root / "another")

    def test_unknown_dispatch_never_replayed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            record = {"dispatch": {"block-0": {"status": "unknown"}}, "jobs": {}}
            with patch("pc_control.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    control.dispatch(root, root, record, 0)
                run.assert_not_called()


class HostEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        cls.package = E.build(cls.root / "seed", testing=True)

    def case(self, fail=False):
        from contextlib import ExitStack

        root = self.root / ("failure" if fail else "complete")
        root.mkdir()
        campaign = root / "campaign"
        campaign.mkdir()
        workspace = root / "scratch"
        workspace.mkdir()
        prepared = root / "prepared"
        prepared.mkdir()
        rewrite(
            prepared / "database-identity.json", C.read(self.package / "frozen/source-index.json")
        )
        rewrite(campaign / "protected-source-before.json", {"same": True})
        native = Mock()
        native.returncode = 0
        sampler = Mock()
        sampler.returncode = 0

        def monitor(process, mon, out):
            if fail:
                raise RuntimeError("Injected monitor failure")
            rewrite(out / "job-exit.json", {"exit_code": 0})
            return 0

        def stop(mon, out):
            rewrite(out / "memory-summary.json", {"status": "complete"})

        args = [
            str(self.package),
            "/bundle",
            str(prepared),
            str(campaign),
            str(workspace),
            "/results",
            "/apptainer",
            sys.executable,
        ]
        error = None
        with ExitStack() as stack:
            entries = [
                ("sys.argv", dict(new=["pc_job.py", *args])),
                (
                    "pc_job.os.uname",
                    dict(return_value=SimpleNamespace(sysname="Linux", machine="x86_64")),
                ),
                ("pc_job.signal.signal", {}),
                ("pc_job.signal.alarm", {}),
                ("pc_job.verify", dict(side_effect=lambda p, b: C.verify(p))),
                ("pc_job.protected", dict(return_value={"same": True})),
                ("pc_resources.preflight", dict(return_value={"memory_gib": 32})),
                ("sr_host.start_sampler", dict(return_value=sampler)),
                ("sr_host.monitor", dict(side_effect=monitor)),
                ("sr_host.stop_sampler", dict(side_effect=stop)),
                ("pc_job.subprocess.Popen", dict(return_value=native)),
            ]
            for name, kw in entries:
                stack.enter_context(patch(name, **kw))
            stack.enter_context(
                patch.dict(
                    os.environ,
                    SLURM_JOB_ID="42",
                    SLURM_ARRAY_TASK_ID="0",
                    SLURM_CPUS_PER_TASK="4",
                    SLURM_EXPORT_ENV="ALL",
                    PYTHONDONTWRITEBYTECODE="1",
                )
            )
            try:
                J.main()
            except RuntimeError as exc:
                error = exc
        return campaign / "run", error, native

    def test_actual_host_entry_complete_lock(self):
        out, error, native = self.case()
        self.assertIsNone(error)
        self.assertTrue(C.read(out / "HOST-LOCK.json")["complete"])
        self.assertEqual(C.read(out / "host-exit.json")["exit_code"], 0)

    def test_actual_host_entry_failure_stops_native_and_keeps_raw(self):
        out, error, native = self.case(True)
        self.assertIsNotNone(error)
        native.terminate.assert_called_once()
        self.assertFalse(C.read(out / "HOST-LOCK.json")["complete"])
        self.assertTrue((out / "host-failure.json").exists())
