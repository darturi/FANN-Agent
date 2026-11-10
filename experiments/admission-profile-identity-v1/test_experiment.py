"""Local simulation/integrity checks only. No native performance qualification."""

# ruff: noqa: E402 -- sealed vendor paths and provider guard must precede their imports.

import ast
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

import experiment
import pp_common as common

# Load the exact sealed adapter/core interfaces, never the mutable source checkout.
sys.path[:0] = [str(experiment.SOURCE), str(experiment.SOURCE / "vendor")]
from no_models import enforce

enforce()
import pp_measure
import pp_report
from execution import Budget
from fannagent_pgvector.prepared import PreparedPolicy, PreparedPolicyCache
from fannagent_pgvector.profiles import PROFILE
from fd_policy_tools import predict
from pp_control import dispatch, reserve

from fannagent.api import validate_policy


class FakeBackend:
    """Replays saved feature prefixes; returns native IDs for fake stopped results."""

    runtime_profile = PROFILE

    def __init__(self, references):
        self.references = references
        self.conn = SimpleNamespace(closed=False)
        self._operation_lock = threading.RLock()
        self._installed = None
        self._policies = PreparedPolicyCache(PROFILE)
        self.execute_calls = 0
        self.prepare_calls = 0
        self.installs = 0

    def _prepare_policy(self, raw):
        if isinstance(raw, PreparedPolicy):
            return raw
        self.prepare_calls += 1
        return self._policies.prepare(raw)

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
        prepared = self._prepare_policy(policy) if policy is not None else None
        raw = prepared.artifact.serialize() if prepared is not None else None
        cp = (
            self.checkpoint(query["id"], json.dumps(raw, sort_keys=True))
            if mode == "policy"
            else None
        )
        if mode == "policy":
            if self._installed != prepared.policy_hash:
                _ = prepared.bytecode
                self.installs += 1
            self._installed = prepared.policy_hash
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
        cls.old_cfg["bootstrap_samples"] = 32  # simulation only; real protocol stays 10,000.
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
            "main_searches": 1731,
            "diagnostic_searches": 360,
            "searches_per_block": 2091,
            "searches_total": 8364,
            "retained_pairs_per_block": 288,
            "warmups_per_block": 72,
            "diagnostic_pairs_per_block": 144,
            "diagnostic_warmups_per_block": 36,
            "control_evictions_per_block": 108,
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
            patch.object(pp_measure, "COUNTS", cls.counts),
            patch("fd_execution.qualify", side_effect=qualify),
            patch(
                "pp_backend.execute_owned",
                side_effect=lambda b, q, h, trace=False: b.execute_probe(
                    q, mode="policy", policy=h.resolve(b), trace=trace
                ),
            ),
        ):
            for block in range(4):
                out = cls.campaign / "blocks" / ("block-" + str(block))
                out.mkdir()
                backend = FakeBackend(refs)
                budget = Budget(cls.counts["searches_per_block"])
                result = pp_measure.measure(
                    backend,
                    SimpleNamespace(score=score),
                    budget,
                    cls.package,
                    out,
                    block,
                    lambda *args, **kwargs: None,
                )
                if result != {"retained_pairs": 288, "diagnostic_pairs": 144}:
                    raise AssertionError(result)
                if budget.calls != 2091 or backend.execute_calls != 1164:
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
                        "retained_pairs": 288,
                        "diagnostic_pairs": 144,
                        "development_cases": 6,
                        "independent_vectors": 2,
                        "diagnostic_cases": 3,
                        "control_installations": 108,
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
            patch.object(pp_report, "COUNTS", self.counts),
            patch.object(pp_report, "verify", return_value=self.cfg),
            patch.object(pp_report, "bootstrap"),
        ):
            return pp_report.analyze(campaign or self.campaign, self.package, output)

    def test_complete_simulated_driver_and_report(self):
        result = self.analyze_fixture()
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["candidate_selection_performed"])
        self.assertFalse(result["canonical_acceptance_established"])
        self.assertEqual(len(result["profiles"]), 4)
        self.assertIn(
            result["execution_gate"]["verdict"],
            ["measurement_inconclusive", "revise_or_retain_original"],
        )
        self.assertEqual(result["mechanism_checks"]["owned_reuse_cache_prepare_calls"], 0)
        for regimes in result["reports"].values():
            self.assertEqual(regimes["reused-warm"]["mean_preparation_ms"], 0)

    def test_profiler_never_enters_primary_pass(self):
        for block in range(4):
            root = self.campaign / "blocks" / ("block-" + str(block))
            self.assertEqual(len(common.lines(root / "pairs.jsonl")), 288)
            self.assertEqual(len(common.lines(root / "diagnostic-pairs.jsonl")), 144)
            self.assertTrue(all(r["pass"] == "primary" for r in common.lines(root / "pairs.jsonl")))
            profiles = common.read(root / "profiles.json")
            self.assertEqual(len(profiles["groups"]), 144)
            self.assertTrue(all(g["calls"] in [1, 3] for g in profiles["groups"].values()))

    def test_real_protocol_counts_and_caps(self):
        self.assertEqual(921 + 600 * (3 + 12 * (1 + 2 * 5)), common.COUNTS["main_searches"])
        self.assertEqual(90 * 12 * 2 * 5, common.COUNTS["diagnostic_searches"])
        self.assertEqual(4 * 92721, common.COUNTS["searches_total"])
        self.assertLess(common.COUNTS["searches_per_block"], 100000)
        self.assertEqual(4 * (600 + 90) * 12, 33120)

    def test_williams_schedule_balances_positions_and_predecessors(self):
        from collections import Counter

        for item in self.items:
            qid = item["query"]["id"]
            for semantic in common.SEMANTIC_ARMS:
                rows = [
                    [
                        r[0].split("/")[0]
                        for r in pp_measure.ordered_arms(self.package, qid, b)
                        if r[0].endswith("/" + semantic)
                    ]
                    for b in range(4)
                ]
                positions = Counter((v, pos) for row in rows for pos, v in enumerate(row))
                predecessors = Counter((a, b) for row in rows for a, b in zip(row, row[1:]))
                self.assertEqual(len(positions), 16)
                self.assertEqual(set(positions.values()), {1})
                self.assertEqual(len(predecessors), 12)
                self.assertEqual(set(predecessors.values()), {1})

    def test_all_variants_use_identical_frozen_policies(self):
        records = {name: raw for name, raw, _ in pp_measure.arms(self.package)}
        for name in common.SEMANTIC_ARMS:
            for variant in common.VARIANTS:
                self.assertEqual(records["original/" + name], records[variant + "/" + name])
        self.assertEqual(
            records["original/candidate"],
            common.read(self.package / "candidate.json")[common.CANDIDATE]["policy"],
        )

    def test_synthetic_package_cannot_verify_or_submit(self):
        with self.assertRaises(Exception):
            common.verify(self.package)

    def test_known_dispatch_not_repeated(self):
        record = {"dispatch": {"block-0": {"status": "unknown"}}}
        with patch("pp_control.subprocess.run") as run:
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
            "pp_control.subprocess.run",
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
        with patch.object(pp_report, "COUNTS", self.counts):
            with self.assertRaises(ValueError):
                pp_report.validate_profiles(value)

    def test_duplicate_measurement_rejected(self):
        with self.assertRaises(ValueError):
            pp_report.unique([{"id": 1}, {"id": 1}], lambda r: r["id"])

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

    def test_schedule_and_physical_order_corruption_rejected_after_relocking(self):
        for mutation in ("metadata", "physical"):
            folder = self.root / ("order-corruption-" + mutation)
            __import__("shutil").copytree(self.campaign, folder)
            block = folder / "blocks/block-0"
            path = block / "pairs.jsonl"
            rows = common.lines(path)
            if mutation == "metadata":
                rows[0]["schedule_position"] = 100
            else:
                rows[0], rows[1] = rows[1], rows[0]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            lock = common.read(block / "LOCK.json")
            lock["files_sha256"]["pairs.jsonl"] = common.sha(path)
            common.replace(block / "LOCK.json", lock)
            with self.assertRaises(ValueError):
                self.analyze_fixture(folder)

    def test_admission_mechanism_requires_one_original_fingerprint(self):
        profiles = {"0": common.read(self.campaign / "blocks/block-0/profiles.json")}
        group = profiles["0"]["groups"]["admission-a/candidate/unfiltered/prepare"]
        target = next(
            r
            for r in group["functions"]
            if "/fannagent/api/profiles.py:" in r["function"]
            and r["function"].endswith(":fingerprint")
        )
        target["total_calls"] += 1
        with self.assertRaises(ValueError):
            pp_report.mechanism_checks(profiles)

    def test_serial_dependency_command(self):
        from pp_control import command

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
        from pp_job import container_command

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
            archive = self.root / ("reviews-admission-profile-v1-" + mode + ".tar.gz")
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


class SessionTests(unittest.TestCase):
    def setUp(self):
        from policy import compose

        self.cfg = common.read(experiment.SOURCE / "experiment.json")
        self.raw = compose("local-continue", "continue")
        self.q = {"id": "fixture-unfiltered", "vector": [1.0, 0.0], "k": 10, "filter": None}
        ref = {
            "native_ids": list(range(10)),
            "native_distances": [i / 100 for i in range(10)],
            "states": [{"checkpoint_index": 1, "features": {"checkpoint_index": 1}}],
        }
        self.backend = FakeBackend({self.q["id"]: ref})
        self.execute_patch = patch(
            "pp_backend.execute_owned",
            side_effect=lambda b, q, h, trace=False: b.execute_probe(
                q, mode="policy", policy=h.resolve(b), trace=trace
            ),
        )
        self.execute_patch.start()
        self.addCleanup(self.execute_patch.stop)

    def owned(self, raw=None):
        from pb_session import session

        return session(self.backend, self.raw if raw is None else raw, self.cfg)

    def query(self, session, q=None):
        return session.query(self.q if q is None else q, Budget(20))

    def test_original_and_owned_same_results_but_owned_prepares_once(self):
        from execution import session

        old = session(self.backend, self.raw, self.cfg)
        self.query(old)
        self.query(old)
        self.assertEqual(self.backend.prepare_calls, 2)
        self.backend.prepare_calls = 0
        self.backend._policies.clear()
        self.backend._installed = None
        new = self.owned()
        self.assertEqual(self.backend.prepare_calls, 0)
        first = self.query(new)
        self.assertEqual(self.backend.prepare_calls, 1)
        second = self.query(new)
        self.assertEqual(self.backend.prepare_calls, 1)
        self.assertEqual((first.ids, first.distances), (second.ids, second.distances))

    def test_caller_mutation_cannot_change_owned_policy(self):
        new = self.owned()
        self.raw["eligible"].clear()
        self.raw["tree"]["root"] = {"invalid": True}
        self.assertFalse(self.query(new).metadata["native_bypass"])

    def test_host_bypass_and_wrong_k_never_prepare_or_compile(self):
        raw = copy.deepcopy(self.raw)
        raw["eligible"] = []
        new = self.owned(raw)
        self.assertTrue(self.query(new).metadata["native_bypass"])
        new = self.owned()
        self.assertTrue(self.query(new, {**self.q, "k": 11}).metadata["native_bypass"])
        self.assertEqual(self.backend.prepare_calls, 0)
        self.assertEqual(self.backend.installs, 0)

    def test_cache_eviction_preserves_owned_artifact_and_reinstalls(self):
        new = self.owned()
        self.query(new)
        self.backend._policies.clear()
        self.backend._installed = "evicted"
        self.query(new)
        self.assertEqual(self.backend.prepare_calls, 1)
        self.assertEqual(self.backend.installs, 2)
        self.assertLessEqual(len(self.backend._policies.entries), self.backend._policies.limit)

    def test_new_session_after_clear_pays_preparation_again(self):
        self.query(self.owned())
        self.backend._policies.clear()
        self.query(self.owned())
        self.assertEqual(self.backend.prepare_calls, 2)

    def test_connection_close_replacement_cache_and_profile_changes_reject(self):
        for mutation in ("closed", "replaced", "cache", "identity", "profile"):
            with self.subTest(mutation=mutation):
                self.backend = FakeBackend(self.backend.references)
                new = self.owned()
                if mutation == "closed":
                    self.backend.conn.closed = True
                if mutation == "replaced":
                    self.backend.conn = SimpleNamespace(closed=False)
                if mutation == "cache":
                    self.backend._policies = PreparedPolicyCache(PROFILE)
                if mutation == "identity":
                    self.backend._policies.identity = "changed"
                if mutation == "profile":
                    self.backend.runtime_profile = PROFILE.model_copy(deep=True)
                with self.assertRaises(RuntimeError):
                    self.query(new)
                self.assertEqual(self.backend.execute_calls, 0)

    def test_cross_backend_handle_and_session_rejected(self):
        new = self.owned()
        other = FakeBackend(self.backend.references)
        with self.assertRaises(RuntimeError):
            new._handle.resolve(other)
        new.backend = other
        with self.assertRaises(RuntimeError):
            self.query(new)

    def test_admission_rejection_matches_original(self):
        from execution import session

        cases = []
        for root in (
            None,
            [],
            {"bad": True},
            {"if": {"bool": 1}, "then": "stop", "else": "continue"},
        ):
            raw = copy.deepcopy(self.raw)
            raw["tree"]["root"] = root
            cases.append(raw)
        for value in (float("nan"), float("inf")):
            raw = copy.deepcopy(self.raw)
            raw["tree"]["root"]["if"] = {"op": "eq", "args": [{"float": value}, {"float": 1.0}]}
            cases.append(raw)
        raw = copy.deepcopy(self.raw)
        raw["tree"]["root"] = "continue"
        cases.append(raw)
        raw = copy.deepcopy(self.raw)
        raw["eligible"] = ["unknown"]
        cases.append(raw)
        raw = copy.deepcopy(self.raw)
        raw["name"] = "x" * 161
        cases.append(raw)
        raw = copy.deepcopy(self.raw)
        node = "continue"
        for _ in range(40):
            node = {"if": {"bool": True}, "then": node, "else": "continue"}
        raw["tree"]["root"] = node
        cases.append(raw)
        for raw in cases:
            with self.subTest(raw=repr(raw)[:100]):
                with self.assertRaises(Exception) as old:
                    session(self.backend, raw, self.cfg)
                with self.assertRaises(type(old.exception)):
                    self.owned(raw)

    def test_real_query_validation_and_numeric_rejection_are_preserved(self):
        from execution import session

        from fannagent.api import Snapshot
        from fannagent.api.profiles import DataProfile

        snapshot = Snapshot(
            [{"source_id": 1, "vector": [1.0, 0.0], "metadata": {}}],
            [],
            DataProfile(min_dimension=2, max_dimension=2),
        )
        self.backend.snapshot = lambda: snapshot
        for vector in ([1.0], [float("nan"), 0.0], [0.0, 0.0], [2.0, 0.0]):
            query = {**self.q, "vector": vector}
            with self.assertRaises(Exception) as old:
                self.query(session(self.backend, self.raw, self.cfg), query)
            with self.assertRaises(type(old.exception)):
                self.query(self.owned(), query)
        old = self.query(session(self.backend, self.raw, self.cfg))
        new = self.query(self.owned())
        self.assertEqual((old.ids, old.distances), (new.ids, new.distances))

    def test_lazy_compilation_and_admission_time_are_visible(self):
        new = self.owned()
        self.assertGreater(new.preparation_ms, 0)
        self.assertIsNone(new._handle.prepared)
        self.query(new)
        self.assertIsNotNone(new._handle.prepared._bytecode)

    def test_backend_body_only_changes_the_preparation_expression(self):
        original = ast.parse(
            (experiment.SOURCE / "vendor/fannagent_pgvector/backend.py").read_text()
        )
        node = next(
            n
            for c in original.body
            if isinstance(c, ast.ClassDef)
            for n in c.body
            if isinstance(n, ast.FunctionDef) and n.name == "_execute_probe"
        )
        node.name = "_execute_owned"
        node.body[2] = ast.parse(
            "policy = policy.resolve(self) if policy is not None else None"
        ).body[0]
        actual = ast.parse((Path(__file__).parent / "pp_backend.py").read_text())
        actual_node = next(
            n for n in actual.body if isinstance(n, ast.FunctionDef) and n.name == "_execute_owned"
        )
        self.assertEqual(
            ast.dump(node, include_attributes=False),
            ast.dump(actual_node, include_attributes=False),
        )


class SQLBodyTests(unittest.TestCase):
    """Execute both actual Python SQL bodies against a deterministic DB protocol stub."""

    def backend(self, batched=False, combined=False):
        from contextlib import nullcontext

        owner = FakeBackend({})
        owner.closed = False
        owner._binding = {"index": {"oid": 77}}
        owner.config = SimpleNamespace(copy=SimpleNamespace(trace_max_bytes=100000))
        owner._combined_query_batch = combined
        owner._batch_ready = lambda conn: batched
        owner._connect = lambda: owner.conn
        owner._statement = lambda q: ("ANN_QUERY", [])
        owner.snapshot = lambda: SimpleNamespace(
            query=lambda q: copy.deepcopy(q), source_to_id={str(i): i - 1 for i in range(1, 11)}
        )
        owner.sql_log = []
        owner.bad_nonce = False

        def execute(statement, params=()):
            owner.sql_log.append(str(statement))
            if "begin_execution" in str(statement):
                owner.nonce = params[3]
                return SimpleNamespace(
                    fetchone=lambda: ("wrong" if owner.bad_nonce else owner.nonce,)
                )
            if "fannagent.complete" in str(statement):
                value = {
                    "request_nonce": owner.nonce,
                    "protocol": "same_execution_v4",
                    "policy_hash": owner._installed,
                    "returned_count": 10,
                    "returned_count_source": "client_reported",
                    "effective_mode": "policy_agent",
                    "policy_applied": True,
                    "policy_opportunity": True,
                    "target_index_oid": 77,
                }
                return SimpleNamespace(fetchone=lambda: (json.dumps(value),))
            return SimpleNamespace(fetchall=lambda: [(i, i / 100) for i in range(1, 11)])

        owner.conn.execute = execute
        owner.conn.transaction = nullcontext

        def install(prepared):
            _ = prepared.bytecode
            owner._installed = prepared.policy_hash
            owner.installs += 1

        owner._install_policy = install

        def close():
            owner.closed = True
            owner.conn.closed = True

        owner.close = close
        return owner

    def test_real_original_and_owned_sql_paths_agree(self):
        from contextlib import ExitStack

        import fannagent_pgvector.backend as original
        import pp_backend
        from fannagent_pgvector.backend import NativeBackend
        from policy import compose
        from pp_session import OwnedPolicy

        raw = compose("sql-continue", "continue")["tree"]
        q = {"id": "sql", "vector": [1.0, 0.0], "k": 10}

        def begin(conn, sql, params):
            return conn.execute(sql, params).fetchone()[0]

        def query(conn, sql, params, statement, values, nonce):
            begin(conn, sql, params)
            return conn.execute(statement, values).fetchall()

        def complete(conn, nonce, count):
            return conn.execute("SELECT fannagent.complete", (nonce, count)).fetchone()[0]

        for batched, combined in [(False, False), (True, False), (True, True)]:
            with self.subTest(batched=batched, combined=combined), ExitStack() as stack:
                for module in (original, pp_backend):
                    for name, fn in [
                        ("begin_execution_batch", begin),
                        ("begin_query_batch", query),
                        ("complete_execution_batch", complete),
                    ]:
                        stack.enter_context(patch.object(module, name, fn))
                stack.enter_context(
                    patch("uuid.uuid4", return_value=SimpleNamespace(hex="fixed-nonce"))
                )
                old = self.backend(batched, combined)
                new = self.backend(batched, combined)
                handle = OwnedPolicy(new, copy.deepcopy(raw))
                for _ in range(2):
                    a = NativeBackend._execute_probe(old, q, mode="policy", policy=raw)
                    b = pp_backend.execute_owned(new, q, handle)
                    self.assertEqual(
                        (a.ids, a.distances, a.metadata), (b.ids, b.distances, b.metadata)
                    )
                self.assertEqual(old.sql_log, new.sql_log)
                self.assertEqual((old.prepare_calls, new.prepare_calls), (2, 1))
                self.assertEqual((old.installs, new.installs), (1, 1))

    def test_real_owned_failure_closes_without_native_replay(self):
        import pp_backend
        from policy import compose
        from pp_session import OwnedPolicy

        b = self.backend()
        b.bad_nonce = True
        handle = OwnedPolicy(b, compose("failure", "continue")["tree"])
        with self.assertRaises(Exception):
            pp_backend.execute_owned(b, {"id": "q", "k": 10, "vector": [1.0, 0.0]}, handle)
        self.assertTrue(b.closed)
        self.assertNotIn("ANN_QUERY", b.sql_log)


class AdmissionTests(unittest.TestCase):
    def test_composite_validator_only_changes_profile_binding(self):
        original = ast.parse((experiment.SOURCE / "policy.py").read_text())
        node = next(
            n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == "validate"
        )
        node.args.args.append(ast.arg(arg="PROFILE"))
        node.body = [
            n
            for n in node.body
            if not (isinstance(n, ast.ImportFrom) and n.module == "fannagent_pgvector.profiles")
        ]
        actual = ast.parse((Path(__file__).parent / "pb_policy.py").read_text())
        actual_node = next(n for n in actual.body if isinstance(n, ast.FunctionDef))
        self.assertEqual(ast.dump(node), ast.dump(actual_node))

    def test_profile_snapshot_is_owned_immutable_and_semantically_identical(self):
        from pb_session import AdmissionProfile

        caller = PROFILE.model_copy(deep=True)
        profile = AdmissionProfile.capture(caller)
        self.assertEqual(profile.fingerprint, PROFILE.fingerprint)
        self.assertEqual(dict(profile.runtime_features), PROFILE.runtime_features)
        feature = next(iter(caller.features))
        self.assertIsNot(profile.runtime_features[feature], caller.features[feature])
        caller.features.clear()
        self.assertTrue(profile.runtime_features)
        with self.assertRaises((AttributeError, TypeError)):
            profile.runtime_features.clear = lambda: None
        with self.assertRaises((AttributeError, TypeError)):
            profile.fingerprint = "changed"
        with self.assertRaises(Exception):
            profile.runtime_features[feature].kind = "bool"

    def test_snapshot_hash_is_fresh_per_admission_and_fully_charged(self):
        from pb_session import AdmissionProfile, session
        from policy import compose

        b = FakeBackend({})
        cfg = common.read(experiment.SOURCE / "experiment.json")
        raw = compose("cold-identity", "continue")
        real_capture = AdmissionProfile.capture
        clock = [1000000]

        def capture(profile):
            clock[0] += 5000000
            return real_capture(profile)

        with (
            patch("pb_session.time.perf_counter_ns", side_effect=lambda: clock[0]),
            patch.object(AdmissionProfile, "capture", side_effect=capture) as snapshots,
        ):
            a = session(b, raw, cfg)
            c = session(b, raw, cfg)
        self.assertEqual(snapshots.call_count, 2)
        self.assertIsNot(a._admission_profile, c._admission_profile)
        self.assertEqual(a.preparation_ms, 5.0)
        self.assertEqual(c.preparation_ms, 5.0)
        self.assertEqual(b.prepare_calls, 0)

    def test_wrong_admission_binding_rejected_before_execution(self):
        from pb_session import session
        from policy import compose

        cfg = common.read(experiment.SOURCE / "experiment.json")
        for mutation in ("runtime", "cache"):
            b = FakeBackend({})
            if mutation == "runtime":
                b.runtime_profile = PROFILE.model_copy(deep=True)
            else:
                b._policies.identity = "different"
            with self.assertRaises(RuntimeError):
                session(b, compose("wrong-profile", "continue"), cfg)
            self.assertEqual(b.execute_calls, 0)

    def test_aa_labels_use_same_factory_but_independent_sessions(self):
        from policy import compose

        cfg = common.read(experiment.SOURCE / "experiment.json")
        raw = compose("aa", "continue")
        b = FakeBackend({})
        a = pp_measure.make_session("admission-a/candidate", b, raw, cfg)
        c = pp_measure.make_session("admission-b/candidate", b, raw, cfg)
        self.assertIs(type(a), type(c))
        self.assertIs(type(a).query, __import__("pp_session").OwnedSession.query)
        self.assertIsNot(a._handle, c._handle)
        self.assertIsNot(a.raw, c.raw)
        self.assertEqual(a.identity, c.identity)


class GateTests(unittest.TestCase):
    def setUp(self):
        neutral = {
            "gap_ms": 0.0,
            "gap_ci95": [-0.01, 0.01],
            "outer_gap_ci95": [-0.01, 0.01],
            "log_latency_ratio_ci95": [-0.001, 0.001],
            "all_valid": True,
            "recall_delta_ci95": [0.0, 0.0],
            "native_recall": 0.99,
        }
        report = {
            "overall": copy.deepcopy(neutral),
            "per_filter": {f: copy.deepcopy(neutral) for f in common.FILTERS},
        }
        regimes = {r: copy.deepcopy(report) for r in ("activation-cold", "reused-warm")}
        arms = {a: copy.deepcopy(regimes) for a in common.SEMANTIC_ARMS}
        self.comparisons = {
            f: copy.deepcopy(arms)
            for f in ("p2a_vs_original", "p2b_vs_p2a", "p2b_vs_original", "aa_b_vs_a")
        }
        for family, regime in [
            ("p2b_vs_p2a", "activation-cold"),
            ("p2b_vs_original", "reused-warm"),
        ]:
            stat = self.comparisons[family]["candidate"][regime]["overall"]
            stat.update(
                gap_ms=-0.2,
                gap_ci95=[-0.3, -0.15],
                outer_gap_ci95=[-0.3, -0.15],
                log_latency_ratio_ci95=[-0.05, -0.03],
            )
        self.blocks = {str(b): copy.deepcopy(self.comparisons) for b in range(4)}
        self.reports = {
            a: {r: {"statistics": copy.deepcopy(report)} for r in regimes} for a in common.ARMS
        }

    def verdict(self):
        return pp_report.gate(self.comparisons, self.blocks, self.reports)

    def test_all_prospective_requirements_can_pass(self):
        self.assertEqual(self.verdict()["verdict"], "pass")

    def test_aa_interval_including_zero_is_insufficient(self):
        self.comparisons["aa_b_vs_a"]["candidate"]["activation-cold"]["per_filter"]["votes32"][
            "gap_ci95"
        ] = [-0.2, 0.2]
        self.assertEqual(self.verdict()["verdict"], "measurement_inconclusive")
        self.assertTrue(self.verdict()["aa_failures"])

    def test_aa_outer_and_relative_equivalence_are_required(self):
        for field, value in [
            ("outer_gap_ci95", [-0.11, 0.01]),
            ("log_latency_ratio_ci95", [-0.03, 0.001]),
        ]:
            with self.subTest(field=field):
                original = self.comparisons["aa_b_vs_a"]["routed-native"]["reused-warm"]["overall"][
                    field
                ]
                self.comparisons["aa_b_vs_a"]["routed-native"]["reused-warm"]["overall"][field] = (
                    value
                )
                self.assertEqual(self.verdict()["verdict"], "measurement_inconclusive")
                self.comparisons["aa_b_vs_a"]["routed-native"]["reused-warm"]["overall"][field] = (
                    original
                )

    def test_per_filter_regression_cannot_hide_in_pooled_gain(self):
        self.comparisons["p2b_vs_p2a"]["routed-native"]["reused-warm"]["per_filter"]["votes108"][
            "outer_gap_ci95"
        ] = [0.0, 0.100001]
        self.assertEqual(self.verdict()["verdict"], "revise_or_retain_original")

    def test_each_block_must_show_incremental_activation_gain(self):
        self.blocks["3"]["p2b_vs_p2a"]["candidate"]["activation-cold"]["overall"]["gap_ms"] = 0.001
        self.assertEqual(self.verdict()["verdict"], "revise_or_retain_original")

    def test_aa_does_not_repair_failed_engineering_bounds(self):
        self.comparisons["p2b_vs_p2a"]["candidate"]["activation-cold"]["overall"]["gap_ci95"] = [
            -0.1,
            0.0,
        ]
        result = self.verdict()
        self.assertEqual(result["aa_verdict"], "equivalent_within_declared_bounds")
        self.assertEqual(result["verdict"], "revise_or_retain_original")

    def test_development_quality_reserve_stays_binding(self):
        self.reports["admission-a/candidate"]["reused-warm"]["statistics"]["per_filter"]["votes32"][
            "recall_delta_ci95"
        ] = [-0.0026, 0.0]
        self.assertEqual(self.verdict()["verdict"], "revise_or_retain_original")


if __name__ == "__main__":
    unittest.main()
