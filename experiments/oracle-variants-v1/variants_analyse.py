"""Verify frozen programs, actual answers, schedule and budgets; report both cohorts."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from common import matches, threshold
from m5_experiment import expected_program
from oracle_design import FILTERS, group, require, validate_output
from variants_benchmark import FAMILIES, POINTS, expected, quality_required, schedule


def read(path):
    return json.loads(path.read_text())


def lines(path):
    with path.open() as handle:
        yield from map(json.loads, handle)


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def timer(row):
    require(row["request_ns"] > 0 and row["construction_ns"] >= 0, "invalid request timer")
    require(row["sql_fetch_decode_ns"] > 0, "invalid SQL timer")
    require(
        row["request_ns"] == row["construction_ns"] + row["sql_fetch_decode_ns"],
        "timer accounting differs",
    )
    require(row["returned_count"] == len(row["output"]), "result count differs")


def verify(results, kit, *, fixture=False):
    receipt = read(results / "receipt.json")
    if not fixture:
        binding = read(kit / "binding.json")
        require(receipt["status"] == "oracle_variants_benchmark_complete", "incomplete benchmark")
        require(receipt["binding_sha256"] == sha(kit / "binding.json"), "binding differs")
        require(receipt["module_sha256"] == sha(kit / "oracle-module.so"), "module differs")
        require(receipt["graph"] == binding["graph"], "graph differs")
        require(receipt["data_index_before_after"] is True, "graph not verified")
        require(
            read(results / "host-exit.json") == {"job_id": receipt["job_id"], "exit_code": 0},
            "host failed",
        )
        require(
            receipt["fresh_exact_queries"] == receipt["exact_serving_calls"] == 0,
            "unexpected fresh exact query",
        )
        require(receipt["provider_calls"] == 0, "unexpected provider call")
        for name, digest in binding["files"].items():
            require(sha(kit / name) == digest, "changed input: " + name)
    for name, digest in receipt["raw_sha256"].items():
        require(sha(results / name) == digest, "changed raw output: " + name)
    frozen = read(results / "policy-freeze.json")
    require(frozen["timing_started"] is False, "policies not frozen before timing")
    require(frozen["quality_sha256"] == sha(results / "quality.jsonl"), "quality freeze differs")
    require(
        frozen["compiled_programs_sha256"] == sha(kit / "compiled-programs.json"),
        "compiled policy freeze differs",
    )
    require(
        frozen["source_cases_sha256"] == sha(kit / "source-cases.jsonl"), "source freeze differs"
    )
    for name in (
        "cases.jsonl",
        "capture-freeze.json",
        "capture-receipt.json",
        "capture-budget.json",
    ):
        require(
            sha(results / ("source-" + name)) == sha(kit / ("source-" + name)),
            "changed capture evidence: " + name,
        )
    queries = list(lines(kit / "queries.jsonl"))
    qmap = {q["id"]: q for q in queries}
    cases = {r["id"]: r for r in lines(kit / "source-cases.jsonl")}
    truth = {r["id"]: r["output"] for r in lines(results / "exact-reference.jsonl")}
    roles = read(kit / "query-roles.json")
    require(len(queries) == len(qmap) == frozen["cases"], "duplicate or missing queries")
    require(set(qmap) == set(cases) == set(truth) == set(roles), "case inventory differs")
    require(
        read(kit / "source-capture-freeze.json")["cases_sha256"] == sha(kit / "source-cases.jsonl"),
        "capture freeze differs",
    )
    eligible = {int(t): set(ids) for t, ids in read(results / "eligibility.json").items()}
    require(
        eligible == {int(t): set(ids) for t, ids in read(kit / "source-eligibility.json").items()},
        "eligibility differs",
    )
    entries = {r["arm"]: r for r in read(kit / "compiled-programs.json")["bindings"]}
    require(set(entries) == {20, 21, 30, 31, 43}, "program pool differs")
    for arm, matched in ((20, 30), (21, 31)):
        require(entries[arm]["policy"] == entries[matched]["policy"], "matched policy differs")
        require(
            not entries[arm]["force_continue"] and entries[matched]["force_continue"],
            "matched control differs",
        )
    quality = {}
    for r in lines(results / "quality.jsonl"):
        key = r["id"], r["family"]
        require(
            key not in quality and r["id"] in cases and r["family"] in FAMILIES,
            "duplicate or unknown quality row",
        )
        row = cases[r["id"]]
        require(r["role"] == row["role"] == roles[r["id"]], "role differs")
        require(r["filter"] == row["filter"] == threshold(qmap[r["id"]]), "filter differs")
        cp, output = expected(row, r["family"], entries)
        require(r["checkpoint"] == cp and matches(r["output"], output), "actual policy differs")
        score = validate_output(r["output"], eligible[r["filter"]], truth[r["id"]])
        require(abs(score - r["recall"]) < 1e-12, "actual quality differs")
        required = quality_required(row, r["family"])
        require(r["quality_required"] == required, "quality gate differs")
        require(not required or score + 1e-12 >= row["native_recall"], "native recall loss")
        timer(r)
        if r["family"] in (
            "oracle_feasible_full",
            "oracle_feasible_test",
            "matched_full",
            "matched_test",
            "empty",
        ):
            arm = {
                "oracle_feasible_full": 20,
                "oracle_feasible_test": 21,
                "matched_full": 30,
                "matched_test": 31,
                "empty": 43,
            }[r["family"]]
            observations = [
                row["observations"][str(cp)] for cp in POINTS if str(cp) in row["observations"]
            ]
            require(
                expected_program(entries[arm], r["filter"], observations, r["output"], r["audit"])
                == cp,
                "compiled decision differs",
            )
        else:
            require(r["audit"] is None, "unexpected audit")
        quality[key] = r
    require(len(quality) == len(queries) * 8, "quality coverage differs")
    cpus = read(results / "allowed-cpus.json")
    require(len(cpus) == len(set(cpus)) == 4, "CPU inventory differs")
    readers = {}
    for r in lines(results / "reader-setup.jsonl"):
        key = r["filter"], r["reader"]
        require(key not in readers and r["affinity_after"] == [r["cpu"]], "invalid reader binding")
        readers[key] = r
    require(len(readers) == 56, "reader coverage differs")
    groups = sorted({group(q["id"]) for q in queries})
    gi = {g: i for i, g in enumerate(groups)}
    values = np.full((len(groups), 7, 8, 8), np.nan)  # vector, filter, reader, family
    routing = np.full_like(values, np.nan)
    cells = (
        cell
        for ti, t in enumerate(FILTERS)
        for cell in schedule([q for q in queries if threshold(q) == t], ti)
    )
    count = 0
    for r, cell in zip(lines(results / "timing.jsonl"), cells, strict=True):
        rotation, position, reader, family, q = cell
        t = threshold(q)
        require(
            (r["id"], r["filter"], r["rotation"], r["position"], r["reader"], r["family"])
            == (q["id"], t, rotation, position, reader, family),
            "timing schedule differs",
        )
        assignment = readers[t, reader]
        require(
            r["pid"] == assignment["pid"]
            and r["cpu"] == assignment["cpu"] == cpus[(reader + FILTERS.index(t)) % 4],
            "reader PID/CPU differs",
        )
        require(r["role"] == roles[q["id"]], "timed role differs")
        require(r["checkpoint"] == quality[q["id"], family]["checkpoint"], "timed stop differs")
        require(matches(r["output"], quality[q["id"], family]["output"]), "timed output differs")
        timer(r)
        key = gi[group(q["id"])], FILTERS.index(t), reader, FAMILIES.index(family)
        require(np.isnan(values[key]), "duplicate timing cell")
        values[key] = r["request_ns"] / 1e6
        routing[key] = r["oracle_routing_ns_outside_primary"] / 1e6
        count += 1
    require(np.isfinite(values).all(), "missing timing tensor cells")
    source = read(kit / "source-capture-receipt.json")["searches"]
    budget = read(kit / "source-capture-budget.json")
    counts = dict(source)
    counts["previous_unused_reserved"] = budget["charged_total"] - counts["total"]
    counts["quality_ann"] = len(queries) * 8
    counts["timed_ann"] = len(queries) * 64
    counts["warmup_ann"] = 64 * sum(
        min(10, sum(threshold(q) == t for q in queries)) for t in FILTERS
    )
    counts["total"] = sum(v for k, v in counts.items() if k != "total")
    require(
        receipt["searches"] == read(results / "attempts.json") == counts,
        "cumulative attempt ledger differs",
    )
    require(count == counts["timed_ann"], "timing count differs")
    final = read(results / "reservation-final.json")
    require(
        final["source_charged"] == budget["charged_total"]
        and final["actual_total"] == counts["total"],
        "source spending reset",
    )
    require(
        final["charged_total"] <= final["cap"] == 2000000
        and final["unused_charged"] == final["charged_total"] - counts["total"] >= 0,
        "reservation accounting differs",
    )
    return groups, roles, cases, quality, values, routing


def report(results, kit, *, fixture=False):
    groups, roles, cases, quality, values, routing = verify(results, kit, fixture=fixture)
    output = {
        "schema": "fannagent.oracle-variants.report.v1",
        "fixture": fixture,
        "hindsight_fit": True,
        "quality_gate": "per-case native Recall@10",
        "latency_optimality_proven": False,
        "cohorts": {},
        "scope": "one allocation; vector-cluster bootstrap conditional on fitted policies",
        "limitations": [
            "Earliest safe stop and work optimization do not prove minimum wall time",
            "Cohorts overlap and each feasible policy used its cohort outcomes",
            "Bootstrap excludes allocation variability and policy fitting uncertainty",
        ],
    }
    for cohort in ("full_workload", "heldout_test"):
        selected = [
            i
            for i, g in enumerate(groups)
            if cohort == "full_workload"
            or any(group(qid) == g and role == "test" for qid, role in roles.items())
        ]
        if not selected:
            continue
        a = values[selected]
        n = len(selected)
        per_vector = a.mean(axis=2)
        rng = np.random.default_rng(20261118)
        draws = []
        for _ in range(40):
            weights = rng.multinomial(n, np.full(n, 1 / n), size=500)
            draws.append((weights @ per_vector.reshape(n, -1) / n).reshape(500, 7, 8))
        boot = np.concatenate(draws)
        means = per_vector.mean(axis=0)
        family = "oracle_feasible_full" if cohort == "full_workload" else "oracle_feasible_test"
        matched = "matched_full" if cohort == "full_workload" else "matched_test"
        fi = FAMILIES.index(family)
        mi = FAMILIES.index(matched)
        stats = {}
        for label, filters in (
            ("equal_six_filters", list(range(1, 7))),
            ("equal_seven_conditions", list(range(7))),
            *((str(t), [ti]) for ti, t in enumerate(FILTERS)),
        ):
            m = means[filters].mean(axis=0)
            b = boot[:, filters].mean(axis=1)
            ci = np.quantile(b[:, 7] / b[:, 0], [0.05, 0.95])
            variants = {}
            for name, index in (
                ("oracle_ideal", 1),
                ("oracle_constrained", 2),
                ("oracle_feasible", fi),
            ):
                ratio = float(m[index] / m[0])
                interval = np.quantile(b[:, index] / b[:, 0], [0.025, 0.975])
                variants[name] = {
                    "mean_ms": float(m[index]),
                    "native_ratio": ratio,
                    "savings_percent": 100 * (1 - ratio),
                    "ratio_conditional95_interval": interval.tolist(),
                    "savings_percent_conditional95_interval": [
                        100 * (1 - float(interval[1])),
                        100 * (1 - float(interval[0])),
                    ],
                    "per_reader_native_ratio": [
                        float(a[:, filters, reader, index].mean() / a[:, filters, reader, 0].mean())
                        for reader in range(8)
                    ],
                }
            stats[label] = {
                "native_mean_ms": float(m[0]),
                "variants": variants,
                "matched_continue_mean_ms": float(m[mi]),
                "empty_mean_ms": float(m[7]),
                "empty_native_ratio": float(m[7] / m[0]),
                "empty_native_conditional90_interval": ci.tolist(),
                "empty_control_within_2pct": bool(ci[0] >= 0.98 and ci[1] <= 1.02),
                "feasible_matched_ratio": float(m[fi] / m[mi]),
                "routing_mean_ms_outside_primary": {
                    name: float(routing[selected][:, filters, :, index].mean())
                    for index, name in ((1, "oracle_ideal"), (2, "oracle_constrained"))
                },
            }
        ids = {
            qid for qid, row in cases.items() if cohort == "full_workload" or row["role"] == "test"
        }
        quality_stats = {}
        for name, actual in (
            ("oracle_ideal", "oracle_ideal"),
            ("oracle_constrained", "oracle_constrained"),
            ("oracle_feasible", family),
        ):
            by_filter = {}
            for t in FILTERS:
                rows = [quality[qid, actual] for qid in ids if cases[qid]["filter"] == t]
                by_filter[str(t)] = {
                    "cases": len(rows),
                    "stops": sum(r["checkpoint"] > 0 for r in rows),
                    "checkpoint_histogram": dict(Counter(r["checkpoint"] for r in rows)),
                    "native_mean_recall": float(
                        np.mean([cases[r["id"]]["native_recall"] for r in rows])
                    ),
                    "mean_recall": float(np.mean([r["recall"] for r in rows])),
                    "recall_losses": sum(
                        r["recall"] + 1e-12 < cases[r["id"]]["native_recall"] for r in rows
                    ),
                    "result_count_losses": sum(
                        len(r["output"]) < len(cases[r["id"]]["native"]) for r in rows
                    ),
                }
            quality_stats[name] = by_filter
        passed = all(stats[str(t)]["empty_control_within_2pct"] for t in FILTERS)
        output["cohorts"][cohort] = {
            "vectors": n,
            "cases": len(ids),
            "feasible_family": family,
            "latency": stats,
            "quality": quality_stats,
            "all_condition_controls_pass": passed,
            "interpretation": "measured hindsight headroom"
            if passed
            else "descriptive estimate; timing equivalence controls inconclusive/outside band",
        }
    output["test_policy_outside_cohort_recall_losses"] = sum(
        r["recall"] + 1e-12 < cases[qid]["native_recall"]
        for (qid, family), r in quality.items()
        if family == "oracle_feasible_test" and cases[qid]["role"] != "test"
    )
    (results / "report.json").write_text(json.dumps(output, sort_keys=True, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    result = report(args.results, args.kit, fixture=args.fixture)
    print(
        json.dumps(
            {c: r["latency"]["equal_seven_conditions"] for c, r in result["cohorts"].items()},
            indent=2,
        )
    )
