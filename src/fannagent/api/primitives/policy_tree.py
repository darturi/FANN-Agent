from __future__ import annotations

import math
from typing import Any, Final

MAX_POLICY_NODES: Final = 255
MAX_POLICY_DEPTH: Final = 8
MAX_SHAPE_MODEL_BYTES: Final = 64 * 1024

INT64_MIN: Final = -(2**63)
INT64_MAX: Final = 2**63 - 1

LEAF_ACTIONS: Final = {"continue", "stop"}
UNARY_OPERATORS: Final = {"not", "is_available"}
BINARY_OPERATORS: Final = {
    "and",
    "or",
    "add",
    "sub",
    "mul",
    "div",
    "eq",
    "lt",
    "lte",
    "gt",
    "gte",
}


def validate_node(
    root: dict[str, Any] | str, *, feature_kinds: dict[str, str] | None = None
) -> None:
    count = 0
    if feature_kinds is None:
        feature_kinds = {}

    def visit(node: Any, depth: int, *, decision_position: bool) -> str:
        nonlocal count
        count += 1
        if count > MAX_POLICY_NODES:
            raise ValueError(f"policy exceeds {MAX_POLICY_NODES} nodes")
        if depth > MAX_POLICY_DEPTH:
            raise ValueError(f"policy exceeds depth {MAX_POLICY_DEPTH}")
        if decision_position and isinstance(node, str):
            if node not in LEAF_ACTIONS:
                raise ValueError(f"unknown policy action: {node!r}")
            return "decision"
        if not isinstance(node, dict) or not node:
            raise ValueError("policy nodes must be nonempty objects")
        keys = set(node)
        if keys == {"if", "then", "else"}:
            condition_type = visit(node["if"], depth + 1, decision_position=False)
            if condition_type != "bool":
                raise ValueError("if condition must evaluate to bool")
            visit(node["then"], depth + 1, decision_position=True)
            visit(node["else"], depth + 1, decision_position=True)
            return "decision"
        if decision_position:
            raise ValueError("decision positions require an action or if/then/else node")
        if keys == {"feature"}:
            feature = node["feature"]
            if not isinstance(feature, str):
                raise ValueError("policy feature must be a string")
            if feature not in feature_kinds:
                raise ValueError(f"unknown policy feature: {feature!r}")
            return feature_kinds[feature]
        if keys == {"int"}:
            value = node["int"]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("int literal must be an integer")
            if not INT64_MIN <= value <= INT64_MAX:
                raise ValueError("int literal must fit in int64")
            return "int"
        if keys == {"float"}:
            value = node["float"]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("float literal must be numeric")
            if not math.isfinite(float(value)):
                raise ValueError("float literal must be finite")
            return "float"
        if keys == {"bool"}:
            if not isinstance(node["bool"], bool):
                raise ValueError("bool literal must be Boolean")
            return "bool"
        if keys == {"op", "args"}:
            op = node["op"]
            args = node["args"]
            if not isinstance(op, str):
                raise ValueError("policy operator must be a string")
            if op not in UNARY_OPERATORS | BINARY_OPERATORS:
                raise ValueError(f"unknown policy operator: {op!r}")
            expected = 1 if op in UNARY_OPERATORS else 2
            if not isinstance(args, list) or len(args) != expected:
                raise ValueError(f"operator {op!r} requires {expected} arguments")
            if op == "is_available" and (
                not isinstance(args[0], dict) or set(args[0]) != {"feature"}
            ):
                raise ValueError("is_available requires a direct feature reference")
            argument_types = [visit(arg, depth + 1, decision_position=False) for arg in args]
            return _operator_result_type(op, argument_types)
        raise ValueError(f"invalid policy node keys: {sorted(keys)}")

    result_type = visit(root, 1, decision_position=True)
    if result_type != "decision":
        raise ValueError("policy root must be a decision")


def _operator_result_type(op: str, argument_types: list[str]) -> str:
    if op == "is_available":
        return "bool"
    if op == "not":
        if argument_types != ["bool"]:
            raise ValueError("not requires a Boolean argument")
        return "bool"
    if op in {"and", "or"}:
        if argument_types != ["bool", "bool"]:
            raise ValueError(f"{op} requires Boolean arguments")
        return "bool"
    if op in {"add", "sub", "mul", "div"}:
        if not all(item in {"int", "float"} for item in argument_types):
            raise ValueError(f"{op} requires numeric arguments")
        if argument_types[0] != argument_types[1]:
            raise ValueError(f"{op} requires arguments with the same numeric type")
        if op == "div" or "float" in argument_types:
            return "float"
        return "int"
    if op == "eq":
        if argument_types[0] != argument_types[1]:
            raise ValueError("eq requires compatible argument types")
        return "bool"
    if op in {"lt", "lte", "gt", "gte"}:
        if not all(item in {"int", "float"} for item in argument_types):
            raise ValueError(f"{op} requires numeric arguments")
        if argument_types[0] != argument_types[1]:
            raise ValueError(f"{op} requires arguments with the same numeric type")
        return "bool"
    raise AssertionError(op)
