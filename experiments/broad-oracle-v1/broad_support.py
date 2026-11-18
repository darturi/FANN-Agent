"""Reference compiled execution against causal capture; never a serving input."""

from broad_contract import (
    COUNT,
    DISTANCE,
    FEATURES,
    FRONTIER,
    PREVIOUS,
    TURNOVER,
    Executable,
    compile_graph,
    start,
)


def predicate(t):
    return "unfiltered" if t < 0 else "votes" + str(t)


def replay(policy, row, *, force_continue=False, trace=False):
    graph = compile_graph(policy)
    return replay_graph(graph, row, force_continue=force_continue, trace=trace)


_EXECUTABLES = {}


def replay_graph(graph, row, *, force_continue=False, trace=False):
    key = id(graph)
    if key not in _EXECUTABLES:
        _EXECUTABLES[key] = (graph, Executable(graph))
    vm = _EXECUTABLES[key][1]
    state = start(graph)
    program = graph["programs"].get(predicate(row["filter"]))
    previous = None
    frames = []
    if not program:
        return 0, frames
    source = {r["checkpoint"]: r for r in row["frames"]}
    previous_cp = 0
    for cp in program["checkpoints"]:
        if cp not in source:
            break
        step = program["steps"][cp]
        mask = step["mask"]
        if not mask or state.exhausted or state.fault:
            previous_cp = cp
            continue
        raw = source[cp]
        full = dict(zip(FEATURES, raw["values"], strict=True))
        values = {name: None for name in FEATURES}
        values["checkpoint"], values["layer0_distance_evaluations"] = (
            cp,
            full["layer0_distance_evaluations"],
        )
        units = 0
        if mask & COUNT:
            values["qualifying_count"] = full["qualifying_count"]
            values["retained_count"] = full["retained_count"]
            units += raw["count_units"]
        if mask & DISTANCE:
            for name in ("first_distance", "fifth_distance", "tenth_distance", "frontier_gap"):
                values[name] = full[name]
            units += 16 * int(full["qualifying_count"])
        if mask & (DISTANCE | FRONTIER):
            values["frontier_distance"] = full["frontier_distance"]
            units += 1
        same_previous = previous is not None and previous["cp"] == previous_cp and previous_cp > 0
        if mask & PREVIOUS and same_previous:
            for output, name in (
                ("previous_qualifying_count", "qualifying_count"),
                ("previous_tenth_distance", "tenth_distance"),
                ("previous_frontier_gap", "frontier_gap"),
            ):
                values[output] = previous["values"][name]
        if (
            mask & TURNOVER
            and same_previous
            and values["tenth_distance"] is not None
            and previous["values"]["tenth_distance"] is not None
        ):
            values["top10_new_since_previous"] = len(set(raw["top_tids"]) - set(previous["tids"]))
            units += 100
        decision = vm.step(predicate(row["filter"]), cp, values, state, collection_units=units)
        if mask & COUNT:
            previous = {"cp": cp, "values": values, "tids": raw["top_tids"]}
        if trace:
            frames.append(
                {
                    "checkpoint": cp,
                    "mask": mask,
                    "remaining": state.remaining,
                    "values": [values[n] for n in FEATURES],
                    "state": list(state.registers),
                    "decision": decision,
                    "exhausted": state.exhausted,
                    "fault": state.fault,
                }
            )
        if decision and not force_continue:
            return cp, frames
        previous_cp = cp
    return 0, frames


def verify_audit(expected, actual):
    assert len(expected) == len(actual["frames"]), "broad audit frame coverage differs"
    for reference, observed in zip(expected, actual["frames"], strict=True):
        for name in ("checkpoint", "mask", "decision", "exhausted", "fault"):
            assert reference[name] == observed[name], (name, reference, observed)
        # A failing collection can consume a partial prefix of its reserved work.
        if observed["exhausted"]:
            assert not observed["decision"] and observed["remaining"] >= 0
            continue
        assert reference["remaining"] == observed["remaining"], (reference, observed)
        for a, b in zip(reference["values"], observed["values"], strict=True):
            assert (a is None and b is None) or (
                a is not None and b is not None and abs(a - b) <= 1e-12
            ), (a, b, reference)
        assert reference["state"] == observed["state"], (reference, observed)
