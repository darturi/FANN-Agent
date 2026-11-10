"""Matched regression targets, group-pruned trees and portable shallow export."""

import math

import numpy as np
from common import check_limits, digest
from data import GRID, training_data
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.tree import DecisionTreeRegressor


def canonical_split(threshold, kind):
    # sklearn predicts with float32 inputs. Express its exact rounding partition
    # as a float64 runtime predicate, including midpoint ties-to-even.
    lower = np.float32(threshold)
    if float(lower) > threshold:
        lower = np.nextafter(lower, np.float32(-np.inf))
    upper = np.nextafter(lower, np.float32(np.inf))
    midpoint = (float(lower) + float(upper)) / 2
    inclusive = np.float32(midpoint) == lower
    if kind == "bool":
        return "bool_false", None
    if kind == "int":
        return "lte", int(math.floor(midpoint) if inclusive else math.ceil(midpoint) - 1)
    return ("lte" if inclusive else "lt"), midpoint


def split_mask(node, x):
    column = x[:, node["feature"]]
    if node["op"] == "bool_false":
        return column == 0
    if node["op"] == "lte":
        return column <= node["cut"]
    return column < node["cut"]


def tree_predict(node, x, field="value"):
    result = np.empty(len(x), dtype=float)
    pending = [(node, np.arange(len(x)))]
    while pending:
        n, ix = pending.pop()
        if "value" in n:
            result[ix] = n[field]
            continue
        mask = split_mask(n, x[ix])
        pending.extend([(n["left"], ix[mask]), (n["right"], ix[~mask])])
    return result


def model_predict(model, x):
    if not len(x):
        return np.empty((0, 2))
    return np.column_stack(
        [
            np.mean([tree_predict(t, x, field) for t in model["trees"]], axis=0)
            for field in ["value", "benefit"]
        ]
    )


def export_tree(estimator, x, loss, benefit, weights, groups, kinds, *, prune):
    t = estimator.tree_

    def node(i, ix):
        if not len(ix):
            raise ValueError("Empty fitted partition")
        count = len(set(groups[ix]))
        leaf = {
            "value": float(np.clip(np.average(loss[ix], weights=weights[ix]), 0, 1)),
            "benefit": float(np.average(benefit[ix], weights=weights[ix])),
            "groups": count,
            "rows": len(ix),
            "weight": float(weights[ix].sum()),
        }
        if t.children_left[i] == t.children_right[i]:
            return leaf
        feature = int(t.feature[i])
        op, cut = canonical_split(float(t.threshold[i]), kinds[feature])
        record = {"feature": feature, "op": op, "cut": cut}
        mask = split_mask(record, x[ix])
        left, right = ix[mask], ix[~mask]
        if prune and min(len(set(groups[left])), len(set(groups[right]))) < 8:
            return {**leaf, "pruned_for_group_support": True}
        return {
            **record,
            "left": node(t.children_left[i], left),
            "right": node(t.children_right[i], right),
        }

    return node(0, np.arange(len(x)))


def leaf_groups(node):
    if "value" in node:
        return [node["groups"]]
    return leaf_groups(node["left"]) + leaf_groups(node["right"])


def node_count(node):
    return 1 if "value" in node else 1 + node_count(node["left"]) + node_count(node["right"])


def fit(data, profile, method, groups, check_x=None):
    check_limits(fit=True)
    x, loss, benefit, weights, ids, receipt = training_data(data, profile, groups)
    params = dict(criterion="squared_error", min_samples_leaf=8, random_state=20261024)
    if method == "shallow_tree":
        estimator = DecisionTreeRegressor(max_depth=3, splitter="best", **params)
    elif method == "extra_trees":
        estimator = ExtraTreesRegressor(
            n_estimators=64, max_depth=8, max_features=1.0, bootstrap=False, n_jobs=1, **params
        )
    else:
        raise ValueError("Undeclared method")
    estimator.fit(x, loss, sample_weight=weights)
    estimators = [estimator] if method == "shallow_tree" else estimator.estimators_
    kinds = [data.definitions[n]["kind"] for n in data.names[profile]]
    unpruned = {
        "trees": [
            export_tree(e, x, loss, benefit, weights, ids, kinds, prune=False) for e in estimators
        ]
    }
    tested = x if check_x is None else np.concatenate([x, check_x])
    if not np.allclose(
        estimator.predict(tested), model_predict(unpruned, tested)[:, 0], rtol=1e-12, atol=1e-10
    ):
        raise ValueError("Canonical risk predictions differ from sklearn")
    model = {
        "version": "risk-partition-benefit-leaves.v1",
        "method": method,
        "profile": profile,
        "feature_names": data.names[profile],
        "trees": [
            export_tree(e, x, loss, benefit, weights, ids, kinds, prune=True) for e in estimators
        ],
    }
    minimum = min(min(leaf_groups(t)) for t in model["trees"])
    if minimum < 8:
        raise ValueError("Leaf support is not eight distinct fitting vectors")
    receipt.update(
        method=method,
        profile=profile,
        model_sha256=digest(model),
        training_vector_count=len(groups),
        sklearn_parameters=estimator.get_params(),
        unpruned_sklearn_risk_prediction_parity=True,
        parity_rows=len(tested),
        minimum_distinct_training_vectors_per_leaf=minimum,
        nodes_before_group_pruning=sum(node_count(t) for t in unpruned["trees"]),
        nodes_after_group_pruning=sum(node_count(t) for t in model["trees"]),
        individual_trees=len(estimators),
        benefit_fitted_on_same_partitions_only=True,
    )
    check_limits()
    return model, receipt


def grid_scores(data, profile, model, indices):
    result = np.empty((len(indices), 8, 2))
    result[:, :, 0] = np.inf
    result[:, :, 1] = -np.inf
    q, j = np.where(data.reached[indices])
    result[q, j] = model_predict(model, data.x[profile][indices[q], j])
    return result


def first_actions(scores, risk_cap, benefit_floor):
    stops = (
        (scores[:, :, 0] <= risk_cap)
        & (scores[:, :, 1] >= benefit_floor)
        & np.isfinite(scores).all(axis=2)
    )
    return np.where(stops.any(axis=1), stops.argmax(axis=1), 8).astype(int)


def references(value):
    if isinstance(value, dict):
        if "feature" in value:
            yield value["feature"]
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def combine(op, expressions):
    if not expressions:
        return {"bool": True}
    if len(expressions) == 1:
        return expressions[0]
    n = len(expressions) // 2
    return {"op": op, "args": [combine(op, expressions[:n]), combine(op, expressions[n:])]}


def shallow_policy(model, risk_cap, benefit_floor):
    if model["method"] != "shallow_tree" or len(model["trees"]) != 1:
        raise ValueError("Ensemble is not a portable shallow policy")
    names = model["feature_names"]

    def compile_node(node):
        if "value" in node:
            return (
                "stop"
                if node["value"] <= risk_cap and node["benefit"] >= benefit_floor
                else "continue"
            )
        name = names[node["feature"]]
        if node["op"] == "bool_false":
            predicate = {"op": "eq", "args": [{"feature": name}, {"bool": False}]}
        else:
            kind = "int" if isinstance(node["cut"], int) else "float"
            predicate = {"op": node["op"], "args": [{"feature": name}, {kind: node["cut"]}]}
        return {
            "if": predicate,
            "then": compile_node(node["left"]),
            "else": compile_node(node["right"]),
        }

    root = compile_node(model["trees"][0])
    required = sorted(set(references(root)) | {"checkpoint_index"})
    guard = combine(
        "and",
        [
            combine("and", [{"op": "is_available", "args": [{"feature": n}]} for n in required]),
            combine(
                "or",
                [
                    {"op": "eq", "args": [{"feature": "checkpoint_index"}, {"int": cp}]}
                    for cp in GRID
                ],
            ),
        ],
    )
    groups = ["basic", "work", "queue", "distances", "local_filter"]
    if model["profile"] == "progress34":
        groups.append("progress_filter")
    return {
        "name": "p3c-shallow-development-only",
        "feature_groups": groups,
        "root": {"if": guard, "then": root, "else": "continue"},
    }


def continue_policy(profile):
    groups = ["basic", "work", "queue", "distances", "local_filter"]
    if profile == "progress34":
        groups.append("progress_filter")
    return {"name": "p3c-explicit-continue", "feature_groups": groups, "root": "continue"}


def verify_shared_interpreter(data, profile, raw, indices, expected, runtime):
    from fannagent.api import FeatureValue, PolicyInput, validate_policy
    from fannagent.api.primitives.interpreter import evaluate_policy

    artifact = validate_policy(raw, runtime)
    names = sorted(set(references(raw["root"])))
    floats = frozenset(n for n in names if runtime.runtime_features[n].kind == "float")
    columns = [data.names[profile].index(n) for n in names]
    checked = 0
    for i, wanted in zip(indices, expected):
        actual = 8
        start, end = data.slices[i]
        for ordinal in range(1, end - start + 1):
            # The validated canonical guard proves all off-grid states continue.
            if ordinal not in GRID and raw["root"] != "continue":
                continue
            values = data.full_x[profile][start + ordinal - 1, columns]

            def typed(name, value):
                kind = data.definitions[name]["kind"]
                return (
                    bool(value) if kind == "bool" else int(value) if kind == "int" else float(value)
                )

            inp = PolicyInput(
                features={
                    n: FeatureValue(available=True, value=typed(n, v))
                    for n, v in zip(names, values)
                }
            )
            checked += 1
            if str(evaluate_policy(artifact, inp, float_features=floats)) == "stop":
                actual = GRID.index(ordinal)
                break
        if actual != wanted:
            raise ValueError("First-stop action differs from shared policy interpreter")
    return {
        "cases": len(indices),
        "interpreter_state_checks": checked,
        "policy_hash": artifact.policy_hash,
        "validated_depth_at_most_four": True,
        "native_execution": False,
    }
