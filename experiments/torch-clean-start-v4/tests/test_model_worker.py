import copy
import time
import uuid

import pytest
from fannclean import model, worker
from fannclean.core import digest, read, sha, write
from fannclean.engine import empty
from fannclean.model import Money
from fannclean.transport import Client, require_authorization


def authorize(stage):
    write(stage / "deployment.json", {"research_image": "sha256:" + "a" * 64})
    write(stage / "package-seal.json", {})
    write(
        stage / "authorization.json",
        {
            "status": "authorized",
            "run_id": read(stage / "config.json")["run_id"],
            "package_sha256": sha(stage / "package-seal.json"),
            "purpose": "clean_start_discovery",
            "user_instruction": "UNIT FIXTURE ONLY; never passed to a real executor",
        },
    )


def active(stage):
    write(
        stage / "private/worker.json",
        {
            "status": "running",
            "run_id": read(stage / "config.json")["run_id"],
            "started_epoch": time.time(),
        },
    )


class StubClient:
    def __init__(self, stage):
        self.stage = stage

    def status(self):
        return {
            "status": "running",
            "run_id": read(self.stage / "config.json")["run_id"],
            "discovery_seconds_remaining": 3600,
            "discovery_queries_remaining": 10000,
            "minimum_action_queries": 28,
        }

    def call(self, operation):
        assert operation == "heartbeat"


class StubProvider:
    def __init__(self, answers):
        self.answers, self.requests = iter(answers), []

    def post(self, path, payload, timeout):
        self.requests.append((path, copy.deepcopy(payload)))
        if path.endswith("count_tokens"):
            return {"input_tokens": 2000}
        answer = next(self.answers)
        if isinstance(answer, Exception):
            raise answer
        return answer


def response(content, stop="tool_use", usage=None):
    return {
        "model": model.MODEL,
        "content": content,
        "stop_reason": stop,
        "usage": usage
        or {
            "input_tokens": 2000,
            "output_tokens": 300,
            "output_tokens_details": {"thinking_tokens": 180},
        },
    }


def test_opus_fresh_conversation_thinking_roundtrip_and_no_implicit_finish(stage):
    authorize(stage)
    thought = {"type": "thinking", "thinking": "synthetic test only", "signature": "signed-fixture"}
    provider = StubProvider(
        [
            response(
                [
                    thought,
                    {
                        "type": "tool_use",
                        "id": "tool1",
                        "name": "list_queries",
                        "input": {"limit": 2},
                    },
                ]
            ),
            response([{"type": "text", "text": "done"}], stop="end_turn"),
        ]
    )
    result = model.run(stage, StubClient(stage), provider=provider, qualify=lambda *a: None)
    assert result["status"] == "model_ended_without_finish"
    paid = [p for path, p in provider.requests if path == "/v1/messages"]
    assert len(paid) == 2
    assert paid[0]["model"] == "claude-opus-5-5"
    assert paid[0]["thinking"] == {"type": "adaptive"}
    assert paid[0]["output_config"] == {"effort": "high"}
    assert paid[0]["max_tokens"] == 16000
    assert len(paid[0]["messages"]) == 1
    assert paid[1]["messages"][1]["content"][0] == thought
    assert read(stage / "host/freeze.json")["disposition"]["status"] == "incomplete"
    assert read(stage / "host/initial-conversation.json")["inherited_messages"] == 0
    assert read(stage / "host/model-ledger.json")["charged"] == 2 * (2000 * 4 + 300 * 20)
    with pytest.raises(ValueError, match="fresh host"):
        model.run(stage, StubClient(stage), provider=provider, qualify=lambda *a: None)


@pytest.mark.parametrize(
    "answer",
    [
        TimeoutError("synthetic uncertain billing"),
        response([], "max_tokens"),
        response([], usage={"input_tokens": 50000, "output_tokens": 300}),
    ],
)
def test_no_retry_on_uncertainty_truncation_or_input_bound_violation(stage, answer):
    authorize(stage)
    provider = StubProvider([answer])
    result = model.run(stage, StubClient(stage), provider=provider, qualify=lambda *a: None)
    assert result["model_closed"]
    assert read(stage / "host/freeze.json")["disposition"]["status"] == "incomplete"
    assert len([p for path, p in provider.requests if path == "/v1/messages"]) == 1
    ledger = read(stage / "host/model-ledger.json")
    if isinstance(answer, TimeoutError):
        assert next(iter(ledger["calls"].values()))["status"] == "open"


def test_context_sized_money_reservations_reduce_artificial_budget_stranding(tmp_path):
    ledger = Money(tmp_path / "money.json", "run", "0.50")
    assert ledger.reserve("one", 2000, 16000) == 16000
    first = ledger.state["calls"]["one"]
    assert first["reserved"] == 4 * 3024 + 20 * 16000
    assert first["reserved"] < 4000000  # no one-million-token input reservation per call
    ledger.settle("one", {"input_tokens": 2000, "output_tokens": 300})
    assert ledger.reserve("two", 2000, 16000) == 16000
    with pytest.raises(ValueError, match="uncertain"):
        ledger.reserve("three", 2000, 16000)


def test_no_model_or_worker_dispatch_without_matching_future_authorization(stage):
    with pytest.raises(FileNotFoundError):
        require_authorization(stage)
    authorize(stage)
    grant = read(stage / "authorization.json")
    grant["run_id"] = "previous"
    write(stage / "authorization.json", grant)
    with pytest.raises(ValueError, match="matching authorization"):
        require_authorization(stage)


def test_worker_rejects_previous_empirical_state_even_with_current_run_id(stage):
    authorize(stage)
    active(stage)
    with pytest.raises(ValueError, match="existing empirical"):
        worker.serve(stage, executor=lambda *a: pytest.fail("must not dispatch"))


def test_worker_does_not_revive_idle_session_and_rejects_late_discovery(stage):
    active(stage)
    s = read(stage / "private/worker.json")
    s["started_epoch"] -= 14500
    write(stage / "private/worker.json", s)
    with pytest.raises(ValueError, match="discovery deadline"):
        worker.dispatch(stage, "submit", uuid.uuid4().hex, {"kind": "acquire"})
    s["status"] = "stopped_idle"
    write(stage / "private/worker.json", s)
    with pytest.raises(ValueError, match="revive"):
        worker.dispatch(stage, "heartbeat")


def test_mailbox_idempotency_freeze_and_single_final(stage):
    active(stage)
    freeze = {
        "run_id": read(stage / "config.json")["run_id"],
        "policy": empty(),
        "test_feedback_seen": False,
        "disposition": {"status": "abstained"},
    }
    closed = {"run_id": freeze["run_id"], "model_closed": True, "freeze_sha256": digest(freeze)}
    payload = {
        "freeze": freeze,
        "model_closed": closed,
        "oracle_full": empty(),
        "oracle_test": empty(),
    }
    assert worker.dispatch(stage, "freeze", payload=payload)["status"] == "frozen"
    with pytest.raises(ValueError, match="already"):
        worker.dispatch(stage, "freeze", payload=payload)
    final = {"kind": "final", "policies": [empty()], "handles": [], "blocks": 2}
    identity = uuid.uuid4().hex
    assert worker.dispatch(stage, "submit", identity, final)["status"] == "registered"
    assert worker.dispatch(stage, "submit", identity, final)["status"] == "already_registered"
    with pytest.raises(ValueError, match="one final"):
        worker.dispatch(stage, "submit", uuid.uuid4().hex, final)
    with pytest.raises(ValueError, match="different action"):
        worker.dispatch(stage, "submit", identity, {**final, "blocks": 3})


def test_transport_records_uncertain_identity_and_does_not_retry(stage, tmp_path):
    calls = []

    def invoke(command, **kwargs):
        calls.append(command)
        raise TimeoutError("synthetic lost delivery")

    client = Client(stage, tmp_path / "mailbox", invoke=invoke)
    with pytest.raises(TimeoutError):
        client.action({"kind": "acquire"})
    assert len(calls) == 1
    receipt = read(next((tmp_path / "mailbox").glob("*.json")))
    assert receipt["status"] == "delivery_not_confirmed"
    assert len(receipt["identity"]) == 32


def test_worker_clock_stops_without_any_action(stage):
    authorize(stage)
    epoch = [0.0]

    def clock():
        return epoch[0]

    def sleep(seconds):
        epoch[0] += 400

    result = worker.serve(
        stage, executor=lambda *a: pytest.fail("unexpected query"), clock=clock, sleep=sleep
    )
    assert result["status"] == "stopped_idle"
    assert not (stage / "private/query-ledger.json").exists()


def test_query_budget_rejection_happens_before_compilation_or_queueing(stage, cases):
    from fannclean.core import Ledger, Limits
    from test_core_engine import request

    active(stage)
    config = read(stage / "config.json")
    ledger = Ledger(stage / "private/query-ledger.json", Limits(), config["run_id"])
    ledger.reserve("spent", 104999)
    for _ in range(1):
        # Settle a synthetic already-issued debit without running any query.
        ledger.tick("spent", "ann")
    s = read(ledger.path)
    s["requests"]["spent"]["actual"] = 104999
    write(ledger.path, s)
    ledger.settle("spent", True)
    identity = uuid.uuid4().hex
    with pytest.raises(ValueError, match="final reservation"):
        worker.dispatch(stage, "submit", identity, request("acquire", cases))
    assert not (stage / "private/queue" / identity).exists()
    assert not (stage / "private/builds").exists()


def test_transport_returns_known_rejection_without_polling_or_retry(stage, tmp_path):
    client = Client(stage, tmp_path / "mailbox")
    calls = []

    def call(operation, identity=None, payload=None):
        calls.append(operation)
        return {
            "status": "rejected",
            "request_id": identity,
            "payload_sha256": digest(payload),
            "run_id": read(stage / "config.json")["run_id"],
            "error": "query budget",
        }

    client.call = call
    assert client.action({"kind": "acquire"})["status"] == "rejected"
    assert calls == ["submit"]


def test_torch_transport_keeps_pinned_host_alias_and_strict_verification(tmp_path):
    import json
    from types import SimpleNamespace

    commands = []

    def invoke(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"status": "not_started"}))

    client = Client(
        "/private/stage",
        tmp_path / "mailbox",
        host="user@10.0.0.1",
        known_hosts=tmp_path / "known_hosts",
        host_key_alias="login.torch.hpc.nyu.edu",
        control_path="/tmp/verified-socket",
        invoke=invoke,
    )
    assert client.status()["status"] == "not_started"
    assert "HostKeyAlias=login.torch.hpc.nyu.edu" in commands[0]
    assert "StrictHostKeyChecking=yes" in commands[0]
