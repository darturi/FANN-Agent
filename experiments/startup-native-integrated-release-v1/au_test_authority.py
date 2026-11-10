"""Adversarial permission/site/capability tests; no production trust is enrolled."""

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import au_authority as A
from au_kernel import digest, parse_stat, trusted_json
from nh_common import config


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.root.chmod(0o700)
        self.now = [10.0]
        self.kernel = Mock()
        self.kernel.snapshot.return_value = {
            "uid": 501,
            "host": "isolated",
            "boot": "generation",
            "cgroup": "0::/job/99999123\n",
            "namespaces": {"pid": 1, "mnt": 2, "cgroup": 3},
            "mountinfo_sha256": "c" * 64,
            "supervisor_pid": os.getpid(),
            "supervisor_start": 99,
        }
        self.site = {
            "schema": "a3.site.v1",
            "domain": "offline-kernel-test",
            "job_id": "99999123",
            "kernel": self.kernel.snapshot(),
            "expires": 200,
            "limits": config()["limits"],
        }
        self.grant = {
            "schema": "a3.permission.v1",
            "domain": "offline-kernel-test",
            "nonce": "a" * 32,
            "job_id": "99999123",
            "binding_sha256": "b" * 64,
            "code_sha256": A.code_identity(),
            "image_sha256": config()["image_sha256"],
            "limits": config()["limits"],
            "host_started": 0,
            "work_deadline": 100,
            "cleanup_deadline": 150,
            "commands": [["/python", "/fixture"]],
            "site_sha256": digest(self.site),
        }
        self.reader = lambda path, h: copy.deepcopy(self.grant if path == "/release" else self.site)

    def authority(self):
        return A.Authority(
            A.Roots(digest(self.grant), digest(self.site), "offline-kernel-test"),
            "/release",
            "/site",
            self.root,
            self.kernel,
            lambda: self.now[0],
            self.reader,
        )

    def reject(self, change, exception=ValueError):
        change()
        with self.assertRaises(exception):
            self.authority()

    def test_valid_permission_claim_is_single_use(self):
        a = self.authority()
        lease = a.claim("b" * 64, A.code_identity())
        self.assertEqual(lease.check()["job_id"], "99999123")
        with self.assertRaises(RuntimeError):
            a.claim("b" * 64, A.code_identity())

    def test_second_authority_cannot_reuse_durable_claim(self):
        self.authority().claim("b" * 64, A.code_identity())
        with self.assertRaises(FileExistsError):
            self.authority().claim("b" * 64, A.code_identity())

    def test_existing_partial_claim_is_permanently_uncertain(self):
        (self.root / ("a" * 32 + ".claim")).write_bytes(b"partial")
        with self.assertRaises(FileExistsError):
            self.authority().claim("b" * 64, A.code_identity())

    def test_claim_binding_must_match_permission(self):
        with self.assertRaises(RuntimeError):
            self.authority().claim("d" * 64, A.code_identity())

    def test_claim_code_must_match_permission(self):
        with self.assertRaises(RuntimeError):
            self.authority().claim("b" * 64, "d" * 64)

    def test_spent_jobs_are_all_rejected(self):
        for job in A.SPENT:
            self.grant["job_id"] = self.site["job_id"] = job
            self.grant["site_sha256"] = digest(self.site)
            with self.assertRaises(ValueError):
                self.authority()

    def test_self_asserted_authority_field_is_rejected(self):
        self.reject(lambda: self.grant.update(authority="site_verified"))

    def test_missing_field_is_rejected(self):
        self.reject(lambda: self.grant.pop("nonce"))

    def test_boolean_limit_cannot_alias_original_integer(self):
        self.reject(lambda: self.grant["limits"].update(allocations=True))

    def test_changed_memory_limit_is_rejected(self):
        self.reject(lambda: self.grant["limits"].update(memory_gib=64))

    def test_changed_image_is_rejected(self):
        self.reject(lambda: self.grant.update(image_sha256="0" * 64))

    def test_mismatched_site_digest_is_rejected(self):
        self.reject(lambda: self.grant.update(site_sha256="0" * 64))

    def test_boolean_endpoint_is_rejected(self):
        self.reject(lambda: self.grant.update(work_deadline=True))

    def test_nan_endpoint_is_rejected(self):
        self.grant["work_deadline"] = float("nan")
        with self.assertRaises(ValueError):
            self.authority()

    def test_outer120_cannot_be_borrowed(self):
        self.reject(lambda: self.grant.update(cleanup_deadline=3481))

    def test_full_guest_reserve_cannot_use_postflight(self):
        self.reject(lambda: self.grant.update(work_deadline=3241, cleanup_deadline=3400))

    def test_site_authority_must_outlive_cleanup_endpoint(self):
        self.site["expires"] = 149
        self.grant["site_sha256"] = digest(self.site)
        with self.assertRaises(ValueError):
            self.authority()

    def test_duplicate_commands_are_not_extra_allowances(self):
        self.reject(lambda: self.grant["commands"].append(["/python", "/fixture"]))

    def test_relative_executable_is_rejected(self):
        self.reject(lambda: self.grant.update(commands=[["python", "/fixture"]]))

    def test_production_roots_are_not_enrolled(self):
        with self.assertRaises(RuntimeError):
            A.Roots("a" * 64, "b" * 64, "native")
        self.assertEqual(len(A.PRODUCTION_RELEASES) + len(A.PRODUCTION_SITES), 0)

    def test_native_factory_remains_closed(self):
        with self.assertRaises(RuntimeError):
            A.native_authority({"site_verified": True})

    def test_copied_capability_cannot_authorize_action(self):
        a = self.authority()
        lease = a.claim("b" * 64, A.code_identity())
        with self.assertRaises(RuntimeError):
            a.check(A.Lease(a, "b" * 64))
        self.assertEqual(lease.check()["nonce"], "a" * 32)

    def test_changed_claim_is_not_valid_authority(self):
        a = self.authority()
        lease = a.claim("b" * 64, A.code_identity())
        (self.root / ("a" * 32 + ".claim")).write_text("{}")
        with self.assertRaises(RuntimeError):
            lease.check()

    def test_wrong_command_is_never_authorized(self):
        lease = self.authority().claim("b" * 64, A.code_identity())
        with self.assertRaises(RuntimeError):
            lease.check(["/foreign"])

    def test_work_expiry_still_permits_bounded_cleanup(self):
        lease = self.authority().claim("b" * 64, A.code_identity())
        self.now[0] = 101
        with self.assertRaises(TimeoutError):
            lease.check()
        self.assertEqual(lease.check(cleanup=True)["cleanup_deadline"], 150)

    def test_cleanup_expiry_never_gets_an_extension(self):
        lease = self.authority().claim("b" * 64, A.code_identity())
        self.now[0] = 150
        with self.assertRaises((ValueError, TimeoutError)):
            lease.check(cleanup=True)

    def test_changed_kernel_generation_revokes_capability(self):
        lease = self.authority().claim("b" * 64, A.code_identity())
        self.kernel.snapshot.return_value["boot"] = "replacement"
        with self.assertRaises(RuntimeError):
            lease.check()

    def test_copied_process_cannot_use_capability(self):
        lease = self.authority().claim("b" * 64, A.code_identity())
        with patch.object(A.os, "getpid", return_value=999), self.assertRaises(RuntimeError):
            lease.check()

    def test_changed_namespace_revokes_capability(self):
        lease = self.authority().claim("b" * 64, A.code_identity())
        self.kernel.snapshot.return_value["namespaces"]["pid"] = 999
        with self.assertRaises(RuntimeError):
            lease.check()

    def test_changed_site_record_revokes_capability(self):
        lease = self.authority().claim("b" * 64, A.code_identity())
        self.site["kernel"]["boot"] = "new"
        with self.assertRaises(RuntimeError):
            lease.check()

    def test_untrusted_world_writable_anchor_parent_rejected(self):
        file = self.root / "record"
        file.write_text("{}")
        with self.assertRaises(ValueError):
            trusted_json(file, "a" * 64)

    def test_symlink_anchor_cannot_be_trusted(self):
        file = self.root / "record"
        file.symlink_to(self.root / "missing")
        with self.assertRaises((ValueError, OSError)):
            trusted_json(file, "a" * 64)

    def test_unsupported_platform_has_no_pid_signal_fallback(self):
        import au_kernel

        with (
            patch.object(au_kernel.platform, "system", return_value="Darwin"),
            self.assertRaises(RuntimeError),
        ):
            au_kernel.LinuxKernel()

    def test_proc_stat_handles_spaces_and_parentheses_in_name(self):
        fields = ["S", "10", "11", "12"] + ["0"] * 15 + ["123"] + ["0"] * 3
        r = parse_stat("20 (a tricky ) name) " + " ".join(fields))
        self.assertEqual((r["pid"], r["ppid"], r["start"]), (20, 10, 123))

    def test_truncated_stat_is_not_identity(self):
        with self.assertRaises(ValueError):
            parse_stat("20 (truncated) S 1")
