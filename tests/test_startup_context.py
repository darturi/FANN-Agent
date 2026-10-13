import copy
import json

import pytest
from test_workflow import configuration

from fannagent import controller
from fannagent.broker import Tools
from fannagent.budget import Budget
from fannagent.config import ModelConfig
from fannagent.controller import command, explore, open_run
from fannagent.environment import ScriptedEnvironment
from fannagent.errors import AgentError
from fannagent.model import BudgetedModel, ScriptedModel
from fannagent.study import Study


def prepared_run(tmp_path, *, paid=False, input_bound=100000):
    config = configuration()
    if paid:
        config.model = ModelConfig(
            model="provider/test",
            ceiling_usd="1",
            input_usd_per_million="1",
            output_usd_per_million="2",
            input_token_bound=input_bound,
            output_token_limit=1000,
            pricing_revision="fixture",
            bound_verified=True,
        )
    config, store, backend = open_run(tmp_path / "run", config)
    store.set("prepared", backend.prepare_copy().serialize())
    return config, store, backend


def initial_context(trajectory):
    return json.loads(trajectory["messages"][1]["content"].split("Initial backend context:\n")[1])


def install_local_provider(monkeypatch, dispatch):
    """Exercise real request formatting and accounting without a provider or Docker."""
    import fannagent.model as model_module

    class LocalBroker:
        def __init__(self, tools, queue):
            self.tools = tools

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class LocalEnvironment(ScriptedEnvironment):
        def close(self):
            pass

    monkeypatch.setattr(
        model_module,
        "BudgetedModel",
        lambda config, budget: BudgetedModel(config, budget, dispatch),
    )
    monkeypatch.setattr(controller, "FileBroker", LocalBroker)
    monkeypatch.setattr(
        controller, "ContainerEnvironment", lambda workspace, broker: LocalEnvironment(broker.tools)
    )


def test_first_provider_request_has_context_and_can_probe(tmp_path, monkeypatch):
    from litellm import ModelResponse

    config, store, backend = prepared_run(tmp_path, paid=True)
    inspection = backend.inspect_target()
    summary = {
        "versions": {"database": "1.2"},
        "index": {"type": "hnsw"},
        "settings": {"effort": 17},
        "guidance": "Preserve effort.",
    }
    inspection.update(
        startup_summary=summary,
        settings={"effort": 17},
        guidance="Preserve effort.",
        extensions=["irrelevant-inventory"],
    )
    monkeypatch.setattr(backend, "inspect_target", lambda: inspection)
    study = Study(config, store, backend)
    query = study.development[0]["query"]
    requests = []
    operations = []
    original_call = Tools.call

    def call(self, operation, args):
        operations.append(operation)
        return original_call(self, operation, args)

    monkeypatch.setattr(Tools, "call", call)

    def dispatch(**kwargs):
        requests.append(kwargs)
        saved = store.read(store.get("trajectory"))
        assert saved["startup_context_version"] == 1
        assert saved["info"]["model_stats"]["api_calls"] == 0
        assert [m["role"] for m in kwargs["messages"]] == ["system", "user"]
        context = initial_context({"messages": kwargs["messages"]})
        assert context["backend"] == "fake"
        assert context["target"] == summary
        assert context["dataset"] == study.snapshot.description()
        assert context["dataset"]["fields"][0]["logical"] == "m_000000"
        assert context["capabilities"]["stopping"]
        assert "runtime_features" not in context["capabilities"]
        assert context["budget"]["committed_usd"] == "0"
        assert "calls" not in context["budget"]
        assert "irrelevant-inventory" not in kwargs["messages"][1]["content"]
        return ModelResponse(
            choices=[
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "first-probe",
                                "type": "function",
                                "function": {
                                    "name": "bash",
                                    "arguments": json.dumps(
                                        {"command": command("probe", {"query": query})}
                                    ),
                                },
                            }
                        ],
                    }
                }
            ],
            usage={"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200},
        )

    install_local_provider(monkeypatch, dispatch)
    assert explore(config, store, backend, step_limit=1)["status"] == "interrupted"
    assert len(requests) == 1
    assert operations == ["probe"]
    saved = store.read(store.get("trajectory"))
    context = initial_context(saved)
    tools = Tools(study, Budget(store, config.model))
    full = tools.call("artifact", {"hash": context["inspection_artifact"]})
    assert full["target"] == inspection
    registry = tools.call("artifact", {"hash": context["feature_registry_artifact"]})
    assert registry["definitions"]
    current = tools.call("inspect", {})
    assert current["target"] == inspection
    assert set(current) == {
        "target",
        "capabilities",
        "features",
        "budget",
        "checkpoint_policy_hash",
    }
    assert current["checkpoint_policy_hash"] is None


def test_fallback_summary_and_inspection_artifact(tmp_path, monkeypatch):
    config, store, backend = prepared_run(tmp_path)
    inspection = {**backend.inspect_target(), "guidance": "Use simulated features."}
    monkeypatch.setattr(backend, "inspect_target", lambda: inspection)
    assert explore(config, store, backend, step_limit=0)["status"] == "interrupted"
    saved = store.read(store.get("trajectory"))
    context = initial_context(saved)
    assert context["target"] == {"settings": {}, "guidance": "Use simulated features."}
    assert saved["scripted_index"] == saved["info"]["model_stats"]["api_calls"] == 0
    assert store.read(context["inspection_artifact"], agent=True)["target"] == inspection


@pytest.mark.parametrize("first_steps", [0, 1, 2])
def test_resume_preserves_initial_context_without_reinspection(tmp_path, monkeypatch, first_steps):
    config, store, backend = prepared_run(tmp_path)
    explore(config, store, backend, step_limit=first_steps)
    before = store.read(store.get("trajectory"))

    def unexpected_context(self):
        pytest.fail("resume must not reinspect or replace startup context")

    monkeypatch.setattr(Tools, "startup_context", unexpected_context)
    monkeypatch.setattr(controller, "SYSTEM", "Changed startup instructions")
    assert (
        explore(config, store, backend, resume=True, step_limit=first_steps + 1)["status"]
        == "interrupted"
    )
    after = store.read(store.get("trajectory"))
    assert after["messages"][: len(before["messages"])] == before["messages"]
    assert initial_context(after) == initial_context(before)
    assert after["startup_context_version"] == 1
    assert after["scripted_index"] == first_steps + 1
    assert after["info"]["model_stats"]["api_calls"] == first_steps + 1
    with store.connect() as db:
        count = db.execute(
            "SELECT COUNT(*) FROM artifacts WHERE kind='backend_inspection'"
        ).fetchone()[0]
        assert count == 1


@pytest.mark.parametrize("first_steps", [0, 1, 2])
def test_older_scripted_trajectory_retains_action_indices(tmp_path, monkeypatch, first_steps):
    from minisweagent.agents.default import DefaultAgent

    config, store, backend = prepared_run(tmp_path)
    study = Study(config, store, backend)
    tools = Tools(study, Budget(store, config.model))
    old_model = ScriptedModel(
        [
            command("inspect", {}),
            command("probe", {"query": study.development[0]["query"]}),
            command("calibrate", {"policy": {"name": "premature", "root": "stop"}}),
        ]
    )
    old_agent = DefaultAgent(
        old_model,
        ScriptedEnvironment(tools),
        system_template="Saved older system instructions",
        instance_template="{{ task }}",
        cost_limit=0,
    )
    old_agent.add_messages(
        {"role": "system", "content": "Saved older system instructions"},
        {"role": "user", "content": "Inspect this target and generate a policy."},
    )
    for _ in range(first_steps):
        old_agent.step()
    old_agent.cost = 0.125
    before = old_agent.serialize()
    store.set("trajectory", store.put("trajectory", before))
    operations = []
    original_call = Tools.call

    def call(self, operation, args):
        operations.append((operation, args))
        return original_call(self, operation, args)

    def unexpected_context(self):
        pytest.fail("older conversations must not receive startup context")

    monkeypatch.setattr(Tools, "call", call)
    monkeypatch.setattr(Tools, "startup_context", unexpected_context)
    explore(config, store, backend, resume=True, step_limit=first_steps + 1)
    assert operations[0][0] == ["inspect", "probe", "calibrate"][first_steps]
    if first_steps == 2:
        assert operations[0][1]["policy"]["name"] == "premature"
    after = store.read(store.get("trajectory"))
    assert "startup_context_version" not in after
    assert after["messages"][: len(before["messages"])] == before["messages"]
    assert after["scripted_index"] == first_steps + 1
    assert after["info"]["model_stats"]["instance_cost"] == 0.125
    assert after["info"]["model_stats"]["api_calls"] == first_steps + 1


@pytest.mark.parametrize(
    "failure", ["inspection", "summary_type", "serialization", "storage", "trajectory_storage"]
)
def test_initialization_failure_precedes_provider_spending(tmp_path, monkeypatch, failure):
    config, store, backend = prepared_run(tmp_path, paid=True)
    inspection = copy.deepcopy(backend.inspect_target())
    requests = []

    def dispatch(**kwargs):
        requests.append(kwargs)
        pytest.fail("initialization failure must precede provider dispatch")

    install_local_provider(monkeypatch, dispatch)
    if failure == "inspection":

        def inspect():
            raise AgentError("inspection failed")

        monkeypatch.setattr(backend, "inspect_target", inspect)
    else:
        if failure == "summary_type":
            inspection["startup_summary"] = "invalid"
        elif failure == "serialization":
            inspection["inventory"] = object()
        else:
            original_put = store.put

            def put(kind, value, **kwargs):
                failed_kind = (
                    "trajectory" if failure == "trajectory_storage" else "backend_inspection"
                )
                if kind == failed_kind:
                    raise AgentError("evidence storage limit reached")
                return original_put(kind, value, **kwargs)

            monkeypatch.setattr(store, "put", put)
        monkeypatch.setattr(backend, "inspect_target", lambda: inspection)
    with pytest.raises(AgentError):
        explore(config, store, backend, step_limit=1)
    assert not requests
    assert Budget(store, config.model).summary()["calls"] == []
    assert store.get("trajectory") is None


def test_oversized_startup_context_precedes_provider_spending(tmp_path, monkeypatch):
    config, store, backend = prepared_run(tmp_path, paid=True, input_bound=10000)
    inspection = {**backend.inspect_target(), "startup_summary": {"guidance": "x" * 20000}}
    monkeypatch.setattr(backend, "inspect_target", lambda: inspection)
    requests = []

    def dispatch(**kwargs):
        requests.append(kwargs)
        pytest.fail("input bound must be enforced before dispatch")

    install_local_provider(monkeypatch, dispatch)
    with pytest.raises(AgentError, match="input bound"):
        explore(config, store, backend, step_limit=1)
    assert not requests
    assert Budget(store, config.model).summary()["calls"] == []
    assert store.read(store.get("trajectory"))["startup_context_version"] == 1
