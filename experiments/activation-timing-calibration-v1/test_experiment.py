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


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.package = cls.root / "package"
        cls.package.mkdir()
        frozen = cls.package / "frozen"
        (frozen / "inputs").mkdir(parents=True)
        cls.cfg = common.read(experiment.SOURCE / "experiment.json")
        cls.cfg["bootstrap_samples"] = 32
        cls.protocol = {"version": common.VERSION, "seed": 20261022, "filters": common.FILTERS}
        common.save(frozen / "experiment.json", cls.cfg)
        common.save(
            frozen / "source-index.json", common.read(experiment.SOURCE / "source-index.json")
        )
        common.save(cls.package / "experiment.json", cls.protocol)
        common.save(cls.package / "manifest.json", {"synthetic_fixture": True})
        common.save(
            cls.package / "candidate.json",
            {
                common.CANDIDATE: common.read(experiment.SOURCE / "candidates.json")[
                    common.CANDIDATE
                ]
            },
        )
        all_items = common.lines(experiment.SOURCE / "inputs/queries.jsonl")
        groups = sorted({i["group"] for i in all_items})[:2]
        cls.items = [i for i in all_items if i["group"] in groups]
        wanted = {i["query"]["id"] for i in cls.items}
        prior = experiment.EPISODE_ROOT / "returned/pilot" / common.PILOT / "blocks/block-0"
        cls.refs = {}
        for line in (prior / "references.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["query_id"] in wanted:
                cls.refs[r["query_id"]] = {**r, "states": r["states"]["light19"]}
        (frozen / "inputs/queries.jsonl").write_text(
            "".join(json.dumps(i) + "\n" for i in cls.items)
        )
        (frozen / "inputs/qualification.jsonl").write_text("")
        common.save(
            frozen / "inputs/development-evidence.json",
            {
                "queries": [
                    {"query_id": q, "base_states": r["states"], "native_recall": r["native_recall"]}
                    for q, r in cls.refs.items()
                ]
            },
        )
        common.save(
            cls.package / "reference-pins.json", {q: common.digest(r) for q, r in cls.refs.items()}
        )
        cls.counts = {
            **common.COUNTS,
            "development_vectors": 2,
            "cases": 6,
            "main_searches": 3873,
            "searches_per_block": 3873,
            "searches_total": 7746,
            "retained_pairs_per_block": 960,
            "warmups_per_block": 240,
            "conditioning_searches_per_block": 480,
            "slots_per_block": 240,
            "proof_executions_per_block": 54,
            "control_evictions_per_block": 240,
        }
        cls.campaign = cls.root / "campaign"
        (cls.campaign / "blocks").mkdir(parents=True)
        common.save(cls.campaign / "protected-source-before.json", {"simulation": True})

        def qualify(backend, budget, items, cfg):
            for _ in range(921):
                budget.reserve("simulated_qualification")
            return common.read(prior / "qualified-features.json")

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
            for block in range(2):
                out = cls.campaign / "blocks" / f"block-{block}"
                out.mkdir()
                backend = FakeBackend(cls.refs)
                budget = Budget(3873)
                result = pp_measure.measure(
                    backend,
                    SimpleNamespace(score=score),
                    budget,
                    cls.package,
                    out,
                    block,
                    lambda *args, **kwargs: None,
                )
                assert budget.calls == 3873 and backend.execute_calls == 2946, (
                    budget.calls,
                    backend.execute_calls,
                )
                assert result == {
                    "retained_pairs": 960,
                    "warmup_pairs": 240,
                    "conditioning_searches": 480,
                    "slots": 240,
                    "diagnostic_pairs": 0,
                }, result
                common.save(
                    out / "status.json",
                    {
                        "status": "complete",
                        "block": block,
                        "backend_searches": budget.calls,
                        "provider_calls": 0,
                        "confirmation_queries": 0,
                        "development_cases": 6,
                        "independent_vectors": 2,
                        "diagnostic_cases": 0,
                        "control_installations": 240,
                        "operations": dict(budget.operations),
                        "elapsed_seconds": 1.0,
                        **result,
                    },
                )
                for name in ["protected-source-before.json", "protected-source-after.json"]:
                    common.save(out / name, {"simulation": True})
                common.save(out / "job-exit.json", {"exit_code": 0})
                common.save(
                    out / "host-exit.json", {"exit_code": 0, "protected_sources_unchanged": True}
                )
                common.save(
                    out / "database-identity.json", common.read(frozen / "source-index.json")
                )
                common.save(
                    out / "runtime-identity.json",
                    {
                        "module_sha256": cls.cfg["module_sha256"],
                        "image_sha256": cls.cfg["image_sha256"],
                        "runtime_profile_hash": PROFILE.fingerprint,
                        "registry_hash": PROFILE.native_registry_hash,
                        "package_manifest_sha256": common.sha(cls.package / "manifest.json"),
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
        cls.temporary.cleanup()

    def analyze(self, campaign=None):
        out = Path(tempfile.mkdtemp(dir=self.root))
        with (
            patch.object(pp_report, "COUNTS", self.counts),
            patch.object(pp_report, "verify", return_value=self.protocol),
            patch.object(pp_report, "bootstrap"),
        ):
            return pp_report.analyze(campaign or self.campaign, self.package, out)

    def mutate(self, name, filename, fn):
        folder = self.root / name
        __import__("shutil").copytree(self.campaign, folder)
        block = folder / "blocks/block-0"
        p = block / filename
        rows = common.lines(p)
        fn(rows)
        p.write_text("".join(json.dumps(r) + "\n" for r in rows))
        lock = common.read(block / "LOCK.json")
        lock["files_sha256"][filename] = common.sha(p)
        common.replace(block / "LOCK.json", lock)
        return folder

    def test_complete_driver_and_verifier(self):
        result = self.analyze()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(set(result["aa_controls"]), set(common.CELLS))
        self.assertFalse(result["canonical_acceptance_established"])
        self.assertFalse(result["retroactive_P2b_qualification"])
        self.assertTrue(result["execution_gate"]["frozen_P2b_gate_logic_used"])

    def test_ABBA_crossover_and_cell_position_balance(self):
        for i in self.items:
            qid = i["query"]["id"]
            self.assertEqual(pp_measure.cell_order(qid, 0), pp_measure.cell_order(qid, 1)[::-1])
            for b in range(2):
                slots = list(pp_measure.schedule(qid, b))
                for cell in common.CELLS:
                    labels = [r["label"] for r in slots if r["cell"] == cell]
                    self.assertIn(labels, [list("abba"), list("baab")])
                    self.assertEqual(
                        len({r["cell_position"] for r in slots if r["cell"] == cell}), 1
                    )

    def test_all_references_and_labels_keep_identical_policy_data(self):
        raws = pp_measure.policies(self.package)
        self.assertEqual(
            raws["candidate"],
            common.read(self.package / "candidate.json")[common.CANDIDATE]["policy"],
        )
        self.assertEqual(
            set(common.ARMS),
            {m["arm"] for m in pp_measure.schedule(self.items[0]["query"]["id"], 0)},
        )
        for variant in ["original", "owned", "admission"]:
            b = FakeBackend(self.refs)
            raw = raws["candidate"]
            a = pp_measure.make_session(variant + "-a/candidate", b, raw, self.cfg)
            c = pp_measure.make_session(variant + "-b/candidate", b, raw, self.cfg)
            self.assertIs(type(a), type(c))
            self.assertEqual(a.identity, c.identity)
            self.assertIsNot(a.raw, c.raw)

    def test_exact_resource_accounting(self):
        self.assertEqual(
            921 + 600 * (3 + 9 + 10 * 2 * 2 * (2 + 5 * 2)), common.COUNTS["searches_per_block"]
        )
        self.assertEqual(2 * 296121, common.COUNTS["searches_total"])
        self.assertEqual(600 * 10 * 4 * 2, common.COUNTS["conditioning_searches_per_block"])
        self.assertEqual(600 * 10 * 4, common.COUNTS["control_evictions_per_block"])

    def test_conditioning_occurs_before_constructor_and_is_recorded(self):
        folder = self.campaign / "blocks/block-0"
        rows = common.lines(folder / "slots.jsonl")
        self.assertEqual(len(rows), 240)
        self.assertEqual(len(common.lines(folder / "conditioning.jsonl")), 480)
        for r in rows:
            self.assertLessEqual(r["conditioned_ns"], r["constructor_started_ns"])
            self.assertTrue(r["cache_empty_after_conditioning"])
            self.assertTrue(r["installation_unchanged_until_first_pair"])

    def test_relocked_conditioning_overlap_rejected(self):
        def change(rows):
            rows[0]["conditioned_ns"] = rows[0]["constructor_finished_ns"] + 1

        with self.assertRaises(ValueError):
            self.analyze(self.mutate("overlap", "slots.jsonl", change))

    def test_relocked_missing_conditioner_rejected(self):
        with self.assertRaises(ValueError):
            self.analyze(
                self.mutate("missing-conditioner", "conditioning.jsonl", lambda rows: rows.pop())
            )

    def test_relocked_physical_pair_order_rejected(self):
        def change(rows):
            rows[0], rows[1] = rows[1], rows[0]

        with self.assertRaises(ValueError):
            self.analyze(self.mutate("pair-order", "pairs.jsonl", change))

    def test_relocked_admission_charge_tampering_rejected(self):
        def change(rows):
            rows[0]["preparation_ms"] = 0.0

        with self.assertRaises(ValueError):
            self.analyze(self.mutate("charge", "pairs.jsonl", change))

    def test_relocked_false_cold_cache_state_rejected(self):
        def change(rows):
            rows[0]["cache_empty_after_constructor"] = False

        with self.assertRaises(ValueError):
            self.analyze(self.mutate("cache-state", "slots.jsonl", change))

    def test_relocked_wrong_conditioner_output_rejected(self):
        def change(rows):
            rows[0]["output_sha256"] = "changed"

        with self.assertRaises(ValueError):
            self.analyze(self.mutate("conditioner-output", "conditioning.jsonl", change))

    def test_no_independent_sample_inflation(self):
        result = self.analyze()
        for regimes in result["aa_controls"].values():
            for record in regimes.values():
                self.assertEqual(record["overall"]["independent_vectors"], 2)

    def test_corrupted_raw_hash_rejected(self):
        folder = self.root / "bad-hash"
        __import__("shutil").copytree(self.campaign, folder)
        with (folder / "blocks/block-0/pairs.jsonl").open("a") as f:
            f.write("{}\n")
        with self.assertRaises(ValueError):
            self.analyze(folder)

    def test_fake_package_cannot_submit_or_verify(self):
        with self.assertRaises(Exception):
            common.verify(self.package)

    def test_ambiguous_submission_retains_unknown(self):
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

    def test_serial_dependency_and_readonly_runner(self):
        from pp_control import command
        from pp_job import container_command

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
        self.assertIn("--kill-on-invalid-dep=yes", args)
        cmd = container_command(
            self.package,
            Path("/bundle"),
            Path("/prepared"),
            Path("/out"),
            Path("/work"),
            "/apptainer",
            1,
        )
        self.assertIn(str(self.package) + ":/patch:ro", cmd)
        self.assertIn("/prepared:/prepared:ro", cmd)
        self.assertIn("OPENBLAS_NUM_THREADS=1", cmd)
        self.assertIn("TORCH_IMAGE_SHA256=" + self.cfg["image_sha256"], cmd)

    def test_unknown_dispatch_cannot_repeat(self):
        with patch("pp_control.subprocess.run") as run:
            with self.assertRaises(ValueError):
                dispatch(
                    self.package, self.campaign, {"dispatch": {"block-0": {"status": "unknown"}}}, 0
                )
            run.assert_not_called()

    def test_global_reservation_prevents_reupload(self):
        folder = Path(tempfile.mkdtemp(dir=self.root))
        reserve(folder, self.package, self.campaign)
        with self.assertRaises(FileExistsError):
            reserve(folder, self.package, self.campaign)

    def test_safe_archive_rejects_links_and_traversal(self):
        for mode in ["link", "traversal"]:
            p = self.root / ("reviews-activation-calibration-v1-" + mode + ".tar.gz")
            with tarfile.open(p, "w:gz") as tar:
                info = tarfile.TarInfo(
                    p.name[:-7] + ("/link" if mode == "link" else "/../../escape")
                )
                if mode == "link":
                    info.type = tarfile.SYMTYPE
                    info.linkname = "/etc/passwd"
                    tar.addfile(info)
                else:
                    info.size = 1
                    tar.addfile(info, io.BytesIO(b"x"))
            with self.assertRaises(ValueError):
                experiment.extract_data(p, self.root / ("extract-" + mode))

    def test_provider_import_guard(self):
        for module in ["openai", "anthropic", "litellm", "minisweagent"]:
            with self.assertRaises(RuntimeError):
                __import__(module)

    def test_strict_remote_local_parity(self):
        experiment.parity({"x": 1.0}, {"x": 1.0 + 1e-14})
        with self.assertRaises(ValueError):
            experiment.parity({"x": True}, {"x": False})


class CalibrationGateTests(unittest.TestCase):
    def setUp(self):
        stat = {
            "gap_ci95": [-0.01, 0.01],
            "outer_gap_ci95": [-0.01, 0.01],
            "log_latency_ratio_ci95": [-0.001, 0.001],
        }
        report = {
            "overall": copy.deepcopy(stat),
            "per_filter": {f: copy.deepcopy(stat) for f in common.FILTERS},
        }
        self.aa = {
            cell: {regime: copy.deepcopy(report) for regime in ["activation-cold", "reused-warm"]}
            for cell in common.CELLS
        }

    def test_all_paths_can_establish_equivalence(self):
        self.assertEqual(pp_report.calibration_gate(self.aa)["verdict"], "pass")

    def test_original_and_native_controls_are_mandatory(self):
        for cell in ["original/candidate", "native/native"]:
            aa = copy.deepcopy(self.aa)
            aa[cell]["activation-cold"]["per_filter"]["votes32"]["gap_ci95"] = [-0.2, 0.2]
            self.assertEqual(pp_report.calibration_gate(aa)["verdict"], "measurement_inconclusive")

    def test_including_zero_is_not_equivalence(self):
        self.aa["admission/candidate"]["activation-cold"]["overall"]["outer_gap_ci95"] = [
            -0.11,
            0.01,
        ]
        self.assertEqual(pp_report.calibration_gate(self.aa)["verdict"], "measurement_inconclusive")

    def test_missing_control_or_filter_cannot_qualify(self):
        missing = copy.deepcopy(self.aa)
        missing.pop("native/native")
        with self.assertRaises(ValueError):
            pp_report.calibration_gate(missing)
        missing = copy.deepcopy(self.aa)
        missing["admission/candidate"]["activation-cold"]["per_filter"].pop("votes32")
        with self.assertRaises(ValueError):
            pp_report.calibration_gate(missing)

    def test_relative_band_remains_binding(self):
        self.aa["owned/routed-native"]["reused-warm"]["overall"]["log_latency_ratio_ci95"] = [
            -0.03,
            0.001,
        ]
        self.assertEqual(pp_report.calibration_gate(self.aa)["verdict"], "measurement_inconclusive")


if __name__ == "__main__":
    unittest.main()
