"""Exercise a seventh and eighth call with actual retained history/debt, without network."""

import json
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from run import drive
from support import DEST, PRIOR_SPEND, STUDY, canonical, seed_campaign, verify_origin, write


class Script:
    automatic_retries = False

    def __init__(self, policies):
        self.responses = iter(
            [
                [
                    {
                        "type": "tool_use",
                        "id": "diagnostic-new-policies",
                        "name": "evaluate_candidates",
                        "input": {"policies": policies},
                    }
                ],
                [
                    {
                        "type": "tool_use",
                        "id": "diagnostic-final",
                        "name": "submit_or_abstain",
                        "input": {},
                    }
                ],
            ]
        )
        self.requests, self.counts = [], []

    def count(self, request, ordinal, phase):
        self.counts.append({"ordinal": ordinal, "phase": phase, "bytes": len(canonical(request))})
        return 40000

    def __call__(self, request):
        self.requests.append(deepcopy(request))
        return {
            "model": "scripted",
            "usage": {"input_tokens": 100, "output_tokens": 20},
            "content": next(self.responses),
        }


def qualify():
    output = DEST / "qualification-v1"
    output.mkdir(exist_ok=False)
    verify_origin()
    programs = json.loads(
        (STUDY / "kits/m1-runtime-qualification-v2/compiled-programs.json").read_text()
    )["bindings"]
    policies = {p["arm"]: p["policy"] for p in programs}
    with patch(
        "socket.create_connection", side_effect=AssertionError("no network in qualification")
    ):
        campaign = seed_campaign(
            output / "retained-six-call-campaign", {"status": "simulation_only"}, simulation=True
        )
        transport = Script([policies[20], policies[21], policies[22]])
        outcomes = drive(campaign, transport, simulation=True)
        assert len(outcomes) == 2
        assert "candidate_ids" in outcomes[-1]["tool_results"][0]["result"]
    state = campaign.store.get("v2_state")
    assert len(campaign.budget.summary()["calls"]) == 8
    assert Decimal(campaign.budget.summary()["committed_usd"]) == PRIOR_SPEND + Decimal("0.0008")
    assert [c["ordinal"] for c in transport.counts] == [7, 8]
    assert [c["phase"] for c in transport.counts] == ["research", "closing"]
    assert state["candidate_submissions"] == 9 and state["tool_calls"] == 10
    assert state["terminal"] == "finalists_frozen_pending_live_measurement"
    assert set(campaign.shortlist()) == {"candidate-7", "candidate-8", "candidate-9"}
    assert [t["name"] for t in transport.requests[-1]["tools"]] == ["submit_or_abstain"]
    assert not campaign.store.get("v2_round_pending")
    verify_origin()
    receipt = {
        "status": "passed_actual_bound_dollar_continuation_beyond_six_and_reserved_closure",
        "prior_real_requests": 6,
        "prior_real_spend_usd": str(PRIOR_SPEND),
        "scripted_total_requests": 8,
        "scripted_phases": transport.counts,
        "synthetic_additional_spend_usd": "0.0008",
        "known_diagnostic_fixture_nominees": campaign.shortlist(),
        "fixture_policies_are_not_new_discovery_or_real_model_seeds": True,
        "prior_candidates_retained": 6,
        "cumulative_submissions": 9,
        "cumulative_tools": 10,
        "closing_tool_only": True,
        "request_ceiling": None,
        "ceiling_usd": "15",
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
