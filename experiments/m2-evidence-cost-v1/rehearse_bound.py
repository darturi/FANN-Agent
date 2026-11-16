"""M3 on actual bound evidence: useful offline tools, unsupported costs blocked, abstention."""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
DEST = STUDY / "evidence-m2-v1"
PROTOCOL = HERE.parent / "filtered-ann-protocol-v2"
sys.path.insert(0, str(PROTOCOL))
from fannproto.controller import Campaign, ProtocolError  # noqa: E402
from fannproto.evidence import Evidence  # noqa: E402
from fannproto.policy import FILTERS  # noqa: E402
from fannproto.rehearsal import ScriptedTransport, fixture_config, request_for  # noqa: E402

from fannagent.store import Store, canonical  # noqa: E402


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def run():
    output = DEST / "M3-bound"
    output.mkdir(exist_ok=False)
    binding = json.loads((DEST / "binding-receipt.json").read_text())
    for name, digest in binding["artifact_sha256"].items():
        assert sha(DEST / name) == digest
    for name, digest in binding["source_sha256"].items():
        assert sha(ROOT / name) == digest
    evidence = Evidence(json.loads((DEST / "bound-evidence.json").read_text()))
    assert not evidence.fixture and evidence.identity == binding["evidence_identity"]
    gates = json.loads((DEST / "bound-gates.json").read_text())
    store = Store(output / "actual-bound-campaign", create=True)
    campaign = Campaign(store, fixture_config(), evidence, gates)
    inspect = campaign.dispatch("inspect", "inspect_workload", {})
    assert set(inspect["per_filter"]) == set(FILTERS)
    assert inspect["cost_ranking_enabled"] is False and "prefix_opportunity" in inspect
    assert len(canonical(inspect)) < 24000
    for category in ("qualified_partial_prefix", "preserving_partial_prefix", "zero_prefix"):
        r = campaign.dispatch(
            category, "explain_cases", {"category": category, "filter": "votes743", "limit": 3}
        )
        assert 1 <= len(r["cases"]) <= 3
        assert all(
            set(case)
            == {
                "group",
                "fold",
                "filter",
                "native_recall",
                "native_count",
                "observations",
                "proofs",
            }
            for case in r["cases"]
        )
    programs = json.loads(
        (STUDY / "kits/m1-runtime-qualification-v2/compiled-programs.json").read_text()
    )["bindings"]
    by_arm = {r["arm"]: r["policy"] for r in programs}
    broad, partial, distance, native = (by_arm[a] for a in (22, 45, 46, 43))
    original = {"policies": [broad, {}, broad]}
    first = campaign.dispatch("batch1", "evaluate_candidates", original)
    assert first["evaluations"][0]["evaluation"]["quality_preserves_raw_native640"]
    assert "rejected" in first["evaluations"][1]
    assert first["evaluations"][0]["rule_hash"] == first["evaluations"][2]["rule_hash"]
    assert all(first["evaluations"][i]["cost_estimate"] is None for i in (0, 2))
    assert campaign.dispatch("batch1", "evaluate_candidates", original) == first
    assert campaign.store.get("v2_state")["candidate_submissions"] == 3
    second = campaign.dispatch(
        "batch2", "evaluate_candidates", {"policies": [partial, distance, native]}
    )
    assert [e["evaluation"]["recall_losses"] for e in second["evaluations"]] == [200, 43, 0]
    assert all(e["evaluation"]["unqualified_stops"] == 0 for e in second["evaluations"])
    assert all(
        len(cases) <= 3
        for e in second["evaluations"]
        for cases in e["evaluation"]["counterexamples"].values()
    )
    assert set(first["evaluations"][0]["work_estimate"]["per_filter_means"]) == set(FILTERS)
    assert not campaign.shortlist(), "no unsupported surrogate may shortlist even a quality pass"
    compared = campaign.dispatch(
        "compare",
        "compare_candidates",
        {"candidate_ids": ["candidate-1", "candidate-4", "candidate-6"]},
    )
    assert len(compared["candidates"]) == 3
    assert "error" in campaign.dispatch("SQL", "SQL", {})
    assert not store.get("v2_round_pending")
    transport = ScriptedTransport([])
    try:
        campaign.round(request_for(campaign), transport)
    except ProtocolError as error:
        assert "M2 cost models failed" in str(error)
        blocked_reason = str(error)
    else:
        raise AssertionError("cost failure unexpectedly allowed a model request")
    assert not transport.requests and not campaign.budget.summary()["calls"]
    resumed = Campaign(store, fixture_config(), evidence, gates)
    assert resumed.store.get("v2_state") == campaign.store.get("v2_state")
    try:
        Campaign(store, fixture_config(), evidence, {**gates, "tampered": True})
    except ProtocolError as error:
        assert "resume cannot change" in str(error)
    else:
        raise AssertionError("changed bound gates accepted on resume")
    abstain = resumed.dispatch(
        "finish",
        "submit_or_abstain",
        {
            "abstain": True,
            "notes": "M3 scripted bound-evidence rehearsal: M2 cost qualification failed; "
            "no cost-ranked finalists.",
        },
    )
    assert abstain["status"] == "abstained"
    try:
        resumed.dispatch("after-terminal", "inspect_workload", {})
    except ProtocolError as error:
        assert "terminal" in str(error)
    else:
        raise AssertionError("terminal bound campaign continued")
    state = resumed.store.get("v2_state")
    assert state["candidate_submissions"] == 6 and state["tool_calls"] == 9
    # Separate bound-data quota scenario; no resetting the main campaign/episode.
    cap = Campaign(
        Store(output / "actual-bound-cap-scenario", create=True), fixture_config(), evidence, gates
    )
    for i in range(12):
        cap.dispatch(str(i), "inspect_workload", {})
    try:
        cap.dispatch("overflow", "inspect_workload", {})
    except ProtocolError as error:
        assert "tool limit" in str(error)
    else:
        raise AssertionError("bound tool quota not enforced")
    assert cap.store.get("v2_state")["tool_calls"] == 12
    receipt = {
        "schema": "filtered-ann.M3-bound-evidence-rehearsal.v1",
        "status": "passed_actual_bound_evidence_negative_cost_gate_and_abstention",
        "evidence_identity": evidence.identity,
        "evidence_sha256": sha(DEST / "bound-evidence.json"),
        "binding_receipt_sha256": sha(DEST / "binding-receipt.json"),
        "gates_sha256": sha(DEST / "bound-gates.json"),
        "main_campaign": {
            "tools": 9,
            "candidate_submissions_including_invalid_duplicate": 6,
            "quality_loss_examples": [200, 43],
            "finalists": [],
            "terminal": state["terminal"],
            "model_transport_invocations": 0,
        },
        "separate_bound_tool_cap_scenario": {"tools": 12, "overflow_rejected": True},
        "checks": [
            "all_seven_conditions",
            "complete_partial_zero_and_preserving_examples",
            "exact_full_precision_quality_replay",
            "bounded_counterexamples",
            "compiled_artifact_and_work_feedback",
            "invalid_duplicate_slots",
            "idempotent_delivery",
            "no_unknown_SQL_capability",
            "contract_preserving_resume",
            "tampered_resume_rejected",
            "cost_gate_before_transport_and_budget",
            "empty_cost_shortlist",
            "explicit_abstention_and_terminal",
            "real_bound_tool_quota",
        ],
        "blocked_reason": blocked_reason,
        "positive_fixture_tests_separate": True,
        "generation_ready": False,
        "cost_ranking_enabled": False,
        "external_provider_requests": 0,
        "actual_api_spend_usd": "0",
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [HERE / "rehearse_bound.py", *sorted((PROTOCOL / "fannproto").glob("*.py"))]
        },
    }
    receipt["artifacts"] = {
        str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()
    }
    write(output / "receipt.json", receipt)
    print(
        json.dumps(
            {k: v for k, v in receipt.items() if k not in ("artifacts", "source_sha256")}, indent=2
        )
    )


if __name__ == "__main__":
    run()
