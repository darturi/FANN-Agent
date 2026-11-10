"""Scoring plus prospective physical-session equivalence, no benefit test."""

import math
from collections import defaultdict


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value, positive=False):
    require(
        type(value) in (float, int)
        and math.isfinite(value)
        and (value > 0 if positive else value >= 0),
        "Invalid duration/value",
    )


def near(a, b):
    require(abs(a - b) <= 1e-9, "Raw timer arithmetic differs")


def unique(rows, key):
    result = {}
    for row in rows:
        k = key(row)
        require(k not in result, "Duplicate raw identity")
        result[k] = row
    return result


def score_result(value, truth, query, eligibility):
    ids, distances = value["ids"], value["distances"]
    require(len(ids) == len(distances) and len(ids) <= 10, "Malformed ANN output")
    require(
        all(type(i) is int and 0 <= i < len(eligibility["votes"]) for i in ids),
        "Unknown analysis ID",
    )
    require(
        all(
            type(d) in (float, int) and math.isfinite(d) and -1e-6 <= d <= 2.000001
            for d in distances
        ),
        "Invalid cosine distance",
    )
    require(distances == sorted(distances), "ANN output is not distance ordered")
    predicate = query.get("filter")
    votes = eligibility["votes"]
    violations = sum(
        predicate is not None and (votes[i] is None or votes[i] < predicate["value"])
        for i in set(ids)
    )
    strict, ties, k = set(truth["truth_strict"]), set(truth["truth_ties"]), truth["truth_k"]
    require(k == 10 and len(strict) <= k and not strict & ties, "Malformed exact truth")
    recall = (len(set(ids) & strict) + min(k - len(strict), len(set(ids) & ties))) / k
    duplicates = len(ids) - len(set(ids))
    expected = {
        "ids": ids,
        "distances": distances,
        "recall": recall,
        "valid": not duplicates and not violations and len(ids) == 10,
        "returned_count": len(ids),
        "duplicate_count": duplicates,
        "predicate_violation_count": violations,
    }
    require(value == expected, "Output membership/recall/validity differs from independent score")


def timing(rows):
    """All-required 56 pointwise intervals; physical identities never pooled away."""
    import numpy as np

    values = unique(
        rows, lambda r: (r["epoch"], r["cell"], r["query_id"], r["physical_slot"], r["repetition"])
    )
    require(len(values) == 4800, "Incomplete retained inventory")
    groups = sorted({r["group"] for r in rows})
    require(len(groups) == 200, "Expected 200 vector groups")
    query = {r["group"]: r["query_id"] for r in rows}
    endpoints = {}

    def add(name, members):
        d, logs = {}, {}
        for g, pairs in members.items():
            require(pairs, "Missing paired observations")
            d[g] = sum(a - b for a, b in pairs) / len(pairs)
            logs[g] = sum(math.log(a / b) for a, b in pairs) / len(pairs)
        endpoints[name + "/gap"] = (d, 0.10)
        endpoints[name + "/log"] = (logs, math.log(1.02))

    for e in (0, 1):
        for c in ("native640", "partial640"):
            aa = {}
            halves = {0: {}, 1: {}}
            for g in groups:
                pairs = []
                for rep in (1, 2, 3):
                    a = values[e, c, query[g], "r1", rep]
                    b = values[e, c, query[g], "r0", rep]
                    finite(a["outer_ms"], True)
                    finite(b["outer_ms"], True)
                    pairs.append((a["outer_ms"], b["outer_ms"]))
                aa[g] = pairs
                halves[a["query_position"] // 100][g] = pairs
            add(f"aa/{e}/{c}", aa)
            for h in (0, 1):
                require(len(halves[h]) == 100, "Incomplete temporal half")
                add(f"half/{e}/{c}/{h}", halves[h])
            for reader in ("r0", "r1"):
                for prev, nxt in ((1, 2), (2, 3)):
                    add(
                        f"stability/{e}/{c}/{reader}/{prev}-{nxt}",
                        {
                            g: [
                                (
                                    values[e, c, query[g], reader, nxt]["outer_ms"],
                                    values[e, c, query[g], reader, prev]["outer_ms"],
                                )
                            ]
                            for g in groups
                        },
                    )
    require(len(endpoints) == 56, "Endpoint inventory differs")
    families = defaultdict(list)
    for name, (data, margin) in endpoints.items():
        families[tuple(sorted(data))].append((name, data, margin))
    result = {}
    for gs, columns in sorted(families.items()):
        matrix = np.asarray([[d[g] for _, d, _ in columns] for g in gs], dtype=np.float64)
        rng = np.random.default_rng(20261019)
        boot = np.empty((10000, len(columns)))
        for offset in range(0, 10000, 128):
            count = min(128, 10000 - offset)
            boot[offset : offset + count] = matrix[
                rng.integers(0, len(gs), size=(count, len(gs)))
            ].mean(axis=1)
        ci = np.quantile(boot, [0.025, 0.975], axis=0, method="linear")
        for j, (name, _, margin) in enumerate(columns):
            interval = ci[:, j].tolist()
            result[name] = dict(
                mean=float(matrix[:, j].mean()),
                ci95=interval,
                independent_vectors=len(gs),
                margin=margin,
                equivalent=bool(interval[0] >= -margin and interval[1] <= margin),
            )
    return dict(
        intervals=result,
        required_intervals=56,
        passed_intervals=sum(r["equivalent"] for r in result.values()),
        all_pass=all(r["equivalent"] for r in result.values()),
        pointwise_not_simultaneous=True,
        treatment_speed_verdict=False,
    )
