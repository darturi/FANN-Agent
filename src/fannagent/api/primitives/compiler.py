from __future__ import annotations

from typing import Any

from .errors import ValidationError


def compile_tree(artifact: Any, *, header: str) -> str:
    """Emit the shared bounded instruction set with an integration-owned header."""
    instructions: list[str] = []

    def emit(value: str) -> int:
        instructions.append(value)
        return len(instructions) - 1

    def expression(node: dict[str, Any]) -> None:
        if "feature" in node:
            emit(f"FEATURE\t{node['feature']}")
            return
        if "int" in node:
            emit(f"INT\t{node['int']}")
            return
        if "float" in node:
            emit(f"FLOAT\t{float(node['float']):.17g}")
            return
        if "bool" in node:
            emit(f"BOOL\t{1 if node['bool'] else 0}")
            return
        for argument in node["args"]:
            expression(argument)
        emit(f"OP\t{node['op']}")

    def decision(node: dict[str, Any] | str) -> None:
        if isinstance(node, str):
            emit(f"RETURN\t{node}")
            return
        expression(node["if"])
        branch = emit("JIF\t-1")
        decision(node["then"])
        instructions[branch] = f"JIF\t{len(instructions)}"
        decision(node["else"])

    decision(artifact.root)
    if len(instructions) > 1024:
        raise ValidationError("compiled policy exceeds 1024 instructions")
    return "\n".join([header, *instructions])


def predicate_leaf_count(expr: dict[str, Any] | None) -> int:
    if expr is None:
        return 0
    if "and" in expr:
        return sum(predicate_leaf_count(child) for child in expr["and"])
    if "or" in expr:
        return sum(predicate_leaf_count(child) for child in expr["or"])
    if "not" in expr:
        return predicate_leaf_count(expr["not"])
    return 1
