"""Open-ended dollar-governed execution, with an explicit funded final-submission phase."""

import argparse
import json
from pathlib import Path

from exploration_network import ExplorationTransport
from exploration_support import (
    DEST,
    append_notice,
    choose_phase,
    finish_without_submission,
    load_authorization,
    request_for,
    seed_campaign,
    verify_current_provider,
    write,
)


def drive(campaign, transport, *, simulation=False):
    outcomes = []
    while not campaign.store.get("v2_state")["terminal"]:
        phase = choose_phase(campaign)
        if phase == "unaffordable":
            finish_without_submission(campaign, "dollar_reservation_unaffordable")
            break
        if phase != campaign.store.get("dollar_phase"):
            append_notice(campaign, phase)
        request = request_for(campaign, simulation=simulation)
        ordinal = len(campaign.budget.summary()["calls"]) + 1
        transport.count(request, ordinal, phase)
        outcome = campaign.round(request, transport)
        outcomes.append(outcome)
        if campaign.store.get("v2_state")["terminal"]:
            break
        if phase == "closing":
            finish_without_submission(campaign, "closing_submission_failed")
            break
        errors = campaign.store.get("dollar_invalid_replies", 0)
        campaign.store.set("dollar_invalid_replies", errors + 1 if "error" in outcome else 0)
        append_notice(campaign, choose_phase(campaign))
    return outcomes


def run(authorization):
    approval = load_authorization(authorization)
    live = DEST / "live-open-exploration"
    live.mkdir(exist_ok=False)
    campaign = seed_campaign(live / "campaign", approval)
    transport = None
    outcomes = []
    try:
        verify_current_provider(live / "dispatch-preflight")
        transport = ExplorationTransport(
            authorization, live / "provider", len(campaign.budget.summary()["calls"]) + 1
        )
        outcomes = drive(campaign, transport)
    except Exception as error:
        finish_without_submission(campaign, "exploration_contract_or_provider_stop")
        write(live / "local-stop.json", {"reason": str(error), "no_automatic_retry": True})
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
        "request_ceiling": None,
        "new_Messages_attempts": transport.message_attempts if transport else 0,
        "new_count_attempts": transport.count_attempts if transport else 0,
        "cumulative_candidates": state["candidate_submissions"],
        "cumulative_tools": state["tool_calls"],
        "outcomes": outcomes,
        "validation_test_outcomes_opened": False,
        "live_policy_timing_measured": False,
    }
    write(live / "disposition.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization", type=Path, default=DEST / "authorization.json")
    print(json.dumps(run(parser.parse_args().authorization), indent=2))
