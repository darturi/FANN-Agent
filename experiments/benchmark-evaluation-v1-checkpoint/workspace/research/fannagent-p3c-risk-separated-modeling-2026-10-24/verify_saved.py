"""Reconstruct locked P3c outputs and fitting-leaf statistics; never fit a model."""

import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "agent/experiments/risk-separated-stop-modeling-v1"
OUT = (
    ROOT
    / "trials/torch-reviews-risk-separated-stop-modeling-v1/runs/p3c-20261024-local-v1"
)
sys.path.insert(0, str(SOURCE))
import common
from common import digest, load_api, offline_guard, read, save, verify_inputs
from data import FILTERS, GRID, load, outcomes
from stats import Bootstrap, assess, paired


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def same(left, right, where="result"):
    if isinstance(left, dict):
        assert isinstance(right, dict) and set(left) == set(right), where
        for key in left:
            same(left[key], right[key], where + "/" + key)
    elif isinstance(left, list):
        assert isinstance(right, list) and len(left) == len(right), where
        for i, (a, b) in enumerate(zip(left, right)):
            same(a, b, where + "/" + str(i))
    elif isinstance(left, float):
        assert (
            isinstance(right, (int, float)) and np.isfinite(left) and np.isfinite(right)
        ), where
        assert abs(left - right) <= 1e-12, (where, left, right)
    else:
        assert left == right, (where, left, right)


def mask(node, x):
    values = x[:, node["feature"]]
    if node["op"] == "bool_false":
        return values == 0
    return values <= node["cut"] if node["op"] == "lte" else values < node["cut"]


def predict(model, x):
    total = np.zeros((len(x), 2))
    for tree in model["trees"]:
        result = np.empty((len(x), 2))
        pending = [(tree, np.arange(len(x)))]
        while pending:
            node, ix = pending.pop()
            if "value" in node:
                result[ix] = [node["value"], node["benefit"]]
            else:
                left = mask(node, x[ix])
                pending.extend([(node["left"], ix[left]), (node["right"], ix[~left])])
        total += result
    return total / len(model["trees"])


def scores(data, profile, model, indices):
    result = np.empty((len(indices), 8, 2))
    result[:, :, 0], result[:, :, 1] = np.inf, -np.inf
    q, j = np.where(data.reached[indices])
    result[q, j] = predict(model, data.x[profile][indices[q], j])
    return result


def first_actions(predictions, cap, floor):
    # Explicit temporal scan instead of the implementation's vectorized argmax.
    return np.array(
        [
            next(
                (
                    j
                    for j, (risk, benefit) in enumerate(row)
                    if np.isfinite(risk)
                    and np.isfinite(benefit)
                    and risk <= cap
                    and benefit >= floor
                ),
                8,
            )
            for row in predictions
        ]
    )


def fitting_arrays(data, profile, groups):
    selected = data.indices(groups)
    q, j = np.where(data.reached[selected])
    qi = selected[q]
    label = data.labels[profile]
    risk = np.array(
        [
            1.0
            if label["valid"][i, cp] != 1 or label["count"][i, cp] != 10
            else max(0.0, data.meta[i]["native_recall"] - label["recall"][i, cp])
            for i, cp in zip(qi, j)
        ]
    )
    benefit = np.minimum(label["activation"][qi, j], label["reuse"][qi, j])
    weights = np.array([1.0 / (3 * int(data.reached[i].sum())) for i in qi])
    ids = np.array([data.meta[i]["group"] for i in qi])
    return data.x[profile][qi, j], risk, benefit, weights, ids


def verify_leaves(model, arrays):
    x, risk, benefit, weights, ids = arrays
    leaves, nodes = 0, 0
    for tree in model["trees"]:
        pending = [(tree, np.arange(len(x)), 0)]
        while pending:
            node, ix, depth = pending.pop()
            nodes += 1
            assert depth <= (3 if model["method"] == "shallow_tree" else 8)
            if "value" in node:
                leaves += 1
                assert node["groups"] == len(set(ids[ix])) >= 8
                assert node["rows"] == len(ix)
                same(float(weights[ix].sum()), node["weight"], "leaf weight")
                same(
                    float(np.clip(np.average(risk[ix], weights=weights[ix]), 0, 1)),
                    node["value"],
                    "leaf risk",
                )
                same(
                    float(np.average(benefit[ix], weights=weights[ix])),
                    node["benefit"],
                    "leaf benefit",
                )
            else:
                assert 0 <= node["feature"] < len(model["feature_names"])
                left = mask(node, x[ix])
                assert min(len(set(ids[ix[left]])), len(set(ids[ix[~left]]))) >= 8
                pending.extend(
                    [
                        (node["left"], ix[left], depth + 1),
                        (node["right"], ix[~left], depth + 1),
                    ]
                )
    return leaves, nodes


def main():
    assert not (OUT / "failure.json").exists()
    pins = verify_inputs()
    lock, verification, performance = [
        read(OUT / name)
        for name in ["design-lock.json", "verification.json", "performance.json"]
    ]
    assert verification["status"] == "passed"
    for name, expected in lock["source_files_sha256"].items():
        assert sha(SOURCE / name) == expected, name
    for name, expected in verification["files_sha256"].items():
        assert sha(OUT / name) == expected, name
    offline_guard(OUT)
    load_api()
    data = load(pins)
    folds = read(OUT / "folds.json")
    baseline_path = ROOT / pins["baseline_run"]
    assert folds["outer"] == data.folds and folds == read(baseline_path / "folds.json")
    models, inner = {}, {}
    leaves = nodes = trees = fits = 0
    for path in sorted((OUT / "fits").glob("*.json")):
        receipt = read(path)
        outer, profile, method = [
            receipt[k] for k in ["outer_fold", "profile", "method"]
        ]
        model_path = OUT / receipt["model_file"]
        assert sha(model_path) == receipt["model_file_sha256"]
        with gzip.open(model_path, "rt") as stream:
            model = json.load(stream)
        assert digest(model) == receipt["model_sha256"]
        assert model["feature_names"] == data.names[profile]
        held = {g for g, f in data.folds.items() if f == outer}
        groups = receipt["training_groups"]
        assert not set(groups) & held
        if receipt["stage"] == "inner":
            assignment = folds["inner"][str(outer)]
            val = sorted(g for g, f in assignment.items() if f == receipt["inner_fold"])
            assert set(groups) == set(assignment) - set(val)
            assert len(groups) == 120 and len(val) == 40
        else:
            assert set(groups) == set(data.folds) - held and len(groups) == 160
        arrays = fitting_arrays(data, profile, groups)
        assert digest(arrays[1].tolist()) == receipt["risk_target_sha256"]
        assert digest(arrays[2].tolist()) == receipt["benefit_target_sha256"]
        assert digest(arrays[3].tolist()) == receipt["weights_sha256"]
        ll, nn = verify_leaves(model, arrays)
        assert nn == receipt["nodes_after_group_pruning"]
        assert len(model["trees"]) == (1 if method == "shallow_tree" else 64)
        fits += 1
        trees += len(model["trees"])
        leaves += ll
        nodes += nn
        if receipt["stage"] == "inner":
            all_train = data.indices(sorted(set(data.folds) - held))
            pos = {i: j for j, i in enumerate(all_train)}
            tag = f"{profile}-{method}-outer{outer}"
            if tag not in inner:
                inner[tag] = np.empty((len(all_train), 8, 2))
                inner[tag][:, :, 0], inner[tag][:, :, 1] = np.inf, -np.inf
            val_ix = data.indices(val)
            inner[tag][[pos[i] for i in val_ix]] = scores(data, profile, model, val_ix)
        else:
            models[(profile, method, outer)] = model
    assert fits == 100 and trees == 3250
    print(
        f"Verified {fits} models, {trees} trees and {leaves} fitting-leaf risk/benefit statistics.",
        flush=True,
    )
    inner_count = 0
    for path in sorted((OUT / "selection").glob("*.json")):
        selection = read(path)
        saved = read(OUT / "inner-predictions" / path.name)
        ix = data.indices(selection["training_groups"])
        assert saved["query_ids"] == [data.meta[i]["query_id"] for i in ix]
        predicted = inner[path.stem]
        stored = np.empty_like(predicted)
        # Decode the null mask explicitly, including legitimate finite risk zeros.
        for i, row in enumerate(saved["risk_benefit_scores"]):
            for j, pair in enumerate(row):
                stored[i, j] = [np.inf, -np.inf] if pair == [None, None] else pair
        assert np.array_equal(np.isfinite(stored), np.isfinite(predicted))
        assert np.allclose(
            stored[np.isfinite(stored)],
            predicted[np.isfinite(predicted)],
            atol=1e-12,
            rtol=0,
        )
        boot = Bootstrap(selection["training_groups"])
        eligible = []
        for trial in selection["trials"]:
            actions = first_actions(
                predicted, trial["risk_cap"], trial["benefit_floor_ms"]
            )
            assert actions.tolist() == trial["inner_oof_actions"]
            report = assess(
                outcomes(data, selection["profile"], ix, actions),
                boot,
                all_metrics=False,
            )
            same(report, trial["assessment"])
            if report["development_signal"]:
                eligible.append(trial)
            inner_count += 1
        winner = (
            max(
                eligible,
                key=lambda t: (
                    t["assessment"]["utility_proxy_ms"],
                    -t["risk_cap"],
                    t["benefit_floor_ms"],
                ),
            )
            if eligible
            else None
        )
        assert selection["chosen"] == (
            None
            if winner is None
            else {k: winner[k] for k in ["risk_cap", "benefit_floor_ms"]}
        )
    assert inner_count == 980
    print(
        "All 980 candidates and selections reconstruct from canonical inner-model predictions.",
        flush=True,
    )
    totals = {
        phase: {
            p: {m: [] for m in ["shallow_tree", "extra_trees"]}
            for p in ["static23", "progress34"]
        }
        for phase in ["calibrated", "fixed_diagnostic"]
    }
    cases = 0
    for path in sorted((OUT / "outer-records").glob("*.json")):
        rows = read(path)["rows"]
        first = rows[0]
        profile, method, outer, phase = [
            first[k] for k in ["profile", "method", "outer_fold", "phase"]
        ]
        ix = data.indices([g for g, f in data.folds.items() if f == outer])
        if first["risk_cap"] is None:
            actions = np.full(len(ix), 8)
        else:
            # Independently use complete causal trajectories, retaining only measured grid states.
            rebuilt_scores = np.empty((len(ix), 8, 2))
            rebuilt_scores[:, :, 0], rebuilt_scores[:, :, 1] = np.inf, -np.inf
            for q, i in enumerate(ix):
                lo, hi = data.slices[i]
                allowed = [cp for cp in GRID if cp <= hi - lo]
                x = data.full_x[profile][[lo + cp - 1 for cp in allowed]]
                rebuilt_scores[q, [GRID.index(cp) for cp in allowed]] = predict(
                    models[(profile, method, outer)], x
                )
            actions = first_actions(
                rebuilt_scores, first["risk_cap"], first["benefit_floor_ms"]
            )
        rebuilt = outcomes(data, profile, ix, actions)
        for fresh, saved in zip(rebuilt, rows):
            for key, value in fresh.items():
                same(value, saved[key], key)
        assert len(rows) == 120
        cases += len(rows)
        totals[phase][profile][method].extend(rows)
    boot = Bootstrap(data.folds)
    reports = {
        phase: {
            p: {m: assess(rs, boot) for m, rs in mm.items()} for p, mm in pp.items()
        }
        for phase, pp in totals.items()
    }
    same(reports, performance["reports"])
    contrasts = {
        phase: {
            p: paired(mm["extra_trees"], mm["shallow_tree"], boot)
            for p, mm in pp.items()
        }
        for phase, pp in totals.items()
    }
    same(contrasts, performance["paired_flexible_minus_shallow"])
    baseline = {
        phase: {
            p: {m: [] for m in ["shallow_tree", "extra_trees"]}
            for p in ["static23", "progress34"]
        }
        for phase in totals
    }
    for path in sorted((baseline_path / "outer-records").glob("*.json")):
        rows = read(path)["rows"]
        f = rows[0]
        baseline[f["phase"]][f["profile"]][f["method"]].extend(rows)
    baseline_reports = {
        phase: {
            p: {m: assess(rs, boot) for m, rs in mm.items()} for p, mm in pp.items()
        }
        for phase, pp in baseline.items()
    }
    same(baseline_reports, read(baseline_path / "performance.json")["reports"])
    comparisons = {
        phase: {
            p: {m: paired(rs, baseline[phase][p][m], boot) for m, rs in mm.items()}
            for p, mm in pp.items()
        }
        for phase, pp in totals.items()
    }
    same(comparisons, performance["paired_p3c_minus_frozen_p3b"])
    for profile in ["static23", "progress34"]:
        all_ix = np.arange(600)
        controls = performance["controls"][profile]
        same(
            assess(outcomes(data, profile, all_ix, np.full(600, 8)), boot),
            controls["measured_profile_continue"],
        )
        same(
            assess(
                outcomes(data, profile, all_ix, np.where(data.reached[:, 7], 7, 8)),
                boot,
            ),
            controls["fixed_checkpoint128_else_continue"],
        )
        native = [
            {
                **q,
                "policy_recall": q["native_recall"],
                "recall_delta": 0.0,
                "valid": True,
                "returned_count": 10,
                "checkpoint": None,
                "activation_proxy_ms_saved": 0.0,
                "reuse_proxy_ms_saved": 0.0,
                "layer0_distances": q["native_work"],
            }
            for q in data.meta
        ]
        same(
            assess(native, boot),
            {k: v for k, v in controls["analytical_native"].items() if k != "scope"},
        )
    verify_inputs()
    assert common.FITS == 0 and cases == 4800
    result = {
        "status": "passed",
        "scientific_estimator_fits": fits,
        "individual_trees": trees,
        "training_leaves_independently_reconstructed": leaves,
        "retained_nodes_verified": nodes,
        "inner_model_predictions_and_candidate_assessments_reconstructed": inner_count,
        "outer_first_stop_cases_reconstructed": cases,
        "prior_baseline_and_controls_reconstructed": True,
        "all_model_hashes_group_splits_and_leaf_values_verified": True,
        "reports_and_all_paired_contrasts_match_tolerance": 1e-12,
        "source_input_preservation": True,
        "new_fits": common.FITS,
        "new_measurements": 0,
        "performance_sha256": sha(OUT / "performance.json"),
        "design_lock_sha256": sha(OUT / "design-lock.json"),
    }
    save(OUT / "verification-replay.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        main()
