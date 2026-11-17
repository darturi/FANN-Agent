from copy import deepcopy
from decimal import Decimal

import common
import dispatch
import pytest
from common import (
    CONTEXT,
    DEST,
    PRIOR_SPEND,
    ApprovalRequired,
    ProtocolError,
    accept_count,
    count_payload,
    request_for,
    seed_campaign,
    verify_origin,
)
from qualify import Script, use
from run_continuation import run


@pytest.mark.parametrize("count", [-1, True, "100", None, 900001])
def test_invalid_context_estimate_is_rejected(count):
    with pytest.raises(ValueError):
        accept_count({"input_tokens": count})


@pytest.mark.parametrize("count", [0, 900000])
def test_estimate_leaves_output_and_large_model_context_margin(count):
    assert accept_count({"input_tokens": count}) == count
    assert count + 6000 <= 906000 < 1000000


def test_missing_amendment_approval_blocks_before_credentials_or_network(tmp_path, monkeypatch):
    monkeypatch.setattr(dispatch, "credentials", lambda: pytest.fail("credential access"))
    monkeypatch.setattr(dispatch, "post", lambda *_: pytest.fail("provider traffic"))
    with pytest.raises(ApprovalRequired):
        run(tmp_path / "missing-approval.json")
    assert not (DEST / "live-continuation").exists()


def test_fork_retains_the_real_debt_history_receipts_and_original_terminal(tmp_path):
    verify_origin()
    c = seed_campaign(tmp_path / "fork", {"status": "simulation_only"}, simulation=True)
    assert len(c.budget.summary()["calls"]) == 2
    assert Decimal(c.budget.summary()["committed_usd"]) == PRIOR_SPEND
    state = c.store.get("v2_state")
    assert state["tool_calls"] == 4 and len(state["receipts"]) == 4
    assert state["candidate_submissions"] == 0 and not state["registry"]
    assert state["terminal"] is None
    assert c.store.get("m4_context_result_slots") == 4
    assert c.store.get("v2_messages") == request_for()["messages"]
    verify_origin()


def test_cached_tool_ids_consume_feedback_slots_without_changing_idempotency(tmp_path):
    c = seed_campaign(tmp_path / "cached", {"status": "simulation_only"}, simulation=True)
    identity = request_for()["messages"][1]["content"][-1]["id"]
    transport = Script([[use(identity, "inspect_workload", {})]] * 2)
    for _ in range(2):
        c.round(request_for(c, simulation=True), transport)
    assert c.store.get("v2_state")["tool_calls"] == 4
    assert c.store.get("m4_context_result_slots") == 6
    assert len(c.budget.summary()["calls"]) == 4


@pytest.mark.parametrize("kind", ["assistant-size", "feedback-slots"])
def test_provider_envelope_violation_is_terminal_and_retains_reservation(tmp_path, kind):
    c = seed_campaign(tmp_path / kind, {"status": "simulation_only"}, simulation=True)
    if kind == "assistant-size":
        blocks = [
            {
                "type": "thinking",
                "thinking": "",
                "signature": "x" * CONTEXT["assistant_message_bytes"],
            }
        ]
    else:
        blocks = [use(str(n), "inspect_workload", {}) for n in range(9)]
    with pytest.raises(ProtocolError):
        c.round(request_for(c, simulation=True), Script([blocks]))
    assert c.store.get("v2_state")["terminal"] == "provider_failure_or_uncertain_response"
    assert c.store.get("v2_state")["tool_calls"] == 4
    assert c.budget.summary()["uncertain_calls"] == 1
    assert Decimal(c.budget.summary()["committed_usd"]) == PRIOR_SPEND + Decimal("2.06")


def transport(tmp_path, monkeypatch, replies):
    auth = tmp_path / "synthetic-approval.json"
    auth.write_text('{"synthetic_unit_only":true}')
    monkeypatch.setattr(dispatch, "load_approval", lambda _: {})
    monkeypatch.setattr(dispatch, "verify_package", lambda _: {})
    calls = []

    def post(path, payload, folder):
        calls.append((path, deepcopy(payload)))
        folder.mkdir()
        return replies[path]

    monkeypatch.setattr(dispatch, "post", post)
    return dispatch.ContinuationTransport(auth, tmp_path / "provider"), calls


def test_failed_count_stops_before_money_and_cannot_be_retried(tmp_path, monkeypatch):
    c = seed_campaign(tmp_path / "campaign", {"status": "simulation_only"}, simulation=True)
    t, calls = transport(
        tmp_path, monkeypatch, {"/v1/messages/count_tokens": {"input_tokens": 900001}}
    )
    with pytest.raises(ValueError, match="input limit"):
        t.count(request_for(), 3)
    assert len(c.budget.summary()["calls"]) == 2
    assert Decimal(c.budget.summary()["committed_usd"]) == PRIOR_SPEND
    with pytest.raises(ValueError, match="reused"):
        t.count(request_for(), 3)
    assert len(calls) == 1 and calls[0][0] == "/v1/messages/count_tokens"
    assert t.message_attempts == 0


def test_counted_payload_must_match_messages_exactly_and_progress_is_unchanged(
    tmp_path, monkeypatch
):
    progress = {"type": "thinking", "thinking": "", "signature": "synthetic-signed-progress"}
    response = {
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5-5",
        "usage": {},
        "content": [progress],
    }
    t, calls = transport(
        tmp_path,
        monkeypatch,
        {
            "/v1/messages/count_tokens": {"input_tokens": 15000},
            "/v1/messages": response,
        },
    )
    request = request_for()
    with pytest.raises(ValueError, match="preflight"):
        t(request)
    t.count(request, 3)
    assert calls[0][1] == count_payload(request)
    altered = deepcopy(request)
    altered["messages"][-1]["content"].append({"type": "text", "text": "changed"})
    with pytest.raises(ValueError, match="preflight"):
        t(altered)
    assert t(request)["content"] == [progress]
    assert [p for p, _ in calls] == ["/v1/messages/count_tokens", "/v1/messages"]
    with pytest.raises(ValueError, match="preflight"):
        t(request)
    assert t.message_attempts == 1


def test_transport_stops_after_four_additional_ordinals(tmp_path, monkeypatch):
    t, calls = transport(
        tmp_path,
        monkeypatch,
        {
            "/v1/messages/count_tokens": {"input_tokens": 15000},
            "/v1/messages": {"type": "message", "role": "assistant", "usage": {}, "content": []},
        },
    )
    for ordinal in range(3, 7):
        t.count(request_for(), ordinal)
        t(request_for())
    with pytest.raises(ValueError):
        t.count(request_for(), 7)
    assert t.message_attempts == t.count_attempts == 4
    assert len(calls) == 8


@pytest.mark.parametrize(
    "field,value",
    [
        ("remaining_requests", 5),
        ("ceiling_usd", "16"),
        ("prior_spend_usd", "0"),
        ("max_count_tokens_requests", 5),
    ],
)
def test_amended_approval_cannot_reset_debt_or_expand_limits(tmp_path, monkeypatch, field, value):
    from common import sha, write

    monkeypatch.setattr(common, "DEST", tmp_path)
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    write(
        prepared / "continuation-contract.json",
        {"first_request_sha256": "f" * 64, "evidence_identity": "e" * 64},
    )
    (tmp_path / "package-freeze.json").write_text("{}")
    approval = {
        "status": "authorized",
        "model": "claude-sonnet-5-5",
        "package_sha256": sha(tmp_path / "package-freeze.json"),
        "contract_sha256": sha(prepared / "continuation-contract.json"),
        "first_request_sha256": "f" * 64,
        "evidence_hash": "e" * 64,
        "max_requests": 6,
        "remaining_requests": 4,
        "max_count_tokens_requests": 4,
        "max_output_tokens": 6000,
        "ceiling_usd": "15",
        "prior_spend_usd": "0.038798",
        "count_tokens_endpoint": "https://api.anthropic.com/v1/messages/count_tokens",
        "user_approval_record": "Synthetic unit test only, no live authorization.",
    }
    approval[field] = value
    path = tmp_path / "unit-only-approval.json"
    write(path, approval)
    monkeypatch.setattr(
        common, "verify_package", lambda _: pytest.fail("mismatched approval proceeded")
    )
    with pytest.raises(ApprovalRequired):
        common.load_approval(path)


@pytest.mark.parametrize("status", [200, 503])
def test_post_has_one_attempt_and_never_persists_secret_headers(tmp_path, monkeypatch, status):
    calls = []

    class Reply:
        def __init__(self):
            self.status = status

        def read(self, _):
            return b'{"input_tokens":15000}'

        def getheader(self, _):
            return "synthetic-id"

    class Connection:
        def __init__(self, host, **_):
            assert host == "api.anthropic.com"

        def request(self, method, path, **kwargs):
            assert method == "POST" and path == "/v1/messages/count_tokens"
            assert kwargs["headers"]["x-api-key"] == "synthetic-secret-never-real"
            calls.append(path)

        def getresponse(self):
            return Reply()

        def close(self):
            pass

    monkeypatch.setattr(dispatch.http.client, "HTTPSConnection", Connection)
    monkeypatch.setattr(dispatch, "credentials", lambda: "synthetic-secret-never-real")
    if status == 200:
        assert (
            dispatch.post(
                "/v1/messages/count_tokens", count_payload(request_for()), tmp_path / "post"
            )["input_tokens"]
            == 15000
        )
    else:
        with pytest.raises(ValueError, match="no retry"):
            dispatch.post(
                "/v1/messages/count_tokens", count_payload(request_for()), tmp_path / "post"
            )
    assert len(calls) == 1
    assert all(
        b"synthetic-secret-never-real" not in p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    )
