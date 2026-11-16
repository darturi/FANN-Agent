"""Versioned empirical envelope qualification; reuse the failed M2 predictor without refit."""

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
DEST = STUDY / "uncertainty-shortlist-v1"
M2 = STUDY / "evidence-m2-v1"
PROTOCOL = HERE.parent / "filtered-ann-protocol-v2"
sys.path.insert(0, str(PROTOCOL))
from fannproto.costmodel import operations  # noqa: E402
from fannproto.policy import FILTERS, POINTS, PROFILE, replay, rule_hash  # noqa: E402
from fannproto.uncertainty import (  # noqa: E402
    ESTIMATE_STATUS,
    SCHEMA,
    proxy_estimate,
    proxy_values,
    select_shortlist,
)


def load_m2_module():
    spec = importlib.util.spec_from_file_location(
        "m2_original_qualification", HERE.parent / "m2-evidence-cost-v1/qualify.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    predecessor = load_m2_module()
    sha, write = predecessor.sha, predecessor.write
    assert not (DEST / "qualification.json").exists(), "preserve completed envelope qualification"
    frozen = json.loads((DEST / "plan-freeze.json").read_text())
    for path, digest in frozen["inputs"].items():
        assert sha(ROOT / path) == digest, path
    for path, digest in frozen["predecessor_source_sha256"].items():
        assert sha(DEST / path) == digest, path
    _, _, _, _, data, _ = predecessor.load()
    bundle = deepcopy(json.loads((M2 / "bound-evidence.json").read_text()))
    point = json.loads((M2 / "model-qualification.json").read_text())
    assert point["status"] == "negative_no_cost_model_qualified"
    contract = {
        "schema": SCHEMA,
        "runtime_profile": PROFILE.fingerprint,
        "status": "pending_new_envelope_qualification",
        "point_model_precision_qualified": False,
        "max_live_nominees": 3,
        "regret_limit": 0.01,
        "error_radius": 0.01,
        "fold_models": {
            fold: {f: model[f]["coefficients"] for f in FILTERS}
            for fold, model in point["models"]["signed_additive"]["fold_models"].items()
        },
        "supported_masks": {f: {str(cp): {0} for cp in POINTS} for f in FILTERS},
    }
    kit = STUDY / "kits/m1-runtime-qualification-v2"
    programs = {
        e["arm"]: e for e in json.loads((kit / "compiled-programs.json").read_text())["bindings"]
    }
    arms = json.loads((kit / "m1-plan.json").read_text())["arms"]
    for entry in programs.values():
        for f, masks in entry["observation_plan"].items():
            for cp, mask in masks.items():
                contract["supported_masks"][f][cp].add(mask)
    contract["supported_masks"] = {
        f: {cp: sorted(masks) for cp, masks in points.items()}
        for f, points in contract["supported_masks"].items()
    }
    cost_inputs = {
        (r["group"], r["filter"]): r
        for r in json.loads((M2 / "evaluator-cost-inputs.json").read_text())
    }
    by_row = {}
    for row in bundle["rows"]:
        costs = {
            k: deepcopy(v)
            for k, v in cost_inputs[row["group"], row["filter"]].items()
            if k not in ("group", "filter")
        }
        caps = {cp: 0 for cp in row["observations"]}
        for family in predecessor.TRAIN:
            entry = programs[arms[family]]
            _, counts = operations(entry["policy"], row, force_continue=entry["force_continue"])
            for cp, comparisons in zip(POINTS, counts["comparison"], strict=True):
                if str(cp) in caps:
                    caps[str(cp)] = max(caps[str(cp)], comparisons)
        costs["comparison_caps"] = caps
        row["costs"] = costs
        by_row[row["group"], row["filter"]] = row
    reference = np.array(
        [[by_row[g, f]["costs"]["reference_native_ms"] for f in FILTERS] for g in range(450)]
    )
    folds = np.array([by_row[g, "unfiltered"]["fold"] for g in range(450)])
    weights = np.random.default_rng(20261116).multinomial(450, np.full(450, 1 / 450), size=20000)
    diagnostics = {}
    estimates = {}
    records = []
    for name in predecessor.TEST:
        entry = programs[arms[name]]
        values, unsupported = proxy_values(
            entry["policy"], bundle["rows"], contract, force_continue=entry["force_continue"]
        )
        assert unsupported is None, (name, unsupported)
        ratios = np.empty((450, 7))
        for row, value in zip(bundle["rows"], values, strict=True):
            ratios[row["group"], FILTERS.index(row["filter"])] = value
        predicted = ratios * reference
        actual = data[name]["actual"]
        native = data[name]["native"]
        p, ref = predicted[:, 1:].mean(axis=1), reference[:, 1:].mean(axis=1)
        a, n = actual[:, 1:].mean(axis=(1, 2, 3)), native[:, 1:].mean(axis=(1, 2, 3))
        center = float(p.mean() / ref.mean())
        target = float(a.mean() / n.mean())
        errors = {"primary": center - target}
        interval = np.quantile(
            (weights @ p) / (weights @ ref) - (weights @ a) / (weights @ n), [0.025, 0.975]
        ).tolist()
        errors.update({"primary_bootstrap_low": interval[0], "primary_bootstrap_high": interval[1]})
        for ti, f in enumerate(FILTERS):
            errors["filter:" + f] = float(
                predicted[:, ti].mean() / reference[:, ti].mean()
                - actual[:, ti].mean() / native[:, ti].mean()
            )
        for fold in range(5):
            select = folds == fold
            errors["fold:" + str(fold)] = float(
                p[select].mean() / ref[select].mean() - a[select].mean() / n[select].mean()
            )
        for cpu in range(4):
            errors["CPU_slot:" + str(cpu)] = float(
                center - actual[:, 1:, cpu].mean() / native[:, 1:, cpu].mean()
            )
        for cycle in range(2):
            errors["cycle:" + str(cycle)] = float(
                center - actual[:, 1:, :, cycle].mean() / native[:, 1:, :, cycle].mean()
            )
        diagnostics[name] = {
            "primary_proxy": center,
            "primary_observed": target,
            "signed_errors": errors,
            "max_absolute_error": max(map(abs, errors.values())),
        }
        estimates[name] = proxy_estimate(
            entry["policy"], bundle["rows"], contract, force_continue=entry["force_continue"]
        )
        evaluation = replay(entry["policy"], bundle["rows"])
        records.append(
            {
                "candidate_id": name,
                "rule_hash": rule_hash(entry["policy"]),
                "policy": entry["policy"],
                "evaluation": evaluation,
                "nominee_role": "control" if entry["force_continue"] else "policy",
            }
        )
    coverage = {}
    for family in ("conservative", "moderate", "broad"):
        held = {"v2_" + family, "matched_" + family}
        cal = {n: d for n, d in diagnostics.items() if n not in held}
        radius = 0.01 + max(d["max_absolute_error"] for d in cal.values())
        failures = {
            n: {k: v for k, v in diagnostics[n]["signed_errors"].items() if abs(v) > radius}
            for n in sorted(held)
        }
        coverage[family] = {
            "excluded_pair": sorted(held),
            "calibration_programs": sorted(cal),
            "radius": radius,
            "failures": failures,
            "passed": radius <= 0.05 and not any(failures.values()),
        }
    radius = 0.01 + max(d["max_absolute_error"] for d in diagnostics.values())
    contract["error_radius"] = radius
    for record in records:
        name = record["candidate_id"]
        estimate = estimates[name]
        center = estimate["primary_ratio_proxy"]
        estimate["engineering_error_radius"] = radius
        estimate["primary_ratio_interval"] = [max(0, center - radius), center + radius]
        for f, value in estimate["per_filter"].items():
            c = value["ratio_proxy"]
            value["ratio_interval"] = [max(0, c - radius), c + radius]
        record["cost_estimate"] = estimate
        assert estimate["status"] == ESTIMATE_STATUS
    selected = select_shortlist(records)
    observed = {
        r["candidate_id"]: diagnostics[r["candidate_id"]]["primary_observed"]
        for r in records
        if r["nominee_role"] == "policy"
    }
    selected_cost = min([1, *(observed[cid] for cid in selected["candidate_ids"])])
    actual_regret = selected_cost - min([1, *observed.values()])
    passed = (
        all(r["passed"] for r in coverage.values())
        and radius <= 0.05
        and selected["status"] == "selected_for_M5"
        and len(selected["candidate_ids"]) <= 3
        and actual_regret <= 0.01
    )
    contract["status"] = (
        "qualified_conditional_experiment_selection"
        if passed
        else "failed_new_envelope_qualification"
    )
    write(DEST / "binding-inputs.json", {"rows": bundle["rows"], "contract": contract})
    report = {
        "schema": "filtered-ann.uncertainty-shortlist-qualification.v1",
        "date": "2026-11-16",
        "status": "qualified_conditional_experiment_selection"
        if passed
        else "negative_uncertainty_contract_not_qualified",
        "point_model_precision_qualified": False,
        "point_model_refit": False,
        "known_M2_results_inform_this_method_version": True,
        "outer_pair_coverage": coverage,
        "deployment_error_radius": radius,
        "radius_limit": 0.05,
        "regret_limit": 0.01,
        "diagnostics": diagnostics,
        "diagnostic_shortlist": selected,
        "diagnostic_observed_regret": actual_regret,
        "diagnostic_selected_hashes": [
            r["rule_hash"] for r in records if r["candidate_id"] in selected["candidate_ids"]
        ],
        "limits": "Empirical exposed-development engineering qualification, not a prediction "
        "coverage guarantee for unseen programs/queries/allocations. The conditional regret "
        "certificate assumes costs inside envelopes and ideal M5 measurement/choice. All M1/M2 "
        "evidence and their earlier precision failures remain unchanged.",
        "all_six_filters": True,
        "unfiltered": True,
        "prefix_labels": 9436,
        "provider_calls": 0,
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
        "plan_freeze_sha256": sha(DEST / "plan-freeze.json"),
        "M2_negative_qualification_sha256": sha(M2 / "model-qualification.json"),
        "binding_inputs_sha256": sha(DEST / "binding-inputs.json"),
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in (HERE / "qualify.py", PROTOCOL / "fannproto/uncertainty.py")
        },
    }
    write(DEST / "qualification.json", report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "outer_pair_radii": {k: v["radius"] for k, v in coverage.items()},
                "outer_failures": {k: v["failures"] for k, v in coverage.items()},
                "deployment_radius": radius,
                "diagnostic_shortlist": selected["candidate_ids"],
                "conditional_regret": selected["conditional_regret_bound"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
