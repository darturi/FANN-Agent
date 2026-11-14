"""Causal v2 policy schema, selective observation dependencies and exact replay."""

from __future__ import annotations

import math

from fannagent.api.profiles import FeatureDefinition, RuntimeProfile
from fannagent.store import digest

FILTERS = ("unfiltered", "votes743", "votes527", "votes310", "votes192", "votes108", "votes32")
POINTS = (16, 32, 64)
FEATURES = ("qualifying_count", "tenth_distance", "frontier_gap", "top10_new_since_previous")
COUNT, DISTANCE, TURNOVER, DECIDE = 1, 2, 4, 8
PROFILE = RuntimeProfile(
    name="filtered-ann-partial-checkpoints/v2",
    features={
        n: FeatureDefinition(
            name=n,
            kind="int" if n in (FEATURES[0], FEATURES[3]) else "float",
            group="checkpoint_heap",
            availability="count at reached checkpoint; tenth/gap only with full top10;"
            " turnover only when current and preceding scheduled top10 ar"
            "e full",
            collection_cost="compiler-derived predicate/checkpoint dependency mask",
        )
        for n in FEATURES
    },
    checkpoint_interval=64,
    checkpoint_semantics="expanded-neighborhood checkpoints16/32/64; previous schedule"
    "d checkpoint, not last collected checkpoint",
    stopping_scope="original noniterative search prefix; actual0..10 SQL results; no completion",
    work_unit="graph score/queue work",
    policy_encoding="filtered_ann_checkpoint_v2",
)


class PolicyError(ValueError):
    pass


def validate(p):
    def check(value, message):
        if not value:
            raise PolicyError(message)

    check(
        isinstance(p, dict) and set(p) == {"schema", "name", "rules", "rationale"},
        "expected schema/name/rules/rationale only",
    )
    check(p["schema"] == "fannagent.filtered-ann.v2", "incompatible policy schema")
    check(type(p["name"]) is str and 0 < len(p["name"]) <= 80, "invalid name")
    check(type(p["rationale"]) is str and len(p["rationale"]) <= 4000, "invalid rationale")
    check(
        type(p["rules"]) is dict and set(p["rules"]) <= set(FILTERS),
        "unexpected predicate or runtime identifier",
    )
    for f, clauses in p["rules"].items():
        check(type(clauses) is list and len(clauses) <= 3, "at most3 clauses/predicate")
        last = 0
        for c in clauses:
            check(type(c) is dict and set(c) == {"cp", "conditions"}, "invalid clause")
            check(
                type(c["cp"]) is int and c["cp"] in POINTS and c["cp"] > last,
                "checkpoints must ascend uniquely",
            )
            last = c["cp"]
            check(
                type(c["conditions"]) is list and len(c["conditions"]) <= 4,
                "at most4 comparisons/clause",
            )
            for test in c["conditions"]:
                check(type(test) is list and len(test) == 3, "invalid comparison")
                name, op, value = test
                check(
                    type(name) is str and name in FEATURES and op in (">=", "<="),
                    "unsupported runtime feature/operator",
                )
                check(
                    type(value) in (int, float) and math.isfinite(value),
                    "threshold must be finite numeric",
                )
                if name == "qualifying_count":
                    check(
                        type(value) is int and 0 <= value <= 247286,
                        "count threshold must be corpus-bounded integer",
                    )
                elif name == "top10_new_since_previous":
                    check(
                        type(value) is int and 0 <= value <= 10,
                        "turnover threshold must be integer0..10",
                    )
                else:
                    check(
                        (-2 if name == "frontier_gap" else 0) <= value <= 2,
                        "cosine threshold outside domain",
                    )
    return p


def rule_hash(p):
    validate(p)
    return digest(
        {"schema": p["schema"], "rules": p["rules"], "runtime_profile": PROFILE.fingerprint}
    )


def observation_plan(p):
    validate(p)
    plan = {f: {str(cp): 0 for cp in POINTS} for f in FILTERS}
    for f, clauses in p["rules"].items():
        for c in clauses:
            cp = c["cp"]
            mask = DECIDE
            for feature, _, _ in c["conditions"]:
                mask |= COUNT if feature == "qualifying_count" else COUNT | DISTANCE
                if feature == "top10_new_since_previous":
                    mask |= TURNOVER
                    index = POINTS.index(cp)
                    if index:
                        plan[f][str(POINTS[index - 1])] |= COUNT | DISTANCE
            plan[f][str(cp)] |= mask
    return plan


def decide(p, f, cp, observation):
    validate(p)
    for c in p["rules"].get(f, []):
        if c["cp"] != cp:
            continue
        if all(
            observation.get(n) is not None
            and (observation[n] >= v if op == ">=" else observation[n] <= v)
            for n, op, v in c["conditions"]
        ):
            return True
    return False


def choose(p, row):
    for cp in POINTS:
        o = row["observations"].get(str(cp))
        if o is not None and decide(p, row["filter"], cp, o):
            return cp
    return None


def replay(p, rows):
    validate(p)
    per = {
        f: {
            "queries": 0,
            "losses": 0,
            "stops": 0,
            "unknown_stops": 0,
            "recall_sum": 0.0,
            "native_recall_sum": 0.0,
        }
        for f in FILTERS
    }
    examples = {f: [] for f in FILTERS}
    folds = {}
    unknown = 0
    for row in rows:
        f = row["filter"]
        m = per[f]
        m["queries"] += 1
        m["native_recall_sum"] += row["native_recall"]
        cp = choose(p, row)
        fold = folds.setdefault(
            str(row["fold"]),
            {"queries": 0, "losses": 0, "stops": 0, "unknown_stops": 0},
        )
        fold["queries"] += 1
        if cp is not None:
            m["stops"] += 1
            fold["stops"] += 1
            proof = row["proofs"].get(str(cp))
            if proof is None:
                m["unknown_stops"] += 1
                fold["unknown_stops"] += 1
                unknown += 1
                continue
            score = proof["recall"]
        else:
            score = row["native_recall"]
        m["recall_sum"] += score
        if score < row["native_recall"] - 1e-12:
            m["losses"] += 1
            fold["losses"] += 1
            if len(examples[f]) < 3:
                examples[f].append(
                    {
                        "anonymous_group": row["group"],
                        "fold": row["fold"],
                        "checkpoint": cp,
                        "features": row["observations"][str(cp)],
                        "recall": score,
                        "native_recall": row["native_recall"],
                    }
                )
    for m in per.values():
        m["native_mean_recall"] = (
            m.pop("native_recall_sum") / m["queries"] if m["queries"] else None
        )
        m["mean_recall"] = (
            None if m["unknown_stops"] else m["recall_sum"] / m["queries"] if m["queries"] else None
        )
        m.pop("recall_sum")
    loss = sum(m["losses"] for m in per.values())
    return {
        "status": "incomplete_prefix_evidence" if unknown else "evaluated",
        "quality_preserves_raw_native640": not unknown
        and not loss
        and all(m["queries"] for m in per.values()),
        "recall_losses": loss,
        "unqualified_stops": unknown,
        "per_filter": per,
        "per_exposed_development_fold": folds,
        "counterexamples": {f: v for f, v in examples.items() if v},
        "latency_status": "not measured; never infer by subtracting fallback or equatin"
        "g work with time",
        "runtime_profile": PROFILE.fingerprint,
        "rule_hash": rule_hash(p),
    }
