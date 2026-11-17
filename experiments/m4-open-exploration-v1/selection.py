"""The existing quality/interval certificate, generalized to any registry size."""

import math

from fannproto.policy import FILTERS
from fannproto.uncertainty import ESTIMATE_STATUS, SCHEMA


def select_shortlist(records):
    admitted, excluded, hashes = {}, {}, set()
    for record in sorted(records, key=lambda r: r["candidate_id"]):
        cid = record["candidate_id"]
        if record.get("nominee_role", "policy") != "policy":
            excluded[cid] = "control_not_a_learned_stopping_nominee"
            continue
        if not record.get("evaluation", {}).get("quality_preserves_raw_native640"):
            excluded[cid] = "quality_or_structure_not_qualified"
            continue
        if record["rule_hash"] in hashes:
            excluded[cid] = "duplicate_canonical_policy"
            continue
        hashes.add(record["rule_hash"])
        estimate = record.get("cost_estimate") or {}
        if estimate.get("status") != ESTIMATE_STATUS:
            excluded[cid] = "uncertainty_estimate_unsupported"
            continue
        if not any(
            record["evaluation"]["per_filter"].get(f, {}).get("stops", 0) > 0
            for f in FILTERS
            if f != "unfiltered"
        ):
            excluded[cid] = "no_scalar_early_stops_on_development"
            continue
        low, high = estimate["primary_ratio_interval"]
        if not all(math.isfinite(x) for x in (low, high)) or not 0 <= low <= high:
            raise ValueError("finite ordered cost interval required")
        admitted[cid] = record

    intervals = {cid: r["cost_estimate"]["primary_ratio_interval"] for cid, r in admitted.items()}
    ordered = sorted(admitted, key=lambda cid: (intervals[cid][0], cid))
    complexity = {}
    for cid, record in admitted.items():
        clauses = [c for values in record["policy"]["rules"].values() for c in values]
        complexity[cid] = (sum(len(c["conditions"]) for c in clauses), len(clauses))

    # For any subset S of <=3 nominees, let j be the position of its first
    # excluded policy in lower-bound order. S contains that entire prefix.
    # Besides the prefix, only the selected policy with the smallest upper bound
    # can improve the regret bound. Removing any other member preserves the bound
    # and wins the existing preference for fewer nominees. Thus prefix + <=1
    # anchor includes every possible winning subset. This is O(n log n), with
    # O(n) bounded-size subset checks, rather than enumerating O(n^3) subsets.
    best, best_bound = None, float("inf")
    for j in range(min(3, len(ordered)) + 1):
        prefix = ordered[:j]
        excluded_low = min(1.0, intervals[ordered[j]][0]) if j < len(ordered) else 1.0
        anchors = [None]
        if j < 3:
            anchors.extend(ordered[j + 1 :])
        for anchor in anchors:
            selected = sorted(prefix + ([] if anchor is None else [anchor]))
            upper = min([1.0, *(intervals[cid][1] for cid in selected)])
            bound = max(0.0, upper - excluded_low)
            best_bound = min(best_bound, bound)
            if bound > 0.01 + 1e-12:
                continue
            key = (
                len(selected),
                bound,
                sum(complexity[cid][0] for cid in selected),
                sum(complexity[cid][1] for cid in selected),
                tuple(sorted(admitted[cid]["rule_hash"] for cid in selected)),
            )
            if best is None or (key, selected) < best:
                best = (key, selected)

    result = {
        "schema": SCHEMA,
        "max_live_nominees": 3,
        "regret_limit": 0.01,
        "admissible_intervals": intervals,
        "exclusions": excluded,
        "certificate_universe": "Quality-preserving supported policies with scalar stops, "
        "plus native. Assumes costs in engineering envelopes and ideal M5 choice; excludes "
        "future measurement/allocation noise and unsupported programs.",
        "no_performance_promotion": True,
    }
    if best is None:
        return {
            **result,
            "status": "abstain_uncertainty_exceeds_cap",
            "candidate_ids": [],
            "conditional_regret_bound": None,
            "best_attainable_bound": best_bound,
        }
    key, selected = best
    return {
        **result,
        "status": "selected_for_M5" if selected else "certified_native_abstention",
        "candidate_ids": selected,
        "conditional_regret_bound": key[1],
        "best_attainable_bound": best_bound,
    }
