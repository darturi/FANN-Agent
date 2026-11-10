"""Local simulation/integrity checks only. No native performance qualification."""

# ruff: noqa: E402 -- sealed vendor paths and provider guard must precede their imports.

import copy
import io
import json
import sys
import tarfile
import tempfile
import threading
import unittest
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import ec_common as common
import experiment

# Load the exact sealed adapter/core interfaces, never the mutable source checkout.
sys.path[:0] = [str(experiment.SOURCE), str(experiment.SOURCE / "vendor")]
from no_models import enforce

enforce()
import ec_measure
import ec_report
from ec_control import dispatch, reserve
from execution import Budget
from fannagent_pgvector.profiles import PROFILE
from fd_policy_tools import predict

from fannagent.api import validate_policy


class FakeBackend:
    """Replays saved feature prefixes; returns native IDs for fake stopped results."""

    runtime_profile = PROFILE

    def __init__(self, references):
        self.references = references
        self.conn = SimpleNamespace(closed=False)
        self._operation_lock = threading.RLock()
        self._installed = None
        self._policies = SimpleNamespace(clear=lambda: None)
        self.execute_calls = 0

    def snapshot(self):
        return SimpleNamespace(query=lambda q: copy.deepcopy(q))

    @staticmethod
    @lru_cache(maxsize=256)
    def artifact(serialized):
        return validate_policy(json.loads(serialized), PROFILE)

    def validate_policy(self, raw):
        return self.artifact(json.dumps(raw, sort_keys=True))

    def install_policy(self, artifact):
        self._installed = artifact.policy_hash
        return {"policy_hash": artifact.policy_hash}

    def exact_reference(self, query):
        ref = self.references[query["id"]]
        return SimpleNamespace(
            strictly_better=frozenset(ref["truth_strict"]),
            boundary_ties=frozenset(ref["truth_ties"]),
            effective_k=ref["truth_k"],
        )

    @lru_cache(maxsize=2000)
    def checkpoint(self, qid, serialized):
        return predict(json.loads(serialized), self.references[qid]["states"], PROFILE)

    def execute_probe(self, query, mode="native", policy=None, trace=False):
        self.execute_calls += 1
        ref = self.references[query["id"]]
        raw = policy.serialize() if hasattr(policy, "serialize") else policy
        cp = (
            self.checkpoint(query["id"], json.dumps(raw, sort_keys=True))
            if mode == "policy"
            else None
        )
        if mode == "policy":
            self._installed = self.validate_policy(raw).policy_hash
        ss = ref["states"] if cp is None else ref["states"][:cp]
        return SimpleNamespace(
            ids=ref["native_ids"].copy(),
            distances=ref["native_distances"].copy(),
            latency_ms=6.0 if mode == "native" else 5.7,
            metadata={
                "policy_applied": mode == "policy",
                "policy_fallback": False,
                "policy_runtime_error": False,
                "stop_reason": "policy_stop" if cp is not None else "natural",
                "checkpoint_count": len(ss),
                "work_counters": {
                    "frontier_snapshot_count": 0,
                    "frontier_sort_count": 0,
                    "layer0_distance_evaluations": len(ss) * 64,
                    "feature_collection_ns": 1000,
                },
            },
            evidence={
                "truncated": False,
                "checkpoints": [
                    {"index": s["checkpoint_index"], "features": s["features"]} for s in ss
                ],
            }
            if trace
            else None,
        )


def score(truth, result):
    recalled = len(set(result.ids) & truth.strictly_better) + min(
        10 - len(truth.strictly_better), len(set(result.ids) & truth.boundary_ties)
    )
    return {"valid": len(result.ids) == 10, "recall": recalled / 10}


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_manifest = common.sha(experiment.SOURCE / "manifest.json")
        cls.old_receipt = common.sha(
            experiment.ROOT / "agent/docs/verification/selective-agent-v1-pilot-postrun.json"
        )
        cls.old_cfg = common.read(experiment.SOURCE / "experiment.json")
        # Six cases suffice for interface/accounting checks.
        # A fake campaign cannot pass real package verification.
        all_items = common.lines(experiment.SOURCE / "inputs/queries.jsonl")
        groups = sorted({i["group"] for i in all_items})[:2]
        cls.items = [i for i in all_items if i["group"] in groups]
        wanted = {i["query"]["id"] for i in cls.items}
        refs = {}
        raw_path = (
            experiment.EPISODE_ROOT
            / "returned/pilot"
            / common.PILOT
            / "blocks/block-0/references.jsonl"
        )
        with raw_path.open() as handle:
            for line in handle:
                row = json.loads(line)
                if row["query_id"] in wanted:
                    refs[row["query_id"]] = {**row, "states": row["states"]["light19"]}
                if len(refs) == len(wanted):
                    break
        cls.refs = refs
        cls.getters = common.read(raw_path.parent / "qualified-features.json")
        cls.counts = {
            **common.COUNTS,
            "development_vectors": 2,
            "cases": 6,
            "diagnostic_vectors": 1,
            "diagnostic_cases": 3,
            "main_searches": 1137,
            "diagnostic_searches": 90,
            "searches_per_block": 1227,
            "searches_total": 3681,
            "retained_pairs_per_block": 72,
            "warmups_per_block": 18,
            "diagnostic_pairs_per_block": 36,
            "diagnostic_warmups_per_block": 9,
            "control_evictions_per_block": 27,
        }
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.package = cls.root / "package"
        cls.package.mkdir()
        frozen = cls.package / "frozen"
        (frozen / "inputs").mkdir(parents=True)
        common.save(frozen / "experiment.json", cls.old_cfg)
        common.save(
            frozen / "source-index.json", common.read(experiment.SOURCE / "source-index.json")
        )
        common.save(
            cls.package / "candidate.json",
            {
                common.CANDIDATE: common.read(experiment.SOURCE / "candidates.json")[
                    common.CANDIDATE
                ]
            },
        )
        common.save(
            cls.package / "reference-pins.json", {k: common.digest(v) for k, v in refs.items()}
        )
        common.save(cls.package / "manifest.json", {"synthetic_fixture": True})
        cls.cfg = {
            "version": common.VERSION,
            "filters": common.FILTERS,
            "seed": 20261022,
            "diagnostic_groups": groups[:1],
        }
        common.save(cls.package / "experiment.json", cls.cfg)
        with (frozen / "inputs/queries.jsonl").open("x") as handle:
            handle.write("".join(json.dumps(i) + "\n" for i in cls.items))
        common.save(
            frozen / "inputs/development-evidence.json",
            {
                "queries": [
                    {
                        "query_id": r["query_id"],
                        "base_states": r["states"],
                        "native_recall": r["native_recall"],
                    }
                    for r in refs.values()
                ]
            },
        )
        (frozen / "inputs/qualification.jsonl").write_text("")
        cls.campaign = cls.root / "simulation"
        (cls.campaign / "blocks").mkdir(parents=True)
        common.save(cls.campaign / "protected-source-before.json", {"simulation": True})

        def qualify(backend, budget, items, cfg):
            for _ in range(921):
                budget.reserve("synthetic_qualification")
            return cls.getters

        with (
            patch.object(ec_measure, "COUNTS", cls.counts),
            patch("fd_execution.qualify", side_effect=qualify),
        ):
            for block in range(3):
                out = cls.campaign / "blocks" / ("block-" + str(block))
                out.mkdir()
                backend = FakeBackend(refs)
                budget = Budget(cls.counts["searches_per_block"])
                result = ec_measure.measure(
                    backend,
                    SimpleNamespace(score=score),
                    budget,
                    cls.package,
                    out,
                    block,
                    lambda *args, **kwargs: None,
                )
                if result != {"retained_pairs": 72, "diagnostic_pairs": 36}:
                    raise AssertionError(result)
                if budget.calls != 1227 or backend.execute_calls != 300:
                    # Six exact references and 921 synthetic getter reservations
                    # are not execute_probe calls.
                    raise AssertionError((budget.calls, backend.execute_calls))
                common.save(
                    out / "status.json",
                    {
                        "status": "complete",
                        "block": block,
                        "provider_calls": 0,
                        "confirmation_queries": 0,
                        "backend_searches": budget.calls,
                        "retained_pairs": 72,
                        "diagnostic_pairs": 36,
                        "development_cases": 6,
                        "independent_vectors": 2,
                        "diagnostic_cases": 3,
                        "control_installations": 27,
                        "operations": dict(budget.operations),
                    },
                )
                for name in ["protected-source-before.json", "protected-source-after.json"]:
                    common.save(out / name, {"simulation": True})
                for name in ["job-exit.json", "host-exit.json"]:
                    common.save(out / name, {"exit_code": 0})
                common.save(
                    out / "database-identity.json", common.read(frozen / "source-index.json")
                )
                common.save(
                    out / "runtime-identity.json",
                    {
                        "module_sha256": cls.old_cfg["module_sha256"],
                        "registry_hash": PROFILE.native_registry_hash,
                        "runtime_profile_hash": PROFILE.fingerprint,
                        "package_manifest_sha256": common.sha(cls.package / "manifest.json"),
                        "image_sha256": cls.old_cfg["image_sha256"],
                    },
                )
                common.save(
                    out / "LOCK.json",
                    {
                        "package_manifest_sha256": common.sha(cls.package / "manifest.json"),
                        "files_sha256": {
                            p.name: common.sha(p) for p in out.iterdir() if p.is_file()
                        },
                    },
                )

    @classmethod
    def tearDownClass(cls):
        assert cls.old_manifest == common.sha(experiment.SOURCE / "manifest.json")
        assert cls.old_receipt == common.sha(
            experiment.ROOT / "agent/docs/verification/selective-agent-v1-pilot-postrun.json"
        )
        cls.temporary.cleanup()

    def analyze_fixture(self, campaign=None):
        output = Path(tempfile.mkdtemp(dir=self.root))
        with (
            patch.object(ec_report, "COUNTS", self.counts),
            patch.object(ec_report, "verify", return_value=self.cfg),
            patch.object(ec_report, "bootstrap"),
        ):
            return ec_report.analyze(campaign or self.campaign, self.package, output)

    def test_complete_simulated_driver_and_report(self):
        result = self.analyze_fixture()
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["candidate_selection_performed"])
        self.assertFalse(result["canonical_acceptance_established"])
        self.assertEqual(len(result["profiles"]), 3)
        for regimes in result["reports"].values():
            self.assertEqual(regimes["reused-warm"]["mean_preparation_ms"], 0)

    def test_profiler_never_enters_primary_pass(self):
        for block in range(3):
            root = self.campaign / "blocks" / ("block-" + str(block))
            self.assertEqual(len(common.lines(root / "pairs.jsonl")), 72)
            self.assertEqual(len(common.lines(root / "diagnostic-pairs.jsonl")), 36)
            self.assertTrue(all(r["pass"] == "primary" for r in common.lines(root / "pairs.jsonl")))
            profiles = common.read(root / "profiles.json")
            self.assertEqual(len(profiles["groups"]), 36)
            self.assertTrue(all(g["calls"] in [1, 3] for g in profiles["groups"].values()))

    def test_real_protocol_counts_and_caps(self):
        self.assertEqual(921 + 600 * (3 + 3 * (1 + 2 * 5)), common.COUNTS["main_searches"])
        self.assertEqual(180 * 3 * 2 * 5, common.COUNTS["diagnostic_searches"])
        self.assertEqual(3 * 27921, common.COUNTS["searches_total"])
        self.assertLess(common.COUNTS["searches_per_block"], 70000)

    def test_synthetic_package_cannot_verify_or_submit(self):
        with self.assertRaises(Exception):
            common.verify(self.package)

    def test_known_dispatch_not_repeated(self):
        record = {"dispatch": {"block-0": {"status": "unknown"}}}
        with patch("ec_control.subprocess.run") as run:
            with self.assertRaises(ValueError):
                dispatch(self.package, self.campaign, record, 0)
            run.assert_not_called()

    def test_ambiguous_dispatch_retained(self):
        folder = Path(tempfile.mkdtemp(dir=self.root))
        record = {
            "dispatch": {},
            "jobs": {},
            "account": "torch_pr_test",
            "bundle": "/b",
            "prepared": "/p",
            "sources": "/s",
            "campaign": str(folder),
            "workspace": "/w",
            "apptainer": "/a",
        }
        common.save(folder / "submission.json", record)
        with patch(
            "ec_control.subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout="uncertain", stderr=""),
        ):
            with self.assertRaises(RuntimeError):
                dispatch(self.package, folder, record, 0)
        self.assertEqual(
            common.read(folder / "submission.json")["dispatch"]["block-0"]["status"], "unknown"
        )

    def test_global_reservation_blocks_reupload(self):
        folder = Path(tempfile.mkdtemp(dir=self.root))
        reserve(folder, self.package, self.campaign)
        with self.assertRaises(FileExistsError):
            reserve(folder, self.package, self.campaign)

    def test_raw_corruption_rejected(self):
        folder = self.root / "corrupted"
        __import__("shutil").copytree(self.campaign, folder)
        with (folder / "blocks/block-0/pairs.jsonl").open("a") as handle:
            handle.write("{}\n")
        with self.assertRaises(ValueError):
            self.analyze_fixture(folder)

    def test_missing_profile_group_rejected(self):
        value = common.read(self.campaign / "blocks/block-0/profiles.json")
        value["groups"].pop(next(iter(value["groups"])))
        with patch.object(ec_report, "COUNTS", self.counts):
            with self.assertRaises(ValueError):
                ec_report.validate_profiles(value)

    def test_duplicate_measurement_rejected(self):
        with self.assertRaises(ValueError):
            ec_report.unique([{"id": 1}, {"id": 1}], lambda r: r["id"])

    def test_semantic_result_corruption_rejected_even_after_relocking(self):
        folder = self.root / "semantic-corruption"
        __import__("shutil").copytree(self.campaign, folder)
        block = folder / "blocks/block-0"
        path = block / "pairs.jsonl"
        rows = common.lines(path)
        rows[0]["recall_delta"] = 1.0
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        lock = common.read(block / "LOCK.json")
        lock["files_sha256"]["pairs.jsonl"] = common.sha(path)
        common.replace(block / "LOCK.json", lock)
        with self.assertRaises(ValueError):
            self.analyze_fixture(folder)

    def test_serial_dependency_command(self):
        from ec_control import command

        record = {
            "account": "torch_pr_test",
            "bundle": "/b",
            "prepared": "/p",
            "sources": "/s",
            "campaign": "/c",
            "workspace": "/w",
            "apptainer": "/a",
        }
        args = command(self.package, record, ["--array=1", "--dependency=afterok:123"])
        self.assertIn("--dependency=afterok:123", args)
        self.assertIn("--export=NONE", args)
        self.assertIn("--kill-on-invalid-dep=yes", args)

    def test_container_preserves_runner_environment_and_readonly_inputs(self):
        from ec_job import container_command

        args = container_command(
            self.package,
            Path("/bundle"),
            Path("/prepared"),
            Path("/out"),
            Path("/work"),
            "/apptainer",
            2,
        )
        self.assertIn("TORCH_IMAGE_SHA256=" + self.old_cfg["image_sha256"], args)
        self.assertIn(str(self.package) + ":/patch:ro", args)
        self.assertIn("/prepared:/prepared:ro", args)
        self.assertIn("OPENBLAS_NUM_THREADS=1", args)
        self.assertEqual(args[-2:], ["--block", "2"])

    def test_safe_extraction_rejects_traversal_and_links(self):
        for mode in ["traversal", "link"]:
            archive = self.root / ("reviews-execution-cost-v1-" + mode + ".tar.gz")
            with tarfile.open(archive, "w:gz") as tar:
                member = tarfile.TarInfo(
                    archive.name[:-7] + ("/../../escape" if mode == "traversal" else "/link")
                )
                if mode == "link":
                    member.type = tarfile.SYMTYPE
                    member.linkname = "/etc/passwd"
                    tar.addfile(member)
                else:
                    member.size = 1
                    tar.addfile(member, io.BytesIO(b"x"))
            with self.assertRaises(ValueError):
                experiment.extract_data(archive, self.root / ("extract-" + mode))

    def test_provider_imports_forbidden(self):
        for name in ["anthropic", "openai", "litellm", "minisweagent"]:
            with self.assertRaises(RuntimeError):
                __import__(name)

    def test_remote_local_parity_is_strict(self):
        experiment.parity({"a": 0.1}, {"a": 0.1 + 1e-14})
        with self.assertRaises(ValueError):
            experiment.parity({"a": 0.1}, {"a": 0.1001})
        with self.assertRaises(ValueError):
            experiment.parity({"accepted": False}, {"accepted": True})


if __name__ == "__main__":
    unittest.main()
