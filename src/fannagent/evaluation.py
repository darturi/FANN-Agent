from __future__ import annotations

import math

import numpy as np

from .contracts import ExactTruth, ProbeResult


def score(truth: ExactTruth, result: ProbeResult) -> dict:
    ids = result.ids
    duplicates = len(ids) - len(set(ids))
    violations = len(set(ids) - truth.eligible_ids)
    strict = len(set(ids) & truth.strictly_better)
    slots = truth.effective_k - len(truth.strictly_better)
    boundary = min(slots, len(set(ids) & truth.boundary_ties))
    recall = (strict + boundary) / truth.effective_k if truth.effective_k else None
    return {
        "recall": recall,
        "valid": not duplicates and not violations and len(ids) <= truth.effective_k,
        "duplicate_count": duplicates,
        "predicate_violation_count": violations,
        "returned_count": len(ids),
    }


def bootstrap(
    values: list[float], seed: int, count: int, weights: list[int] | None = None
) -> list[float] | None:
    if len(values) < 2:
        return None
    array = np.asarray(values)
    weight = np.ones(len(array)) if weights is None else np.asarray(weights, dtype=float)
    rng = np.random.default_rng(seed)
    means = []
    for start in range(0, count, 128):
        indices = rng.integers(0, len(array), size=(min(128, count - start), len(array)))
        selected_weights = weight[indices]
        means.extend(
            (
                (array[indices] * selected_weights).sum(axis=1) / selected_weights.sum(axis=1)
            ).tolist()
        )
    return np.quantile(means, [0.025, 0.975]).tolist()


def summarize(rows: list[dict], *, seed: int, samples: int, minimum: int, tolerance: float) -> dict:
    reports = {}
    for group in ("overall", "easy", "hard"):
        selected = [r for r in rows if group == "overall" or r.get("hardness") == group]
        by_group = {}
        for row in selected:
            by_group.setdefault(row["group"], []).append(row)
        differences, ratios = [], []
        difference_weights, ratio_weights = [], []
        for members in by_group.values():
            known = [r for r in members if r.get("recall_delta") is not None]
            if known:
                differences.append(float(np.mean([r["recall_delta"] for r in known])))
                difference_weights.append(len(known))
            timed = [
                r
                for r in members
                if (r.get("native_ms") or 0) > 0 and (r.get("policy_ms") or 0) > 0
            ]
            if timed:
                ratios.append(
                    float(np.mean([math.log(r["policy_ms"] / r["native_ms"]) for r in timed]))
                )
                ratio_weights.append(len(timed))
        recall_ci = bootstrap(differences, seed, samples, difference_weights)
        latency_ci = bootstrap(ratios, seed, samples, ratio_weights)
        reports[group] = {
            "independent_groups": len(differences),
            "mean_recall_delta": float(np.average(differences, weights=difference_weights))
            if differences
            else None,
            "recall_delta_ci95": recall_ci,
            "log_latency_ratio_ci95": latency_ci,
            "recall_noninferior": bool(
                len(differences) >= minimum and recall_ci and recall_ci[0] >= -tolerance
            ),
            "latency_improved": bool(len(ratios) >= minimum and latency_ci and latency_ci[1] < 0),
            "recall_assessment": ("inconclusive" if len(differences) < minimum else "conclusive"),
            "latency_assessment": "inconclusive" if len(ratios) < minimum else "conclusive",
        }
    correct = bool(rows) and all(r.get("valid", False) for r in rows)
    accepted = correct and all(reports[g]["recall_noninferior"] for g in reports)
    accepted = accepted and reports["easy"]["latency_improved"]
    latencies = {}
    for mode in ("native", "policy"):
        values = [r[f"{mode}_ms"] for r in rows if r.get(f"{mode}_ms") is not None]
        latencies[mode] = {
            "median_ms": float(np.median(values)) if values else None,
            "p95_ms": float(np.quantile(values, 0.95)) if values else None,
            "sample_count": len(values),
        }
    return {
        "status": "accepted" if accepted else "no_recommendation",
        "valid": correct,
        "groups": reports,
        "latencies": latencies,
        "recall_tolerance": tolerance,
        "regressed_pairs": sum((r.get("recall_delta") or 0) < 0 for r in rows),
        "failed_pairs": sum(not r.get("valid", False) for r in rows),
        "pair_count": len(rows),
        "per_query_regressions": [
            {
                "id": identifier,
                "mean_recall_delta": float(np.mean([r["recall_delta"] for r in members])),
                "mean_latency_ratio": float(
                    np.mean([r["policy_ms"] / r["native_ms"] for r in members])
                ),
            }
            for identifier, members in _query_groups(rows).items()
            if members
            and (
                np.mean([r["recall_delta"] for r in members]) < 0
                or np.mean([r["policy_ms"] / r["native_ms"] for r in members]) > 1
            )
        ],
    }


def _query_groups(rows):
    groups = {}
    for row in rows:
        if (
            row.get("recall_delta") is not None
            and (row.get("native_ms") or 0) > 0
            and (row.get("policy_ms") or 0) > 0
        ):
            groups.setdefault(row.get("id", row["group"]), []).append(row)
    return groups
