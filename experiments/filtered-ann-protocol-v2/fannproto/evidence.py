"""Frozen development evidence; never manufacture missing partial-prefix outputs."""

import math
import re
from collections import Counter
from copy import deepcopy

from fannagent.store import digest

from .policy import FEATURES, FILTERS, POINTS, PROFILE


class Evidence:
    def __init__(self, bundle, *, fixture=False):
        if (
            bundle.get("schema") != "filtered-ann-evidence.v2"
            or bundle.get("scope") != "development"
        ):
            raise ValueError("development bundle required")
        self.bundle = bundle = deepcopy(bundle)
        self.rows = bundle["rows"]
        self.fixture = fixture
        if type(self.rows) is not list or not self.rows:
            raise ValueError("nonempty development rows required")
        seen = set()
        groups = set()
        cells = Counter()
        folds = {}
        for r in self.rows:
            if set(r) - {"costs"} != {
                "group",
                "fold",
                "filter",
                "native_recall",
                "native_count",
                "observations",
                "proofs",
            }:
                raise ValueError("unexpected row fields, possibly source IDs/oracle inputs")
            key = r["group"], r["filter"]
            if (
                key in seen
                or type(r["group"]) is not int
                or r["group"] < 0
                or r["filter"] not in FILTERS
                or type(r["fold"]) is not int
                or not 0 <= r["fold"] < 5
            ):
                raise ValueError("group/filter/fold inventory")
            seen.add(key)
            groups.add(r["group"])
            cells[r["filter"]] += 1
            if r["group"] in folds and folds[r["group"]] != r["fold"]:
                raise ValueError("group fold must be consistent across filters")
            folds[r["group"]] = r["fold"]
            if (
                type(r["native_count"]) is not int
                or not 0 <= r["native_count"] <= 10
                or not numeric(r["native_recall"], 0, r["native_count"] / 10)
            ):
                raise ValueError("invalid raw native label")
            for cp, o in r["observations"].items():
                if cp not in {str(x) for x in POINTS} or set(o) != set(FEATURES):
                    raise ValueError("invalid checkpoint or evaluator leakage into features")
                n = o["qualifying_count"]
                t = o["tenth_distance"]
                g = o["frontier_gap"]
                u = o["top10_new_since_previous"]
                if type(n) is not int or not 0 <= n <= 247286:
                    raise ValueError("invalid qualifying count")
                if t is not None and (n < 10 or not numeric(t, 0, 2)):
                    raise ValueError("invalid tenth distance availability/value")
                if g is not None and (t is None or not numeric(g, -2, 2)):
                    raise ValueError("invalid gap availability/value")
                previous = (
                    r["observations"].get(str(POINTS[POINTS.index(int(cp)) - 1]))
                    if int(cp) != 16
                    else None
                )
                if u is not None and (
                    type(u) is not int
                    or not 0 <= u <= 10
                    or t is None
                    or previous is None
                    or previous["tenth_distance"] is None
                ):
                    raise ValueError("turnover requires two full scheduled top tens")
            for cp, proof in r["proofs"].items():
                if (
                    set(proof) != {"recall", "returned_count"}
                    or cp not in r["observations"]
                    or type(proof["returned_count"]) is not int
                    or not 0 <= proof["returned_count"] <= 10
                    or not numeric(proof["recall"], 0, proof["returned_count"] / 10)
                ):
                    raise ValueError("invalid prefix label")
            if bundle.get("cost_status") == "qualified":
                validate_costs(r.get("costs"), r["observations"])
        if not fixture and (
            len(self.rows) != 3150
            or groups != set(range(450))
            or any(cells[f] != 450 for f in FILTERS)
        ):
            raise ValueError("frozen450-group/seven-condition coverage required")
        if bundle.get("runtime_profile") != PROFILE.fingerprint:
            raise ValueError("runtime profile mismatch")
        if bundle.get("cost_status") == "qualified" and not re.fullmatch(
            "[a-f0-9]{64}", bundle.get("cost_qualification_receipt_sha256", "")
        ):
            raise ValueError("cost qualification receipt required")
        self.identity = digest(bundle)

    def summary(self):
        per = {}
        for f in FILTERS:
            rows = [r for r in self.rows if r["filter"] == f]
            n = len(rows)
            per[f] = {
                "queries": n,
                "native_mean_recall": sum(r["native_recall"] for r in rows) / n if n else None,
                "short_native": sum(r["native_count"] < 10 for r in rows),
                "checkpoints": {
                    str(cp): {
                        "observed": sum(str(cp) in r["observations"] for r in rows),
                        "qualified_prefixes": sum(str(cp) in r["proofs"] for r in rows),
                        "missing_prefixes": sum(
                            str(cp) in r["observations"] and str(cp) not in r["proofs"]
                            for r in rows
                        ),
                    }
                    for cp in POINTS
                },
            }
        return {
            "scope": "development",
            "groups": len({r["group"] for r in self.rows}),
            "per_filter": per,
            "runtime_profile": PROFILE.describe(),
            "evidence_hash": self.identity,
            "cost_status": self.bundle["cost_status"],
            "limit": "No measured v2 serving costs implied; incomplete prefix evid"
            "ence never yields a quality pass.",
        }

    def examples(self, category, filter_, limit):
        if (
            category not in ("short_native", "qualified_full_prefix", "missing_partial_prefix")
            or filter_ not in FILTERS
            or type(limit) is not int
            or not 1 <= limit <= 12
        ):
            raise ValueError("bounded category/filter/limit required")
        rows = [r for r in self.rows if r["filter"] == filter_]
        predicate = {
            "short_native": lambda r: r["native_count"] < 10,
            "qualified_full_prefix": lambda r: any(
                v["returned_count"] == 10 for v in r["proofs"].values()
            ),
            "missing_partial_prefix": lambda r: any(
                cp not in r["proofs"] and o["qualifying_count"] < 10
                for cp, o in r["observations"].items()
            ),
        }[category]
        return [
            {
                k: r[k]
                for k in (
                    "group",
                    "fold",
                    "filter",
                    "native_recall",
                    "native_count",
                    "observations",
                    "proofs",
                )
            }
            for r in rows
            if predicate(r)
        ][:limit]

    def estimate(self, p):
        """Qualified component proxy only; never a measured new-program latency."""
        if self.bundle["cost_status"] != "qualified":
            return None
        import math

        from .policy import COUNT, DECIDE, DISTANCE, POINTS, TURNOVER, choose, observation_plan

        plan = observation_plan(p)
        totals = {f: [] for f in FILTERS}
        for row in self.rows:
            costs = row.get("costs")
            if costs is None:
                raise ValueError("qualified component-cost row missing")
            cp = choose(p, row)
            full = costs["search_ms"]["full"]
            value = costs["search_ms"][str(cp)] if cp is not None else full
            for point in POINTS:
                if str(point) not in row["observations"] or cp is not None and point > cp:
                    continue
                mask = plan[row["filter"]][str(point)]
                if mask & COUNT:
                    value += costs["ranked_ms"] if mask & DISTANCE else costs["count_only_ms"]
                if mask & TURNOVER:
                    value += costs["turnover_ms"]
                if mask & DECIDE:
                    clause = next(c for c in p["rules"][row["filter"]] if c["cp"] == point)
                    value += (
                        costs["decision_base_ms"]
                        + len(clause["conditions"]) * costs["comparison_ms"]
                    )
            if not math.isfinite(value) or value <= 0:
                raise ValueError("invalid cost proxy")
            totals[row["filter"]].append(value)
        per = {f: sum(values) / len(values) for f, values in totals.items() if values}
        if set(per) != set(FILTERS):
            raise ValueError("all conditions required for cost ranking")
        return {
            "equal_scalar_mean_ms": sum(per[f] for f in FILTERS if f != "unfiltered") / 6,
            "per_filter_mean_ms": per,
            "status": "measured-component surrogate, not live policy cost",
            "qualification_receipt_sha256": self.bundle["cost_qualification_receipt_sha256"],
        }


def numeric(value, low, high):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and low - 1e-12 <= value <= high + 1e-12
    )


def validate_costs(costs, observations):
    fields = {
        "search_ms",
        "count_only_ms",
        "ranked_ms",
        "turnover_ms",
        "decision_base_ms",
        "comparison_ms",
    }
    if (
        type(costs) is not dict
        or set(costs) != fields
        or type(costs["search_ms"]) is not dict
        or set(costs["search_ms"]) != {"full", *observations}
    ):
        raise ValueError("complete measured component costs required")
    for k, v in costs.items():
        values = v.values() if k == "search_ms" else (v,)
        if any(not numeric(x, 0, 1e9) or k == "search_ms" and x <= 0 for x in values):
            raise ValueError("finite nonnegative component costs required")
