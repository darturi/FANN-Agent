"""Positive and abstention M3 paths with actual bound evidence and scripted-only transport."""

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
DEST = STUDY / "uncertainty-shortlist-v1"
PROTOCOL = HERE.parent / "filtered-ann-protocol-v2"
sys.path.insert(0, str(PROTOCOL))
from fannproto.controller import Campaign, ProtocolError, generation_ready  # noqa: E402
from fannproto.evidence import Evidence  # noqa: E402
from fannproto.policy import FILTERS  # noqa: E402
from fannproto.rehearsal import ScriptedTransport, fixture_config, request_for  # noqa: E402

from fannagent.store import Store, canonical  # noqa: E402


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def use(identity, operation, arguments):
    return {"type": "tool_use", "id": identity, "name": operation, "input": arguments}


def run():
    output = DEST / "M3-bound-v2"
    output.mkdir(exist_ok=False)
    binding = json.loads((DEST / "binding-receipt-v2.json").read_text())
    for name, digest in binding["artifact_sha256"].items():
        assert sha(DEST / name) == digest
    for path, digest in binding["source_sha256"].items():
        assert sha(ROOT / path) == digest
    evidence = Evidence(json.loads((DEST / "bound-evidence.json").read_text()))
    gates = json.loads((DEST / "bound-gates.json").read_text())
    generation_ready(evidence, gates)
    assert not evidence.fixture and evidence.identity == binding["evidence_identity"]
    programs = json.loads(
        (STUDY / "kits/m1-runtime-qualification-v2/compiled-programs.json").read_text()
    )["bindings"]
    policies = {e["arm"]: e["policy"] for e in programs}
    store = Store(output / "positive-bound-campaign", create=True)
    campaign = Campaign(store, fixture_config(), evidence, gates)
    transport = ScriptedTransport(
        [
            [use("inspect", "inspect_workload", {})],
            [
                use(
                    "evaluate",
                    "evaluate_candidates",
                    {"policies": [policies[20], policies[21], policies[22]]},
                )
            ],
            [
                {
                    "type": "text",
                    "text": "Freeze the scripted qualification nominees.\n```json\n{}\n```",
                }
            ],
        ]
    )
    requests = []
    outcomes = []
    for _ in range(3):
        request = request_for(campaign)
        requests.append(len(canonical(request)))
        outcomes.append(campaign.round(request, transport))
    state = store.get("v2_state")
    assert state["terminal"] == "finalists_frozen_pending_live_measurement"
    assert set(outcomes[-1]["candidate_ids"]) == {"candidate-1", "candidate-2", "candidate-3"}
    assert outcomes[-1]["selection_decision"]["conditional_regret_bound"] == 0
    assert state["tool_calls"] == state["candidate_submissions"] == 3
    assert len(transport.requests) == 3 and not store.get("v2_round_pending")
    budget = campaign.budget.summary()
    assert len(budget["calls"]) == 3 and all(c["status"] == "settled" for c in budget["calls"])
    # Actual bound evidence with a semantics-equivalent fourth policy; no threshold fitting.
    ambiguous = Campaign(
        Store(output / "ambiguous-bound-campaign", create=True), fixture_config(), evidence, gates
    )
    repeated = deepcopy(policies[20])
    repeated["name"] = "scripted_redundant_comparison_semantic_test"
    repeated["rationale"] = "M3 diagnostic only: repeat an unchanged comparison; no new threshold."
    for clauses in repeated["rules"].values():
        for clause in clauses:
            clause["conditions"].append(deepcopy(clause["conditions"][0]))
    first = ambiguous.dispatch(
        "first", "evaluate_candidates", {"policies": [policies[20], policies[21], policies[22]]}
    )
    fourth = ambiguous.dispatch("fourth", "evaluate_candidates", {"policies": [repeated]})
    assert all(
        v["evaluation"]["quality_preserves_raw_native640"]
        for v in first["evaluations"] + fourth["evaluations"]
    )
    assert (
        fourth["evaluations"][0]["cost_estimate"]["status"]
        == "supported_uncertainty_shortlist_proxy"
    )
    assert ambiguous.shortlist_decision()["status"] == "abstain_uncertainty_exceeds_cap"
    abstention = ambiguous.dispatch("finish", "submit_or_abstain", {})
    assert abstention["status"] == "abstained"
    assert ambiguous.store.get("v2_state")["terminal"] == "uncertainty_shortlist_abstention"
    try:
        ambiguous.dispatch("after", "inspect_workload", {})
    except ProtocolError as error:
        assert "terminal" in str(error)
    else:
        raise AssertionError("abstaining campaign continued")
    diagnostic = Campaign(
        Store(output / "diagnostic-bound-campaign", create=True), fixture_config(), evidence, gates
    )
    for category in ("qualified_partial_prefix", "preserving_partial_prefix", "zero_prefix"):
        result = diagnostic.dispatch(
            category, "explain_cases", {"category": category, "filter": "votes743", "limit": 3}
        )
        assert 1 <= len(result["cases"]) <= 3
        assert all("source_id" not in case and "vector" not in case for case in result["cases"])
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
    batch = {"policies": [policies[22], {}, policies[22]]}
    first = diagnostic.dispatch("duplicates", "evaluate_candidates", batch)
    assert "rejected" in first["evaluations"][1]
    assert diagnostic.dispatch("duplicates", "evaluate_candidates", batch) == first
    assert diagnostic.store.get("v2_state")["candidate_submissions"] == 3
    second = diagnostic.dispatch(
        "probes", "evaluate_candidates", {"policies": [policies[45], policies[46], unsupported]}
    )
    assert [v["evaluation"]["recall_losses"] for v in second["evaluations"]] == [200, 43, 0]
    assert second["evaluations"][2]["cost_estimate"]["status"] == "unsupported_uncertainty_estimate"
    assert all(
        len(cases) <= 3
        for v in second["evaluations"]
        for cases in v["evaluation"]["counterexamples"].values()
    )
    assert set(first["evaluations"][0]["work_estimate"]["per_filter_means"]) == set(FILTERS)
    assert "error" in diagnostic.dispatch("SQL", "SQL", {})
    resumed = Campaign(diagnostic.store, fixture_config(), evidence, gates)
    assert resumed.store.get("v2_state") == diagnostic.store.get("v2_state")
    try:
        Campaign(diagnostic.store, fixture_config(), evidence, {**gates, "tampered": True})
    except ProtocolError as error:
        assert "resume cannot change" in str(error)
    else:
        raise AssertionError("tampered gate accepted")
    diagnostic.dispatch("abstain", "submit_or_abstain", {"abstain": True})
    native = Campaign(
        Store(output / "native-bound-campaign", create=True), fixture_config(), evidence, gates
    )
    native.dispatch("native", "evaluate_candidates", {"policies": [policies[43]]})
    native_result = native.dispatch("finish", "submit_or_abstain", {})
    assert native_result["selection_decision"]["status"] == "certified_native_abstention"
    cap = Campaign(
        Store(output / "cap-bound-campaign", create=True), fixture_config(), evidence, gates
    )
    for index in range(12):
        cap.dispatch(str(index), "inspect_workload", {})
    try:
        cap.dispatch("overflow", "inspect_workload", {})
    except ProtocolError as error:
        assert "tool limit" in str(error)
    else:
        raise AssertionError("tool quota ignored")
    paid = Campaign(
        Store(output / "unauthorized-provider-bound-campaign", create=True),
        fixture_config(model="unapproved-paid-model"),
        evidence,
        gates,
    )
    blocked = ScriptedTransport([])
    try:
        paid.round(request_for(paid), blocked)
    except ProtocolError as error:
        assert "provider authorization" in str(error)
    else:
        raise AssertionError("unapproved provider transport reached")
    assert not blocked.requests and not paid.budget.summary()["calls"]
    result = {
        "schema": "filtered-ann.uncertainty-M3-rehearsal.v1",
        "date": "2026-11-16",
        "status": "passed_actual_bound_positive_interval_selection_and_abstention_paths",
        "evidence_identity": evidence.identity,
        "binding_receipt_sha256": sha(DEST / "binding-receipt-v2.json"),
        "positive_main": {
            "scripted_requests": 3,
            "tools": 3,
            "submitted_known_policies": 3,
            "nominee_ids": outcomes[-1]["candidate_ids"],
            "selection_decision": outcomes[-1]["selection_decision"],
            "request_bytes": requests,
            "synthetic_accounting_usd": budget["committed_usd"],
        },
        "ambiguous_four_policy_pool": abstention,
        "native_abstention": native_result,
        "checks": [
            "actual_450_group_evidence",
            "all_seven_conditions",
            "unchanged_known_transfer_replay",
            "positive_scripted_round_and_usage_settlement",
            "conditional_certificate",
            "four_way_ambiguous_terminal_abstention",
            "native_abstention",
            "partial_and_zero_examples",
            "invalid_duplicate_idempotence",
            "unsupported_cost_retains_quality_work",
            "200_and43_loss_probes",
            "bounded_counterexamples",
            "scope_quota_and_resume",
            "tampered_resume_rejected",
            "unapproved_paid_transport_and_budget_blocked",
        ],
        "all_five_folds_exposed": True,
        "point_model_precision_qualified": False,
        "scripted_nominees_only_not_new_agent_discovery": True,
        "provider_authorized": False,
        "external_provider_requests": 0,
        "actual_API_spend_usd": "0",
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [HERE / "rehearse.py", *sorted((PROTOCOL / "fannproto").glob("*.py"))]
        },
    }
    result["artifacts"] = {
        str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()
    }
    write(output / "receipt.json", result)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("artifacts", "source_sha256")}, indent=2
        )
    )


if __name__ == "__main__":
    run()
