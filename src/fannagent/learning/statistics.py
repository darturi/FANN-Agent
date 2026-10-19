"""Host-controlled vector-cluster summaries shared by replay and returned-data checks."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from ..evaluation import bootstrap
from .models import LearningObjective


def cluster_summary(rows, query_groups: dict[str, str], objective: LearningObjective) -> dict:
    grouped = defaultdict(list)
    for row in rows:
        grouped[query_groups[row.query_id]].append(row)
    if not grouped:
        raise ValueError("cannot summarize an empty measurement set")
    values = np.asarray(
        [
            [
                np.mean([r.policy_ms - r.native_ms for r in rs]),
                np.mean([r.policy_outer_ms - r.native_outer_ms for r in rs]),
                np.mean([r.policy_recall - r.native_recall for r in rs]),
                np.mean([math.log(r.policy_ms / r.native_ms) for r in rs]),
            ]
            for rs in grouped.values()
        ]
    )
    # Preserve first-seen vector order and the declared random stream. Each vector
    # is sampled once across all repetitions, filter variants and allocations.
    intervals = [
        bootstrap(values[:, i].tolist(), objective.seed, objective.bootstrap_samples)
        for i in range(4)
    ]
    enough = len(grouped) >= objective.minimum_groups

    def mean(fn):
        return float(np.mean([fn(r) for r in rows]))

    return {
        "pairs": len(rows),
        "independent_vectors": len(grouped),
        "native_ms": mean(lambda r: r.native_ms),
        "policy_ms": mean(lambda r: r.policy_ms),
        "gap_ms": float(values[:, 0].mean()),
        "gap_ci95": intervals[0],
        "outer_gap_ms": float(values[:, 1].mean()),
        "outer_gap_ci95": intervals[1],
        "recall_delta": float(values[:, 2].mean()),
        "recall_delta_ci95": intervals[2],
        "log_latency_ratio_ci95": intervals[3],
        "native_recall": mean(lambda r: r.native_recall),
        "policy_recall": mean(lambda r: r.policy_recall),
        "returned_count": mean(lambda r: r.returned_count),
        "collection_ms": mean(lambda r: r.work.get("feature_collection_ns", 0) / 1e6),
        "layer0_distances": mean(lambda r: r.work["layer0_distance_evaluations"]),
        "all_valid": all(r.valid for r in rows),
        "recall_noninferior": bool(
            enough and intervals[2] and intervals[2][0] >= -objective.recall_tolerance
        ),
        "latency_improved": bool(enough and intervals[3] and intervals[3][1] < 0),
    }


def with_filters(rows, queries, objective):
    groups = {q.query_id: q.group for q in queries}
    strata = {q.query_id: q.stratum for q in queries}
    return {
        "overall": cluster_summary(rows, groups, objective),
        "per_filter": {
            s: cluster_summary([r for r in rows if strata[r.query_id] == s], groups, objective)
            for s in sorted(set(strata.values()))
        },
    }


def feasible(report: dict, objective: LearningObjective) -> bool:
    overall = report["overall"]
    return bool(
        overall["all_valid"]
        and overall["recall_noninferior"]
        and overall["latency_improved"]
        and all(
            r["all_valid"]
            and r["recall_noninferior"]
            and r["native_recall"] >= objective.minimum_native_recall
            for r in report["per_filter"].values()
        )
    )


def compare_numeric(expected, actual, *, tolerance=1e-12, path="") -> list[dict]:
    """Exact structure/discrete values; finite floating results allow only roundoff."""
    differences = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            raise ValueError("scorer parity structure differs: " + path)
        for key in expected:
            differences.extend(
                compare_numeric(
                    expected[key], actual[key], tolerance=tolerance, path=path + "/" + str(key)
                )
            )
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            raise ValueError("scorer parity list differs: " + path)
        for i, (left, right) in enumerate(zip(expected, actual)):
            differences.extend(
                compare_numeric(left, right, tolerance=tolerance, path=path + "/" + str(i))
            )
    elif type(expected) is float:
        if type(actual) is not float or not math.isfinite(expected) or not math.isfinite(actual):
            raise ValueError("scorer parity finite number differs: " + path)
        error = abs(expected - actual)
        if error > tolerance:
            raise ValueError("scorer parity exceeds roundoff tolerance: " + path)
        if error:
            differences.append({"path": path, "absolute_error": error})
    elif type(expected) is not type(actual) or expected != actual:
        raise ValueError("scorer parity value differs: " + path)
    return differences
