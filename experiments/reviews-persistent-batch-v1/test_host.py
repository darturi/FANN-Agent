"""Exercise the dispatch and return guards with synthetic site records only."""

import ast
import datetime
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import rb_host as host
import rb_native
import rb_site as site
from rb_seal import inventory, json_bytes, sha_bytes, sha_file

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "trials" / host.NAME / "startup-memory-gate-v1" / (host.NAME + ".tar.gz")
COMPUTE_TOOLS = {
    "scontrol": {"path": "/opt/slurm/25.05/bin/scontrol", "sha256": "a" * 64},
    "apptainer": {"path": "/share/apps/apptainer/1.5.3/bin/apptainer", "sha256": "b" * 64},
}


class HostTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.staged = self.root / "staged"
        self.staged.mkdir(mode=0o700)
        for name in host.KIT:
            shutil.copyfile(Path(__file__).parent / name, self.staged / name)
        self.home = self.root / "results"
        self.home.mkdir()
        self.scratch = self.root / "scratch"
        self.scratch.mkdir()
        for name, value in (("RESULTS", self.home), ("SCRATCH", self.scratch)):
            mocked = patch.object(site, name, value)
            mocked.start()
            self.addCleanup(mocked.stop)
        self.state = self.home / host.RESERVATION

    def test_quota_uses_explicit_site_path_outside_scheduler_path(self):
        def resolve(name, *, path):
            self.assertEqual(path, site.ENV["PATH"])
            self.assertNotEqual(name, "myquota")
            return f"/opt/slurm/bin/{name}"

        with (
            patch.object(site.shutil, "which", side_effect=resolve),
            patch.object(site, "binary", side_effect=lambda p: {"path": str(p)}),
            patch.object(site.sys, "executable", "/usr/bin/python3.12"),
            patch.object(site.sys, "version_info", (3, 12)),
        ):
            tools = site.association_tools()

        self.assertEqual(tools["myquota"]["path"], "/share/apps/local/bin/myquota")
        self.assertIn("/share/apps/local/bin", site.QUOTA_ENV["PATH"].split(":"))
        self.assertEqual(site.QUOTA_ENV["USER"], site.USER)
        self.assertEqual(site.QUOTA_ENV["LOGNAME"], site.USER)
        self.assertNotIn("USER", site.ENV)
        self.assertNotIn("/share/apps/local/bin", site.ENV["PATH"].split(":"))

    def test_site_admits_bare_torch_login_to_remaining_checks(self):
        with (
            patch.object(site.platform, "system", return_value="Linux"),
            patch.object(site.platform, "machine", return_value="x86_64"),
            patch.object(site.platform, "node", return_value="torch-login") as hostname,
            patch.object(site.pwd, "getpwuid", return_value=SimpleNamespace(pw_name=site.USER)),
            patch.dict(site.os.environ, {"SLURM_JOB_ID": ""}),
            patch.object(site, "association_tools", side_effect=RuntimeError("next site check")),
        ):
            with self.assertRaisesRegex(RuntimeError, "next site check"):
                site.site_check()
            with patch.dict(site.os.environ, {"SLURM_JOB_ID": "123456"}):
                with self.assertRaisesRegex(ValueError, "outside a job"):
                    site.site_check()
            hostname.return_value = "gr106"
            with self.assertRaisesRegex(ValueError, "outside a job"):
                site.site_check()

    def test_prepared_identity_accepts_only_the_two_reviewed_byte_encodings(self):
        original = (
            ROOT
            / "trials/torch-reviews-results/reviews-size-sweep-20261019T021505Z.jbrSqB"
            / "preparation/size-247286/database-identity.json"
        )
        frozen = json_bytes(site.read_json(original))
        self.assertEqual(sha_file(original), site.PREPARED_INDEX_SHA)
        self.assertEqual(sha_bytes(frozen), site.INDEX_SHA)
        bundle = self.root / "bundle"
        files = {}
        for name in (
            "images/runtime.sif",
            "inputs/reviews.parquet",
            "inputs/local-identity.json",
            "experiment.json",
        ):
            path = bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
            files[name] = sha_file(path)
        manifest = bundle / "manifest.json"
        manifest.write_bytes(json_bytes({"files": files}))
        prepared = self.root / "prepared"
        (prepared / "base").mkdir(parents=True)
        (prepared / "base/backup_manifest").touch()
        (prepared / "admin.pgpass").touch()
        (prepared / "READY.json").write_bytes(
            json_bytes(
                {
                    "architecture": "x86_64",
                    "image_sha256": files["images/runtime.sif"],
                    "index_identity": site.GRAPH,
                }
            )
        )
        identity = prepared / "database-identity.json"
        with (
            patch.object(site, "BUNDLE", bundle),
            patch.object(site, "PREPARED", prepared),
            patch.object(site, "BASE_SHA", sha_file(manifest)),
            patch.object(site, "IMAGE_SHA", files["images/runtime.sif"]),
        ):
            for raw in (original.read_bytes(), frozen):
                identity.write_bytes(raw)
                self.assertEqual(site.retained_inputs()["prepared_index_sha256"], sha_bytes(raw))
            identity.write_bytes(frozen + b"\n")
            with self.assertRaisesRegex(ValueError, "Prepared database identity differs"):
                site.retained_inputs()

    def test_stage_exact_archive_and_reject_extra_attempt(self):
        result = host.stage(self.staged, ARCHIVE)
        self.assertEqual(result["status"], "staged_held")
        self.assertEqual(result["host_kit_sha256"], host.kit_digest(self.staged))
        with self.assertRaisesRegex(ValueError, "already exists"):
            host.stage(self.staged, ARCHIVE)
        self.assertFalse(self.state.exists())

    def release_files(self):
        receipt = {
            "schema": "reviews-persistent-batch.torch-site.v1",
            "checked_utc": site.now().isoformat(),
            "host": "torch-login-a-0",
            "uid": host.os.getuid(),
            "cluster": {"ClusterName": "torch"},
            "partition": {"PartitionName": site.PARTITION},
            "account": site.ACCOUNT,
            "tools": {},
            "inputs": {"mock": "inputs"},
            "allocations": 0,
            "searches": 0,
        }
        preflight = self.root / "preflight.json"
        preflight.write_bytes(
            json_bytes(
                {
                    "status": "scheduler_test_passed_held",
                    "stage": str(self.staged),
                    "site": receipt,
                    "package_manifest_sha256": host.MANIFEST,
                    "host_kit_sha256": host.kit_digest(self.staged),
                }
            )
        )
        approval = {
            "schema": host.SCHEMA,
            "preflight_sha256": sha_file(preflight),
            "host_kit_sha256": host.kit_digest(self.staged),
            "package_manifest_sha256": host.MANIFEST,
            "candidate": host.CANDIDATE,
            "uid": host.os.getuid(),
            "account": site.ACCOUNT,
            "partition": site.PARTITION,
            "allocations": 1,
            "no_retry": True,
            "valid_until_utc": (site.now() + datetime.timedelta(minutes=20)).isoformat(),
        }
        release = self.root / "approval.json"
        release.write_bytes(json_bytes(approval))
        return receipt, (release, sha_file(release), preflight, sha_file(preflight))

    def test_site_identity_change_rejects_release(self):
        receipt, args = self.release_files()
        with patch.object(site, "site_check", return_value={**receipt, "host": "torch-login-b-2"}):
            with self.assertRaisesRegex(ValueError, "preflight identity changed"):
                host.release(*args, self.staged)
        with self.assertRaisesRegex(ValueError, "Digest differs"):
            host.release(args[0], "0" * 64, *args[2:], self.staged)
        preflight = site.read_json(args[2])
        preflight["host_kit_sha256"] = "0" * 64
        args[2].write_bytes(json_bytes(preflight))
        with self.assertRaisesRegex(ValueError, "exact staged scheduler dry-run receipt"):
            host.release(*args[:3], sha_file(args[2]), self.staged)
        self.assertFalse(self.state.exists())

    def test_scheduler_test_requests_no_allocation_and_keeps_no_reservation(self):
        host.stage(self.staged, ARCHIVE)
        receipt, _ = self.release_files()
        with (
            patch.object(site, "site_check", return_value=receipt),
            patch.object(host, "scheduler", return_value="/site/tool"),
            patch.object(
                host.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, "scheduler dry-run", ""),
            ) as process,
        ):
            result = host.scheduler_test(self.staged)
            self.assertEqual(result["status"], "scheduler_test_passed_held")
            self.assertIn("--test-only", process.call_args.args[0])
            self.assertFalse(self.state.exists())

    def test_dispatch_reserves_before_mock_submit_and_refuses_second_call(self):
        host.stage(self.staged, ARCHIVE)
        receipt, args = self.release_files()
        previous = self.home / (host.NAME + "-reservation")
        previous.mkdir()
        spent = previous / "job.json"
        spent.write_bytes(json_bytes({"job_id": "22372968", "no_retry": True}))
        spent_digest = sha_file(spent)

        def mock_sbatch(argv, **kwargs):
            self.assertTrue((self.state / "reservation.json").is_file())
            self.assertEqual(argv[0], "/site/sbatch")
            self.assertIn("--no-requeue", argv)
            self.assertIn("--mem=32G", argv)
            self.assertIn("--time=02:00:00", argv)
            self.assertIn("--cpus-per-task=4", argv)
            self.assertNotIn("--array", " ".join(argv))
            self.assertIn("--cpu-bind=verbose", kwargs["input"])
            self.assertEqual(kwargs["env"], site.ENV)
            return subprocess.CompletedProcess(argv, 0, "123456;torch\n", "")

        with (
            patch.object(site, "site_check", return_value=receipt),
            patch.object(host, "scheduler", side_effect=lambda _checked, name: "/site/" + name),
            patch.object(host.subprocess, "run", side_effect=mock_sbatch) as process,
        ):
            result = host.submit(self.staged, *args)
            self.assertEqual(result["job_id"], "123456")
            with self.assertRaisesRegex(ValueError, "already reserved"):
                host.submit(self.staged, *args)
            process.assert_called_once()
        self.assertEqual(list(previous.iterdir()), [spent])
        self.assertEqual(sha_file(spent), spent_digest)

    def test_timeout_closes_attempt_with_no_job_admission(self):
        host.stage(self.staged, ARCHIVE)
        receipt, args = self.release_files()
        with (
            patch.object(site, "site_check", return_value=receipt),
            patch.object(host, "scheduler", return_value="/site/tool"),
            patch.object(host.subprocess, "run", side_effect=subprocess.TimeoutExpired("mock", 30)),
        ):
            with self.assertRaises(subprocess.TimeoutExpired):
                host.submit(self.staged, *args)
        self.assertEqual(
            site.read_json(self.state / "dispatch-response.json")["status"], "uncertain"
        )
        self.assertFalse((self.state / "job.json").exists())
        with self.assertRaisesRegex(ValueError, "already reserved"):
            host.submit(self.staged, *args)

    def test_scheduler_and_guest_are_bound_to_same_job(self):
        job = "123456"
        binding = host.expected_job(job, 123)
        binding.update(NumCPUs="8", MinMemoryNode="32G", NodeList="gr106", BatchHost="gr106")
        host.verify_binding(binding, job, 123)
        with self.assertRaisesRegex(ValueError, "allocation differs"):
            host.verify_binding({**binding, "CPUs/Task": "8"}, job, 123)
        for login in ("torch-login", "torch-login-b-1"):
            with self.assertRaisesRegex(ValueError, "allocation differs"):
                host.verify_binding({**binding, "NodeList": login, "BatchHost": login}, job, 123)
        apptainer = COMPUTE_TOOLS["apptainer"]["path"]
        cmd = host.guest_command(self.staged, self.root, self.root / "work", job, apptainer, "sha")
        self.assertEqual(cmd[0], apptainer)
        self.assertIn(f"{self.staged}/package:/patch:ro", cmd)
        self.assertIn(f"{site.PREPARED}:/prepared:ro", cmd)
        self.assertIn("SLURM_JOB_ID=123456", cmd)
        self.assertEqual(cmd[-4:], ["--admission", "/admission.json", "--admission-sha256", "sha"])

    def test_compute_tool_rejects_redirects_and_writable_install_paths(self):
        observed = COMPUTE_TOOLS["scontrol"]
        with (
            patch.object(site, "binary", return_value=observed) as binary,
            patch.object(Path, "stat", return_value=SimpleNamespace(st_mode=0o755, st_uid=0)),
            patch.object(site.os, "getuid", return_value=3213387),
            patch.object(site.os, "access", return_value=False) as access,
        ):
            self.assertEqual(site.compute_tool("scontrol"), observed)
            binary.assert_called_once_with(Path("/opt/slurm/bin/scontrol"))
            access.side_effect = lambda path, _mode: path == Path("/opt/slurm")
            with self.assertRaisesRegex(ValueError, "Writable compute tool path"):
                site.compute_tool("scontrol")
            access.side_effect = None
            binary.return_value = {**observed, "path": "/usr/bin/scontrol"}
            self.assertEqual(site.compute_tool("scontrol"), binary.return_value)
            binary.return_value = {**observed, "path": "/tmp/scontrol"}
            with self.assertRaisesRegex(ValueError, "Unexpected compute installation"):
                site.compute_tool("scontrol")

    def test_compute_binds_live_job_and_launches_with_independent_tool_fingerprints(self):
        host.stage(self.staged, ARCHIVE)
        self.state.mkdir(mode=0o700)
        run = self.scratch / "attempt"
        run.mkdir(mode=0o700)
        job = "123456"
        uid = host.os.getuid()
        login_tools = {
            name: {"path": str(site.COMPUTE_TOOL_PATHS[name]), "sha256": "c" * 64}
            for name in COMPUTE_TOOLS
        }
        login_tools["apptainer"]["path"] = COMPUTE_TOOLS["apptainer"]["path"]
        checked = {"uid": uid, "tools": login_tools, "inputs": {"mock": "inputs"}}
        record = {
            "site": checked,
            "stage": str(self.staged),
            "run": str(run),
            "host_kit_sha256": host.kit_digest(self.staged),
            "package_manifest_sha256": host.MANIFEST,
            "candidate": host.CANDIDATE,
        }
        reservation = self.state / "reservation.json"
        reservation.write_bytes(json_bytes(record))
        (self.state / "job.json").write_bytes(
            json_bytes({"job_id": job, "reservation_sha256": sha_file(reservation)})
        )
        binding = host.expected_job(job, uid)
        binding.update(NumCPUs="4", MinMemoryNode="32G", NodeList="cs610", BatchHost="cs610")
        runner_path = ROOT / "trials/torch-reviews-first/runner.py"
        self.assertEqual(sha_file(runner_path), rb_native.RUNNER)
        # Exercise the real pinned ownership check without importing the database driver.
        connection = next(
            node
            for node in ast.parse(runner_path.read_bytes()).body
            if isinstance(node, ast.FunctionDef) and node.name == "job_connection"
        )
        frozen = {"Path": Path, "os": host.os, "make_conninfo": dict}
        exec(
            compile(ast.Module(body=[connection], type_ignores=[]), str(runner_path), "exec"),
            frozen,
        )

        def launch(argv, **_kwargs):
            self.assertEqual(argv[0], COMPUTE_TOOLS["apptainer"]["path"])
            self.assertEqual(site.read_json(run / "admission.json"), host.admission_for(job, uid))
            work = run / "work"
            self.assertIn(f"{work}:/run:rw", argv)
            self.assertEqual((work / ".torch-owned").read_bytes(), b"123456\n")
            self.assertEqual(frozen["job_connection"](work, admin=True)["user"], "torch_owner")
            guest = run / "result/guest"
            guest.mkdir()
            (guest / "guest-lock.json").write_bytes(json_bytes({"mock": "lock"}))
            (guest / "guest-exit.json").write_bytes(json_bytes({"exit_code": 0, "job_id": job}))
            return SimpleNamespace(wait=lambda timeout: 0, poll=lambda: 0)

        with (
            patch.dict(host.os.environ, {"SLURM_JOB_ID": job, "SLURM_STEP_ID": "0"}, clear=True),
            patch.object(
                host.os,
                "uname",
                return_value=SimpleNamespace(sysname="Linux", machine="x86_64", nodename="cs610"),
            ),
            patch.object(site, "compute_tool", side_effect=COMPUTE_TOOLS.__getitem__),
            patch.object(site, "retained_inputs", return_value=checked["inputs"]),
            patch.object(
                site,
                "command",
                return_value=" ".join(f"{key}={value}" for key, value in binding.items()),
            ) as query,
            patch.object(
                host, "scheduler", side_effect=AssertionError("login tool used on compute")
            ),
            patch.object(host.signal, "signal"),
            patch.object(host.subprocess, "Popen", side_effect=launch) as process,
        ):
            self.assertEqual(host.compute(self.staged, self.state), 0)
            process.assert_called_once()
            query.assert_called_once_with(
                [
                    COMPUTE_TOOLS["scontrol"]["path"],
                    "--local",
                    "--oneliner",
                    "show",
                    "job",
                    job,
                ]
            )
        start = site.read_json(run / "result/host-start.json")
        self.assertEqual(start["compute_tools"], COMPUTE_TOOLS)
        self.assertTrue(site.read_json(run / "result/host-exit.json")["apptainer_unchanged"])

    def test_scheduler_client_change_during_query_is_rejected(self):
        observed = COMPUTE_TOOLS["scontrol"]
        with (
            patch.object(
                site, "compute_tool", side_effect=[observed, {**observed, "sha256": "d" * 64}]
            ),
            patch.object(site, "command", return_value=""),
            self.assertRaisesRegex(ValueError, "changed during the job query"),
        ):
            host.bound_job("123456", {"uid": 123})

    def test_locked_host_return_and_scheduler_failures(self):
        job = "123456"
        uid = 123
        folder = self.root / "return"
        folder.mkdir()
        (folder / "guest").mkdir()

        def put(name, payload):
            (folder / name).write_bytes(json_bytes(payload))
            return sha_file(folder / name)

        binding = host.expected_job(job, uid)
        binding.update(NumCPUs="4", MinMemoryNode="32G", NodeList="gr106", BatchHost="gr106")
        top = [
            job,
            host.JOB_NAME,
            site.USER,
            site.ACCOUNT,
            site.PARTITION,
            "COMPLETED",
            "0:0",
            "0:0",
            "4",
            "1",
            "32Gn",
            "6500",
            "120",
            "0",
        ]
        step = top.copy()
        step[0] = job + ".batch"
        lines = ["|".join(top), "|".join(step)]
        step[0] = job + ".0"
        lines.append("|".join(step))
        raw = "\n".join(lines)
        with self.assertRaisesRegex(ValueError, "bounded completed"):
            host.terminal_rows(raw.replace("COMPLETED", "FAILED"), job)
        with self.assertRaisesRegex(ValueError, "unexpected scheduler steps"):
            host.terminal_rows("\n".join(lines[:2]), job)
        (folder / "sacct.txt").write_text(raw)
        reservation = put(
            "reservation.json",
            {
                "candidate": host.CANDIDATE,
                "package_manifest_sha256": host.MANIFEST,
                "allocations_reserved": 1,
                "no_retry": True,
                "site": {"inputs": {}, "uid": uid},
            },
        )
        put("job.json", {"job_id": job, "reservation_sha256": reservation})
        put(
            "dispatch-response.json", {"status": "response_received", "exit_code": 0, "stdout": job}
        )
        lock = put("guest/guest-lock.json", {"test": "guest lock fixture"})
        admission = host.admission_for(job, uid)
        put("guest/runtime.json", {"job": admission})
        put(
            "host-start.json",
            {
                "job": binding,
                "compute_tools": COMPUTE_TOOLS,
                "reservation_sha256": reservation,
                "inputs": {},
                "admission_sha256": sha_bytes(json_bytes(admission)),
            },
        )
        put(
            "host-exit.json",
            {
                "job_id": job,
                "exit_code": 0,
                "inputs_unchanged": True,
                "postmaster_stopped": True,
                "apptainer_unchanged": True,
                "guest_lock_sha256": lock,
            },
        )
        pin = put(host.LOCK, {"job_id": job, "files": inventory(folder)})
        self.assertEqual(
            host.review_host(folder, pin)["status"], "host_verified_guest_replay_required"
        )
        put("guest/runtime.json", {"job": host.admission_for("654321", uid)})
        with self.assertRaisesRegex(ValueError, "contents differ"):
            host.review_host(folder, pin)
