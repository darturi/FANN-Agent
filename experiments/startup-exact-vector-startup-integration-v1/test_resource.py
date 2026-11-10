"""Actual packed startup entry, authentic proof gates and independent resource replay."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import ev_startup
import experiment as E
import pc_common as C
from test_fixtures import complete_return, relock, reseal, rewrite, runtime_fixture
from test_memory import memory_case


class ResourceRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.seed = E.build(Path(cls.tmp.name) / "seed", testing=True)

    def fixture(self, fault=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return runtime_fixture(Path(tmp.name), self.seed, fault)

    def failed(self, fault):
        result = self.fixture(fault)
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["status"]["status"], "failed")
        self.assertEqual(result["status"]["backend_searches"], 0)
        self.assertEqual(result["status"]["search_sql"], 0)
        self.assertTrue(all(c.closed for c in result["opened"]))
        self.assertEqual(set(result["stopped"]), set(C.CELLS))
        self.assertFalse(C.read(result["out"] / "LOCK.json")["complete"])
        ev_startup.assert_restored()
        if fault.startswith("stream_") or fault in ("snapshot_identity", "eligibility"):
            # These failures must reach the intended producer/constructor/identity
            # boundary; a missing preflight dependency cannot make them pass.
            self.assertTrue((result["out"] / "identity-stream.json").exists())
        return result

    def test_complete_actual_runtime_and_retained_packed_aliases(self):
        r = self.fixture()
        self.assertIsNone(
            r["error"],
            C.read(r["out"] / "failure.json") if (r["out"] / "failure.json").exists() else "",
        )
        self.assertEqual(r["status"]["full_scans"], {"snapshot": 1, "data": 4})
        self.assertEqual(r["status"]["reader_connections"], 10)
        self.assertEqual(r["status"]["maximum_live_readers"], 6)
        immutable = Path("frozen/inputs/development-evidence.json")
        self.assertEqual(
            (r["package"] / immutable).stat().st_ino, (self.seed / immutable).stat().st_ino
        )
        self.assertEqual((r["package"] / immutable).stat().st_mode & 0o222, 0)
        self.assertNotEqual(
            (r["package"] / "eligibility.json").stat().st_ino,
            (self.seed / "eligibility.json").stat().st_ino,
        )
        self.assertEqual(C.read(r["out"] / "admitted-requests.json"), dict(count=200, executed=0))
        retained = C.read(r["out"] / "ev-retention.json")
        self.assertFalse(retained["root_released"])
        self.assertEqual([row["live_readers"] for row in retained["records"]], [2, 2, 0])
        self.assertEqual(len({row["snapshot_token"] for row in retained["records"]}), 1)
        self.assertTrue(
            all(row["packed_vectors"] == row["rows"] == 40 for row in retained["records"])
        )
        self.assertTrue(all(c.closed for c in r["opened"]))
        self.assertFalse(any("<=>" in text for c in r["opened"] for text, _ in c.executed))
        phases = C.lines(r["out"] / "phases.jsonl")
        for e in (0, 1):
            hold = next(x for x in phases if x["phase"] == f"epoch{e}_hold")
            following = next(x for x in phases if x["time_ns"] > hold["time_ns"])
            self.assertGreaterEqual(following["time_ns"] - hold["time_ns"], 5 * 10**9)

    def test_actual_eligibility_failure_rolls_back_and_cleans(self):
        self.failed("eligibility")

    def test_actual_identity_failure_restores(self):
        r = self.failed("snapshot_identity")
        self.assertTrue(C.read(r["out"] / "identity-stream.json")["binding_restored"])

    def test_actual_constructor_rejection_restores(self):
        self.failed("stream_constructor")

    def test_actual_framing_error_restores(self):
        r = self.failed("stream_hash")
        self.assertTrue(C.read(r["out"] / "identity-stream.json")["helper_binding_restored"])

    def test_actual_framing_deadline_restores(self):
        self.failed("stream_deadline")

    def test_actual_framing_keyboard_interrupt_restores(self):
        self.failed("stream_interrupt")

    def test_actual_framing_byte_cap_restores(self):
        self.failed("stream_cap")

    def test_actual_preflight_failure_before_copy_or_SQL(self):
        r = self.failed("preflight")
        self.assertFalse(r["opened"])
        self.assertFalse((r["out"] / "copies.json").exists())

    def test_actual_sampler_failure_before_reader_or_copy(self):
        r = self.failed("sampler")
        self.assertFalse(r["opened"])

    def test_actual_second_server_failure_stops_both(self):
        self.failed("second_server")

    def test_actual_cleanup_failure_cannot_qualify(self):
        self.failed("cleanup")

    def test_native_entry_rejects_synthetic_before_bootstrap(self):
        import pc_runtime

        mapping = {"/patch": self.seed}
        with (
            patch("pc_runtime.Path", side_effect=lambda p: mapping.get(str(p), Path(p))),
            patch(
                "pc_runtime.os.uname",
                return_value=SimpleNamespace(sysname="Linux", machine="x86_64"),
            ),
            patch.dict(os.environ, SLURM_JOB_ID="fake", SLURM_CPUS_PER_TASK="4"),
            patch("sys.argv", ["pc_runtime.py", "--block", "0"]),
            patch("pc_runtime.bootstrap") as boot,
        ):
            with self.assertRaises(RuntimeError):
                pc_runtime.main()
            boot.assert_not_called()

    def test_authentic_native_proofs_are_accepted(self):
        release = C.validate_native_proofs(self.seed)
        self.assertEqual(release["scope"]["memory_gib"], 32)
        self.assertEqual(release["scope"]["data_verification_scans"], 4)
        self.assertFalse(release["full_B2f_released"])

    def test_unchanged_native_spec_accepts_authentic_proofs_metadata_only(self):
        import exact_vector
        import integration

        with patch.object(exact_vector, "PACKAGE", E.REFERENCE):
            spec = integration.native_spec(self.seed.resolve())
        self.assertEqual(spec.rows, 247286)
        self.assertEqual(
            spec.identity, C.read(E.REFERENCE / "experiment.json")["snapshot_identity"]
        )

    def test_stale_native_receipt_fails_after_reseal(self):
        r = self.fixture()
        path = r["package"] / "integration-sealed.json"
        value = C.read(path)
        value["tests_run"] = 55
        rewrite(path, value)
        reseal(r["package"])
        with self.assertRaises(ValueError):
            C.verify(r["package"])

    def test_relaxed_release_margin_fails_after_reseal(self):
        r = self.fixture()
        path = r["package"] / "NATIVE-RELEASE.json"
        value = C.read(path)
        value["scope"]["reserve_bytes"] -= 1
        rewrite(path, value)
        reseal(r["package"])
        with self.assertRaises(ValueError):
            C.verify(r["package"])

    def test_wrong_binding_rejected(self):
        r = self.fixture()
        C.save(
            r["package"] / "submission-binding.json",
            dict(
                campaign="/tmp/not-authorized",
                package_manifest_sha256=C.sha(r["package"] / "manifest.json"),
            ),
        )
        with self.assertRaises(ValueError):
            C.verify(r["package"])


class ResourceReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.seed = E.build(Path(cls.tmp.name) / "seed", testing=True)

    def fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        actual = runtime_fixture(root / "acquisition", self.seed)
        self.assertIsNone(actual["error"])
        return root, *complete_return(root, actual)

    def test_complete_metadata_only_resource_replay(self):
        root, campaign, package = self.fixture()
        result = E.analyze(campaign, root / "analysis", package)
        self.assertEqual(result["outcome"], "startup_resource_margin_pass_scoped")
        self.assertFalse(result["calibration_qualified"])
        self.assertFalse(result["memory"]["workload_memory_qualified"])
        self.assertTrue((root / "analysis/A3-startup-proof.json").exists())

    def test_retention_tamper_fails_even_when_relocked(self):
        root, campaign, package = self.fixture()
        path = campaign / "run/ev-retention.json"
        value = C.read(path)
        value["records"][-1]["shared_aliases"] = 0
        rewrite(path, value)
        relock(campaign / "run")
        with self.assertRaises(ValueError):
            E.analyze(campaign, root / "analysis", package)

    def test_exact_provenance_tamper_fails_even_when_relocked(self):
        root, campaign, package = self.fixture()
        path = campaign / "run/ev-runtime-preflight.json"
        value = C.read(path)
        value["actual_provenance"]["python"] = "3.12.7"
        rewrite(path, value)
        relock(campaign / "run")
        with self.assertRaises(ValueError):
            E.analyze(campaign, root / "analysis", package)

    def test_host_runtime_budget_overrun_rejected(self):
        root, campaign, package = self.fixture()
        path = campaign / "run/ev-host-timing.json"
        value = C.read(path)
        value["post_started"] = value["runtime_deadline"] + 0.01
        rewrite(path, value)
        relock(campaign / "run")
        with self.assertRaises(ValueError):
            E.analyze(campaign, root / "analysis", package)

    def test_framing_delegate_proof_tamper_rejected(self):
        root, campaign, package = self.fixture()
        path = campaign / "run/identity-stream.json"
        value = C.read(path)
        value["helper_binding_restored"] = False
        rewrite(path, value)
        relock(campaign / "run")
        with self.assertRaises(ValueError):
            E.analyze(campaign, root / "analysis", package)


class AdditionalMemoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.args = memory_case(Path(tmp.name))

    def outcome(self):
        from sr_report import memory_result

        return memory_result(*self.args)

    def set_peak(self, peak):
        for row in self.args[1]:
            for scope in row["scopes"]:
                if scope["peak"] is not None:
                    scope["peak"] = peak

    def test_exact_28GiB_boundary_passes(self):
        self.set_peak(28 * 1024**3)
        self.assertEqual(self.outcome()["outcome"], "startup_resource_margin_pass_scoped")

    def test_one_byte_over_boundary_is_inconclusive(self):
        self.set_peak(28 * 1024**3 + 1)
        self.assertIn(
            "conservative_total_charge_margin_not_demonstrated", self.outcome()["reasons"]
        )

    def test_ancestor_peak_cannot_be_ignored(self):
        for row in self.args[1]:
            row["scopes"][1]["peak"] = 32 * 1024**3
        result = self.outcome()
        self.assertEqual(result["largest_kernel_aggregate_peak_bytes"], 32 * 1024**3)
        self.assertEqual(result["outcome"], "startup_complete_resource_margin_inconclusive")

    def test_max_event_without_oom_is_inconclusive(self):
        self.args[1][-1]["scopes"][0]["events"]["max"] += 1
        self.assertIn("limit_or_oom_event_delta", self.outcome()["reasons"])

    def test_missing_events_are_inconclusive(self):
        for row in self.args[1]:
            row["scopes"][0]["events"].pop("max")
        self.assertIn("event_coverage_incomplete", self.outcome()["reasons"])


class MetadataAdapterTests(unittest.TestCase):
    def fixture(self):
        from pc_interface import freeze

        from fannagent.store import canonical

        fields = C.read(E.REFERENCE / "origin-source.json")["metadata"]
        state = {"source_manifest": freeze({"metadata": fields, "fixed": 1})}
        backend = SimpleNamespace(
            state=state,
            store=SimpleNamespace(get=lambda key, default=None: state.get(key, default)),
        )
        return backend, canonical(fields)

    def test_actual_frozen_metadata_literal_preflight(self):
        from ev_metadata import preflight

        value = preflight(C.read(E.REFERENCE / "origin-source.json")["metadata"])
        self.assertEqual(value["cases"], 8)
        self.assertTrue(value["bindings_restored"] and value["original_state_unchanged"])

    def test_view_restores_before_producer_connection_and_preserves_origin(self):
        from ev_metadata import View
        from pc_interface import FrozenDict, FrozenList

        from fannagent.store import canonical

        backend, expected = self.fixture()
        original = backend.store.get
        source = backend.state["source_manifest"]
        with View(backend, expected) as view:
            result = backend.store.get("source_manifest")
            self.assertIs(backend.store.get, original)
            self.assertIs(type(result["metadata"]), list)
            self.assertEqual(canonical(result["metadata"]), expected)
            self.assertIs(backend.state["source_manifest"], source)
            self.assertIs(type(source), FrozenDict)
            self.assertIs(type(source["metadata"]), FrozenList)
        self.assertEqual(view.record["status"], "complete")

    def test_interrupted_metadata_read_restores(self):
        import ev_metadata
        from ev_metadata import View

        backend, expected = self.fixture()
        original = backend.store.get
        with self.assertRaises(KeyboardInterrupt):
            with View(backend, expected):
                raise KeyboardInterrupt("synthetic interruption")
        self.assertIs(backend.store.get, original)

        self.assertIsNone(ev_metadata._ACTIVE)

    def test_foreign_binding_restored_and_rejected(self):
        from ev_metadata import View

        backend, expected = self.fixture()
        original = backend.store.get
        with self.assertRaises(RuntimeError):
            with View(backend, expected):
                backend.store.get = lambda *a: None
        self.assertIs(backend.store.get, original)

    def test_changed_source_identity_restored_and_rejected(self):
        from ev_metadata import View
        from pc_interface import freeze

        backend, expected = self.fixture()
        original = backend.store.get
        with self.assertRaises(RuntimeError):
            with View(backend, expected):
                backend.state["source_manifest"] = freeze({"metadata": []})
        self.assertIs(backend.store.get, original)

    def test_wrong_metadata_identity_rejected_before_binding(self):
        from ev_metadata import View

        backend, _ = self.fixture()
        original = backend.store.get
        with self.assertRaises(RuntimeError):
            with View(backend, b"[]"):
                pass
        self.assertIs(backend.store.get, original)


class ArchiveTests(unittest.TestCase):
    def fixture(self, kind):
        import io
        import tarfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        name = C.PREFIX + "20261031T010000Z.fixture"
        archive = root / (name + ".tar.gz")
        with tarfile.open(archive, "w:gz") as tar:
            path = name + ("/../escape" if kind == "traversal" else "/run/returned.py")
            member = tarfile.TarInfo(path)
            if kind == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "/outside"
                tar.addfile(member)
            else:
                payload = b"returned data is never executed\n"
                member.size = len(payload)
                tar.addfile(member, io.BytesIO(payload))
                if kind == "duplicate":
                    tar.addfile(member, io.BytesIO(payload))
        return root, archive

    def test_safe_return_is_extracted_only_as_data(self):
        root, archive = self.fixture("safe")
        returned = E.extract_data(archive, root / "returned")
        self.assertEqual(
            (returned / "run/returned.py").read_bytes(), b"returned data is never executed\n"
        )
        with self.assertRaises(FileExistsError):
            E.extract_data(archive, root / "returned")

    def test_traversal_is_rejected_before_extraction(self):
        root, archive = self.fixture("traversal")
        with self.assertRaises(ValueError):
            E.extract_data(archive, root / "returned")
        self.assertFalse((root / "escape").exists())

    def test_symlink_is_rejected_before_extraction(self):
        root, archive = self.fixture("symlink")
        with self.assertRaises(ValueError):
            E.extract_data(archive, root / "returned")

    def test_duplicate_member_is_rejected_before_extraction(self):
        root, archive = self.fixture("duplicate")
        with self.assertRaises(ValueError):
            E.extract_data(archive, root / "returned")


class ProtectedContextTests(unittest.TestCase):
    """Real inherited path/hash logic on bounded filesystem packages, no services."""

    def setUp(self):
        import shutil
        import sys
        from contextlib import ExitStack

        import legacy_common as legacy

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        self.home = root / "home"
        self.home.mkdir()
        self.sources = self.home / "results"
        self.sources.mkdir()
        self.package = root / "scratch/a3-resource-path-fix-packages" / C.NAME
        self.package.mkdir(parents=True)
        self.reference = self.package / "reference"
        self.main = self.home / "torch-startup-attribution-v1-image-reference"
        self.main.mkdir()

        def prior(name):
            p = self.home / name
            p.mkdir()
            (p / "payload").write_bytes(name.encode())
            C.save(p / "manifest.json", dict(files={"payload": C.sha(p / "payload")}))
            return p

        pilot, anchor, midpoint = [prior(name) for name in ("pilot", "anchor", "midpoint")]
        self.exact = prior("torch-exact-topk-v1")
        (self.main / "frozen").mkdir()
        for original, name in (
            (pilot, "frozen/manifest.json"),
            (anchor, "b1b-manifest.json"),
            (midpoint, "b1b2-manifest.json"),
            (self.exact, "prior-exact-manifest.json"),
        ):
            shutil.copyfile(original / "manifest.json", self.main / name)
        raw = self.sources / "prior-campaign"
        raw.mkdir()
        (raw / "raw.txt").write_bytes(b"preserved old result")
        (raw / "completed.txt").write_bytes(b"preserved completed result")
        C.save(
            self.main / "experiment.json",
            dict(
                prior_pilot_package=str(pilot),
                prior_b1b_package=str(anchor),
                prior_b1b2_package=str(midpoint),
                prior_raw_files={raw.name: {"raw.txt": C.sha(raw / "raw.txt")}},
            ),
        )
        # This bounded original-layer fixture delegates to the actual unchanged
        # inherited implementation, including its package.parent sibling lookup.
        # The wider original guard source stays byte-pinned in release review.
        (self.main / "pc_common.py").write_text("from legacy_common import protected\n")
        C.save(
            self.main / "manifest.json",
            dict(
                files={
                    str(p.relative_to(self.main)): C.sha(p)
                    for p in self.main.rglob("*")
                    if p.is_file()
                }
            ),
        )
        shutil.copytree(self.main, self.reference)
        manifest_sha = C.sha(self.main / "manifest.json")
        self.binding = dict(
            campaign="/home/dar579/torch-reviews-results/completed-main",
            package_manifest_sha256=manifest_sha,
        )
        C.save(self.main / "submission-binding.json", self.binding)
        self.reservation = self.sources / ".torch-startup-attribution-v1-reservation.json"
        C.save(self.reservation, self.binding)
        main_entry = dict(
            directory=str(self.main),
            files_sha256={
                **C.read(self.main / "manifest.json")["files"],
                "manifest.json": manifest_sha,
            },
            binding=self.binding,
            reservation_name=self.reservation.name,
        )
        self.additions = dict(
            completed_main_A2=main_entry,
            completed_return=dict(
                directory=str(raw), files_sha256={"completed.txt": C.sha(raw / "completed.txt")}
            ),
        )
        C.save(self.package / "PROTECTED-ADDITIONS.json", self.additions)
        C.save(
            self.package / "RESOURCE-FREEZE.json",
            dict(baseline=dict(reference_manifest_sha256=manifest_sha)),
        )
        self.bootstraps = []

        def bootstrap(path):
            self.bootstraps.append(Path(path))
            sys.path.insert(0, str(root / "historical-bootstrap-only"))

        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(C, "RETAINED_MAIN", self.main))
        stack.enter_context(patch.object(legacy, "SOURCE_MANIFEST", C.sha(pilot / "manifest.json")))
        stack.enter_context(
            patch.object(legacy, "ANCHOR_MANIFEST", C.sha(anchor / "manifest.json"))
        )
        stack.enter_context(
            patch.object(legacy, "MID_MANIFEST_SHA", C.sha(midpoint / "manifest.json"))
        )
        stack.enter_context(
            patch.object(legacy, "PRIOR_EXACT_MANIFEST", C.sha(self.exact / "manifest.json"))
        )
        stack.enter_context(patch.object(legacy, "bootstrap", side_effect=bootstrap))
        self.check = SimpleNamespace(
            check=lambda sources, prior: {"earlier_inventory": "bounded fixture"}
        )
        stack.enter_context(patch.dict(sys.modules, {"protected": self.check}))

    def test_old_embedded_context_reproduces_missing_exact_sibling(self):
        with self.assertRaises(FileNotFoundError) as caught:
            C.original_protection(self.reference, self.reference, self.sources)
        self.assertEqual(
            Path(caught.exception.filename), self.package / "torch-exact-topk-v1/manifest.json"
        )

    def test_nested_capsule_uses_actual_inherited_home_sibling_checks(self):
        import sys

        before = list(sys.path)
        result = C.protected(self.package, self.sources)
        self.assertIn("original_exact_sealed_package", result)
        self.assertIn("completed_main_A2", result)
        self.assertIn("completed_return", result)
        self.assertEqual(self.bootstraps, [self.main])
        self.assertEqual(sys.path, before)

    def test_main_bytes_checked_before_original_import(self):
        (self.main / "experiment.json").write_text("changed")
        with self.assertRaises(ValueError):
            C.protected(self.package, self.sources)
        self.assertEqual(self.bootstraps, [])

    def test_main_binding_checked_before_original_import(self):
        rewrite(
            self.main / "submission-binding.json",
            {**self.binding, "package_manifest_sha256": "0" * 64},
        )
        with self.assertRaises(ValueError):
            C.protected(self.package, self.sources)
        self.assertEqual(self.bootstraps, [])

    def test_main_reservation_checked_before_original_import(self):
        rewrite(self.reservation, {**self.binding, "campaign": "wrong"})
        with self.assertRaises(ValueError):
            C.protected(self.package, self.sources)
        self.assertEqual(self.bootstraps, [])

    def test_historical_exact_mutation_rejected_and_import_path_restored(self):
        import sys

        before = list(sys.path)
        (self.exact / "payload").write_bytes(b"changed exact source")
        with self.assertRaisesRegex(ValueError, "exact-topk v1 source differs"):
            C.protected(self.package, self.sources)
        self.assertEqual(sys.path, before)

    def test_other_completed_return_is_still_checked(self):
        (self.sources / "prior-campaign/completed.txt").write_bytes(b"changed return")
        with self.assertRaises(ValueError):
            C.protected(self.package, self.sources)

    def test_embedded_reference_cannot_replace_retained_context(self):
        self.additions["completed_main_A2"]["directory"] = str(self.reference)
        rewrite(self.package / "PROTECTED-ADDITIONS.json", self.additions)
        with self.assertRaisesRegex(ValueError, "protection context differs"):
            C.protected(self.package, self.sources)
        self.assertEqual(self.bootstraps, [])

    def test_historical_interrupt_restores_caller_import_path(self):
        import sys

        before = list(sys.path)
        self.check.check = lambda *a: (_ for _ in ()).throw(KeyboardInterrupt("bounded failure"))
        with self.assertRaises(KeyboardInterrupt):
            C.protected(self.package, self.sources)
        self.assertEqual(sys.path, before)
