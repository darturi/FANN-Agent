"""Hindsight pure-leaf trees compiled through the ordinary v3 agent interface.

Fitting labels may use outcomes; emitted features never contain identifiers,
labels, roles or future state. Unknown executed prefixes are negative labels.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "agent/src"), str(HERE.parent / "filtered-ann-protocol-v3")]
from fannproto3.tools import BroadPolicyTools  # noqa: E402
from prepare_capture import STUDY, sha  # noqa: E402

from fannagent.api.broad_policy import FEATURES, compile_graph, policy_hash, validate  # noqa: E402

# These costs only guide offline tree selection; actual serving overhead is timed.
COSTS = np.array([1, 1, 3, 14, 14, 20, 14, 14, 1, 3, 4, 18, 18], dtype=float)


def rows(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def frontier_tree(x, y):
    """A balanced threshold tree can separate unique causal frontier values.

    This deliberately exposes the capacity of hindsight fitting. It does not
    require ranking retained candidates, and it contains no query identifiers.
    Ambiguous feature values fall back to the richer classifier.
    """
    values = x[:, 8]
    if not np.isfinite(values).all():
        return None
    order = np.argsort(values, kind="stable")
    values, labels = values[order], y[order]
    if np.any((values[:-1] == values[1:]) & (labels[:-1] != labels[1:])):
        return None
    transitions = np.flatnonzero(labels[:-1] != labels[1:])
    cuts = []
    for i in transitions:
        cut = float(values[i] + (values[i + 1] - values[i]) / 2)
        if not values[i] <= cut < values[i + 1]:
            cut = float(values[i])
        cuts.append(cut)
    leaves = [labels[0].item(), *(labels[i + 1].item() for i in transitions)]

    def build(lo, hi):
        if lo == hi:
            return leaves[lo]
        mid = (lo + hi) // 2
        return [
            "if",
            ["le", ["feature", "frontier_distance"], cuts[mid]],
            build(lo, mid),
            build(mid + 1, hi),
        ]

    return build(0, len(cuts))


def tree(x, y, w, depth=0, max_depth=28):
    if y.all():
        return True
    if not y.any() or depth >= max_depth:
        return False
    if depth == 0:
        cheap = frontier_tree(x, y)
        if cheap is not None:
            return cheap
    total = w.sum()
    positive = (w * y).sum()
    impurity = positive * (total - positive) / total
    best = None
    for feature in range(1, len(FEATURES)):
        values = x[:, feature]
        finite = np.isfinite(values)
        if finite.any() and not finite.all():
            left = finite
            wl = w[left].sum()
            pl = (w[left] * y[left]).sum()
            gain = (
                impurity
                - pl * (wl - pl) / wl
                - (positive - pl) * (total - wl - positive + pl) / (total - wl)
            )
            candidate = (gain / COSTS[feature], -COSTS[feature], -feature, 0, feature, None, left)
            if best is None or candidate[:4] > best[:4]:
                best = candidate
            continue
        if not finite.all() or len(values) < 2:
            continue
        order = np.argsort(values, kind="stable")
        v = values[order]
        a = w[order]
        b = y[order]
        wl = np.cumsum(a)[:-1]
        pl = np.cumsum(a * b)[:-1]
        wr = total - wl
        pr = positive - pl
        gains = impurity - pl * (wl - pl) / wl - pr * (wr - pr) / wr
        gains[v[:-1] == v[1:]] = -np.inf
        split = int(np.argmax(gains))
        if not np.isfinite(gains[split]):
            continue
        cut = float(v[split] + (v[split + 1] - v[split]) / 2)
        if not v[split] <= cut < v[split + 1]:
            cut = float(v[split])
        left = values <= cut
        candidate = (
            float(gains[split]) / COSTS[feature],
            -COSTS[feature],
            -feature,
            -cut,
            feature,
            cut,
            left,
        )
        if best is None or candidate[:4] > best[:4]:
            best = candidate
    if best is None:
        return False
    feature, cut, left = best[4:]
    a = tree(x[left], y[left], w[left], depth + 1, max_depth)
    b = tree(x[~left], y[~left], w[~left], depth + 1, max_depth)
    if a == b:
        return a
    condition = (
        ["available", ["feature", FEATURES[feature]]]
        if cut is None
        else ["le", ["feature", FEATURES[feature]], cut]
    )
    return ["if", condition, a, b]


def dispatch(points):
    if not points:
        return False
    if len(points) == 1:
        return points[0][1]
    mid = len(points) // 2
    return [
        "if",
        ["le", ["feature", "checkpoint"], points[mid - 1][0]],
        dispatch(points[:mid]),
        dispatch(points[mid:]),
    ]


def predict(node, values):
    if type(node) in (bool, int, float):
        return node
    condition = node[1]
    index = FEATURES.index(condition[1][1])
    value = values[index]
    if condition[0] == "available":
        result = value is not None
    elif value is None:
        return False
    else:
        result = value <= condition[2]
    return predict(node[2] if result else node[3], values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir()
    capture = list(rows(args.capture / "cases.jsonl"))
    by_id = {r["id"]: r for r in capture}
    safe = {qid: set() for qid in by_id}
    known = {qid: {} for qid in by_id}
    original = STUDY / "full-workload-oracle-v1/return-23567950/results"
    for r in rows(original / "prefixes.jsonl"):
        qid, cp = r["id"], r["checkpoint"]
        if r["recall"] + 1e-12 >= by_id[qid]["native_recall"]:
            safe[qid].add(cp)
        known[qid][cp] = r["output"]
    legal = STUDY / "oracle-variants-v1/return-23604734/results/cases.jsonl"
    legacy = {r["id"]: r for r in rows(legal)}
    for qid, r in legacy.items():
        for cp, action in r["actions"].items():
            cp = int(cp)
            known[qid][cp] = action["output"]
            if action["safe"]:
                safe[qid].add(cp)
    # Independent prefix-label feature qualification at every known observation.
    checked = 0
    for r in capture:
        for frame in r["frames"]:
            output = known[r["id"]].get(frame["checkpoint"])
            if output is None:
                continue
            values = frame["values"]
            assert min(10, values[2]) == len(output)
            for rank, index in ((1, 6), (5, 7), (10, 3)):
                if len(output) >= rank:
                    assert abs(values[index] - output[rank - 1][1]) < 2e-6, (
                        r["id"],
                        frame["checkpoint"],
                        rank,
                        values[index],
                        output,
                    )
            checked += 1
    (args.output / "source-verification.json").write_text(
        json.dumps(
            {
                "status": "broad_capture_and_prefix_features_verified",
                "cases": len(capture),
                "frames": sum(len(r["frames"]) for r in capture),
                "known_prefix_feature_checks": checked,
                "cases_sha256": sha(args.capture / "cases.jsonl"),
            },
            indent=2,
        )
        + "\n"
    )
    sys.path.insert(0, str(args.capture.parent.parent / "capture-runtime-v3"))
    from broad_support import replay_graph

    certificates = {}
    for cohort in ("full_workload", "heldout_test"):
        selected = [r for r in capture if cohort == "full_workload" or r["role"] == "test"]
        policy = None
        for max_depth in ("state", 28, 20, 14, 10, 7):
            programs = {}
            for t in sorted({r["filter"] for r in selected}):
                subset = [r for r in selected if r["filter"] == t]
                if max_depth == "state":
                    # Predict a stopping ordinal from the first causal frontier;
                    # store it in one ordinary query-local numeric register.
                    x = np.array([r["frames"][0]["values"] for r in subset], dtype=float)
                    targets = np.array(
                        [legacy[r["id"]]["ideal"]["checkpoint"] for r in subset], dtype=int
                    )
                    model = frontier_tree(x, targets)
                    if model is None:
                        break
                    name = "unfiltered" if t < 0 else "votes" + str(t)
                    first = ["eq", ["feature", "checkpoint"], 1]
                    programs[name] = {
                        "checkpoints": list(range(1, max(len(r["frames"]) for r in subset) + 1)),
                        "root": [
                            "if",
                            first,
                            ["eq", model, 1],
                            ["eq", ["feature", "checkpoint"], ["state", 0]],
                        ],
                        "updates": {"0": ["if", first, model, ["state", 0]]},
                    }
                    continue
                remaining = {r["id"]: r for r in subset}
                points = []
                maximum = max(len(r["frames"]) for r in subset)
                for cp in range(1, maximum + 1):
                    active = [r for r in remaining.values() if len(r["frames"]) >= cp]
                    if not active:
                        points.append((cp, False))
                        continue
                    y = np.array([cp in safe[r["id"]] for r in active], dtype=bool)
                    if not y.any():
                        points.append((cp, False))
                        continue
                    x = np.array(
                        [
                            [math.nan if v is None else v for v in r["frames"][cp - 1]["values"]]
                            for r in active
                        ],
                        dtype=float,
                    )
                    w = np.array(
                        [
                            max(1, r["native_layer0_work"] - r["frames"][cp - 1]["values"][1])
                            for r in active
                        ],
                        dtype=float,
                    )
                    root = tree(x, y, w, max_depth=max_depth)
                    for r, label in zip(active, y, strict=True):
                        stop = predict(root, r["frames"][cp - 1]["values"])
                        assert not stop or label
                        if stop:
                            del remaining[r["id"]]
                    points.append((cp, root))
                name = "unfiltered" if t < 0 else "votes" + str(t)
                programs[name] = {
                    "checkpoints": list(range(1, maximum + 1)),
                    "root": dispatch(points),
                    "updates": {},
                }
            if len(programs) != len({r["filter"] for r in selected}):
                continue
            candidate = {
                "schema": "fannagent.broad-stop.v3",
                "name": "oracle_feasible-broad-" + cohort,
                "rationale": (
                    "Hindsight causal frontier trees with bounded query-local state; "
                    "causal features only, fitted on this cohort. "
                    "Best found under deployment resource limits."
                ),
                "fuel": 2000000,
                "state_slots": int(max_depth == "state"),
                "programs": programs,
            }
            try:
                validate(candidate)
                graph = compile_graph(candidate)
                from fannproto3.compiler import compile_programs

                compile_programs([{"arm": 60, "policy": candidate, "force_continue": False}])
                policy = candidate
                break
            except ValueError as exc:
                print(
                    json.dumps({"cohort": cohort, "depth": max_depth, "rejected": str(exc)}),
                    flush=True,
                )
        assert policy is not None, "no deployable fit"
        choices = []
        ideal_matches = stops = exhausted = 0
        for r in selected:
            cp, frames = replay_graph(graph, r, trace=True)
            assert not cp or cp in safe[r["id"]]
            ideal = legacy[r["id"]]["ideal"]["checkpoint"]
            ideal_matches += cp == ideal
            stops += cp > 0
            exhausted += any(f["exhausted"] for f in frames)
            choices.append(
                {
                    "id": r["id"],
                    "checkpoint": cp,
                    "output": known[r["id"]][cp] if cp else r["native"],
                }
            )
        filename = "oracle_feasible-broad-" + cohort + ".json"
        (args.output / filename).write_text(
            json.dumps(policy, sort_keys=True, separators=(",", ":")) + "\n"
        )
        with (args.output / (cohort + "-choices.jsonl")).open("x") as out:
            for r in choices:
                out.write(json.dumps(r, separators=(",", ":")) + "\n")
        certificate = {
            "schema": "fannagent.broad-fit.v1",
            "cohort": cohort,
            "cases": len(selected),
            "policy_hash": policy_hash(policy),
            "cases_sha256": sha(args.capture / "cases.jsonl"),
            "fitter_sha256": sha(Path(__file__)),
            "max_tree_depth": None if max_depth == "state" else max_depth,
            "stops": stops,
            "matches_ideal_checkpoint": ideal_matches,
            "budget_fallbacks": exhausted,
            "recall_losses": 0,
            "uses_only_actual_prefix_labels": True,
            "hindsight_fit": True,
            "optimality_proven": False,
            "method": "first-frontier target prediction in one register"
            if max_depth == "state"
            else "checkpoint frontier thresholds with richer collision fallback",
            "choices_sha256": sha(args.output / (cohort + "-choices.jsonl")),
        }
        certificates[cohort] = certificate
        (args.output / (cohort + "-certificate.json")).write_text(
            json.dumps(certificate, indent=2) + "\n"
        )
        print(json.dumps(certificate), flush=True)
    host = BroadPolicyTools(
        args.output,
        args.output / "agent-registry",
        lambda p, c: {
            "hindsight_certificate": certificates[p["name"].removeprefix("oracle_feasible-broad-")]
        },
    )
    submission = {"policy_paths": ["oracle_feasible-broad-" + c + ".json" for c in certificates]}
    result = host.evaluate_broad_candidates(submission)
    (args.output / "agent-submission.json").write_text(
        json.dumps(
            {"tool": "evaluate_broad_candidates", "arguments": submission, "result": result},
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
