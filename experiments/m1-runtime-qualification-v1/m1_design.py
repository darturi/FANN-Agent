"""Prospective M1 pool, blocked reader crossover and exact search-attempt ledger."""

import hashlib

FILTERS = (-1, 743, 527, 310, 192, 108, 32)
POINTS = (16, 32, 64)
SEED = "reviews-protocol-v2-M1-20261116"
ARMS = {
    "native640": None,
    "legacy_noop": 6,
    "legacy_conservative": 7,
    "legacy_moderate": 8,
    "legacy_broad": 9,
    "v2_conservative": 20,
    "v2_moderate": 21,
    "v2_broad": 22,
    "matched_conservative": 30,
    "matched_moderate": 31,
    "matched_broad": 32,
    "count_stop16": 40,
    "count_stop32": 41,
    "count_stop64": 42,
    "empty": 43,
    "dependency64": 44,
    "partial_condition": 45,
    "distance64": 46,
    "count_continue": 47,
    "ranked_continue": 48,
    "turnover_continue": 49,
    "decision_continue": 50,
    "bare_stop16": 51,
    "bare_stop32": 52,
    "bare_stop64": 53,
    "four_compare_continue": 54,
}
GROUPS = (
    ("native640", "legacy_conservative", "v2_conservative", "matched_conservative", "empty"),
    ("native640", "legacy_moderate", "v2_moderate", "matched_moderate", "empty"),
    ("native640", "legacy_broad", "v2_broad", "matched_broad", "empty"),
    (
        "native640",
        "decision_continue",
        "count_continue",
        "ranked_continue",
        "turnover_continue",
        "four_compare_continue",
    ),
    ("native640", "count_stop16", "bare_stop16", "count_stop32", "bare_stop32"),
    ("native640", "count_stop64", "bare_stop64", "legacy_noop", "empty"),
)
COUNT, DISTANCE, TURNOVER, DECIDE = 1, 2, 4, 8
FEATURES = ("qualifying_count", "tenth_distance", "frontier_gap", "top10_new_since_previous")
COUNTERS = (
    "vector_calls",
    "layer0_neighbor_scores",
    "upper_neighbor_scores",
    "layer0_queue_pops",
    "layer0_adjacencies_examined",
    "feature_passes",
    "membership_probes",
)
GRAPH_COUNTERS = COUNTERS[:5]
CONTINUE_FAMILIES = {
    "native640",
    "legacy_noop",
    "empty",
    "matched_conservative",
    "matched_moderate",
    "matched_broad",
    "count_continue",
    "ranked_continue",
    "turnover_continue",
    "decision_continue",
    "four_compare_continue",
}


def blocks(group):
    n = len(GROUPS[group])
    return tuple((0, r) for r in range(n)) + tuple((1, r) for r in reversed(range(n)))


def role(group, reader, rotation):
    return GROUPS[group][(reader + rotation) % len(GROUPS[group])]


def cpu_for(reader, filter_index, group, cpus):
    return cpus[(reader + filter_index + group) % 4]


def reader_order(position, cycle, rotation, filter_index, group):
    base = (0, 1, 3, 2)
    offset = (position + rotation + filter_index + group) % 4
    row = [(x + offset) % 4 for x in base]
    return list(reversed(row)) if cycle else row


def ordered(cases, group, rotation, cycle):
    rows = sorted(
        cases,
        key=lambda q: hashlib.sha256(
            (
                SEED + ":" + str(group) + ":" + str(rotation) + ":" + q["id"].rsplit("-", 1)[0]
            ).encode()
        ).hexdigest(),
    )
    return list(reversed(rows)) if cycle else rows


def ledger(query_count=3150, reached=9436, cases_per_filter=450):
    roles = sum(map(len, GROUPS))
    measured = roles * 8 * query_count
    warmups = roles * 2 * 4 * min(10, cases_per_filter) * 7
    timing = {
        "reference_exact": query_count,
        "capture": query_count,
        "forced_prefix": reached,
        "native_bridge": 2 * query_count,
        "quality_ann": (len(ARMS) - 1) * query_count,
        "warmup_ann": warmups,
        "timed_ann": measured,
    }
    work = {"reference_exact": query_count, "work_ann": len(ARMS) * query_count}
    return {
        "timing": {**timing, "total": sum(timing.values())},
        "work": {**work, "total": sum(work.values())},
        "total": sum(timing.values()) + sum(work.values()),
    }


def masks(policy, filter_name):
    out = {str(cp): 0 for cp in POINTS}
    for clause in policy["rules"].get(filter_name, []):
        cp = clause["cp"]
        mask = DECIDE
        for feature, _, _ in clause["conditions"]:
            mask |= COUNT if feature == "qualifying_count" else COUNT | DISTANCE
            if feature == "top10_new_since_previous":
                mask |= TURNOVER
                i = POINTS.index(cp)
                if i:
                    out[str(POINTS[i - 1])] |= COUNT | DISTANCE
        out[str(cp)] |= mask
    return out


def decision(policy, filter_name, cp, observation):
    return any(
        c["cp"] == cp
        and all(
            observation.get(n) is not None
            and (observation[n] >= v if op == ">=" else observation[n] <= v)
            for n, op, v in c["conditions"]
        )
        for c in policy["rules"].get(filter_name, [])
    )


def choose(entry, filter_name, observations):
    if entry["force_continue"]:
        return 0
    return next(
        (
            o["checkpoint"]
            for o in observations
            if decision(entry["policy"], filter_name, o["checkpoint"], o)
        ),
        0,
    )
