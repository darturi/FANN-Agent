"""Independently verify native answers, execution audits and timing coverage."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np


def read(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open() as handle:
        yield from map(json.loads, handle)


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def timer(row):
    assert row["request_ns"] > 0 and row["construction_ns"] >= 0 and row["sql_fetch_decode_ns"] > 0
    assert row["request_ns"] == row["construction_ns"] + row["sql_fetch_decode_ns"]
    assert row["returned_count"] == len(row["output"])


def verify(results, kit):
    from broad_benchmark import ARMS, FAMILIES, quality_required, schedule
    from broad_contract import compile_graph
    from broad_support import replay_graph, verify_audit
    from common import matches, threshold
    from m5_experiment import expected_program
    from oracle_design import FILTERS, group, validate_output
    from variants_benchmark import expected as legacy_expected

    receipt = read(results / "receipt.json")
    assert receipt["status"] == "broad_oracle_benchmark_complete"
    assert receipt["binding_sha256"] == sha(kit / "binding.json")
    assert receipt["module_sha256"] == sha(kit / "oracle-module.so")
    binding = read(kit / "binding.json")
    plan = read(kit / "timing-plan.json")
    if plan.get("explicit_user_resume"):
        resumed = read(kit / "resume-plan.json")
        cancelled = read(kit / "prior-cancelled-accounting.json")
        assert resumed["explicit_user_resume"] and resumed["no_partial_timings_used"]
        assert cancelled["job_id"] == plan["prior_cancelled_job_id"] == "23648495"
        assert "CANCELLED" in cancelled["accounting"].splitlines()[0]
        prior_seconds = max(int(r.split("|")[4]) for r in cancelled["accounting"].splitlines())
        assert prior_seconds == plan["prior_cancelled_elapsed_seconds"] == 122
        assert cancelled["result_inventory"] == ["exposure.json", "host-exit.json"]
        assert all(
            cancelled["results_metadata"][n] is None
            for n in (
                "attempts.json",
                "reservation.json",
                "reservation.pending",
                "reservation-final.json",
            )
        )
        assert resumed["prior_extra_ann_attempts"] == resumed["prior_extra_ann_reservations"] == 0
        for name, digest in resumed["policy_and_measurement_inputs_unchanged"].items():
            assert sha(kit / name) == digest, name
        assert plan["aggregate_max_seconds"] <= plan["aggregate_allocation_cap_seconds"] == 21600
        assert receipt["prior_cancelled_elapsed_seconds"] == prior_seconds
        assert receipt["explicit_user_resume"]
    prior_failed_charge = 0
    if plan.get("supervised_validation_repair"):
        from prepare_repair import measurement_ast

        failure = read(kit / "prior-failed-accounting.json")
        resumed = read(kit / "resume-plan.json")
        assert failure["job_id"] == plan["prior_failed_job_id"] == "23716630"
        assert failure["accounting"].splitlines()[0].split("|")[1:3] == ["FAILED", "1:0"]
        assert max(int(r.split("|")[4]) for r in failure["accounting"].splitlines()) == 207
        assert (
            receipt["prior_failed_elapsed_seconds"] == plan["prior_failed_elapsed_seconds"] == 207
        )
        prior_failed_charge = failure["extra_reserved_queries_charged"]
        assert prior_failed_charge == plan["prior_failed_extra_reserved_queries"] == 1024
        assert not failure["quality_or_latency_samples_collected"]
        original = kit.parent / "benchmark-kit-v2/broad_benchmark.py"
        assert sha(original) == resumed["prior_benchmark_source_sha256"]
        assert sha(kit / "broad_benchmark.py") == resumed["repaired_benchmark_source_sha256"]
        assert (
            measurement_ast(original)
            == measurement_ast(kit / "broad_benchmark.py")
            == resumed["primary_measurement_ast_unchanged"]
        )
    assert receipt["graph"] == binding["graph"] and receipt["data_index_before_after"]
    assert (
        receipt["fresh_exact_queries"]
        == receipt["exact_serving_calls"]
        == receipt["provider_calls"]
        == 0
    )
    assert read(results / "host-exit.json") == {"job_id": receipt["job_id"], "exit_code": 0}
    for name, digest in binding["files"].items():
        assert sha(kit / name) == digest, name
    for name, digest in receipt["raw_sha256"].items():
        assert sha(results / name) == digest, name
    freeze = read(results / "policy-freeze.json")
    assert not freeze["timing_started"] and freeze["quality_sha256"] == sha(
        results / "quality.jsonl"
    )
    assert freeze["compiled_v3_sha256"] == sha(kit / "compiled-v3.json")
    assert freeze["compiled_v2_sha256"] == sha(kit / "compiled-programs.json")
    assert (
        freeze["source_cases_sha256"]
        == sha(kit / "source-cases.jsonl")
        == read(kit / "source-capture-freeze.json")["cases_sha256"]
    )
    frontier = read(results / "frontier-qualification.json")
    assert frontier["cases"] == 7000 and frontier["all_prefix_chains_match"]
    assert frontier["frames"] == read(kit / "source-capture-freeze.json")["frames"]
    assert frontier["all_frontier_values_match"] and frontier["all_work_values_match"]
    if plan.get("supervised_validation_repair"):
        assert frontier["canonical_projection"] == "max(0,min(2,canonical_raw_cosine))"
        assert frontier["boundary_roundoff_max_abs"] <= frontier["roundoff_envelope"] == 1e-6
    queries = list(rows(kit / "queries.jsonl"))
    qmap = {q["id"]: q for q in queries}
    cases = {r["id"]: r for r in rows(kit / "source-cases.jsonl")}
    legacy = {r["id"]: r for r in rows(kit / "legacy-cases.jsonl")}
    roles = read(kit / "query-roles.json")
    truth = {r["id"]: r["output"] for r in rows(results / "exact-reference.jsonl")}
    assert len(queries) == len(qmap) == freeze["cases"] == 7000
    assert set(qmap) == set(cases) == set(legacy) == set(roles) == set(truth)
    eligible = {int(t): set(ids) for t, ids in read(results / "eligibility.json").items()}
    assert eligible == {
        int(t): set(ids) for t, ids in read(kit / "source-eligibility.json").items()
    }
    entries = {r["arm"]: r for r in read(kit / "compiled-programs.json")["bindings"]}
    broad_entries = {r["arm"]: r for r in read(kit / "compiled-v3.json")["bindings"]}
    assert set(entries) == {20, 21, 30, 31, 43} and set(broad_entries) == {60, 61, 70, 71, 85}
    for arm in (60, 61):
        assert broad_entries[arm]["policy"] == broad_entries[arm + 10]["policy"]
        assert (
            not broad_entries[arm]["force_continue"] and broad_entries[arm + 10]["force_continue"]
        )
    graphs = {arm: compile_graph(b["policy"]) for arm, b in broad_entries.items()}
    quality = {}
    for r in rows(results / "quality.jsonl"):
        key = r["id"], r["family"]
        assert key not in quality and r["id"] in qmap and r["family"] in FAMILIES
        source = cases[r["id"]]
        family = r["family"]
        arm = ARMS[family]
        assert r["role"] == source["role"] == roles[r["id"]]
        assert r["filter"] == source["filter"] == threshold(qmap[r["id"]])
        if arm is not None and arm >= 60:
            cp, trace = replay_graph(
                graphs[arm], source, force_continue=broad_entries[arm]["force_continue"], trace=True
            )
            assert r["checkpoint"] == cp
            verify_audit(trace, r["audit"])
        elif family in ("native_clone", "empty_v2"):
            cp, wanted = 0, source["native"]
            assert r["checkpoint"] == cp and matches(r["output"], wanted)
        else:
            cp, wanted = legacy_expected(legacy[r["id"]], family, entries)
            assert r["checkpoint"] == cp and matches(r["output"], wanted)
        if arm in (20, 21, 43):
            old = legacy[r["id"]]
            observations = [
                old["observations"][str(p)] for p in (16, 32, 64) if str(p) in old["observations"]
            ]
            assert (
                expected_program(entries[arm], r["filter"], observations, r["output"], r["audit"])
                == cp
            )
        if (
            family in ("matched_broad_full", "matched_broad_test", "empty_v3")
            or r["checkpoint"] == 0
        ):
            assert matches(r["output"], source["native"])
        score = validate_output(r["output"], eligible[r["filter"]], truth[r["id"]])
        assert abs(score - r["recall"]) < 1e-12
        assert r["quality_required"] == quality_required(source, family)
        assert not r["quality_required"] or score + 1e-12 >= source["native_recall"]
        timer(r)
        quality[key] = r
    assert len(quality) == 7000 * 12
    # Independently match each fitted cohort to the frozen actual prefix choices.
    for cohort, family in (("full_workload", "broad_full"), ("heldout_test", "broad_test")):
        for choice in rows(kit / (cohort + "-choices.jsonl")):
            actual = quality[choice["id"], family]
            assert actual["checkpoint"] == choice["checkpoint"] and matches(
                actual["output"], choice["output"]
            )
    cpus = read(results / "allowed-cpus.json")
    assert len(cpus) == len(set(cpus)) == 4
    readers = {}
    for r in rows(results / "reader-setup.jsonl"):
        key = r["filter"], r["reader"]
        assert key not in readers and r["affinity_after"] == [r["cpu"]]
        readers[key] = r
    assert len(readers) == 28
    groups = sorted({group(q["id"]) for q in queries})
    gi = {g: i for i, g in enumerate(groups)}
    values = np.full((len(groups), 7, 4, 12), np.nan)
    routing = np.full_like(values, np.nan)
    cells = (
        cell
        for ti, t in enumerate(FILTERS)
        for cell in schedule([q for q in queries if threshold(q) == t], ti)
    )
    count = 0
    for r, cell in zip(rows(results / "timing.jsonl"), cells, strict=True):
        rotation, position, reader, family, q = cell
        t = threshold(q)
        ti = FILTERS.index(t)
        assert (r["id"], r["filter"], r["rotation"], r["position"], r["reader"], r["family"]) == (
            q["id"],
            t,
            rotation,
            position,
            reader,
            family,
        )
        assignment = readers[t, reader]
        assert (
            r["pid"] == assignment["pid"]
            and r["cpu"] == assignment["cpu"] == cpus[(reader + ti) % 4]
        )
        assert r["role"] == roles[q["id"]]
        actual = quality[q["id"], family]
        assert r["checkpoint"] == actual["checkpoint"] and matches(r["output"], actual["output"])
        timer(r)
        key = gi[group(q["id"])], ti, reader, FAMILIES.index(family)
        assert np.isnan(values[key])
        values[key] = r["request_ns"] / 1e6
        routing[key] = r["oracle_routing_ns_outside_primary"] / 1e6
        count += 1
    assert count == 336000 and np.isfinite(values).all()
    budget = read(kit / "source-capture-budget.json")
    counts = dict(read(kit / "source-capture-receipt.json")["searches"])
    counts["previous_unused_reserved"] = budget["charged_total"] - counts["total"]
    if prior_failed_charge:
        counts["prior_failed_reserved"] = prior_failed_charge
    counts.update(quality_ann=84000, timed_ann=336000, warmup_ann=3360, frontier_qualification=7000)
    transfer = sum(
        r["checkpoint"] > 0 and r["role"] != "test"
        for (qid, f), r in quality.items()
        if f == "broad_test"
    )
    if transfer:
        counts["transfer_prefix"] = transfer
    counts["total"] = sum(v for k, v in counts.items() if k != "total")
    assert receipt["searches"] == read(results / "attempts.json") == counts
    final = read(results / "reservation-final.json")
    assert (
        final["source_charged"] == budget["charged_total"] + prior_failed_charge
        and final["actual_total"] == counts["total"]
    )
    assert final["charged_total"] <= final["cap"] == 2000000
    assert final["unused_charged"] == final["charged_total"] - counts["total"] >= 0
    return groups, roles, cases, quality, values, routing


def report(results, kit):
    from broad_benchmark import FAMILIES
    from oracle_design import FILTERS, group

    groups, roles, cases, quality, values, routing = verify(results, kit)
    test_groups = {group(qid) for qid, role in roles.items() if role == "test"}
    output = {
        "schema": "fannagent.broad-oracle.report.v1",
        "hindsight_fit": True,
        "latency_optimality_proven": False,
        "bootstrap_draws": 20000,
        "bootstrap_seed": 20261118,
        "scope": "Vector-cluster uncertainty conditional on fitted policies and one allocation",
        "cohorts": {},
        "qualification": read(results / "frontier-qualification.json"),
        "analysis_environment": {"python": sys.version, "numpy": np.__version__},
    }
    for cohort in ("full_workload", "heldout_test"):
        selected = [
            i for i, g in enumerate(groups) if cohort == "full_workload" or g in test_groups
        ]
        a = values[selected]
        n = len(selected)
        per_vector = a.mean(axis=2)
        rng = np.random.default_rng(20261118)
        draws = []
        for _ in range(40):
            weights = rng.multinomial(n, np.full(n, 1 / n), size=500)
            draws.append((weights @ per_vector.reshape(n, -1) / n).reshape(500, 7, 12))
        boot = np.concatenate(draws)
        means = per_vector.mean(axis=0)
        narrow = "oracle_feasible_full" if cohort == "full_workload" else "oracle_feasible_test"
        broad = "broad_full" if cohort == "full_workload" else "broad_test"
        chosen = {
            "oracle_ideal": 1,
            "oracle_constrained": 2,
            "oracle_feasible_narrow": FAMILIES.index(narrow),
            "oracle_feasible_broad": FAMILIES.index(broad),
        }
        stats = {}
        for label, filters in (
            ("equal_seven_conditions", list(range(7))),
            ("equal_six_filters", list(range(1, 7))),
            *((str(t), [i]) for i, t in enumerate(FILTERS)),
        ):
            m = means[filters].mean(axis=0)
            b = boot[:, filters].mean(axis=1)
            variants = {}
            for name, index in chosen.items():
                interval = np.quantile(b[:, index] / b[:, 0], [0.025, 0.975])
                variants[name] = {
                    "mean_ms": float(m[index]),
                    "savings_percent": float(100 * (1 - m[index] / m[0])),
                    "savings_percent_conditional95_interval": [
                        float(100 * (1 - interval[1])),
                        float(100 * (1 - interval[0])),
                    ],
                    "per_reader_native_ratio": [
                        float(a[:, filters, r, index].mean() / a[:, filters, r, 0].mean())
                        for r in range(4)
                    ],
                }
            controls = {}
            for name in ("empty_v2", "empty_v3", "native_clone"):
                index = FAMILIES.index(name)
                interval = np.quantile(b[:, index] / b[:, 0], [0.05, 0.95])
                controls[name] = {
                    "native_ratio": float(m[index] / m[0]),
                    "conditional90_interval": interval.tolist(),
                    "within_2pct": bool(interval[0] >= 0.98 and interval[1] <= 1.02),
                }
            difference = (
                100
                * (b[:, chosen["oracle_feasible_narrow"]] - b[:, chosen["oracle_feasible_broad"]])
                / b[:, 0]
            )
            stats[label] = {
                "native_mean_ms": float(m[0]),
                "variants": variants,
                "controls": controls,
                "broad_improvement_percentage_points": variants["oracle_feasible_broad"][
                    "savings_percent"
                ]
                - variants["oracle_feasible_narrow"]["savings_percent"],
                "broad_improvement_percentage_points_conditional95_interval": np.quantile(
                    difference, [0.025, 0.975]
                ).tolist(),
                "matched_broad_mean_ms": float(m[FAMILIES.index("matched_" + broad)]),
                "routing_mean_ms_outside_primary": {
                    name: float(routing[selected][:, filters, :, i].mean())
                    for name, i in (("oracle_ideal", 1), ("oracle_constrained", 2))
                },
            }
        ids = {qid for qid, r in cases.items() if cohort == "full_workload" or r["role"] == "test"}
        quality_stats = {}
        for name, index in chosen.items():
            family = FAMILIES[index]
            by_filter = {}
            for t in FILTERS:
                actual = [quality[qid, family] for qid in ids if cases[qid]["filter"] == t]
                by_filter[str(t)] = {
                    "cases": len(actual),
                    "stops": sum(r["checkpoint"] > 0 for r in actual),
                    "checkpoint_histogram": dict(Counter(r["checkpoint"] for r in actual)),
                    "recall_losses": sum(
                        r["recall"] + 1e-12 < cases[r["id"]]["native_recall"] for r in actual
                    ),
                    "result_count_losses": sum(
                        len(r["output"]) < len(cases[r["id"]]["native"]) for r in actual
                    ),
                    "budget_fallbacks": sum(
                        bool(r["audit"] and r["audit"].get("exhausted")) for r in actual
                    ),
                    "fault_fallbacks": sum(
                        bool(r["audit"] and r["audit"].get("fault")) for r in actual
                    ),
                }
            quality_stats[name] = by_filter
        passed = all(
            all(c["within_2pct"] for c in stats[str(t)]["controls"].values()) for t in FILTERS
        )
        output["cohorts"][cohort] = {
            "vectors": n,
            "cases": len(ids),
            "latency": stats,
            "quality": quality_stats,
            "all_condition_controls_pass": passed,
            "interpretation": "measured hindsight headroom"
            if passed
            else "descriptive estimate; control equivalence not established",
        }
    output["test_policy_outside_cohort_recall_losses"] = {
        name: sum(
            r["recall"] + 1e-12 < cases[qid]["native_recall"]
            for (qid, f), r in quality.items()
            if f == family and r["role"] != "test"
        )
        for name, family in (("narrow", "oracle_feasible_test"), ("broad", "broad_test"))
    }
    (results / "report.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--kit", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.kit.resolve()))
    value = report(args.results, args.kit)
    print(
        json.dumps(
            {c: r["latency"]["equal_seven_conditions"] for c, r in value["cohorts"].items()},
            indent=2,
        )
    )
