"""Semantics and operational bounds of public agent programs."""

import pytest

from fannagent.api.broad_policy import (
    Executable,
    PolicyError,
    compile_graph,
    decide,
    start,
    validate,
)


def policy(root, *, updates=None, fuel=1000, slots=0):
    return {
        "schema": "fannagent.broad-stop.v3",
        "name": "test",
        "rationale": "test",
        "fuel": fuel,
        "state_slots": slots,
        "programs": {
            "unfiltered": {"checkpoints": [1, 2, 3, 9, 97], "root": root, "updates": updates or {}}
        },
    }


def test_richer_boolean_arithmetic_and_short_circuit():
    root = [
        "or",
        [
            "lt",
            [
                "div",
                ["feature", "frontier_gap"],
                ["add", ["abs", ["feature", "tenth_distance"]], 0.01],
            ],
            0.2,
        ],
        ["and", False, ["gt", ["div", 1, 0], 2]],
    ]
    p = validate(policy(root))
    state = start(p)
    assert decide(p["programs"]["unfiltered"], {"frontier_gap": 0.02, "tenth_distance": 0.4}, state)
    assert not state.fault
    assert not decide(
        p["programs"]["unfiltered"], {"frontier_gap": None, "tenth_distance": 0.4}, state
    )


def test_simultaneous_local_state_and_checkpoint_specialization():
    p = validate(
        policy(
            ["and", ["ge", ["feature", "checkpoint"], 3], ["ge", ["state", 0], 2]],
            updates={"0": ["add", ["state", 0], 1]},
            slots=1,
        )
    )
    vm = Executable(compile_graph(p))
    state = start(p)
    assert not vm.step("unfiltered", 1, {"checkpoint": 1}, state)
    assert not vm.step("unfiltered", 2, {"checkpoint": 2}, state)
    assert vm.step("unfiltered", 3, {"checkpoint": 3}, state)
    assert state.registers == [3]


def test_fault_and_budget_continue_for_rest_of_query():
    p = policy(["gt", ["div", 1, 0], 0])
    s = start(p)
    assert not decide(p["programs"]["unfiltered"], {}, s) and s.fault
    assert not decide({"root": True, "updates": {}}, {}, s)
    p = policy(["gt", ["feature", "qualifying_count"], 0], fuel=2)
    s = start(p)
    assert not decide(p["programs"]["unfiltered"], {"qualifying_count": 3}, s)
    assert s.exhausted


def test_unreachable_feature_collection_is_eliminated():
    p = policy(
        [
            "if",
            ["eq", ["feature", "checkpoint"], 9],
            ["gt", ["feature", "qualifying_count"], 7],
            False,
        ]
    )
    graph = compile_graph(p)
    steps = graph["programs"]["unfiltered"]["steps"]
    assert steps[1]["mask"] == 0 and steps[97]["mask"] == 0
    assert steps[9]["mask"] & 1


@pytest.mark.parametrize(
    "node",
    [
        ["feature", "query_id"],
        ["feature", "recall"],
        ["system", "echo"],
        ["state", 8],
        ["add", True, 3],
        ["div", 1],
    ],
)
def test_forbidden_inputs_and_malformed_code(node):
    with pytest.raises(PolicyError):
        validate(policy(node))
