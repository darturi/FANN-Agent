import copy
import json
import os
import subprocess
import sys
import urllib.request
from decimal import Decimal

import pytest
from minisweagent.exceptions import FormatError
from test_checkpoint import response
from test_startup_context import install_local_provider, prepared_run

from fannagent import controller, tool_client
from fannagent.broker import Broker, FileBroker, Tools, dispatch_request
from fannagent.budget import Budget
from fannagent.controller import command, explore
from fannagent.environment import ContainerEnvironment
from fannagent.model import BudgetedModel
from fannagent.study import Study
from fannagent.submission import CORRECTION_GUIDANCE, InvalidSubmission, SubmissionTracker


@pytest.fixture
def run(tmp_path):
    return prepared_run(tmp_path, paid=True)


def tools_for(run):
    config, store, backend = run
    return Tools(Study(config, store, backend), Budget(store, config.model))


def fail(*args, **kwargs):
    pytest.fail("rejected submissions must not reach execution or consume another model call")


def install_sequence(monkeypatch, responses):
    requests = []
    sequence = iter(responses)

    def dispatch(**kwargs):
        requests.append(copy.deepcopy(kwargs))
        return next(sequence)

    install_local_provider(monkeypatch, dispatch)
    return requests


def tool_response(arguments, *, name="bash"):
    from litellm import ModelResponse

    return ModelResponse(
        choices=[
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "malformed-action",
                            "type": "function",
                            "function": {"name": name, "arguments": arguments},
                        }
                    ],
                },
            }
        ],
        usage={"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200},
    )


@pytest.mark.parametrize(
    "arguments,name",
    [
        ('{"command":', "bash"),
        ("{}", "bash"),
        ("[]", "bash"),
        ('{"command":42}', "bash"),
        ('{"command":null}', "bash"),
        ('{"command":" "}', "bash"),
        ('{"command":"\\u0000"}', "bash"),
        ('{"command":"true"}', "unknown"),
    ],
)
def test_invalid_model_actions_are_billed_and_receive_feedback(run, arguments, name):
    config, store, _ = run
    model = BudgetedModel(
        config.model, Budget(store, config.model), lambda **kw: tool_response(arguments, name=name)
    )
    with pytest.raises(FormatError) as caught:
        model.query([{"role": "user", "content": "generate a policy"}])
    extra = caught.value.messages[0]["extra"]
    assert extra["error_info"]["code"] == "invalid_tool_call"
    assert extra["response_artifact"]
    assert extra["cost"] == pytest.approx(0.0003)
    assert Decimal(model.budget.summary()["committed_usd"]) == Decimal(".0003")


def test_mixed_valid_and_invalid_model_calls_execute_nothing(run, monkeypatch):
    malformed = tool_response('{"command":42}')
    valid = response(command("inspect", {}))
    malformed.choices[0].message.tool_calls.insert(0, valid.choices[0].message.tool_calls[0])
    install_sequence(monkeypatch, [malformed])
    monkeypatch.setattr(Tools, "call", fail)
    config, store, backend = run
    result = explore(config, store, backend, step_limit=1)
    assert result["status"] == "interrupted"
    saved = store.read(store.get("trajectory"))
    assert saved["submission_recovery"]["consecutive_invalid_turns"] == 1
    assert saved["info"]["model_stats"]["instance_cost"] == pytest.approx(0.0003)


def test_invalid_then_corrected_request_succeeds_and_resets_streak(run, monkeypatch):
    requests = install_sequence(
        monkeypatch,
        [
            tool_response("{}"),
            response(command("probe", {"query": {"id": "missing-vector"}})),
            response(command("queries", {"limit": 1})),
        ],
    )
    config, store, backend = run
    monkeypatch.setattr(backend, "execute_probe", fail)
    result = explore(config, store, backend, step_limit=3)
    saved = store.read(store.get("trajectory"))
    assert result["status"] == "interrupted" and not store.get("frozen")
    assert saved["submission_recovery"]["consecutive_invalid_turns"] == 0
    assert "invalid_tool_call" in requests[1]["messages"][-1]["content"]
    assert "query.k" in requests[2]["messages"][-1]["content"]
    assert "inline numeric vector" in requests[2]["messages"][-1]["content"]
    assert "generated-" in saved["messages"][-1]["content"]
    assert saved["info"]["model_stats"]["instance_cost"] == pytest.approx(0.0009)
    assert Decimal(result["budget"]["committed_usd"]) == Decimal(".0009")


def test_three_mixed_invalid_turns_stop_and_resume_does_not_spend(run, monkeypatch):
    config, store, backend = run
    tools = tools_for(run)
    query = {**tools.study.development[0]["query"], "filter": {"op": []}}
    requests = install_sequence(
        monkeypatch,
        [
            response("fannagent-tool probe '{"),
            response(command("probe", {"query": {"id": "missing"}})),
            response(command("probe", {"query": query})),
        ],
    )
    factory = controller.ContainerEnvironment
    closed = []

    def environment(workspace, broker):
        env = factory(workspace, broker)
        env.close = lambda: closed.append(True)
        return env

    monkeypatch.setattr(controller, "ContainerEnvironment", environment)
    monkeypatch.setattr(backend, "execute_probe", fail)
    result = explore(config, store, backend)
    assert result["status"] == "invalid_submission_limit" and len(requests) == 3
    assert closed == [True]
    assert store.get("submission_recovery")["consecutive_invalid_turns"] == 3
    assert store.get("submission_recovery")["last_error"]["code"] == "invalid_filter"
    report = store.read(store.get("report"))
    assert report["status"] == "no_recommendation" and report["valid"]
    assert report["reason_code"] == "invalid_submission_limit"
    assert not store.get("frozen") and not store.get("test_entitlement")
    monkeypatch.setattr(controller, "ContainerEnvironment", fail)
    monkeypatch.setattr(backend, "snapshot", fail)
    assert explore(config, store, backend, resume=True) == result
    assert explore(config, store, backend) == result
    assert len(requests) == 3


def test_interrupted_resume_preserves_invalid_streak(run, monkeypatch):
    requests = install_sequence(monkeypatch, [tool_response("{}")] * 3)
    config, store, backend = run
    assert explore(config, store, backend, step_limit=2)["status"] == "interrupted"
    assert (
        store.read(store.get("trajectory"))["submission_recovery"]["consecutive_invalid_turns"] == 2
    )
    result = explore(config, store, backend, resume=True)
    assert result["status"] == "invalid_submission_limit" and len(requests) == 3
    assert result["budget"]["committed_usd"] == "0.0009"


def test_runtime_failure_does_not_increment_or_reset_streak(run, monkeypatch):
    config, store, backend = run
    query = tools_for(run).study.development[0]["query"]
    install_sequence(
        monkeypatch,
        [tool_response("{}"), response(command("probe", {"query": query})), tool_response("{}")],
    )

    def timeout(*args, **kwargs):
        raise TimeoutError("postgres://private-credentials")

    monkeypatch.setattr(backend, "execute_probe", timeout)
    assert explore(config, store, backend, step_limit=3)["status"] == "interrupted"
    saved = store.read(store.get("trajectory"))
    assert saved["submission_recovery"]["consecutive_invalid_turns"] == 2
    observation = next(m for m in saved["messages"] if m["role"] == "tool")
    assert "TimeoutError" in observation["content"]
    assert "private-credentials" not in observation["content"]


@pytest.mark.parametrize(
    "change",
    [
        {"vector": [1.0]},
        {"vector": [float("inf")] * 8},
        {"vector": [0.0] * 8},
        {"k": 0},
        {"k": 101},
        {"filter": {"field": [], "op": "eq", "value": 1}},
        {"filter": {"field": "m_000000", "op": [], "value": 1}},
        {"filter": {"and": [{"field": "m_000000", "op": "eq", "value": 1}, None]}},
    ],
)
def test_query_validation_is_actionable_and_precedes_execution(run, monkeypatch, change):
    tools = tools_for(run)
    query = {**tools.study.development[0]["query"], **change}
    monkeypatch.setattr(tools.study.backend, "execute_probe", fail)
    result = dispatch_request(tools, {"operation": "probe", "args": {"query": query}})
    assert not result["ok"]
    assert result["error_info"]["code"] in {"invalid_query", "invalid_filter"}
    assert result["error_info"]["details"] and result["error_info"]["hint"]


def test_policy_shape_failures_are_input_errors(run):
    tools = tools_for(run)
    for policy in [
        [],
        {},
        {
            "name": "bad",
            "root": {
                "if": {"feature": []},
                "then": "stop",
                "else": "continue",
            },
        },
        {"name": "bad", "root": "continue", "feature_groups": [None]},
    ]:
        result = dispatch_request(tools, {"operation": "validate", "args": {"policy": policy}})
        assert result["error_info"]["code"] == "invalid_policy"


def test_error_details_are_bounded_and_do_not_echo_query_values(run):
    tools = tools_for(run)
    query = {**tools.study.development[0]["query"], "vector": ["postgres://secret"]}
    result = dispatch_request(tools, {"operation": "probe", "args": {"query": query}})
    assert "postgres://secret" not in json.dumps(result)
    error = InvalidSubmission(
        "invalid_query",
        '\\"\n😀' * 5000,
        details=[{"path": "😀" * 5000, "message": '\\"\n😀' * 5000}] * 100,
        hint='\\"\n😀' * 5000,
    )
    assert len(json.dumps(error.info).encode()) <= 4096
    assert len(json.dumps(error.response()).encode()) <= 4096


def test_older_trajectory_gets_guidance_once_and_defaults_to_zero(run, monkeypatch):
    config, store, backend = run
    install_sequence(
        monkeypatch,
        [tool_response("{}"), tool_response("{}"), response(command("queries", {"limit": 1}))],
    )
    explore(config, store, backend, step_limit=1)
    saved = store.read(store.get("trajectory"))
    saved.pop("recovery_protocol_version")
    saved.pop("submission_recovery")
    saved["messages"][0]["content"] = saved["messages"][0]["content"].replace(
        CORRECTION_GUIDANCE, ""
    )
    store.set_many({"trajectory": store.put("trajectory", saved)}, delete=("submission_recovery",))
    explore(config, store, backend, resume=True, step_limit=2)
    after = store.read(store.get("trajectory"))
    assert after["submission_recovery"]["consecutive_invalid_turns"] == 1
    assert after["startup_context_version"] == saved["startup_context_version"]
    assert after["checkpoint_protocol_version"] == saved["checkpoint_protocol_version"]
    explore(config, store, backend, resume=True, step_limit=3)
    final = store.read(store.get("trajectory"))
    assert sum(m.get("content") == CORRECTION_GUIDANCE for m in final["messages"]) == 1
    assert final["submission_recovery"]["consecutive_invalid_turns"] == 0


def test_frozen_completion_wins_over_invalid_streak(run, monkeypatch):
    config, store, backend = run
    from fannagent.backends.fake import PROFILE

    study = Study(config, store, backend)
    policy = backend.validate_policy(PROFILE.scripted_policy)
    store.set(f"calibration:{policy.policy_hash}", {"status": "accepted", "valid": True})
    monkeypatch.setattr(Study, "boundaries", lambda self: None)
    mixed = response(command("probe", {"query": {}}))
    valid = response(command("submit", {"policy": PROFILE.scripted_policy}))
    valid.choices[0].message.tool_calls[0].id = "successful-submit"
    mixed.choices[0].message.tool_calls.extend(valid.choices[0].message.tool_calls)
    install_sequence(monkeypatch, [tool_response("{}"), tool_response("{}"), mixed])
    result = explore(config, store, backend)
    assert result["status"] == "frozen" and result["policy_hash"] == policy.policy_hash
    assert store.get("status") == "frozen"
    assert store.get("submission_recovery")["consecutive_invalid_turns"] == 3
    assert not store.get("report") and not store.get("test_entitlement")
    assert study.frozen_policy().policy_hash == policy.policy_hash


def test_invalid_limit_report_replaces_old_exploration_report_and_has_quota_fallback(
    run, monkeypatch
):
    config, store, backend = run
    store.set("report", store.put("report", {"status": "no_recommendation", "reason": "old"}))
    install_sequence(monkeypatch, [tool_response("{}")] * 3)
    result = explore(config, store, backend)
    assert store.read(store.get("report"))["run_status"] == "invalid_submission_limit"
    completed = store.put("report", {"status": "accepted", "split": "test"})
    store.set_many({"report": completed, "test_entitlement": "consumed"})
    assert explore(config, store, backend, resume=True) == result
    assert store.get("report") == completed
    store.set_many({}, delete=("report", "test_entitlement"))
    original_put = store.put

    def put(kind, value, **kwargs):
        if kind == "report":
            from fannagent.errors import AgentError

            raise AgentError("evidence storage limit reached")
        return original_put(kind, value, **kwargs)

    monkeypatch.setattr(store, "put", put)
    assert explore(config, store, backend, resume=True) == result
    assert store.get("invalid_submission_report")["run_status"] == "invalid_submission_limit"


def test_tracker_ignores_old_turns_and_counts_multiple_failures_once(run, monkeypatch):
    config, store, backend = run
    malformed = response(command("probe", {"query": {}}))
    second = response(command("probe", {"query": []}))
    second.choices[0].message.tool_calls[0].id = "second"
    malformed.choices[0].message.tool_calls.extend(second.choices[0].message.tool_calls)
    install_sequence(monkeypatch, [malformed])
    explore(config, store, backend, step_limit=1)
    assert store.get("submission_recovery")["consecutive_invalid_turns"] == 1
    tracker = SubmissionTracker()
    stale = tracker.begin_turn()
    active = tracker.begin_turn()
    tracker.record(stale, error={"code": "invalid_arguments"})
    tracker.record(active, success=True)
    assert tracker.finish_turn() == (None, True)


def bare_container():
    env = ContainerEnvironment.__new__(ContainerEnvironment)
    env.name = "test-container"
    env.submissions = SubmissionTracker()
    env.turn_id = env.submissions.begin_turn()
    return env


def test_shell_preflight_rejects_before_execution_without_echoing_command(monkeypatch):
    env = bare_container()
    calls = []

    def execute(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 2, "", "syntax error SECRET_VECTOR")

    monkeypatch.setattr(subprocess, "run", execute)
    result = env.execute({"command": "echo 'SECRET_VECTOR"})
    assert len(calls) == 1 and calls[0][3:6] == ["bash", "-n", "-c"]
    assert result["extra"]["error_info"]["code"] == "invalid_shell_syntax"
    assert "SECRET_VECTOR" not in result["output"]
    assert env.submissions.finish_turn()[0]["code"] == "invalid_shell_syntax"


def test_environment_rejects_bad_command_types_without_subprocess(monkeypatch):
    env = bare_container()
    monkeypatch.setattr(subprocess, "run", fail)
    result = env.execute({"command": 42})
    assert result["extra"]["error_info"]["code"] == "invalid_tool_call"


def test_masked_tool_failure_remains_visible_in_host_metadata(run, monkeypatch):
    tools = tools_for(run)
    env = bare_container()
    env.submissions = tools.submissions
    env.turn_id = tools.submissions.begin_turn()

    def execute(args, **kwargs):
        if "-lc" in args:
            assert "FANNAGENT_TURN_ID=" + env.turn_id in args
            dispatch_request(tools, {"argv": ["probe", "{"], "turn_id": env.turn_id})
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", execute)
    result = env.execute({"command": "fannagent-tool probe '{' >/dev/null || true"})
    assert result["returncode"] == 0 and "invalid_arguments" in result["output"]
    invalid, successful = tools.submissions.finish_turn()
    assert invalid["code"] == "invalid_arguments" and not successful


def test_file_and_http_transports_accept_legacy_requests_and_client_corrections(run, tmp_path):
    tools = tools_for(run)
    turn_id = tools.submissions.begin_turn()
    queue = tmp_path / "queue"
    payload = {"argv": ["probe", "{"], "turn_id": turn_id}
    with FileBroker(tools, queue) as broker:
        env = {
            **os.environ,
            "FANNAGENT_QUEUE": str(queue),
            "FANNAGENT_TOKEN": broker.token,
            "FANNAGENT_TURN_ID": turn_id,
        }
        invalid = subprocess.run(
            [sys.executable, tool_client.__file__, "probe", "{"],
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        assert invalid.returncode == 1 and not invalid.stderr
        file_error = json.loads(invalid.stdout)
        corrected = subprocess.run(
            [sys.executable, tool_client.__file__, "queries", '{"limit":1}'],
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        assert corrected.returncode == 0
        assert len(json.loads(corrected.stdout)["result"]) == 1
        missing = subprocess.run(
            [sys.executable, tool_client.__file__],
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )
        assert missing.returncode == 1 and not missing.stderr
        assert json.loads(missing.stdout)["error_info"]["code"] == "invalid_arguments"
    with Broker(tools) as broker:
        endpoint = f"http://127.0.0.1:{broker.server.server_port}/tool"

        def request(data):
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(data).encode(),
                headers={
                    "Authorization": "Bearer " + broker.token,
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as handle:
                return json.load(handle)

        assert request(payload) == file_error
        assert request({"operation": "queries", "args": {"limit": "1"}})["ok"]
        assert request({"argv": ["queries", "{}"], "operation": "queries"})["error_info"]
    assert tools.submissions.finish_turn()[0]["code"] == "invalid_arguments"


def test_unix_socket_client_recovers_from_invalid_json(run, tmp_path):
    tools = tools_for(run)
    with Broker(tools, socket_path=tmp_path / "socket") as broker:
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in {
                "FANNAGENT_QUEUE",
                "FANNAGENT_BROKER",
                "FANNAGENT_SOCKET",
            }
        }
        env.update(FANNAGENT_TOKEN=broker.token, FANNAGENT_SOCKET=str(broker.socket_path))
        invalid = subprocess.run(
            [sys.executable, tool_client.__file__, "probe", "{"],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        assert invalid.returncode == 1 and not invalid.stderr
        assert json.loads(invalid.stdout)["error_info"]["code"] == "invalid_arguments"
        corrected = subprocess.run(
            [sys.executable, tool_client.__file__, "queries", "{}"],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        assert corrected.returncode == 0 and json.loads(corrected.stdout)["ok"]
