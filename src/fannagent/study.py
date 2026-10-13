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

    def screen(self, raw, raw_policy):
        """Small production-mode comparison; never a statistical acceptance result."""
        query = self.permitted(raw)
        policy = self.backend.validate_policy(raw_policy)
        control = self.backend.validate_policy(
            {
                "name": "screen-continue-control",
                "root": "continue",
                "feature_groups": list(policy.feature_groups),
            }
        )
        truth = self.backend.exact_reference(query)
        candidates = {"native": None, "policy": policy, "continue": control}
        results = {name: [] for name in candidates}
        rng = np.random.default_rng(self.config.workload.seed)
        for repetition in range(4):  # One warmup and three small paired repetitions.
            for name in rng.permutation(list(candidates)):
                candidate = candidates[name]
                result = self.backend.execute_probe(
                    ProbeRequest(
                        query,
                        mode="policy" if candidate else "native",
                        policy=candidate,
                        trace=False,
                    )
                )
                if repetition:
                    results[name].append(
                        {
                            "latency_ms": result.latency_ms,
                            "score": score(truth, result),
                            "stop_reason": result.metadata.get("stop_reason"),
                        }
                    )
        view = {
            name: {
                "median_ms": float(np.median([r["latency_ms"] for r in rows])),
                "mean_recall": float(np.mean([r["score"]["recall"] for r in rows]))
                if all(r["score"]["recall"] is not None for r in rows)
                else None,
                "valid": all(r["score"]["valid"] for r in rows),
                "stop_reasons": [r["stop_reason"] for r in rows],
            }
            for name, rows in results.items()
        }
        return {
            "artifact": self.store.put(
                "development_screen",
                {
                    "query": query,
                    "policy_hash": policy.policy_hash,
                    "results": results,
                },
                scope="development",
                limit=self.config.evidence.max_bytes,
            ),
            "modes": view,
            "warmups": 1,
            "paired_passes": 3,
            "timing_metric": "unchanged ProbeResult.latency_ms",
            "trace": False,
            "statistical_acceptance": False,
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
        for position, item in enumerate(self.development, 1):
            label = self.stop_labels(item["query"])
            diagnostics.append({"id": item["query"]["id"], **label})
            if label["cost"] is not None:
                costs.append(label["cost"])
            self._evaluation_progress("development_labels", position, len(self.development))
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
        self._evaluation_progress("identity_check")
        compatibility = self.backend.compatibility()
        bounds = self.boundaries()
        items = [i for i in self.manifest["items"] if i["split"] == split]
        rng = np.random.default_rng(self.config.workload.seed)
        rows, diagnostics = [], []
        for position, item in enumerate(items, 1):
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
            # Progress is recorded between query batches, outside ProbeResult timing.
            self._evaluation_progress("paired_measurements", position, len(items))
        wc = self.config.workload
        self._evaluation_progress("final_identity_check")
        if self.backend.compatibility() != compatibility:
            raise AgentError("backend identity changed during evaluation")
        self._evaluation_progress("statistical_summary")
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

    def _evaluation_progress(self, phase, completed=0, total=None):
        callback = getattr(self, "evaluation_progress", None)
        if callback:
            callback(phase, completed, total)

    def checkpoint_policy_hash(self):
        return (self.store.get("candidate_checkpoint") or {}).get("policy_hash")

    def _envelope(self, policy):
        return {
            "policy": policy.model_dump(mode="json"),
            "policy_hash": policy.policy_hash,
            "study_hash": self.manifest["workload_hash"],
            "dataset_hash": self.snapshot.identity,
            "copy_hash": digest(self.store.get("prepared")),
            "compatibility": self.backend.compatibility(),
            "backend": self.config.backend.name,
            "evaluation_config": self.config.workload.model_dump(mode="json"),
        }

    def validate(self, raw, *, calibration=False, checkpoint=False):
        if type(checkpoint) is not bool:
            raise AgentError("checkpoint must be a Boolean")
        if checkpoint and not calibration:
            raise AgentError("checkpoint requires calibration")
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
            envelope = self._envelope(policy) if checkpoint else None
            report = self.measure(policy, "calibration")
            updates = {f"calibration:{policy.policy_hash}": report}
            if checkpoint and report["status"] == "accepted" and report["valid"] is True:
                if (
                    envelope != self._envelope(policy)
                    or report["policy_hash"] != policy.policy_hash
                    or report["compatibility"] != envelope["compatibility"]
                ):
                    raise AgentError("checkpoint identity changed during calibration")
                boundaries = self.store.get("hardness_boundaries")
                if boundaries is None:
                    raise AgentError("checkpoint requires cached hardness boundaries")
                identity = self.store.put(
                    "candidate_checkpoint",
                    {
                        "envelope": envelope,
                        "calibration": report,
                        "study_artifact": self.store.get("study"),
                        "hardness_boundaries": boundaries,
                    },
                )
                updates["candidate_checkpoint"] = {
                    "artifact": identity,
                    "policy_hash": policy.policy_hash,
                }
            self.store.set_many(updates)
            return {
                **{k: report[k] for k in ("status", "valid", "groups", "latencies")},
                "checkpoint_policy_hash": self.checkpoint_policy_hash(),
            }
        return {"policy_hash": policy.policy_hash, "feature_groups": policy.feature_groups}

    def _eligible_policy(self, raw):
        if self.store.get("frozen") or self.store.get("test_entitlement"):
            raise ProtectedEvidence("candidate selection is closed")
        policy = self.backend.validate_policy(raw)
        calibration = self.store.get(f"calibration:{policy.policy_hash}")
        if (
            not calibration
            or calibration["status"] != "accepted"
            or calibration.get("valid") is not True
        ):
            raise AgentError("candidate must pass aggregate calibration before submission")
        return policy, calibration

    def _freeze(self, envelope, *, finalization=None):
        frozen = self.store.put("frozen_policy", envelope)
        updates = {"frozen": frozen, "status": "frozen"}
        delete = ()
        if finalization:
            updates["finalization"] = finalization
            delete = ("budget_exhaustion_report",)
            previous = self.store.get("report")
            if previous and not self.store.get("test_entitlement"):
                report = self.store.read(previous)
                if report.get("run_status") == "budget_exhausted" and report.get("split") != "test":
                    delete += ("report",)
        self.store.set_many(updates, delete=delete)
        return {"frozen": frozen, "policy_hash": envelope["policy_hash"]}

    def submit(self, raw):
        policy, _ = self._eligible_policy(raw)
        from .experiments import ExperimentJournal
        from .guidance import prepare_guidance

        prepare_guidance(self.config, self.store, self.backend)
        ExperimentJournal(self.store).require_candidate(policy.policy_hash)
        self.validate(raw)
        self.boundaries()
        return self._freeze(self._envelope(policy))

    def finalize_checkpoint(self):
        """Freeze the agent's choice using cached evidence, never new measurements."""
        if self.store.get("frozen"):
            return {
                "status": "frozen",
                "policy_hash": self.frozen_policy().policy_hash,
                **(self.store.get("finalization") or {}),
            }
        selected = self.store.get("candidate_checkpoint")
        if not selected:
            return no_checkpoint_outcome()
        policy_hash = selected.get("policy_hash")
        try:
            record = self.store.read(selected["artifact"])
            envelope = record["envelope"]
            policy, calibration = self._eligible_policy(envelope["policy"])
            if (
                policy.policy_hash != policy_hash
                or envelope != self._envelope(policy)
                or calibration != record["calibration"]
                or record["study_artifact"] != self.store.get("study")
                or record["hardness_boundaries"] is None
                or record["hardness_boundaries"] != self.store.get("hardness_boundaries")
            ):
                raise AgentError("checkpoint evidence or environment identity changed")
        except Exception as exc:
            return checkpoint_failure("checkpoint_ineligible", policy_hash, exc)
        finalization = {
            "termination_reason": "budget_exhausted",
            "finalization_source": "checkpoint",
            "checkpoint_policy_hash": policy_hash,
        }
        try:
            frozen = self._freeze(envelope, finalization=finalization)
        except Exception as exc:
            return checkpoint_failure("checkpoint_finalization_failed", policy_hash, exc)
        return {"status": "frozen", **frozen, **finalization}

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
        report.update(self.store.get("finalization") or {})
        self.store.set("report", self.store.put("report", report))
        return report


def checkpoint_failure(reason_code, policy_hash, exc):
    return {
        "status": "no_recommendation",
        "valid": False,
        "reason_code": reason_code,
        "policy_hash": policy_hash,
        "failure": type(exc).__name__,
        "failure_message": str(exc),
    }


def no_checkpoint_outcome():
    return {
        "status": "no_recommendation",
        "valid": True,
        "reason_code": "no_eligible_checkpoint",
        "reason": "monetary ceiling reached without an agent-selected checkpoint",
    }
