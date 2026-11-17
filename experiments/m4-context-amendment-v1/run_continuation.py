"""Actual dispatch is disabled until a separate matched amendment approval exists."""

import argparse
import json
from pathlib import Path

from common import DEST, load_approval, request_for, seed_campaign, verify_current_provider, write
from dispatch import ContinuationTransport
from run_episode import finish_without_submission


def run(authorization):
    approval = load_approval(authorization)  # Before GETs, credentials, migration or live state.
    live = DEST / "live-continuation"
    live.mkdir(exist_ok=False)
    campaign = seed_campaign(live / "campaign", approval)
    transport = None
    outcomes = []
    try:
        verify_current_provider(live / "dispatch-preflight")
        transport = ContinuationTransport(authorization, live / "provider")
        for _ in range(4):
            state = campaign.store.get("v2_state")
            if state["terminal"]:
                break
            if state["tool_calls"] >= 12 or campaign.store.get("m4_context_result_slots") >= 12:
                finish_without_submission(campaign, "cumulative_tool_limit")
                break
            ordinal = len(campaign.budget.summary()["calls"]) + 1
            request = request_for(campaign)
            transport.count(request, ordinal)  # Free context check, before monetary reservation.
            outcomes.append(campaign.round(request, transport))
    except Exception as error:
        finish_without_submission(campaign, "continuation_contract_or_provider_stop")
        write(live / "local-stop.json", {"reason": str(error), "no_automatic_retry": True})
    finish_without_submission(campaign, "cumulative_request_limit_without_submission")
    state = campaign.store.get("v2_state")
    ids = (
        campaign.shortlist()
        if state["terminal"] == "finalists_frozen_pending_live_measurement"
        else []
    )
    result = {
        "status": state["terminal"],
        "candidate_ids": ids,
        "nominees": {cid: campaign.store.read(state["registry"][cid]) for cid in ids},
        "budget": campaign.budget.summary(),
        "prior_requests": 2,
        "new_Messages_attempts": transport.message_attempts if transport else 0,
        "new_count_tokens_attempts": transport.count_attempts if transport else 0,
        "cumulative_tool_calls": state["tool_calls"],
        "cumulative_candidate_submissions": state["candidate_submissions"],
        "outcomes": outcomes,
        "validation_test_outcomes_opened": False,
        "live_policy_timing_measured": False,
        "next_step": "M5 actual development policy/matched-control qualification and timing"
        if ids
        else "No M5 nominees; assess the recorded abstention or failure before further work",
    }
    write(live / "continuation-disposition.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--authorization", type=Path, default=DEST / "authorization.json")
    a = p.parse_args()
    print(json.dumps(run(a.authorization), indent=2))
