"""Engineering envelopes and bounded M5 experiment selection, with explicit abstention."""

import itertools
import math

from .costmodel import features, operations
from .policy import FILTERS, POINTS, PROFILE, observation_plan

COST_STATUS = "qualified_uncertainty_shortlist_v1"
ESTIMATE_STATUS = "supported_uncertainty_shortlist_proxy"
SCHEMA = "filtered-ann.uncertainty-shortlist.v1"


def validate_contract(contract):
    if (
        contract.get("schema") != SCHEMA
        or contract.get("runtime_profile") != PROFILE.fingerprint
        or contract.get("status") != "qualified_conditional_experiment_selection"
        or contract.get("point_model_precision_qualified") is not False
        or contract.get("max_live_nominees") != 3
        or contract.get("regret_limit") != 0.01
        or not 0.01 <= contract.get("error_radius", -1) <= 0.05
        or len(contract.get("qualification_receipt_sha256", "")) != 64
        or set(contract.get("fold_models", {})) != set(map(str, range(5)))
        or set(contract.get("supported_masks", {})) != set(FILTERS)
    ):
        raise ValueError("qualified uncertainty shortlist contract required")
    for fold in contract["fold_models"].values():
        if set(fold) != set(FILTERS):
            raise ValueError("complete per-filter proxy required")
        for coefficients in fold.values():
            if len(coefficients) != 5 or not all(math.isfinite(x) for x in coefficients):
                raise ValueError("finite signed coefficients required")


def proxy_values(policy, rows, contract, *, force_continue=False):
    """Return per-row proxy ratios or a bounded unsupported reason; no label enters decisions."""
    plan = observation_plan(policy)
    for f in FILTERS:
        for cp in POINTS:
            if plan[f][str(cp)] not in contract["supported_masks"][f][str(cp)]:
                return None, {
                    "reason": "unsupported_observation_mask",
                    "filter": f,
                    "checkpoint": cp,
                }
    values = []
    for row in rows:
        _, counts = operations(policy, row, force_continue=force_continue)
        costs = row["costs"]
        for cp, comparisons in zip(POINTS, counts["comparison"], strict=True):
            if comparisons > costs["comparison_caps"].get(str(cp), 0):
                return None, {
                    "reason": "numeric_comparisons_exceed_measured_support",
                    "filter": row["filter"],
                    "checkpoint": cp,
                    "anonymous_group": row["group"],
                }
        base, additive, _ = features(policy, row, costs, force_continue=force_continue)
        coefficients = contract["fold_models"][str(row["fold"])][row["filter"]]
        value = base + sum(a * b for a, b in zip(additive, coefficients, strict=True))
        if not math.isfinite(value) or value <= 0:
            return None, {"reason": "nonpositive_or_nonfinite_proxy", "filter": row["filter"]}
        values.append(value)
    return values, None


def proxy_estimate(policy, rows, contract, *, force_continue=False):
    values, unsupported = proxy_values(policy, rows, contract, force_continue=force_continue)
    if unsupported:
        return {"status": "unsupported_uncertainty_estimate", **unsupported}
    totals = {f: [0.0, 0.0] for f in FILTERS}
    for row, value in zip(rows, values, strict=True):
        reference = row["costs"]["reference_native_ms"]
        totals[row["filter"]][0] += value * reference
        totals[row["filter"]][1] += reference
    if any(v[1] <= 0 for v in totals.values()):
        raise ValueError("all seven conditions required")
    radius = contract["error_radius"]

    def interval(center):
        # Intersection with the physical nonnegative domain, never clipping fitted components.
        return [max(0.0, center - radius), center + radius]

    center = sum(v[0] for f, v in totals.items() if f != "unfiltered") / sum(
        v[1] for f, v in totals.items() if f != "unfiltered"
    )
    return {
        "status": ESTIMATE_STATUS,
        "primary_ratio_proxy": center,
        "primary_ratio_interval": interval(center),
        "per_filter": {
            f: {"ratio_proxy": a / b, "ratio_interval": interval(a / b)}
            for f, (a, b) in totals.items()
        },
        "engineering_error_radius": radius,
        "point_model_precision_qualified": False,
        "qualification_receipt_sha256": contract.get("qualification_receipt_sha256"),
        "limits": "Empirical engineering envelope on exposed development, conditional on "
        "support and reference block3. Not a future-program prediction interval, measured new "
        "latency or cross-allocation guarantee. M5 actual measurements remain required.",
    }


def regret_bound(intervals, selected):
    """Tight interval-box regret for ideal M5 selection with native available at cost one."""
    selected = set(selected)
    available_upper = min([1.0, *(v[1] for cid, v in intervals.items() if cid in selected)])
    excluded_lower = min([1.0, *(v[0] for cid, v in intervals.items() if cid not in selected)])
    return max(0.0, available_upper - excluded_lower)


def select_shortlist(records):
    if len(records) > 9:
        raise ValueError("at most nine submitted records")
    admitted = {}
    excluded = {}
    hashes = set()
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
    choices = []
    all_choices = []
    ids = sorted(admitted)
    for count in range(min(3, len(ids)) + 1):
        for selected in itertools.combinations(ids, count):
            bound = regret_bound(intervals, selected)
            all_choices.append(bound)
            if bound > 0.01 + 1e-12:
                continue
            clauses = [
                c
                for cid in selected
                for values in admitted[cid]["policy"]["rules"].values()
                for c in values
            ]
            key = (
                count,
                bound,
                sum(len(c["conditions"]) for c in clauses),
                len(clauses),
                tuple(sorted(admitted[cid]["rule_hash"] for cid in selected)),
            )
            choices.append((key, selected))
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
    if not choices:
        return {
            **result,
            "status": "abstain_uncertainty_exceeds_cap",
            "candidate_ids": [],
            "conditional_regret_bound": None,
            "best_attainable_bound": min(all_choices),
        }
    key, selected = min(choices, key=lambda c: c[0])
    return {
        **result,
        "status": "selected_for_M5" if selected else "certified_native_abstention",
        "candidate_ids": list(selected),
        "conditional_regret_bound": key[1],
        "best_attainable_bound": min(all_choices),
    }


def validate_proxy_costs(costs, observations):
    if (
        type(costs) is not dict
        or set(costs) != {"reference_native_ms", "prefix_ratio", "search_work", "comparison_caps"}
        or not math.isfinite(costs["reference_native_ms"])
        or costs["reference_native_ms"] <= 0
        or set(costs["prefix_ratio"]) != {"full", *observations}
        or set(costs["search_work"]) != {"full", *observations}
        or set(costs["comparison_caps"]) != set(observations)
    ):
        raise ValueError("complete evaluator-only uncertainty inputs required")
    for value in costs["prefix_ratio"].values():
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("finite positive measured prefix ratio required")
    for counters in costs["search_work"].values():
        if set(counters) != {"vector_calls", "layer0_queue_pops"} or any(
            type(v) is not int or v <= 0 for v in counters.values()
        ):
            raise ValueError("positive measured work required")
    if any(type(v) is not int or not 0 <= v <= 4 for v in costs["comparison_caps"].values()):
        raise ValueError("bounded numeric comparison support required")
