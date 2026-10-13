import json
import threading

import pytest
from test_bounded_workflow import prepared

from fannagent.broker import Tools
from fannagent.budget import Budget
from fannagent.errors import AgentError
from fannagent.evaluation_jobs import EvaluationJobs
from fannagent.experiments import scripted_plan
from fannagent.store import ReadOnlyStore, Store
from fannagent.study import Study


def test_screen_uses_production_modes_and_never_admits_held_out_queries(tmp_path, monkeypatch):
    config, store, backend = prepared(tmp_path)
    study = Study(config, store, backend)
    calls = []
    execute = backend.execute_probe

    def observed(request):
        calls.append(request)
        return execute(request)

    monkeypatch.setattr(backend, "execute_probe", observed)
    from fannagent.backends.fake import PROFILE
    result = study.screen(study.development[0]["query"], PROFILE.scripted_policy)
    assert len(calls) == 12 and all(not request.trace for request in calls)
    assert sum(request.mode == "native" for request in calls) == 4
    assert set(result["modes"]) == {"native", "policy", "continue"}
    assert result["statistical_acceptance"] is False and result["trace"] is False
    assert result["timing_metric"] == "unchanged ProbeResult.latency_ms"
    held_out = next(i["query"] for i in study.manifest["items"] if i["split"] != "development")
    with pytest.raises(AgentError, match="outside the development entitlement"):
        study.screen(held_out, PROFILE.scripted_policy)
    assert len(calls) == 12


def test_live_progress_survives_reopen_and_result_retrieval_never_replays(tmp_path, monkeypatch):
    config, store, backend = prepared(tmp_path)
    study = Study(config, store, backend)
    tools = Tools(study, Budget(store, config.model), turn_limit=12)
    tools.call(
        "experiment",
        {"action": "start", "plan": scripted_plan("candidate", "candidate_evaluation")},
    )
    entered, release = threading.Event(), threading.Event()
    measurements, results = [], []
    policy = {"name": "control", "root": "continue"}

    def measure(candidate, split):
        measurements.append(split)
        study._evaluation_progress("paired_measurements", 7, 20)
        entered.set()
        assert release.wait(5)
        return {
            "status": "no_recommendation",
            "valid": True,
            "per_query_regressions": [{"id": str(i)} for i in range(2000)],
        }

    monkeypatch.setattr(study, "measure", measure)
    identity = "a" * 32
    worker = threading.Thread(
        target=lambda: results.append(
            tools.call("development_evaluate", {"policy": policy}, request_id=identity)
        )
    )
    worker.start()
    try:
        assert entered.wait(5)
        reader = EvaluationJobs(ReadOnlyStore(store.root))
        progress = reader.status(identity)
        assert progress["state"] == "running" and progress["completed"] == 7
        assert "request_hash" not in progress and progress["do_not_replay"]
        with pytest.raises(AgentError, match="already started"):
            tools.call("development_evaluate", {"policy": policy}, request_id=identity)
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive() and measurements == ["development"]
    result = results[0]
    assert "per_query_regressions" not in result
    assert (
        len(store.read(result["evaluation_report_artifact"], agent=True)["per_query_regressions"])
        == 2000
    )
    assert tools.call("evaluation_status", {"job_id": identity})["result"] == result
    assert tools.call("development_evaluate", {"policy": policy}, request_id=identity) == result
    assert measurements == ["development"] and len(tools.experiments.events()) == 1
    store.set("frozen", {"fixture": True})
    assert tools.call("evaluation_status", {"job_id": identity})["state"] == "completed"


def test_calibration_job_exports_only_approved_aggregates(tmp_path):
    store = Store(tmp_path / "run", create=True)
    jobs = EvaluationJobs(store)
    identity, _ = jobs.begin("calibrate", {"policy": {"name": "candidate"}})
    result = jobs.complete(
        identity,
        {
            "status": "accepted",
            "valid": True,
            "groups": {"overall": {"count": 30}},
            "rows": "private_rows",
            "diagnostics": "private_diagnostics",
            "private_queries": [{"vector": [123]}],
            "compatibility": {"private": True},
        },
    )
    report = store.read(result["evaluation_report_artifact"], agent=True)
    assert set(report) == {"status", "valid", "groups"}
    assert "private" not in json.dumps(jobs.status(identity))


def test_failed_registration_is_durable_and_never_replayed(tmp_path):
    config, store, backend = prepared(tmp_path)
    tools = Tools(Study(config, store, backend), Budget(store, config.model))
    identity = "b" * 32
    args = {"policy": {"name": "control", "root": "continue"}}
    with pytest.raises(AgentError):
        tools.call("development_evaluate", args, request_id=identity)
    assert tools.call("evaluation_status", {"job_id": identity})["state"] == "failed"
    with pytest.raises(AgentError, match="already started"):
        tools.call("development_evaluate", args, request_id=identity)
