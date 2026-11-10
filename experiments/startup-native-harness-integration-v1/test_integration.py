"""Behavioral boundary, durable identity, failure recovery and host composition checks."""

import json
import os
import stat
import tarfile
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import nh_binding as B
import nh_common as C
import nh_host as H
import nh_retention as R
import nh_storage as S


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def directory(self, name):
        p = self.root / name
        p.mkdir(mode=0o700)
        return p

    def known(self):
        p = self.directory("known")
        (p / "input").write_bytes(b"immutable-reference" * 100)
        C.save(p / "manifest.json", {"files": {"input": C.sha(p / "input")}})
        return p

    def store(self):
        return R.RawStore(self.directory("raw"))

    def binding(self):
        return B.specification(
            "/input", "/stage", "/result", "/workspace", C.config()["image_sha256"]
        )


class IdentityTests(Base):
    def campaign(self, b=None):
        return B.Campaign(self.directory("local-campaign"), b or self.binding())

    def test_exclusive_campaign_preserves_existing_binding(self):
        c = self.campaign()
        before = C.sha(c.root / "binding.json")
        with self.assertRaises(FileExistsError):
            B.Campaign(c.root, self.binding())
        self.assertEqual(C.sha(c.root / "binding.json"), before)

    def test_uncertain_launch_never_repeats(self):
        c = self.campaign()
        with self.assertRaisesRegex(ValueError, "uncertain"):
            c.launch_once(lambda *a: (_ for _ in ()).throw(ValueError("uncertain")))
        with self.assertRaises(RuntimeError):
            c.launch_once(lambda *a: None)

    def test_known_launch_never_repeats(self):
        c = self.campaign()
        c.launch_once(lambda *a: 123)
        with self.assertRaises(RuntimeError):
            c.launch_once(lambda *a: 123)

    def test_mutated_persisted_binding_rejected(self):
        c = self.campaign()
        (c.root / "binding.json").write_text("{}")
        with self.assertRaises(RuntimeError):
            c.launch_once(lambda *a: 123)

    def test_old_history_tampering_rejected(self):
        c = self.campaign()
        c.launch_once(lambda *a: 123)
        (c.root / "event-00.json").write_text("{}")
        with self.assertRaises((RuntimeError, KeyError)):
            c.append("terminal")

    def test_invalid_transition_rejected(self):
        c = self.campaign()
        with self.assertRaises(RuntimeError):
            c.append("retained")

    def test_native_campaign_namespace_rejected_before_write(self):
        p = self.directory("reviews-native-21595967")
        with self.assertRaises(ValueError):
            B.Campaign(p, self.binding())
        self.assertEqual(list(p.iterdir()), [])

    def test_spent_job_injection_rejected(self):
        b = self.binding()
        b["job_id"] = "21595967"
        with self.assertRaises(ValueError):
            self.campaign(b)

    def test_boolean_allocation_cannot_alias_integer(self):
        b = self.binding()
        b["limits"]["allocations"] = True
        with self.assertRaises(ValueError):
            self.campaign(b)

    def test_changed_phase_cap_rejected(self):
        b = self.binding()
        b["phase_seconds"]["a3_source"] += 1
        with self.assertRaises(ValueError):
            self.campaign(b)

    def test_changed_source_digest_rejected(self):
        b = self.binding()
        b["integration_files"]["nh_host.py"] = "0" * 64
        with self.assertRaises(ValueError):
            self.campaign(b)

    def test_native_release_truthy_rejected(self):
        b = self.binding()
        b["native_release"] = True
        with self.assertRaises(ValueError):
            self.campaign(b)

    def test_native_submit_always_closed(self):
        with self.assertRaises(RuntimeError):
            self.campaign().submit()

    def test_slurm_environment_cannot_execute_offline_controller(self):
        with patch.dict(os.environ, SLURM_JOB_ID="21595967"), self.assertRaises(RuntimeError):
            self.campaign()

    def test_source_and_image_binding_required(self):
        with self.assertRaises(ValueError):
            B.specification("/a", "/b", "/c", "/d", "0" * 64)

    def test_bind_delimiter_injection_rejected(self):
        with self.assertRaises(ValueError):
            B.specification("/a:rw", "/b", "/c", "/d", C.config()["image_sha256"])


class StorageTests(Base):
    def observation(self):
        return {
            "path": "/job/private",
            "filesystem": "xfs",
            "device": "8:1",
            "mount_device": "8:1",
            "uid": 501,
            "mode": 0o700,
            "free_bytes": 9 * 1024**3,
            "free_inodes": 40000,
            "allocation_block_bytes": 4096,
            "ram_backed": False,
            "shared": False,
            "quota_status": "finite_verified",
            "quota_free_bytes": 9 * 1024**3,
            "quota_free_inodes": 40000,
            "synthetic": True,
        }

    def test_longest_covering_mount_selected(self):
        m = S.mount_record(
            "1 0 8:0 / / rw - xfs disk rw\n2 1 8:1 / /job rw - xfs local rw", "/job/private"
        )
        self.assertEqual(m["device"], "8:1")

    def test_mount_device_disagreement_rejected(self):
        with self.assertRaises(ValueError):
            S.admit_observation(
                self.observation(),
                "1 0 8:2 / /job rw - xfs disk rw",
                {"planned_bytes": 1, "planned_inodes": 1},
                501,
            )

    def test_ram_mount_cannot_be_admitted(self):
        o = self.observation()
        o["filesystem"] = "tmpfs"
        with self.assertRaises(ValueError):
            S.admit_observation(
                o,
                "1 0 8:1 / /job rw - tmpfs none rw",
                {"planned_bytes": 1, "planned_inodes": 1},
                501,
            )

    def test_unknown_quota_rejected(self):
        o = self.observation()
        o["quota_status"] = "unknown"
        with self.assertRaises(ValueError):
            S.admit_observation(
                o, "1 0 8:1 / /job rw - xfs disk rw", {"planned_bytes": 1, "planned_inodes": 1}, 501
            )

    def test_user_inode_quota_cannot_be_hidden_by_global_free(self):
        o = self.observation()
        o["quota_free_inodes"] = 29999
        with self.assertRaises(ValueError):
            S.admit_observation(
                o, "1 0 8:1 / /job rw - xfs disk rw", {"planned_bytes": 1, "planned_inodes": 1}, 501
            )

    def test_positive_policy_record_still_has_no_native_qualification(self):
        r = S.admit_observation(
            self.observation(),
            "1 0 8:1 / /job rw - xfs disk rw",
            {"planned_bytes": 1, "planned_inodes": 1},
            501,
        )
        self.assertFalse(r["native_release"])
        self.assertFalse(r["native_storage_qualified"])

    def test_ambiguous_mount_rejected(self):
        with self.assertRaises(ValueError):
            S.mount_record("1 0 8:1 / /job rw - xfs a rw\n2 0 8:2 / /job rw - xfs b rw", "/job/x")

    def test_escaped_mount_rejected(self):
        with self.assertRaises(ValueError):
            S.mount_record("1 0 8:1 / /job\\040x rw - xfs a rw", "/job/x")

    def test_missing_covering_mount_rejected(self):
        with self.assertRaises(ValueError):
            S.mount_record("1 0 8:1 / /other rw - xfs a rw", "/job/x")

    def test_observer_requires_site_placement_authority(self):
        p = self.directory("disk")
        with self.assertRaises(ValueError):
            S.observe_candidate(p, "", {}, {}, "1")

    def test_startup_launch_exact_boundary_and_late_rejection(self):
        self.assertEqual(S.launch_admission(10, 220)["guest_ready_deadline"], 250)
        with self.assertRaises(RuntimeError):
            S.launch_admission(10, 220.001)

    def test_ready_keeps_entire_guest_post_outer_reserve(self):
        self.assertEqual(S.ready_admission(10, 250)["guest_end"], 3250)
        with self.assertRaises(RuntimeError):
            S.ready_admission(10, 250.001)

    def test_boolean_clock_rejected(self):
        with self.assertRaises(RuntimeError):
            S.ready_admission(0, True)

    def test_binding_commands_are_non_dispatchable_and_read_only(self):
        p = self.directory("p")
        C.save(p / "ASSET-PLAN.json", {"frozen_aliases": {"trials/a": {}, "trials/b": {}}})
        r = S.draft_command(p, "/integration", "/results", "/work", "/image", "/apptainer", 3000)
        self.assertFalse(r["dispatchable"])
        self.assertFalse(r["executed"])
        self.assertEqual(sum(x["mode"] == "ro" for x in r["bindings"]), 5)

    def test_nonfinite_deadline_rejected(self):
        with self.assertRaises(ValueError):
            S.draft_command("/p", "/i", "/r", "/w", "/s", "/a", float("nan"))

    def persistent(self):
        return {
            "uid": 501,
            "mode": 0o700,
            "free_bytes": 256 * 1024**2,
            "free_inodes": 2000,
            "quota_status": "finite_verified",
            "quota_free_bytes": 128 * 1024**2,
            "quota_free_inodes": 1000,
        }

    def test_persistent_policy_exact_original_boundaries(self):
        self.assertFalse(S.admit_persistent(self.persistent(), 501)["native_release"])

    def test_persistent_global_free_cannot_hide_user_byte_quota(self):
        r = self.persistent()
        r["quota_free_bytes"] -= 1
        with self.assertRaises(ValueError):
            S.admit_persistent(r, 501)

    def test_persistent_global_free_cannot_hide_user_inode_quota(self):
        r = self.persistent()
        r["quota_free_inodes"] -= 1
        with self.assertRaises(ValueError):
            S.admit_persistent(r, 501)

    def test_persistent_unknown_quota_rejected(self):
        r = self.persistent()
        r["quota_status"] = "unknown"
        with self.assertRaises(ValueError):
            S.admit_persistent(r, 501)

    def test_persistent_boolean_capacity_rejected(self):
        r = self.persistent()
        r["quota_free_inodes"] = True
        with self.assertRaises(ValueError):
            S.admit_persistent(r, 501)


class RetentionTests(Base):
    def test_restored_regular_metadata_matches_captured_record(self):
        known, work, store, result = self.capture()
        target = self.root / "restored"
        R.restore(store, known, target, time.monotonic() + 20)
        row = next(x for x in result["entries"] if x["path"] == "mutable")
        info = (target / "mutable").stat()
        self.assertEqual(
            (stat.S_IMODE(info.st_mode), info.st_atime_ns, info.st_mtime_ns),
            (row["mode"], row["atime_ns"], row["mtime_ns"]),
        )

    def test_restored_link_metadata_never_follows_target(self):
        known, work, store, result = self.capture()
        target = self.root / "restored"
        R.restore(store, known, target, time.monotonic() + 20)
        row = next(x for x in result["entries"] if x["path"] == "link")
        info = (target / "link").lstat()
        self.assertEqual((info.st_atime_ns, info.st_mtime_ns), (row["atime_ns"], row["mtime_ns"]))

    def capture(self):
        known = self.known()
        work = self.directory("work")
        store = self.store()
        (work / "reference").write_bytes((known / "input").read_bytes())
        (work / "mutable").write_bytes(b"changed payload" * 1000)
        (work / "duplicate").write_bytes((work / "mutable").read_bytes())
        (work / "link").symlink_to("/unfollowed/outside")
        result = R.capture(work, known, store, time.monotonic() + 20)
        return known, work, store, result

    def test_complete_snapshot_restores_every_byte_and_link_without_following(self):
        known, work, store, r = self.capture()
        self.assertTrue(r["complete"])
        target = self.root / "restored"
        R.restore(store, known, target, time.monotonic() + 20)
        self.assertEqual((target / "mutable").read_bytes(), (work / "mutable").read_bytes())
        self.assertEqual((target / "reference").read_bytes(), (work / "reference").read_bytes())
        self.assertEqual(os.readlink(target / "link"), "/unfollowed/outside")

    def test_every_source_file_hashed_even_when_blobs_deduplicate(self):
        known, work, store, r = self.capture()
        self.assertEqual(len([x for x in r["entries"] if x["kind"] == "file"]), 3)
        with tarfile.open(store.root / "failure-payload.tar.gz") as t:
            self.assertEqual(len(t.getmembers()), 1)

    def test_referenced_immutable_bytes_are_not_duplicated_in_payload(self):
        known, work, store, r = self.capture()
        self.assertEqual(
            next(x for x in r["entries"] if x["path"] == "reference")["reference"], "input"
        )

    def test_changed_persistent_reference_rejected_before_restore(self):
        known, work, store, r = self.capture()
        (known / "input").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            R.restore(store, known, self.root / "new", time.monotonic() + 20)

    def test_changed_payload_rejected(self):
        known, work, store, r = self.capture()
        (store.root / "failure-payload.tar.gz").write_bytes(b"broken")
        with self.assertRaises((ValueError, tarfile.TarError, EOFError)):
            R.restore(store, known, self.root / "new", time.monotonic() + 20)

    def test_existing_restore_target_preserved(self):
        known, work, store, r = self.capture()
        target = self.directory("new")
        (target / "keep").write_text("prior")
        with self.assertRaises(FileExistsError):
            R.restore(store, known, target, time.monotonic() + 20)
        self.assertEqual((target / "keep").read_text(), "prior")

    def test_traversal_manifest_rejected(self):
        known, work, store, r = self.capture()
        r["entries"][0]["path"] = "../escape"
        (store.root / "failure-manifest.json").write_bytes(C.encoded(r))
        with self.assertRaises(ValueError):
            R.restore(store, known, self.root / "new", time.monotonic() + 20)

    def test_overlapping_roots_rejected(self):
        known = self.known()
        work = self.directory("work")
        raw = work / "raw"
        raw.mkdir(mode=0o700)
        with self.assertRaises(ValueError):
            R.capture(work, known, R.RawStore(raw), time.monotonic() + 20)

    def test_capture_deadline_marks_incomplete_and_keeps_artifacts(self):
        known = self.known()
        work = self.directory("work")
        store = self.store()
        r = R.capture(work, known, store, 0)
        self.assertFalse(r["complete"])
        self.assertTrue((store.root / "CONTROL.json").exists())

    def test_special_file_never_silently_omitted(self):
        known = self.known()
        work = self.directory("work")
        os.mkfifo(work / "pipe")
        store = self.store()
        r = R.capture(work, known, store, time.monotonic() + 20)
        self.assertFalse(r["complete"])
        self.assertTrue((work / "pipe").exists())

    def test_whole_return_cap_includes_control_reserve(self):
        store = self.store()
        with self.assertRaises(R.BudgetError):
            store.json("oversize", {"data": "x" * R.CAP})
        self.assertEqual(store.usage()[0], 2 * R.SLOT)

    def test_member_count_ceiling_is_not_extended(self):
        store = self.store()
        for i in range(254):
            (store.root / str(i)).touch()
        with self.assertRaises(R.BudgetError):
            store.json("extra", {})
        self.assertEqual(store.usage()[1], 256)

    def test_control_records_have_content_checksum(self):
        store = self.store()
        store.control({"status": "failed"})
        value = C.read(store.root / "CONTROL.json")
        self.assertEqual(value["sha256"], C.digest(value["record"]))

    def test_unsafe_raw_symlink_rejected(self):
        store = self.store()
        (store.root / "outside").symlink_to("/etc")
        with self.assertRaises(ValueError):
            store.budget()

    def test_failure_can_be_complete_without_becoming_qualified(self):
        known, work, store, r = self.capture()
        store.seal(False)
        self.assertTrue(r["complete"])
        self.assertFalse(C.read(store.root / "LOCK.json")["record"]["complete"])

    def test_persistent_archive_reference_is_verified_and_restored(self):
        known = self.known()
        work = self.directory("work")
        store = self.store()
        extra = self.root / "sealed-archive"
        extra.write_bytes(b"verified archive bytes")
        (work / "archive-copy").write_bytes(extra.read_bytes())
        extras = {"sealed-archive": {"path": str(extra), "sha256": C.sha(extra)}}
        result = R.capture(work, known, store, time.monotonic() + 20, extras=extras)
        self.assertTrue(result["complete"])
        self.assertEqual(result["entries"][0]["extra_reference"], "sealed-archive")
        R.restore(store, known, self.root / "restored", time.monotonic() + 20, extras=extras)
        self.assertEqual((self.root / "restored/archive-copy").read_bytes(), extra.read_bytes())

    def test_changed_extra_reference_never_qualifies_retention(self):
        known = self.known()
        work = self.directory("work")
        store = self.store()
        extra = self.root / "archive"
        extra.write_bytes(b"changed")
        result = R.capture(
            work,
            known,
            store,
            time.monotonic() + 20,
            extras={"archive": {"path": str(extra), "sha256": "0" * 64}},
        )
        self.assertFalse(result["complete"])


class RunnerTests(Base):
    def test_interpreter_alias_cannot_be_retargeted_even_to_identical_bytes(self):
        import shutil
        import sys

        module, runner, store = self.runner()
        alias = self.root / "python-alias"
        original = Path(sys.executable).resolve()
        alias.symlink_to(original)
        runner.python = str(alias)
        runner.python_identity = C.executable_identity(alias)
        other = self.root / "other-python"
        shutil.copy2(original, other)
        alias.unlink()
        alias.symlink_to(other)
        with self.assertRaises(RuntimeError):
            runner.execute("alias", "/not-run", [], 1, time.monotonic() + 2)

    def runner(self):
        import nh_runner

        store = self.store()
        science = store.root / "science"
        science.mkdir()
        work = self.directory("work")
        (work / "tmp").mkdir()
        runner = nh_runner.LocalRunner(
            {"science": str(science), "work": str(work)},
            store,
            str(C.ROOT / "agent/.venv/bin/python"),
        )
        return nh_runner, runner, store

    def fake(self, wait_exit=False):
        import subprocess

        class Process:
            pid = 12345
            returncode = None

            def poll(self):
                return self.returncode

            def wait(self, timeout):
                if self.returncode is not None:
                    return self.returncode
                if wait_exit:
                    self.returncode = 0
                    return 0
                raise subprocess.TimeoutExpired("fake", timeout)

            def terminate(self):
                self.returncode = -15

            def kill(self):
                self.returncode = -9

        return Process()

    def memory(self, fail=False):
        class Memory:
            def memory_info(self):
                if fail:
                    raise PermissionError("simulated live RSS loss")
                from types import SimpleNamespace

                return SimpleNamespace(rss=1024**2)

        return Memory()

    def test_timeout_stops_exact_owned_child(self):
        module, runner, store = self.runner()
        proc = self.fake()
        with (
            patch.object(module.subprocess, "Popen", return_value=proc),
            patch.object(module.psutil, "Process", return_value=self.memory()),
        ):
            with self.assertRaises(TimeoutError):
                runner.execute("timeout", "/not-run", [], 1, 0)
        self.assertEqual(proc.returncode, -15)
        self.assertIsNone(runner.child)

    def test_live_missing_RSS_fails_and_stops_child(self):
        module, runner, store = self.runner()
        proc = self.fake()
        with (
            patch.object(module.subprocess, "Popen", return_value=proc),
            patch.object(module.psutil, "Process", return_value=self.memory(True)),
        ):
            with self.assertRaises(RuntimeError):
                runner.execute("rss", "/not-run", [], 1, time.monotonic() + 2)
        self.assertEqual(proc.returncode, -15)

    def test_successful_exit_proof_is_required_for_RSS_race(self):
        module, runner, store = self.runner()
        proc = self.fake(True)
        with (
            patch.object(module.subprocess, "Popen", return_value=proc),
            patch.object(module.psutil, "Process", return_value=self.memory(True)),
        ):
            runner.execute("exit", "/not-run", [], 1, time.monotonic() + 2)
        self.assertEqual(runner.records["exit"]["exit_code"], 0)

    def test_combined_raw_budget_failure_stops_child(self):
        module, runner, store = self.runner()
        proc = self.fake()
        with (store.root / "flood").open("wb") as f:
            f.truncate(R.CAP)
        with (
            patch.object(module.subprocess, "Popen", return_value=proc),
            patch.object(module.psutil, "Process", return_value=self.memory()),
        ):
            with self.assertRaises(R.BudgetError):
                runner.execute("raw", "/not-run", [], 1, time.monotonic() + 2)
        self.assertEqual(proc.returncode, -15)

    def test_unscheduled_process_is_denied(self):
        module, runner, store = self.runner()
        with self.assertRaises(RuntimeError):
            runner.audit("subprocess.Popen", ("/bin/sh", ["/bin/sh", "-c", "forbidden"]))

    def test_network_is_denied(self):
        module, runner, store = self.runner()
        with self.assertRaises(RuntimeError):
            runner.audit("socket.connect", ())

    def test_native_runner_has_no_dispatch_path(self):
        module, runner, store = self.runner()
        with self.assertRaises(RuntimeError):
            runner.native()


class HostTests(Base):
    def scenario(self, kind="success"):
        known = self.known()
        work = self.directory("work")
        (work / "diagnostic").write_bytes(b"preserve me")
        campaign = self.directory("local-campaign")
        now = [0.0]
        context = {
            "work": str(work),
            "original": str(known),
            "inner": "/stage",
            "workspace": "/workspace",
        }

        def prepare(start, store):
            if kind == "late_launch":
                now[0] = 210.01
            if kind == "startup_reserve":
                now[0] = 209.0
            return context

        def guest(ctx, ready, store):
            if kind == "missing_ready":
                return {"status": "complete"}
            if kind == "late_ready":
                now[0] = 240.01
            if kind == "startup_reserve":
                now[0] = 239.0
            ready("wrong" if kind == "wrong_binding" else ctx["binding_sha256"], now[0])
            if kind == "repeat_ready":
                ready(ctx["binding_sha256"], now[0])
            return {"status": "failed" if kind == "guest_failure" else "complete"}

        def verify(ctx, end):
            if kind == "post_failure":
                raise RuntimeError("integrity failed")
            if kind == "post_timeout":
                now[0] += 241

        result = H.execute(
            campaign, prepare, guest, verify, clock=lambda: now[0], initial_context=context
        )
        return result, campaign

    def test_complete_host_ready_guest_post_path(self):
        r, p = self.scenario()
        self.assertEqual(r["status"], "pass")
        self.assertFalse(r["native_release"])

    def test_late_launch_fails_without_launching(self):
        r, p = self.scenario("late_launch")
        self.assertEqual(r["status"], "failed")
        self.assertIsNone(r["guest"])

    def test_late_ready_cannot_borrow_guest_or_post(self):
        r, p = self.scenario("late_ready")
        self.assertEqual(r["status"], "failed")

    def test_missing_ready_cannot_qualify(self):
        r, p = self.scenario("missing_ready")
        self.assertEqual(r["status"], "failed")

    def test_binding_mismatch_fails(self):
        r, p = self.scenario("wrong_binding")
        self.assertEqual(r["status"], "failed")

    def test_repeated_ready_fails(self):
        r, p = self.scenario("repeat_ready")
        self.assertEqual(r["status"], "failed")

    def test_guest_failure_retains_work_under_same_return_cap(self):
        r, p = self.scenario("guest_failure")
        self.assertEqual(r["status"], "failed")
        self.assertTrue(r["retention_complete"])
        self.assertLessEqual(sum(x.stat().st_size for x in p.rglob("*") if x.is_file()), R.CAP)

    def test_post_integrity_failure_still_preserves_diagnostics(self):
        r, p = self.scenario("post_failure")
        self.assertEqual(r["status"], "failed")
        self.assertTrue(r["retention_complete"])

    def test_post_timeout_never_publishes_success(self):
        with self.assertRaises(TimeoutError):
            self.scenario("post_timeout")

    def test_native_host_entry_remains_closed(self):
        with self.assertRaises(RuntimeError):
            C.closed_native()

    def test_launch_at209_can_ready_at239_without_borrowing(self):
        r, p = self.scenario("startup_reserve")
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["ready_admission"]["guest_end"], 3239)


class NativeClosureTests(Base):
    def test_native_guest_entry_fails_before_touching_mounts(self):
        import nh_guest

        with self.assertRaises(RuntimeError):
            nh_guest.main()

    def test_native_host_adapter_fails_before_spawning(self):
        import nh_native

        with self.assertRaises(RuntimeError):
            nh_native.launch({}, None, None)

    def test_native_runner_constructor_fails_before_any_filesystem_work(self):
        from nh_runner import NativeRunner

        with self.assertRaises(RuntimeError):
            NativeRunner({}, None, "/missing/python")

    def test_new_staging_adapter_retains_every_original_check(self):
        original = (C.HERE / "compat/staging.py").read_text()
        expected = original.replace(
            "from policy import FREE_BYTES, FREE_INODES",
            "from policy import FREE_BYTES, FREE_INODES\nfrom nh_common import closed_native",
            1,
        )
        expected = expected.replace(
            'raise RuntimeError("Offline prototype only; all native allowances closed")',
            "closed_native()",
            1,
        )
        self.assertEqual((C.HERE / "nh_materialize.py").read_text(), expected)

    def test_new_staging_adapter_is_still_closed_on_slurm(self):
        C.compat()
        import nh_materialize

        with patch.dict(os.environ, SLURM_JOB_ID="21595967"), self.assertRaises(RuntimeError):
            nh_materialize.stage_exact("/none", "/none", "/none", "0" * 64, "0" * 64)

    def test_existing_control_slots_are_validated_without_overwriting(self):
        store = self.store()
        before = C.sha(store.root / "CONTROL.json")
        reopened = R.RawStore.existing(store.root)
        self.assertEqual(C.sha(reopened.root / "CONTROL.json"), before)

    def test_corrupt_control_slot_cannot_be_reopened(self):
        store = self.store()
        (store.root / "CONTROL.json").write_bytes(b" " * R.SLOT)
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            R.RawStore.existing(store.root)
