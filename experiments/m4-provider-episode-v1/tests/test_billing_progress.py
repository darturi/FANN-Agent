from copy import deepcopy
from decimal import Decimal

import pytest
from fannproto.controller import Campaign, ProtocolError
from fannproto.rehearsal import (
    ScriptedTransport,
    fixture_config,
    fixture_evidence,
    fixture_gates,
    request_for,
)

from fannagent.store import Store


def campaign(path):
    e = fixture_evidence()
    gates = fixture_gates(e)
    gates["execution_contract"] = {"request_byte_bound": 50000}
    return Campaign(Store(path, create=True), fixture_config(input_token_bound=1000000), e, gates)


def request(c):
    r = request_for(c)
    r.update(thinking={"type": "between_tools"}, output_config={"effort": "high"})
    return r


def test_signed_progress_and_redacted_blocks_round_trip_without_becoming_actions(tmp_path):
    c = campaign(tmp_path / "progress")
    blocks = [
        {
            "type": "thinking",
            "thinking": "Synthetic progress update.",
            "signature": "synthetic-signature",
        },
        {"type": "redacted_thinking", "data": "synthetic-encrypted-data"},
        {"type": "tool_use", "id": "inspect", "name": "inspect_workload", "input": {}},
    ]
    transport = ScriptedTransport(
        [deepcopy(blocks), [{"type": "text", "text": '{"abstain":true}'}]]
    )
    first = c.round(request(c), transport)
    assert len(first["tool_results"]) == 1
    history = c.store.get("v2_messages")
    assert history[-2]["content"] == blocks
    second_request = request(c)
    assert second_request["messages"][-2]["content"] == blocks
    assert c.round(second_request, transport)["status"] == "abstained"
    assert len(c.budget.summary()["calls"]) == 2


@pytest.mark.parametrize(
    "block",
    [
        {"type": "thinking", "thinking": "x"},
        {"type": "thinking", "thinking": "x", "signature": ""},
        {"type": "thinking", "thinking": 5, "signature": "test"},
        {"type": "redacted_thinking", "data": ""},
        {"type": "server_tool_use", "name": "web_search"},
    ],
)
def test_unknown_or_malformed_provider_blocks_stop_after_the_paid_response(tmp_path, block):
    c = campaign(tmp_path / "malformed")
    result = c.round(request(c), ScriptedTransport([[block]]))
    assert result["paid_request_consumed"]
    assert c.store.get("v2_state")["terminal"] == "invalid_content_envelope"
    assert c.budget.summary()["calls"][0]["status"] == "settled"


def test_financial_ceiling_uses_full_model_input_while_byte_guard_stays_small(tmp_path):
    c = campaign(tmp_path / "bounds")
    assert c.budget.maximum_call() == Decimal("2.06")
    r = request(c)
    r["messages"][0]["content"] = "x" * 50000
    transport = ScriptedTransport([])
    with pytest.raises(ProtocolError, match="input bound"):
        c.round(r, transport)
    assert not transport.requests and not c.budget.summary()["calls"]


def test_six_worst_case_reservations_stay_below15_and_seventh_is_blocked(tmp_path):
    c = campaign(tmp_path / "six")

    class MaximumUsage:
        automatic_retries = False

        def __init__(self):
            self.calls = 0

        def __call__(self, _):
            self.calls += 1
            return {
                "model": "scripted",
                "usage": {"input_tokens": 1000000, "output_tokens": 6000},
                "content": [{"type": "text", "text": "malformed final JSON"}],
            }

    transport = MaximumUsage()
    for _ in range(6):
        assert c.round(request(c), transport)["paid_request_consumed"]
    assert c.budget.summary()["committed_usd"] == "12.36"
    assert c.budget.summary()["ceiling_usd"] == "15"
    assert c.budget.summary()["allowance_usd"] == "0"
    with pytest.raises(ProtocolError, match="six paid"):
        c.round(request(c), transport)
    assert transport.calls == 6


@pytest.mark.parametrize(
    "usage",
    [
        {"input_tokens": 1000001, "output_tokens": 20},
        {"input_tokens": 100, "output_tokens": 6001},
        {"input_tokens": 100, "output_tokens": 20, "cache_creation_input_tokens": 1},
    ],
)
def test_unqualified_usage_retains_the_reservation_and_blocks_retry(tmp_path, usage):
    c = campaign(tmp_path / "usage-drift")

    class ChangedUsage:
        automatic_retries = False

        def __init__(self):
            self.calls = 0

        def __call__(self, _):
            self.calls += 1
            return {"model": "scripted", "usage": usage, "content": []}

    transport = ChangedUsage()
    with pytest.raises(ProtocolError, match="usage contract"):
        c.round(request(c), transport)
    summary = c.budget.summary()
    assert summary["committed_usd"] == "2.06" and summary["uncertain_calls"]
    with pytest.raises(ProtocolError, match="terminal"):
        c.round(request(c), transport)
    assert transport.calls == 1
