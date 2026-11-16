from copy import deepcopy

import pytest
from fannproto.controller import Campaign, ProtocolError, generation_ready
from fannproto.evidence import Evidence
from fannproto.policy import FILTERS, PROFILE
from fannproto.rehearsal import fixture_bundle, fixture_config, fixture_gates, fixture_policy
from fannproto.uncertainty import COST_STATUS, SCHEMA

from fannagent.store import Store, digest


def bound_fixture():
    b = fixture_bundle()
    b["cost_status"] = COST_STATUS
    b["shortlist_contract"] = {
        "schema": SCHEMA,
        "status": "qualified_conditional_experiment_selection",
        "runtime_profile": PROFILE.fingerprint,
        "point_model_precision_qualified": False,
        "max_live_nominees": 3,
        "regret_limit": 0.01,
        "error_radius": 0.03,
        "qualification_receipt_sha256": "0" * 64,
        "fold_models": {
            str(fold): {f: [0.001, 0, 0, 0.0001, 0.0001] for f in FILTERS} for fold in range(5)
        },
        "supported_masks": {
            f: {str(cp): [0, 3, 8, 9, 11, 15] for cp in (16, 32, 64)} for f in FILTERS
        },
    }
    for r in b["rows"]:
        r["costs"] = {
            "reference_native_ms": 10,
            "prefix_ratio": {"full": 1, "16": 0.1},
            "search_work": {
                key: {"vector_calls": n, "layer0_queue_pops": n}
                for key, n in (("full", 100), ("16", 10))
            },
            "comparison_caps": {"16": 1},
        }
    return b


def campaign(tmp_path):
    e = Evidence(bound_fixture(), fixture=True)
    gates = fixture_gates(e)
    gates["M2"].update(
        {
            "uncertainty_shortlisting_enabled": True,
            "shortlist_contract_hash": digest(e.bundle["shortlist_contract"]),
            "shortlist_qualification_sha256": "0" * 64,
        }
    )
    return Campaign(Store(tmp_path, create=True), fixture_config(), e, gates)


def test_supported_bound_estimates_submit_with_a_conditional_certificate(tmp_path):
    c = campaign(tmp_path / "positive")
    generation_ready(c.evidence, c.gates)
    r = c.dispatch("evaluate", "evaluate_candidates", {"policies": [fixture_policy()]})
    assert r["evaluations"][0]["cost_estimate"]["point_model_precision_qualified"] is False
    final = c.dispatch("submit", "submit_or_abstain", {})
    assert final["candidate_ids"] == ["candidate-1"]
    assert final["selection_decision"]["conditional_regret_bound"] == 0
    assert final["no_performance_promotion"]


def test_ambiguous_four_program_pool_terminates_with_abstention(tmp_path):
    c = campaign(tmp_path / "ambiguous")
    policies = []
    for value in (7, 8, 9, 10):
        p = fixture_policy()
        p["rules"] = {
            f: [{"cp": 16, "conditions": [["qualifying_count", "<=", value]]}] for f in FILTERS
        }
        policies.append(p)
    c.dispatch("first", "evaluate_candidates", {"policies": policies[:3]})
    c.dispatch("second", "evaluate_candidates", {"policies": policies[3:]})
    assert c.shortlist() == []
    final = c.dispatch("finish", "submit_or_abstain", {})
    assert final["status"] == "abstained"
    assert final["selection_decision"]["status"] == "abstain_uncertainty_exceeds_cap"
    assert c.store.get("v2_state")["terminal"] == "uncertainty_shortlist_abstention"
    with pytest.raises(ProtocolError, match="terminal"):
        c.dispatch("after", "inspect_workload", {})


def test_unsupported_comparisons_keep_quality_without_nomination(tmp_path):
    c = campaign(tmp_path / "unsupported")
    p = fixture_policy()
    p["rules"] = {
        f: [
            {"cp": 16, "conditions": [["qualifying_count", ">=", 0], ["qualifying_count", ">=", 0]]}
        ]
        for f in FILTERS
    }
    r = c.dispatch("e", "evaluate_candidates", {"policies": [p]})
    assert r["evaluations"][0]["evaluation"]["quality_preserves_raw_native640"]
    assert r["evaluations"][0]["cost_estimate"]["status"] == "unsupported_uncertainty_estimate"
    assert not c.shortlist()
    assert c.dispatch("finish", "submit_or_abstain", {})["status"] == "abstained"


def test_gate_contract_hash_and_deterministic_submission_are_enforced(tmp_path):
    c = campaign(tmp_path / "contracts")
    tampered = deepcopy(c.gates)
    tampered["M2"]["shortlist_contract_hash"] = "f" * 64
    with pytest.raises(ProtocolError, match="binding"):
        generation_ready(c.evidence, tampered)
    c.dispatch("e", "evaluate_candidates", {"policies": [fixture_policy()]})
    assert "error" in c.dispatch("wrong", "submit_or_abstain", {"candidate_ids": ["candidate-2"]})
    assert c.dispatch("right", "submit_or_abstain", {})["candidate_ids"] == ["candidate-1"]


def test_agent_feedback_is_compact_while_full_registry_records_are_retained(tmp_path):
    from fannproto.controller import candidate_feedback

    c = campaign(tmp_path / "feedback")
    answer = c.dispatch("e", "evaluate_candidates", {"policies": [fixture_policy()]})
    view = answer["evaluations"][0]
    assert "compiled_artifact" not in view and "policy" not in view
    full = c.store.read(c.store.get("v2_state")["registry"]["candidate-1"], agent=True)
    assert "compiled_artifact" in full and "policy" in full
    assert "limits" in full["cost_estimate"] and "limits" not in view["cost_estimate"]
    assert (
        view["cost_estimate"]["primary_ratio_interval"]
        == full["cost_estimate"]["primary_ratio_interval"]
    )
    assert candidate_feedback(full)["evaluation"] == full["evaluation"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b["shortlist_contract"].update(error_radius=0.06),
        lambda b: b["shortlist_contract"].update(point_model_precision_qualified=True),
        lambda b: b["shortlist_contract"]["fold_models"].pop("0"),
        lambda b: b["rows"][0]["costs"].update(source_id=123),
        lambda b: b["rows"][0]["costs"]["comparison_caps"].update({"16": 5}),
    ],
)
def test_malformed_decision_contract_or_evaluator_inputs_are_rejected(mutation):
    b = bound_fixture()
    mutation(b)
    with pytest.raises(ValueError):
        Evidence(b, fixture=True)
