"""Versioned continuation over the unchanged frozen research controller."""

import json
import shutil
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "m4-provider-episode-v1"))
from episode import DEST as ORIGINAL  # noqa: E402
from episode import ROOT, STUDY, Evidence, ModelConfig, canonical, digest, sha  # noqa: E402
from episode import write as write  # noqa: E402
from fannproto.controller import Campaign, ProtocolError  # noqa: E402
from transport import ApprovalRequired, has_cache_directive  # noqa: E402
from transport import verify_current_provider as verify_current_provider  # noqa: E402
from transport import verify_sources as verify_original_sources  # noqa: E402

from fannagent.store import ReadOnlyStore as ReadOnlyStore  # noqa: E402
from fannagent.store import Store  # noqa: E402

DEST = STUDY / "m4-context-amendment-v1"
PRIOR_SPEND = Decimal("0.038798")
CONTEXT = {
    "request_byte_bound": 8 * 1024**2,
    "headroom_bytes": 8192,
    "assistant_message_bytes": 512 * 1024,
    "tool_result_block_bytes": 512 * 1024,
    "counted_input_token_limit": 900000,
    "model_context_tokens": 1000000,
    "max_output_tokens": 6000,
    "count_tokens_requests": 4,
    "additional_Messages_requests": 4,
    "cumulative_Messages_requests": 6,
    "cumulative_tools": 12,
    "cumulative_submissions": 9,
    "prior_requests": 2,
    "prior_tools": 4,
    "prior_submissions": 0,
    "cumulative_feedback_slots": 12,
    "prior_feedback_slots": 4,
    "ceiling_usd": "15",
    "prior_spend_usd": str(PRIOR_SPEND),
    "remaining_monetary_headroom_usd": str(Decimal("15") - PRIOR_SPEND),
    "maximum_reservation_per_request_usd": "2.06",
    "maximum_four_new_reservations_usd": "8.24",
    "maximum_cumulative_commitment_usd": str(PRIOR_SPEND + Decimal("8.24")),
    "automatic_retries": False,
}


def tool_block(identity, value):
    return {
        "type": "tool_result",
        "tool_use_id": identity,
        "content": canonical(value).decode(),
        "is_error": "error" in value,
    }


class ContextCampaign(Campaign):
    """Research decisions unchanged; bound host result envelopes without truncation."""

    def _dispatch(self, identity, operation, arguments):
        answer = super()._dispatch(identity, operation, arguments)
        if len(canonical(tool_block(identity, answer))) > CONTEXT["tool_result_block_bytes"]:
            state = self.store.get("v2_state")
            state["terminal"] = "host_feedback_envelope_qualification_violation"
            self.store.set("v2_state", state)
            raise ProtocolError("host feedback exceeds qualified envelope; retained in full; stop")
        return answer

    def round(self, request, transport):
        if getattr(transport, "automatic_retries", None) is not False:
            raise ProtocolError("transport must disable retries")
        owner = self

        class CheckedTransport:
            automatic_retries = False

            def __call__(self, payload):
                response = transport(payload)
                content = response.get("content")
                assistant = {"role": "assistant", "content": content}
                if len(canonical(assistant)) > CONTEXT["assistant_message_bytes"]:
                    raise ProtocolError("assistant envelope exceeds qualified context capacity")
                uses = (
                    [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
                    if isinstance(content, list)
                    else []
                )
                # Cached IDs and malformed text consume feedback capacity too.
                used = owner.store.get(
                    "m4_context_result_slots", owner.store.get("v2_state")["tool_calls"]
                )
                slots = len(uses) or 1
                if used + slots > CONTEXT["cumulative_feedback_slots"]:
                    raise ProtocolError("cumulative feedback slots exceeded; stop without retry")
                owner.store.set("m4_context_result_slots", used + slots)
                return response

        return super().round(request, CheckedTransport())


def verify_origin():
    verify_original_sources(ORIGINAL / "package-freeze.json")
    assessment = json.loads((ORIGINAL / "assessment-v1/receipt.json").read_text())
    for path, digest_ in assessment["live_artifacts_sha256"].items():
        if sha(ROOT / path) != digest_:
            raise ValueError("original terminal episode changed: " + path)
    assert assessment["request_count"] == 2 and assessment["actual_spend_usd"] == str(PRIOR_SPEND)
    assert assessment["candidate_submissions"] == assessment["M5_nominees"] == 0
    return assessment


def request_for(campaign=None, *, simulation=False):
    request = json.loads((DEST / "prepared/first-request.json").read_text())
    if campaign is not None:
        request["messages"] = campaign.store.get("v2_messages")
    if simulation:
        request["model"] = "scripted"
    return request


def seed_campaign(target, authorization, *, simulation=False):
    """Fork the verified snapshot. Never reopen the original episode for writing."""
    prepared = DEST / "prepared"
    shutil.copytree(prepared / "origin-campaign", target)
    store = Store(target, create=False)
    state = store.get("v2_state")
    assert state["terminal"] == "bounded_M4_abstention_local_contract_limit"
    assert state["tool_calls"] == 4 and state["candidate_submissions"] == 0
    assert not state["registry"] and store.get("v2_round_pending") is None
    with store.connect() as db:
        before = [dict(x) for x in db.execute("SELECT * FROM charges ORDER BY rowid")]
    assert len(before) == 2 and all(x["status"] == "settled" for x in before)
    assert sum(Decimal(x["actual"]) / 1000000000 for x in before) == PRIOR_SPEND
    old_contract = store.get("v2_contract")
    old_prompt = store.get("v2_prompt_contract")
    history = deepcopy(store.get("v2_messages"))
    config_data = json.loads((ORIGINAL / "prepared/model-config.json").read_text())
    gates = json.loads((prepared / "bound-gates.json").read_text())
    gates["provider_authorization"] = authorization
    config = ModelConfig.model_validate(config_data)
    if simulation:
        config = config.model_copy(update={"model": "scripted"})
        store.set("budget_contract", config.model_dump(mode="json"))
    state["terminal"] = None
    store.set_many({"v2_state": state}, delete=("v2_contract",))
    evidence = Evidence(
        json.loads(
            (
                ROOT
                / json.loads((prepared / "continuation-contract.json").read_text())[
                    "evidence_workspace_path"
                ]
            ).read_text()
        )
    )
    campaign = ContextCampaign(store, config, evidence, gates)
    if simulation:
        req = request_for(campaign, simulation=True)
        store.set(
            "v2_prompt_contract",
            digest(
                {
                    k: req[k]
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
            ),
        )
    else:
        assert store.get("v2_prompt_contract") == old_prompt
    assert store.get("v2_messages") == history
    with store.connect() as db:
        assert [dict(x) for x in db.execute("SELECT * FROM charges ORDER BY rowid")] == before
    store.set(
        "m4_context_bridge",
        {
            "original_terminal": "bounded_M4_abstention_local_contract_limit",
            "original_contract": old_contract,
            "new_contract": store.get("v2_contract"),
            "prior_charge_ids": [x["id"] for x in before],
            "prior_spend_usd": str(PRIOR_SPEND),
            "prior_history_sha256": digest(history),
            "simulation_only": simulation,
        },
    )
    store.set("m4_context_result_slots", 4)
    return campaign


def verify_package(package):
    frozen = json.loads(Path(package).read_text())
    for section in ("source_sha256", "artifact_sha256"):
        for path, digest_ in frozen[section].items():
            if sha(ROOT / path) != digest_:
                raise ValueError("amended packet changed: " + path)
    verify_origin()
    return frozen


def load_approval(path):
    path = Path(path)
    if not path.exists():
        raise ApprovalRequired("amended continuation pending explicit approval; no data dispatch")
    value = json.loads(path.read_text())
    contract = json.loads((DEST / "prepared/continuation-contract.json").read_text())
    required = {
        "status": "authorized",
        "model": "claude-sonnet-5-5",
        "package_sha256": sha(DEST / "package-freeze.json"),
        "contract_sha256": sha(DEST / "prepared/continuation-contract.json"),
        "first_request_sha256": contract["first_request_sha256"],
        "evidence_hash": contract["evidence_identity"],
        "max_requests": 6,
        "remaining_requests": 4,
        "max_count_tokens_requests": 4,
        "max_output_tokens": 6000,
        "ceiling_usd": "15",
        "prior_spend_usd": str(PRIOR_SPEND),
        "count_tokens_endpoint": "https://api.anthropic.com/v1/messages/count_tokens",
    }
    if (
        any(value.get(k) != v for k, v in required.items())
        or not isinstance(value.get("user_approval_record"), str)
        or not value["user_approval_record"].strip()
        or value.get("simulation_only")
    ):
        raise ApprovalRequired("approval differs from amended packet and cumulative limits")
    verify_package(DEST / "package-freeze.json")
    return value


def check_request(request):
    first = request_for()
    if set(request) != set(first) or any(request[k] != first[k] for k in first if k != "messages"):
        raise ValueError("frozen prompt/tools/model/inference parameters changed")
    if has_cache_directive(request):
        raise ValueError("cache directives are outside the charge contract")
    if len(canonical(request)) + CONTEXT["headroom_bytes"] > CONTEXT["request_byte_bound"]:
        raise ValueError("qualified cumulative wire capacity exceeded")
    return digest(request)


def count_payload(request):
    return {
        k: request[k] for k in ("model", "system", "tools", "messages", "thinking", "output_config")
    }


def accept_count(value):
    count = value.get("input_tokens")
    if type(count) is not int or not 0 <= count <= CONTEXT["counted_input_token_limit"]:
        raise ValueError("token count is missing or exceeds the amended input limit")
    if count + CONTEXT["max_output_tokens"] > CONTEXT["model_context_tokens"]:
        raise ValueError("token estimate plus output exceeds model context")
    return count
