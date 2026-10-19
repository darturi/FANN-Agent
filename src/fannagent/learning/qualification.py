"""Aggregate development qualification, distinct from conservative proposal labels."""

from collections import defaultdict

import numpy as np

from ..evaluation import bootstrap


def replay_quality(corpus, decisions, timings):
    by_query = {q.query_id: q for q in corpus.queries}
    objective = corpus.objective

    def summarize(rows):
        complete = all(r["recall_delta"] is not None for r in rows)
        valid = all(r["status"] not in ("invalid_result", "runtime_error") for r in rows)
        groups = defaultdict(list)
        for row in rows:
            if row["recall_delta"] is not None:
                groups[row["group"]].append(row["recall_delta"])
        values = [float(np.mean(rs)) for rs in groups.values()]
        interval = (
            bootstrap(
                values,
                objective.seed,
                objective.bootstrap_samples,
                [len(rs) for rs in groups.values()],
            )
            if complete
            else None
        )
        native = float(np.mean([by_query[r["query_id"]].native_recall for r in rows]))
        return {
            "queries": len(rows),
            "independent_groups": len({r["group"] for r in rows}),
            "quality_coverage_complete": complete,
            "all_valid_complete": valid and complete,
            "recall_delta_ci95": interval,
            "mean_native_recall": native,
            "recall_noninferior": bool(
                complete
                and valid
                and len(groups) >= objective.minimum_groups
                and interval
                and interval[0] >= -objective.recall_tolerance
            ),
            "native_floor_passed": native >= objective.minimum_native_recall,
        }

    overall = summarize(decisions)
    filters = {
        s: summarize([r for r in decisions if r["stratum"] == s])
        for s in sorted({r["stratum"] for r in decisions})
    }
    replay_passed = overall["recall_noninferior"] and all(
        r["recall_noninferior"] and r["native_floor_passed"] for r in filters.values()
    )
    # Full measured policy executions can establish quality even when a reusable
    # trace-verified StopOutcome has not yet been acquired for fitting.
    measured = [
        result.get("report", result)
        for result in timings.values()
        if result.get("status") == "measured"
    ]

    def measured_quality(report):
        main = report["overall"]
        return (
            main.get("all_valid_complete", main.get("all_valid", False))
            and main["recall_noninferior"]
            and all(
                r.get("all_valid_complete", r.get("all_valid", False))
                and r["recall_noninferior"]
                and r.get("mean_native_recall", r.get("native_recall", 0))
                >= objective.minimum_native_recall
                for r in report["per_filter"].values()
            )
        )

    unknown = sum(r["status"] == "unknown_stop" for r in decisions)
    invalid = any(r["status"] in ("runtime_error", "invalid_result") for r in decisions)
    passed = all(measured_quality(r) for r in measured) if measured else replay_passed
    passed = passed and not invalid
    status = (
        "invalid"
        if invalid
        else "needs_actual_outcomes"
        if unknown and not measured
        else "ready_for_timing"
        if passed
        else "quality_not_established"
    )
    return {
        "scope": "learning",
        "status": status,
        "aggregate_quality_passed": bool(passed),
        "quality_source": "measured_policy_executions" if measured else "trace_verified_outcomes",
        "replay_quality_passed": bool(replay_passed),
        "per_query_loss_count": sum(r["status"] == "measured_recall_loss" for r in decisions),
        "unknown_stops": unknown,
        "overall": overall,
        "per_filter": filters,
        "regimes": {
            regime: {
                "status": (
                    "training_feasible"
                    if passed and result.get("training_feasible") is True
                    else "measured_rejection"
                    if result.get("training_feasible") is False
                    else "measurement_required"
                ),
                "training_feasible": bool(passed and result.get("training_feasible") is True),
            }
            for regime, result in timings.items()
        },
        "per_query_loss_is_unconditional_rejection": False,
        "canonical_acceptance_established": False,
    }
