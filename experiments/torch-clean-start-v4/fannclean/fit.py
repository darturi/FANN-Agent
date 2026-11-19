"""Generic, data-free threshold/linear/tree synthesis. Only caller-supplied observations."""

import hashlib

import numpy as np

try:
    from broad_contract import FEATURES, validate
except ImportError:
    from fannagent.api.broad_policy import FEATURES, validate


def tree(x, y, features, depth, min_leaf, costs):
    if len(y) < min_leaf or not y.any():
        return False
    if y.all():
        return True
    if not depth:
        return False
    best = None
    parent = len(y) * y.mean() * (1 - y.mean())
    for j, name in enumerate(features):
        finite = np.isfinite(x[:, j])
        values = np.unique(x[finite, j])
        cuts = (values[:-1] + values[1:]) / 2
        if len(cuts) > 128:
            cuts = np.unique(np.quantile(cuts, np.linspace(0, 1, 128)))
        for cut in cuts:
            left = finite & (x[:, j] <= cut)
            if min(left.sum(), (~left).sum()) < min_leaf:
                continue
            impurity = sum(len(v) * v.mean() * (1 - v.mean()) for v in (y[left], y[~left]))
            gain = (parent - impurity) / max(float(costs.get(name, 1)), 1e-9)
            if best is None or gain > best[0]:
                best = (gain, j, float(cut), left)
    if best is None:
        return False
    _, j, cut, left = best
    a = tree(x[left], y[left], features, depth - 1, min_leaf, costs)
    b = tree(x[~left], y[~left], features, depth - 1, min_leaf, costs)
    return [
        "if",
        ["available", ["feature", features[j]]],
        ["if", ["le", ["feature", features[j]], cut], a, b],
        False,
    ]


def predict(node, values):
    if type(node) in (bool, int, float):
        return node
    op, args = node[0], node[1:]
    if op == "feature":
        return values.get(args[0])
    if op == "available":
        v = predict(args[0], values)
        return v is not None and np.isfinite(v)
    if op == "if":
        return predict(args[1] if predict(args[0], values) else args[2], values)
    if op == "and":
        return bool(predict(args[0], values)) and bool(predict(args[1], values))
    a, b = (predict(n, values) for n in args)
    if a is None or b is None:
        return False
    return {"le": lambda: a <= b, "gt": lambda: a > b, "add": lambda: a + b, "mul": lambda: a * b}[
        op
    ]()


def classifier(x, y, features, method, depth, min_leaf, costs):
    if method not in ("threshold", "linear", "tree"):
        raise ValueError("method must be threshold, linear, or tree")
    if len(y) < min_leaf or not y.any():
        return False
    if y.all():
        return True
    if method == "tree":
        return tree(x, y, features, depth, min_leaf, costs)
    if method == "threshold":
        best = (0, False)
        for j, name in enumerate(features):
            finite = np.isfinite(x[:, j])
            for sign in (1, -1):
                negatives = sign * x[finite & ~y, j]
                if not len(negatives):
                    continue
                threshold = float(np.nextafter(negatives.max(), np.inf))
                fire = finite & (sign * x[:, j] > threshold)
                if fire.sum() > best[0]:
                    comparison = ["gt", ["mul", float(sign), ["feature", name]], threshold]
                    best = (int(fire.sum()), ["and", ["available", ["feature", name]], comparison])
        return best[1]
    if method != "linear":
        raise ValueError("method must be threshold, linear, or tree")
    finite = np.isfinite(x).all(axis=1)
    xx, yy = x[finite], y[finite]
    if len(yy) < min_leaf or not yy.any() or yy.all():
        return False
    mean, scale = xx.mean(0), xx.std(0) + 1e-9
    z = np.c_[(xx - mean) / scale, np.ones(len(xx))]
    w = np.zeros(z.shape[1])
    for _ in range(300):
        probability = 1 / (1 + np.exp(-np.clip(z @ w, -40, 40)))
        w -= 0.2 * (z.T @ (probability - yy) / len(yy) + 0.01 * np.r_[w[:-1], 0])
    threshold = float(np.nextafter((z @ w)[~yy].max(), np.inf))
    weights = w[:-1] / scale
    expression = float(w[-1] - np.sum(weights * mean))
    guard = True
    for name, weight in zip(features, weights, strict=True):
        expression = ["add", expression, ["mul", float(weight), ["feature", name]]]
        guard = ["and", guard, ["available", ["feature", name]]]
    return ["and", guard, ["gt", expression, threshold]]


def fit(
    records, *, run_id, method, features, checkpoints, depth=6, min_leaf=4, costs=None, folds=5
):
    if not records or any(
        r.get("run_id") != run_id or r.get("query_ordinal", 0) <= 0 for r in records
    ):
        raise ValueError("only this run's executed observations may be fitted")
    if not features or not set(features) <= set(FEATURES) or not 1 <= depth <= 28 or min_leaf < 1:
        raise ValueError("invalid generic fitting settings")
    if (
        not checkpoints
        or checkpoints != sorted(set(checkpoints))
        or any(type(c) is not int or not 1 <= c <= 4096 for c in checkpoints)
        or type(folds) is not int
        or folds < 2
    ):
        raise ValueError("legal checkpoint schedule and at least two group folds required")
    if costs and any(k not in FEATURES or not np.isfinite(v) or v <= 0 for k, v in costs.items()):
        raise ValueError("feature costs must be finite and positive")
    excluded = 0
    if any(n.startswith("previous_") or n == "top10_new_since_previous" for n in features):
        compatible = [r for r in records if r.get("observation_schedule") == checkpoints]
        excluded = len(records) - len(compatible)
        records = compatible
        if not records:
            raise ValueError(
                "previous/turnover features require the identical observation schedule"
            )
    programs, validation = {}, []
    for t in sorted({r["filter"] for r in records}):
        nodes = []
        for cp in checkpoints:
            selected = [
                r
                for r in records
                if r["filter"] == t and r["checkpoint"] == cp and r.get("label") is not None
            ]
            if not selected:
                nodes.append((cp, False))
                continue
            x = np.array(
                [
                    [np.nan if r["features"].get(f) is None else r["features"][f] for f in features]
                    for r in selected
                ]
            )
            y = np.array(
                [r["label"]["safe"] and r["label"]["count_preserving"] for r in selected],
                dtype=bool,
            )
            split = np.array(
                [
                    int(hashlib.sha256(r["group"].encode()).hexdigest()[:8], 16) % folds
                    for r in selected
                ]
            )
            false_stops = stops = 0
            for k in range(folds):
                train, test = split != k, split == k
                model = classifier(
                    x[train], y[train], features, method, depth, min_leaf, costs or {}
                )
                for r, positive in zip(
                    np.array(selected, dtype=object)[test], y[test], strict=True
                ):
                    fired = bool(predict(model, r["features"]))
                    stops += fired
                    false_stops += fired and not positive
            model = classifier(x, y, features, method, depth, min_leaf, costs or {})
            nodes.append((cp, model))
            validation.append(
                {
                    "filter": t,
                    "checkpoint": cp,
                    "samples": len(y),
                    "groups": len({r["group"] for r in selected}),
                    "cross_validated_stops": stops,
                    "cross_validated_false_stops": false_stops,
                }
            )
        root = False
        for cp, node in reversed(nodes):
            root = ["if", ["eq", ["feature", "checkpoint"], cp], node, root]
        programs["unfiltered" if t < 0 else f"votes{t}"] = {
            "checkpoints": checkpoints,
            "root": root,
            "updates": {},
        }
    policy = {
        "schema": "fannagent.broad-stop.v3",
        "name": "own-evidence-" + method,
        "rationale": (
            "Fitted only on observations acquired within this run; "
            "group CV is diagnostic, not a safety guarantee."
        ),
        "fuel": 16000000,
        "state_slots": 0,
        "programs": programs,
    }
    validate(policy)
    return {
        "policy": policy,
        "validation": validation,
        "native_validation_required": True,
        "excluded_incompatible_schedule_records": excluded,
    }
