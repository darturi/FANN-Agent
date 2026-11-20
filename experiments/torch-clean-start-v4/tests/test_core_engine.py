import copy
import json
import uuid

import pytest
from fannclean.core import (
    FILTERS,
    Ledger,
    Limits,
    append_evidence,
    digest,
    prepare,
    read,
    verify_initial,
    write,
)
from fannclean.engine import Engine, empty
from fannclean.report import analyze
from fannclean.search import qualified, quality_ok
from fannclean.timing import summarize

from fannagent.api.broad_policy import FEATURES


def policy(name="good", root=True, cp=4):
    return {
        **empty(),
        "name": name,
        "programs": {
            key: {"checkpoints": [cp], "root": root, "updates": {}}
            for key in (
                "unfiltered",
                "votes743",
                "votes527",
                "votes310",
                "votes192",
                "votes108",
                "votes32",
            )
        },
    }


class SyntheticBackend:
    """Unit fixture only. Never starts a database, compiler, subprocess or provider."""

    native = [[11, 0.1], [12, 0.2]]
    calls = []
    control_ratio = 1.0
    cleanup_verified = False
    fail = False

    def __init__(self, programs, directory):
        self.programs, self.directory = programs, directory
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cleanup_verified = True

    def execute(self, case, family, *, reader=0, audit=False, checkpoint=None):
        self.calls.append((case["handle"], family, reader, audit, checkpoint))
        if self.fail:
            raise RuntimeError("synthetic interrupted query")
        cp, output, frames = 0, self.native, []
        name = self.programs.get(family, ({"name": "native"}, True))[0]["name"]
        force = self.programs.get(family, ({}, True))[1]
        if family == "forced":
            cp = checkpoint
            output = self.native if cp == 4 else [[99, 0.3]]
        elif family in self.programs:
            p = self.programs[family][0]
            points = next(iter(p["programs"].values()), {}).get("checkpoints", [])
            if points and not force and name not in ("continuing", "fault"):
                cp = points[0]
                output = self.native if cp == 4 else [[99, 0.3]]
            if audit:
                for point in points:
                    values = {f: None for f in FEATURES}
                    values.update(
                        checkpoint=point, qualifying_count=2, layer0_distance_evaluations=point * 3
                    )
                    frames.append({"checkpoint": point, "values": [values[f] for f in FEATURES]})
        latency = 50 if cp and family != "forced" else 100
        if family in ("clone", "empty"):
            latency *= self.control_ratio
        return {
            "output": copy.deepcopy(output),
            "checkpoint": cp,
            "request_ns": latency,
            "frames": frames,
            "fault": name == "fault",
            "exhausted": False,
        }


def request(kind, cases, **kw):
    handles = [r["handle"] for r in cases if r["role"] == "development"]
    if kind in ("acquire", "profile"):
        return {
            "kind": kind,
            "handles": handles,
            "checkpoints": [2, 4],
            "features": ["qualifying_count"],
            **kw,
        }
    return {"kind": kind, "policies": [policy()], "handles": handles, "blocks": 2, **kw}


def process(stage, payload, backend=SyntheticBackend):
    return Engine(stage, backend).process(uuid.uuid4().hex, payload)


def test_empty_sealed_start_and_reject_inherited_files(stage):
    verify_initial(stage)
    assert (stage / "agent/evidence/observations.jsonl").read_bytes() == b""
    assert read(stage / "initial-seal.json")["initial_empirical_records"] == 0
    assert "source-" not in (stage / "agent/task.json").read_text()
    (stage / "agent/scratch/old-results.json").write_text("{}")
    with pytest.raises(ValueError, match="inherited"):
        verify_initial(stage)


def test_static_inputs_are_bound(stage):
    p = stage / "private/cases.json"
    changed = read(p)
    changed[0]["vector"][0] += 1
    write(p, changed)
    with pytest.raises(ValueError, match="static query"):
        verify_initial(stage)


def test_cold_acquisition_charges_fresh_truth_and_never_infers_labels(stage, cases):
    answer = process(stage, request("acquire", cases))
    ledger = read(stage / "private/query-ledger.json")
    assert ledger["charged"] == 14 * 5  # native + exact + capture + two actual prefixes
    assert ledger["requests"][answer["request_id"]]["operations"] == {"ann": 56, "exact": 14}
    assert len(answer["evidence"]) == 28
    labels = {r["checkpoint"]: r["label"]["safe"] for r in answer["evidence"]}
    assert labels == {2: False, 4: True}
    append_evidence(stage / "agent", answer["run_id"], answer)
    assert len((stage / "agent/evidence/observations.jsonl").read_text().splitlines()) == 28
    assert all("vector" not in r and "output" not in r for r in answer["evidence"])
    second = process(stage, request("acquire", cases))
    assert second["ledger"]["charged"] == 70 + 14 * 3  # only this run's refs reused
    bad = {**answer, "run_id": "older-run"}
    with pytest.raises(ValueError, match="cross-run"):
        append_evidence(stage / "agent", answer["run_id"], bad)


def test_protected_or_unbalanced_timing_queries_rejected_before_backend(stage, cases):
    with pytest.raises(ValueError, match="protected"):
        process(
            stage,
            request("acquire", cases, handles=[r["handle"] for r in cases if r["role"] == "test"]),
        )
    with pytest.raises(ValueError, match="balanced requested conditions"):
        process(stage, request("screen", cases, handles=[cases[0]["handle"]]))
    assert read(stage / "private/query-ledger.json")["charged"] == 0


def test_targeted_acquisition_and_timing_can_focus_on_one_condition(stage, cases):
    handles = [r["handle"] for r in cases if r["role"] == "development" and r["filter"] == 108]
    answer = process(
        stage, request("acquire", cases, handles=handles[:1], checkpoints=list(range(2, 19)))
    )
    assert answer["status"] == "complete"
    assert answer["evidence"]
    screened = process(stage, request("screen", cases, handles=handles))
    assert screened["timing"]["families"]["candidate:0"]["108"]["groups"] == 2


def test_mixed_quality_feedback_keeps_lossy_and_resource_failed_candidates(stage, cases):
    answer = process(
        stage, request("screen", cases, policies=[policy("lossy", cp=2), policy(), policy("fault")])
    )
    assert not quality_ok(answer, "candidate:0")
    assert quality_ok(answer, "candidate:1")
    assert not quality_ok(answer, "candidate:2")
    assert len(answer["quality"]) == 42
    assert len({r["family"] for r in answer["samples"] if r["phase"] == "sample"}) == 8
    assert answer["timing"]["controls_pass"]
    assert answer["timing"]["families"]["candidate:1"]["all"]["savings_percent"] == 50
    assert all(r["query_ordinal"] > 0 for r in answer["quality"])


def test_continuing_does_not_mislabel_earlier_prefix_safe(stage, cases):
    answer = process(stage, request("screen", cases, policies=[policy("continuing", False, 2)]))
    assert quality_ok(answer, "candidate:0")
    assert answer["evidence"]
    assert all(not r["label"]["safe"] for r in answer["evidence"])
    assert all(r["label"]["query_ordinal"] > r["query_ordinal"] for r in answer["evidence"])


def test_controls_and_confirmation_gate(stage, cases):
    confirmation = process(stage, request("confirm", cases, handles=[]))
    assert qualified(confirmation, "candidate:0")
    no_stops = copy.deepcopy(confirmation)
    for row in no_stops["quality"]:
        row["checkpoint"] = 0
    assert not qualified(no_stops, "candidate:0")

    class Drift(SyntheticBackend):
        control_ratio = 1.1

    failed = process(stage, request("confirm", cases, handles=[]), Drift)
    assert not failed["timing"]["controls_pass"]
    assert not qualified(failed, "candidate:0")


def test_warmups_are_charged_and_predeclared_partial_blocks_rejected(stage, cases):
    answer = process(stage, request("profile", cases))
    assert answer["ledger"]["charged"] == 14 * 5 + 14 * 14 + 56
    records = answer["samples"]
    assert sum(r["phase"] == "warmup" for r in records) == 56
    assert answer["timing"]["families"]["capture"]["all"]["savings_percent"] == 0
    with pytest.raises(ValueError, match="incomplete"):
        summarize([r for r in records if r["block"] == 0], draws=64)
    dropped = next(r["group"] for r in records if r["phase"] == "sample")
    with pytest.raises(ValueError, match="incomplete declared"):
        summarize([r for r in records if r.get("group") != dropped], draws=64)
    assert {r["reader"] for r in records if r["phase"] == "sample"} == {0, 1}


def test_unknown_query_keeps_worst_case_reservation_and_blocks_redispatch(stage, cases):
    class Interrupted(SyntheticBackend):
        fail = True

    engine = Engine(stage, Interrupted)
    payload = request("screen", cases)
    _, worst = engine.validate_request(payload)
    with pytest.raises(RuntimeError, match="interrupted"):
        engine.process(uuid.uuid4().hex, payload)
    ledger = read(engine.ledger.path)
    assert ledger["charged"] == worst
    assert next(iter(ledger["requests"].values()))["actual"] == 1
    with pytest.raises(ValueError, match="uncertain"):
        process(stage, payload)


def test_caps_final_reserve_and_cross_run_ledger(tmp_path):
    limits = Limits(query_cap=100, final_reserve=60)
    ledger = Ledger(tmp_path / "ledger.json", limits, "fresh")
    ledger.reserve("one", 40)
    ledger.tick("one", "exact")
    with pytest.raises(ValueError, match="cleanup"):
        ledger.settle("one", False)
    ledger.settle("one", True)
    with pytest.raises(ValueError, match="reservation"):
        ledger.reserve("two", 40)
    ledger.reserve("final", 99, final=True)
    assert read(ledger.path)["charged"] == 100
    with pytest.raises(ValueError, match="cross-run"):
        Ledger(ledger.path, limits, "other")


def test_declared_full_workload_leaves_real_cold_acquisition_budget(tmp_path):
    roles = (
        ["development"] * 450
        + ["validation"] * 150
        + ["test"] * 275
        + ["excluded_historical"] * 125
    )
    cases = [
        {"handle": f"{g}-{t}", "group": str(g), "role": role, "filter": t, "vector": [float(g)]}
        for g, role in enumerate(roles)
        for t in FILTERS
    ]
    root = tmp_path / "full-static"
    task = prepare(root, cases)
    assert len(task["queries"]) == 3150
    config = read(root / "config.json")
    assert config["final_worst"] == 208062
    assert config["limits"]["final_reserve"] == 211000
    assert config["limits"]["query_cap"] - config["limits"]["final_reserve"] == 89000


def test_batched_progress_crash_still_holds_full_durable_query_reservation(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, Limits(), "run", checkpoint_every=64)
    ledger.reserve("request", 1000)
    for _ in range(7):
        ledger.tick("request", "ann")
    saved = read(path)
    assert saved["charged"] == 1000 and saved["requests"]["request"]["actual"] == 0
    # Simulate loss of all in-memory progress. The ceiling protection survives.
    restarted = Ledger(path, Limits(), "run", checkpoint_every=64)
    with pytest.raises(ValueError, match="uncertain"):
        restarted.reserve("duplicate", 1)
    ledger.settle("request", True)
    assert read(path)["charged"] == 7
    assert read(path)["requests"]["request"]["actual"] == 7


def test_batched_progress_flushes_caught_failures_without_releasing_reservation(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json", Limits(), "run", checkpoint_every=64)
    ledger.reserve("request", 1000)
    with pytest.raises(RuntimeError):
        with ledger.checkpoint_on_exit():
            ledger.tick("request", "ann")
            raise RuntimeError("known failure")
    assert read(ledger.path)["requests"]["request"]["actual"] == 1
    assert read(ledger.path)["charged"] == 1000


def test_per_case_warmup_removes_false_noop_speedup_from_cold_first_baseline():
    from fannclean.timing import measure

    cases = [
        {"handle": f"h{i}", "group": f"g{i}", "filter": -1, "role": "development"} for i in range(4)
    ]
    previous, ordinal = {}, [0]

    def execute(case, family, reader):
        cold = previous.get(reader) != case["handle"]
        previous[reader] = case["handle"]
        ordinal[0] += 1
        return {"request_ns": 400 if cold else 100, "query_ordinal": ordinal[0]}

    records = measure(cases, lambda _: ["clone", "empty"], execute, 1, 2)
    samples = [r for r in records if r["phase"] == "sample"]
    assert any(r["case_warmup_ns"] == 400 for r in samples)
    assert all(r["native_ns"] == 100 for r in samples)
    assert {tuple(r["pair_order"]).index("native") for r in samples} == {0, 1}
    summary = summarize(records, draws=64)
    assert summary["controls_pass"]
    assert summary["families"]["clone"]["all"]["ratio"] == 1


def test_final_is_single_attempt_with_private_oracles_only_after_freeze(stage, cases):
    payload = request("final", cases, handles=[])
    with pytest.raises(ValueError, match="frozen"):
        process(stage, payload)
    config = read(stage / "config.json")
    freeze = {
        "run_id": config["run_id"],
        "policy": policy(),
        "disposition": {"status": "policy_frozen"},
    }
    write(stage / "private/final-freeze.json", freeze)
    write(
        stage / "private/comparison.json",
        {"agent_freeze_sha256": digest(freeze), "oracle_full": policy(), "oracle_test": policy()},
    )
    answer = process(stage, payload)
    assert answer["final_complete"]
    assert not {"quality", "evidence", "samples", "timing"} & answer.keys()
    report = analyze(stage)
    assert report["cohorts"]["held_out"]["cases"] == 14
    assert report["cohorts"]["full"]["cases"] == 28
    assert report["cohorts"]["full"]["qualified_agent_win"]
    with pytest.raises(ValueError, match="already"):
        process(stage, payload)
    with pytest.raises(ValueError, match="closed|frozen"):
        process(stage, request("acquire", cases))
    saved = [
        json.loads(s)
        for s in (stage / "private/requests" / answer["request_id"] / "queries.jsonl")
        .read_text()
        .splitlines()
    ]
    assert len(saved) == answer["ledger"]["charged"]


def test_randomized_native_pairs_remove_multistep_cache_order_bias():
    from collections import defaultdict

    from fannclean.timing import measure

    cases = [
        {"handle": str(g), "group": str(g), "filter": -1, "role": "development"}
        for g in range(2000)
    ]
    positions = defaultdict(int)
    ordinal = 0
    curve = [400, 180, 160, 120, 110, 105, 102, 101, 100]

    def execute(case, family, reader):
        nonlocal ordinal
        key = case["handle"], reader
        pos = positions[key]
        positions[key] += 1
        ordinal += 1
        return {"request_ns": curve[min(pos, len(curve) - 1)], "query_ordinal": ordinal}

    rows = measure(cases, lambda _: ["clone", "empty"], execute, 81, 2)
    for family in ("clone", "empty"):
        samples = [r for r in rows if r.get("phase") == "sample" and r["family"] == family]
        ratio = sum(r["request_ns"] for r in samples) / sum(r["native_ns"] for r in samples)
        assert 0.98 < ratio < 1.02
        assert all(abs(r["query_ordinal"] - r["native_ordinal"]) == 1 for r in samples)
