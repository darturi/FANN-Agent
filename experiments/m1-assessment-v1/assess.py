"""Independent reconstruction of the sealed M1 return and ID-normalized evidence export.

The original packaged analysis and its failed export log remain unchanged. No search,
provider call, policy fitting or protected outcome is needed here.
"""

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path

import numpy as np

FILTERS = (-1, 743, 527, 310, 192, 108, 32)
GRAPH = (
    "vector_calls",
    "layer0_neighbor_scores",
    "upper_neighbor_scores",
    "layer0_queue_pops",
    "layer0_adjacencies_examined",
)
CONTINUE = (
    "native640",
    "legacy_noop",
    "empty",
    "matched_conservative",
    "matched_moderate",
    "matched_broad",
    "decision_continue",
    "count_continue",
    "ranked_continue",
    "turnover_continue",
    "four_compare_continue",
)
FEATURES = ("qualifying_count", "tenth_distance", "frontier_gap", "top10_new_since_previous")


def lines(path):
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def source_key(group):
    """Fold keys are canonical integers; query IDs retain their original padding."""
    return str(int(group.removeprefix("reviews-clean-v")))


def assess(results, kit):
    verified = json.loads((results / "local-verification.json").read_text())
    analysis = json.loads((results / "serving-cost-library.json").read_text())
    assert verified["status"] == "M1_runtime_prefix_cost_return_verified"
    assert analysis["status"] == "M1_measured_serving_cost_library_pending_scheduler_and_M2_binding"
    binding = json.loads((kit / "binding.json").read_text())
    plan = json.loads((kit / "m1-plan.json").read_text())
    job = verified["job_id"]
    downloads = results.parents[1]
    scheduler_file = downloads / f"M1-{job}-sacct.txt"
    scheduler = [
        line.split() for line in scheduler_file.read_text().splitlines()[2:] if line.strip()
    ]
    assert len(scheduler) == 4 and scheduler[0][0] == job
    assert all(row[0].startswith(job) and row[1:3] == ["COMPLETED", "0:0"] for row in scheduler)
    startup = {}
    for phase in ("timing", "work"):
        path = downloads / f"M1-{job}-preflight-{phase}.json"
        r = json.loads(path.read_text())
        assert r["status"] == "M1_native_startup_preflight_passed"
        assert r["backend_import_exercised"] and r["search_attempts"] == 0
        assert r["module_sha256"] == binding[phase + "_module_sha256"]
        assert r["programs_sha256"] == binding["programs_sha256"]
        assert r["runtime_profile"] == binding["runtime_profile"]
        assert r["provider_calls"] == 0 and not r["validation_test_outcomes_opened"]
        startup[phase] = {"sha256": sha(path), "full_backend_preflight_passed": True}
    names = plan["timing_groups"]
    cpus = json.loads((results / "timing/allowed-cpus.json").read_text())
    groups = sorted(
        {q["id"].rsplit("-", 1)[0] for q in lines(kit / "queries.jsonl")},
        key=lambda g: int(source_key(g)),
    )
    gi = {g: i for i, g in enumerate(groups)}
    folds = json.loads((kit / "fold-map.json").read_text())
    assert len(groups) == len(folds) == 450
    assert set(folds) == {source_key(g) for g in groups}
    assert set(map(int, folds)) == set(binding["development_source_indices"])
    # Exercise the real export failure and equivalence of padded/unpadded IDs.
    assert source_key("reviews-clean-v0126") == source_key("reviews-clean-v126") == "126"
    assert all(int(g.rsplit("-v", 1)[1]) == int(source_key(g)) for g in groups)
    sums = collections.Counter()
    counts = collections.Counter()
    vector_ns = [np.zeros((450, len(block)), dtype=np.int64) for block in names]
    timed = 0
    for r in lines(results / "timing/timing.jsonl"):
        assert r["request_ns"] == r["construction_ns"] + r["sql_fetch_decode_ns"] > 0
        key = r["group"], r["filter"], r["family"], r["cpu"], r["cycle"]
        sums[key] += r["request_ns"]
        counts[key] += 1
        if r["filter"] >= 0:
            vector_ns[r["group"]][
                gi[r["id"].rsplit("-", 1)[0]], names[r["group"]].index(r["family"])
            ] += r["request_ns"]
        timed += 1
    assert timed == 781200 and set(counts.values()) == {450}
    assert len(counts) == sum(map(len, names)) * 7 * 4 * 2

    def mean(group, name, conditions=FILTERS[1:], selected_cpus=cpus, cycles=(0, 1)):
        selected = [
            (group, t, name, c, e) for t in conditions for c in selected_cpus for e in cycles
        ]
        return sum(sums[k] for k in selected) / sum(counts[k] for k in selected) / 1e6

    comparisons = 0

    def equal(a, b):
        nonlocal comparisons
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), (a, b)
        comparisons += 1

    summaries = {}
    for group, block in enumerate(names):
        stats = {}
        for name in block:
            s = analysis["timing_groups"][str(group)]["families"][name]
            ms = mean(group, name)
            equal(ms, s["equal_scalar_mean_ms"])
            equal(ms / mean(group, "native640"), s["ratio_to_same_block_native"])
            for t in FILTERS:
                equal(mean(group, name, [t]), s["per_filter_mean_ms"][str(t)])
            for cpu in cpus:
                equal(
                    mean(group, name, selected_cpus=[cpu]), s["per_cpu_primary_mean_ms"][str(cpu)]
                )
                equal(
                    mean(group, name, selected_cpus=[cpu])
                    / mean(group, "native640", selected_cpus=[cpu]),
                    s["per_cpu_primary_native_ratio"][str(cpu)],
                )
            for cycle in (0, 1):
                equal(
                    mean(group, name, cycles=[cycle]) / mean(group, "native640", cycles=[cycle]),
                    s["per_cycle_primary_native_ratio"][str(cycle)],
                )
            ci = s["native_ratio_conditional95pct_interval"]
            stats[name] = {
                **s,
                "speedup_vs_native_pct": 100 * (1 - s["ratio_to_same_block_native"]),
                "conditional95pct_speedup_interval_pct": [100 * (1 - ci[1]), 100 * (1 - ci[0])],
            }
        summaries[str(group)] = stats
    # Independent single weight matrix, rather than the packaged chunked tensor computation.
    weights = np.random.default_rng(20261116).multinomial(450, np.full(450, 1 / 450), size=20000)
    boots = []
    for group, block in enumerate(names):
        values = vector_ns[group] / (6 * 4 * 2) / 1e6
        samples = weights @ values / 450
        boots.append(samples)
        for fi, name in enumerate(block):
            interval = np.quantile(samples[:, fi] / samples[:, 0], [0.025, 0.975])
            for a, b in zip(
                interval,
                analysis["timing_groups"][str(group)]["families"][name][
                    "native_ratio_conditional95pct_interval"
                ],
                strict=True,
            ):
                equal(float(a), b)
            if name.startswith("v2_"):
                interval = np.quantile(samples[:, fi] / samples[:, 3], [0.025, 0.975])
                for a, b in zip(
                    interval,
                    analysis["timing_groups"][str(group)]["families"][name][
                        "matched_ratio_conditional95pct_interval"
                    ],
                    strict=True,
                ):
                    equal(float(a), b)
    for component, hi, lo in (
        ("decision_plan_minus_native", 1, 0),
        ("count_plan_minus_decision_plan", 2, 1),
        ("ranked_plan_minus_count_plan", 3, 2),
        ("turnover_plan_minus_ranked_plan", 4, 3),
        ("four_compare_plan_minus_turnover_plan", 5, 4),
    ):
        s = analysis["paired_complete_plan_differences"][component]
        equal(
            mean(3, names[3][hi]) - mean(3, names[3][lo]), s["mean_complete_request_difference_ms"]
        )
        interval = np.quantile(boots[3][:, hi] - boots[3][:, lo], [0.025, 0.975])
        for a, b in zip(interval, s["conditional95pct_interval_ms"], strict=True):
            equal(float(a), b)
    quality = {}
    oracle = collections.Counter()
    evidence = []
    raw_quality = {}
    for r in lines(results / "timing/quality.jsonl"):
        t = r["filter"]
        native = r["results"]["native640"]["recall"]
        raw_quality[r["id"]] = r["results"]
        for name, v in r["results"].items():
            item = quality.setdefault(
                (t, name),
                {"recalls": [], "losses": 0, "short_outputs": 0, "stops": collections.Counter()},
            )
            item["recalls"].append(v["recall"])
            item["losses"] += v["recall"] < native - 1e-12
            item["short_outputs"] += v["returned_count"] < 10
            item["stops"][str(v["checkpoint"])] += 1
        any_full = any_partial = False
        for proof in r["prefixes"].values():
            partial = proof["returned_count"] < 10
            preserving = proof["recall"] >= native - 1e-12
            oracle["partial_prefixes" if partial else "full_prefixes"] += 1
            oracle["zero_output_prefixes"] += proof["returned_count"] == 0
            if preserving:
                any_partial |= partial
                any_full |= not partial
        oracle["cases_with_any_preserving_prefix"] += any_full or any_partial
        oracle["cases_with_preserving_full_prefix"] += any_full
        oracle["cases_with_preserving_partial_prefix"] += any_partial
        oracle["cases_added_only_by_partial_prefixes"] += any_partial and not any_full
        group = r["id"].rsplit("-", 1)[0]
        evidence.append(
            {
                "group": gi[group],
                "fold": int(folds[source_key(group)]),
                "filter": "unfiltered" if t < 0 else "votes" + str(t),
                "native_recall": native,
                "native_count": r["results"]["native640"]["returned_count"],
                "observations": {
                    str(o["checkpoint"]): {key: o[key] for key in FEATURES}
                    for o in r["checkpoints"]
                },
                "proofs": {
                    cp: {key: p[key] for key in ("recall", "returned_count")}
                    for cp, p in r["prefixes"].items()
                },
            }
        )
    assert len(evidence) == 3150 and oracle["partial_prefixes"] == 1496
    assert oracle["full_prefixes"] == 7940
    work = {}
    totals = collections.Counter()
    for r in lines(results / "work/work.jsonl"):
        c = r["counts"]
        assert c["start_cpu"] == c["end_cpu"] == cpus[FILTERS.index(r["filter"]) % 4]
        work[r["id"], r["family"]] = c
        for name, value in c.items():
            if name not in ("pid", "start_cpu", "end_cpu"):
                totals[r["filter"], r["family"], name] += value
    assert len(work) == 81900
    reference = {r["id"]: r["counts"] for r in lines(kit / "native-work-reference.jsonl")}
    mismatches = collections.Counter()
    for qid in raw_quality:
        for key in GRAPH:
            mismatches["native_to_M0_" + key] += work[qid, "native640"][key] != reference[qid][key]
        for name in CONTINUE:
            for key in GRAPH:
                mismatches["continue_to_native_" + key] += (
                    work[qid, name][key] != work[qid, "native640"][key]
                )
        for old, new in (
            ("legacy_conservative", "v2_conservative"),
            ("legacy_moderate", "v2_moderate"),
            ("legacy_broad", "v2_broad"),
            ("count_stop16", "bare_stop16"),
            ("count_stop32", "bare_stop32"),
            ("count_stop64", "bare_stop64"),
        ):
            for key in GRAPH:
                mismatches["compatible_prefix_" + key] += work[qid, old][key] != work[qid, new][key]
        for name in ("native640", "empty", "decision_continue"):
            assert work[qid, name]["feature_passes"] == work[qid, name]["membership_probes"] == 0
    assert not any(mismatches.values())
    per_condition = {}
    eligible = json.loads((results / "timing/eligibility.json").read_text())
    for t in FILTERS:
        per_condition[str(t)] = {
            "eligible_rows": len(eligible[str(t)]),
            "families": {},
        }
        for name in plan["arms"]:
            q = quality[t, name]
            assert len(q["recalls"]) == 450
            counters = {
                key: totals[t, name, key] / 450
                for key in GRAPH + ("feature_passes", "membership_probes")
            }
            for key, value in counters.items():
                equal(value, analysis["work_counter_means"][str(t)][name][key])
            per_condition[str(t)]["families"][name] = {
                "mean_recall": math.fsum(q["recalls"]) / 450,
                "recall_losses": q["losses"],
                "short_outputs": q["short_outputs"],
                "first_stop_counts": dict(q["stops"]),
                "work_counter_means": counters,
            }
    for name in plan["arms"]:
        assert (
            sum(quality[t, name]["losses"] for t in FILTERS)
            == verified["quality_losses_diagnostic_only_for_probes"][name]
        )
    for t in FILTERS:
        for name in CONTINUE + (
            "legacy_conservative",
            "legacy_moderate",
            "legacy_broad",
            "v2_conservative",
            "v2_moderate",
            "v2_broad",
        ):
            assert quality[t, name]["losses"] == 0
    actual_ledger = {
        "timing": {
            "capture": len(raw_quality),
            "forced_prefix": oracle["partial_prefixes"] + oracle["full_prefixes"],
            "native_bridge": len(raw_quality) * 2,
            "quality_ann": sum(len(v) - 1 for v in raw_quality.values()),
            "reference_exact": sum(1 for _ in lines(results / "timing/exact-reference.jsonl")),
            "timed_ann": timed,
            "warmup_ann": sum(1 for _ in lines(results / "timing/warmup.jsonl")),
        },
        "work": {
            "reference_exact": sum(1 for _ in lines(results / "work/exact-reference.jsonl")),
            "work_ann": len(work),
        },
    }
    for phase in ("timing", "work"):
        actual_ledger[phase]["total"] = sum(actual_ledger[phase].values())
    actual_ledger["total"] = actual_ledger["timing"]["total"] + actual_ledger["work"]["total"]
    assert actual_ledger == verified["attempts"] == plan["attempts"]
    assignments = list(lines(results / "timing/assignments.jsonl"))
    visits = collections.Counter(
        (r["filter"], r["group"], r["reader"], r["family"]) for r in assignments
    )
    assert len(assignments) == 1736 and set(visits.values()) == {2}
    backend_count = len({r["pid"] for r in assignments})
    assert backend_count == 7 * 6 * 4
    bundle = {
        "schema": "filtered-ann-evidence.v2",
        "scope": "development",
        "runtime_profile": binding["runtime_profile"],
        "cost_status": "unqualified_pending_M2_serving_cost_model_binding",
        "rows": evidence,
        "source_verification_sha256": sha(results / "local-verification.json"),
        "source_cost_library_sha256": sha(results / "serving-cost-library.json"),
        "fixture_only": False,
        "export_repair": "Fold lookup normalizes source-index padding only; original query IDs, "
        "group ordering, labels, features and measured costs unchanged. "
        "Packaged export failure retained.",
        "limits": "Actual qualified full/partial labels and empirical complete-request costs. "
        "No automatically qualified additive estimator or unmeasured-program latency claim.",
    }
    export = results / "development-prefix-evidence.json"
    assert not export.exists(), "preserve previous export"
    write(export, bundle)
    out = {
        "schema": "fannagent.M1-independent-assessment.v1",
        "status": "M1_original_graph_runtime_labels_and_measured_cost_library_verified",
        "job_id": job,
        "scheduler_rows": scheduler,
        "scheduler_sha256": sha(scheduler_file),
        "native_preflights": startup,
        "timing_records_reconstructed": timed,
        "aggregate_and_bootstrap_checks": comparisons,
        "work_queries_reconstructed": len(work),
        "assignments": len(assignments),
        "timing_backend_PIDs": backend_count,
        "physical_CPU_ids": cpus,
        "role_repetitions_per_backend": 2,
        "attempts": actual_ledger,
        "runtime_profile": binding["runtime_profile"],
        "primary_same_block_summaries": summaries,
        "paired_complete_plan_differences": analysis["paired_complete_plan_differences"],
        "per_condition_quality_and_work": per_condition,
        "per_query_graph_counter_mismatches": dict(mismatches),
        "prefix_opportunity_diagnostic_only": dict(oracle),
        "prefix_opportunity_limits": "Finite exposed-development raw-native-relative oracle; "
        "not an executable policy, absolute high-recall guarantee or measured speedup.",
        "export_repair": bundle["export_repair"],
        "export_sha256": sha(export),
        "cost_status": bundle["cost_status"],
        "scoring_and_scope": {
            "development_groups": 450,
            "scalar_filters": 6,
            "unfiltered_control": True,
            "offline_exact_queries": 6300,
            "exact_serving_calls": 0,
            "validation_test_outcomes_opened": False,
            "provider_calls": 0,
        },
        "limits": "One allocation and exposed development. Bootstrap retains vector/filter/CPU/"
        "cycle/plan-block pairing. Do not pool native across blocks, add context-dependent plan "
        "differences as universal operation costs, or promote a final policy.",
        "provenance": {
            "kit_binding_sha256": sha(kit / "binding.json"),
            "verification_sha256": sha(results / "local-verification.json"),
            "cost_library_sha256": sha(results / "serving-cost-library.json"),
            "packaged_analysis_sha256": sha(kit / "m1_analyse.py"),
            "preserved_failed_analysis_log_sha256": sha(results.parent / "analysis.log"),
            "assessment_source_sha256": sha(Path(__file__)),
        },
    }
    write(results / "independent-assessment.json", out)
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--kit", type=Path, required=True)
    a = p.parse_args()
    out = assess(a.results, a.kit)
    print(
        json.dumps(
            {
                k: out[k]
                for k in (
                    "status",
                    "job_id",
                    "aggregate_and_bootstrap_checks",
                    "attempts",
                    "prefix_opportunity_diagnostic_only",
                )
            },
            indent=2,
        )
    )
