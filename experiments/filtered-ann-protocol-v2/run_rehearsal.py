"""Exercise a complete scripted campaign; never load credentials or call a provider."""

import argparse
import hashlib
import json
from pathlib import Path

from fannproto.controller import Campaign, ProtocolError, generation_ready
from fannproto.evidence import Evidence
from fannproto.rehearsal import (
    ScriptedTransport,
    fixture_config,
    fixture_evidence,
    fixture_gates,
    fixture_policy,
    request_for,
)

from fannagent.store import Store


def run(output, evidence_path=None):
    output.mkdir(parents=True, exist_ok=False)
    evidence = fixture_evidence()
    campaign = Campaign(
        Store(output / "scripted-campaign", create=True),
        fixture_config(),
        evidence,
        fixture_gates(evidence),
    )
    policy = fixture_policy()
    transport = ScriptedTransport(
        [
            [{"type": "tool_use", "id": "inspect", "name": "inspect_workload", "input": {}}],
            [
                {
                    "type": "tool_use",
                    "id": "evaluate",
                    "name": "evaluate_candidates",
                    "input": {"policies": [policy, {}, policy]},
                }
            ],
            [{"type": "text", "text": "Freeze the fixture.\n```json\n{}\n```"}],
        ]
    )
    outcomes = [campaign.round(request_for(campaign), transport) for _ in range(3)]
    state = campaign.store.get("v2_state")
    budget = campaign.budget.summary()
    assert state["terminal"] == "finalists_frozen_pending_live_measurement"
    assert outcomes[-1]["candidate_ids"] == ["candidate-1"]
    assert state["candidate_submissions"] == 3 and state["tool_calls"] == 3
    assert len(budget["calls"]) == 3 and all(c["status"] == "settled" for c in budget["calls"])
    assert campaign.store.get("v2_round_pending") is None
    receipt = {
        "schema": "filtered-ann-controller-rehearsal.v2",
        "status": "passed_scripted_only",
        "runtime_profile": evidence.bundle["runtime_profile"],
        "fixture_evidence_hash": evidence.identity,
        "external_provider_requests": 0,
        "actual_api_spend_usd": "0",
        "synthetic_accounting_usd": budget["committed_usd"],
        "scripted_response_count": 3,
        "tools": state["tool_calls"],
        "candidate_submissions_including_invalid_duplicate": state["candidate_submissions"],
        "finalists": outcomes[-1]["candidate_ids"],
        "terminal": state["terminal"],
        "limits": "Synthetic labels, costs and rate card. No study performance or qualification.",
        "holdout_access": False,
    }
    if evidence_path is not None:
        actual = Evidence(json.loads(evidence_path.read_text()))
        try:
            generation_ready(actual, {})
        except ProtocolError as error:
            receipt["real_generation_preflight"] = {
                "status": "blocked_as_required",
                "first_gate": str(error),
                "evidence_hash": actual.identity,
                "development_rows": len(actual.rows),
                "known_prefix_labels": sum(len(r["proofs"]) for r in actual.rows),
                "missing_reached_prefix_labels": sum(
                    len(r["observations"]) - len(r["proofs"]) for r in actual.rows
                ),
                "cost_status": actual.bundle["cost_status"],
            }
        else:
            raise AssertionError("Missing original-graph receipts unexpectedly allowed generation")
    receipt["artifacts"] = {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob("*"))
        if p.is_file()
    }
    (output / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    result = run(args.output, args.evidence)
    print(json.dumps({k: v for k, v in result.items() if k != "artifacts"}, indent=2))
