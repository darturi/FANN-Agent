"""Adversarial policy, host wiring, site identity and account admission models."""

import contextlib
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import site_control as C
import site_trust as T


class PrefixCases(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self, changes=None, writable=(), linked=(), uid=501):
        changes = {} if changes is None else changes

        def metadata(p):
            name = str(p)
            info = dict(
                st_uid=0,
                st_gid=0,
                st_mode=stat.S_IFDIR | 0o755,
                st_dev=1,
                st_ino=len(name),
                st_ctime_ns=1,
            )
            if name.endswith("/scontrol") or name.endswith("/sbatch"):
                info["st_mode"] = stat.S_IFREG | 0o755
            if name == "/opt/slurm":
                info.update(st_uid=1001, st_gid=1001)
            if name == "/":
                info["st_mode"] = stat.S_IFDIR | 0o555
            info.update(changes.get(name, {}))
            return SimpleNamespace(**info)

        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch.object(T, "ROOT_BINARY", side_effect=ValueError("old root predicate"))
            )
            stack.enter_context(patch.object(T, "sha", return_value="a" * 64))
            stack.enter_context(patch.object(T.os, "getuid", return_value=uid))
            stack.enter_context(patch.object(Path, "resolve", lambda p, strict=False: p))
            stack.enter_context(patch.object(Path, "stat", metadata))
            stack.enter_context(patch.object(Path, "is_symlink", lambda p: str(p) in linked))
            stack.enter_context(patch.object(Path, "is_file", return_value=True))
            stack.enter_context(
                patch.object(
                    T.os,
                    "access",
                    side_effect=lambda p, m: str(p) in writable if m == os.W_OK else True,
                )
            )
            yield

    def reject(self, changes=None, **kw):
        with self.fixture(changes, **kw), self.assertRaises((ValueError, RuntimeError)):
            T.trusted_binary("/opt/slurm/bin/scontrol")

    def test_exact_observed_layout_passes_with_actual_owner_recorded(self):
        with self.fixture():
            p = T.trusted_binary("/opt/slurm/bin/scontrol")
            row = next(r for r in p["components"] if r["path"] == "/opt/slurm")
            self.assertEqual(row["uid"], 1001)
            self.assertEqual(row["gid"], 1001)

    def test_sbatch_uses_identical_policy(self):
        with self.fixture():
            self.assertEqual(
                T.trusted_binary("/opt/slurm/bin/sbatch")["path"], "/opt/slurm/bin/sbatch"
            )

    def test_ordinary_root_policy_is_preserved(self):
        value = {"path": "/usr/bin/scontrol", "sha256": "a" * 64}
        with patch.object(T, "ROOT_BINARY", return_value=value):
            self.assertIs(T.trusted_binary("/usr/bin/scontrol"), value)

    def test_foreign_prefix_owner_rejected(self):
        self.reject({"/opt/slurm": {"st_uid": 1002}})

    def test_foreign_prefix_group_rejected(self):
        self.reject({"/opt/slurm": {"st_gid": 1002}})

    def test_owner_caller_rejected(self):
        self.reject(uid=1001)

    def test_privileged_caller_cannot_use_exception(self):
        self.reject(uid=0)

    def test_prefix_world_write_rejected(self):
        self.reject({"/opt/slurm": {"st_mode": stat.S_IFDIR | 0o777}})

    def test_prefix_group_write_rejected(self):
        self.reject({"/opt/slurm": {"st_mode": stat.S_IFDIR | 0o775}})

    def test_other_prefix_mode_rejected(self):
        self.reject({"/opt/slurm": {"st_mode": stat.S_IFDIR | 0o750}})

    def test_nonroot_leaf_rejected(self):
        self.reject({"/opt/slurm/bin/scontrol": {"st_uid": 1001}})

    def test_nonroot_bin_rejected(self):
        self.reject({"/opt/slurm/bin": {"st_uid": 1001}})

    def test_nonroot_opt_ancestor_rejected(self):
        self.reject({"/opt": {"st_uid": 1001}})

    def test_leaf_write_access_rejected_even_with_normal_mode(self):
        self.reject(writable=("/opt/slurm/bin/scontrol",))

    def test_prefix_write_access_rejected(self):
        self.reject(writable=("/opt/slurm",))

    def test_linked_prefix_rejected(self):
        self.reject(linked=("/opt/slurm",))

    def test_unlisted_program_rejected(self):
        with self.fixture(), self.assertRaises(ValueError):
            T.trusted_binary("/opt/slurm/bin/unknown")

    def test_other_nonroot_prefix_not_whitelisted(self):
        with self.fixture(), self.assertRaises(ValueError):
            T.trusted_binary("/home/other/slurm/bin/scontrol")

    def test_hash_time_generation_race_holds(self):
        changes = {}

        def change(path):
            changes["/opt/slurm"] = {"st_ctime_ns": 2}
            return "a" * 64

        with (
            self.fixture(changes),
            patch.object(T, "sha", side_effect=change),
            self.assertRaises(RuntimeError),
        ):
            T.trusted_binary("/opt/slurm/bin/scontrol")

    def test_not_executable_holds(self):
        with (
            self.fixture(),
            patch.object(T.os, "access", return_value=False),
            self.assertRaises(ValueError),
        ):
            T.trusted_binary("/opt/slurm/bin/scontrol")

    def test_site_config_path_scoped(self):
        with self.fixture():
            T.exception_chain("/opt/slurm/etc/slurm.conf", "configuration")

    def test_other_site_config_name_rejected(self):
        with self.fixture(), self.assertRaises(ValueError):
            T.exception_chain("/opt/slurm/etc/other.conf", "configuration")

    def test_root_library_directory_scoped(self):
        with self.fixture():
            T.exception_chain("/opt/slurm/lib", "library")

    def test_nonroot_library_leaf_rejected(self):
        with self.fixture({"/opt/slurm/lib": {"st_uid": 1001}}), self.assertRaises(ValueError):
            T.exception_chain("/opt/slurm/lib", "library")


class EnvironmentCases(unittest.TestCase):
    def test_loader_and_scheduler_overrides_rejected(self):
        for key in ("SLURM_CONF_SERVER", "SLURM_CONFIG", "LD_PRELOAD", "PYTHONHOME"):
            with (
                self.subTest(key=key),
                patch.dict(os.environ, {key: "override"}, clear=True),
                self.assertRaises(ValueError),
            ):
                T.clean_environment()

    def test_only_original_environment_keys_survive(self):
        with patch.dict(
            os.environ, {"HOME": "/home/test", "UNREVIEWED": "x", "PATH": "/user/bin"}, clear=True
        ):
            env = T.clean_environment()
            self.assertNotIn("UNREVIEWED", env)
            self.assertEqual(env["PATH"], "/usr/bin:/bin:/usr/sbin:/sbin")

    def test_user_library_search_rejected(self):
        with (
            tempfile.TemporaryDirectory() as d,
            patch.dict(os.environ, {"LD_LIBRARY_PATH": d}, clear=True),
            self.assertRaises(ValueError),
        ):
            T.clean_environment()

    def test_relative_library_search_rejected(self):
        with (
            patch.dict(os.environ, {"LD_LIBRARY_PATH": "relative"}, clear=True),
            self.assertRaises(ValueError),
        ):
            T.clean_environment()

    def test_library_environment_retained_only_after_validation(self):
        with (
            patch.dict(os.environ, {"LD_LIBRARY_PATH": "/usr/lib"}, clear=True),
            patch.object(T, "trusted_data", return_value=Path("/usr/lib")) as validate,
        ):
            self.assertEqual(T.clean_environment()["LD_LIBRARY_PATH"], "/usr/lib")
            validate.assert_called_once_with(Path("/usr/lib"), "library")

    def test_allocated_host_aliases_receive_policy(self):
        import ni_control
        import ni_native
        import ni_site

        old = (
            ni_site.trusted_binary,
            ni_site.clean_environment,
            ni_control.trusted_binary,
            ni_native.trusted_binary,
        )
        try:
            T.install()
            self.assertIs(ni_site.trusted_binary, T.trusted_binary)
            self.assertIs(ni_control.trusted_binary, T.trusted_binary)
            self.assertIs(ni_native.trusted_binary, T.trusted_binary)
        finally:
            (
                ni_site.trusted_binary,
                ni_site.clean_environment,
                ni_control.trusted_binary,
                ni_native.trusted_binary,
            ) = old


class SiteIdentityCases(unittest.TestCase):
    TEXT = (
        "AuthType = auth/munge\nClusterName = torch\n"
        "SlurmctldPort = 6817\nSlurmctldHost[0] = controller\n"
    )

    def test_full_stable_configuration_retained(self):
        self.assertEqual(C.stable_configuration(self.TEXT)["ClusterName"], "torch")

    def test_missing_controller_holds(self):
        with self.assertRaises(ValueError):
            C.stable_configuration(self.TEXT.replace("SlurmctldHost[0] = controller\n", ""))

    def test_duplicate_auth_holds(self):
        with self.assertRaises(ValueError):
            C.stable_configuration(self.TEXT + "AuthType = auth/munge\n")

    def test_dynamic_response_data_ignored_as_identity(self):
        self.assertEqual(
            C.stable_configuration(self.TEXT + "NextJobId = 1\n"),
            C.stable_configuration(self.TEXT + "NextJobId = 2\n"),
        )

    def test_cross_node_inode_changes_are_observations(self):
        a = {"path": "/opt/slurm/bin/scontrol", "sha256": "a" * 64, "inode": 1, "device": 1}
        b = {**a, "inode": 2, "device": 2}
        self.assertEqual(C.stable_client(a), C.stable_client(b))

    def test_different_executable_hash_is_identity_change(self):
        a = {"path": "/opt/slurm/bin/scontrol", "sha256": "a" * 64}
        b = {**a, "sha256": "b" * 64}
        self.assertNotEqual(C.stable_client(a), C.stable_client(b))

    def test_unknown_authentication_holds(self):
        with self.assertRaises(ValueError):
            C.stable_configuration(self.TEXT.replace("auth/munge", "auth/none"))


class AccountCases(unittest.TestCase):
    def test_current_project_association_found(self):
        self.assertEqual(
            C.assoc_accounts(
                "torch|dar579|torch_pr_288_courant|cs|normal|normal\n", "torch", "dar579"
            ),
            ["torch_pr_288_courant"],
        )

    def test_other_cluster_not_used(self):
        self.assertEqual(
            C.assoc_accounts("other|dar579|torch_pr_288_courant|cs||\n", "torch", "dar579"), []
        )

    def test_other_user_not_used(self):
        self.assertEqual(
            C.assoc_accounts("torch|other|torch_pr_288_courant|cs||\n", "torch", "dar579"), []
        )

    def test_other_partition_not_used(self):
        self.assertEqual(
            C.assoc_accounts("torch|dar579|torch_pr_288_courant|gpu||\n", "torch", "dar579"), []
        )

    def test_partition_independent_association_accepted(self):
        self.assertEqual(C.assoc_accounts("torch|dar579|users|||\n", "torch", "dar579"), ["users"])

    def test_bad_field_count_holds(self):
        with self.assertRaises(ValueError):
            C.assoc_accounts("torch|dar579|users\n", "torch", "dar579")

    def test_configured_users_is_not_silently_changed(self):
        value = {
            "account": {
                "configured": "users",
                "intended_association_present": True,
                "configured_matches_intended": False,
            }
        }
        with patch.object(C, "site_check", return_value=value), self.assertRaises(RuntimeError):
            C.submission_site_check(Path("/package"))

    def test_missing_project_association_holds(self):
        with (
            patch.object(
                C,
                "site_check",
                return_value={
                    "account": {
                        "intended_association_present": False,
                        "configured_matches_intended": True,
                    }
                },
            ),
            self.assertRaises(RuntimeError),
        ):
            C.submission_site_check(Path("/package"))

    def test_fresh_intended_account_required(self):
        value = {
            "account": {"intended_association_present": True, "configured_matches_intended": True}
        }
        with patch.object(C, "site_check", return_value=value):
            self.assertIs(C.submission_site_check(Path("/package")), value)

    def test_account_query_is_readonly_and_exactly_scoped(self):
        identity = {"path": "/opt/slurm/bin/sacctmgr"}
        client = Mock()
        client.query.return_value = "PartitionName=cs"
        with (
            patch.object(T, "trusted_binary", return_value=identity),
            patch.object(C.C, "bounded_command", return_value="") as run,
        ):
            C.query_accounting(client, "dar579")
        args = run.call_args.args[0]
        self.assertIn("--readonly", args)
        self.assertIn("show", args)
        self.assertIn("user=dar579", args)
        self.assertNotIn("sbatch", args)


class AdmissionFlowCases(unittest.TestCase):
    TEXT = SiteIdentityCases.TEXT

    @contextlib.contextmanager
    def layout(self):
        import ni_control
        import ni_native
        import ni_site

        with tempfile.TemporaryDirectory() as d, contextlib.ExitStack() as stack:
            root = Path(d).resolve()
            client = Mock()
            client.probe.return_value = {
                "client": {
                    "path": "/opt/slurm/bin/scontrol",
                    "sha256": "a" * 64,
                    "device": 1,
                    "inode": 1,
                },
                "version": "slurm fixture",
                "authentication": "auth/munge",
                "configuration_sha256": "c" * 64,
            }
            client.query.return_value = self.TEXT
            old = (
                ni_site.trusted_binary,
                ni_site.clean_environment,
                ni_control.trusted_binary,
                ni_native.trusted_binary,
                ni_control.site_check,
            )
            stack.enter_context(
                patch.object(C.C, "verify", return_value={"qualification_account": C.PROJECT})
            )
            stack.enter_context(patch.object(C.C, "state_root", return_value=root))
            stack.enter_context(patch.object(C.C, "SiteClient", return_value=client))
            stack.enter_context(
                patch.object(C.pwd, "getpwuid", return_value=SimpleNamespace(pw_name="dar579"))
            )
            stack.enter_context(
                patch.dict(os.environ, {"TORCH_SLURM_ACCOUNT": "users"}, clear=True)
            )
            stack.enter_context(
                patch.object(
                    C,
                    "query_accounting",
                    return_value={
                        "associations": "torch|dar579|torch_pr_288_courant|cs||\n",
                        "partition_cs": "PartitionName=cs AllowAccounts=ALL",
                    },
                )
            )
            try:
                yield root, client
            finally:
                (
                    ni_site.trusted_binary,
                    ni_site.clean_environment,
                    ni_control.trusted_binary,
                    ni_native.trusted_binary,
                    ni_control.site_check,
                ) = old

    def test_site_query_never_creates_permission_or_dispatch(self):
        with (
            self.layout() as (root, client),
            contextlib.redirect_stdout(__import__("io").StringIO()),
        ):
            C.site_check(root / "package")
            self.assertFalse((root / "approval.json").exists())
            self.assertFalse((root / "submission.json").exists())
            self.assertEqual(len(list(root.glob("site-observation-*"))), 1)

    def test_node_local_generation_can_change_between_site_observations(self):
        with (
            self.layout() as (root, client),
            contextlib.redirect_stdout(__import__("io").StringIO()),
        ):
            C.site_check(root / "package")
            client.probe.return_value["client"]["inode"] = 2
            client.probe.return_value["client"]["device"] = 2
            C.site_check(root / "package")
            self.assertEqual(len(list(root.glob("site-observation-*"))), 2)

    def test_real_binary_hash_change_holds_without_overwriting_anchor(self):
        with (
            self.layout() as (root, client),
            contextlib.redirect_stdout(__import__("io").StringIO()),
        ):
            C.site_check(root / "package")
            client.probe.return_value["client"]["sha256"] = "b" * 64
            with self.assertRaises(RuntimeError):
                C.site_check(root / "package")
            self.assertEqual(len(list(root.glob("site-observation-*"))), 1)

    def test_auth_race_holds_before_accounting(self):
        with self.layout() as (root, client), patch.object(C, "query_accounting") as query:
            client.query.return_value = self.TEXT.replace("auth/munge", "auth/slurm")
            with self.assertRaises(RuntimeError):
                C.site_check(root / "package")
            query.assert_not_called()

    def test_configured_users_is_observed_without_mutation(self):
        with (
            self.layout() as (root, client),
            contextlib.redirect_stdout(__import__("io").StringIO()),
        ):
            row = C.site_check(root / "package")
            self.assertEqual(row["account"]["configured"], "users")
            self.assertFalse(row["account"]["configured_matches_intended"])
            self.assertTrue(row["account"]["intended_association_present"])
            self.assertEqual(os.environ["TORCH_SLURM_ACCOUNT"], "users")

    def main_fixture(self, plan, callback):
        with self.layout() as (root, client):
            package = root / "package"
            entry = package / "readiness/site_control.py"
            expected = {
                "admission_control_sha256": "a" * 64,
                "site_trust_sha256": "a" * 64,
                "site_trust_policy": T.POLICY,
                **plan,
            }
            with (
                patch.object(C, "__file__", str(entry)),
                patch.object(C.sys, "argv", [str(entry), "host", str(package)]),
                patch.object(C.C, "verify", return_value=expected),
                patch.object(C, "sha", return_value="a" * 64),
                patch.object(C.C, "main", side_effect=callback) as main,
            ):
                C.main()
                return main.call_count

    def test_allocated_host_installs_policy_before_original_entry(self):
        def check():
            import ni_native
            import ni_site

            self.assertIs(ni_native.trusted_binary, T.trusted_binary)
            self.assertIs(ni_site.trusted_binary, T.trusted_binary)

        self.assertEqual(self.main_fixture({}, check), 1)

    def test_wrong_admission_hash_holds_before_original_entry(self):
        with self.assertRaises(RuntimeError):
            self.main_fixture(
                {"admission_control_sha256": "b" * 64}, lambda: self.fail("must not dispatch")
            )

    def test_wrong_trust_module_hash_holds_before_original_entry(self):
        with self.assertRaises(RuntimeError):
            self.main_fixture(
                {"site_trust_sha256": "b" * 64}, lambda: self.fail("must not dispatch")
            )

    def test_weakened_policy_cannot_be_selected_from_plan(self):
        with self.assertRaises(RuntimeError):
            self.main_fixture({"site_trust_policy": {}}, lambda: self.fail("must not dispatch"))

    def test_accounting_binary_generation_change_holds(self):
        client = Mock()
        with (
            patch.object(
                T,
                "trusted_binary",
                side_effect=[
                    {"path": "/opt/slurm/bin/sacctmgr", "inode": 1},
                    {"path": "/opt/slurm/bin/sacctmgr", "inode": 2},
                ],
            ),
            patch.object(C.C, "bounded_command", return_value=""),
            self.assertRaises(RuntimeError),
        ):
            C.query_accounting(client, "dar579")
