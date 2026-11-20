import json
import sys
import uuid

import pytest
from fannclean import fit, model, worker
from fannclean.comparison import compare_reports, panels, run_scripted
from fannclean.controller import REPORT_KEYS, Workspace
from fannclean.core import FILTERS, Limits, digest, prepare, read
from fannclean.engine import Engine
from fannclean.report import analyze
from test_core_engine import SyntheticBackend, policy
from test_model_worker import StubProvider, active, authorize, response


def inputs():
    return [
        {
            "handle": f"g{i}:{condition}",
            "group": f"g{i}",
            "role": "development" if i < 12 else "test",
            "filter": condition,
            "vector": [i, 1],
        }
        for i in range(16)
        for condition in FILTERS
    ]


class LocalFixtureClient:
    def __init__(self, root):
        self.root = root

    def status(self):
        return worker.status(self.root)

    def call(self, name):
        return worker.dispatch(self.root, name)

    def action(self, payload):
        return Engine(self.root, SyntheticBackend).process(uuid.uuid4().hex, payload)


def plan(arm, seed):
    return {"arm": arm, "seed": seed, "initial_groups": 6, "followup_groups": 4, "screen_groups": 2}


def finalize(root, client, completed):
    freeze = read(root / "host/freeze.json")
    worker.dispatch(root, "freeze", payload={"freeze": freeze, "model_closed": completed})
    result = client.action(
        {"kind": "final", "policies": [freeze["policy"]], "handles": [], "blocks": 2}
    )
    assert "evidence" not in result
    report = analyze(root)
    config = read(root / "config.json")
    report["comparison"] = {
        **config["comparison"],
        "limits": config["limits"],
        "initial_handles_sha256": completed["initial_handles_sha256"],
        "model_charged_usd": completed["model_charged_usd"],
        "model_calls": completed.get("model_calls", 0),
    }
    return report


def test_first_stop_scores_once_and_unknown_prefix_is_not_native():
    row = {
        "features": {"layer0_distance_evaluations": 5},
        "label": {"safe": True, "count_preserving": True},
    }
    later = {
        "features": {"layer0_distance_evaluations": 12},
        "label": {"safe": False, "count_preserving": False},
    }
    cases = {(-1, "complete"): {2: row, 4: later}, (-1, "missing"): {4: later}}
    decisions = {(-1, "complete", 2): True, (-1, "complete", 4): True, (-1, "missing", 4): True}
    replay = fit.first_stop_feedback(cases, decisions, [2, 4])
    assert replay["all"] == {
        "cases": 2,
        "stops": 1,
        "unknown": 1,
        "recall_losses": 0,
        "count_losses": 0,
        "observed_work_saved": 7,
    }


def test_comparison_refuses_same_vector_in_development_and_test(tmp_path):
    cases = inputs()
    for case in cases:
        if case["group"] == "g12":
            case["vector"] = [0, 1]
    with pytest.raises(ValueError, match="identical vectors"):
        prepare(tmp_path / "overlap", cases, comparison=plan("agent", 1))


def test_missing_collector_mask_fails_acquisition_before_publishing_evidence(tmp_path):
    class MissingCollector(SyntheticBackend):
        def execute(self, case, family, **kwargs):
            result = super().execute(case, family, **kwargs)
            for frame in result["frames"]:
                frame["mask"] = 0
            return result

    root = tmp_path / "missing-collector"
    settings = prepare(root, inputs(), comparison=plan("agent", 7))
    payload = {
        "kind": "acquire",
        "handles": [settings["queries"][0]["handle"]],
        "checkpoints": [4],
        "features": ["qualifying_count"],
    }
    with pytest.raises(ValueError, match="omitted a requested collector"):
        Engine(root, MissingCollector).process(uuid.uuid4().hex, payload)
    assert not (root / "agent/evidence/observations.jsonl").read_bytes()


def tool(n, name, /, **arguments):
    return response([{"type": "tool_use", "id": f"tool{n}", "name": name, "input": arguments}])


def agent_fixture(root, client):
    simple = policy("fixed", True)
    threshold = policy("threshold", ["gt", ["feature", "qualifying_count"], 1])
    code = (
        "from pathlib import Path\n"
        f"Path('policies/fixed.json').write_text({json.dumps(simple)!r})\n"
        f"Path('policies/threshold.json').write_text({json.dumps(threshold)!r})"
    )
    provider = StubProvider(
        [
            tool(0, "inspect_state"),
            tool(1, "list_queries", limit=2),
            tool(2, "fit_batch", name="initial", checkpoints=[4], features=["qualifying_count"]),
            tool(3, "research_python", code=code),
            tool(4, "evaluate", policy_paths=["policies/fixed.json"]),
            tool(5, "evaluate", policy_paths=["policies/threshold.json"]),
            tool(6, "confirm", candidate_id="c2"),
            tool(
                7,
                "finish",
                candidate_id="c2",
                report={
                    key: "The paired fixture uses observed synthetic evidence."
                    for key in REPORT_KEYS
                },
            ),
        ]
    )
    result = model.run(root, client, provider=provider, qualify=lambda *args: None)
    assert result["status"] == "policy_frozen"
    sent = [request for path, request in provider.requests if path == "/v1/messages"]
    assert len(sent[6]["messages"]) == 1
    assert "coverage_groups_by_filter_and_checkpoint" in sent[6]["messages"][0]["content"]
    assert len(read(root / "host/conversation.json")) > len(sent[6]["messages"])
    return result


def test_paired_runners_complete_three_clean_seeds(tmp_path, monkeypatch):
    def fixture_python(workspace, source, timeout=None):
        with monkeypatch.context() as ctx:
            ctx.chdir(workspace.root)
            ctx.setitem(sys.modules, "fit", fit)
            exec(source, {})
        return {"exit_code": 0, "output": ""}

    monkeypatch.setattr(Workspace, "execute", fixture_python)
    reports = []
    for seed in (7, 17, 29):
        initial = []
        for arm in ("scripted", "agent"):
            root = tmp_path / f"{seed}-{arm}"
            fixture_limits = Limits(query_cap=20_000, final_reserve=2_000, bootstrap_draws=60)
            prepare(
                root,
                inputs(),
                fixture_limits,
                comparison=plan(arm, seed),
            )
            assert not (root / "agent/evidence/observations.jsonl").read_bytes()
            initial.append(panels(root, read(root / "config.json")["comparison"])[0])
            authorize(root)
            active(root)
            client = LocalFixtureClient(root)
            result = (run_scripted if arm == "scripted" else agent_fixture)(root, client)
            assert result["initial_handles_sha256"] == digest(initial[-1])
            report = finalize(root, client, result)
            assert report["cohorts"]["held_out"]["cases"] == 4 * len(FILTERS)
            assert set(report["cohorts"]) == {"held_out"}
            assert report["cohorts"]["held_out"]["quality"]["candidate:0"]["strict_quality_pass"]
            reports.append(report)
        assert initial[0] == initial[1]

    summary = compare_reports(reports)
    assert summary["pair_count"] == 3
    assert summary["qualified_runs"] == {"scripted": 3, "agent": 3}
    assert all(
        p["scripted"]["model_calls"] == 0 and p["agent"]["model_calls"] == 8
        for p in summary["pairs"]
    )
    with pytest.raises(ValueError, match="both finalized"):
        compare_reports(reports[:-1])
    reports[-1]["comparison"]["initial_handles_sha256"] = "wrong sample"
    with pytest.raises(ValueError, match="differ"):
        compare_reports(reports)
