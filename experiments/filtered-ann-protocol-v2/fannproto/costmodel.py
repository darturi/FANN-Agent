"""Fixed M2 engineering proxies. Work and measured bases are evaluator-only inputs."""

from .policy import COUNT, DECIDE, DISTANCE, POINTS, TURNOVER, choose, observation_plan

OP_NAMES = ("count", "ranked", "turnover", "decision", "comparison")
WORK_FEATURES = (
    "vector_ratio_minus_one",
    "queue_ratio_minus_one",
    *(f"{kind}{cp}_div3" for kind in OP_NAMES[:3] for cp in POINTS),
    "decision_calls_div3",
    "numeric_comparisons_div12",
)


def operations(policy, row, *, force_continue=False):
    """Count scheduled passes and evaluated numeric tests, honoring null/short circuiting."""
    stop = None if force_continue else choose(policy, row)
    masks = observation_plan(policy)[row["filter"]]
    counts = {kind: [0, 0, 0] for kind in OP_NAMES}
    for index, cp in enumerate(POINTS):
        observation = row["observations"].get(str(cp))
        if observation is None or stop is not None and cp > stop:
            continue
        mask = masks[str(cp)]
        counts["count"][index] = int(bool(mask & COUNT))
        counts["ranked"][index] = int(bool(mask & DISTANCE))
        counts["turnover"][index] = int(
            bool(mask & TURNOVER) and observation["top10_new_since_previous"] is not None
        )
        if mask & DECIDE:
            counts["decision"][index] = 1
            clause = next(c for c in policy["rules"][row["filter"]] if c["cp"] == cp)
            for feature, op, threshold in clause["conditions"]:
                value = observation[feature]
                if value is None:
                    break
                counts["comparison"][index] += 1
                if not (value >= threshold if op == ">=" else value <= threshold):
                    break
    return stop, counts


def features(policy, row, costs, *, force_continue=False):
    stop, counts = operations(policy, row, force_continue=force_continue)
    key = str(stop) if stop is not None else "full"
    base = costs["prefix_ratio"][key]
    work = costs["search_work"][key]
    native = costs["search_work"]["full"]
    additive = [sum(counts[k]) for k in OP_NAMES]
    ridge = [
        work["vector_calls"] / native["vector_calls"] - 1,
        work["layer0_queue_pops"] / native["layer0_queue_pops"] - 1,
        *(n / 3 for kind in OP_NAMES[:3] for n in counts[kind]),
        additive[3] / 3,
        additive[4] / 12,
    ]
    return base, additive, ridge


def predict_ratio(model, policy, row, costs, *, force_continue=False):
    base, additive, ridge = features(policy, row, costs, force_continue=force_continue)
    values = additive if model["kind"] == "signed_additive" else ridge
    coefficient = model["coefficients"][row["filter"]]
    if len(values) != len(coefficient):
        raise ValueError("cost model feature contract differs")
    return base + sum(a * b for a, b in zip(values, coefficient, strict=True))
