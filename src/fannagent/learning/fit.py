"""A deterministic same-feature CART baseline trained only on measured outcomes."""

from __future__ import annotations

import math

import numpy as np
from pydantic import Field

from ..api import AgentError
from ..store import digest
from .evaluate import OfflineEvaluator, referenced_features
from .models import Record


class FitConfig(Record):
    depth: int = Field(default=2, ge=1, le=3)
    minimum_leaf_groups: int = Field(default=8, ge=1)
    risk_weight: float = Field(default=20.0, gt=0, le=10000)
    folds: int = Field(default=5, ge=2, le=10)
    seed: int = Field(default=20261019, ge=0)


def _tree(X, y, weight, groups, names, kinds, config):
    def build(indices, depth):
        total = float(weight[indices].sum())
        positive = float((weight[indices] * y[indices]).sum())
        leaf = "stop" if positive > total / 2 else "continue"
        if not depth or len(set(groups[indices])) < 2 * config.minimum_leaf_groups:
            return leaf

        def impurity(p, w):
            return 2 * p * (w - p) / w if w else 0.0

        best = None
        for column, name in enumerate(names):
            values = X[indices, column]
            thresholds = (
                [0.5]
                if kinds[name] == "bool"
                else np.unique(np.quantile(values, np.linspace(0.05, 0.95, 13)))
            )
            for threshold in thresholds:
                if kinds[name] == "int":
                    threshold = math.ceil(threshold)
                mask = values >= threshold
                if any(
                    len(set(groups[indices[m]])) < config.minimum_leaf_groups for m in (mask, ~mask)
                ):
                    continue
                right = float(weight[indices[mask]].sum())
                right_positive = float((weight[indices[mask]] * y[indices[mask]]).sum())
                score = impurity(right_positive, right) + impurity(
                    positive - right_positive, total - right
                )
                if best is None or score < best[0] - 1e-12:
                    best = (score, column, threshold, mask)
        if best is None or best[0] >= impurity(positive, total) - 1e-12:
            return leaf
        _, column, threshold, mask = best
        high, low = build(indices[mask], depth - 1), build(indices[~mask], depth - 1)
        if isinstance(high, str) and high == low:
            return high
        kind = kinds[names[column]]
        literal = (
            {"bool": True}
            if kind == "bool"
            else ({"int": int(threshold)} if kind == "int" else {"float": float(threshold)})
        )
        return {
            "if": {
                "op": "eq" if kind == "bool" else "gte",
                "args": [{"feature": names[column]}, literal],
            },
            "then": high,
            "else": low,
        }

    return build(np.arange(len(y)), config.depth)


def _guard(root):
    names = sorted(referenced_features(root))
    if not names:
        return root

    def conjunction(items):
        if len(items) == 1:
            return items[0]
        middle = len(items) // 2
        return {"op": "and", "args": [conjunction(items[:middle]), conjunction(items[middle:])]}

    return {
        "if": conjunction([{"op": "is_available", "args": [{"feature": n}]} for n in names]),
        "then": root,
        "else": "continue",
    }


def fit_policy(evaluator: OfflineEvaluator, config: FitConfig | None = None) -> dict:
    config = config or FitConfig()
    corpus = evaluator.corpus
    if config.depth + 1 > corpus.objective.maximum_decision_depth:
        raise AgentError("fitter depth plus its availability guard exceeds the study limit")
    group_ids = sorted({q.group for q in corpus.queries}, key=lambda g: digest([config.seed, g]))
    if len(group_ids) < config.folds:
        raise AgentError("fitter needs at least one independent group per fold")
    folds = {g: index % config.folds for index, g in enumerate(group_ids)}
    names = sorted(corpus.qualified_features)
    kinds = {n: corpus.profile.runtime_features[n].kind for n in names}
    X, y, weights, groups = [], [], [], []
    group_sizes = {g: sum(q.group == g for q in corpus.queries) for g in group_ids}
    skipped = 0
    for query in corpus.queries:
        for outcome in query.outcomes:
            values = query.checkpoints[outcome.checkpoint_index - 1].features
            if any(values[n] is None for n in names):
                skipped += 1
                continue
            for name in names:
                value = values[name]
                if kinds[name] == "int" and isinstance(value, int) and value > 2**53:
                    raise AgentError(
                        "baseline float matrix cannot exactly represent this int64 feature"
                    )
            preserves = (
                outcome.valid
                and outcome.returned_count == query.effective_k
                and outcome.recall >= query.native_recall
            )
            scale = 1 / (group_sizes[query.group] * len(query.outcomes))
            benefit = max(0.005, 1 - outcome.actual_work / max(1, query.native_work))
            cost = config.risk_weight * max(0.1, query.native_recall - outcome.recall)
            if not outcome.valid or outcome.returned_count != query.effective_k:
                cost = config.risk_weight
            X.append([values[n] for n in names])
            y.append(float(preserves))
            weights.append(scale * (benefit if preserves else cost))
            groups.append(query.group)
    if not y:
        raise AgentError("no fully observed measured labels for fitting")
    matrix, target, weight = np.asarray(X, float), np.asarray(y), np.asarray(weights)
    group_array = np.asarray(groups)

    def fit(mask):
        if not np.any(mask):
            raise AgentError("cross-validation fold has no measured training labels")
        root = _tree(
            matrix[mask], target[mask], weight[mask], group_array[mask], names, kinds, config
        )
        return evaluator.validate(
            {
                "name": "measured-cart-" + digest(config.model_dump(mode="json"))[:12],
                "root": _guard(root),
                "feature_groups": corpus.collection_groups,
            }
        )

    cv = []
    for fold in range(config.folds):
        training = [g for g in group_ids if folds[g] != fold]
        held_out = [g for g in group_ids if folds[g] == fold]
        artifact = fit(np.asarray([folds[g] != fold for g in groups]))
        report = evaluator.evaluate(artifact, groups=held_out)
        cv.append(
            {
                "fold": fold,
                "training_groups": training,
                "held_out_groups": held_out,
                "policy_hash": artifact.policy_hash,
                "overall": report["overall"],
                "per_filter": report["per_filter"],
                "assessment_hash": report["assessment_hash"],
            }
        )
    artifact = fit(np.ones(len(y), dtype=bool))
    return {
        "schema_version": 1,
        "format": "fannagent.learning.fit.v1",
        "scope": "learning",
        "policy": artifact.serialize(),
        "policy_hash": artifact.policy_hash,
        "evidence_hash": evaluator.evidence_hash,
        "configuration": config.model_dump(mode="json"),
        "group_folds": folds,
        "cross_validation": cv,
        "measured_labels_used": len(y),
        "labels_skipped_for_missing_features": skipped,
        "proposal_target": "measured per-query native-preserving stops; not aggregate acceptance",
        "canonical_acceptance_established": False,
    }
