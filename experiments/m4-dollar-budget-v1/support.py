"""Dollar-governed continuation without resetting any prior exposure or charges."""

import json
import shutil
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "m4-context-amendment-v1"))
import common as previous  # noqa: E402
from common import ROOT, STUDY, Evidence, ModelConfig, canonical, digest, sha  # noqa: E402
from common import accept_count as accept_count  # noqa: E402
from common import count_payload as count_payload  # noqa: E402
from common import has_cache_directive as has_cache_directive  # noqa: E402
from common import verify_current_provider as verify_current_provider  # noqa: E402
from common import write as write  # noqa: E402
from dispatch import post as post  # noqa: E402
from run_episode import finish_without_submission as finish_without_submission  # noqa: E402

from fannagent.store import ReadOnlyStore as ReadOnlyStore  # noqa: E402
from fannagent.store import Store  # noqa: E402

DEST = STUDY / "m4-dollar-budget-v1"
PRIOR = previous.DEST
PRIOR_SPEND = Decimal("0.244308")
CONFIG = {
    "spending_policy": "dollar_ceiling",
    "ceiling_usd": "15",
    "allowance_usd": "0",
    "max_requests": None,
    "max_count_requests": None,
    "count_preflight": "one_per_message",
    "prior_Messages_requests": 6,
    "prior_spend_usd": str(PRIOR_SPEND),
    "remaining_USD": str(Decimal("15") - PRIOR_SPEND),
    "max_output_tokens": 6000,
    "billing_input_token_bound": 1000000,
    "maximum_reservation_usd": "2.06",
    "closing_reservation_usd": "2.06",
    "request_byte_bound": 8 * 1024**2,
    "headroom_bytes": 8192,
    "assistant_message_bytes": 512 * 1024,
    "tool_result_block_bytes": 512 * 1024,
    "counted_input_token_limit": 900000,
    "candidate_submissions": 9,
    "domain_tools": 12,
    "reserved_closing_tools": 1,
    "automatic_retries": False,
}


def verify_origin():
    previous.verify_package(PRIOR / "package-freeze.json")
    receipt = json.loads((PRIOR / "assessment-v1/receipt.json").read_text())
    for path, digest_ in receipt["live_artifacts_sha256"].items():
        if sha(ROOT / path) != digest_:
            raise ValueError("closed six-request outcome changed: " + path)
    assert receipt["total_Messages_requests"] == 6 and receipt["total_spend_usd"] == str(
        PRIOR_SPEND
    )
    assert receipt["candidate_submissions"] == 6
    return receipt


def template(phase, *, simulation=False):
    request = json.loads((DEST / "prepared/research-template.json").read_text())
    if phase == "closing":
        request["tools"] = [t for t in request["tools"] if t["name"] == "submit_or_abstain"]
    elif phase != "research":
        raise ValueError("unknown dollar-budget phase")
    if simulation:
        request["model"] = "scripted"
    return request


def prompt_hash(request):
    return digest(
        {
            k: request.get(k)
            for k in (
                "model",
                "system",
                "tools",
                "inference_geo",
                "service_tier",
                "thinking",
                "output_config",
            )
        }
    )


def choose_phase(campaign):
    state = campaign.store.get("v2_state")
    summary = campaign.budget.summary()
    if summary["uncertain_calls"]:
        raise ValueError("uncertain charge requires audit before any further request")
    available = Decimal("15") - Decimal(summary["committed_usd"])
    maximum = campaign.budget.maximum_call()
    if available < maximum:
        return "unaffordable"
    if (
        campaign.store.get("dollar_phase") == "closing"
        or available < maximum * 2
        or state["candidate_submissions"] >= 9
        or state["tool_calls"] >= 11
        or campaign.store.get("dollar_invalid_replies", 0) >= 3
    ):
        return "closing"
    return "research"


def notice(campaign, phase, *, initial=False):
    state = campaign.store.get("v2_state")
    summary = campaign.budget.summary()
    value = {
        "host_protocol": "dollar-budget-v1",
        "phase": phase,
        "cumulative_spend_usd": summary["committed_usd"],
        "ceiling_usd": "15",
        "remaining_USD": str(Decimal("15") - Decimal(summary["committed_usd"])),
        "Messages_requests_so_far": len(summary["calls"]),
        "Messages_request_cap": None,
        "candidate_submissions_remaining": 9 - state["candidate_submissions"],
        "research_tool_slots_remaining": max(0, 11 - state["tool_calls"]),
        "closing_tool_slot_reserved": True,
        "instruction": "Submit the deterministic eligible shortlist or abstain now; "
        "only submit_or_abstain is available. Do not propose or inspect more policies."
        if phase == "closing"
        else "Continue bounded research or submit/abstain. There is no "
        "Messages-call ceiling. Keep all six filters; preserve raw-native recall; exact truth "
        "is scoring only; validation/test unavailable. Research quotas remain cumulative.",
    }
    if initial:
        value["amendment"] = "This supersedes historical six-request/four-request allowances. "
        "All six prior charges, candidates and feedback remain. Total budget is the original "
        "$15, with $0.244308 already spent. This is not a fresh $15 allocation."
        value["measured_cost_supported_masks"] = campaign.evidence.bundle["shortlist_contract"][
            "supported_masks"
        ]
        value["cost_support_note"] = "Unsupported masks remain runtime-valid but lack qualified "
        "cost estimates and cannot be nominated. No threshold repair or host optimizer is added."
    return {"role": "user", "content": canonical(value).decode()}


def append_notice(campaign, phase, *, initial=False):
    campaign.store.set("dollar_phase", phase)
    campaign.store.set(
        "v2_messages",
        campaign.store.get("v2_messages") + [notice(campaign, phase, initial=initial)],
    )


def request_for(campaign, *, simulation=False):
    request = template(campaign.store.get("dollar_phase", "research"), simulation=simulation)
    request["messages"] = campaign.store.get("v2_messages")
    return request


def seed_campaign(target, authorization, *, simulation=False):
    from dollar_controller import DollarCampaign

    shutil.copytree(DEST / "prepared/origin-campaign", target)
    store = Store(target, create=False)
    with store.connect() as db:
        charges = [dict(x) for x in db.execute("SELECT * FROM charges ORDER BY rowid")]
    assert len(charges) == 6 and all(x["status"] == "settled" for x in charges)
    assert sum(Decimal(x["actual"]) / 1000000000 for x in charges) == PRIOR_SPEND
    state = store.get("v2_state")
    assert state["terminal"] == "bounded_M4_abstention_cumulative_request_limit_without_submission"
    assert (
        state["candidate_submissions"] == len(state["registry"]) == 6 and state["tool_calls"] == 8
    )
    assert store.get("v2_round_pending") is None
    old_history = deepcopy(store.get("v2_messages"))
    old_contract = store.get("v2_contract")
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
    campaign = DollarCampaign(store, config, evidence, gates)
    append_notice(campaign, "research", initial=True)
    assert campaign.store.get("v2_messages")[:-1] == old_history
    with store.connect() as db:
        assert [dict(x) for x in db.execute("SELECT * FROM charges ORDER BY rowid")] == charges
    store.set(
        "dollar_bridge",
        {
            "old_contract": old_contract,
            "prior_history_sha256": digest(old_history),
            "prior_charge_ids": [x["id"] for x in charges],
            "prior_spend_usd": str(PRIOR_SPEND),
            "prior_candidates_retained": list(state["registry"]),
            "simulation_only": simulation,
        },
    )
    return campaign


def verify_package():
    package = DEST / "package-freeze.json"
    value = json.loads(package.read_text())
    for section in ("source_sha256", "artifact_sha256"):
        for path, digest_ in value[section].items():
            if sha(ROOT / path) != digest_:
                raise ValueError("dollar-budget packet changed: " + path)
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
        "max_output_tokens": 6000,
        "ceiling_usd": "15",
        "prior_spend_usd": str(PRIOR_SPEND),
        "evidence_hash": contract["evidence_identity"],
        "contract_sha256": sha(DEST / "prepared/contract.json"),
        "package_sha256": sha(DEST / "package-freeze.json"),
    }
    if any(value.get(k) != v for k, v in required.items()) or not value.get("user_approval_record"):
        raise ValueError("dollar-budget authorization differs from the user's cumulative cap")
    verify_package()
    return value
