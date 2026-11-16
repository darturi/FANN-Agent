"""Frozen paired full-serving cost library and complete prefix evidence; no policy selection."""

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
import argparse
import json
from pathlib import Path

import numpy as np
from common import require, sha, write
from m1_design import ARMS, FEATURES, FILTERS, GROUPS, cpu_for
from m1_verify import lines


def analyse(results, kit):
    verified = json.loads((results / "local-verification.json").read_text())
    fixture = verified["status"] == "M1_fixture_return_verified_not_study_evidence"
    require(
        fixture or verified["status"] == "M1_runtime_prefix_cost_return_verified",
        "verify return before analysis",
    )
    queries = list(lines(kit / "queries.jsonl"))
    groups = sorted(
        {q["id"].rsplit("-", 1)[0] for q in queries},
        key=lambda name: int(name.rsplit("-v", 1)[1]),
    )
    gi = {g: i for i, g in enumerate(groups)}
    cpus = json.loads((results / "timing/allowed-cpus.json").read_text())
    require(len(cpus) == len(set(cpus)) == 4, "four physical CPUs required")
    arrays = [np.full((len(groups), 7, 4, 2, len(names)), np.nan) for names in GROUPS]
    for r in lines(results / "timing/timing.jsonl"):
        g = r["group"]
        key = (
            gi[r["id"].rsplit("-", 1)[0]],
            FILTERS.index(r["filter"]),
            r["reader"],
            r["cycle"],
            GROUPS[g].index(r["family"]),
        )
        require(np.isnan(arrays[g][key]), "duplicate timing tensor cell")
        arrays[g][key] = r["request_ns"] / 1e6
    require(all(np.all(np.isfinite(a)) for a in arrays), "incomplete timing tensor")
    rng = np.random.default_rng(20261116)
    draws = 20000
    sampled = [[] for _ in GROUPS]
    scalar = [a[:, 1:].mean(axis=(1, 2, 3)) for a in arrays]
    for _ in range(40):
        weights = rng.multinomial(len(groups), np.full(len(groups), 1 / len(groups)), size=500)
        for group, values in enumerate(scalar):
            sampled[group].append(weights @ values / len(groups))
    boot = [np.concatenate(parts) for parts in sampled]
    summaries = {}
    for group, names in enumerate(GROUPS):
        a = arrays[group]
        means = a.mean(axis=(0, 2, 3))
        primary = scalar[group].mean(axis=0)
        cpu_primary = {}
        for cpu in cpus:
            per_filter = []
            for ti in range(1, len(FILTERS)):
                reader = next(r for r in range(4) if cpu_for(r, ti, group, cpus) == cpu)
                per_filter.append(a[:, ti, reader, :, :].mean(axis=(0, 1)))
            cpu_primary[cpu] = np.mean(per_filter, axis=0)
        stats = {}
        for fi, name in enumerate(names):
            ratio = boot[group][:, fi] / boot[group][:, 0]
            stats[name] = {
                "equal_scalar_mean_ms": float(primary[fi]),
                "per_filter_mean_ms": {
                    str(t): float(means[ti, fi]) for ti, t in enumerate(FILTERS)
                },
                "ratio_to_same_block_native": float(primary[fi] / primary[0]),
                "native_ratio_conditional95pct_interval": np.quantile(
                    ratio, [0.025, 0.975]
                ).tolist(),
                "per_reader_primary_native_ratio": {
                    str(r): float(a[:, 1:, r, :, fi].mean() / a[:, 1:, r, :, 0].mean())
                    for r in range(4)
                },
                "per_cpu_primary_mean_ms": {
                    str(cpu): float(values[fi]) for cpu, values in cpu_primary.items()
                },
                "per_cpu_primary_native_ratio": {
                    str(cpu): float(values[fi] / values[0]) for cpu, values in cpu_primary.items()
                },
                "per_cycle_primary_native_ratio": {
                    str(c): float(a[:, 1:, :, c, fi].mean() / a[:, 1:, :, c, 0].mean())
                    for c in (0, 1)
                },
            }
            if group < 3 and name.startswith("v2_"):
                matched = 3
                relative = boot[group][:, fi] / boot[group][:, matched]
                stats[name]["ratio_to_matched_continue"] = float(primary[fi] / primary[matched])
                stats[name]["matched_ratio_conditional95pct_interval"] = np.quantile(
                    relative, [0.025, 0.975]
                ).tolist()
        summaries[str(group)] = {
            "families": stats,
            "native_anchor_not_pooled_across_blocks": True,
            "reader_slot_limit": "Reader slots map to different physical CPUs and PIDs across "
            "filter blocks; use per_cpu summaries for physical CPU consistency.",
        }
    # Within the single calibration block: do not subtract unpaired cross-block/control gaps.
    component_pairs = (
        ("decision_plan_minus_native", 1, 0),
        ("count_plan_minus_decision_plan", 2, 1),
        ("ranked_plan_minus_count_plan", 3, 2),
        ("turnover_plan_minus_ranked_plan", 4, 3),
        ("four_compare_plan_minus_turnover_plan", 5, 4),
    )
    differences = {}
    for name, hi, lo in component_pairs:
        if hi is None:
            continue
        samples = boot[3][:, hi] - boot[3][:, lo]
        differences[name] = {
            "mean_complete_request_difference_ms": float(
                scalar[3][:, hi].mean() - scalar[3][:, lo].mean()
            ),
            "conditional95pct_interval_ms": np.quantile(samples, [0.025, 0.975]).tolist(),
            "definition": "Paired difference of complete compiled serving plans; includes "
            "dispatch, conditions and cache effects, not an isolated "
            "pure-operation timer.",
            "negative_estimates_retained": True,
        }
    work_means = {}
    for t in FILTERS:
        by = {name: [] for name in ARMS}
        for r in lines(results / "work/work.jsonl"):
            if r["filter"] == t:
                by[r["family"]].append(r["counts"])
        work_means[str(t)] = {
            name: {
                k: sum(c[k] for c in rows) / len(rows)
                for k in rows[0]
                if k not in ("pid", "start_cpu", "end_cpu")
            }
            for name, rows in by.items()
        }
    report = {
        "status": "M1_fixture_cost_library_only"
        if fixture
        else "M1_measured_serving_cost_library_pending_scheduler_and_M2_binding",
        "runtime_profile": verified["runtime_profile"],
        "timing_groups": summaries,
        "paired_complete_plan_differences": differences,
        "work_counter_means": work_means,
        "uncertainty": (
            f"{draws} paired exposed-vector group bootstrap draws, seed20261116; "
            "conditional on one allocation, preserving all filter/reader/cycle/family/group pairs."
        ),
        "cost_limits": "No cross-block control-gap subtraction, negative clipping, "
        "hidden threshold fitter, automatic additive-model qualification "
        "or inference that a new program has already achieved these "
        "latencies. Primary times exclude instrumented work-stage times "
        "and setup/lifecycle costs.",
        "final_policy_selected": False,
        "provider_calls": 0,
        "validation_test_outcomes_opened": False,
    }
    write(results / "serving-cost-library.json", report)
    fold_map = {} if fixture else json.loads((kit / "fold-map.json").read_text())
    evidence = []
    for r in lines(results / "timing/quality.jsonl"):
        group = r["id"].rsplit("-", 1)[0]
        ordinal = gi[group]
        source = group.removeprefix("reviews-clean-v")
        evidence.append(
            {
                "group": ordinal,
                "fold": ordinal % 5 if fixture else fold_map[source],
                "filter": "unfiltered" if r["filter"] < 0 else "votes" + str(r["filter"]),
                "native_recall": r["results"]["native640"]["recall"],
                "native_count": r["results"]["native640"]["returned_count"],
                "observations": {
                    str(o["checkpoint"]): {k: o[k] for k in FEATURES} for o in r["checkpoints"]
                },
                "proofs": {
                    cp: {"recall": p["recall"], "returned_count": p["returned_count"]}
                    for cp, p in r["prefixes"].items()
                },
            }
        )
    bundle = {
        "schema": "filtered-ann-evidence.v2",
        "scope": "development",
        "runtime_profile": verified["runtime_profile"],
        "cost_status": "unqualified_pending_M2_serving_cost_model_binding",
        "rows": evidence,
        "source_verification_sha256": sha(results / "local-verification.json"),
        "source_cost_library_sha256": sha(results / "serving-cost-library.json"),
        "fixture_only": fixture,
        "limits": "Actual qualified full/partial prefix labels; cost library is "
        "empirical complete-request evidence, not an automatically "
        "qualified additive estimator.",
    }
    write(results / "development-prefix-evidence.json", bundle)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--kit", type=Path, required=True)
    a = p.parse_args()
    r = analyse(a.results, a.kit)
    print(
        json.dumps(
            {
                "status": r["status"],
                "groups": len(r["timing_groups"]),
                "final_policy_selected": False,
            },
            indent=2,
        )
    )
