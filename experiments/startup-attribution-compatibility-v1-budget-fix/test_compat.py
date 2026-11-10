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
            "--time=00:21:00",
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
    def guest_case(
        self,
        wrong_python=False,
        fail_suite=False,
        phase_fault=None,
        tests_run=128,
        late_start=False,
        cleanup_fault=False,
        publication_fault=False,
    ):
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
                        tests_run=tests_run,
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
                        exit_code=0,
                        error=None,
                        fixture_io=dict(clones=1, seeds_verified=1, reseals=10),
                        fixture_builds=dict(
                            requests=5,
                            actual_builds=1,
                            reused=4,
                            seed_verifications=6,
                            restored=True,
                        ),
                    ),
                )
                proc = Mock()
                proc.poll.return_value = 0
                proc.returncode = 0
                return proc

            actual_read = K.read
            from contextlib import contextmanager

            original_phase = G.phase_budget

            @contextmanager
            def injected_phase(name, *args, **kwargs):
                with original_phase(name, *args, **kwargs) as end:
                    if phase_fault == name:
                        raise TimeoutError("Injected phase deadline: " + name)
                    yield end

            with ExitStack() as stack:
                stack.enter_context(patch("guest.phase_budget", side_effect=injected_phase))
                if publication_fault:

                    def fail_guest_publication(path, value):
                        if Path(path).name == "status.json":
                            raise TimeoutError("guest publication sentinel")
                        return K.save(path, value)

                    stack.enter_context(patch("guest.save", side_effect=fail_guest_publication))
                if cleanup_fault:
                    stack.enter_context(
                        patch("guest.stop", side_effect=TimeoutError("termination sentinel"))
                    )
                stack.enter_context(
                    patch.dict(
                        os.environ,
                        CC_DEADLINE=str(
                            __import__("time").monotonic() + (989 if late_start else 1080)
                        ),
                    )
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

    def host_case(
        self,
        fail=False,
        startup_fault=False,
        integrity_fault=False,
        termination_fault=False,
        publication_fault=False,
    ):
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
            K.save(
                package / "COMPATIBILITY-CONTRACT.json",
                K.read(P.HERE / "COMPATIBILITY-CONTRACT.json"),
            )

            def launch(*a, **kw):
                K.save(out / "status.json", dict(status="failed" if fail else "complete"))
                proc = Mock()
                proc.wait.return_value = 1 if fail else 0
                if termination_fault:
                    proc.poll.return_value = None
                    proc.terminate.side_effect = TimeoutError("termination sentinel")
                if not termination_fault:
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
                stack.enter_context(
                    patch(
                        "host.verify",
                        side_effect=(
                            [RuntimeError("startup sentinel"), None]
                            if startup_fault
                            else [None, RuntimeError("integrity sentinel")]
                            if integrity_fault
                            else [None, None]
                        ),
                    )
                )
                stack.enter_context(
                    patch(
                        "host.sha",
                        side_effect=lambda p: K.IMAGE if str(p) == "/image" else K.sha(p),
                    )
                )
                if publication_fault:

                    def fail_host_publication(path, value):
                        if Path(path).name == "LOCK.json":
                            raise TimeoutError("host publication sentinel")
                        return K.save(path, value)

                    stack.enter_context(patch("host.save", side_effect=fail_host_publication))
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


class PreparedSeedTests(unittest.TestCase):
    def exercise(self, fault=None):
        from types import SimpleNamespace

        from fixture_io import file_sha, prepared_seed

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            calls = []

            def original(output, testing=False):
                calls.append((output, testing))
                package = output / "fake-package"
                package.mkdir(parents=True)
                K.save(
                    package / "experiment.json", dict(synthetic_fixture=fault != "native_result")
                )
                (package / "immutable").write_text("original")
                archive = package.parent / (package.name + ".tar.gz")
                archive.write_bytes(b"bounded fake archive")
                Path(str(archive) + ".sha256").write_text(
                    file_sha(archive) + "  " + archive.name + "\n"
                )
                return package

            module = SimpleNamespace(build=original)
            try:
                stages = []
                with prepared_seed(module, lambda kind, name: stages.append(name)) as stats:
                    if fault == "native_request":
                        module.build(root / "a", testing=False)
                    seed = module.build(root / "a", testing=True)
                    if fault == "mutation":
                        (seed / "immutable").write_text("changed")
                    elif fault == "archive":
                        (seed.parent / (seed.name + ".tar.gz")).write_bytes(b"changed")
                    elif fault == "checksum":
                        Path(str(seed.parent / (seed.name + ".tar.gz")) + ".sha256").write_text(
                            "changed"
                        )
                    elif fault == "exception":
                        raise KeyboardInterrupt("prepared seed sentinel")
                    elif fault == "duplicate":
                        module.build(root / "a", testing=True)
                    self.assertEqual(module.build(root / "b", testing=True), seed)
            finally:
                self.assertIs(module.build, original)
            self.assertEqual(len(calls), 1)
            self.assertEqual(stages.count("seed_build.before"), 1)
            self.assertEqual(stages.count("seed_build.after"), 1)
            self.assertEqual(stages.count("shared_seed_verify.before"), 3)
            self.assertEqual(stages.count("shared_seed_verify.after"), 3)
            self.assertEqual(
                stats,
                dict(requests=2, actual_builds=1, reused=1, seed_verifications=3, restored=True),
            )

    def test_shared_seed_calls_actual_builder_once_and_restores(self):
        self.exercise()

    def test_changed_seed_rejects(self):
        with self.assertRaisesRegex(RuntimeError, "seed/archive changed"):
            self.exercise("mutation")

    def test_changed_archive_rejects(self):
        with self.assertRaisesRegex(RuntimeError, "seed/archive changed"):
            self.exercise("archive")

    def test_changed_checksum_rejects(self):
        with self.assertRaisesRegex(RuntimeError, "checksum changed"):
            self.exercise("checksum")

    def test_native_build_request_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "offline synthetic"):
            self.exercise("native_request")

    def test_native_build_result_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "native seed"):
            self.exercise("native_result")

    def test_duplicate_target_rejected(self):
        with self.assertRaises(FileExistsError):
            self.exercise("duplicate")

    def test_baseexception_restores_builder(self):
        with self.assertRaisesRegex(KeyboardInterrupt, "prepared seed sentinel"):
            self.exercise("exception")


class FixtureFixTests(unittest.TestCase):
    def test_release_output_is_isolated_from_failed_parent(self):
        self.assertEqual(P.OUTPUT.name, K.NAME.replace("torch-", "torch-reviews-", 1))

    def test_unexpected_child_error_still_publishes_restored_guard(self):
        from types import SimpleNamespace

        import check_child

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            receipt = root / "guard.json"
            fixture = SimpleNamespace(
                runtime_fixture=lambda *a: None,
                reseal=lambda *a: None,
                E=SimpleNamespace(build=lambda *a, **kw: None),
            )
            with (
                patch(
                    "sys.argv",
                    [
                        "child",
                        "--runner",
                        str(root / "run_checks.py"),
                        "--guard-receipt",
                        str(receipt),
                    ],
                ),
                patch.dict(sys.modules, sa_fixtures=fixture),
                patch(
                    "check_child.runpy.run_path",
                    side_effect=RuntimeError("unexpected child sentinel"),
                ),
                patch(
                    "check_child.faulthandler.dump_traceback_later",
                    side_effect=AssertionError("No background watchdog allowed"),
                ),
                patch(
                    "check_child.faulthandler.cancel_dump_traceback_later",
                    side_effect=AssertionError("No background watchdog cancellation allowed"),
                ),
                patch("check_child.traceback.print_exc"),
                self.assertRaises(SystemExit) as exit_result,
            ):
                check_child.main()
            self.assertEqual(exit_result.exception.code, 1)
            guard = K.read(receipt)
            self.assertTrue(guard["connection_bindings_restored"])
            self.assertEqual(guard["error"]["message"], "unexpected child sentinel")

    def test_packaged_metadata_is_exact_and_actual_constructor_works(self):
        sys.path.insert(0, str(K.MAIN))
        import sa_fixtures as fixtures

        with tempfile.TemporaryDirectory() as d:
            package = P.build(Path(d) / "capsule", testing=True)
            bundle = package / "workspace/trials/torch-reviews-first"
            expected = K.read(package / "COMPATIBILITY-CONTRACT.json")[
                "fixture_dependency_files_sha256"
            ]
            for name, digest in expected.items():
                self.assertEqual(K.sha(bundle / name), digest)
            work = Path(d) / "work"
            fixtures.source_cell(work)
            _, backend = fixtures.frozen_backend()
            with patch("psycopg.connect", side_effect=AssertionError("Real DB forbidden")):
                value = backend(bundle, work)
            self.assertIsNone(value.conn)

    def test_missing_packaged_metadata_reproduces_actual_constructor_error(self):
        sys.path.insert(0, str(K.MAIN))
        import sa_fixtures as fixtures

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundle = root / "bundle"
            bundle.mkdir()
            work = root / "work"
            fixtures.source_cell(work)
            _, backend = fixtures.frozen_backend()
            with patch("psycopg.connect", side_effect=AssertionError("Real DB forbidden")):
                with self.assertRaisesRegex(FileNotFoundError, "inputs/local-identity.json"):
                    backend(bundle, work)

    def fixture_case(self, mode="normal"):
        from types import SimpleNamespace

        from fixture_io import MUTABLE, fixture_copies

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            seed = root / "seed"
            seed.mkdir()
            for n in MUTABLE:
                K.save(seed / n, dict(synthetic_fixture=True))
            (seed / "immutable.txt").write_text("original")
            if mode == "symlink":
                (seed / "link").symlink_to("immutable.txt")
            if mode == "native":
                (seed / "experiment.json").write_text('{"synthetic_fixture":false}')
            target = root / "target"
            target.mkdir()

            def original(folder, source, fault):
                __import__("shutil").copytree(source, folder / "package")
                package = folder / "package"
                self.assertTrue(
                    os.path.samefile(source / "immutable.txt", package / "immutable.txt")
                )
                for n in MUTABLE:
                    self.assertFalse(os.path.samefile(source / n, package / n))
                    (package / n).write_text("changed")
                if mode == "corrupt":
                    (package / "immutable.txt").write_text("bad")
                if mode == "extra":
                    (package / "unexpected").write_text("bad")
                if mode == "detached":
                    (package / "immutable.txt").unlink()
                    (package / "immutable.txt").write_text("original")
                if mode == "exception":
                    raise ValueError("Injected fixture error")
                module.reseal(package)
                return 7

            def original_reseal(package):
                from fixture_io import fingerprint

                manifest = package / "manifest.json"
                if manifest.exists():
                    manifest.unlink()
                K.save(manifest, dict(version="fixture", files=fingerprint(package)))

            module = SimpleNamespace(
                runtime_fixture=original,
                reseal=original_reseal,
                C=SimpleNamespace(VERSION="fixture", save=K.save),
            )
            copytree = __import__("shutil").copytree
            try:
                stages = []
                with fixture_copies(module, lambda kind, name: stages.append(name)) as stats:
                    result = module.runtime_fixture(target, seed, None)
            finally:
                self.assertIs(module.runtime_fixture, original)
                self.assertIs(module.reseal, original_reseal)
                self.assertIs(__import__("shutil").copytree, copytree)
            self.assertEqual(
                (result, stats["clones"], stats["seeds_verified"], stats["mutable_copies"]),
                (7, 1, 1, 4),
            )
            optimized = (target / "package/manifest.json").read_bytes()
            original_reseal(target / "package")
            self.assertEqual((target / "package/manifest.json").read_bytes(), optimized)
            self.assertEqual(stats["reseals"], 1)
            for phase in (
                "fixture_seed_hash",
                "fixture_clone",
                "fixture_reseal",
                "fixture_final_seed_hash",
            ):
                self.assertEqual(stages.count(phase + ".before"), 1)
                self.assertEqual(stages.count(phase + ".after"), 1)

    def test_fixture_reseal_rejects_unexpected_files(self):
        with self.assertRaisesRegex(RuntimeError, "inventory"):
            self.fixture_case("extra")

    def test_fixture_reseal_rejects_detached_immutable_file(self):
        with self.assertRaisesRegex(RuntimeError, "detached"):
            self.fixture_case("detached")

    def test_fixture_clone_separates_mutable_files_and_restores(self):
        self.fixture_case()

    def test_fixture_clone_detects_seed_mutation(self):
        with self.assertRaisesRegex(RuntimeError, "seed bytes"):
            self.fixture_case("corrupt")

    def test_fixture_exception_restores_copy_and_fixture_bindings(self):
        with self.assertRaisesRegex(ValueError, "Injected fixture error"):
            self.fixture_case("exception")

    def test_fixture_native_flag_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "synthetic seed"):
            self.fixture_case("native")

    def test_fixture_symlink_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            self.fixture_case("symlink")

    def test_setup_error_is_immediate_and_stops_suite(self):
        from check_child import immediate_results

        class Broken(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise RuntimeError("fixture setup sentinel")

            def test_never(self):
                raise AssertionError("Unreachable")

        class Later(unittest.TestCase):
            def test_no_continue(self):
                raise AssertionError("Must stop before later class")

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "events.jsonl"
            stream = io.StringIO()
            suite = unittest.TestSuite(
                [unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (Broken, Later)]
            )
            with immediate_results(path):
                result = unittest.TextTestRunner(stream=stream).run(suite)
            self.assertEqual(result.testsRun, 0)
            self.assertEqual(len(result.errors), 1)
            self.assertIn("RuntimeError: fixture setup sentinel", stream.getvalue())
            events = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual([r["kind"] for r in events], ["suite_start", "error", "suite_end"])


if __name__ == "__main__":
    unittest.main()


class BudgetTests(unittest.TestCase):
    def test_frozen_critical_path_and_unchanged_compute(self):
        from budget import LIMITS, validate

        limits = validate(K.read(P.HERE / "COMPATIBILITY-CONTRACT.json")["limits"])
        self.assertEqual(limits, LIMITS)
        self.assertEqual(limits["guest_seconds"], 30 + 420 + 90 + 420 + 30)
        self.assertEqual(limits["wall_seconds"], 90 + 990 + 15 + 60 + 105)
        self.assertEqual((limits["physical_cpus"], limits["memory_gib"]), (2, 4))

    def test_contract_budget_tampering_rejected(self):
        from budget import LIMITS, validate

        for key in LIMITS:
            altered = dict(LIMITS)
            altered[key] += 1
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(altered)

    def test_exact_full_phase_and_tail_boundary(self):
        from budget import admit

        self.assertEqual(admit(100, 420, 1060, tail=540), 520)
        with self.assertRaises(TimeoutError):
            admit(100.0001, 420, 1060, tail=540)

    def test_phase_never_shrinks_or_borrows_cleanup(self):
        from budget import admit

        for seconds, tail in ((420, 540), (90, 450), (420, 30), (30, 0)):
            with self.subTest(seconds=seconds, tail=tail), self.assertRaises(TimeoutError):
                admit(0, seconds, seconds + tail - 0.001, tail)

    def test_nonfinite_and_negative_times_reject(self):
        from budget import admit

        for args in ((0, 1, float("nan")), (0, 1, float("inf")), (0, 0, 10), (0, 1, 10, -1)):
            with self.subTest(args=args), self.assertRaises((ValueError, TimeoutError)):
                admit(*args)

    def test_phase_exact_deadline_fails_and_disarms(self):
        import budget

        ledger = []
        now = [10.0]
        with (
            patch("budget.time.monotonic", side_effect=lambda: now[0]),
            patch("budget.signal.alarm") as alarm,
        ):
            with self.assertRaises(TimeoutError):
                with budget.phase("source", 420, 1000, ledger):
                    now[0] = 430.0
        self.assertEqual(ledger[0]["status"], "failed")
        self.assertEqual(ledger[0]["elapsed_seconds"], 420)
        self.assertEqual(alarm.call_args.args, (0,))

    def test_phase_exception_records_failure_and_disarms(self):
        import budget

        ledger = []
        with patch("budget.signal.alarm") as alarm:
            with self.assertRaises(KeyboardInterrupt):
                with budget.phase("candidate", 90, __import__("time").monotonic() + 1000, ledger):
                    raise KeyboardInterrupt("sentinel")
        self.assertEqual(ledger[0]["error_type"], "KeyboardInterrupt")
        self.assertEqual(alarm.call_args.args, (0,))

    def test_preflight_accounts_time_before_context_entry(self):
        import budget

        ledger = []
        with patch("budget.time.monotonic", return_value=115.0), patch("budget.signal.alarm"):
            with budget.phase("preflight", 30, 1090, ledger, tail=960, began=100):
                pass
        self.assertEqual(ledger[0]["deadline_monotonic"], 130)
        self.assertEqual(ledger[0]["elapsed_seconds"], 15)

    def test_expired_preflight_cannot_start_suites(self):
        import budget

        with patch("budget.time.monotonic", return_value=130), patch("budget.signal.alarm"):
            with self.assertRaises(TimeoutError):
                with budget.phase("preflight", 30, 1090, [], tail=960, began=100):
                    self.fail("expired preflight entered")

    def test_native_command_has_no_subtracted_guest_deadline(self):
        args = H.command(Path("/p"), Path("/r"), Path("/w"), Path("/i"), Path("/a"), 1080)
        self.assertIn("CC_DEADLINE=1080", args)


class BudgetEntryTests(unittest.TestCase):
    guest_case = EntryTests.guest_case
    host_case = EntryTests.host_case

    def test_every_guest_phase_timeout_prevents_success(self):
        for phase in ("preflight", "source", "candidate", "sealed", "guest_cleanup"):
            with self.subTest(phase=phase):
                code, status = self.guest_case(phase_fault=phase)
                self.assertEqual(code, 1)
                self.assertEqual(status["status"], "failed")
                self.assertFalse(status["main_A2_launched"])
                if phase in ("preflight", "source", "candidate"):
                    self.assertNotIn("sealed", status["result"])

    def test_partial_119_case_receipt_never_qualifies(self):
        code, status = self.guest_case(tests_run=119)
        self.assertEqual(code, 1)
        self.assertNotIn("sealed", status["result"])

    def test_late_guest_start_never_shrinks_suites(self):
        code, status = self.guest_case(late_start=True)
        self.assertEqual(code, 1)
        self.assertEqual(status["result"], {})

    def test_guest_stop_failure_publishes_failure(self):
        code, status = self.guest_case(cleanup_fault=True)
        self.assertEqual(code, 1)
        self.assertEqual(status["cleanup"]["status"], "failed")

    def test_host_startup_failure_keeps_incomplete_lock(self):
        code, lock, host = self.host_case(startup_fault=True)
        self.assertEqual(code, 1)
        self.assertFalse(lock["complete"])
        self.assertEqual(host["exit_code"], 1)

    def test_host_final_integrity_failure_keeps_incomplete_lock(self):
        code, lock, host = self.host_case(integrity_fault=True)
        self.assertEqual(code, 1)
        self.assertFalse(lock["complete"])
        self.assertEqual(host["exit_code"], 1)

    def test_host_termination_failure_keeps_incomplete_lock(self):
        code, lock, host = self.host_case(termination_fault=True)
        self.assertEqual(code, 1)
        self.assertFalse(lock["complete"])
        self.assertEqual(host["exit_code"], 1)


class PublicationBudgetTests(unittest.TestCase):
    guest_case = EntryTests.guest_case
    host_case = EntryTests.host_case

    def test_guest_publication_timeout_cannot_leave_complete_status(self):
        code, status = self.guest_case(publication_fault=True)
        self.assertEqual(code, 1)
        self.assertEqual(status["status"], "failed")
        self.assertFalse(status["main_A2_launched"])

    def test_host_lock_timeout_cannot_leave_complete_lock(self):
        code, lock, host = self.host_case(publication_fault=True)
        self.assertEqual(code, 1)
        self.assertFalse(lock["complete"])
        self.assertEqual(host["exit_code"], 1)
