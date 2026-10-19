from __future__ import annotations

from collections import Counter
from typing import NotRequired, TypedDict

from ..api import AgentError, FeatureValue, PolicyArtifact, PolicyInput, validate_policy
from ..api.primitives.errors import ValidationError as PolicyError
from ..api.primitives.interpreter import PolicyDecision
from ..api.primitives.interpreter import evaluate_policy as interpret
from ..store import digest
from .qualification import replay_quality
from .returned_models import LearningEvidence, ReturnedFeedback
from .timings import measured_timings


class DecisionRecord(TypedDict):
    query_id: str
    group: str
    stratum: str
    status: str
    checkpoint_index: int | None
    recall_delta: float | None
    work: int
    source_ref: str | None
    earliest_measured_preserving_checkpoint: int | None
    avoidable_work_against_measured_preserving_stop: int | None
    error: NotRequired[str]


def referenced_features(root) -> set[str]:
    if not isinstance(root, dict):
        return set()
    result = {root["feature"]} if "feature" in root else set()
    for value in root.values():
        if isinstance(value, dict):
            result.update(referenced_features(value))
        elif isinstance(value, list):
            for item in value:
                result.update(referenced_features(item))
    return result


def decision_depth(node) -> int:
    return (
        0
        if isinstance(node, str)
        else 1 + max(decision_depth(node["then"]), decision_depth(node["else"]))
    )


class OfflineEvaluator:
    """Replay decisions only; unknown stopped recall and latency stay unknown."""

    def __init__(self, corpus: LearningEvidence):
        # Own a validated copy so caller mutations cannot silently change cached identity.
        self.evidence = type(corpus).model_validate_json(corpus.model_dump_json())
        self.corpus = (
            self.evidence.corpus if isinstance(self.evidence, ReturnedFeedback) else self.evidence
        )
        self.benchmark = (
            self.evidence.benchmark if isinstance(self.evidence, ReturnedFeedback) else None
        )
        self.evidence_hash = self.evidence.evidence_hash
        self.float_features = frozenset(
            n for n, f in self.corpus.profile.runtime_features.items() if f.kind == "float"
        )

    def validate(self, raw: dict | PolicyArtifact) -> PolicyArtifact:
        if not isinstance(raw, (dict, PolicyArtifact)):
            raise AgentError("candidate policy must be an object")
        if isinstance(raw, dict):
            raw = {"feature_groups": self.corpus.collection_groups, **raw}
        groups = (
            raw.feature_groups if isinstance(raw, PolicyArtifact) else raw.get("feature_groups")
        )
        if groups != self.corpus.collection_groups:
            raise AgentError("candidate must retain the corpus collection groups")
        policy = validate_policy(raw, self.corpus.profile)
        if policy.feature_groups != self.corpus.collection_groups:
            raise AgentError("candidate must retain the corpus collection groups")
        if referenced_features(policy.root).difference(self.corpus.qualified_features):
            raise AgentError("candidate references a feature without native qualification")
        if decision_depth(policy.root) > self.corpus.objective.maximum_decision_depth:
            raise AgentError("candidate exceeds the study decision depth")
        return policy

    def evaluate(
        self,
        raw: dict | PolicyArtifact,
        *,
        maximum_examples: int = 20,
        groups: list[str] | None = None,
    ) -> dict:
        if type(maximum_examples) is not int or not 1 <= maximum_examples <= 100:
            raise AgentError("maximum_examples must be between 1 and 100")
        policy = self.validate(raw)
        names = referenced_features(policy.root)
        selected_groups = {q.group for q in self.corpus.queries}
        if groups is not None:
            if not groups or len(set(groups)) != len(groups) or set(groups) - selected_groups:
                raise AgentError("evaluation groups must be a unique training subset")
            selected_groups = set(groups)
        rows: list[DecisionRecord] = []
        requests = []
        for query in self.corpus.queries:
            if query.group not in selected_groups:
                continue
            selected, error = None, None
            for checkpoint in query.checkpoints:
                inputs = PolicyInput(
                    features={
                        n: FeatureValue(
                            available=checkpoint.features[n] is not None,
                            value=checkpoint.features[n],
                        )
                        for n in names
                    }
                )
                try:
                    decision = interpret(policy, inputs, float_features=self.float_features)
                except PolicyError as exc:
                    selected, error = checkpoint, str(exc)
                    break
                if decision == PolicyDecision.STOP:
                    selected = checkpoint
                    break
            label = next(
                (
                    outcome
                    for outcome in query.outcomes
                    if selected and (outcome.checkpoint_index == selected.checkpoint_index)
                ),
                None,
            )
            if error:
                status, recall_delta = "runtime_error", None
            elif selected is None:
                status, recall_delta = "continued", 0.0
            elif label is None:
                status, recall_delta = "unknown_stop", None
            elif not label.valid or label.returned_count != query.effective_k:
                status, recall_delta = "invalid_result", label.recall - query.native_recall
            elif label.recall < query.native_recall:
                status, recall_delta = "measured_recall_loss", label.recall - query.native_recall
            else:
                status, recall_delta = "measured_preserving", label.recall - query.native_recall
            preserving = [
                outcome
                for outcome in query.outcomes
                if outcome.valid
                and outcome.returned_count == query.effective_k
                and outcome.recall >= query.native_recall
            ]
            earliest = (
                min(preserving, key=lambda outcome: outcome.checkpoint_index)
                if preserving
                else None
            )
            work = selected.features[self.corpus.work_feature] if selected else query.native_work
            if type(work) is not int:
                raise AgentError("verified work counter is no longer an integer")
            row: DecisionRecord = {
                "query_id": query.query_id,
                "group": query.group,
                "stratum": query.stratum,
                "status": status,
                "checkpoint_index": selected.checkpoint_index if selected else None,
                "recall_delta": recall_delta,
                "work": work,
                "source_ref": label.source_ref if label and not error else None,
                "earliest_measured_preserving_checkpoint": (
                    earliest.checkpoint_index if earliest else None
                ),
                "avoidable_work_against_measured_preserving_stop": (
                    max(0, work - earliest.actual_work) if earliest and not error else None
                ),
            }
            if error:
                row["error"] = error
            if status == "unknown_stop":
                assert selected is not None
                requests.append(
                    {
                        "query_id": query.query_id,
                        "group": query.group,
                        "stratum": query.stratum,
                        "checkpoint_index": selected.checkpoint_index,
                        "reason": "candidate first stop has no measured outcome",
                    }
                )
            rows.append(row)

        def summary(selected: list[DecisionRecord]):
            deltas = [delta for r in selected if (delta := r["recall_delta"]) is not None]
            return {
                "queries": len(selected),
                "independent_groups": len({r["group"] for r in selected}),
                "counts": dict(sorted(Counter(r["status"] for r in selected).items())),
                "observed_quality_queries": len(deltas),
                "quality_coverage_complete": len(deltas) == len(selected),
                "mean_observed_recall_delta": (sum(deltas) / len(deltas) if deltas else None),
                "mean_predicted_work": sum(r["work"] for r in selected) / len(selected),
                "work_is_latency": False,
            }

        timings = {
            regime: (
                measured_timings(self.corpus, policy.policy_hash, regime, self.benchmark)
                if groups is None
                else {"status": "group_subset", "training_feasible": None}
            )
            for regime in ("activation-cold", "reused-warm")
        }
        failures = [
            r
            for r in rows
            if r["status"] in {"runtime_error", "invalid_result", "measured_recall_loss"}
        ]
        continuation = sorted(
            [r for r in rows if (r["avoidable_work_against_measured_preserving_stop"] or 0) > 0],
            key=lambda r: -(r["avoidable_work_against_measured_preserving_stop"] or 0),
        )
        report = {
            "schema_version": 1,
            "format": "fannagent.learning.assessment.v1",
            "scope": "learning",
            "policy_hash": policy.policy_hash,
            "evidence_hash": self.evidence_hash,
            "runtime_profile_hash": self.corpus.profile.fingerprint,
            "evaluated_groups": sorted(selected_groups),
            "objective": self.corpus.objective.model_dump(mode="json"),
            "overall": summary(rows),
            "per_filter": {
                s: summary([r for r in rows if r["stratum"] == s])
                for s in sorted({r["stratum"] for r in rows})
            },
            "decisions": rows,
            "measurement_requests": requests,
            "timings": timings,
            "learning_qualification": replay_quality(self.corpus, rows, timings),
            "feedback": {
                "measured_failures": failures[:maximum_examples],
                "unknown_stops": requests[:maximum_examples],
                "unnecessary_continuation_examples": continuation[:maximum_examples],
                "interpretation": (
                    "Per-query recall loss is a diagnostic, not aggregate rejection. "
                    "Unmeasured recall and latency remain unknown. Earliest measured "
                    "preserving stops are retrospective references, not proven optima."
                ),
            },
            "canonical_acceptance_established": False,
        }
        return {**report, "assessment_hash": digest(report)}
