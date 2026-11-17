"""Prepare a reviewable M4 request and strict spending contract; never dispatch generation."""

import hashlib
import json
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
DEST = STUDY / "m4-episode-v1"
BOUND = STUDY / "uncertainty-shortlist-v1"
PROTOCOL = HERE.parent / "filtered-ann-protocol-v2"
sys.path.insert(0, str(PROTOCOL))

from fannproto.controller import generation_ready  # noqa: E402
from fannproto.evidence import Evidence  # noqa: E402
from fannproto.toolspec import SYSTEM, TOOLS  # noqa: E402

from fannagent.config import ModelConfig  # noqa: E402
from fannagent.store import canonical, digest  # noqa: E402

MODEL = "claude-sonnet-5-5"
PARAMETERS = {
    "model": MODEL,
    "max_tokens": 6000,
    "inference_geo": "global",
    "service_tier": "standard_only",
    "thinking": {"type": "between_tools"},
    "output_config": {"effort": "high"},
}


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def make_request(campaign, prepared):
    initial = json.loads((prepared / "first-request.json").read_text())
    return {**initial, "messages": campaign.store.get("v2_messages") or initial["messages"]}


def prepare():
    prepared = DEST / "prepared"
    prepared.mkdir(exist_ok=False)
    provider = json.loads((DEST / "provider/preflight.json").read_text())
    assert provider["status"] == "official_prices_and_account_model_GET_verified"
    assert provider["model"] == MODEL and provider["billing_input_token_bound"] == 1000000
    assert provider["input_usd_per_million"] == "2" and provider["output_usd_per_million"] == "10"
    for record in provider["official_documents"].values():
        label = next(k for k, v in provider["official_documents"].items() if v == record)
        assert sha(DEST / "provider" / (label + ".md")) == record["sha256"]
    assert sha(DEST / "provider/model-api-response.json") == provider["model_response_sha256"]
    pricing = (DEST / "provider/pricing.md").read_text()
    assert "standard pricing" in pricing and "900k" in pricing and "9k" in pricing
    evidence_path = BOUND / "bound-evidence.json"
    evidence = Evidence(json.loads(evidence_path.read_text()))
    frozen = json.loads((STUDY / "freeze/uncertainty-shortlist-v1.json").read_text())
    assert frozen["bound_evidence_sha256"] == sha(evidence_path)
    assert frozen["bound_evidence_identity"] == evidence.identity
    assert frozen["active_M3_receipt_sha256"] == sha(BOUND / "M3-bound-v2/receipt.json")
    m3 = json.loads((BOUND / "M3-bound-v2/receipt.json").read_text())
    assert m3["status"] == "passed_actual_bound_positive_interval_selection_and_abstention_paths"
    gates = deepcopy(
        json.loads(
            (STUDY / "reports/protocol-v2-gates-after-uncertainty-shortlist-v1.json").read_text()
        )
    )
    generation_ready(evidence, gates)
    assert gates["M3"]["evidence_hash"] == evidence.identity and not gates["provider_authorized"]
    model = ModelConfig(
        model=MODEL,
        ceiling_usd=Decimal("15"),
        allowance_usd=Decimal("0"),
        input_usd_per_million=Decimal("2"),
        output_usd_per_million=Decimal("10"),
        input_token_bound=1000000,
        output_token_limit=6000,
        bound_verified=True,
        max_attempts=1,
        pricing_revision="anthropic-sonnet-5-5-global-standard-2026-11-16",
    )
    maximum = (Decimal(model.input_token_bound) * 2 + Decimal(6000) * 10) / 1000000
    assert maximum == Decimal("2.06") and maximum * 6 <= model.ceiling_usd
    execution = {
        "schema": "filtered-ann.M4-execution.v1",
        "request_byte_bound": 50000,
        "reserved_protocol_headroom_bytes": 8192,
        "max_requests": 6,
        "max_output_tokens": 6000,
        "billing_input_token_bound": 1000000,
        "maximum_reserved_usd_per_request": str(maximum),
        "six_maximal_requests_usd": str(maximum * 6),
        "ceiling_usd": "15",
        "allowance_usd": "0",
        "automatic_retries": False,
        "thinking_progress_preserved": True,
    }
    gates["execution_contract"] = execution
    gates["provider_authorization"] = "pending_explicit_user_approval"
    full_summary = evidence.summary()
    guidance = evidence.bundle["cost_guidance"]
    summary = {
        "scope": "450 exposed development groups; all five folds are diagnostics",
        "per_filter": {
            f: {
                "queries": value["queries"],
                "native_mean_recall": value["native_mean_recall"],
                "short_native": value["short_native"],
                **evidence.bundle["development_prefix_summary"][f],
            }
            for f, value in full_summary["per_filter"].items()
        },
        "uncertainty_contract": full_summary["shortlist_contract"],
        "native_primary_ms_range_across_blocks": guidance["native_primary_ms_range_across_blocks"],
        "paired_complete_plan_differences": {
            name: {
                k: value[k]
                for k in ("mean_complete_request_difference_ms", "conditional95pct_interval_ms")
            }
            for name, value in guidance["paired_complete_plan_differences"].items()
        },
        "interpretation": "All prefix outcomes are actual offline labels. Preserving/lossy "
        "counts are oracle diagnostics, not separating rules. Plan differences are contextual "
        "complete-request measurements, not pure additive operation prices. Engineering "
        "envelopes do not guarantee future predictive coverage or measured new-policy speed.",
    }
    initial = {
        "episode": "M4 fresh bounded policy discovery, version1",
        "instruction": "Choose your own causal hypotheses, features and thresholds. Use bounded "
        "inspection/evaluation feedback, preserve raw-native recall on every development case "
        "and retain all six scalar conditions. The compact orientation is already supplied; "
        "avoid redundant full inspection. Prefer bounded cases and concise speculative batches, "
        "then conclude via submit_or_abstain before request/tool/context capacity ends. "
        "Six requests and nine submissions are upper limits, not targets. No prior policy is "
        "supplied as a seed.",
        "primer": (BOUND / "primer.md")
        .read_text()
        .replace(
            "No validation/test access or external provider episode is authorized by this binding.",
            "No validation/test access. External episode authorization is enforced by the host.",
        ),
        "development_summary": summary,
        "limits": {
            "Messages_requests": 6,
            "total_USD": 15,
            "domain_tools": 12,
            "candidate_submissions": 9,
            "policies_per_batch": 3,
            "M5_nominees": 3,
        },
    }
    system = SYSTEM + "\nThis is the real M4 development episode after uncertainty qualification. "
    system += "Point-model precision remains failed; supported engineering envelopes can still "
    system += "qualify conditional M5 experiment nomination. No live speedup is implied. "
    system += "Keep hypotheses/rationales concise and cite the available evidence. "
    system += "Stop before quota/context exhaustion; exhaustion without final submission is "
    system += "recorded as abstention with no extra rescue request.\n"
    request = {
        **PARAMETERS,
        "system": system,
        "tools": deepcopy(TOOLS),
        "messages": [{"role": "user", "content": canonical(initial).decode()}],
    }
    payload = canonical(request)
    assert len(payload) + 8192 <= 50000
    assert len(evidence.rows) == 3150 and all(
        set(r["proofs"]) == set(r["observations"]) for r in evidence.rows
    )
    (prepared / "first-request.json").write_bytes(payload)
    write(prepared / "first-request.preview.json", request)
    (prepared / "system-prompt.md").write_text(system)
    (prepared / "initial-user-message.json").write_text(
        json.dumps(initial, sort_keys=True, indent=2) + "\n"
    )
    write(prepared / "tools.json", TOOLS)
    write(prepared / "model-config.json", model.model_dump(mode="json"))
    write(prepared / "bound-gates.json", gates)
    write(prepared / "execution-contract.json", execution)
    write(prepared / "development-summary.json", summary)
    contract = {
        "schema": "filtered-ann.M4-proposal.v1",
        "date": "2026-11-16",
        "status": "prepared_pending_explicit_user_approval",
        "model": MODEL,
        "endpoint": "https://api.anthropic.com/v1/messages",
        "api_version": "2023-06-01",
        "evidence_identity": evidence.identity,
        "evidence_file_sha256": sha(evidence_path),
        "evidence_workspace_path": str(evidence_path.relative_to(ROOT)),
        "model_config": model.model_dump(mode="json"),
        "limits": execution,
        "research_limits": {
            "tools": 12,
            "submissions": 9,
            "batch_size": 3,
            "case_limit": 12,
            "live_nominees": 3,
        },
        "request_fields": PARAMETERS,
        "first_request_bytes": len(payload),
        "first_request_sha256": sha(prepared / "first-request.json"),
        "prompt_tools_inference_hash": digest(
            {
                k: request[k]
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
        "provider_preflight_sha256": sha(DEST / "provider/preflight.json"),
        "qualified_uncertainty_outcome_sha256": sha(STUDY / "freeze/uncertainty-shortlist-v1.json"),
        "approval_required": True,
        "provider_authorized": False,
        "paid_requests": 0,
        "payload_egress": "Compact anonymized development summaries and bounded case/recall/"
        "feature/work/cost feedback only. No source IDs, vectors, neighbors, credentials "
        "or holdouts.",
        "scope": {
            "development_groups": 450,
            "scalar_filters": 6,
            "unfiltered": True,
            "exact_scoring_only": True,
            "validation_test_outcomes_opened": False,
        },
        "files_sha256": {p.name: sha(p) for p in sorted(prepared.iterdir()) if p.is_file()},
    }
    write(prepared / "episode-contract.json", contract)
    approval = {
        "status": "pending_user_approval_not_dispatchable",
        "model": MODEL,
        "endpoint": contract["endpoint"],
        "evidence_hash": evidence.identity,
        "max_requests": 6,
        "max_output_tokens": 6000,
        "ceiling_usd": "15",
        "episode_contract_sha256": sha(prepared / "episode-contract.json"),
        "first_request_sha256": contract["first_request_sha256"],
        "prompt_tools_inference_hash": contract["prompt_tools_inference_hash"],
        "user_approval_record": None,
        "requested_authority": "Send the frozen compact development payload and allowed "
        "follow-up feedback to Anthropic Messages using the pinned contract, at most six "
        "requests/$15 total, without validation/test access or automatic retry.",
    }
    write(prepared / "approval-specification.json", approval)
    print(
        json.dumps(
            {
                "status": contract["status"],
                "first_request_bytes": len(payload),
                "first_request_sha256": contract["first_request_sha256"],
                "max_requests": 6,
                "hard_cap_usd": "15",
                "maximum_six_request_reservations_usd": str(maximum * 6),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    prepare()
