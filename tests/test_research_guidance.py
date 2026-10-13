import copy
import json
from importlib.resources import files

import pytest
from test_checkpoint import response
from test_startup_context import install_local_provider, prepared_run
from test_workflow import configuration

from fannagent import guidance
from fannagent.broker import Tools, dispatch_request
from fannagent.budget import Budget
from fannagent.cli import experiments, status
from fannagent.config import ResearchConfig, load_config
from fannagent.controller import command, explore, open_run
from fannagent.errors import AgentError
from fannagent.experiments import (
    MAX_VIEW_BYTES,
    ExperimentJournal,
    scripted_conclusion,
    scripted_plan,
)
from fannagent.onboarding import initialize
from fannagent.store import ReadOnlyStore, canonical, digest
from fannagent.study import Study
from fannagent.submission import InvalidSubmission


@pytest.fixture
def guided(tmp_path, monkeypatch):
    config = configuration()
    config.research = ResearchConfig(mode="guided")
    config, store, backend = open_run(tmp_path / "run", config)
    store.set("prepared", backend.prepare_copy().serialize())
    study = Study(config, store, backend)
    calls = []

    def measure(self, policy, split):
        calls.append((policy.policy_hash, split))
        self.store.set("hardness_boundaries", {"lower": 1, "upper": 2})
        return {
            "status": "accepted",
            "valid": True,
            "groups": {"overall": {"recall_noninferior": True}},
            "latencies": {"native": {"median_ms": 2}, "policy": {"median_ms": 1}},
            "policy_hash": policy.policy_hash,
            "compatibility": self.backend.compatibility(),
            "split": split,
            "simulated": True,
            "rows": self.store.put("private_calibration_rows", {"private": split}),
        }

    monkeypatch.setattr(Study, "measure", measure)
    tools = Tools(study, Budget(store, config.model))
    return config, store, backend, study, tools, calls


def start(tools, key="investigate"):
    return tools.call("experiment", {"action": "start", "plan": scripted_plan(key)})


def finish(tools, key="investigate"):
    return tools.call(
        "experiment", {"action": "finish", "client_key": key, "conclusion": scripted_conclusion()}
    )


def test_old_config_serialization_and_generated_guidance(tmp_path):
    config = configuration()
    assert "research" not in config.public()
    previous = config.model_dump(mode="json", exclude={"research"})
    assert config.public() == previous
    root = tmp_path / "old"
    open_run(root, config)
    previous = config.public()  # Existing backend normalization is part of the run identity.
    reopened, _, _ = open_run(root)
    assert reopened.public() == previous and digest(reopened.public()) == digest(previous)
    initialize("fake", tmp_path / "new.yaml")
    assert load_config(tmp_path / "new.yaml").research.mode == "guided"
    changed = config.model_copy(update={"research": ResearchConfig()})
    with pytest.raises(AgentError, match="immutable"):
        open_run(root, changed)


def test_primer_sources_classifications_and_backend_applicability(guided):
    _, store, _, _, tools, _ = guided
    state = guidance.read_guidance(store)
    snapshot = store.read(state["snapshot"])
    assert len(snapshot["primer"].encode()) <= guidance.MAX_PRIMER_BYTES
    assert "simulation" in snapshot["primer"]
    assert "not a live filter" in snapshot["primer"]
    for principle in snapshot["manifest"]["principles"]:
        if principle["classification"] == "literature_finding":
            assert principle["citations"] and principle["limit"]
            for citation in principle["citations"]:
                assert citation["sections"]
                source = snapshot["manifest"]["sources"][citation["source_id"]]
                assert source["url"].startswith("https://arxiv.org/html/")
                assert source["verified_date"] == "2026-10-09"
        else:
            assert principle["classification"] == "project_rule" and not principle["citations"]
    public = tools.call("artifact", {"hash": state["artifact"]})
    assert public["view"] == "development_research_guidance"
    with pytest.raises(AgentError, match="scope"):
        tools.call("artifact", {"hash": state["snapshot"]})


def test_invalid_plan_prevents_measurement_and_orientation_remains_available(guided, monkeypatch):
    _, _, backend, study, tools, _ = guided
    calls = []
    monkeypatch.setattr(backend, "execute_probe", lambda *args: calls.append(args))
    assert tools.call("queries", {"limit": 1})
    tools.call("inspect", {})
    result = dispatch_request(
        tools, {"operation": "probe", "args": {"query": study.development[0]["query"]}}
    )
    assert result["error_info"]["code"] == "experiment_required"
    plan = scripted_plan("bad")
    plan["hypothesis"] = "x" * 513
    result = dispatch_request(
        tools, {"operation": "experiment", "args": {"action": "start", "plan": plan}}
    )
    assert result["error_info"]["code"] == "invalid_experiment"
    assert calls == []


@pytest.mark.parametrize("reference", ["unknown", "private"])
def test_basis_rejects_unknown_and_private_evidence(guided, reference):
    _, store, _, _, tools, _ = guided
    ref = (
        store.put("private", {"secret": "private-evidence"})
        if reference == "private"
        else "unknown"
    )
    plan = scripted_plan("bad-ref")
    plan["basis"] = {"kind": "measurement", "evidence_refs": [ref]}
    with pytest.raises(InvalidSubmission, match="development scope"):
        tools.call("experiment", {"action": "start", "plan": plan})
    assert store.get("research_active_experiment") is None


def test_registered_principles_and_exploratory_hypotheses(guided):
    _, _, _, _, tools, _ = guided
    plan = scripted_plan("literature")
    plan["basis"] = {"kind": "literature", "principle_ids": ["invented-paper"]}
    with pytest.raises(InvalidSubmission, match="principle"):
        tools.call("experiment", {"action": "start", "plan": plan})
    plan["basis"]["principle_ids"] = ["PROJECT_RECALL"]
    with pytest.raises(InvalidSubmission, match="cited literature"):
        tools.call("experiment", {"action": "start", "plan": plan})
    plan["basis"]["principle_ids"] = ["E2E_FILTER_SIGNALS"]
    assert tools.call("experiment", {"action": "start", "plan": plan})["state"] == "open"


def test_operations_capture_identity_before_execution_and_conclusions_are_idempotent(
    guided, monkeypatch
):
    _, store, _, study, tools, _ = guided
    record = start(tools)
    assert start(tools) == record
    changed = scripted_plan("investigate")
    changed["hypothesis"] = "another claim"
    with pytest.raises(InvalidSubmission, match="another plan"):
        tools.call("experiment", {"action": "start", "plan": changed})
    query = study.development[0]["query"]
    original = study.probe

    def probe(*args, **kwargs):
        events = tools.experiments.events(record["experiment_id"])
        assert events[-1]["state"] == "pending"
        assert events[-1]["query_hash"] == digest(study.permitted(query))
        assert store.get("research_active_experiment") == record["experiment_id"]
        return original(*args, **kwargs)

    monkeypatch.setattr(study, "probe", probe)
    result = tools.call("probe", {"query": query})
    assert result["experiment_event_id"].startswith("evt_")
    done = finish(tools)
    assert done["conclusion"]["evidence_refs"] == [result["experiment_event_id"]]
    assert finish(tools) == done
    assert store.get("research_active_experiment") is None
    assert tools.experiments.events(record["experiment_id"])[0]["state"] == "success"
    with pytest.raises(InvalidSubmission, match="hypothesis"):
        tools.call("count", {"query": query})


def test_conclusion_cannot_cite_unobserved_or_private_artifacts(guided):
    _, store, _, study, tools, _ = guided
    start(tools)
    tools.call("count", {"query": study.development[0]["query"]})
    conclusion = scripted_conclusion()
    conclusion["evidence_refs"] = [store.put("private", {"private": "final-test"})]
    with pytest.raises(InvalidSubmission, match="unrecorded"):
        tools.call(
            "experiment",
            {"action": "finish", "client_key": "investigate", "conclusion": conclusion},
        )


def test_calibration_journal_has_only_public_aggregates_and_exact_candidate_origin(guided):
    _, store, backend, _, tools, _ = guided
    record = start(tools)
    candidate = backend.runtime_profile.scripted_policy
    output = tools.call("calibrate", {"policy": candidate, "checkpoint": True})
    private = store.get("candidate_checkpoint")["artifact"]
    journal = tools.call("experiment", {"action": "get", "experiment_id": record["experiment_id"]})
    rendered = json.dumps(journal)
    assert "private_calibration_rows" not in rendered and private not in rendered
    assert "rows" not in journal["events"][0]["observation"]
    assert journal["events"][0]["policy_hash"] == backend.validate_policy(candidate).policy_hash
    with pytest.raises(InvalidSubmission, match="finish"):
        tools.call("submit", {"policy": candidate})
    finish(tools)
    submitted = tools.call("submit", {"policy": candidate})
    assert submitted["policy_hash"] == journal["events"][0]["policy_hash"]
    assert output["checkpoint_policy_hash"] == submitted["policy_hash"]


def test_calibration_of_another_candidate_cannot_supply_provenance(guided):
    _, _, backend, study, tools, _ = guided
    candidate = backend.runtime_profile.scripted_policy
    study.validate(candidate, calibration=True)
    with pytest.raises(InvalidSubmission, match="completed calibrated"):
        study.submit(candidate)
    start(tools)
    tools.call("calibrate", {"policy": {**candidate, "name": "other"}})
    finish(tools)
    with pytest.raises(InvalidSubmission, match="completed calibrated"):
        tools.call("submit", {"policy": candidate})


def test_failures_and_unknown_operations_are_not_replayed(guided, monkeypatch):
    _, _, backend, study, tools, _ = guided
    record = start(tools)

    def failure(*args):
        raise AgentError("backend timeout")

    monkeypatch.setattr(backend, "execute_probe", failure)
    query = study.development[0]["query"]
    with pytest.raises(AgentError, match="timeout"):
        tools.call("probe", {"query": query})
    pending = tools.experiments.before(study, "count", {"query": query})
    monkeypatch.setattr(backend, "execute_probe", lambda *args: pytest.fail("must not replay"))
    tools.experiments.recover()
    events = tools.experiments.events(record["experiment_id"])
    assert [e["state"] for e in events] == ["failed", "unknown"]
    assert events[1]["event_id"] == pending[1]["event_id"]
    finish(tools)


def test_storage_exhaustion_preserves_sqlite_observations_and_conclusion(guided, monkeypatch):
    _, store, _, study, tools, _ = guided
    record = start(tools)
    original = store.put

    def full(kind, value, **kwargs):
        if kind in {"experiment_record", "experiment_observation"}:
            raise AgentError("evidence storage limit reached")
        return original(kind, value, **kwargs)

    monkeypatch.setattr(store, "put", full)
    tools.call("count", {"query": study.development[0]["query"]})
    done = finish(tools)
    assert "storage_failure" in done
    event = tools.experiments.events(record["experiment_id"])[0]
    assert event["observation"]["eligible_count"] > 0 and event["storage_failure"]
    assert ExperimentJournal(ReadOnlyStore(store.root)).summary()["experiments"]["completed"] == 1


@pytest.mark.parametrize("mode", ["guided", "protocol_only"])
def test_scripted_protocol_resume_and_frozen_submission(guided, monkeypatch, mode):
    config, store, backend, _, _, _ = guided
    # A separate fresh run avoids changing the pinned mode in the fixture.
    config = config.model_copy(update={"research": ResearchConfig(mode=mode)})
    config, fresh, backend = open_run(store.root.parent / mode, config)
    fresh.set("prepared", backend.prepare_copy().serialize())
    assert explore(config, fresh, backend, step_limit=2)["status"] == "interrupted"
    before = fresh.read(fresh.get("trajectory"))
    assert before["research_mode"] == mode
    assert ExperimentJournal(fresh).summary()["experiments"]["open"] == 1
    monkeypatch.setattr(
        guidance, "render_primer", lambda *a: pytest.fail("resume must use snapshot")
    )
    monkeypatch.setattr(
        "fannagent.controller.scripted_plan",
        lambda *a: pytest.fail("resume must use saved actions"),
    )
    result = explore(config, fresh, backend, resume=True, step_limit=10)
    assert result["status"] == "frozen"
    after = fresh.read(fresh.get("trajectory"))
    assert after["messages"][: len(before["messages"])] == before["messages"]
    assert result["research"]["experiments"]["completed"] == 3
    assert result["research"]["candidate_origins"]
    system = before["messages"][0]["content"]
    assert ("E2E_FILTER_SIGNALS" in system) is (mode == "guided")


def test_budget_checkpoint_survives_incomplete_conclusion(guided, monkeypatch):
    config, store, backend, _, tools, _ = guided
    start(tools)
    tools.call("calibrate", {"policy": backend.runtime_profile.scripted_policy, "checkpoint": True})
    store.set("status", "budget_exhausted")
    monkeypatch.setattr(Study, "measure", lambda *args: pytest.fail("must use cached calibration"))
    result = explore(config, store, backend, resume=True)
    assert result["status"] == "frozen" and result["finalization_source"] == "checkpoint"
    assert result["research"]["experiments"]["interrupted"] == 1
    assert store.get("test_entitlement") is None


def test_first_mocked_provider_request_is_pinned_before_dispatch(tmp_path, monkeypatch):
    config, store, backend = prepared_run(tmp_path, paid=True)
    config.research = ResearchConfig()
    store.set("config", config.public())
    requests = []

    def dispatch(**kwargs):
        requests.append(kwargs)
        saved = store.read(store.get("trajectory"))
        state = guidance.read_guidance(store)
        assert saved["research_primer_hash"] == state["primer_hash"]
        assert saved["research_system_prompt_hash"] == digest(kwargs["messages"][0]["content"])
        assert "E2E_FILTER_SIGNALS" in kwargs["messages"][0]["content"]
        return response(command("experiment", {"action": "start", "plan": scripted_plan("paid")}))

    install_local_provider(monkeypatch, dispatch)
    assert explore(config, store, backend, step_limit=1)["status"] == "interrupted"
    assert len(requests) == 1


def test_small_bound_and_unsupported_protocol_make_no_provider_calls(tmp_path, monkeypatch):
    config, store, backend = prepared_run(tmp_path, paid=True, input_bound=1000)
    config.research = ResearchConfig()
    store.set("config", config.public())
    install_local_provider(monkeypatch, lambda **kw: pytest.fail("must fail before provider call"))
    with pytest.raises(AgentError, match="input bound"):
        explore(config, store, backend)
    assert Budget(store, config.model).summary()["committed_usd"] == "0"
    state = guidance.read_guidance(store)
    store.set("research_guidance", {**state, "research_protocol_version": 99})
    with pytest.raises(AgentError, match="unsupported research"):
        explore(config, store, backend)


def test_journal_inspection_is_readonly_and_contains_provenance(guided, capsys, monkeypatch):
    _, store, _, study, tools, _ = guided
    record = start(tools)
    tools.call("count", {"query": study.development[0]["query"]})
    finish(tools)
    original = store.path.read_bytes()
    monkeypatch.setattr(
        type(store), "set_many", lambda *a, **k: pytest.fail("inspection must not write")
    )
    experiments(store.root, record["experiment_id"])
    result = json.loads(capsys.readouterr().out)
    assert result["journal"]["plan"]["hypothesis"]
    assert result["journal"]["events"][0]["observation"]
    status(store.root)
    assert json.loads(capsys.readouterr().out)["research"]["experiments"]["completed"] == 1
    assert original == store.path.read_bytes()


def test_protocol_only_rejects_literature_without_primer(tmp_path):
    config = configuration()
    config.research = ResearchConfig(mode="protocol_only")
    config, store, backend = open_run(tmp_path / "protocol", config)
    store.set("prepared", backend.prepare_copy().serialize())
    tools = Tools(Study(config, store, backend), Budget(store, config.model))
    plan = scripted_plan("paper")
    plan["basis"] = {"kind": "literature", "principle_ids": ["E2E_FILTER_SIGNALS"]}
    with pytest.raises(InvalidSubmission, match="principle"):
        tools.call("experiment", {"action": "start", "plan": plan})


def test_primer_asset_is_loaded_from_installed_resources():
    value = json.loads(files("fannagent").joinpath("assets/research_primer_v1.json").read_text())
    assert value["version"] == 1
    assert {p["id"] for p in value["principles"]} >= {"E2E_QUERY_EFFORT", "GLS_LOCAL_ALIGNMENT"}


def test_tampered_prompt_identity_is_rejected(guided):
    config, store, backend, _, _, _ = guided
    explore(config, store, backend, step_limit=1)
    trajectory = copy.deepcopy(store.read(store.get("trajectory")))
    trajectory["messages"][0]["content"] += "\nchanged"
    store.set("trajectory", store.put("trajectory", trajectory))
    with pytest.raises(AgentError, match="prompt identity"):
        explore(config, store, backend, resume=True, step_limit=2)


def test_guided_conversation_cannot_be_replaced_with_run(guided):
    config, store, backend, _, _, _ = guided
    explore(config, store, backend, step_limit=1)
    saved = store.get("trajectory")
    with pytest.raises(AgentError, match="use resume"):
        explore(config, store, backend, step_limit=2)
    assert store.get("trajectory") == saved


def test_missing_hypotheses_use_existing_invalid_turn_limit(tmp_path, monkeypatch):
    config, store, backend = prepared_run(tmp_path, paid=True)
    config.research = ResearchConfig()
    store.set("config", config.public())
    query = Study(config, store, backend).development[0]["query"]
    requests = []

    def dispatch(**kwargs):
        requests.append(kwargs)
        return response(command("probe", {"query": query}))

    install_local_provider(monkeypatch, dispatch)
    result = explore(config, store, backend, step_limit=10)
    assert result["status"] == "invalid_submission_limit" and len(requests) == 3
    assert store.get("submission_recovery")["consecutive_invalid_turns"] == 3
    assert result["research"]["operations"]["success"] == 0
    assert Budget(store, config.model).summary()["committed_usd"] != "0"


def test_baseline_recording_limit_does_not_block_measurement(tmp_path, monkeypatch):
    config, store, backend = prepared_run(tmp_path)
    tools = Tools(Study(config, store, backend), Budget(store, config.model))
    monkeypatch.setattr("fannagent.experiments.MAX_EVENTS", 0)
    result = tools.call("count", {"query": tools.study.development[0]["query"]})
    assert result["eligible_count"] > 0 and "experiment_event_id" not in result


def test_failed_durable_registration_cannot_admit_measurement(guided, monkeypatch):
    _, store, _, study, tools, _ = guided
    original = store.set_many

    def failed_registration(updates):
        if "research_active_experiment" in updates:
            raise AgentError("state storage unavailable")
        return original(updates)

    monkeypatch.setattr(store, "set_many", failed_registration)
    with pytest.raises(AgentError, match="storage unavailable"):
        start(tools)
    monkeypatch.setattr(
        study, "probe", lambda *a, **kw: pytest.fail("registration was not durable")
    )
    with pytest.raises(InvalidSubmission, match="hypothesis"):
        tools.call("probe", {"query": study.development[0]["query"]})
    assert tools.experiments.events() == []


def test_journal_pages_are_bounded_and_progress_without_skipping_events(guided):
    _, _, _, study, tools, _ = guided
    record = start(tools)
    for _ in range(8):
        pending = tools.experiments.before(study, "count", {"query": study.development[0]["query"]})
        tools.experiments.after(pending, result={"observation": "x" * 12000})
    offset = 0
    seen = []
    while offset is not None:
        page = tools.call(
            "experiment",
            {
                "action": "get",
                "experiment_id": record["experiment_id"],
                "offset": offset,
                "limit": 100,
            },
        )
        assert len(canonical(page)) <= MAX_VIEW_BYTES
        assert page["events"]
        seen.extend(event["event_id"] for event in page["events"])
        offset = page["next_offset"]
    assert seen == [
        event["event_id"] for event in tools.experiments.events(record["experiment_id"])
    ]


def test_malformed_experiment_actions_return_correction_feedback(guided):
    _, _, _, _, tools, _ = guided
    for args in (
        {"action": []},
        {"action": "list", "private": True},
        {"action": "get", "offset": {}},
    ):
        result = dispatch_request(tools, {"operation": "experiment", "args": args})
        assert result["error_info"]["code"] == "invalid_experiment"
