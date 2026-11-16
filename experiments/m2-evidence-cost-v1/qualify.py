"""Fit only the two frozen M2 cost hypotheses and retain every negative diagnostic."""

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
DEST = STUDY / "evidence-m2-v1"
RESULTS = STUDY / "returns/job-23376796/results"
KIT = STUDY / "kits/m1-runtime-qualification-v2"
sys.path.insert(0, str(HERE.parent / "filtered-ann-protocol-v2"))

from fannproto.costmodel import OP_NAMES, WORK_FEATURES, features, operations  # noqa: E402
from fannproto.evidence import Evidence  # noqa: E402
from fannproto.policy import FILTERS  # noqa: E402

TRAIN = (
    "decision_continue",
    "count_continue",
    "ranked_continue",
    "turnover_continue",
    "four_compare_continue",
    "count_stop16",
    "bare_stop16",
    "count_stop32",
    "bare_stop32",
    "count_stop64",
    "bare_stop64",
)
TEST = (
    "v2_conservative",
    "v2_moderate",
    "v2_broad",
    "matched_conservative",
    "matched_moderate",
    "matched_broad",
)
CALIBRATION_PAIRS = (
    ("count_continue", "decision_continue", 0),
    ("ranked_continue", "count_continue", 1),
    ("turnover_continue", "ranked_continue", 2),
    ("decision_continue", "native640", 3),
    ("four_compare_continue", "turnover_continue", 4),
)


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def lines(path):
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load():
    frozen = json.loads((DEST / "prospective-plan.json").read_text())
    for path, digest in frozen["inputs"].items():
        assert sha(ROOT / path) == digest, path
    outcome = json.loads((STUDY / "freeze/m1-assessment-v1.json").read_text())
    assert sha(STUDY / "reports/m1-assessment-23376796.json") == outcome["receipt_sha256"]
    for phase in ("timing", "work"):
        folder = RESULTS / phase
        assert sha(folder / "receipt.json") == outcome["raw_phase_receipt_sha256"][phase]
        receipt = json.loads((folder / "receipt.json").read_text())
        for name, digest in receipt["raw_sha256"].items():
            assert sha(folder / name) == digest, name
    bundle = json.loads((RESULTS / "development-prefix-evidence.json").read_text())
    evidence = Evidence(bundle)
    assert sum(len(r["proofs"]) for r in evidence.rows) == 9436
    assert all(set(r["proofs"]) == set(r["observations"]) for r in evidence.rows)
    plan = json.loads((KIT / "m1-plan.json").read_text())
    programs = {
        e["arm"]: e for e in json.loads((KIT / "compiled-programs.json").read_text())["bindings"]
    }
    qids = sorted(
        {q["id"].rsplit("-", 1)[0] for q in lines(KIT / "queries.jsonl")},
        key=lambda q: int(q.rsplit("-v", 1)[1]),
    )
    gi = {q: i for i, q in enumerate(qids)}
    rows = {(r["group"], r["filter"]): r for r in evidence.rows}
    folds = np.array([rows[g, "unfiltered"]["fold"] for g in range(450)])
    cpus = json.loads((RESULTS / "timing/allowed-cpus.json").read_text())
    # Every entry retains its own block's native: never pool repeated anchors.
    timing = [np.full((450, 7, 4, 2, len(block)), np.nan) for block in plan["timing_groups"]]
    for r in lines(RESULTS / "timing/timing.jsonl"):
        block = r["group"]
        index = (
            gi[r["id"].rsplit("-", 1)[0]],
            0 if r["filter"] < 0 else FILTERS.index("votes" + str(r["filter"])),
            cpus.index(r["cpu"]),
            r["cycle"],
            plan["timing_groups"][block].index(r["family"]),
        )
        assert np.isnan(timing[block][index])
        timing[block][index] = r["request_ns"] / 1e6
    assert all(np.all(np.isfinite(t)) for t in timing)
    appearance = {
        name: (g, block.index(name))
        for g, block in enumerate(plan["timing_groups"])
        for name in block
        if name not in ("native640", "empty")
    }
    work = {}
    for r in lines(RESULTS / "work/work.jsonl"):
        work[
            gi[r["id"].rsplit("-", 1)[0]],
            0 if r["filter"] < 0 else FILTERS.index("votes" + str(r["filter"])),
            r["family"],
        ] = r["counts"]
    costs = {}
    for g in range(450):
        for ti, filter_ in enumerate(FILTERS):
            costs[g, filter_] = {
                "reference_native_ms": float(timing[3][g, ti, :, :, 0].mean()),
                "prefix_ratio": {"full": 1.0},
                "search_work": {
                    "full": {
                        k: work[g, ti, "native640"][k]
                        for k in ("vector_calls", "layer0_queue_pops")
                    }
                },
            }
            for cp in (16, 32, 64):
                if str(cp) not in rows[g, filter_]["observations"]:
                    continue
                block, fi = appearance["bare_stop" + str(cp)]
                costs[g, filter_]["prefix_ratio"][str(cp)] = float(
                    timing[block][g, ti, :, :, fi].mean() / timing[block][g, ti, :, :, 0].mean()
                )
                costs[g, filter_]["search_work"][str(cp)] = {
                    k: work[g, ti, "bare_stop" + str(cp)][k]
                    for k in ("vector_calls", "layer0_queue_pops")
                }
    arithmetic_checks = 0
    for arm, entry in programs.items():
        family = next(name for name, number in plan["arms"].items() if number == arm)
        for g in range(450):
            for ti, filter_ in enumerate(FILTERS):
                stop, counts = operations(
                    entry["policy"], rows[g, filter_], force_continue=entry["force_continue"]
                )
                assert sum(counts["count"]) == work[g, ti, family]["feature_passes"], family
                arithmetic_checks += 1
    data = {}
    for name in TRAIN + TEST:
        block, fi = appearance[name]
        entry = programs[plan["arms"][name]]
        actual = timing[block][:, :, :, :, fi]
        native = timing[block][:, :, :, :, 0]
        x = np.empty((450, 7, len(WORK_FEATURES)))
        ops = np.empty((450, 7, len(OP_NAMES)))
        base = np.empty((450, 7))
        for g in range(450):
            for ti, filter_ in enumerate(FILTERS):
                base[g, ti], ops[g, ti], x[g, ti] = features(
                    entry["policy"],
                    rows[g, filter_],
                    costs[g, filter_],
                    force_continue=entry["force_continue"],
                )
        data[name] = {
            "actual": actual,
            "native": native,
            "target": actual.mean(axis=(2, 3)) / native.mean(axis=(2, 3)),
            "x": x,
            "ops": ops,
            "base": base,
        }
    # Native participates only in a within-block paired difference for A.
    data["native640"] = {"target": np.ones((450, 7)), "ops": np.zeros((450, 7, 5))}
    return evidence, rows, folds, costs, data, arithmetic_checks


def fit(data, select, kind):
    result = {}
    for ti, filter_ in enumerate(FILTERS):
        if kind == "signed_additive":
            beta = []
            for hi, lo, operation in CALIBRATION_PAIRS:
                numerator = (data[hi]["target"][select, ti] - data[lo]["target"][select, ti]).mean()
                denominator = (
                    data[hi]["ops"][select, ti, operation] - data[lo]["ops"][select, ti, operation]
                ).mean()
                assert denominator > 0, (filter_, operation)
                beta.append(float(numerator / denominator))
            result[filter_] = {"coefficients": beta}
        else:
            x = np.concatenate([data[name]["x"][select, ti] for name in TRAIN])
            target = np.concatenate(
                [
                    data[name]["target"][select, ti] - data[name]["base"][select, ti]
                    for name in TRAIN
                ]
            )
            beta = np.linalg.solve(
                x.T @ x / len(x) + 1e-3 * np.eye(x.shape[1]), x.T @ target / len(x)
            )
            result[filter_] = {
                "coefficients": beta.tolist(),
                "design_rank": int(np.linalg.matrix_rank(x)),
                "features": x.shape[1],
            }
    return result


def predict(model, item, kind):
    values = item["ops"] if kind == "signed_additive" else item["x"]
    beta = np.array([model[f]["coefficients"] for f in FILTERS])
    return item["base"] + np.einsum("gti,ti->gt", values, beta)


def evaluate(data, predictions, folds, weights):
    details = {}
    for name in TEST:
        r = predictions[name]
        native = data[name]["native"]
        actual = data[name]["actual"]
        predicted = native * r[:, :, None, None]
        base = native[:, 1:].mean(axis=(1, 2, 3))
        observed = actual[:, 1:].mean(axis=(1, 2, 3))
        proxy = predicted[:, 1:].mean(axis=(1, 2, 3))
        error = float((proxy.mean() - observed.mean()) / base.mean())
        interval = np.quantile(
            (weights @ (proxy - observed)) / (weights @ base), [0.025, 0.975]
        ).tolist()
        per_filter = {
            f: float((predicted[:, ti].mean() - actual[:, ti].mean()) / native[:, ti].mean())
            for ti, f in enumerate(FILTERS)
        }
        per_fold = {
            str(f): float(
                (proxy[folds == f].mean() - observed[folds == f].mean()) / base[folds == f].mean()
            )
            for f in range(5)
        }
        per_cpu = {
            str(c): float(
                (predicted[:, 1:, c].mean() - actual[:, 1:, c].mean()) / native[:, 1:, c].mean()
            )
            for c in range(4)
        }
        per_cycle = {
            str(c): float(
                (predicted[:, 1:, :, c].mean() - actual[:, 1:, :, c].mean())
                / native[:, 1:, :, c].mean()
            )
            for c in range(2)
        }
        violations = []
        if not np.all(np.isfinite(predicted)) or np.any(predicted <= 0):
            violations.append("nonpositive_or_nonfinite_prediction")
        if abs(error) > 0.01:
            violations.append("primary_error_exceeds_0.01")
        if interval[0] < -0.01 or interval[1] > 0.01:
            violations.append("primary_error_interval_exceeds_plus_minus_0.01")
        for label, values in (
            ("condition", per_filter),
            ("fold", per_fold),
            ("CPU_slot", per_cpu),
            ("cycle", per_cycle),
        ):
            violations.extend(
                f"{label}_{key}_error_exceeds_0.02"
                for key, value in values.items()
                if abs(value) > 0.02
            )
        details[name] = {
            "primary_predicted_ratio": float(proxy.mean() / base.mean()),
            "primary_observed_ratio": float(observed.mean() / base.mean()),
            "primary_signed_ratio_error": error,
            "conditional95pct_error_interval": interval,
            "per_filter_signed_error": per_filter,
            "per_exposed_fold_signed_error": per_fold,
            "per_CPU_slot_signed_error": per_cpu,
            "per_cycle_signed_error": per_cycle,
            "violations": violations,
            "passed": not violations,
        }
    ordering = []
    for i, a in enumerate(TEST[:3]):
        for b in TEST[i + 1 : 3]:
            actual = details[a]["primary_observed_ratio"] - details[b]["primary_observed_ratio"]
            predicted = (
                details[a]["primary_predicted_ratio"] - details[b]["primary_predicted_ratio"]
            )
            if abs(actual) > 0.01:
                ordering.append(
                    {
                        "programs": [a, b],
                        "observed_difference": actual,
                        "predicted_difference": predicted,
                        "passed": actual * predicted > 0,
                    }
                )
    return {
        "passed": all(d["passed"] for d in details.values()) and all(d["passed"] for d in ordering),
        "excluded_programs": details,
        "ordering_checks": ordering,
    }


def main():
    out = DEST / "model-qualification.json"
    assert not out.exists(), "preserve completed qualification; use a new version for amendments"
    evidence, rows, folds, costs, data, checks = load()
    weights = np.random.default_rng(20261116).multinomial(450, np.full(450, 1 / 450), size=20000)
    models = {}
    for kind in ("signed_additive", "ridge_work_observation"):
        predictions = {name: np.full((450, 7), np.nan) for name in TEST}
        fold_models = {}
        for fold in range(5):
            trained = fit(data, folds != fold, kind)
            fold_models[str(fold)] = trained
            for name in TEST:
                p = predict(trained, data[name], kind)
                predictions[name][folds == fold] = p[folds == fold]
        evaluation = evaluate(data, predictions, folds, weights)
        models[kind] = {
            **evaluation,
            "fold_models": fold_models,
            "full_development_model": fit(data, np.ones(450, dtype=bool), kind),
            "prediction_artifact": kind + "-predictions.npz",
        }
        np.savez_compressed(DEST / models[kind]["prediction_artifact"], **predictions)
    selected = next((kind for kind in models if models[kind]["passed"]), None)
    # Inputs are retained for the eventual binding; they never become policy features.
    write(
        DEST / "evaluator-cost-inputs.json",
        [{"group": g, "filter": f, **costs[g, f]} for g in range(450) for f in FILTERS],
    )
    report = {
        "schema": "filtered-ann.M2-cost-qualification.v1",
        "date": "2026-11-16",
        "status": "qualified_bounded_development_proxy"
        if selected
        else "negative_no_cost_model_qualified",
        "selected_model": selected,
        "cost_ranking_enabled": selected is not None,
        "models": models,
        "feature_arithmetic_checks": checks,
        "features": {"additive": OP_NAMES, "ridge": WORK_FEATURES},
        "calibration_programs": TRAIN,
        "excluded_complete_programs": TEST,
        "scope": {
            "development_groups": 450,
            "scalar_filters": 6,
            "unfiltered": True,
            "prefix_labels": 9436,
            "partial_prefix_labels": 1496,
            "external_requests": 0,
            "SQL_searches": 0,
            "validation_test_outcomes_opened": False,
        },
        "exposed_fold_limit": "Query groups and base-probe costs are exposed; target complete "
        "programs are excluded from calibration. This is not protected validation or "
        "unseen-query/allocation prediction.",
        "plan_freeze_sha256": sha(DEST / "prospective-plan.json"),
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in (
                HERE / "qualify.py",
                HERE.parent / "filtered-ann-protocol-v2/fannproto/costmodel.py",
            )
        },
        "input_evidence_identity": evidence.identity,
    }
    write(out, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "selected_model": selected,
                "feature_arithmetic_checks": checks,
                "model_results": {
                    kind: {
                        "passed": value["passed"],
                        "programs": {
                            name: {
                                k: v
                                for k, v in d.items()
                                if k in ("primary_signed_ratio_error", "violations")
                            }
                            for name, d in value["excluded_programs"].items()
                        },
                    }
                    for kind, value in models.items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
