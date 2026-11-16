"""Bind the qualified decision-support contract; preserve M2 precision failures and inputs."""

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
DEST = STUDY / "uncertainty-shortlist-v1"
M2 = STUDY / "evidence-m2-v1"
PROTOCOL = HERE.parent / "filtered-ann-protocol-v2"
sys.path.insert(0, str(PROTOCOL))
from fannproto.controller import generation_ready  # noqa: E402
from fannproto.evidence import Evidence  # noqa: E402
from fannproto.uncertainty import COST_STATUS  # noqa: E402

from fannagent.store import digest  # noqa: E402


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def main():
    assert not (DEST / "bound-evidence.json").exists(), "preserve completed binding"
    result = json.loads((DEST / "qualification.json").read_text())
    assert result["status"] == "qualified_conditional_experiment_selection"
    assert (
        result["point_model_refit"] is False and result["point_model_precision_qualified"] is False
    )
    for path, value in result["source_sha256"].items():
        assert sha(ROOT / path) == value
    assert sha(DEST / "binding-inputs.json") == result["binding_inputs_sha256"]
    inputs = json.loads((DEST / "binding-inputs.json").read_text())
    contract = inputs["contract"]
    contract["qualification_receipt_sha256"] = sha(DEST / "qualification.json")
    original = json.loads((M2 / "bound-evidence.json").read_text())
    # Exact proof/feature/work equivalence: the only row addition is evaluator cost-support data.
    assert len(inputs["rows"]) == len(original["rows"]) == 3150
    for old, new in zip(original["rows"], inputs["rows"], strict=True):
        assert {k: v for k, v in new.items() if k != "costs"} == old
    bundle = deepcopy(original)
    bundle["rows"] = inputs["rows"]
    bundle["cost_status"] = COST_STATUS
    bundle["shortlist_contract"] = contract
    bundle["evidence_qualification"]["uncertainty_contract_qualification_sha256"] = sha(
        DEST / "qualification.json"
    )
    bundle["cost_guidance"].update(
        {
            "status": "qualified_uncertainty_aware_M5_experiment_selection_only",
            "point_model_precision_qualified": False,
            "engineering_error_radius": contract["error_radius"],
            "conditional_regret_limit": contract["regret_limit"],
            "limits": "M2 point-precision qualification remains failed. Empirical engineering "
            "envelopes support a bounded M5 measurement shortlist only, conditional on support and "
            "costs in the intervals. Abstain when more than three ambiguous nominees cannot meet "
            "the regret limit. No future coverage or final performance guarantee; actual M5 "
            "program/matched-control timing remains required.",
        }
    )
    evidence = Evidence(bundle)
    gates = deepcopy(json.loads((M2 / "bound-gates.json").read_text()))
    gates["M2"] = {
        **gates["M2"],
        "status": "qualified_uncertainty_shortlist_contract",
        "evidence_hash": evidence.identity,
        "point_cost_ranking_enabled": False,
        "cost_ranking_enabled": False,
        "uncertainty_shortlisting_enabled": True,
        "shortlist_contract_hash": digest(contract),
        "shortlist_qualification_sha256": sha(DEST / "qualification.json"),
        "old_M2_precision_qualification_remains_failed": True,
    }
    gates["generation_blocked_by"] = [
        "Concrete provider episode payload/rates/authorization",
        "Bound M3 rerun pending",
    ]
    gates["provider_authorization"] = "new concrete provider episode not authorized"
    generation_ready(evidence, gates)
    write(DEST / "bound-evidence.json", bundle)
    write(DEST / "bound-gates.json", gates)
    write(DEST / "compact-summary.json", evidence.summary())
    (DEST / "primer.md").write_text(
        "# Uncertainty-aware development research contract\n\n"
        "450 exposed development groups; all six scalar filters plus unfiltered; frozen folds.\n"
        "All9,436 actual prefix labels, including1,496 partials; zero unknown reached labels.\n"
        "Preserve each query's raw native640 recall. Exact truth is scoring only, never repair.\n"
        "Policies see only qualified causal features; IDs, folds, costs and outcomes "
        "are evaluator-only.\n\n"
        f"The engineering native-ratio envelope is plus/minus "
        f"{100 * contract['error_radius']:.4f} percentage points.\n"
        "It is not a prediction confidence interval or measured new-policy latency. "
        "M2 precision remains failed.\n"
        "The controller enumerates subsets of at most3 supported zero-loss "
        "scalar-stopping policies.\n"
        "It accepts only a conditional interval regret bound<=one native percentage point, "
        "with native available.\n"
        "Close point estimates never break interval ties. An ambiguous pool larger than "
        "the cap can force abstention.\n"
        "Unsupported comparisons retain quality/work feedback but cannot be nominated "
        "through this contract.\n"
        "Any nominated programs require actual M5 timings and matched continue controls "
        "before speed claims.\n"
        "No validation/test access or external provider episode is authorized by this binding.\n"
    )
    receipt = {
        "schema": "filtered-ann.uncertainty-shortlist-binding.v1",
        "date": "2026-11-16",
        "status": "bound_qualified_conditional_experiment_selection",
        "evidence_identity": evidence.identity,
        "shortlist_contract_hash": digest(contract),
        "qualification_sha256": sha(DEST / "qualification.json"),
        "predecessor_evidence_sha256": sha(M2 / "bound-evidence.json"),
        "counts": {
            "rows": 3150,
            "groups": 450,
            "conditions": 7,
            "prefixes": 9436,
            "partial_prefixes": 1496,
            "missing": 0,
        },
        "all_row_proofs_features_work_and_folds_preserved": True,
        "point_cost_ranking_enabled": False,
        "uncertainty_shortlisting_enabled": True,
        "point_model_precision_qualified": False,
        "provider_authorized": False,
        "provider_calls": 0,
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                HERE / "bind.py",
                PROTOCOL / "fannproto/evidence.py",
                PROTOCOL / "fannproto/controller.py",
                PROTOCOL / "fannproto/uncertainty.py",
            ]
        },
        "artifact_sha256": {
            name: sha(DEST / name)
            for name in (
                "bound-evidence.json",
                "bound-gates.json",
                "compact-summary.json",
                "primer.md",
            )
        },
    }
    write(DEST / "binding-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
