"""Pinned B1b scoring/timer statistics, unchanged algorithms with B2b criteria."""

import math
from collections import defaultdict

from pa_common import CRITERIA


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


def contrasts(rows, treatment, baseline=None):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[(row["block"], row["query_id"], row["round"], row["repetition"])][
            (row["cell"], row["label"])
        ] = row
    result = []
    for members in grouped.values():
        a = (
            [members[(treatment, "b")]]
            if baseline is None
            else [members[(treatment, label)] for label in ("a", "b")]
        )
        b = (
            [members[(treatment, "a")]]
            if baseline is None
            else [members[(baseline, label)] for label in ("a", "b")]
        )
        require(
            all(x["result"]["valid"] for x in a + b)
            and all(x["result"]["recall"] == a[0]["result"]["recall"] for x in a)
            and all(x["result"]["recall"] == b[0]["result"]["recall"] for x in b),
            "Identical labels changed semantic quality",
        )

        def mean(values, key):
            return sum(v[key] for v in values) / len(values)

        first = a[0]
        result.append(
            {
                "group": first["group"],
                "query_id": first["query_id"],
                "stratum": first["query_id"].rsplit("-", 1)[1],
                "block": first["block"],
                "regime": first["regime"],
                "treatment_ms": mean(a, "outer_ms"),
                "baseline_ms": mean(b, "outer_ms"),
                "sql_gap_ms": mean(a, "sql_ms") - mean(b, "sql_ms"),
                "recall_delta": a[0]["result"]["recall"] - b[0]["result"]["recall"],
                "reference_recall": b[0]["result"]["recall"],
                "treatment_recall": a[0]["result"]["recall"],
                "all_valid": all(v["result"]["valid"] for v in a + b),
            }
        )
    return result


def summary(rows):
    import numpy as np

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["group"]].append(row)
    require(len(grouped) == 200, "Expected200 independent exposed vectors")

    def columns(r):
        return [
            r["treatment_ms"] - r["baseline_ms"],
            math.log(r["treatment_ms"] / r["baseline_ms"]),
            r["recall_delta"],
            r["sql_gap_ms"],
        ]

    matrix = np.asarray(
        [np.mean([columns(r) for r in grouped[g]], axis=0) for g in sorted(grouped)]
    )
    rng = np.random.default_rng(CRITERIA["bootstrap_seed"])
    boot = np.empty((CRITERIA["bootstrap_samples"], 4))
    for offset in range(0, len(boot), 128):
        count = min(128, len(boot) - offset)
        boot[offset : offset + count] = matrix[
            rng.integers(0, len(matrix), size=(count, len(matrix)))
        ].mean(axis=1)
    ci = np.quantile(boot, [0.025, 0.975], axis=0)

    def mean(key):
        return float(np.mean([r[key] for r in rows]))

    return {
        "observations": len(rows),
        "independent_vectors": len(grouped),
        "gap_ms": float(matrix[:, 0].mean()),
        "gap_upper_adjusted": float(np.quantile(boot[:, 0], CRITERIA["benefit_upper_quantile"])),
        "log_ratio_upper_adjusted": float(
            np.quantile(boot[:, 1], CRITERIA["benefit_upper_quantile"])
        ),
        "gap_ci95": ci[:, 0].tolist(),
        "log_ratio": float(matrix[:, 1].mean()),
        "log_ratio_ci95": ci[:, 1].tolist(),
        "recall_delta": float(matrix[:, 2].mean()),
        "recall_delta_ci95": ci[:, 2].tolist(),
        "sql_gap_ms": float(matrix[:, 3].mean()),
        "sql_gap_ci95": ci[:, 3].tolist(),
        "baseline_ms": mean("baseline_ms"),
        "treatment_ms": mean("treatment_ms"),
        "reference_recall": mean("reference_recall"),
        "treatment_recall": mean("treatment_recall"),
        "all_valid": all(r["all_valid"] for r in rows),
        "block_gap_ms": {
            str(b): float(
                np.mean([r["treatment_ms"] - r["baseline_ms"] for r in rows if r["block"] == b])
            )
            for b in range(2)
        },
    }


def equivalent(value, expected, truth, cell):
    if cell == "native640":
        require(value == expected, "Native640 output changed")
        return
    require(
        value["valid"] and value["recall"] == 1.0 and value["returned_count"] == 10,
        "Exact10 failed tie-aware exact semantics",
    )
    strict, ties = set(truth["truth_strict"]), set(truth["truth_ties"])
    ids = set(value["ids"])
    require(
        strict <= ids and ids <= strict | ties and len(ids) == 10,
        "Exact10 membership differs from truth",
    )
    known = dict(zip(expected["ids"], expected["distances"]))
    boundary = expected["distances"][-1]
    for i, d in zip(value["ids"], value["distances"]):
        require(d == (known[i] if i in known else boundary), "Exact10 distance mapping/tie differs")
