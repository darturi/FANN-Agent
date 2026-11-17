from decimal import Decimal

import network
import pytest
from dollar_controller import DollarCampaign
from fannproto.controller import Campaign as LegacyCampaign
from fannproto.controller import ProtocolError
from fannproto.rehearsal import fixture_config, fixture_evidence, fixture_gates
from support import (
    CONFIG,
    PRIOR_SPEND,
    choose_phase,
    prompt_hash,
    seed_campaign,
    template,
    verify_origin,
)

from fannagent.errors import BudgetExceeded
from fannagent.store import Store


class Script:
    automatic_retries = False

    def __init__(self, blocks, *, maximum=False):
        self.blocks, self.maximum, self.calls = iter(blocks), maximum, 0

    def __call__(self, _):
        self.calls += 1
        return {
            "model": "scripted",
            "usage": {
                "input_tokens": 1000000 if self.maximum else 100,
                "output_tokens": 6000 if self.maximum else 20,
            },
            "content": next(self.blocks),
        }


def fixture(path):
    evidence = fixture_evidence()
    gates = fixture_gates(evidence)
    request = {
        "model": "scripted",
        "max_tokens": 6000,
        "system": "dollar-unit-fixture",
        "tools": [],
        "messages": [{"role": "user", "content": "Research within the cumulative dollar cap."}],
    }
    gates["phase_prompt_hashes"] = {p: prompt_hash(request) for p in ("research", "closing")}
    gates["execution_contract"] = CONFIG
    campaign = DollarCampaign(
        Store(path, create=True), fixture_config(input_token_bound=1000000), evidence, gates
    )
    campaign.store.set("dollar_phase", "research")
    return campaign, request


def request_for(c, base):
    return {**base, "messages": c.store.get("v2_messages") or base["messages"]}


def test_six_request_stop_is_removed_even_for_more_than_twelve_paid_rounds(tmp_path):
    c, request = fixture(tmp_path / "many")
    tool = {"type": "tool_use", "id": "cached", "name": "inspect_workload", "input": {}}
    transport = Script([[tool]] * 16)
    for _ in range(16):
        c.round(request_for(c, request), transport)
    assert transport.calls == len(c.budget.summary()["calls"]) == 16
    assert c.store.get("v2_state")["tool_calls"] == 1
    assert c.store.get("v2_state")["terminal"] is None
    assert c.store.get("v2_contract")["limits"]["paid_requests"] is None


def test_dollars_block_the_next_reservation_before_transport_not_at_call_six(tmp_path):
    c, request = fixture(tmp_path / "money")
    transport = Script([[{"type": "text", "text": "malformed"}]] * 8, maximum=True)
    for _ in range(7):
        c.round(request_for(c, request), transport)
    assert c.budget.summary()["committed_usd"] == "14.42"
    with pytest.raises(BudgetExceeded):
        c.round(request_for(c, request), transport)
    assert transport.calls == 7 and len(c.budget.summary()["calls"]) == 7


def test_closing_call_remains_funded_and_research_cannot_spend_it(tmp_path):
    c, request = fixture(tmp_path / "reserve-final")
    transport = Script([[{"type": "text", "text": "malformed"}]] * 6, maximum=True)
    for _ in range(6):
        c.round(request_for(c, request), transport)
    assert c.budget.summary()["committed_usd"] == "12.36"
    assert choose_phase(c) == "closing"
    c.store.set("dollar_phase", "closing")
    with pytest.raises(ProtocolError, match="closing"):
        c.dispatch("not-final", "inspect_workload", {})
    final = Script([[{"type": "text", "text": '{"abstain":true}'}]], maximum=True)
    assert c.round(request_for(c, request), final)["status"] == "abstained"
    assert c.budget.summary()["committed_usd"] == "14.42"


def test_tool_and_candidate_limits_reserve_submission_without_resetting_science(tmp_path):
    c, _ = fixture(tmp_path / "quota")
    for n in range(11):
        c.dispatch(str(n), "inspect_workload", {})
    assert choose_phase(c) == "closing"
    with pytest.raises(ProtocolError, match="reserved"):
        c.dispatch("overflow", "inspect_workload", {})
    assert c.dispatch("close", "submit_or_abstain", {"abstain": True})["status"] == "abstained"
    assert c.store.get("v2_state")["tool_calls"] == 12


def test_phase_hash_prevents_silent_prompt_mutation(tmp_path):
    c, request = fixture(tmp_path / "prompt")
    request["system"] = "changed outside the contract"
    transport = Script([])
    with pytest.raises(ProtocolError, match="phase"):
        c.round(request, transport)
    assert not c.budget.summary()["calls"] and transport.calls == 0


def test_uncertain_delivery_is_not_retried_and_stops_before_context_count(tmp_path):
    c, request = fixture(tmp_path / "uncertain")

    class Failure:
        automatic_retries = False

        def __call__(self, _):
            raise TimeoutError("synthetic")

    with pytest.raises(TimeoutError):
        c.round(request, Failure())
    with pytest.raises(ValueError, match="uncertain"):
        choose_phase(c)
    assert c.budget.summary()["committed_usd"] == "2.06"


def test_real_fork_keeps_six_charges_six_candidates_and_all_prior_history(tmp_path):
    verify_origin()
    c = seed_campaign(tmp_path / "fork", {"status": "simulation_only"}, simulation=True)
    assert len(c.budget.summary()["calls"]) == 6
    assert Decimal(c.budget.summary()["committed_usd"]) == PRIOR_SPEND
    assert c.store.get("v2_state")["candidate_submissions"] == 6
    assert len(c.store.get("v2_state")["registry"]) == 6
    assert c.store.get("v2_state")["tool_calls"] == 8
    assert c.store.get("v2_contract")["limits"]["paid_requests"] is None
    verify_origin()


def test_transport_has_no_hidden_six_four_or_twelve_ordinal_limit(tmp_path, monkeypatch):
    auth = tmp_path / "unit-only.json"
    auth.write_text('{"synthetic":true}')
    monkeypatch.setattr(network, "load_authorization", lambda _: {})
    monkeypatch.setattr(network, "verify_package", lambda: {})
    calls = []

    def post(path, payload, folder):
        calls.append(path)
        folder.mkdir()
        return (
            {"input_tokens": 200}
            if path.endswith("count_tokens")
            else {"type": "message", "role": "assistant", "usage": {}}
        )

    monkeypatch.setattr(network, "post", post)
    transport = network.DollarTransport(auth, tmp_path / "wire", 7)
    request = template("research")
    request["messages"] = [{"role": "user", "content": "synthetic"}]
    for ordinal in range(7, 23):
        transport.count(request, ordinal, "research")
        transport(request)
    assert transport.message_attempts == transport.count_attempts == 16
    assert len(calls) == 32


def test_closing_template_keeps_only_submission_and_old_research_math_is_inherited():
    assert [t["name"] for t in template("closing")["tools"]] == ["submit_or_abstain"]
    assert DollarCampaign.shortlist_decision is LegacyCampaign.shortlist_decision
    assert DollarCampaign.shortlist is LegacyCampaign.shortlist
    assert CONFIG["max_requests"] is None and CONFIG["max_count_requests"] is None
    assert CONFIG["remaining_USD"] == "14.755692"
