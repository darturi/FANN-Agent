"""Paired full-request nominee costs on development; no final policy selection."""

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
import argparse
import json
from pathlib import Path

import numpy as np
from common import require, write
from m5_design import ARMS, FILTERS, GROUPS, MATCHED, cpu_for
from m5_verify import lines


def analyse(results, kit):
    verified = json.loads((results / "local-verification.json").read_text())
    fixture = verified["status"] == "M5_fixture_return_verified_not_study_evidence"
    require(
        fixture or verified["status"] == "M5_nominee_return_verified",
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
    sampled_filters = [[] for _ in GROUPS]
    scalar = [a[:, 1:].mean(axis=(1, 2, 3)) for a in arrays]
    filter_values = [a.mean(axis=(2, 3)) for a in arrays]
    for _ in range(40):
        weights = rng.multinomial(len(groups), np.full(len(groups), 1 / len(groups)), size=500)
        for group, values in enumerate(scalar):
            sampled[group].append(weights @ values / len(groups))
            flat = filter_values[group].reshape(len(groups), -1)
            sampled_filters[group].append(
                (weights @ flat / len(groups)).reshape(500, 7, len(GROUPS[group]))
            )
    boot = [np.concatenate(parts) for parts in sampled]
    boot_filters = [np.concatenate(parts) for parts in sampled_filters]
    require(
        all(np.allclose(b, f[:, 1:].mean(axis=1)) for b, f in zip(boot, boot_filters, strict=True)),
        "primary/filter bootstrap pairing differs",
    )
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
            stats[name]["per_filter_native_ratio"] = {
                str(t): float(means[ti, fi] / means[ti, 0]) for ti, t in enumerate(FILTERS)
            }
            stats[name]["per_filter_native_ratio_conditional95pct_interval"] = {
                str(t): np.quantile(
                    boot_filters[group][:, ti, fi] / boot_filters[group][:, ti, 0], [0.025, 0.975]
                ).tolist()
                for ti, t in enumerate(FILTERS)
            }
            if name in MATCHED:
                matched = names.index(MATCHED[name])
                relative = boot[group][:, fi] / boot[group][:, matched]
                stats[name]["ratio_to_matched_continue"] = float(primary[fi] / primary[matched])
                stats[name]["matched_ratio_conditional95pct_interval"] = np.quantile(
                    relative, [0.025, 0.975]
                ).tolist()
                stats[name]["per_filter_matched_continue_ratio"] = {
                    str(t): float(means[ti, fi] / means[ti, matched])
                    for ti, t in enumerate(FILTERS)
                }
                stats[name]["per_filter_matched_ratio_conditional95pct_interval"] = {
                    str(t): np.quantile(
                        boot_filters[group][:, ti, fi] / boot_filters[group][:, ti, matched],
                        [0.025, 0.975],
                    ).tolist()
                    for ti, t in enumerate(FILTERS)
                }
        summaries[str(group)] = {
            "families": stats,
            "native_anchor_not_pooled_across_blocks": True,
            "reader_slot_limit": "Reader slots map to different physical CPUs and PIDs across "
            "filter blocks; use per_cpu summaries for physical CPU consistency.",
        }
    empty = GROUPS[0].index("empty")
    empty_interval = np.quantile(boot[0][:, empty] / boot[0][:, 0], [0.05, 0.95]).tolist()
    equivalence = {
        "ratio_band": [0.98, 1.02],
        "conditional90pct_interval": empty_interval,
        "status": "equivalent_within_2pct"
        if empty_interval[0] >= 0.98 and empty_interval[1] <= 1.02
        else "inconclusive_or_outside_band_no_automatic_repeat",
    }
    rankings = []
    for name in MATCHED:
        stats = summaries["0"]["families"][name]
        native_ci = stats["native_ratio_conditional95pct_interval"]
        matched_ci = stats["matched_ratio_conditional95pct_interval"]
        credible = (
            native_ci[1] < 1
            and matched_ci[1] < 1
            and equivalence["status"] == "equivalent_within_2pct"
        )
        rankings.append(
            {
                "candidate": name,
                "ratio_to_native": stats["ratio_to_same_block_native"],
                "ratio_to_matched_continue": stats["ratio_to_matched_continue"],
                "interpretation": "development_signal_for_independent_confirmation"
                if credible
                else "no_credible_net_development_benefit_established",
            }
        )
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
        "status": "M5_fixture_analysis_only"
        if fixture
        else "M5_development_nominee_timing_pending_scheduler_gate",
        "runtime_profile": verified["runtime_profile"],
        "timing_groups": summaries,
        "empty_native_diagnostic": equivalence,
        "nominee_assessment": rankings,
        "work_counter_means": work_means,
        "uncertainty": (
            f"{draws} paired exposed-vector group bootstrap draws, seed20261116; "
            "conditional on one allocation, preserving all filter/reader/cycle/family/group pairs."
        ),
        "cost_limits": "Development-only, one allocation and two cycles; intervals reflect vector "
        "sampling, not allocation variability or held-out generalization. Primary complete-request "
        "times exclude setup and separate instrumented work. Raw negative or noisy contrasts "
        "retained; no threshold fitting, control-gap subtraction, automatic promotion or retry.",
        "final_policy_selected": False,
        "native_remains_admissible": True,
        "provider_calls": 0,
        "validation_test_outcomes_opened": False,
    }
    write(results / "nominee-assessment.json", report)
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
                "native_remains_admissible": True,
            },
            indent=2,
        )
    )
