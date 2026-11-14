from decimal import Decimal

import pytest
from fannproto.controller import Campaign, ProtocolError, generation_ready, parse_final
from fannproto.evidence import Evidence
from fannproto.policy import FILTERS, PROFILE
from fannproto.rehearsal import (
    ScriptedTransport,
    fixture_bundle,
    fixture_config,
    fixture_evidence,
    fixture_gates,
    fixture_policy,
    request_for,
)

from fannagent.errors import AgentError, BudgetExceeded
from fannagent.store import Store


@pytest.fixture
def campaign(tmp_path):
    e = fixture_evidence()
    return Campaign(Store(tmp_path / "run", create=True), fixture_config(), e, fixture_gates(e))


def use(identity, name, arguments):
    return {"type": "tool_use", "id": identity, "name": name, "input": arguments}


def test_bounded_tools_preserve_all_conditions_and_charge_invalid_duplicate_slots(campaign):
    a = campaign.dispatch("i", "inspect_workload", {})
    assert set(a["per_filter"]) == set(FILTERS)
    p = fixture_policy()
    b = campaign.dispatch("e", "evaluate_candidates", {"policies": [p, {}, p]})
    assert b["candidate_submissions_remaining"] == 6
    assert b["evaluations"][0]["evaluation"]["quality_preserves_raw_native640"]
    assert "rejected" in b["evaluations"][1]
    assert b["evaluations"][0]["rule_hash"] == b["evaluations"][2]["rule_hash"]
    assert campaign.shortlist() == ["candidate-1"]
    # An exact delivery retry is read-only; changing an id's meaning is rejected.
    assert campaign.dispatch("e", "evaluate_candidates", {"policies": [p, {}, p]}) == b
    assert campaign.store.get("v2_state")["candidate_submissions"] == 3
    with pytest.raises(ProtocolError):
        campaign.dispatch("e", "inspect_workload", {})
    for i in range(2):
        campaign.dispatch("e" + str(i), "evaluate_candidates", {"policies": [p, p, p]})
    assert campaign.store.get("v2_state")["candidate_submissions"] == 9
    assert "error" in campaign.dispatch("overflow", "evaluate_candidates", {"policies": [p]})
    assert (
        campaign.store.get("v2_state")["terminal"]
        == "candidate_submission_limit_or_batch_violation"
    )


def test_batch_limit_tool_limit_and_no_other_capabilities(campaign):
    for i in range(12):
        result = campaign.dispatch(
            str(i),
            "SQL" if i % 2 else "explain_cases",
            {} if i % 2 else {"filter": "votes32", "limit": 13, "category": "short_native"},
        )
        assert "error" in result
    with pytest.raises(ProtocolError, match="tool limit"):
        campaign.dispatch("x", "inspect_workload", {})
    assert campaign.store.get("v2_state")["tool_calls"] == 12


def test_shortlist_freezes_compiled_candidate_pending_live_measurement(campaign):
    campaign.dispatch("e", "evaluate_candidates", {"policies": [fixture_policy()]})
    result = campaign.dispatch("f", "submit_or_abstain", {})
    assert result["candidate_ids"] == ["candidate-1"] and result["no_performance_promotion"]
    assert result["status"] == "finalists_frozen_pending_live_measurement"
    record = campaign.store.read(
        campaign.store.get("v2_state")["registry"]["candidate-1"], agent=True
    )
    compiled = campaign.store.read(record["compiled_artifact"], agent=True)
    assert (
        compiled["source"] and compiled["manifest"]["profile"]["fingerprint"] == PROFILE.fingerprint
    )
    with pytest.raises(ProtocolError, match="terminal"):
        campaign.dispatch("again", "inspect_workload", {})


def test_abstention_and_unique_fenced_json(campaign):
    final = parse_final(
        'Reasoning\n```json\n{"abstain":true,"notes":"negative evidence"}\n```\nDone'
    )
    assert campaign.dispatch("f", "submit_or_abstain", final)["status"] == "abstained"
    for value in ("```json\n{}\n```\n```json\n{}\n```", "[]", '{"shell":"ls"}', "{broken"):
        with pytest.raises(ProtocolError):
            parse_final(value)


def test_real_missing_gates_cannot_call_transport(campaign):
    campaign.gates = {}
    transport = ScriptedTransport([])
    with pytest.raises(ProtocolError, match="M0"):
        campaign.round(request_for(campaign), transport)
    assert not transport.requests and not campaign.budget.summary()["calls"]


def test_missing_partial_label_blocks_generation_and_finalist(tmp_path):
    b = fixture_bundle()
    del b["rows"][0]["proofs"]["16"]
    e = Evidence(b, fixture=True)
    c = Campaign(Store(tmp_path / "missing", create=True), fixture_config(), e, fixture_gates(e))
    with pytest.raises(ProtocolError, match="partial-prefix"):
        generation_ready(e, c.gates)
    r = c.dispatch("e", "evaluate_candidates", {"policies": [fixture_policy()]})
    assert (
        not r["evaluations"][0]["evaluation"]["quality_preserves_raw_native640"]
        and not c.shortlist()
    )


def test_six_requests_cap_malformed_output_is_still_charged_and_history_frozen(campaign):
    transport = ScriptedTransport([[{"type": "text", "text": "malformed"}] for _ in range(7)])
    for i in range(6):
        result = campaign.round(request_for(campaign), transport)
        assert result["paid_request_consumed"]
        assert len(campaign.budget.summary()["calls"]) == i + 1
    with pytest.raises(ProtocolError, match="six paid"):
        campaign.round(request_for(campaign), transport)
    assert len(transport.requests) == 6
    assert campaign.budget.summary()["committed_usd"] == "0.0018"
    assert all(c["status"] == "settled" for c in campaign.budget.summary()["calls"])
    assert campaign.store.get("v2_round_pending") is None


def test_transcript_tool_feedback_and_resume_contract(campaign):
    transport = ScriptedTransport([[use("inspect", "inspect_workload", {})]])
    original = request_for(campaign)
    result = campaign.round(original, transport)
    assert result["tool_results"][0]["tool_use_id"] == "inspect"
    history = campaign.store.get("v2_messages")
    assert history[-2]["content"] == [use("inspect", "inspect_workload", {})]
    assert history[-1]["content"][0]["type"] == "tool_result"
    with pytest.raises(ProtocolError, match="exact transcript"):
        campaign.round(original, transport)
    changed = request_for(campaign)
    changed["system"] = "different"
    with pytest.raises(ProtocolError, match="prompt/tools"):
        campaign.round(changed, transport)
    resumed = Campaign(campaign.store, fixture_config(), campaign.evidence, campaign.gates)
    assert resumed.store.get("v2_messages") == history
    with pytest.raises(ProtocolError, match="campaign contract"):
        Campaign(
            campaign.store, fixture_config(), campaign.evidence, {**campaign.gates, "changed": True}
        )
    with pytest.raises(AgentError, match="spending contract"):
        Campaign(
            campaign.store,
            fixture_config(ceiling_usd=Decimal("14")),
            campaign.evidence,
            campaign.gates,
        )


def test_uncertain_or_interrupted_call_is_not_retried(campaign):
    transport = ScriptedTransport([TimeoutError("scripted timeout")])
    with pytest.raises(TimeoutError):
        campaign.round(request_for(campaign), transport)
    assert campaign.budget.summary()["uncertain_calls"] == 1
    assert campaign.store.get("v2_state")["terminal"] == "provider_failure_or_uncertain_response"
    assert campaign.store.get("v2_round_pending")
    with pytest.raises(ProtocolError):
        campaign.round(request_for(campaign), transport)
    assert len(transport.requests) == 1


def test_settled_but_unfinished_round_requires_audit(campaign):
    campaign.store.set("v2_round_pending", {"reservation": "simulated-crash-after-settlement"})
    transport = ScriptedTransport([])
    with pytest.raises(ProtocolError, match="interrupted model round"):
        campaign.round(request_for(campaign), transport)
    assert not transport.requests


def test_interrupted_domain_tool_not_automatically_repeated(campaign):
    campaign.dispatch("i", "inspect_workload", {})
    s = campaign.store.get("v2_state")
    s["receipts"]["i"]["status"] = "reserved"
    campaign.store.set("v2_state", s)
    with pytest.raises(ProtocolError, match="interrupted tool"):
        campaign.dispatch("i", "inspect_workload", {})


@pytest.mark.parametrize(
    "content",
    [
        [use("same", "inspect_workload", {}), use("same", "inspect_workload", {})],
        [{"type": "text", "text": 7}],
        None,
    ],
)
def test_invalid_provider_envelope_settled_and_terminal(campaign, content):
    result = campaign.round(request_for(campaign), ScriptedTransport([content]))
    assert result["paid_request_consumed"] and campaign.store.get("v2_state")["terminal"]
    assert campaign.budget.summary()["calls"][0]["status"] == "settled"


def test_ceiling_reserved_before_transport_and_no_automatic_retries(campaign):
    # Reserve capacity is 0.16, not the much smaller scripted realized charge.
    campaign.model_config.ceiling_usd = Decimal(".15")
    transport = ScriptedTransport([])
    with pytest.raises(BudgetExceeded):
        campaign.round(request_for(campaign), transport)
    assert not transport.requests


def test_fixture_cannot_enable_real_paid_model_and_request_bound(campaign):
    campaign.model_config.model = "unapproved-paid-model"
    with pytest.raises(ProtocolError, match="fixture"):
        campaign.round(request_for(campaign), ScriptedTransport([]))
    campaign.model_config.model = "scripted"
    request = request_for(campaign)
    request["messages"][0]["content"] = "x" * 50000
    with pytest.raises(ProtocolError, match="input bound"):
        campaign.round(request, ScriptedTransport([]))
    assert not campaign.budget.summary()["calls"]


def test_text_submission_round_retains_scoped_terminal_receipt(campaign):
    transport = ScriptedTransport([[{"type": "text", "text": '{"abstain":true}'}]])
    outcome = campaign.round(request_for(campaign), transport)
    assert outcome["status"] == "abstained"
    last = campaign.store.get("v2_last_round")
    private = campaign.store.read(last["outcome_artifact"])
    assert private["outcome"] == outcome
    with pytest.raises(AgentError, match="scope"):
        campaign.store.read(last["outcome_artifact"], agent=True)
    assert campaign.store.get("v2_round_pending") is None
