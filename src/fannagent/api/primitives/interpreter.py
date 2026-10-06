from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .errors import ValidationError
from .policy_tree import INT64_MAX, INT64_MIN


class PolicyDecision(StrEnum):
    CONTINUE = "continue"
    STOP = "stop"


@dataclass(frozen=True)
class _Unavailable:
    pass


UNAVAILABLE = _Unavailable()


def evaluate_policy(
    artifact: Any, policy_input: Any, *, float_features: frozenset[str] = frozenset()
) -> PolicyDecision:
    """Evaluate policy/v1 with explicit, portable numeric and availability rules."""

    decision = _evaluate_decision(artifact.root, policy_input, float_features)
    return PolicyDecision(decision)


def _evaluate_decision(
    node: dict[str, Any] | str, policy_input: Any, float_features: frozenset[str]
) -> str:
    if isinstance(node, str):
        return node
    condition = _evaluate_expression(node["if"], policy_input, float_features)
    if condition is UNAVAILABLE:
        raise ValidationError("policy condition depends on an unavailable feature")
    if not isinstance(condition, bool):
        raise ValidationError("policy condition did not evaluate to bool")
    branch = node["then"] if condition else node["else"]
    return _evaluate_decision(branch, policy_input, float_features)


def _evaluate_expression(
    node: dict[str, Any], policy_input: Any, float_features: frozenset[str]
) -> Any:
    if "feature" in node:
        feature = policy_input.features.get(node["feature"])
        if feature is None or not feature.available:
            return UNAVAILABLE
        value = feature.value
        if node["feature"] in float_features:
            return _checked_float(value)
        return value
    if "int" in node:
        return node["int"]
    if "float" in node:
        return _checked_float(node["float"])
    if "bool" in node:
        return node["bool"]

    op = node["op"]
    values = [_evaluate_expression(arg, policy_input, float_features) for arg in node["args"]]
    if op == "is_available":
        return values[0] is not UNAVAILABLE
    if any(value is UNAVAILABLE for value in values):
        return UNAVAILABLE
    if op == "not":
        return not values[0]
    if op == "and":
        return values[0] and values[1]
    if op == "or":
        return values[0] or values[1]
    if op == "eq":
        return values[0] == values[1]
    if op == "lt":
        return values[0] < values[1]
    if op == "lte":
        return values[0] <= values[1]
    if op == "gt":
        return values[0] > values[1]
    if op == "gte":
        return values[0] >= values[1]
    if op == "div":
        if values[1] == 0:
            raise ValidationError("policy division by zero")
        if any(isinstance(value, int) and abs(value) > 2**53 for value in values):
            raise ValidationError("policy integer division would lose float64 precision")
        return _checked_float(float(values[0]) / float(values[1]))
    if op in {"add", "sub", "mul"}:
        result = {
            "add": lambda: values[0] + values[1],
            "sub": lambda: values[0] - values[1],
            "mul": lambda: values[0] * values[1],
        }[op]()
        if isinstance(result, int):
            if not INT64_MIN <= result <= INT64_MAX:
                raise ValidationError("policy int64 arithmetic overflow")
            return result
        return _checked_float(result)
    raise AssertionError(op)


def _checked_float(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError("policy float operation produced a non-finite value")
    return result
