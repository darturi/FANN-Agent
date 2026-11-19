import importlib
import json
import sys
from collections import Counter
from pathlib import Path

import pytest
from analysis import summarize
from controller import LiveTools
from limits import FILTERS, read
from workspace import ResearchWorkspace


def empty():
    return {
        "schema": "fannagent.broad-stop.v3",
        "name": "test",
        "rationale": "fixture",
        "fuel": 10000,
        "state_slots": 0,
        "programs": {},
    }


class Client:
    def __init__(self):
        self.calls = []

    def call(self, op):
        assert op == "status"
        return {"status": "running"}

    def evaluate(self, policies, identity):
        self.calls.append((policies, identity))
        return {
            "status": "measured",
            "feedback": {
                "quality_loss_cases": {"candidate1": 0},
                "latency": {
                    "candidate1": {
                        "conditional95_interval": [0.7, 0.8],
                        "matched_conditional95_interval": [0.7, 0.8],
                    }
                },
                "all_condition_controls_pass": False,
            },
        }


def service(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    client = Client()
    tools = LiveTools(
        {"cases": 3150, "protected_outcomes_exposed": False},
        client,
        tmp_path / "state.json",
        workspace,
        "image-id",
    )
    return tools, client


def test_v3_artifact_and_idempotent_submission(tmp_path):
    tools, client = service(tmp_path)
    path = tools.workspace.root / "policies/fitted.json"
    path.write_text(json.dumps(empty()))
    args = {"policy_paths": ["policies/fitted.json"]}
    first = tools.call("delivery", "evaluate_broad_candidates", args)
    assert tools.call("delivery", "evaluate_broad_candidates", args) == first
    assert len(client.calls) == 1
    assert "policy_hash" in tools.state["registry"]["candidate-1"]
    with pytest.raises(ValueError, match="conflicting"):
        tools.call("delivery", "evaluate_broad_candidates", {"policies": [empty()]})


def test_legacy_policy_and_evaluator_fields_rejected_before_native(tmp_path):
    tools, client = service(tmp_path)
    for policy in [
        {"schema": "fannagent.filtered-ann.v2", "name": "old", "rationale": "x", "rules": {}},
        {**empty(), "query_id_lookup": {}},
        {
            **empty(),
            "programs": {
                "unfiltered": {
                    "checkpoints": [1],
                    "root": ["gt", ["feature", "truth"], 0],
                    "updates": {},
                }
            },
        },
    ]:
        answer = tools.call(
            str(len(tools.state["receipts"])), "evaluate_broad_candidates", {"policies": [policy]}
        )
        assert "error" in answer
    assert not client.calls


def test_exploratory_freeze_does_not_pass_failed_controls(tmp_path):
    tools, _ = service(tmp_path)
    tools.call("eval", "evaluate_broad_candidates", {"policies": [empty()]})
    assert tools.quality_eligible("candidate-1")
    assert not tools.eligible("candidate-1")
    answer = tools.call(
        "freeze", "submit_or_abstain", {"candidate_ids": ["candidate-1"], "abstain": False}
    )
    assert answer["status"] == "development_candidate_frozen"
    assert not answer["strict_development_qualification"]
    with pytest.raises(ValueError, match="closed"):
        tools.call("post-freeze", "research_python", {"code": "print('revise')"})


def test_research_paths_cannot_read_outside_policies(tmp_path):
    tools, _ = service(tmp_path)
    outside = tmp_path / "protected.json"
    outside.write_text(json.dumps(empty()))
    (tools.workspace.root / "policies/link.json").symlink_to(outside)
    for name in ("../protected.json", "policies/link.json"):
        with pytest.raises(ValueError, match="under policies"):
            tools.workspace.policies({"policy_paths": [name]})


def test_research_container_is_offline_and_receipts_are_not_mounted(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "api").mkdir()
    (root / "evidence").mkdir()
    calls = []

    def invoke(command, **kwargs):
        calls.append((command, kwargs))
        kwargs["stdout"].write("synthetic execution\n")
        return type("Result", (), {"returncode": 0})()

    workspace = ResearchWorkspace(root, "sha256:pinned", invoke=invoke)
    result = workspace.execute("print('synthetic execution')")
    command, _ = calls[0]
    assert command[command.index("--network") + 1] == "none"
    assert "--read-only" in command
    assert "--cap-drop" in command
    assert "ANTHROPIC_API_KEY" not in str(command)
    assert result["exit_code"] == 0
    assert (tmp_path / "research-executions" / result["execution_id"] / "receipt.json").is_file()
    assert not (root / "executions").exists()


def measurement_module():
    helper = Path(__file__).resolve().parents[3] / (
        "../trials/fannagent-benchmark-evaluation-v1/reviews-small/broad-oracle-v1/benchmark-kit-v3"
    )
    sys.path.insert(0, str(helper.resolve()))
    return importlib.import_module("measurement")


def test_ledger_reserves_before_request_and_never_exceeds_cap(tmp_path):
    m = measurement_module()
    ledger = m.Ledger(tmp_path, 95, 100)
    counter = Counter(total=0)
    ledger.reserve(counter, "query")
    assert read(tmp_path / "attempts.json")["total"] == 5
    for _ in range(4):
        ledger.reserve(counter, "query")
    with pytest.raises(ValueError, match="limit"):
        ledger.reserve(counter, "query")
    ledger.finish(counter)
    assert read(tmp_path / "attempts.json")["actual"] == 5


@pytest.mark.parametrize("n", [4, 6, 8])
def test_each_family_runs_once_on_every_reader(n):
    m = measurement_module()
    families = tuple(f"family{i}" for i in range(n))
    for ti in range(7):
        for f in families:
            readers = [
                r
                for rotation in range(n)
                for r in range(4)
                if m.family_for(families, rotation, r, ti) == f
            ]
            assert sorted(readers) == [0, 1, 2, 3]


def data():
    families = ("native640", "candidate1", "matched1", "empty", "native_clone")
    quality = []
    timing = []
    for group in range(3):
        for t in FILTERS:
            qid = f"anon{group}-" + ("unfiltered" if t < 0 else f"votes{t}")
            for f in families:
                quality.append(
                    {
                        "id": qid,
                        "filter": t,
                        "family": f,
                        "checkpoint": 1 if f == "candidate1" else 0,
                        "recall": 1.0,
                        "native_recall": 1.0,
                        "output": [[1, 0.0]],
                        "native_count": 1,
                    }
                )
                for reader in range(4):
                    duration = 50 if f == "candidate1" else 110 if f == "native_clone" else 100
                    timing.append(
                        {
                            "id": qid,
                            "filter": t,
                            "family": f,
                            "reader": reader,
                            "request_ns": duration,
                        }
                    )
    return quality, timing, families


def test_complete_timing_keeps_failed_controls_and_both_aggregates():
    q, t, f = data()
    result = summarize(q, t, f, draws=100)
    assert result["aggregates"]["all_seven"]["candidate1"]["savings_percent"] == 50
    assert result["aggregates"]["six_filters"]["native640"]["native_ratio"] == 1
    assert not result["all_condition_controls_pass"]
    assert not result["performance_claim"]
    with pytest.raises(ValueError, match="incomplete"):
        summarize(q, t[:-1], f, draws=100)


def test_final_abstention_uses_native_without_v3_dispatch(tmp_path, monkeypatch):
    import compile_batch
    from limits import digest, write

    stage = tmp_path / "stage"
    (stage / "engine/src").mkdir(parents=True)
    for name in ("oracle-full.json", "oracle-test.json"):
        write(stage / name, empty())
    batch = tmp_path / "batch"
    batch.mkdir()
    payload = {"mode": "final", "policies": [empty()]}
    write(
        batch / "request.json",
        {"request_id": "test", "payload": payload, "payload_sha256": digest(payload)},
    )

    def build(command, **kwargs):
        (kwargs["cwd"] / "vector.so").write_bytes(b"synthetic module")
        return type("Result", (), {"returncode": 0, "stdout": b"synthetic build"})()

    monkeypatch.setattr(compile_batch.subprocess, "run", build)
    compile_batch.compile_batch(stage, batch)
    binding = read(batch / "batch-binding.json")
    assert binding["arms"]["agent"] is None
    assert len(binding["arms"]) == 6
