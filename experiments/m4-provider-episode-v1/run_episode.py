"""Dispatch only an explicitly approved frozen M4 packet. Preparation never calls this."""

import argparse
import json
from pathlib import Path

from episode import DEST, ROOT, Evidence, ModelConfig, make_request, write
from fannproto.controller import Campaign
from transport import MessagesTransport, load_approval, verify_current_provider, verify_sources

from fannagent.store import Store


def finish_without_submission(campaign, reason):
    with campaign.store.lease("run"):
        state = campaign.store.get("v2_state")
        if not state["terminal"]:
            state["terminal"] = "bounded_M4_abstention_" + reason
            campaign.store.set("v2_state", state)


def run(authorization_path, *, resume=False):
    prepared = DEST / "prepared"
    package = DEST / "package-freeze.json"
    # Approval/source checks precede credential access, GETs, Store creation and any POST.
    approval = load_approval(authorization_path, prepared, package)
    verify_sources(package)
    output = DEST / "live-episode"
    if resume and not output.is_dir():
        raise ValueError("no approved live episode to resume")
    output.mkdir(mode=0o700, exist_ok=resume)
    contract = json.loads((prepared / "episode-contract.json").read_text())
    evidence = Evidence(json.loads((ROOT / contract["evidence_workspace_path"]).read_text()))
    gates = json.loads((prepared / "bound-gates.json").read_text())
    gates["provider_authorization"] = approval
    campaign = Campaign(
        Store(output / "campaign", create=not resume),
        ModelConfig.model_validate(contract["model_config"]),
        evidence,
        gates,
    )
    prior_calls = len(campaign.budget.summary()["calls"])
    if resume and (
        campaign.budget.summary()["uncertain_calls"]
        or campaign.store.get("v2_round_pending")
        or campaign.store.get("v2_state")["terminal"]
        or prior_calls >= 6
    ):
        raise ValueError("uncertain, interrupted or terminal episode requires audit; no retry")
    verify_current_provider(
        output / ("dispatch-preflight" if not resume else f"resume-preflight-{prior_calls}")
    )
    transport = MessagesTransport(
        authorization_path,
        prepared,
        package,
        output / "provider",
        resume_attempts=prior_calls if resume else None,
    )
    outcomes = []
    for _ in range(6 - prior_calls):
        state = campaign.store.get("v2_state")
        if state["terminal"]:
            break
        if state["tool_calls"] >= 12:
            finish_without_submission(campaign, "tool_limit")
            break
        try:
            outcome = campaign.round(make_request(campaign, prepared), transport)
        except Exception as error:
            if not campaign.budget.summary()["calls"] or not campaign.store.get("v2_round_pending"):
                finish_without_submission(campaign, "local_contract_limit")
            write(output / "local-stop.json", {"reason": str(error), "no_automatic_retry": True})
            break
        outcomes.append(outcome)
    finish_without_submission(campaign, "request_limit_without_final_submission")
    state = campaign.store.get("v2_state")
    final_ids = []
    if state["terminal"] == "finalists_frozen_pending_live_measurement":
        final_ids = campaign.shortlist()
    result = {
        "status": state["terminal"],
        "candidate_ids": final_ids,
        "nominees": {cid: campaign.store.read(state["registry"][cid]) for cid in final_ids},
        "budget": campaign.budget.summary(),
        "tool_calls": state["tool_calls"],
        "candidate_submissions": state["candidate_submissions"],
        "outcomes": outcomes,
        "live_policy_timing_measured": False,
        "validation_test_outcomes_opened": False,
        "next_step": "M5 development-only actual program/matched-control qualification and timing",
    }
    write(output / "episode-disposition.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--authorization", type=Path, default=DEST / "authorization.json")
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    print(json.dumps(run(a.authorization, resume=a.resume), indent=2))
