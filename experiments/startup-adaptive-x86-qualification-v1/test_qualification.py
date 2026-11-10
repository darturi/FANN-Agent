"""Controller, native-evidence, complete-budget, archive and immutable-source negatives."""

import contextlib
import copy
import io
import json
import os
import struct
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import budget
import cc_control as C
import common as M
import hardware
import host
import package as P
import proofs


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.c = M.read(M.HERE / "QUALIFICATION-CONTRACT.json")

    def dispatch(self):
        p = self.root / "package"
        p.mkdir()
        M.save(p / "manifest.json", {"files": {}})
        campaign = self.root / "campaign"
        campaign.mkdir()
        m = M.sha(p / "manifest.json")
        binding = {"campaign": str(campaign), "package_manifest_sha256": m}
        M.save(p / "submission-binding.json", binding)
        M.save(campaign.parent / ("." + M.NAME + "-reservation.json"), binding)
        r = dict(
            account="torch_pr_test",
            run=str(campaign / "run"),
            scratch="/scratch/test",
            image="/image",
            apptainer="/apptainer",
            python="/python",
            dispatch=None,
        )
        r["package_manifest_sha256"] = m
        M.save(campaign / "submission.json", r)
        return p, campaign, r

    def test_exact_native_and_guest_budget_close(self):
        self.assertEqual(
            budget.validate(self.c["limits"], self.c["phase_seconds"]), self.c["limits"]
        )
        self.assertEqual(sum(self.c["phase_seconds"].values()), 2940)
        self.assertEqual(self.c["phase_seconds"]["guest_cleanup"], 600)

    def test_no_resource_limit_relaxation(self):
        for key in (
            "wall_seconds",
            "memory_gib",
            "physical_cpus",
            "guest_seconds",
            "guest_cleanup_seconds",
        ):
            bad = copy.deepcopy(self.c["limits"])
            bad[key] += 1
            with self.assertRaises(ValueError):
                budget.validate(bad, self.c["phase_seconds"])

    def test_no_phase_cap_or_cleanup_reduction(self):
        for key in self.c["phase_seconds"]:
            bad = self.c["phase_seconds"].copy()
            bad[key] -= 1
            with self.assertRaises(ValueError):
                budget.validate(self.c["limits"], bad)

    def test_full_phase_and_tail_required(self):
        self.assertEqual(budget.admit(10, 20, 50, 20), 30)
        with self.assertRaises(TimeoutError):
            budget.admit(10.001, 20, 50, 20)
        for x in (float("nan"), float("inf")):
            with self.assertRaises(TimeoutError):
                budget.admit(x, 20, 50)

    def native_header(self):
        h = bytearray(64)
        h[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", h, 18, 62)
        return bytes(h)

    def test_genuine_x86_evidence(self):
        for vendor in ("GenuineIntel", "AuthenticAMD"):
            self.assertEqual(
                hardware.validate_x86(
                    "x86_64", "Linux", self.native_header(), "vendor_id : " + vendor, "python", {}
                ),
                vendor,
            )

    def test_uname_alone_cannot_certify_native_execution(self):
        for cpu, maps, env in [
            ("processor : 0", "python", {}),
            ("vendor_id : GenuineIntel", "qemu-x86_64", {}),
            ("vendor_id : GenuineIntel", "python", {"QEMU_CPU": "max"}),
            ("vendor_id : TCG", "python", {}),
            ("vendor_id : AuthenticAMD", "rosetta", {}),
        ]:
            with self.assertRaises(RuntimeError):
                hardware.validate_x86("x86_64", "Linux", self.native_header(), cpu, maps, env)

    def test_wrong_elf_or_platform_rejected(self):
        for machine, system, header in [
            ("arm64", "Linux", self.native_header()),
            ("x86_64", "Darwin", self.native_header()),
            ("x86_64", "Linux", b"not ELF"),
        ]:
            with self.assertRaises(RuntimeError):
                hardware.validate_x86(machine, system, header, "vendor_id : GenuineIntel", "", {})

    def test_one_new_dispatch_only(self):
        p, c, r = self.dispatch()
        with patch.object(
            C.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout="1234;torch", stderr=""),
        ) as call:
            C.dispatch(p, c, r)
            with self.assertRaises(RuntimeError):
                C.dispatch(p, c, r)
            self.assertEqual(call.call_count, 1)
        self.assertEqual(
            M.read(c / "submission.json")["dispatch"], dict(status="submitted", job_id="1234")
        )

    def test_ambiguous_dispatch_spends_new_reservation(self):
        p, c, r = self.dispatch()
        with patch.object(C.subprocess, "run", side_effect=OSError("transport lost")):
            with self.assertRaises(OSError):
                C.dispatch(p, c, r)
        self.assertEqual(M.read(c / "submission.json")["dispatch"], {"status": "unknown"})
        with patch.object(C.subprocess, "run") as call:
            with self.assertRaises(RuntimeError):
                C.dispatch(p, c, r)
            call.assert_not_called()

    def test_rejected_dispatch_cannot_retry(self):
        p, c, r = self.dispatch()
        with patch.object(
            C.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=1, stdout="", stderr="rejected"),
        ):
            with self.assertRaises(RuntimeError):
                C.dispatch(p, c, r)
        self.assertEqual(r["dispatch"]["status"], "rejected")
        with self.assertRaises(RuntimeError):
            C.dispatch(p, c, r)

    def test_bad_scheduler_identifier_is_uncertain(self):
        p, c, r = self.dispatch()
        with patch.object(
            C.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout="1234 5678", stderr=""),
        ):
            with self.assertRaises(RuntimeError):
                C.dispatch(p, c, r)
        self.assertEqual(r["dispatch"]["status"], "unknown")

    def test_binding_mutation_prevents_dispatch(self):
        p, c, r = self.dispatch()
        (p / "submission-binding.json").write_text(
            json.dumps({"campaign": str(c), "package_manifest_sha256": "0" * 64})
        )
        with patch.object(C.subprocess, "run") as call:
            with self.assertRaises(RuntimeError):
                C.dispatch(p, c, r)
            call.assert_not_called()

    def test_old_allowance_cannot_bind_new_dispatch(self):
        p, c, r = self.dispatch()
        (c.parent / ("." + M.NAME + "-reservation.json")).unlink()
        M.save(
            c.parent / ".torch-startup-exact-vector-compatibility-v1-reservation.json",
            {"campaign": str(c), "package_manifest_sha256": M.sha(p / "manifest.json")},
        )
        with patch.object(C.subprocess, "run") as call:
            with self.assertRaises(FileNotFoundError):
                C.dispatch(p, c, r)
            call.assert_not_called()

    def test_existing_binding_never_resubmits(self):
        p, c, r = self.dispatch()
        with (
            patch.object(C, "verify", return_value=self.c),
            patch.object(C.subprocess, "run") as call,
        ):
            with self.assertRaises(RuntimeError):
                C.submit(p)
            call.assert_not_called()

    def test_unbound_status_is_read_only(self):
        with patch.object(C.subprocess, "run") as call, contextlib.redirect_stdout(io.StringIO()):
            C.status(self.root)
        call.assert_not_called()

    def test_scheduler_request_uses_only_new_launcher(self):
        p, c, r = self.dispatch()
        a = C.scheduler(p, r, [])
        self.assertIn("--export=NONE", a)
        self.assertIn("--hint=nomultithread", a)
        self.assertEqual(a[-7], str(p / "LAUNCHER.sh"))
        self.assertIn("adaptive-x86", M.NAME)

    def test_live_campaign_cannot_collect(self):
        p, c, r = self.dispatch()
        r.update(job_id="1234", dispatch={"status": "submitted", "job_id": "1234"})
        with (
            patch.object(C, "bound", return_value=(c, r)),
            patch.object(
                C.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0, stdout="1234", stderr=""),
            ),
        ):
            with self.assertRaises(RuntimeError):
                C.collect(p)
        self.assertFalse(Path(str(c) + ".tar.gz").exists())

    def test_unknown_terminal_state_cannot_collect(self):
        p, c, r = self.dispatch()
        r.update(job_id="1234", dispatch={"status": "submitted", "job_id": "1234"})
        answers = [
            SimpleNamespace(returncode=0, stdout="", stderr=""),
            SimpleNamespace(returncode=0, stdout="1234|RUNNING|0:0|00:01|\n", stderr=""),
        ]
        with (
            patch.object(C, "bound", return_value=(c, r)),
            patch.object(C.subprocess, "run", side_effect=answers),
        ):
            with self.assertRaises(RuntimeError):
                C.collect(p)

    def test_manifest_inventory_and_asset_pins_are_explicit(self):
        plan = M.read(M.HERE / "ASSET-PLAN.json")
        self.assertEqual(M.sha(M.HERE / "ASSET-PLAN.json"), M.ASSET_SHA)
        self.assertEqual(self.c["source_inventory"], M.inventory(M.ROOT / self.c["source_scope"]))
        self.assertEqual(len(plan["frozen_aliases"]), 2)

    def test_preserved_case_inventories(self):
        self.assertEqual(len(proofs.expected(M.ROOT, "main")), 128)
        self.assertEqual(len(proofs.expected(M.ROOT, "a3")), 276)

    def archive(self, name, member, kind=None):
        path = self.root / (name + ".tar.gz")
        with tarfile.open(path, "w:gz") as t:
            m = tarfile.TarInfo(member)
            m.size = 2
            if kind:
                m.type = kind
                m.linkname = "/escape"
            t.addfile(m, io.BytesIO(b"{}") if not kind else None)
        Path(str(path) + ".sha256").write_text(M.sha(path) + "  " + path.name + "\n")
        return path

    def test_archive_traversal_rejected_before_writes(self):
        name = M.PREFIX + "20261101T000000Z.fixture"
        a = self.archive(name, name + "/../escape")
        with self.assertRaises(ValueError):
            P.ingest(a, self.root)
        self.assertFalse((self.root / "escape").exists())

    def test_archive_symlinks_rejected(self):
        name = M.PREFIX + "20261101T000000Z.fixture"
        a = self.archive(name, name + "/link", tarfile.SYMTYPE)
        with self.assertRaises(ValueError):
            P.ingest(a, self.root)

    def test_other_campaign_namespace_rejected(self):
        a = self.archive(
            "reviews-startup-exact-vector-compatibility-v1-20261101T000000Z.old", "foo"
        )
        with self.assertRaises(ValueError):
            P.ingest(a, self.root)

    def test_original_resource_science_stays_unchanged(self):
        source = M.ROOT / self.c["source_scope"]
        self.assertEqual(M.read(source / "RESOURCE-CONTRACT.json"), self.c["science"])
        self.assertEqual(self.c["science"]["counts"]["ANN_searches"], 0)
        self.assertEqual(self.c["science"]["counts"]["exact_searches"], 0)
        self.assertEqual(self.c["CPU"]["CPU_seconds_cap"], 120)
        self.assertEqual(self.c["CPU"]["wall_seconds_cap"], 180)

    def test_no_auto_resource_release_in_contract(self):
        self.assertFalse(self.c["CPU"]["automatic_release"])
        self.assertFalse(self.c["CPU"]["full_startup_CPU_qualification"])
        self.assertFalse(self.c["full_B2f_released"])

    def test_host_command_has_only_owned_writable_mounts(self):
        p = self.root / "package"
        p.mkdir()
        M.save(p / "ASSET-PLAN.json", {"frozen_aliases": {"trials/ref": {}}})
        a = host.command(
            p, self.root / "out", self.root / "work", Path("/image"), Path("/apptainer"), 123
        )
        binds = [a[i + 1] for i, x in enumerate(a) if x == "--bind"]
        self.assertEqual(sum(x.endswith(":rw") for x in binds), 2)
        self.assertIn("--containall", a)
        self.assertIn("--no-home", a)
        self.assertIn("QX_DEADLINE=123", a)
        self.assertTrue(any(x.endswith(":/qual:ro") for x in binds))

    def test_guest_preflight_failure_retains_cleanup_and_failed_lock(self):
        import guest

        p = self.root / "package"
        out = self.root / "out"
        work = self.root / "work"
        for d in (p, out, work):
            d.mkdir()
        M.save(p / "QUALIFICATION-CONTRACT.json", self.c)
        old_path = Path

        def path(value):
            return {"/qual": p, "/results": out, "/work": work}.get(str(value), old_path(value))

        with (
            patch.object(guest, "Path", side_effect=path),
            patch.object(guest, "verify"),
            patch("hardware.capture", side_effect=RuntimeError("native guard rejected")),
            patch.object(guest.signal, "signal"),
            patch.object(guest.signal, "alarm"),
            patch.dict(os.environ, QX_DEADLINE=str(__import__("time").monotonic() + 4000)),
        ):
            with self.assertRaises(SystemExit) as caught:
                guest.main()
        self.assertEqual(caught.exception.code, 1)
        self.assertEqual(M.read(out / "status.json")["status"], "failed")
        self.assertFalse(M.read(out / "GUEST-LOCK.json")["complete"])
        self.assertEqual(M.read(out / "guest-integrity.json")["status"], "pass")
        self.assertTrue((out / "guest-terminal.json").is_file())

    def test_guest_cleanup_failure_cannot_leave_complete_status(self):
        import guest

        p = self.root / "package"
        out = self.root / "out"
        work = self.root / "work"
        for d in (p, out, work):
            d.mkdir()
        M.save(p / "QUALIFICATION-CONTRACT.json", self.c)
        old_path = Path

        def path(value):
            return {"/qual": p, "/results": out, "/work": work}.get(str(value), old_path(value))

        with (
            patch.object(guest, "Path", side_effect=path),
            patch.object(guest, "verify", side_effect=RuntimeError("integrity failure")),
            patch.object(guest.signal, "signal"),
            patch.object(guest.signal, "alarm"),
            patch.dict(os.environ, QX_DEADLINE=str(__import__("time").monotonic() + 4000)),
        ):
            with self.assertRaises(SystemExit) as caught:
                guest.main()
        self.assertEqual(caught.exception.code, 1)
        self.assertTrue((out / "cleanup-failure.json").exists())
        self.assertFalse((out / "GUEST-LOCK.json").exists())

    def test_header_rejects_aarch64_executable_even_with_x86_uname(self):
        h = bytearray(self.native_header())
        struct.pack_into("<H", h, 18, 183)
        with self.assertRaises(RuntimeError):
            hardware.validate_x86("x86_64", "Linux", h, "vendor_id : GenuineIntel", "", {})

    def test_stale_in_memory_dispatch_cannot_override_durable_state(self):
        p, c, r = self.dispatch()
        with patch.object(
            C.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout="1234", stderr=""),
        ):
            C.dispatch(p, c, r)
        stale = r.copy()
        stale["dispatch"] = None
        with patch.object(C.subprocess, "run") as call:
            with self.assertRaises(RuntimeError):
                C.dispatch(p, c, stale)
            call.assert_not_called()

    def test_data_lock_rejects_uncovered_file(self):
        import analysis

        (self.root / "a.json").write_text("{}")
        M.save(
            self.root / "LOCK.json",
            {"complete": True, "files": {"a.json": M.sha(self.root / "a.json")}},
        )
        (self.root / "extra.json").write_text("{}")
        with self.assertRaises(ValueError):
            analysis.lock(self.root, "LOCK.json", lambda p: p.name == "LOCK.json")

    def test_data_lock_rejects_false_complete_and_changed_bytes(self):
        import analysis

        (self.root / "a.json").write_text("{}")
        M.save(
            self.root / "LOCK.json",
            {"complete": False, "files": {"a.json": M.sha(self.root / "a.json")}},
        )
        with self.assertRaises(ValueError):
            analysis.lock(self.root, "LOCK.json", lambda p: p.name == "LOCK.json")
        (self.root / "LOCK.json").unlink()
        M.save(
            self.root / "LOCK.json",
            {"complete": True, "files": {"a.json": M.sha(self.root / "a.json")}},
        )
        (self.root / "a.json").write_text("changed")
        with self.assertRaises(ValueError):
            analysis.lock(self.root, "LOCK.json", lambda p: p.name == "LOCK.json")

    def test_data_lock_rejects_traversal(self):
        import analysis

        M.save(self.root / "LOCK.json", {"complete": True, "files": {"../escape": "0" * 64}})
        with self.assertRaises(ValueError):
            analysis.lock(self.root, "LOCK.json", lambda p: p.name == "LOCK.json")

    def test_host_native_rejection_never_starts_container(self):
        import sys

        p = self.root / "package"
        out = self.root / "out"
        scratch = self.root / "scratch"
        for d in (p, out, scratch):
            d.mkdir()
        argv = ["host.py", str(p), str(out), str(scratch), "/image", "/apptainer", sys.executable]
        with (
            patch.object(host.sys, "argv", argv),
            patch.object(host, "verify", return_value=self.c),
            patch("hardware.capture", side_effect=RuntimeError("emulator rejected")),
            patch.object(host.signal, "signal"),
            patch.object(host.signal, "alarm"),
            patch.dict(os.environ, SLURM_JOB_ID="1234"),
            patch.object(host.subprocess, "Popen") as child,
        ):
            with self.assertRaises(SystemExit) as caught:
                host.main()
            child.assert_not_called()
        self.assertEqual(caught.exception.code, 1)
        self.assertEqual(M.read(out / "host-exit.json")["exit_code"], 1)
        self.assertFalse(M.read(out / "HOST-LOCK.json")["complete"])

    def test_owned_child_termination_escalates_once(self):
        import signal

        import guest

        class Child:
            pid = 123

            def __init__(self):
                self.code = None
                self.calls = 0

            def poll(self):
                return self.code

            def wait(self, timeout):
                self.calls += 1
                if self.calls == 1:
                    raise C.subprocess.TimeoutExpired("owned", timeout)
                self.code = 1
                return 1

        child = Child()
        with patch.object(guest.os, "killpg") as kill:
            guest.stop(child)
        self.assertEqual(
            kill.call_args_list,
            [unittest.mock.call(123, signal.SIGTERM), unittest.mock.call(123, signal.SIGKILL)],
        )

    def local_evidence(self):
        return (
            M.ROOT
            / "trials/torch-reviews-startup-adaptive-x86-qualification-v1/local-full-verified/run"
        )

    def test_complete_local_evidence_cannot_grant_target_qualification(self):
        result = proofs.validate(self.local_evidence(), M.ROOT, self.c, "local")
        self.assertEqual(result["status"], "complete_local_readiness_only")
        self.assertFalse(result["target_correctness_qualified"])
        self.assertFalse(result["native_CPU_budget_qualified"])

    def test_missing_cpu_repeat_rejected_by_replay(self):
        original = proofs.read

        def changed(path):
            value = original(path)
            if str(path).endswith("/cpu/cpu.json"):
                value["measurements"] = value["measurements"][:-1]
            return value

        with patch.object(proofs, "read", side_effect=changed):
            with self.assertRaises(ValueError):
                proofs.validate(self.local_evidence(), M.ROOT, self.c, "local")

    def test_forged_native_packet_does_not_match_local_proof(self):
        original = proofs.read

        def changed(path):
            value = original(path)
            if str(path).endswith("/a3-source/receipt.json"):
                value["actual_provenance"] = self.c["target_reference"]
            return value

        with patch.object(proofs, "read", side_effect=changed):
            with self.assertRaises(ValueError):
                proofs.validate(self.local_evidence(), M.ROOT, self.c, "local")

    def test_boolean_or_float_test_counts_cannot_alias_integer(self):
        original = proofs.read
        for invalid in (True, 128.0):

            def changed(path):
                value = original(path)
                if str(path).endswith("/main-source/tests.json"):
                    value["tests_run"] = invalid
                return value

            with patch.object(proofs, "read", side_effect=changed):
                with self.assertRaises(ValueError):
                    proofs.validate(self.local_evidence(), M.ROOT, self.c, "local")
