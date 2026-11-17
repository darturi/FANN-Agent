import itertools
import random
from copy import deepcopy
from decimal import Decimal

import exploration_network
import pytest
from exploration_controller import ExplorationCampaign
from exploration_run import drive
from exploration_support import (
    CONFIG,
    PRIOR_SPEND,
    choose_phase,
    prompt_hash,
    seed_campaign,
    template,
    verify_origin,
)
from fannproto.controller import ProtocolError
from fannproto.policy import FILTERS
from fannproto.rehearsal import fixture_config, fixture_evidence, fixture_gates, fixture_policy
from fannproto.uncertainty import ESTIMATE_STATUS, regret_bound
from fannproto.uncertainty import select_shortlist as old_select
from selection import select_shortlist

from fannagent.errors import BudgetExceeded
from fannagent.store import Store


class Script:
    automatic_retries = False

    def __init__(self, contents, *, maximum=False):
        self.contents, self.calls, self.maximum = iter(contents), 0, maximum
        self.phases = []

    def count(self, request, ordinal, phase):
        self.phases.append(phase)

    def __call__(self, request):
        self.calls += 1
        return {
            "model": "scripted",
            "usage": {
                "input_tokens": 1000000 if self.maximum else 100,
                "output_tokens": 6000 if self.maximum else 20,
            },
            "content": next(self.contents),
        }


def fixture(path):
    evidence = fixture_evidence()
    gates = fixture_gates(evidence)
    request = template("research", simulation=True)
    request["messages"] = [{"role": "user", "content": "Explore; stop voluntarily when useful."}]
    gates["phase_prompt_hashes"] = {
        p: prompt_hash(template(p, simulation=True)) for p in ("research", "closing")
    }
    gates["execution_contract"] = CONFIG
    campaign = ExplorationCampaign(
        Store(path, create=True), fixture_config(input_token_bound=1000000), evidence, gates
    )
    campaign.store.set_many({"v2_messages": request["messages"], "dollar_phase": "research"})
    return campaign, request


def tool(identity, name, arguments):
    return [{"type": "tool_use", "id": identity, "name": name, "input": arguments}]


def test_more_than_nine_candidates_and_twelve_unique_tools_keep_exploring(tmp_path):
    campaign, _ = fixture(tmp_path / "open")
    for n in range(24):
        answer = campaign.dispatch(f"inspect-{n}", "inspect_workload", {})
        assert "error" not in answer
    policy = fixture_policy()
    for n in range(6):
        answer = campaign.dispatch(f"batch-{n}", "evaluate_candidates", {"policies": [policy] * 3})
        assert len(answer["evaluations"]) == 3
        assert answer["candidate_submissions_remaining"] is None
    state = campaign.store.get("v2_state")
    assert state["candidate_submissions"] == len(state["registry"]) == 18
    assert state["tool_calls"] == 30 and state["terminal"] is None
    assert choose_phase(campaign) == "research"
    comparison = campaign.dispatch(
        "compare", "compare_candidates", {"candidate_ids": list(state["registry"])}
    )
    assert len(comparison["candidates"]) == 18
    assert campaign.dispatch("finish", "submit_or_abstain", {})["candidate_ids"] == ["candidate-1"]


def test_invalid_duplicates_and_cached_tools_preserve_accounting_without_exhaustion(tmp_path):
    campaign, _ = fixture(tmp_path / "invalid")
    policy = fixture_policy()
    for n in range(12):
        answer = campaign.dispatch(f"batch-{n}", "evaluate_candidates", {"policies": [{}, policy]})
        assert answer["evaluations"][0].get("rejected")
    cached = campaign.dispatch("inspect", "inspect_workload", {})
    assert campaign.dispatch("inspect", "inspect_workload", {}) == cached
    with pytest.raises(ProtocolError, match="reused"):
        campaign.dispatch("inspect", "explain_cases", {})
    assert campaign.store.get("v2_state")["candidate_submissions"] == 24
    assert campaign.store.get("v2_state")["tool_calls"] == 13
    assert choose_phase(campaign) == "research"


def test_driver_many_unique_actions_and_early_abstention_leave_budget_unspent(tmp_path):
    campaign, _ = fixture(tmp_path / "driver")
    blocks = [tool(str(n), "inspect_workload", {}) for n in range(20)]
    blocks += [tool("done", "submit_or_abstain", {"abstain": True})]
    transport = Script(blocks)
    outcomes = drive(campaign, transport, simulation=True)
    assert len(outcomes) == transport.calls == 21
    assert campaign.store.get("v2_state")["tool_calls"] == 21
    assert campaign.store.get("v2_state")["terminal"] == "explicit_abstention"
    assert Decimal(campaign.budget.summary()["committed_usd"]) < Decimal("0.01")
    with pytest.raises(ProtocolError, match="terminal"):
        campaign.dispatch("after", "inspect_workload", {})


def test_dollar_reservation_still_blocks_before_transport(tmp_path):
    campaign, request = fixture(tmp_path / "dollars")
    transport = Script([tool(str(n), "inspect_workload", {}) for n in range(8)], maximum=True)
    for _ in range(7):
        request["messages"] = campaign.store.get("v2_messages")
        campaign.round(request, transport)
    assert campaign.budget.summary()["committed_usd"] == "14.42"
    with pytest.raises(BudgetExceeded):
        request["messages"] = campaign.store.get("v2_messages")
        campaign.round(request, transport)
    assert transport.calls == 7


def test_driver_closes_with_funded_final_submission_before_budget_runs_out(tmp_path):
    campaign, _ = fixture(tmp_path / "closing")
    blocks = [tool(str(n), "inspect_workload", {}) for n in range(6)]
    blocks += [tool("done", "submit_or_abstain", {"abstain": True})]
    transport = Script(blocks, maximum=True)
    drive(campaign, transport, simulation=True)
    assert transport.phases == ["research"] * 6 + ["closing"]
    assert campaign.budget.summary()["committed_usd"] == "14.42"
    with pytest.raises(ProtocolError, match="closing|terminal"):
        campaign.dispatch("inspect-again", "inspect_workload", {})


def test_uncertain_delivery_still_stops_without_retry(tmp_path):
    campaign, request = fixture(tmp_path / "uncertain")

    class Failure:
        automatic_retries = False

        def __call__(self, request):
            raise TimeoutError("synthetic")

    with pytest.raises(TimeoutError):
        campaign.round(request, Failure())
    with pytest.raises(ValueError, match="uncertain"):
        choose_phase(campaign)
    assert campaign.budget.summary()["committed_usd"] == "2.06"


def test_quality_features_unknown_prefixes_and_holdouts_stay_protected(tmp_path):
    campaign, _ = fixture(tmp_path / "quality")
    policy = fixture_policy()
    forbidden = deepcopy(policy)
    forbidden["rules"]["votes32"][0]["conditions"] = [["query_id", ">=", 1]]
    result = campaign.dispatch("forbidden", "evaluate_candidates", {"policies": [forbidden]})
    assert result["evaluations"][0].get("rejected")
    for operation in ("sql", "shell", "validation", "test", "artifact"):
        assert "error" in campaign.dispatch(operation, operation, {})
    assert "error" in campaign.dispatch(
        "protected-filter",
        "explain_cases",
        {"category": "lossy_prefix", "filter": "test", "limit": 1},
    )
    # A runtime-valid program with an unknown chosen prefix cannot become eligible.
    campaign.evidence.rows[0]["proofs"] = {}
    result = campaign.dispatch("unknown", "evaluate_candidates", {"policies": [policy]})
    assert result["evaluations"][0]["evaluation"]["unqualified_stops"] == 1
    assert "error" in campaign.dispatch("submit-unknown", "submit_or_abstain", {})
    campaign.evidence.rows[0]["proofs"] = {"16": {"recall": 0.6, "returned_count": 7}}
    result = campaign.dispatch("loss", "evaluate_candidates", {"policies": [policy]})
    assert result["evaluations"][0]["evaluation"]["recall_losses"] == 1
    assert "error" in campaign.dispatch("submit-loss", "submit_or_abstain", {})


def test_batch_and_live_finalist_limits_remain(tmp_path):
    campaign, _ = fixture(tmp_path / "bounded-batches")
    result = campaign.dispatch(
        "too-many", "evaluate_candidates", {"policies": [fixture_policy()] * 4}
    )
    assert "error" in result and campaign.store.get("v2_state")["terminal"] is None
    assert "error" in campaign.dispatch(
        "too-many-finalists", "submit_or_abstain", {"candidate_ids": [str(i) for i in range(4)]}
    )


def test_oversized_comparison_is_recoverable_without_ending_research(tmp_path):
    campaign, _ = fixture(tmp_path / "large-comparison")
    state = campaign.store.get("v2_state")
    state["registry"]["candidate-1"] = campaign.store.put(
        "large_fixture_feedback",
        {"evaluation": {"diagnostic": "x" * (512 * 1024)}},
        scope="development",
    )
    campaign.store.set("v2_state", state)
    answer = campaign.dispatch("large", "compare_candidates", {"candidate_ids": ["candidate-1"]})
    assert "compare fewer" in answer["error"]
    assert "candidates" in campaign.store.read(answer["full_feedback_artifact"])
    assert campaign.store.get("v2_state")["terminal"] is None
    assert "error" not in campaign.dispatch("next", "inspect_workload", {})


def test_model_transcript_and_context_contract_cannot_be_silently_changed(tmp_path):
    campaign, request = fixture(tmp_path / "context")
    transport = Script([])
    changed = deepcopy(request)
    changed["system"] += "changed"
    with pytest.raises(ProtocolError, match="phase"):
        campaign.round(changed, transport)
    changed = deepcopy(request)
    changed["messages"] = [{"role": "user", "content": "reset"}]
    with pytest.raises(ProtocolError, match="transcript"):
        campaign.round(changed, transport)
    changed = deepcopy(request)
    changed["messages"] += [{"role": "user", "content": "x" * (8 * 1024**2)}]
    campaign.store.set("v2_messages", changed["messages"])
    with pytest.raises(ProtocolError, match="bytes"):
        campaign.round(changed, transport)
    assert transport.calls == 0 and not campaign.budget.summary()["calls"]


def test_real_snapshot_preserves_all_eight_charges_candidates_and_feedback(tmp_path):
    origin = verify_origin()
    campaign = seed_campaign(tmp_path / "copy", {"status": "simulation_only"}, simulation=True)
    summary, state = campaign.budget.summary(), campaign.store.get("v2_state")
    assert len(summary["calls"]) == 8 and Decimal(summary["committed_usd"]) == PRIOR_SPEND
    assert state["candidate_submissions"] == len(state["registry"]) == 8
    assert state["tool_calls"] == 10 and state["terminal"] is None
    assert campaign.shortlist() == origin["formal_M5_nominees"]
    assert choose_phase(campaign) == "research"
    limits = campaign.store.get("v2_contract")["limits"]
    assert limits["tool_calls"] is limits["candidate_submissions"] is None
    verify_origin()


def record(index, interval, *, comparisons=1):
    return {
        "candidate_id": f"candidate-{index}",
        "rule_hash": f"{index:064x}",
        "policy": {"rules": {"votes32": [{"cp": 16, "conditions": [0] * comparisons}]}},
        "evaluation": {
            "quality_preserves_raw_native640": True,
            "per_filter": {f: {"stops": int(f == "votes32")} for f in FILTERS},
        },
        "cost_estimate": {
            "status": ESTIMATE_STATUS,
            "primary_ratio_interval": interval,
            "primary_ratio_proxy": 99,
        },
    }


def test_selector_preserves_old_exact_decisions_and_ties_on_randomized_pools():
    rng = random.Random(20261117)
    for trial in range(500):
        records = []
        for i in range(trial % 10):
            low = rng.randrange(70, 105) / 100
            records.append(record(i, [low, low + rng.randrange(0, 12) / 100], comparisons=i % 3))
        rng.shuffle(records)
        assert select_shortlist(records) == old_select(records)


def test_selector_over_nine_matches_exhaustive_regret_and_fewest_finalists():
    rng = random.Random(12)
    for _ in range(30):
        records = [
            record(i, [0.9 + rng.randrange(6) / 100, 0.96 + rng.randrange(6) / 100])
            for i in range(12)
        ]
        intervals = {
            r["candidate_id"]: r["cost_estimate"]["primary_ratio_interval"] for r in records
        }
        choices = [
            (len(s), regret_bound(intervals, s))
            for n in range(4)
            for s in itertools.combinations(intervals, n)
        ]
        result = select_shortlist(records)
        assert result["best_attainable_bound"] == min(bound for _, bound in choices)
        eligible = [(n, b) for n, b in choices if b <= 0.01 + 1e-12]
        if eligible:
            assert (len(result["candidate_ids"]), result["conditional_regret_bound"]) == min(
                eligible
            )
        else:
            assert result["status"] == "abstain_uncertainty_exceeds_cap"


def test_selector_large_pool_keeps_quality_cost_and_uncertainty_gates():
    records = [record(i, [0.9, 0.96]) for i in range(2048)]
    assert select_shortlist(records)["status"] == "abstain_uncertainty_exceeds_cap"
    records[0]["cost_estimate"]["primary_ratio_interval"] = [0.7, 0.8]
    assert select_shortlist(records)["candidate_ids"] == ["candidate-0"]
    records[0]["evaluation"]["quality_preserves_raw_native640"] = False
    assert select_shortlist(records)["status"] == "abstain_uncertainty_exceeds_cap"
    records[0]["evaluation"]["quality_preserves_raw_native640"] = True
    records[0]["cost_estimate"]["status"] = "unsupported_uncertainty_estimate"
    assert select_shortlist(records)["status"] == "abstain_uncertainty_exceeds_cap"


def test_transport_has_no_tool_candidate_or_request_ordinal_ceiling(tmp_path, monkeypatch):
    auth = tmp_path / "synthetic.json"
    auth.write_text("{}")
    monkeypatch.setattr(exploration_network, "load_authorization", lambda _: {})
    monkeypatch.setattr(exploration_network, "verify_package", lambda: {})

    def post(path, payload, folder):
        folder.mkdir()
        return (
            {"input_tokens": 100}
            if path.endswith("count_tokens")
            else {"type": "message", "role": "assistant", "usage": {}}
        )

    monkeypatch.setattr(exploration_network, "post", post)
    transport = exploration_network.ExplorationTransport(auth, tmp_path / "wire", 9)
    request = template("research")
    request["messages"] = [{"role": "user", "content": "synthetic"}]
    for ordinal in range(9, 49):
        transport.count(request, ordinal, "research")
        transport(request)
    assert transport.message_attempts == transport.count_attempts == 40


def test_active_prompt_and_schema_expose_no_cumulative_search_limits():
    request = template("research")
    assert "NO cumulative candidate-submission or domain-tool-call ceiling" in request["system"]
    assert "spending $15 is not a goal" in request["system"].lower()
    tools = {t["name"]: t for t in request["tools"]}
    assert (
        "maxItems" not in tools["compare_candidates"]["input_schema"]["properties"]["candidate_ids"]
    )
    assert [t["name"] for t in template("closing")["tools"]] == ["submit_or_abstain"]
