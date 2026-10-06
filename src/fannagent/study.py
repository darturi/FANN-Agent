from __future__ import annotations

from dataclasses import asdict

import numpy as np

from .api import ProbeRequest, StopAtCheckpoint, require_capabilities
from .errors import AgentError, ProtectedEvidence
from .evaluation import score, summarize
from .store import digest
from .workload import create_workload


class Study:
    def __init__(self, config, store, backend):
        self.config, self.store, self.backend = config, store, backend
        require_capabilities(backend, study=True)
        self.snapshot = backend.snapshot()
        self.compatibility = backend.compatibility()
        existing = store.get("study")
        if existing:
            self.manifest = store.read(existing)
            if self.manifest["dataset_hash"] != self.snapshot.identity:
                raise AgentError("prepared dataset identity changed")
            if digest(self.manifest["items"]) != self.manifest["workload_hash"]:
                raise AgentError("workload split identity changed")
        else:
            self.manifest = create_workload(self.snapshot, config.workload)
            store.set("study", store.put("study", self.manifest))
        self.development = [i for i in self.manifest["items"] if i["split"] == "development"]
        self.protected = np.asarray(
            [i["query"]["vector"] for i in self.manifest["items"] if i["split"] != "development"]
        )
        self.development_vectors = np.asarray([i["query"]["vector"] for i in self.development])
        self.protected_anchors = {
            self.snapshot.analysis_id(i["anchor"])
            for i in self.manifest["items"]
            if i["split"] != "development" and i.get("anchor") is not None
        }

    def permitted(self, raw):
        if self.store.get("frozen"):
            raise ProtectedEvidence("exploration is closed after policy freeze")
        query = self.snapshot.query(raw)
        vector = np.asarray(query["vector"])
        if len(self.protected) and np.any(np.linalg.norm(self.protected - vector, axis=1) <= 1e-3):
            raise ProtectedEvidence("query vector is outside the development entitlement")
        known_development = np.any(
            np.linalg.norm(self.development_vectors - vector, axis=1) <= 1e-3
        )
        if self.protected_anchors and not known_development:
            nearest_anchor = int(
                np.argmin(np.linalg.norm(self.snapshot.data.vectors - vector, axis=1))
            )
            if nearest_anchor in self.protected_anchors:
                raise ProtectedEvidence("query belongs to a protected synthetic anchor group")
        return query

    def probe(self, raw, policy=None, *, audit=False):
        query = self.permitted(raw)
        result = self.backend.execute_probe(
            ProbeRequest(
                query,
                mode="policy" if policy else "observation",
                policy=policy,
                trace=True,
                audit=audit,
            )
        )
        truth = self.backend.exact_reference(query)
        evidence = self.backend.collect_evidence(result)
        record = {
            "query": query,
            "result": asdict(result),
            "score": score(truth, result),
            "evidence": asdict(evidence),
        }
        artifact = self.store.put(
            "probe", record, scope="development", limit=self.config.evidence.max_bytes
        )
        return {
            "artifact": artifact,
            "score": record["score"],
            "metadata": result.metadata,
            "checkpoint_count": len(evidence.checkpoints),
        }

    def stop_labels(self, query):
        """Real reruns; native-default recall is the query-specific target."""
        cache_key = "stop_labels:" + digest({"query": query, "compatibility": self.compatibility})
        cached = self.store.get(cache_key)
        if cached:
            return self.store.read(cached)["result"]
        result = self._stop_labels(query)
        self.store.set(
            cache_key,
            self.store.put(
                "cached_real_stop_labels",
                {"query_hash": digest(query), "result": result},
                limit=self.config.evidence.max_bytes,
            ),
        )
        return result

    def _stop_labels(self, query):
        truth = self.backend.exact_reference(query)
        default = self.backend.execute_probe(ProbeRequest(query))
        baseline = score(truth, default)
        observation = self.backend.execute_probe(
            ProbeRequest(query, mode="observation", trace=True)
        )
        evidence = self.backend.collect_evidence(observation)
        labels = []
        if baseline["recall"] is None:
            return {"status": "empty_eligible", "labels": [], "cost": None}
        if evidence.truncated:
            return {"status": "truncated", "labels": [], "cost": None}
        if (
            evidence.query_hash != digest(query)
            or evidence.runtime_profile_hash != self.backend.runtime_profile.fingerprint
        ):
            raise AgentError("label evidence identity mismatch")
        if evidence.scope != self.backend.runtime_profile.stopping_scope or any(
            c.work.unit != self.backend.runtime_profile.work_unit for c in evidence.checkpoints
        ):
            raise AgentError("label evidence scope/work units differ from the selected profile")
        for checkpoint in evidence.checkpoints:
            reference = checkpoint.reference
            index = reference.ordinal
            stopped = self.backend.execute_probe(
                ProbeRequest(
                    query,
                    mode="policy",
                    trace=True,
                    intervention=StopAtCheckpoint(reference, evidence.collection_groups),
                )
            )
            actual_evidence = self.backend.collect_evidence(stopped)
            actual = actual_evidence.checkpoints
            prefix = evidence.checkpoints[: len(actual)]
            same = (
                not actual_evidence.truncated
                and actual_evidence.query_hash == evidence.query_hash
                and actual_evidence.runtime_profile_hash == evidence.runtime_profile_hash
                and actual_evidence.scope == evidence.scope
                and 0 < len(actual) <= len(evidence.checkpoints)
                and actual[-1].reference == reference
                and all(a.observation_hash == b.observation_hash for a, b in zip(actual, prefix))
            )
            measured = score(truth, stopped)
            valid = (
                same
                and stopped.metadata.get("stop_reason") == "policy_stop"
                and measured["valid"]
                and measured["recall"] >= baseline["recall"]
            )
            cost = checkpoint.work.value
            labels.append(
                {
                    "checkpoint_index": index,
                    "preserves_default": bool(valid),
                    "default_recall": baseline["recall"],
                    "recall": measured["recall"],
                    "cost": cost,
                    "prefix_matches": same,
                    "work_unit": checkpoint.work.unit,
                }
            )
            if valid:
                return {"status": "observed", "cost": cost, "labels": labels}
        return {
            "status": "censored" if labels else "no_opportunity",
            "cost": None,
            "labels": labels,
        }

    def boundaries(self):
        existing = self.store.get("hardness_boundaries")
        if existing:
            return existing
        costs = []
        diagnostics = []
        for item in self.development:
            label = self.stop_labels(item["query"])
            diagnostics.append({"id": item["query"]["id"], **label})
            if label["cost"] is not None:
                costs.append(label["cost"])
        values = np.quantile(costs, [1 / 3, 2 / 3]).tolist() if costs else [None, None]
        result = {
            "lower": values[0],
            "upper": values[1],
            "definition": "earliest tested real stop preserving default recall",
            "work_unit": self.backend.runtime_profile.work_unit,
            "diagnostics": self.store.put("development_labels", diagnostics, scope="development"),
        }
        self.store.set("hardness_boundaries", result)
        return result

    @staticmethod
    def hardness(label, bounds):
        if label["status"] != "observed" or bounds["lower"] is None:
            return label["status"]
        if label["cost"] <= bounds["lower"]:
            return "easy"
        if label["cost"] >= bounds["upper"]:
            return "hard"
        return "medium"

    def measure(self, policy, split):
        compatibility = self.backend.compatibility()
        bounds = self.boundaries()
        items = [i for i in self.manifest["items"] if i["split"] == split]
        rng = np.random.default_rng(self.config.workload.seed)
        rows, diagnostics = [], []
        for item in items:
            query = item["query"]
            truth = self.backend.exact_reference(query)
            label = self.stop_labels(query)
            hardness = self.hardness(label, bounds)
            diagnostics.append({"id": query["id"], **label})
            for _ in range(self.config.workload.warmups):
                self.backend.execute_probe(ProbeRequest(query))
                self.backend.execute_probe(ProbeRequest(query, mode="policy", policy=policy))
            for repetition in range(self.config.workload.passes):
                results, errors = {}, {}
                for mode in rng.permutation(["native", "policy"]):
                    try:
                        results[mode] = self.backend.execute_probe(
                            ProbeRequest(
                                query, mode=mode, policy=policy if mode == "policy" else None
                            )
                        )
                    except Exception as exc:
                        errors[mode] = type(exc).__name__
                scores = {m: score(truth, r) for m, r in results.items()}
                row = {
                    "id": query["id"],
                    "group": item["group"],
                    "hardness": hardness,
                    "repetition": repetition,
                    "valid": not errors and all(s["valid"] for s in scores.values()),
                    "errors": errors,
                    "recall_delta": None,
                }
                for mode in ("native", "policy"):
                    row[f"{mode}_ms"] = results[mode].latency_ms if mode in results else None
                    row[f"{mode}_recall"] = scores[mode]["recall"] if mode in scores else None
                if all(row[f"{m}_recall"] is not None for m in ("native", "policy")):
                    row["recall_delta"] = row["policy_recall"] - row["native_recall"]
                rows.append(row)
                # Persist progress. Test measurements cannot be replayed after a crash.
                if split == "test":
                    pair = self.store.put("test_pair", row, limit=self.config.evidence.max_bytes)
                    self.store.set(
                        "test_progress",
                        {"pairs": len(rows), "last_query": query["id"], "last_pair": pair},
                    )
        wc = self.config.workload
        if self.backend.compatibility() != compatibility:
            raise AgentError("backend identity changed during evaluation")
        summary = summarize(
            rows,
            seed=wc.seed,
            samples=wc.bootstrap_samples,
            minimum=wc.minimum_groups,
            tolerance=wc.recall_tolerance,
        )
        summary.update(
            {
                "policy_hash": policy.policy_hash,
                "extension_manifest": self.store.get("extension_manifest"),
                "compatibility": compatibility,
                "split": split,
                "workload_origin": self.manifest["origin"],
                "claims": self.manifest["claims"],
                "simulated": bool(self.backend.inspect_target().get("simulated")),
                "measurement_schedule": {"warmups": wc.warmups, "paired_passes": wc.passes},
                "rows": self.store.put(
                    f"{split}_measurements",
                    rows,
                    scope="development" if split == "development" else "private",
                    limit=self.config.evidence.max_bytes,
                ),
                "diagnostics": self.store.put(
                    f"{split}_labels",
                    diagnostics,
                    scope="development" if split == "development" else "private",
                    limit=self.config.evidence.max_bytes,
                ),
            }
        )
        return summary

    def validate(self, raw, *, calibration=False):
        if self.store.get("frozen"):
            raise ProtectedEvidence("candidate selection is closed")
        policy = self.backend.validate_policy(raw)
        self.store.put(
            "candidate_policy",
            policy.model_dump(mode="json"),
            scope="development",
            limit=self.config.evidence.max_bytes,
        )
        if calibration:
            report = self.measure(policy, "calibration")
            self.store.set(f"calibration:{policy.policy_hash}", report)
            return {k: report[k] for k in ("status", "valid", "groups", "latencies")}
        return {"policy_hash": policy.policy_hash, "feature_groups": policy.feature_groups}

    def submit(self, raw):
        policy = self.backend.validate_policy(raw)
        self.validate(raw)
        calibration = self.store.get(f"calibration:{policy.policy_hash}")
        if not calibration or calibration["status"] != "accepted":
            raise AgentError("candidate must pass aggregate calibration before submission")
        self.boundaries()
        envelope = {
            "policy": policy.model_dump(mode="json"),
            "policy_hash": policy.policy_hash,
            "study_hash": self.manifest["workload_hash"],
            "dataset_hash": self.snapshot.identity,
            "copy_hash": digest(self.store.get("prepared")),
            "compatibility": self.backend.compatibility(),
            "backend": self.config.backend.name,
            "evaluation_config": self.config.workload.model_dump(mode="json"),
        }
        frozen = self.store.put("frozen_policy", envelope)
        self.store.set("frozen", frozen)
        return {"frozen": frozen, "policy_hash": policy.policy_hash}

    def frozen_policy(self):
        identity = self.store.get("frozen")
        if not identity:
            raise AgentError("no frozen policy")
        envelope = self.store.read(identity)
        if (
            envelope["dataset_hash"] != self.snapshot.identity
            or envelope["copy_hash"] != digest(self.store.get("prepared"))
            or envelope["study_hash"] != self.manifest["workload_hash"]
            or envelope["evaluation_config"] != self.config.workload.model_dump(mode="json")
            or envelope["compatibility"] != self.backend.compatibility()
        ):
            raise AgentError("frozen policy compatibility changed")
        policy = self.backend.validate_policy(envelope["policy"])
        if policy.policy_hash != envelope["policy_hash"]:
            raise AgentError("frozen policy hash changed")
        return policy

    def final(self):
        policy = self.frozen_policy()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM state WHERE key='test_entitlement'").fetchone():
                existing = self.store.get("report")
                if existing:
                    return self.store.read(existing)
                raise ProtectedEvidence("final test consumed; interrupted results are inconclusive")
            db.execute("INSERT INTO state VALUES ('test_entitlement',?)", ('"consumed"',))
        try:
            report = self.measure(policy, "test")
        except Exception as exc:
            report = {
                "status": "no_recommendation",
                "valid": False,
                "failure": type(exc).__name__,
                "policy_hash": policy.policy_hash,
                "partial_progress": self.store.get("test_progress"),
            }
        self.store.set("report", self.store.put("report", report))
        return report
