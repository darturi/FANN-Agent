from __future__ import annotations

from typing import Any

import numpy as np

from .contracts import (
    MAX_FILTER_DEPTH,
    MAX_FILTER_LEAVES,
    MAX_MEMBERSHIP_VALUES,
    MAX_STRING_BYTES,
)
from .data import DatasetManifest, FieldType
from .errors import ValidationError

COMPARISONS = {"eq", "in", "lt", "lte", "gt", "gte"}
NULL_TESTS = {"is_null", "is_not_null"}
BOOLEANS = {"and", "or", "not"}


def validate_filter(expr: dict[str, Any] | None, manifest: DatasetManifest) -> None:
    leaves = [0]
    _validate_filter(expr, manifest, depth=0, leaves=leaves)


def _validate_filter(
    expr: dict[str, Any] | None,
    manifest: DatasetManifest,
    *,
    depth: int,
    leaves: list[int],
) -> None:
    if expr is None:
        return
    if depth > MAX_FILTER_DEPTH:
        raise ValidationError(f"filter exceeds maximum depth {MAX_FILTER_DEPTH}")
    if not isinstance(expr, dict) or not expr:
        raise ValidationError("filter must be a nonempty object")
    keys = set(expr)
    boolean_keys = keys.intersection(BOOLEANS)
    if boolean_keys:
        if len(boolean_keys) != 1 or len(keys) != 1:
            raise ValidationError("a Boolean filter must contain exactly one of and/or/not")
        op = next(iter(boolean_keys))
        children = expr[op]
        if op == "not":
            if not isinstance(children, dict):
                raise ValidationError("not requires one filter object")
            _validate_filter(children, manifest, depth=depth + 1, leaves=leaves)
            return
        if not isinstance(children, list) or not children:
            raise ValidationError(f"{op} requires a nonempty list")
        for child in children:
            _validate_filter(child, manifest, depth=depth + 1, leaves=leaves)
        return
    null_test = expr.get("op") in NULL_TESTS
    if keys != ({"field", "op"} if null_test else {"field", "op", "value"}):
        raise ValidationError(
            "comparison filters require field, op, and value; null tests require field and op"
        )
    leaves[0] += 1
    if leaves[0] > MAX_FILTER_LEAVES:
        raise ValidationError(f"filter exceeds maximum leaf count {MAX_FILTER_LEAVES}")
    field_map = {item.name: item for item in manifest.metadata_fields if item.filterable}
    field = expr["field"]
    op = expr["op"]
    value = expr.get("value")
    if field not in field_map:
        raise ValidationError(f"field is not declared filterable: {field!r}")
    if null_test:
        if manifest.schema_version < 2:
            raise ValidationError("null predicates require dataset schema version 2")
        return
    if op not in COMPARISONS:
        raise ValidationError(f"unsupported comparison operator: {op!r}")
    if value is None:
        raise ValidationError("null filter values are not supported")
    field_type = field_map[field].type
    if op in {"lt", "lte", "gt", "gte"} and field_type not in {
        FieldType.INTEGER,
        FieldType.FLOAT,
    }:
        raise ValidationError(f"{op} requires a numeric field")
    if op == "in" and (not isinstance(value, list) or not value):
        raise ValidationError("in requires a nonempty list value")
    if op == "in" and len(value) > MAX_MEMBERSHIP_VALUES:
        raise ValidationError(f"in exceeds maximum value count {MAX_MEMBERSHIP_VALUES}")
    values = value if op == "in" else [value]
    for candidate in values:
        if isinstance(candidate, float) and not np.isfinite(candidate):
            raise ValidationError("numeric filter values must be finite")
        if not _matches_type(candidate, field_type):
            raise ValidationError(f"value {candidate!r} does not match {field_type.value}")
        if (
            field_type == FieldType.INTEGER
            and not np.iinfo(np.int64).min <= candidate <= np.iinfo(np.int64).max
        ):
            raise ValidationError("integer filter values must fit in int64")
        if field_type == FieldType.FLOAT and isinstance(candidate, int) and abs(candidate) > 2**53:
            raise ValidationError("integer-valued float literals must be exactly representable")
        if isinstance(candidate, str) and len(candidate.encode("utf-8")) > MAX_STRING_BYTES:
            raise ValidationError(f"string filter value exceeds {MAX_STRING_BYTES} UTF-8 bytes")


def _matches_type(value: Any, field_type: FieldType) -> bool:
    if field_type == FieldType.BOOLEAN:
        return isinstance(value, bool)
    if field_type == FieldType.INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type == FieldType.FLOAT:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if field_type == FieldType.STRING:
        return isinstance(value, str)
    return False


def evaluate_filter(expr: dict[str, Any] | None, metadata: dict[str, np.ndarray]) -> np.ndarray:
    """SQL three-valued logic: retain only true rows, including under nested NOT."""
    size = len(next(iter(metadata.values()))) if metadata else 0

    def masks(node: dict[str, Any] | None) -> tuple[np.ndarray, np.ndarray]:
        if node is None:
            return np.ones(size, dtype=bool), np.zeros(size, dtype=bool)
        if "not" in node:
            true, false = masks(node["not"])
            return false, true
        for op in ("and", "or"):
            if op in node:
                children = [masks(child) for child in node[op]]
                true_op = np.logical_and if op == "and" else np.logical_or
                false_op = np.logical_or if op == "and" else np.logical_and
                return true_op.reduce([p[0] for p in children]), false_op.reduce(
                    [p[1] for p in children]
                )
        column = metadata[node["field"]]
        present = ~np.ma.getmaskarray(column)
        values = np.ma.getdata(column)
        op = node["op"]
        if op in NULL_TESTS:
            true = ~present if op == "is_null" else present
            return true, ~true
        target = node["value"]
        true = {
            "eq": lambda: values == target,
            "in": lambda: np.isin(values, target),
            "lt": lambda: values < target,
            "lte": lambda: values <= target,
            "gt": lambda: values > target,
            "gte": lambda: values >= target,
        }[op]()
        return present & true, present & ~true

    return masks(expr)[0]
