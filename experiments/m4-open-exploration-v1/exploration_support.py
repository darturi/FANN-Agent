"""Versioned continuation of the settled eight-call ledger; no inference on import."""

import json
import shutil
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "m4-dollar-budget-v1"))
import support as legacy  # noqa: E402
from support import (  # noqa: E402
    ROOT,
    STUDY,
    Evidence,
    ModelConfig,
    canonical,
    digest,
    prompt_hash,
    sha,
)
from support import accept_count as accept_count  # noqa: E402
from support import count_payload as count_payload  # noqa: E402
from support import finish_without_submission as finish_without_submission  # noqa: E402
from support import has_cache_directive as has_cache_directive  # noqa: E402
from support import post as post  # noqa: E402
from support import verify_current_provider as verify_current_provider  # noqa: E402
from support import write as write  # noqa: E402

from fannagent.store import Store  # noqa: E402

PRIOR = legacy.DEST
DEST = STUDY / "m4-open-exploration-v1"
PRIOR_SPEND = Decimal("0.403114")
CONFIG = {
    **legacy.CONFIG,
    "prior_Messages_requests": 8,
    "prior_spend_usd": str(PRIOR_SPEND),
    "remaining_USD": str(Decimal("15") - PRIOR_SPEND),
    "candidate_submissions": None,
    "domain_tools": None,
    "reserved_closing_tools": None,
}


def verify_origin():
    legacy.verify_package()
    receipt = json.loads((PRIOR / "assessment-v1/receipt.json").read_text())
    if receipt["total_spend_usd"] != str(PRIOR_SPEND) or receipt["total_Messages_requests"] != 8:
        raise ValueError("expected the settled eight-call origin")
    for path, expected in receipt["live_artifacts_sha256"].items():
        if sha(ROOT / path) != expected:
            raise ValueError("completed M4 outcome changed: " + path)
    return receipt


def template(phase, *, simulation=False):
    request = json.loads((DEST / "prepared/research-template.json").read_text())
    if phase == "closing":
        request["tools"] = [t for t in request["tools"] if t["name"] == "submit_or_abstain"]
    elif phase != "research":
        raise ValueError("unknown exploration phase")
    if simulation:
        request["model"] = "scripted"
    return request


def choose_phase(campaign):
    summary = campaign.budget.summary()
    if summary["uncertain_calls"]:
        raise ValueError("uncertain charge requires audit before another request")
    available = Decimal("15") - Decimal(summary["committed_usd"])
    maximum = campaign.budget.maximum_call()
    if available < maximum:
        return "unaffordable"
    if (
        campaign.store.get("dollar_phase") == "closing"
        or available < maximum * 2
        or campaign.store.get("dollar_invalid_replies", 0) >= 3
    ):
        return "closing"
    return "research"


def notice(campaign, phase, *, initial=False):
    state, summary = campaign.store.get("v2_state"), campaign.budget.summary()
    value = {
        "host_protocol": "open-exploration-v1",
        "phase": phase,
        "cumulative_spend_usd": summary["committed_usd"],
        "ceiling_usd": "15",
        "remaining_USD": str(Decimal("15") - Decimal(summary["committed_usd"])),
        "Messages_requests_so_far": len(summary["calls"]),
        "Messages_request_cap": None,
        "candidate_submissions_so_far": state["candidate_submissions"],
        "candidate_submission_cap": None,
        "domain_tools_so_far": state["tool_calls"],
        "domain_tool_cap": None,
        "instruction": "Submit the eligible shortlist or abstain now; only submit_or_abstain "
        "is available."
        if phase == "closing"
        else "Explore additional evidence-backed hypotheses when useful. Submit or abstain when "
        "further investigation is unlikely to help; spending the full budget is not a goal. "
        "There is no cumulative request, candidate or domain-tool ceiling. Keep all six filters, "
        "raw-native quality, scoring-only exact truth and the protected holdouts.",
    }
    if initial:
        value["amendment"] = (
            "This supersedes all historical candidate/tool/request quotas in the transcript. "
            "The prior submission belongs to the preserved completed episode. This version "
            "resumes development from all eight candidates, ten tools, eight charges and exact "
            "feedback, with the same cumulative $15 ceiling and $0.403114 already spent. "
            "The prior nominees and sealed M5 kit remain historical, unchanged artifacts."
        )
        value["measured_cost_supported_masks"] = campaign.evidence.bundle["shortlist_contract"][
            "supported_masks"
        ]
    return {"role": "user", "content": canonical(value).decode()}


def append_notice(campaign, phase, *, initial=False):
    campaign.store.set_many(
        {
            "dollar_phase": phase,
            "v2_messages": campaign.store.get("v2_messages")
            + [notice(campaign, phase, initial=initial)],
        }
    )


def request_for(campaign, *, simulation=False):
    request = template(campaign.store.get("dollar_phase", "research"), simulation=simulation)
    request["messages"] = campaign.store.get("v2_messages")
    return request


def seed_campaign(target, authorization, *, simulation=False):
    from exploration_controller import ExplorationCampaign

    verify_origin()
    shutil.copytree(DEST / "prepared/origin-campaign", target)
    store = Store(target, create=False)
    with store.connect() as db:
        charges = [dict(row) for row in db.execute("SELECT * FROM charges ORDER BY rowid")]
    if (
        len(charges) != 8
        or any(row["status"] != "settled" for row in charges)
        or sum(Decimal(row["actual"]) / 1000000000 for row in charges) != PRIOR_SPEND
    ):
        raise ValueError("all eight settled charges must carry forward")
    state = store.get("v2_state")
    if (
        state["terminal"] != "finalists_frozen_pending_live_measurement"
        or state["candidate_submissions"] != 8
        or len(state["registry"]) != 8
        or state["tool_calls"] != 10
        or store.get("v2_round_pending")
    ):
        raise ValueError("completed origin has different candidates, tools or pending work")
    history, old_contract = deepcopy(store.get("v2_messages")), store.get("v2_contract")
    config = ModelConfig.model_validate(
        json.loads((DEST / "prepared/model-config.json").read_text())
    )
    gates = json.loads((DEST / "prepared/gates.json").read_text())
    gates["provider_authorization"] = authorization
    if simulation:
        config = config.model_copy(update={"model": "scripted"})
        store.set("budget_contract", config.model_dump(mode="json"))
        gates["phase_prompt_hashes"] = {
            p: prompt_hash(template(p, simulation=True)) for p in ("research", "closing")
        }
    state["terminal"] = None
    store.set_many(
        {"v2_state": state, "dollar_phase": "research", "dollar_invalid_replies": 0},
        delete=("v2_contract", "v2_prompt_contract"),
    )
    contract = json.loads((DEST / "prepared/contract.json").read_text())
    evidence = Evidence(json.loads((ROOT / contract["evidence_workspace_path"]).read_text()))
    campaign = ExplorationCampaign(store, config, evidence, gates)
    append_notice(campaign, "research", initial=True)
    assert campaign.store.get("v2_messages")[:-1] == history
    with store.connect() as db:
        assert [dict(row) for row in db.execute("SELECT * FROM charges ORDER BY rowid")] == charges
    store.set(
        "open_exploration_bridge",
        {
            "old_contract": old_contract,
            "prior_history_sha256": digest(history),
            "prior_charge_ids": [row["id"] for row in charges],
            "prior_spend_usd": str(PRIOR_SPEND),
            "prior_candidates_retained": list(state["registry"]),
            "simulation_only": simulation,
        },
    )
    return campaign


def verify_package():
    value = json.loads((DEST / "package-freeze.json").read_text())
    for section in ("source_sha256", "artifact_sha256"):
        for path, expected in value[section].items():
            if sha(ROOT / path) != expected:
                raise ValueError("open-exploration packet changed: " + path)
    verify_origin()
    return value


def load_authorization(path):
    value = json.loads(Path(path).read_text())
    contract = json.loads((DEST / "prepared/contract.json").read_text())
    required = {
        "status": "authorized",
        "model": "claude-sonnet-5-5",
        "spending_policy": "dollar_ceiling",
        "max_requests": None,
        "max_count_requests": None,
        "candidate_submissions": None,
        "domain_tools": None,
        "max_output_tokens": 6000,
        "ceiling_usd": "15",
        "prior_spend_usd": str(PRIOR_SPEND),
        "evidence_hash": contract["evidence_identity"],
        "contract_sha256": sha(DEST / "prepared/contract.json"),
        "package_sha256": sha(DEST / "package-freeze.json"),
    }
    if (
        any(key not in value or value[key] != expected for key, expected in required.items())
        or not value.get("user_approval_record")
        or value.get("simulation_only")
    ):
        raise ValueError("authorization differs from the open-exploration contract")
    verify_package()
    return value
