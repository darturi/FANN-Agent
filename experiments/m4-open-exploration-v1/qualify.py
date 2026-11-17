"""Real-bound continuation rehearsal using scripted responses and no network."""

import json
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from exploration_run import drive
from exploration_support import DEST, PRIOR_SPEND, seed_campaign, verify_origin, write


class Script:
    automatic_retries = False

    def __init__(self, policy):
        def tool(identity, name, arguments):
            return [{"type": "tool_use", "id": identity, "name": name, "input": arguments}]

        self.blocks = [tool(f"inspect-{n}", "inspect_workload", {}) for n in range(16)]
        self.blocks += [
            tool(f"batch-{n}", "evaluate_candidates", {"policies": [policy, {}, policy]})
            for n in range(4)
        ]
        self.blocks += [
            tool(
                "compare-all",
                "compare_candidates",
                {"candidate_ids": [f"candidate-{n}" for n in range(1, 21)]},
            ),
            tool("finish", "submit_or_abstain", {}),
        ]
        self.requests, self.counts = [], []

    def count(self, request, ordinal, phase):
        self.counts.append({"ordinal": ordinal, "phase": phase})

    def __call__(self, request):
        self.requests.append(deepcopy(request))
        return {
            "model": "scripted",
            "usage": {"input_tokens": 100, "output_tokens": 20},
            "content": self.blocks.pop(0),
        }


def qualify():
    output = DEST / "qualification-v1"
    output.mkdir(exist_ok=False)
    original = verify_origin()
    with patch("socket.create_connection", side_effect=AssertionError("no network in rehearsal")):
        campaign = seed_campaign(
            output / "campaign", {"status": "simulation_only"}, simulation=True
        )
        state = campaign.store.get("v2_state")
        policy = campaign.store.read(state["registry"]["candidate-7"])["policy"]
        transport = Script(policy)
        outcomes = drive(campaign, transport, simulation=True)
    state = campaign.store.get("v2_state")
    budget = campaign.budget.summary()
    assert len(outcomes) == len(transport.requests) == 22
    assert state["candidate_submissions"] == len(state["registry"]) == 20
    assert state["tool_calls"] == 32
    assert state["terminal"] == "finalists_frozen_pending_live_measurement"

    # Canonical duplicate selection uses the frozen selector's lexicographic ID
    # ordering. Above nine records, an equivalent candidate-11 can precede -7.
    # Check exact rule identities rather than assuming the same duplicate alias.
    def hashes(ids):
        return {campaign.store.read(state["registry"][cid])["rule_hash"] for cid in ids}

    assert hashes(campaign.shortlist()) == hashes(original["formal_M5_nominees"])
    assert all(item["phase"] == "research" for item in transport.counts)
    assert len(budget["calls"]) == 30
    assert Decimal(budget["committed_usd"]) == PRIOR_SPEND + Decimal("0.0088")
    assert "error" not in outcomes[-2]["tool_results"][0]["result"]
    assert all(
        campaign.store.read(state["registry"][f"candidate-{n}"]).get("rejected")
        for n in (10, 13, 16, 19)
    )
    verify_origin()
    receipt = {
        "status": "passed_open_exploration_actual_bound_rehearsal",
        "prior_real_requests": 8,
        "prior_real_spend_usd": str(PRIOR_SPEND),
        "scripted_new_requests": 22,
        "scripted_cumulative_requests": 30,
        "cumulative_candidate_submissions": 20,
        "cumulative_domain_tools": 32,
        "compared_candidate_ids": 20,
        "scripted_total_spend_usd": budget["committed_usd"],
        "ending_reason": state["terminal"],
        "scripted_finalists": campaign.shortlist(),
        "fixture_note": "Existing candidate7 duplicated to exercise growth; no new discovery.",
        "prior_charge_ids_preserved": True,
        "prior_history_preserved": True,
        "original_outcome_unchanged": True,
        "new_paid_requests": 0,
        "new_count_requests": 0,
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
    }
    write(output / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    qualify()
