"""Training-only qualification from complete measured pairs, grouped by vector."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from ..evaluation import bootstrap
from .models import FeedbackCorpus


def measured_timings(corpus: FeedbackCorpus, policy_hash: str, regime: str) -> dict:
    pairs = [p for p in corpus.timings if p.policy_hash == policy_hash and p.regime == regime]
    schedule = corpus.timing_schedule
    if schedule is None:
        return {"status": "unmeasured", "training_feasible": None, "pairs": 0}
    passes = schedule.cold_passes if regime == "activation-cold" else schedule.warm_passes
    # Corpus validation proves uniqueness and membership in the schedule.
    # Cardinality proves coverage without allocating the schedule's Cartesian product.
    expected = len(corpus.queries) * len(schedule.blocks) * passes
    if len(pairs) != expected:
        return {
            "status": "incomplete",
            "training_feasible": None,
            "pairs": len(pairs),
            "expected_pairs": expected,
            "missing_pairs": expected - len(pairs),
        }
    queries = {q.query_id: q for q in corpus.queries}
    objective = corpus.objective

    def summarize(selected):
        by_query = defaultdict(list)
        for pair in selected:
            by_query[pair.query_id].append(pair)
        groups = defaultdict(list)
        for query_id, rows in by_query.items():
            groups[queries[query_id].group].append(
                (
                    float(np.mean([p.policy_recall - p.native_recall for p in rows])),
                    float(np.mean([math.log(p.policy_ms) - math.log(p.native_ms) for p in rows])),
                    float(np.mean([p.policy_ms - p.native_ms for p in rows])),
                )
            )
        values = [np.mean(rows, axis=0) for rows in groups.values()]
        weights = [len(rows) for rows in groups.values()]
        intervals = [
            bootstrap(
                [float(v[column]) for v in values],
                objective.seed,
                objective.bootstrap_samples,
                weights,
            )
            for column in range(3)
        ]
        enough = len(groups) >= objective.minimum_groups
        native = float(np.mean([p.native_recall for p in selected]))
        return {
            "independent_groups": len(groups),
            "pairs": len(selected),
            "mean_recall_delta": float(np.average([v[0] for v in values], weights=weights)),
            "mean_latency_gap_ms": float(np.average([v[2] for v in values], weights=weights)),
            "recall_delta_ci95": intervals[0],
            "log_latency_ratio_ci95": intervals[1],
            "latency_gap_ci95_ms": intervals[2],
            "mean_native_recall": native,
            "all_valid_complete": all(
                p.valid and p.returned_count == queries[p.query_id].effective_k for p in selected
            ),
            "recall_noninferior": bool(
                enough and intervals[0] and intervals[0][0] >= -objective.recall_tolerance
            ),
            "latency_improved": bool(enough and intervals[1] and intervals[1][1] < 0),
            "native_floor_passed": native >= objective.minimum_native_recall,
            "assessment": "conclusive" if enough else "inconclusive",
        }

    strata = sorted({q.stratum for q in corpus.queries})
    overall = summarize(pairs)
    per_filter = {
        s: summarize([p for p in pairs if queries[p.query_id].stratum == s]) for s in strata
    }
    feasible = overall["all_valid_complete"] and overall["recall_noninferior"]
    feasible = (
        feasible
        and overall["latency_improved"]
        and all(
            r["all_valid_complete"] and r["recall_noninferior"] and r["native_floor_passed"]
            for r in per_filter.values()
        )
    )
    return {
        "status": "measured",
        "training_feasible": bool(feasible),
        "pairs": len(pairs),
        "overall": overall,
        "per_filter": per_filter,
        "per_block": {
            str(b): summarize([p for p in pairs if p.block == b]) for b in schedule.blocks
        },
        "scope": "training only; no confirmation or serving acceptance",
    }
