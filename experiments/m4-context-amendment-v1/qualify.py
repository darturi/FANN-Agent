"""No-network capacity checks using actual development evidence and retained debt."""

import json
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from common import (
    CONTEXT,
    DEST,
    PRIOR_SPEND,
    STUDY,
    ApprovalRequired,
    canonical,
    check_request,
    count_payload,
    request_for,
    seed_campaign,
    tool_block,
    verify_origin,
    write,
)
from fannproto.controller import ProtocolError
from fannproto.policy import FILTERS
from run_continuation import run


def use(identity, operation, arguments):
    return {"type": "tool_use", "id": identity, "name": operation, "input": arguments}


class Script:
    automatic_retries = False

    def __init__(self, blocks, *, maximal_usage=False):
        self.blocks = iter(blocks)
        self.requests = []
        self.maximal_usage = maximal_usage

    def __call__(self, request):
        self.requests.append(deepcopy(request))
        return {
            "model": "scripted",
            "usage": {
                "input_tokens": 1000000 if self.maximal_usage else 100,
                "output_tokens": 6000 if self.maximal_usage else 20,
            },
            "content": next(self.blocks),
        }


def qualify():
    output = DEST / "qualification-v1"
    output.mkdir(exist_ok=False)
    verify_origin()
    first = request_for()
    check_request(first)
    assert len(canonical(first)) == 42382
    assert len(canonical(first)) + 8192 == 50574
    assert count_payload(first)["messages"] == first["messages"]
    contract = json.loads((DEST / "prepared/continuation-contract.json").read_text())
    assert contract["context"] == CONTEXT
    gates = {"status": "simulation_only_not_provider_authorization"}
    sizes = []
    with patch(
        "socket.create_connection", side_effect=AssertionError("no network in qualification")
    ):
        try:
            run(DEST / "authorization.json")
        except ApprovalRequired:
            pass
        else:
            raise AssertionError("pending amendment reached dispatch")
        assert not (DEST / "live-continuation").exists()
        campaign = seed_campaign(output / "full-legal-tool-sequence", gates, simulation=True)
        programs = json.loads(
            (STUDY / "kits/m1-runtime-qualification-v2/compiled-programs.json").read_text()
        )["bindings"]
        policies = {p["arm"]: p["policy"] for p in programs}
        unsupported = deepcopy(policies[43])
        unsupported["rules"] = {
            "votes743": [
                {
                    "cp": 16,
                    "conditions": [["qualifying_count", ">=", 0]] * 3
                    + [["qualifying_count", ">=", 247286]],
                }
            ]
        }
        blocks = [
            [
                use(
                    "eval-a",
                    "evaluate_candidates",
                    {"policies": [policies[20], policies[21], policies[22]]},
                ),
                use(
                    "eval-b",
                    "evaluate_candidates",
                    {"policies": [policies[45], policies[46], policies[43]]},
                ),
                use("eval-c", "evaluate_candidates", {"policies": [{}, policies[20], unsupported]}),
            ],
            [
                use(
                    "compare-all",
                    "compare_candidates",
                    {"candidate_ids": [f"candidate-{n}" for n in range(1, 10)]},
                ),
                use(
                    "cases-max",
                    "explain_cases",
                    {"category": "qualified_full_prefix", "filter": "unfiltered", "limit": 12},
                ),
                use("inspect-again", "inspect_workload", {}),
            ],
            [
                use(
                    "compare-again",
                    "compare_candidates",
                    {"candidate_ids": [f"candidate-{n}" for n in range(1, 10)]},
                )
            ],
            [{"type": "text", "text": "{}"}],
        ]
        transport = Script(blocks)
        for _ in range(4):
            request = request_for(campaign, simulation=True)
            sizes.append(len(canonical(request)))
            assert sizes[-1] + 8192 <= CONTEXT["request_byte_bound"]
            campaign.round(request, transport)
        state = campaign.store.get("v2_state")
        assert state["tool_calls"] == campaign.store.get("m4_context_result_slots") == 12
        assert state["candidate_submissions"] == 9
        assert state["terminal"] == "finalists_frozen_pending_live_measurement"
        assert campaign.shortlist() == ["candidate-1", "candidate-2", "candidate-3"]
        assert len(campaign.budget.summary()["calls"]) == 6
        assert Decimal(campaign.budget.summary()["committed_usd"]) == PRIOR_SPEND + Decimal(
            "0.0016"
        )
        try:
            campaign.round(request_for(campaign, simulation=True), transport)
        except ProtocolError:
            pass
        else:
            raise AssertionError("terminal seventh request allowed")

        # Every advertised category/filter at max12, not just the known discovery path.
        categories = (
            "short_native",
            "qualified_full_prefix",
            "missing_partial_prefix",
            "qualified_partial_prefix",
            "preserving_partial_prefix",
            "zero_prefix",
            "lossy_prefix",
        )
        cases = []
        for f in FILTERS:
            for category in categories:
                value = {"cases": campaign.evidence.examples(category, f, 12)}
                size = len(canonical(tool_block("x" * 100, value)))
                assert size <= CONTEXT["tool_result_block_bytes"]
                cases.append(
                    {"category": category, "filter": f, "cases": len(value["cases"]), "bytes": size}
                )
        feedback = []
        for request in transport.requests:
            for message in request["messages"]:
                if isinstance(message["content"], list):
                    feedback.extend(
                        len(canonical(b)) for b in message["content"] if b["type"] == "tool_result"
                    )
        assert max(feedback) < CONTEXT["tool_result_block_bytes"]

        # Large assistant signatures and the entire remaining host envelope together.
        envelope = deepcopy(first)
        assistant = {
            "role": "assistant",
            "content": [{"type": "thinking", "thinking": "", "signature": ""}],
        }
        assistant["content"][0]["signature"] = "s" * (
            CONTEXT["assistant_message_bytes"] - len(canonical(assistant))
        )
        assert len(canonical(assistant)) == CONTEXT["assistant_message_bytes"]
        tool = tool_block("x" * 100, {"payload": ""})
        tool["content"] = canonical(
            {"payload": "z" * (CONTEXT["tool_result_block_bytes"] - len(canonical(tool)))}
        ).decode()
        assert len(canonical(tool)) == CONTEXT["tool_result_block_bytes"]
        for n in (3, 3, 2):
            envelope["messages"].extend(
                [
                    deepcopy(assistant),
                    {"role": "user", "content": [deepcopy(tool) for _ in range(n)]},
                ]
            )
        envelope_bytes = len(canonical(envelope))
        check_request(envelope)
        assert envelope_bytes + 8192 < CONTEXT["request_byte_bound"]
        # Structural upper bound includes wrapper punctuation and an additional 1KiB margin.
        upper = (
            len(canonical(first))
            + 3 * CONTEXT["assistant_message_bytes"]
            + 8 * CONTEXT["tool_result_block_bytes"]
            + 1024
            + 8192
        )
        assert envelope_bytes + 8192 <= upper < CONTEXT["request_byte_bound"]

        financial = seed_campaign(output / "maximum-financial-commitment", gates, simulation=True)
        maximum = Script([[{"type": "text", "text": "malformed final"}]] * 4, maximal_usage=True)
        for _ in range(4):
            financial.round(request_for(financial, simulation=True), maximum)
        assert len(financial.budget.summary()["calls"]) == 6
        assert Decimal(financial.budget.summary()["committed_usd"]) == Decimal("8.278798")
        try:
            financial.round(request_for(financial, simulation=True), maximum)
        except ProtocolError as error:
            assert "six paid" in str(error)
        else:
            raise AssertionError("six cumulative request limit bypassed")
    verify_origin()
    receipt = {
        "schema": "filtered-ann.M4-context-qualification.v1",
        "date": "2026-11-16",
        "status": "passed_actual_bound_transcript_migration_tool_capacity_and_cumulative_budget",
        "original_episode_unchanged": True,
        "evidence_identity": contract["evidence_identity"],
        "resumed_exact_first_request_sha256": contract["first_request_sha256"],
        "formerly_blocked_request_bytes": 42382,
        "full_four_round_request_bytes": sizes,
        "simulated_tools_cumulative": 12,
        "simulated_submissions_cumulative": 9,
        "simulated_known_nominees": campaign.shortlist(),
        "known_fixture_policies_not_new_discovery": True,
        "all_category_filter_combinations": len(cases),
        "max_cases_per_explanation": 12,
        "category_filter_sizes": cases,
        "maximum_observed_tool_result_bytes": max(feedback + [v["bytes"] for v in cases]),
        "synthetic_full_remaining_envelope_bytes": envelope_bytes,
        "structural_wire_bound_including_headroom_bytes": upper,
        "configured_wire_limit_bytes": CONTEXT["request_byte_bound"],
        "capacity_certificate": "Conditional on hard assistant/tool-result envelope and "
        "cumulative feedback-slot caps. No guarantee for oversized/malformed provider output "
        "or token-estimate failure. Count preflight protects model context independently.",
        "prior_actual_spend_retained_usd": str(PRIOR_SPEND),
        "maximum_cumulative_commitment_usd": "8.278798",
        "ceiling_usd": "15",
        "cumulative_requests": 6,
        "new_paid_requests": 0,
        "new_count_requests": 0,
        "actual_new_API_spend_usd": "0",
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
        "pending_approval_blocks_before_live_state_and_network": True,
    }
    write(output / "receipt.json", receipt)
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "full_four_round_request_bytes",
                    "maximum_observed_tool_result_bytes",
                    "structural_wire_bound_including_headroom_bytes",
                    "configured_wire_limit_bytes",
                    "maximum_cumulative_commitment_usd",
                    "new_paid_requests",
                    "new_count_requests",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    qualify()
