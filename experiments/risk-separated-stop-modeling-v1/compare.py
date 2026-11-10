"""One frozen nested grouped offline comparison. Never dispatches measurements."""

import argparse
import gzip
import json
import platform
import resource
import time
from collections import Counter
from pathlib import Path

import common
import numpy as np
from common import (
    BASE,
    SOURCE,
    contract,
    digest,
    load_api,
    offline_guard,
    read,
    save,
    sha,
    timestamp,
    verify_inputs,
    versions,
)
from data import FILTERS, GRID, load, outcomes
from models import (
    continue_policy,
    first_actions,
    fit,
    grid_scores,
    shallow_policy,
    verify_shared_interpreter,
)
from stats import Bootstrap, assess, paired
from threadpoolctl import threadpool_limits


def inner_assignment(groups, outer):
    ordered = sorted(groups, key=lambda g: digest([20261024, "p3b-inner-v1", outer, g]))
    return {g: i % 4 for i, g in enumerate(ordered)}


def select(trials):
    eligible = [t for t in trials if t["assessment"]["development_signal"]]
    return (
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


def model_file(output, identity, model, receipt):
    path = output / "models" / (identity + ".json.gz")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(model, separators=(",", ":"), sort_keys=True, allow_nan=False).encode()
    with path.open("xb") as stream:
        with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as zipped:
            zipped.write(data)
    receipt["model_file"] = str(path.relative_to(output))
    receipt["model_file_sha256"] = sha(path)
    save(output / "fits" / (identity + ".json"), receipt)


def diagnostic_errors(rows):
    return {
        "by_filter": {
            f: {
                "cases": sum(r["stratum"] == f for r in rows),
                "stops": sum(r["stratum"] == f and r["checkpoint"] is not None for r in rows),
                "loss_cases": sum(r["stratum"] == f and r["recall_delta"] < -1e-12 for r in rows),
                "incomplete_cases": sum(r["stratum"] == f and not r["valid"] for r in rows),
            }
            for f in FILTERS
        },
        "by_checkpoint": {
            cp: {
                "cases": len(rs),
                "loss_cases": sum(r["recall_delta"] < -1e-12 for r in rs),
                "incomplete_cases": sum(not r["valid"] for r in rs),
                "mean_recall_delta": float(np.mean([r["recall_delta"] for r in rs])),
            }
            for cp in [*map(str, GRID), "continue"]
            if (
                rs := [
                    r
                    for r in rows
                    if ("continue" if r["checkpoint"] is None else str(r["checkpoint"])) == cp
                ]
            )
        },
    }


def run(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError(
            "Preserve prior/partial output; never overwrite or rerun to improve a result"
        )
    output.mkdir(parents=True)
    started = time.monotonic()
    try:
        design = contract()
        pins = verify_inputs()
        source_hashes = {p.name: sha(p) for p in SOURCE.iterdir() if p.is_file()}
        packages = versions()
        expected_versions = dict(
            line.strip().split("==")
            for line in (SOURCE / "requirements.txt").read_text().splitlines()
            if line.strip()
        )
        if packages["packages"] != expected_versions:
            raise ValueError("Isolated dependency versions differ from frozen requirements")
        tests = read(BASE / "local-checks.json")
        if tests["status"] != "passed" or tests["source_files_sha256"] != source_hashes:
            raise ValueError("Source differs from locally checked implementation")
        save(
            output / "design-lock.json",
            {
                "contract": design,
                "contract_sha256": sha(SOURCE / "contract.json"),
                "input_pins_sha256": sha(SOURCE / "input-pins.json"),
                "source_files_sha256": source_hashes,
                "runtime": packages,
                "platform": platform.platform(),
                "new_policy_latency": "unmeasured",
                "maximum_scientific_fits": 100,
                "local_checks_sha256": sha(BASE / "local-checks.json"),
            },
        )
        offline_guard(output)
        runtime = load_api()
        data = load(pins)
        groups = sorted(data.folds)
        if Counter(data.folds.values()) != {0: 40, 1: 40, 2: 40, 3: 40, 4: 40}:
            raise ValueError("Outer folds differ")
        save(
            output / "folds.json",
            {
                "outer": data.folds,
                "inner": {
                    str(o): inner_assignment([g for g in groups if data.folds[g] != o], o)
                    for o in range(5)
                },
            },
        )
        baseline_path = common.ROOT / pins["baseline_run"]
        baseline_folds = read(baseline_path / "folds.json")
        if read(output / "folds.json") != baseline_folds:
            raise ValueError("P3c outer/inner groups differ from frozen P3b baseline")
        baseline_totals = {
            phase: {p: {m: [] for m in design["methods"]} for p in design["profiles"]}
            for phase in ["calibrated", "fixed_diagnostic"]
        }
        for path in sorted((baseline_path / "outer-records").glob("*.json")):
            rs = read(path)["rows"]
            first = rs[0]
            baseline_totals[first["phase"]][first["profile"]][first["method"]].extend(rs)
        totals = {
            "calibrated": {p: {m: [] for m in design["methods"]} for p in design["profiles"]},
            "fixed_diagnostic": {p: {m: [] for m in design["methods"]} for p in design["profiles"]},
        }
        selections = []
        for outer in range(5):
            train = [g for g in groups if data.folds[g] != outer]
            held = [g for g in groups if data.folds[g] == outer]
            inner = inner_assignment(train, outer)
            train_ix, held_ix = data.indices(train), data.indices(held)
            train_position = {i: j for j, i in enumerate(train_ix)}
            boot = Bootstrap(train)
            for profile in design["profiles"]:
                for method in design["methods"]:
                    tag = f"{profile}-{method}-outer{outer}"
                    print(
                        json.dumps(
                            {"phase": "nested_fit", "cell": tag, "scientific_fits": common.FITS}
                        ),
                        flush=True,
                    )
                    scores = np.empty((len(train_ix), 8, 2))
                    scores[:, :, 0], scores[:, :, 1] = np.inf, -np.inf
                    seen = set()
                    for fold in range(4):
                        fitting = sorted(g for g in train if inner[g] != fold)
                        validation = sorted(g for g in train if inner[g] == fold)
                        if set(fitting) & (set(validation) | set(held)) or set(validation) & set(
                            held
                        ):
                            raise ValueError("Group leakage")
                        val_ix = data.indices(validation)
                        q, j = np.where(data.reached[val_ix])
                        model, receipt = fit(
                            data, profile, method, fitting, check_x=data.x[profile][val_ix[q], j]
                        )
                        receipt.update(
                            outer_fold=outer,
                            inner_fold=fold,
                            stage="inner",
                            validation_groups=validation,
                            outer_heldout_groups=held,
                        )
                        model_file(output, tag + f"-inner{fold}", model, receipt)
                        scores[[train_position[i] for i in val_ix]] = grid_scores(
                            data, profile, model, val_ix
                        )
                        seen.update(val_ix.tolist())
                    if seen != set(train_ix):
                        raise ValueError("Incomplete inner held-out predictions")
                    trials = []
                    for cap in design["risk_caps"]:
                        for floor in design["benefit_floors_ms"]:
                            decisions = first_actions(scores, cap, floor)
                            trials.append(
                                {
                                    "risk_cap": cap,
                                    "benefit_floor_ms": floor,
                                    "assessment": assess(
                                        outcomes(data, profile, train_ix, decisions),
                                        boot,
                                        all_metrics=False,
                                    ),
                                    "inner_oof_actions": decisions.tolist(),
                                }
                            )
                    chosen = select(trials)
                    choice = {
                        "profile": profile,
                        "method": method,
                        "outer_fold": outer,
                        "training_groups": train,
                        "heldout_groups": held,
                        "chosen": None
                        if chosen is None
                        else {k: chosen[k] for k in ["risk_cap", "benefit_floor_ms"]},
                        "reason": (
                            "No inner candidate qualifies: explicit measured profile continue."
                        )
                        if chosen is None
                        else (
                            "Best inner qualified worst-regime proxy; "
                            "smaller risk cap then higher benefit floor breaks exact ties."
                        ),
                        "trials": trials,
                    }
                    save(output / "selection" / (tag + ".json"), choice)
                    save(
                        output / "inner-predictions" / (tag + ".json"),
                        {
                            "query_ids": [data.meta[i]["query_id"] for i in train_ix],
                            "risk_benefit_scores": [
                                [
                                    [None if not np.isfinite(v) else float(v) for v in pair]
                                    for pair in row
                                ]
                                for row in scores
                            ],
                            "channels": [
                                "predicted_recall_loss_fraction",
                                "predicted_minimum_proxy_saving_ms",
                            ],
                            "unreachable_score_representation": (
                                "Both channels null; excluded from decisions, "
                                "never imputed as a feature."
                            ),
                        },
                    )
                    selections.append({k: v for k, v in choice.items() if k != "trials"})
                    q, j = np.where(data.reached[held_ix])
                    model, receipt = fit(
                        data, profile, method, train, check_x=data.x[profile][held_ix[q], j]
                    )
                    receipt.update(
                        outer_fold=outer, inner_fold=None, stage="outer_refit", heldout_groups=held
                    )
                    model_file(output, tag + "-outer-refit", model, receipt)
                    held_scores = grid_scores(data, profile, model, held_ix)
                    for phase in ["calibrated", "fixed_diagnostic"]:
                        if phase == "calibrated" and chosen is None:
                            cap, floor = None, None
                            decisions = np.full(len(held_ix), 8)
                            raw = continue_policy(profile) if method == "shallow_tree" else None
                        else:
                            gates = (
                                design["selection"]["fixed_diagnostic"]
                                if phase == "fixed_diagnostic"
                                else chosen
                            )
                            cap, floor = gates["risk_cap"], gates["benefit_floor_ms"]
                            decisions = first_actions(held_scores, cap, floor)
                            raw = (
                                shallow_policy(model, cap, floor)
                                if method == "shallow_tree"
                                else None
                            )
                        checks = None
                        if raw is not None:
                            checks = verify_shared_interpreter(
                                data, profile, raw, held_ix, decisions, runtime
                            )
                            save(
                                output / "policies" / (tag + "-" + phase + ".json"),
                                {
                                    "policy": raw,
                                    "interpreter_checks": checks,
                                    "scope": (
                                        "Fold-specific development tree only; "
                                        "no native execution, global refit or deployment."
                                    ),
                                },
                            )
                        records = [
                            {
                                **r,
                                "outer_fold": outer,
                                "method": method,
                                "profile": profile,
                                "phase": phase,
                                "risk_cap": cap,
                                "benefit_floor_ms": floor,
                            }
                            for r in outcomes(data, profile, held_ix, decisions)
                        ]
                        totals[phase][profile][method].extend(records)
                        save(
                            output / "outer-records" / (tag + "-" + phase + ".json"),
                            {"rows": records, "interpreter_checks": checks},
                        )
                    save(
                        output / ("progress.json." + str(len(selections))),
                        {"cells_complete": len(selections), "scientific_fits": common.FITS},
                    )
        boot = Bootstrap(groups)
        reports = {
            phase: {
                p: {m: assess(rs, boot) for m, rs in methods.items()}
                for p, methods in profiles.items()
            }
            for phase, profiles in totals.items()
        }
        contrasts = {
            phase: {
                p: paired(methods["extra_trees"], methods["shallow_tree"], boot)
                for p, methods in profiles.items()
            }
            for phase, profiles in totals.items()
        }
        baseline_reports = read(baseline_path / "performance.json")["reports"]
        if {
            phase: {
                p: {m: assess(rs, boot) for m, rs in methods.items()}
                for p, methods in profiles.items()
            }
            for phase, profiles in baseline_totals.items()
        } != baseline_reports:
            raise ValueError("Frozen baseline OOF reports do not reconstruct exactly")
        p3b_contrasts = {
            phase: {
                p: {m: paired(rs, baseline_totals[phase][p][m], boot) for m, rs in methods.items()}
                for p, methods in profiles.items()
            }
            for phase, profiles in totals.items()
        }
        if common.FITS != 100:
            raise ValueError("Finite fit count differs from 80 inner+20 shared outer refits")
        controls = {}
        all_ix = np.arange(600)
        for profile in design["profiles"]:
            controls[profile] = {}
            for label, actions in [
                ("measured_profile_continue", np.full(600, 8)),
                ("fixed_checkpoint128_else_continue", np.where(data.reached[:, 7], 7, 8)),
            ]:
                rs = outcomes(data, profile, all_ix, actions)
                controls[profile][label] = assess(rs, boot)
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
            controls[profile]["analytical_native"] = {
                **assess(native, boot),
                "scope": (
                    "Analytical reference only; "
                    "no new native execution or free serving route claim."
                ),
            }
        branch = {}
        for profile in design["profiles"]:
            shallow = reports["calibrated"][profile]["shallow_tree"]["development_signal"]
            flexible = reports["calibrated"][profile]["extra_trees"]["development_signal"]
            branch[profile] = (
                "investigate_bounded_representation_or_compression"
                if flexible and not shallow
                else "preserve_shallow_family_for_separate_interface_and_actual_latency_contract"
                if shallow
                else (
                    "close_finite_formulation_allowance_"
                    "gate_fresh_development_diversity_or_B1_scope"
                )
            )
        result = {
            "version": design["version"],
            "status": "completed_offline_development_comparison",
            "reports": reports,
            "paired_flexible_minus_shallow": contrasts,
            "paired_p3c_minus_frozen_p3b": p3b_contrasts,
            "baseline_outer_and_inner_folds_match": True,
            "baseline_reports_reconstruct_exactly": True,
            "controls": controls,
            "selections": selections,
            "error_diagnostics": {
                phase: {
                    p: {m: diagnostic_errors(rs) for m, rs in methods.items()}
                    for p, methods in profiles.items()
                }
                for phase, profiles in totals.items()
            },
            "branch": branch,
            "independent_vectors": 200,
            "cases_per_method_profile": 600,
            "scientific_estimator_fits": common.FITS,
            "scientific_fit_limit": 100,
            "calibrated_outer_cells_with_noncontinue_selection": sum(
                v["chosen"] is not None for v in selections
            ),
            "provider_calls": 0,
            "database_calls": 0,
            "torch_allocations": 0,
            "protected_query_values_opened": False,
            "full_data_refit": False,
            "globally_selected_policy": False,
            "actual_new_policy_latency": "unmeasured",
            "canonical_acceptance": False,
            "M1": False,
            "M2": False,
            "M3": False,
            "elapsed_seconds": time.monotonic() - started,
            "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "bootstrap": {
                "samples": 10000,
                "seed": 20261019,
                "unit": "vector; all filters/repetitions/folds clustered",
                "pointwise": True,
            },
            "limitations": [
                (
                    "All 200 vectors previously exposed; "
                    "grouped outer folds do not remove earlier design adaptation."
                ),
                (
                    "Uncertainty conditions on fixed OOF fits; "
                    "training uncertainty not independently resampled."
                ),
                (
                    "Fixed-stop proxy costs do not measure "
                    "a learned tree or composite-session serving latency."
                ),
                (
                    "Finite risk partitions, benefit estimates and pruning procedure "
                    "do not establish a universal information or policy-family ceiling."
                ),
                (
                    "Extra Trees remains an offline diagnostic predictor; "
                    "shallow artifacts have observed interpreter parity only."
                ),
            ],
        }
        save(output / "performance.json", result)
        verify_inputs()
        if any(sha(SOURCE / name) != value for name, value in source_hashes.items()):
            raise ValueError("Implementation changed during campaign")
        files = {str(p.relative_to(output)): sha(p) for p in output.rglob("*") if p.is_file()}
        save(
            output / "verification.json",
            {
                "status": "passed",
                "source_input_preservation": True,
                "files_sha256": files,
                "all_outer_and_inner_groups_disjoint": True,
                "all_inner_candidate_outcomes_retained": True,
                "all_shallow_export_first_stops_match_shared_interpreter": True,
                "full_reached_grid_coverage": 4695,
                "new_labels": 0,
                "scientific_estimator_fits": common.FITS,
                "total_metered_input_and_output_bytes_read": common.READ_BYTES,
                "source_read_limit_bytes": 16 * 1024**3,
                "network_and_child_processes_blocked_during_modeling": True,
                "new_policy_latency": "unmeasured",
            },
        )
        lines = [
            "P3c risk-separated stopping-model comparison — exposed development evidence only",
            "Actual new-policy latency: UNMEASURED; zero provider/database/Torch calls.",
            (
                "profile | method | stops | recall delta | lower95 recall | "
                "activation proxy saved ms | reuse proxy saved ms | development signal"
            ),
        ]
        for p in design["profiles"]:
            for m in design["methods"]:
                report = reports["calibrated"][p][m]
                o = report["overall"]
                lines.append(
                    f"{p} | {m} | {o['stopped_cases']} | {o['recall_delta']:.6f} | "
                    f"{o['recall_delta_ci95'][0]:.6f} | {o['activation_proxy_ms_saved']:.6f} | "
                    f"{o['reuse_proxy_ms_saved']:.6f} | {report['development_signal']}"
                )
        lines.extend(["", "Branch: " + json.dumps(branch, sort_keys=True)])
        (output / "report.txt").write_text("\n".join(lines) + "\n")
        print("\n".join(lines), flush=True)
        print("Verified output: " + str(output), flush=True)
    except Exception as error:
        if not (output / "failure.json").exists():
            save(
                output / "failure.json",
                {
                    "status": "failed_preserved",
                    "type": type(error).__name__,
                    "error": str(error),
                    "scientific_fits_completed_or_attempted": common.FITS,
                    "elapsed_seconds": time.monotonic() - started,
                    "no_automatic_rerun": True,
                    "provider_database_Torch_calls": 0,
                },
            )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=BASE / "runs" / ("p3c-" + timestamp()))
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        run(args.output)
