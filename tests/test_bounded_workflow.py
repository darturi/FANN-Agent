"""No provider or Docker: exercise a complete bounded research conversation."""

import json
import subprocess

import pytest
from test_checkpoint import response
from test_startup_context import initial_context, install_local_provider
from test_workflow import configuration

from fannagent import environment
from fannagent.backends.fake import PROFILE
from fannagent.broker import Tools
from fannagent.budget import Budget
from fannagent.config import ModelConfig, ResearchConfig
from fannagent.controller import command, explore, open_run
from fannagent.errors import AgentError
from fannagent.experiments import scripted_conclusion, scripted_plan
from fannagent.study import Study
from fannagent.submission import SubmissionTracker


def prepared(tmp_path):
    config = configuration()
    config.research = ResearchConfig(mode="guided")
    config.model = ModelConfig(
        model="provider/test",
        ceiling_usd="3",
        input_usd_per_million="1",
        output_usd_per_million="2",
        input_token_bound=100000,
        output_token_limit=1000,
        pricing_revision="fixture",
        bound_verified=True,
        max_attempts=1,
    )
    config, store, backend = open_run(tmp_path / "run", config)
    store.set("prepared", backend.prepare_copy().serialize())
    return config, store, backend


def start(key, purpose):
    return command("experiment", {"action": "start", "plan": scripted_plan(key, purpose)})


def finish(key):
    return command(
        "experiment",
        {
            "action": "finish",
            "client_key": key,
            "conclusion": scripted_conclusion(),
        },
    )


def test_catalog_covers_development_only_and_exposes_pagination(tmp_path, monkeypatch):
    config, store, backend = prepared(tmp_path)
    study = Study(config, store, backend)
    tools = Tools(study, Budget(store, config.model), turn_limit=12)
    target = backend.inspect_target()
    target["startup_summary"] = {"reviews_trial": {"allowed_collection_groups": []}}
    monkeypatch.setattr(backend, "inspect_target", lambda: target)
    context = tools.startup_context()
    catalog = context["development_queries"]
    items = store.read(catalog["catalog_artifact"], agent=True)["items"]
    assert len(items) == len(study.development) == catalog["count"]
    assert len({i["group"] for i in items}) == catalog["independent_vector_groups"]
    assert all(set(item) == {"query", "group"} for item in items)
    assert {i["query"]["id"] for i in items} == {i["query"]["id"] for i in study.development}
    held_out = {i["query"]["id"] for i in study.manifest["items"] if i["split"] != "development"}
    assert not held_out & {i["query"]["id"] for i in items}
    assert "vector" not in json.dumps(catalog["representative_groups"])
    assert context["runtime_feature_groups"] == {}
    assert len(tools.call("queries", {})) == 20
    assert len(tools.call("queries", {"limit": 200})) == 100
    assert tools.call("queries", {"offset": 100, "limit": 100}) == [
        i["query"] for i in items[100:200]
    ]
    assert context["workflow"]["full_development_evaluation_by_turn"] == 6
    assert context["workflow"]["calibration_by_turn"] == 8


@pytest.mark.parametrize("accepted", [True, False])
def test_real_evaluation_calibration_or_abstention_within_twelve_turns(
    tmp_path,
    monkeypatch,
    accepted,
):
    import litellm

    def forbidden(*args, **kwargs):
        pytest.fail("offline regression must never dispatch to a provider")

    monkeypatch.setattr(litellm, "completion", forbidden)
    config, store, backend = prepared(tmp_path)
    study = Study(config, store, backend)
    policy = PROFILE.scripted_policy if accepted else {"name": "premature", "root": "stop"}
    actions = [
        start("screen", "investigation"),
        command("labels", {"query": study.development[0]["query"]}),
        finish("screen"),
        start("candidate", "candidate_evaluation"),
        command("development_evaluate", {"policy": policy}),
        finish("candidate"),
    ]
    actions += (
        [
            start("calibration", "calibration"),
            command("calibrate", {"policy": policy, "checkpoint": True}),
            finish("calibration"),
            command("submit", {"policy": policy}),
        ]
        if accepted
        else ["exit 0"]
    )
    requests, splits = [], []
    measure = Study.measure

    def measured(self, candidate, split):
        splits.append(split)
        return measure(self, candidate, split)

    monkeypatch.setattr(Study, "measure", measured)

    def dispatch(**kwargs):
        index = len(requests)
        requests.append(kwargs)
        assert kwargs["num_retries"] == kwargs["max_retries"] == 0
        if index == 0:
            context = initial_context({"messages": kwargs["messages"]})
            assert context["workflow"]["model_turn_limit"] == 12
            assert context["development_queries"]["count"] == len(study.development)
            assert "sim.ready" in context["runtime_feature_groups"]["simulation"]
            assert '"query": QUERY_OBJECT' in kwargs["messages"][0]["content"]
        else:
            notice = json.loads(
                kwargs["messages"][-1]["content"].split("Study workflow progress:\n")[1]
            )
            assert notice["model_turns_remaining"] == 12 - index
            assert notice["charged_provider_attempts"] == index
            assert notice["successful_calibration_operations"] == (1 if index >= 8 else 0)
            assert "private" not in json.dumps(notice)
            if index == 6:
                assert notice["reserve_warning"] and "If supported" in notice["next_step"]
        assert index < len(actions), "controller requested an extra attempt"
        return response(actions[index])

    install_local_provider(monkeypatch, dispatch)
    result = explore(config, store, backend, step_limit=12)
    assert len(requests) == len(actions) <= 12
    assert splits == (["development", "calibration"] if accepted else ["development"])
    assert result["status"] == ("frozen" if accepted else "no_recommendation")
    assert bool(store.get("candidate_checkpoint")) is accepted
    assert bool(store.get("frozen")) is accepted
    assert store.get("test_entitlement") is None
    if accepted:
        assert result["research"]["experiments"]["completed"] == 3
        assert len(result["research"]["candidate_origins"]) == 1
        assert result["checkpoint_policy_hash"] == backend.validate_policy(policy).policy_hash


def bare_container():
    env = environment.ContainerEnvironment.__new__(environment.ContainerEnvironment)
    env.name = "offline-container"
    env.submissions = SubmissionTracker()
    env.turn_id = env.submissions.begin_turn()
    return env


def test_full_evaluation_can_outlast_three_minutes_without_replay(monkeypatch):
    env = bare_container()
    calls = []
    ticks = iter([0, 180])  # even the entire syntax allowance leaves a full broker deadline
    monkeypatch.setattr(environment.time, "monotonic", lambda: next(ticks))

    def run(argv, **kwargs):
        calls.append((argv, kwargs["timeout"]))
        if "-lc" in argv and kwargs["timeout"] < 900:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        return subprocess.CompletedProcess(argv, 0, "completed", "")

    monkeypatch.setattr(environment.subprocess, "run", run)
    monkeypatch.setattr(env, "close", lambda: pytest.fail("valid long evaluation was killed"))
    assert env.execute({"command": "fannagent-tool development_evaluate '{}'"})["returncode"] == 0
    assert len(calls) == 2  # syntax check and one execution, never replay
    assert 3600 < calls[1][1] <= environment.DEVELOPMENT_COMMAND_TIMEOUT_SECONDS


def test_command_deadline_still_stops_sandbox_without_retry(monkeypatch):
    env = bare_container()
    calls, closed = [], []

    def run(argv, **kwargs):
        calls.append(argv)
        if "-lc" in argv:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(environment.subprocess, "run", run)
    monkeypatch.setattr(env, "close", lambda: closed.append(True))
    with pytest.raises(AgentError, match="timed out; sandbox stopped"):
        env.execute({"command": "fannagent-tool development_evaluate '{}'"})
    assert closed == [True] and len(calls) == 2
