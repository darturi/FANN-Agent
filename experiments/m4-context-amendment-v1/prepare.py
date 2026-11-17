"""Prepare an exact-transcript continuation; no credential or data network access."""

import json
import shutil
from decimal import Decimal

from common import (
    CONTEXT,
    DEST,
    ORIGINAL,
    PRIOR_SPEND,
    ReadOnlyStore,
    canonical,
    digest,
    sha,
    verify_origin,
    write,
)


def prepare():
    assessment = verify_origin()
    prepared = DEST / "prepared"
    prepared.mkdir(exist_ok=False)
    shutil.copytree(ORIGINAL / "live-episode/campaign", prepared / "origin-campaign")
    origin = ReadOnlyStore(prepared / "origin-campaign")
    request = json.loads((ORIGINAL / "prepared/first-request.json").read_text())
    request["messages"] = origin.get("v2_messages")
    assert len(canonical(request)) == 42382
    assert len(canonical(request)) + 8192 < CONTEXT["request_byte_bound"]
    (prepared / "first-request.json").write_bytes(canonical(request))
    write(prepared / "first-request.preview.json", request)
    gates = json.loads((ORIGINAL / "prepared/bound-gates.json").read_text())
    gates["execution_contract"]["request_byte_bound"] = CONTEXT["request_byte_bound"]
    gates["execution_contract"]["context_amendment"] = CONTEXT
    gates["provider_authorization"] = "pending_amended_continuation_approval"
    write(prepared / "bound-gates.json", gates)
    prior = json.loads((ORIGINAL / "prepared/episode-contract.json").read_text())
    assert PRIOR_SPEND + Decimal("8.24") == Decimal("8.278798") < 15
    contract = {
        "schema": "filtered-ann.M4-context-continuation.v1",
        "date": "2026-11-16",
        "status": "prepared_pending_explicit_amendment_approval",
        "model": prior["model"],
        "api_version": prior["api_version"],
        "endpoint": prior["endpoint"],
        "count_tokens_endpoint": "https://api.anthropic.com/v1/messages/count_tokens",
        "context": CONTEXT,
        "evidence_identity": prior["evidence_identity"],
        "evidence_workspace_path": prior["evidence_workspace_path"],
        "evidence_file_sha256": prior["evidence_file_sha256"],
        "original_package_sha256": sha(ORIGINAL / "package-freeze.json"),
        "original_authorization_sha256": sha(ORIGINAL / "authorization.json"),
        "original_assessment_sha256": sha(ORIGINAL / "assessment-v1/receipt.json"),
        "original_terminal": "bounded_M4_abstention_local_contract_limit",
        "prior_history_sha256": digest(request["messages"]),
        "first_request_sha256": sha(prepared / "first-request.json"),
        "first_request_bytes": len(canonical(request)),
        "prompt_tools_inference_hash": prior["prompt_tools_inference_hash"],
        "prompt_tools_inference_unchanged": True,
        "tool_feedback_unchanged_no_truncation": True,
        "prior_requests_retained": assessment["requests"],
        "prior_tool_calls": 4,
        "remaining_tool_calls": 8,
        "prior_candidate_submissions": 0,
        "remaining_candidate_submissions": 9,
        "scope": prior["scope"],
        "model_config": prior["model_config"],
        "new_paid_requests": 0,
        "new_count_requests": 0,
        "provider_authorized": False,
        "token_counting": "At most one free count_tokens POST per remaining Messages ordinal; "
        "same frozen input payload and unchanged signed blocks. Reject over900000 estimated "
        "input tokens before reserving money. This is a conservative estimate gate, not a "
        "guaranteed provider token bound. Full-model financial reservations remain unchanged.",
        "migration": "Fork verified campaign snapshot, retain both charge IDs/settlements and "
        "all four tool receipts/transcript. Clear only documented terminal/contract in the fork; "
        "original terminal episode remains byte-identical.",
    }
    write(prepared / "continuation-contract.json", contract)
    write(
        prepared / "approval-specification.json",
        {
            "status": "pending_user_approval_not_dispatchable",
            "model": prior["model"],
            "contract_sha256": sha(prepared / "continuation-contract.json"),
            "first_request_sha256": contract["first_request_sha256"],
            "evidence_hash": prior["evidence_identity"],
            "max_requests": 6,
            "remaining_requests": 4,
            "max_count_tokens_requests": 4,
            "max_output_tokens": 6000,
            "ceiling_usd": "15",
            "prior_spend_usd": str(PRIOR_SPEND),
            "count_tokens_endpoint": contract["count_tokens_endpoint"],
            "user_approval_record": None,
        },
    )
    verify_origin()
    print(
        json.dumps(
            {
                "status": contract["status"],
                "first_request_bytes": contract["first_request_bytes"],
                "first_request_sha256": contract["first_request_sha256"],
                "maximum_cumulative_commitment_usd": CONTEXT["maximum_cumulative_commitment_usd"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    prepare()
