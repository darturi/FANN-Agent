import json
import sqlite3

import pytest
from test_startup_context import install_local_provider, prepared_run

from fannagent import controller
from fannagent.backends.fake import PROFILE
from fannagent.broker import Tools
from fannagent.budget import Budget
from fannagent.cli import report, status
from fannagent.controller import command, explore, open_run
from fannagent.errors import AgentError
from fannagent.store import ReadOnlyStore
from fannagent.study import Study


@pytest.fixture
def study_run(tmp_path, monkeypatch):
    config, store, backend = prepared_run(tmp_path, paid=True)
    study = Study(config, store, backend)
    measurements = []

    def measure(self, policy, split):
        measurements.append((policy.policy_hash, split))
        self.store.set("hardness_boundaries", {"lower": 1, "upper": 2})
        accepted = policy.name != "rejected"
        return {
            "status": "accepted" if accepted else "no_recommendation",
            "valid": True,
            "groups": {"overall": {"recall_noninferior": accepted}},
            "latencies": {"native": {"median_ms": 2}, "policy": {"median_ms": 1}},
            "policy_hash": policy.policy_hash,
            "compatibility": self.backend.compatibility(),
            "split": split,
            "simulated": True,
        }

    monkeypatch.setattr(Study, "measure", measure)
    return config, store, backend, study, measurements


def candidate(name="chosen"):
    return {**PROFILE.scripted_policy, "name": name}


def checkpoint(study, name="chosen"):
    return study.validate(candidate(name), calibration=True, checkpoint=True)


def exhausted_resume(config, store, backend):
    store.set("status", "budget_exhausted")
    return explore(config, store, backend, resume=True)


def fail(*args, **kwargs):
    pytest.fail("finalization must use only cached evidence")


def response(action, *, tokens=100):
    from litellm import ModelResponse

    return ModelResponse(
        choices=[
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "checkpoint-action",
                            "type": "function",
                            "function": {
                                "name": "bash",
                                "arguments": json.dumps({"command": action}),
                            },
                        }
                    ],
                },
            }
        ],
        usage={
            "prompt_tokens": tokens,
            "completion_tokens": tokens,
            "total_tokens": 2 * tokens,
        },
    )


def test_checkpoint_is_private_and_selection_is_explicit(study_run):
    config, store, backend, study, measurements = study_run
    tools = Tools(study, Budget(store, config.model))
    selected = tools.call("calibrate", {"policy": candidate(), "checkpoint": True})
    pointer = store.get("candidate_checkpoint")
    assert selected["checkpoint_policy_hash"] == backend.validate_policy(candidate()).policy_hash
    assert set(selected) == {
        "status",
        "valid",
        "groups",
        "latencies",
        "checkpoint_policy_hash",
        "evaluation_job_id",
        "evaluation_report_artifact",
    }
    public_report = store.read(selected["evaluation_report_artifact"], agent=True)
    assert set(public_report) == {
        "status",
        "valid",
        "groups",
        "latencies",
        "checkpoint_policy_hash",
    }
    record = store.read(pointer["artifact"])
    assert record["calibration"]["split"] == "calibration"
    assert record["envelope"]["policy_hash"] == pointer["policy_hash"]
    with pytest.raises(AgentError, match="scope"):
        tools.call("artifact", {"hash": pointer["artifact"]})
    for name, marked in [("other", False), ("rejected", True)]:
        result = tools.call("calibrate", {"policy": candidate(name), "checkpoint": marked})
        assert result["checkpoint_policy_hash"] == pointer["policy_hash"]
        assert store.get("candidate_checkpoint") == pointer
    checkpoint(study, "replacement")
    assert study.checkpoint_policy_hash() != pointer["policy_hash"]
    assert tools.call("inspect", {})["checkpoint_policy_hash"] == study.checkpoint_policy_hash()
    assert len(measurements) == 4


@pytest.mark.parametrize("flag", [None, 0, 1, "true", [], {}])
def test_checkpoint_flag_is_strict(study_run, flag):
    config, store, _, study, measurements = study_run
    with pytest.raises(AgentError, match="Boolean"):
        Tools(study, Budget(store, config.model)).call(
            "calibrate", {"policy": candidate(), "checkpoint": flag}
        )
    assert not measurements and store.get("candidate_checkpoint") is None


def test_invalid_measurement_cannot_replace_checkpoint(study_run, monkeypatch):
    _, store, _, study, _ = study_run
    checkpoint(study)
    before = store.get("candidate_checkpoint")
    measure = Study.measure

    def invalid(self, policy, split):
        return {**measure(self, policy, split), "valid": False}

    monkeypatch.setattr(Study, "measure", invalid)
    assert checkpoint(study, "invalid")["valid"] is False
    assert store.get("candidate_checkpoint") == before


@pytest.mark.parametrize("failure", ["artifact", "transaction"])
def test_checkpoint_failure_preserves_prior_selection_and_calibration(
    study_run, monkeypatch, failure
):
    _, store, backend, study, _ = study_run
    checkpoint(study)
    before = store.get("candidate_checkpoint")
    replacement_hash = backend.validate_policy(candidate("replacement")).policy_hash
    if failure == "artifact":
        original_put = store.put

        def put(kind, value, **kwargs):
            if kind == "candidate_checkpoint":
                raise AgentError("checkpoint storage failed")
            return original_put(kind, value, **kwargs)

        monkeypatch.setattr(store, "put", put)
        expected = AgentError
    else:
        with store.connect() as db:
            db.execute("""CREATE TRIGGER refuse_checkpoint BEFORE INSERT ON state
                WHEN NEW.key='candidate_checkpoint'
                BEGIN SELECT RAISE(ABORT, 'checkpoint commit failed'); END""")
        expected = sqlite3.IntegrityError
    with pytest.raises(expected):
        checkpoint(study, "replacement")
    assert store.get("candidate_checkpoint") == before
    assert store.get(f"calibration:{replacement_hash}") is None


@pytest.mark.parametrize("marked", [False, True])
def test_budget_exhaustion_after_calibration_never_dispatches_again(study_run, monkeypatch, marked):
    config, store, backend, study, measurements = study_run
    config.model = type(config.model).model_validate(
        {**config.model.model_dump(), "ceiling_usd": ".0003"}
    )
    store.set("config", config.public())
    requests = []
    events = []
    original_finalize = Study.finalize_checkpoint

    def finalize(self):
        assert events == ["sandbox_closed", "broker_closed"]
        return original_finalize(self)

    monkeypatch.setattr(Study, "finalize_checkpoint", finalize)

    def dispatch(**kwargs):
        requests.append(kwargs)
        if len(requests) != 1:
            pytest.fail("budget-exhausted exploration must not dispatch another request")
        return response(command("calibrate", {"policy": candidate(), "checkpoint": marked}))

    install_local_provider(monkeypatch, dispatch)
    original_broker = controller.FileBroker
    original_env = controller.ContainerEnvironment

    class ClosingBroker(original_broker):
        def __exit__(self, *args):
            events.append("broker_closed")

    def environment(workspace, broker):
        env = original_env(workspace, broker)
        env.close = lambda: events.append("sandbox_closed")
        return env

    monkeypatch.setattr(controller, "FileBroker", ClosingBroker)
    monkeypatch.setattr(controller, "ContainerEnvironment", environment)
    outcome = explore(config, store, backend)
    assert outcome["termination_reason"] == "budget_exhausted"
    assert len(requests) == len(measurements) == 1
    assert len(Budget(store, config.model).summary()["calls"]) == 1
    assert store.get("trajectory") and store.get("ledger")
    assert store.get("test_entitlement") is None
    if marked:
        assert outcome["status"] == "frozen"
        assert outcome["finalization_source"] == "checkpoint"
        assert outcome["policy_hash"] == study.checkpoint_policy_hash()
        assert store.get("report") is None
    else:
        assert outcome["status"] == "budget_exhausted"
        result = store.read(store.get("report"))
        assert result["status"] == "no_recommendation" and result["valid"]
        assert result["reason_code"] == "no_eligible_checkpoint"
        assert store.get("frozen") is None


@pytest.mark.parametrize(
    "change",
    [
        "compatibility",
        "copy",
        "workload",
        "study",
        "boundaries",
        "calibration",
        "artifact",
        "hash",
    ],
)
def test_changed_checkpoint_cannot_freeze(study_run, monkeypatch, change):
    config, store, backend, study, measurements = study_run
    checkpoint(study)
    selected = store.get("candidate_checkpoint")
    if change == "compatibility":
        original = backend.compatibility()
        monkeypatch.setattr(backend, "compatibility", lambda: {**original, "changed": True})
    elif change == "copy":
        store.set("prepared", {**store.get("prepared"), "changed": True})
    elif change == "workload":
        config.workload.passes += 1
    elif change == "study":
        store.set("study", "different-study-artifact")
    elif change == "boundaries":
        store.set("hardness_boundaries", {"lower": 0, "upper": 0})
    elif change == "calibration":
        key = f"calibration:{selected['policy_hash']}"
        store.set(key, {**store.get(key), "status": "no_recommendation"})
    elif change == "artifact":
        path = store.root / "private/artifacts" / f"{selected['artifact']}.json"
        path.write_bytes(b"x" * path.stat().st_size)
    else:
        store.set("candidate_checkpoint", {**selected, "policy_hash": "incorrect"})
    monkeypatch.setattr(Study, "measure", fail)
    monkeypatch.setattr(backend, "execute_probe", fail)
    result = study.finalize_checkpoint()
    assert result["reason_code"] == "checkpoint_ineligible" and not result["valid"]
    assert result["failure"] and result["failure_message"]
    assert store.get("frozen") is None and store.get("test_entitlement") is None
    assert len(measurements) == 1


def test_recalibration_invalidates_the_same_selected_policy(study_run, monkeypatch):
    _, store, _, study, _ = study_run
    checkpoint(study)
    selected = store.get("candidate_checkpoint")
    original_measure = Study.measure

    def rejected(self, policy, split):
        return {**original_measure(self, policy, split), "status": "no_recommendation"}

    monkeypatch.setattr(Study, "measure", rejected)
    checkpoint(study)
    assert store.get("candidate_checkpoint") == selected
    assert study.finalize_checkpoint()["reason_code"] == "checkpoint_ineligible"


@pytest.mark.parametrize("failure", ["artifact", "transaction"])
def test_freeze_failure_is_reported_and_can_be_retried(study_run, monkeypatch, failure):
    config, store, backend, study, measurements = study_run
    checkpoint(study)
    original_put = store.put
    if failure == "artifact":

        def put(kind, value, **kwargs):
            if kind == "frozen_policy":
                raise AgentError("frozen storage failed")
            return original_put(kind, value, **kwargs)

        monkeypatch.setattr(store, "put", put)
    else:
        with store.connect() as db:
            db.execute("""CREATE TRIGGER refuse_finalization BEFORE INSERT ON state
                WHEN NEW.key='finalization' AND NEW.value LIKE '%checkpoint%'
                BEGIN SELECT RAISE(ABORT, 'freeze commit failed'); END""")
    result = exhausted_resume(config, store, backend)
    assert result["status"] == "budget_exhausted"
    report_value = store.read(store.get("report"))
    assert report_value["reason_code"] == "checkpoint_finalization_failed"
    assert not report_value["valid"] and report_value["failure_message"]
    assert store.get("frozen") is None and store.get("test_entitlement") is None
    monkeypatch.setattr(store, "put", original_put)
    if failure == "transaction":
        with store.connect() as db:
            db.execute("DROP TRIGGER refuse_finalization")
    monkeypatch.setattr(Study, "measure", fail)
    monkeypatch.setattr(backend, "execute_probe", fail)
    result = explore(config, store, backend, resume=True)
    assert result["status"] == "frozen"
    assert store.get("report") is None and len(measurements) == 1


def test_reopen_is_idempotent_and_final_test_is_separate(study_run, monkeypatch, capsys):
    config, store, backend, study, measurements = study_run
    checkpoint(study)
    selected = store.get("candidate_checkpoint")
    store.set("status", "budget_exhausted")
    import fannagent.model as model_module

    monkeypatch.setattr(model_module, "BudgetedModel", fail)
    monkeypatch.setattr(controller, "FileBroker", fail)
    monkeypatch.setattr(controller, "ContainerEnvironment", fail)
    config, reopened, backend = open_run(store.root)
    first = explore(config, reopened, backend, resume=True)
    frozen = reopened.get("frozen")
    assert first["status"] == "frozen" and first["policy_hash"] == selected["policy_hash"]
    assert reopened.get("report") is None and reopened.get("test_entitlement") is None
    second = explore(config, reopened, backend, resume=True)
    assert second == first and reopened.get("frozen") == frozen
    status(reopened.root)
    status_value = json.loads(capsys.readouterr().out)
    assert status_value["checkpoint_policy_hash"] == selected["policy_hash"]
    assert status_value["termination_reason"] == "budget_exhausted"
    study = Study(config, reopened, backend)
    final_report = study.final()
    assert final_report["termination_reason"] == "budget_exhausted"
    assert final_report["finalization_source"] == "checkpoint"
    assert final_report["status"] == "accepted"
    assert study.final() == final_report
    assert [split for _, split in measurements] == ["calibration", "test"]
    assert explore(config, reopened, backend, resume=True) == first
    assert reopened.read(reopened.get("report")) == final_report
    report(reopened.root)
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["result"]["finalization_source"] == "checkpoint"


def test_step_limit_and_abstention_do_not_freeze(study_run, monkeypatch):
    config, store, backend, study, _ = study_run
    checkpoint(study)
    install_local_provider(monkeypatch, lambda **kw: response(command("inspect", {})))
    assert explore(config, store, backend, step_limit=1)["status"] == "interrupted"
    assert store.get("frozen") is None
    from minisweagent.exceptions import InterruptAgentFlow

    def abstain(*args):
        raise InterruptAgentFlow({"role": "exit", "content": "No candidate submitted"})

    # Exercise an explicit exit action through the local environment rather than Docker.
    from fannagent.environment import ScriptedEnvironment

    class ExitEnvironment(ScriptedEnvironment):
        def execute(self, action):
            abstain()

        def close(self):
            pass

    install_local_provider(monkeypatch, lambda **kw: response("exit 0"))
    monkeypatch.setattr(
        controller, "ContainerEnvironment", lambda workspace, broker: ExitEnvironment(broker.tools)
    )
    assert explore(config, store, backend, resume=True)["status"] == "no_recommendation"
    assert store.get("frozen") is None and store.get("test_entitlement") is None


def test_operational_failure_does_not_freeze(study_run, monkeypatch):
    config, store, backend, study, _ = study_run
    checkpoint(study)

    def dispatch(**kwargs):
        raise TimeoutError("provider timeout")

    install_local_provider(monkeypatch, dispatch)
    with pytest.raises(AgentError, match="provider request failed"):
        explore(config, store, backend)
    assert store.get("frozen") is None and store.get("status") == "interrupted"


def test_funded_response_can_submit_at_the_ceiling(study_run, monkeypatch):
    config, store, backend, study, _ = study_run
    config.model = type(config.model).model_validate(
        {**config.model.model_dump(), "ceiling_usd": ".0003"}
    )
    store.set("config", config.public())
    checkpoint(study)
    requests = []

    def dispatch(**kwargs):
        requests.append(kwargs)
        return response(command("submit", {"policy": candidate()}))

    install_local_provider(monkeypatch, dispatch)
    assert explore(config, store, backend)["status"] == "frozen"
    assert len(requests) == 1 and store.get("finalization") is None


def test_old_resume_receives_checkpoint_notice_once(study_run, monkeypatch):
    config, store, backend, _, _ = study_run
    install_local_provider(monkeypatch, lambda **kw: response(command("inspect", {})))
    explore(config, store, backend, step_limit=1)
    before = store.read(store.get("trajectory"))
    before.pop("checkpoint_protocol_version")
    store.set("trajectory", store.put("trajectory", before))
    explore(config, store, backend, resume=True, step_limit=2)
    after = store.read(store.get("trajectory"))
    assert after["messages"][: len(before["messages"])] == before["messages"]
    notices = [m for m in after["messages"] if m.get("content") == controller.CHECKPOINT_GUIDANCE]
    assert len(notices) == 1 and after["checkpoint_protocol_version"] == 1
    assert after["startup_context_version"] == before["startup_context_version"]
    assert after["info"]["model_stats"]["api_calls"] == 2
    explore(config, store, backend, resume=True, step_limit=3)
    final = store.read(store.get("trajectory"))
    assert final["messages"][: len(after["messages"])] == after["messages"]
    assert sum(m.get("content") == controller.CHECKPOINT_GUIDANCE for m in final["messages"]) == 1


def test_completed_test_report_is_never_replaced(study_run):
    config, store, backend, study, _ = study_run
    checkpoint(study)
    completed = {"status": "accepted", "valid": True, "split": "test"}
    identity = store.put("report", completed)
    store.set_many({"report": identity, "test_entitlement": "consumed"})
    result = exhausted_resume(config, store, backend)
    assert result["reason_code"] == "checkpoint_ineligible"
    assert store.get("frozen") is None and store.get("report") == identity
    assert store.read(identity) == completed


def test_readonly_store_rejects_transactional_mutation(study_run):
    _, store, _, _, _ = study_run
    with pytest.raises(AgentError, match="read-only"):
        ReadOnlyStore(store.root).set_many({"status": "changed"})


def test_full_evidence_store_preserves_failure_report(study_run, monkeypatch, capsys):
    config, store, backend, study, _ = study_run
    checkpoint(study)
    with store.connect() as db:
        used = db.execute("SELECT SUM(bytes) FROM artifacts").fetchone()[0]
    limited = config.public()
    limited["evidence"]["max_bytes"] = used
    store.set("config", limited)
    result = exhausted_resume(config, store, backend)
    assert result["reason_code"] == "checkpoint_finalization_failed"
    assert store.get("frozen") is None
    assert store.get("ledger_summary") == Budget(store, config.model).summary()
    assert store.get("budget_exhaustion_report")["report_storage_failure"]
    report(store.root)
    saved = json.loads(capsys.readouterr().out)["result"]
    assert saved["reason_code"] == "checkpoint_finalization_failed" and not saved["valid"]
    store.set("config", config.public())
    monkeypatch.setattr(Study, "measure", fail)
    assert explore(config, store, backend, resume=True)["status"] == "frozen"
    assert store.get("budget_exhaustion_report") is None and store.get("report") is None


def test_real_calibration_checkpoint_freezes_without_experiments(tmp_path, monkeypatch):
    config, store, backend = prepared_run(tmp_path)
    result = explore(config, store, backend, step_limit=3)
    assert result["status"] == "interrupted"
    assert store.get("candidate_checkpoint") is not None and store.get("frozen") is None
    monkeypatch.setattr(Study, "measure", fail)
    monkeypatch.setattr(backend, "execute_probe", fail)
    monkeypatch.setattr(controller, "ScriptedEnvironment", fail)
    result = exhausted_resume(config, store, backend)
    assert result["status"] == "frozen" and result["finalization_source"] == "checkpoint"
    assert store.get("test_entitlement") is None


def test_resume_without_a_checkpoint_does_not_reopen_study(study_run, monkeypatch):
    config, store, backend, study, _ = study_run
    study.validate(candidate(), calibration=True)
    monkeypatch.setattr(backend, "snapshot", fail)
    monkeypatch.setattr(controller, "ContainerEnvironment", fail)
    result = exhausted_resume(config, store, backend)
    assert result["reason_code"] == "no_eligible_checkpoint" and result["valid"]
    assert store.get("frozen") is None


def test_explicit_submission_can_choose_another_candidate(study_run):
    _, store, backend, study, _ = study_run
    checkpoint(study)
    study.validate(candidate("explicit"), calibration=True)
    submitted = study.submit(candidate("explicit"))
    assert submitted["policy_hash"] == backend.validate_policy(candidate("explicit")).policy_hash
    assert submitted["policy_hash"] != study.checkpoint_policy_hash()
    assert store.get("finalization") is None


def test_cleanup_failure_does_not_finalize_checkpoint(study_run, monkeypatch):
    config, store, backend, study, _ = study_run
    config.model = type(config.model).model_validate(
        {**config.model.model_dump(), "ceiling_usd": ".0003"}
    )
    store.set("config", config.public())
    checkpoint(study)
    install_local_provider(monkeypatch, lambda **kw: response(command("inspect", {})))
    original_env = controller.ContainerEnvironment

    def close():
        raise AgentError("sandbox cleanup failed")

    def environment(workspace, broker):
        env = original_env(workspace, broker)
        env.close = close
        return env

    monkeypatch.setattr(controller, "ContainerEnvironment", environment)
    with pytest.raises(AgentError, match="sandbox cleanup failed"):
        explore(config, store, backend)
    assert store.get("status") == "interrupted" and store.get("frozen") is None
    assert store.get("trajectory") and store.get("ledger")
