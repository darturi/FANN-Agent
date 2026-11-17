"""Configure the user's dollar-only amendment without dispatching paid inference."""

import json
import shutil
from types import SimpleNamespace

from support import (
    CONFIG,
    DEST,
    PRIOR,
    ROOT,
    Evidence,
    ModelConfig,
    ReadOnlyStore,
    canonical,
    digest,
    notice,
    prompt_hash,
    sha,
    template,
    verify_origin,
    write,
)

from fannagent.budget import Budget


def prepare():
    original = verify_origin()
    assert original["candidate_submissions"] == 6
    prepared = DEST / "prepared"
    prepared.mkdir(parents=True, exist_ok=False)
    shutil.copytree(PRIOR / "live-continuation/campaign", prepared / "origin-campaign")
    origin = ReadOnlyStore(prepared / "origin-campaign")
    request = json.loads((PRIOR / "prepared/first-request.json").read_text())
    old = "The fixed allowance is6 paid requests,$15,12 domain tools and9 candidate\n"
    old += "submissions TOTAL, at most3 per batch."
    assert request["system"].count(old) == 1
    request["system"] = request["system"].replace(
        old,
        "The cumulative dollar ceiling is$15 with NO Messages-request ceiling. "
        "Research limits remain12 domain tools and9 candidate submissions TOTAL, "
        "at most3 per batch.",
    )
    request["system"] += "\nThe dollar-budget amendment supersedes historical call-count limits in "
    request["system"] += "the transcript. Follow the current host dollar/quota/phase notices. "
    request["system"] += "A funded closing step is reserved. In closing, submit_or_abstain is "
    request["system"] += "the only available tool; do not propose more candidates.\n"
    for tool in request["tools"]:
        if tool["name"] == "explain_cases":
            tool["input_schema"]["properties"]["filter"]["enum"] = [
                "unfiltered",
                "votes743",
                "votes527",
                "votes310",
                "votes192",
                "votes108",
                "votes32",
            ]
    request["messages"] = []
    write(prepared / "research-template.json", request)
    config = ModelConfig.model_validate(
        json.loads((PRIOR / "prepared/continuation-contract.json").read_text())["model_config"]
    )
    write(prepared / "model-config.json", config.model_dump(mode="json"))
    prior_contract = json.loads((PRIOR / "prepared/continuation-contract.json").read_text())
    evidence = Evidence(json.loads((ROOT / prior_contract["evidence_workspace_path"]).read_text()))
    preview = SimpleNamespace(
        store=origin, budget=Budget(origin, config, readonly=True), evidence=evidence
    )
    first = {
        **request,
        "messages": origin.get("v2_messages") + [notice(preview, "research", initial=True)],
    }
    (prepared / "first-request.json").write_bytes(canonical(first))
    write(prepared / "first-request.preview.json", first)
    gates = json.loads((PRIOR / "prepared/bound-gates.json").read_text())
    gates["execution_contract"] = CONFIG
    gates["phase_prompt_hashes"] = {p: prompt_hash(template(p)) for p in ("research", "closing")}
    gates["provider_authorization"] = (
        "user_requested_dollar_reconfiguration_not_yet_bound_to_package"
    )
    write(prepared / "gates.json", gates)
    contract = {
        "schema": "filtered-ann.M4-dollar-budget.v1",
        "date": "2026-11-16",
        "status": "configured_dollar_ceiling_no_inference_dispatched",
        "model": "claude-sonnet-5-5",
        "config": CONFIG,
        "evidence_identity": evidence.identity,
        "evidence_workspace_path": prior_contract["evidence_workspace_path"],
        "scope": prior_contract["scope"],
        "original_closed_outcome_sha256": sha(PRIOR / "assessment-v1/receipt.json"),
        "prior_history_sha256": digest(origin.get("v2_messages")),
        "prior_charge_ids": [],
        "prior_Messages_requests": 6,
        "prior_spend_usd": "0.244308",
        "remaining_USD": CONFIG["remaining_USD"],
        "prior_candidate_submissions": 6,
        "prior_tools": 8,
        "remaining_candidate_submissions": 3,
        "remaining_domain_tools": 4,
        "first_request_bytes": len(canonical(first)),
        "first_request_sha256": sha(prepared / "first-request.json"),
        "phase_prompt_hashes": gates["phase_prompt_hashes"],
        "new_paid_requests": 0,
        "new_count_requests": 0,
        "changes": [
            "Remove paid and free-count ordinal ceilings",
            "Preserve cumulative$15 and prior debt/history/candidates",
            "Reserve funded closing step and final tool slot",
            "Explicit filter enum, cost-support disclosure and current quota notices",
        ],
    }
    with origin.connect() as db:
        contract["prior_charge_ids"] = [
            row["id"] for row in db.execute("SELECT id FROM charges ORDER BY rowid")
        ]
    write(prepared / "contract.json", contract)
    verify_origin()
    print(
        json.dumps(
            {
                k: contract[k]
                for k in (
                    "status",
                    "prior_Messages_requests",
                    "prior_spend_usd",
                    "remaining_USD",
                    "first_request_sha256",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    prepare()
