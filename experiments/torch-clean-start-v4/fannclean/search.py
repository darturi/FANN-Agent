"""Search progress and evidence-based stopping, separate from final policy validity."""

from .core import FILTERS, digest


def structure(policy):
    def node(value):
        if isinstance(value, list):
            return [value[0], *[node(v) for v in value[1:]]]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return "number"
        return value

    # Operator/feature vocabulary and register usage are deliberately conservative
    # evidence of structural diversity, not a claim of exhaustive search.
    def vocabulary(value):
        if isinstance(value, list):
            if (
                len(value) == 4
                and value[0] == "if"
                and isinstance(value[1], list)
                and value[1][:2] == ["eq", ["feature", "checkpoint"]]
            ):
                return vocabulary(value[2]) | vocabulary(value[3])
            return {
                digest(node(value)),
                *(v for x in value if isinstance(x, list) for v in vocabulary(x)),
            }
        return set()

    return digest(
        {
            "slots": policy["state_slots"],
            "shapes": sorted(
                {
                    v
                    for p in policy["programs"].values()
                    for x in [p["root"], *p["updates"].values()]
                    for v in vocabulary(x)
                    if v
                }
            ),
        }
    )


def quality_ok(result, family):
    rows = [r for r in result["quality"] if r["family"] == family]
    return bool(rows) and all(
        r["recall"] + 1e-12 >= r["native_recall"]
        and r["count"] >= r["native_count"]
        and not r.get("fault")
        and not r.get("exhausted")
        for r in rows
    )


def qualified(result, family):
    estimate = (result.get("timing") or {}).get("families", {}).get(family, {})
    return (
        result.get("full_quality", False)
        and quality_ok(result, family)
        and any(r["checkpoint"] > 0 for r in result["quality"] if r["family"] == family)
        and result["timing"]["controls_pass"]
        and estimate.get("all", {}).get("ci95", [0, 2])[1] < 1
        and estimate.get("matched", {}).get("ci95", [0, 2])[1] < 1
    )


def stopping_review(state, limits, candidate_id, report, resources):
    required = {
        "alternatives_considered",
        "acquisition_coverage",
        "cost_evidence",
        "why_more_search_not_worth_cost",
        "reason",
    }
    if set(report) != required or any(
        not isinstance(report[k], str) or len(report[k].strip()) < 12 for k in required
    ):
        raise ValueError("provide a substantive search/stopping report for all required fields")
    completed = [r for r in state["rounds"] if r["status"] == "complete"]
    structures = {
        c["structure"]
        for c in state["candidates"].values()
        if c.get("screened") and c["policy"]["programs"]
    }
    exhausted = (
        resources["discovery_queries_remaining"] < resources["minimum_action_queries"]
        or resources["discovery_seconds_remaining"] <= 60
        or resources.get("model_exhausted", False)
        or (
            resources["discovery_queries_remaining"]
            < resources.get("minimum_confirmation_queries", 0)
            and not any(
                c.get("confirmation") and qualified(c["confirmation"], "candidate:0")
                for c in state["candidates"].values()
            )
        )
    )
    adequate = (
        len(completed) >= limits.minimum_rounds
        and len(structures) >= limits.minimum_structures
        and set(state.get("observed_filters", [])) == set(FILTERS)
    )
    if not adequate and not exhausted:
        raise ValueError(
            "search stopped prematurely: budget/time remains and "
            "multiple rounds/structures and all-condition evidence have not been evaluated"
        )
    if candidate_id is not None:
        candidate = state["candidates"].get(candidate_id)
        if (
            not candidate
            or not candidate.get("confirmation")
            or not qualified(candidate["confirmation"], "candidate:0")
        ):
            raise ValueError(
                "freeze requires full quality/count preservation and independently "
                "controlled confirmation; failed timing is inconclusive"
            )
    return {
        "status": "policy_frozen" if candidate_id else "abstained",
        "search_coverage_requirement_met": adequate,
        "resource_exit": exhausted,
        "report": report,
        "candidate_id": candidate_id,
    }
