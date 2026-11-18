"""Portable, resource-bounded stopping programs; no fitting or evaluator access.

Programs are typed expression graphs with arbitrary Boolean structure, numeric
arithmetic, a declared checkpoint schedule and bounded query-local registers.
The limits bound deployment resources rather than prescribing a rule shape.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any

SCHEMA = "fannagent.broad-stop.v3"
FILTERS = ("unfiltered", "votes743", "votes527", "votes310", "votes192", "votes108", "votes32")
FEATURES = (
    "checkpoint",
    "layer0_distance_evaluations",
    "qualifying_count",
    "tenth_distance",
    "frontier_gap",
    "top10_new_since_previous",
    "first_distance",
    "fifth_distance",
    "frontier_distance",
    "retained_count",
    "previous_qualifying_count",
    "previous_tenth_distance",
    "previous_frontier_gap",
)
MAX_CHECKPOINT = 4096
MAX_NODES = 131072
MAX_DEPTH = 64
MAX_BYTES = 8 * 1024 * 1024
MAX_STATE = 32
MAX_FUEL = 16_000_000
COUNT, DISTANCE, TURNOVER, PREVIOUS, DECIDE, FRONTIER = 1, 2, 4, 8, 16, 32
OPS = (
    "number",
    "boolean",
    "feature",
    "state",
    "add",
    "sub",
    "mul",
    "div",
    "min",
    "max",
    "abs",
    "lt",
    "le",
    "gt",
    "ge",
    "eq",
    "and",
    "or",
    "not",
    "available",
    "if",
    "coalesce",
)
OPCODE = {name: i for i, name in enumerate(OPS)}
NUMERIC = {"add", "sub", "mul", "div", "min", "max"}
COMPARE = {"lt", "le", "gt", "ge", "eq"}


class PolicyError(ValueError):
    pass


def check(ok: bool, message: str) -> None:
    if not ok:
        raise PolicyError(message)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def policy_hash(policy: dict) -> str:
    validate(policy)
    return hashlib.sha256(canonical(policy).encode()).hexdigest()


def validate(policy: dict) -> dict:
    check(
        type(policy) is dict
        and set(policy) == {"schema", "name", "rationale", "fuel", "state_slots", "programs"},
        "expected schema/name/rationale/fuel/state_slots/programs",
    )
    check(policy["schema"] == SCHEMA, "incompatible broad policy schema")
    check(type(policy["name"]) is str and 0 < len(policy["name"]) <= 80, "invalid name")
    check(
        type(policy["rationale"]) is str and len(policy["rationale"]) <= 4000, "invalid rationale"
    )
    check(type(policy["fuel"]) is int and 1 <= policy["fuel"] <= MAX_FUEL, "fuel out of range")
    slots = policy["state_slots"]
    check(type(slots) is int and 0 <= slots <= MAX_STATE, "query-state size out of range")
    check(
        type(policy["programs"]) is dict and set(policy["programs"]) <= set(FILTERS),
        "unsupported predicate",
    )
    count = 0

    def visit(node, depth=0):
        nonlocal count
        count += 1
        check(count <= MAX_NODES and depth <= MAX_DEPTH, "program storage/stack budget exceeded")
        if type(node) is bool:
            return "bool"
        if type(node) in (int, float):
            check(math.isfinite(node) and abs(node) <= 1e300, "nonfinite/oversized constant")
            return "number"
        check(type(node) is list and len(node) >= 2 and type(node[0]) is str, "invalid expression")
        op, args = node[0], node[1:]
        if op == "feature":
            check(
                len(args) == 1 and type(args[0]) is str and args[0] in FEATURES,
                "unknown or evaluator-only feature",
            )
            return "number"
        if op == "state":
            check(
                len(args) == 1 and type(args[0]) is int and 0 <= args[0] < slots,
                "invalid query-local register",
            )
            return "number"
        check(op in OPCODE and op not in ("number", "boolean"), "unsupported operator")
        arity = 3 if op == "if" else 1 if op in ("not", "abs", "available") else 2
        check(len(args) == arity, "wrong operator arity")
        types = [visit(a, depth + 1) for a in args]
        if op == "if":
            check(types[0] == "bool" and types[1] == types[2], "invalid conditional types")
            return types[1]
        if op == "available":
            return "bool"
        if op in ("and", "or", "not"):
            check(all(t == "bool" for t in types), "Boolean arguments required")
            return "bool"
        check(all(t == "number" for t in types), "numeric arguments required")
        return "bool" if op in COMPARE else "number"

    for program in policy["programs"].values():
        check(
            type(program) is dict and set(program) == {"checkpoints", "root", "updates"},
            "invalid program fields",
        )
        cps = program["checkpoints"]
        check(
            type(cps) is list
            and all(type(c) is int and 1 <= c <= MAX_CHECKPOINT for c in cps)
            and cps == sorted(set(cps)),
            "checkpoints must ascend uniquely in 1..4096",
        )
        check(visit(program["root"]) == "bool", "decision root must be Boolean")
        updates = program["updates"]
        check(
            type(updates) is dict
            and all(
                type(k) is str and k.isdecimal() and str(int(k)) == k and 0 <= int(k) < slots
                for k in updates
            ),
            "invalid state-update destination",
        )
        for expression in updates.values():
            check(visit(expression) == "number", "state updates must be numeric")
    check(len(canonical(policy).encode()) <= MAX_BYTES, "artifact byte budget exceeded")
    return policy


def feature_mask(node) -> int:
    if type(node) is not list:
        return 0
    if node[0] == "feature":
        name = node[1]
        if name in ("checkpoint", "layer0_distance_evaluations"):
            return 0
        if name == "frontier_distance":
            return FRONTIER
        if name == "previous_qualifying_count":
            return COUNT | PREVIOUS
        if name.startswith("previous_"):
            return COUNT | DISTANCE | PREVIOUS
        if name == "top10_new_since_previous":
            return COUNT | DISTANCE | TURNOVER | PREVIOUS
        if name in ("qualifying_count", "retained_count"):
            return COUNT
        return COUNT | DISTANCE
    if node[0] == "state":
        return 0
    return sum_masks(feature_mask(a) for a in node[1:])


def sum_masks(values) -> int:
    mask = 0
    for value in values:
        mask |= value
    return mask


def plan(program: dict) -> dict[int, int]:
    # Constant continuation has no observable state outside this query.
    if program["root"] is False:
        return {}
    mask = feature_mask(program["root"]) | sum_masks(
        feature_mask(n) for n in program["updates"].values()
    )
    points = program["checkpoints"]
    result = {c: mask | DECIDE for c in points}
    if mask & PREVIOUS:
        dependency = COUNT | (DISTANCE if mask & DISTANCE else 0)
        for cp in points[:-1]:
            result[cp] |= dependency
    return result


@dataclass
class QueryState:
    registers: list[float]
    remaining: int
    exhausted: bool = False
    fault: bool = False
    previous: dict[str, float | None] = field(default_factory=dict)

    def charge(self, units=1):
        if self.exhausted or self.fault or self.remaining < units:
            self.exhausted = self.exhausted or self.remaining < units
            raise PolicyError("query execution budget exhausted or disabled")
        self.remaining -= units


def start(policy: dict) -> QueryState:
    return QueryState([0.0] * policy["state_slots"], policy["fuel"])


def evaluate(node, values, state: QueryState):
    state.charge()
    if type(node) in (bool, int, float):
        return node if type(node) is bool else float(node)
    op, args = node[0], node[1:]
    if op == "feature":
        value = values.get(args[0])
        return None if value is None else float(value)
    if op == "state":
        return state.registers[args[0]]
    a = evaluate(args[0], values, state)
    if op == "available":
        return a is not None
    if op == "not":
        return None if a is None else not a
    if op == "if":
        return None if a is None else evaluate(args[1] if a else args[2], values, state)
    if op == "and" and a is False or op == "or" and a is True:
        return a
    if op == "coalesce" and a is not None:
        return a
    if op == "abs":
        return None if a is None else abs(a)
    b = evaluate(args[1], values, state)
    if op == "coalesce":
        return b
    if op == "and":
        return False if b is False else None if a is None or b is None else True
    if op == "or":
        return True if b is True else None if a is None or b is None else False
    if a is None or b is None:
        return None
    if op in COMPARE:
        return {
            "lt": lambda: a < b,
            "le": lambda: a <= b,
            "gt": lambda: a > b,
            "ge": lambda: a >= b,
            "eq": lambda: a == b,
        }[op]()
    if op == "div" and b == 0:
        state.fault = True
        raise PolicyError("division by zero")
    try:
        value = {
            "add": lambda: a + b,
            "sub": lambda: a - b,
            "mul": lambda: a * b,
            "div": lambda: a / b,
            "min": lambda: min(a, b),
            "max": lambda: max(a, b),
        }[op]()
    except (OverflowError, ZeroDivisionError) as error:
        state.fault = True
        raise PolicyError("numeric fault") from error
    if not math.isfinite(value):
        state.fault = True
        raise PolicyError("nonfinite arithmetic")
    return value


def decide(program: dict, values: dict, state: QueryState) -> bool:
    if state.exhausted or state.fault:
        return False
    try:
        result = evaluate(program["root"], values, state)
        updates = {
            int(k): evaluate(node, values, state)
            for k, node in sorted(program["updates"].items(), key=lambda item: int(item[0]))
        }
        for k, value in updates.items():
            if value is not None:
                state.registers[k] = value
        return result is True
    except PolicyError:
        return False


def compile_graph(policy: dict) -> dict:
    """Typed constants and indexed nodes; the native VM interprets this frozen data."""
    validate(policy)
    nodes, indices = [], {}

    def emit(node):
        key = canonical(node)
        if key in indices:
            return indices[key]
        if type(node) in (bool, int, float):
            code = [OPCODE["boolean" if type(node) is bool else "number"], -1, -1, -1, float(node)]
        elif node[0] in ("feature", "state"):
            index = FEATURES.index(node[1]) if node[0] == "feature" else node[1]
            code = [OPCODE[node[0]], index, -1, -1, 0.0]
        else:
            args = [emit(a) for a in node[1:]]
            code = [OPCODE[node[0]], *args, *([-1] * (3 - len(args))), 0.0]
        indices[key] = len(nodes)
        check(len(nodes) < MAX_NODES, "compiled instruction-table budget exceeded")
        nodes.append(code)
        return indices[key]

    programs = {}
    for name, p in sorted(policy["programs"].items()):
        points = p["checkpoints"]
        steps = {}
        for cp in points:
            root = specialize(p["root"], cp)
            updates = {
                k: specialize(n, cp)
                for k, n in sorted(p["updates"].items(), key=lambda item: int(item[0]))
            }
            if p["root"] is False or root is False and not updates:
                steps[cp] = {"root": emit(False), "updates": {}, "mask": 0}
            else:
                mask = feature_mask(root) | sum_masks(feature_mask(n) for n in updates.values())
                steps[cp] = {
                    "root": emit(root),
                    "updates": {k: emit(n) for k, n in updates.items()},
                    "mask": mask | DECIDE,
                }
        for previous, cp in zip(points, points[1:]):
            mask = steps[cp]["mask"]
            if mask & PREVIOUS:
                steps[previous]["mask"] |= COUNT | (DISTANCE if mask & DISTANCE else 0)
        programs[name] = {"checkpoints": points, "steps": steps}
    return {
        "schema": SCHEMA,
        "policy_hash": policy_hash(policy),
        "features": FEATURES,
        "fuel": policy["fuel"],
        "state_slots": policy["state_slots"],
        "nodes": nodes,
        "programs": programs,
    }


class Executable:
    """Reference VM for the exact compiled graph and its execution-budget semantics."""

    def __init__(self, graph):
        self.graph = graph
        self.expressions = []
        for op, a, b, c, value in graph["nodes"]:
            name = OPS[op]
            if name in ("number", "boolean"):
                expression = bool(value) if name == "boolean" else value
            elif name == "feature":
                expression = [name, FEATURES[a]]
            elif name == "state":
                expression = [name, a]
            else:
                expression = [name, *(self.expressions[i] for i in (a, b, c) if i >= 0)]
            self.expressions.append(expression)

    def step(self, predicate, checkpoint, values, state, *, collection_units=0):
        program = self.graph["programs"].get(predicate)
        step = program and program["steps"].get(checkpoint)
        if not step or not step["mask"] or state.exhausted or state.fault:
            return False
        try:
            state.charge(collection_units)
            if not step["mask"] & DECIDE:
                return False
            source = {
                "root": self.expressions[step["root"]],
                "updates": {k: self.expressions[v] for k, v in step["updates"].items()},
            }
            return decide(source, values, state)
        except PolicyError:
            return False


def specialize(node, checkpoint):
    """Fold checkpoint-only branches before deriving feature dependencies."""
    if type(node) is not list:
        return node
    op, args = node[0], node[1:]
    if op == "feature":
        return float(checkpoint) if args[0] == "checkpoint" else node
    if op == "state":
        return node
    first = specialize(args[0], checkpoint)
    if op == "if" and type(first) is bool:
        return specialize(args[1] if first else args[2], checkpoint)
    if op == "and" and first is False or op == "or" and first is True:
        return first
    rest = [specialize(n, checkpoint) for n in args[1:]]
    expression = [op, first, *rest]
    if all(type(n) in (bool, int, float) for n in expression[1:]):
        state = QueryState([], MAX_FUEL)
        try:
            value = evaluate(expression, {}, state)
            # Preserve faulting code; an unreachable fault must remain unevaluated.
            if value is not None and not state.fault:
                return value
        except PolicyError:
            pass
    return expression
