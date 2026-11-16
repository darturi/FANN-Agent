"""Independent descriptive reconstruction after the frozen attribution verifier/analysis."""

import argparse
import collections
import hashlib
import json
from pathlib import Path

import numpy as np

FAMILIES = ("native640", "noop640", "conservative_a", "moderate_b_fixed", "broad_c_fixed")
FILTERS = (-1, 743, 527, 310, 192, 108, 32)
GRAPH = (
    "vector_calls",
    "layer0_neighbor_scores",
    "upper_neighbor_scores",
    "layer0_queue_pops",
    "layer0_adjacencies_examined",
)


def lines(path):
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def assess(results, kit):
    verified = json.loads((results / "local-verification.json").read_text())
    analysis = json.loads((results / "diagnostic-analysis.json").read_text())
    assert verified["status"] == "counterbalanced_attribution_return_verified"
    binding = json.loads((kit / "binding.json").read_text())
    query_groups = sorted({q["id"].rsplit("-", 1)[0] for q in lines(kit / "queries.jsonl")})
    assert len(query_groups) == 450
    assert {int(g.removeprefix("reviews-clean-v")) for g in query_groups} == set(
        binding["development_source_indices"]
    )
    group_index = {g: i for i, g in enumerate(query_groups)}
    # Each exposed vector/condition/backend/cycle/family has exactly one observation.
    data = np.full((450, 7, 20, 2, 5), np.nan)
    exposures = collections.Counter()
    timer_parts = collections.defaultdict(lambda: np.zeros(3))
    count = 0
    for r in lines(results / "timing/timing.jsonl"):
        g = group_index[r["id"].rsplit("-", 1)[0]]
        t = FILTERS.index(r["filter"])
        f = FAMILIES.index(r["family"])
        key = g, t, r["reader"], r["cycle"], f
        assert np.isnan(data[key])
        data[key] = r["request_ns"]
        assert r["request_ns"] == r["construction_ns"] + r["sql_fetch_decode_ns"]
        timer_parts[r["filter"], r["family"]] += (
            r["request_ns"],
            r["construction_ns"],
            r["sql_fetch_decode_ns"],
        )
        exposures[r["filter"], r["family"], r["cpu"]] += 1
        count += 1
    assert count == 630000 and np.all(np.isfinite(data)) and np.all(data > 0)
    assert set(exposures.values()) == {4500} and len(exposures) == 7 * 5 * 4
    summary = {}
    for f, name in enumerate(FAMILIES):
        mean_ms = float(data[:, 1:, :, :, f].mean() / 1e6)
        assert abs(mean_ms - verified["metrics"][name]["equal_scalar_mean_ms"]) < 1e-10
        assert abs(mean_ms - analysis["timing"][name]["mean_ms"]) < 1e-10
        ratios = [
            float(data[:, 1:, r, :, f].mean() / data[:, 1:, r, :, 0].mean()) for r in range(20)
        ]
        ci = analysis["timing"][name]["native_ratio_95pct_conditional_group_interval"]
        summary[name] = {
            "mean_ms": mean_ms,
            "speedup_vs_native_pct": 100
            * (1 - mean_ms / verified["metrics"]["native640"]["equal_scalar_mean_ms"]),
            "speedup_vs_noop_pct": 100
            * (1 - mean_ms / verified["metrics"]["noop640"]["equal_scalar_mean_ms"]),
            "conditional_group_95pct_speedup_interval_pct": [100 * (1 - ci[1]), 100 * (1 - ci[0])],
            "reader_slot_scalar_pooled_ratios": ratios,
            "reader_slot_limit": (
                "Slots aggregate distinct backend PIDs across filters, "
                "not 20 allocation replicates."
            ),
            "per_cpu": analysis["timing"][name]["per_cpu"],
            "cycle_ratios": analysis["timing"][name]["per_cycle_native_ratio"],
        }
    eligible = json.loads((results / "timing/eligibility.json").read_text())
    quality = {}
    losses = collections.Counter()
    short_counts = collections.Counter()
    stops = collections.defaultdict(collections.Counter)
    work = {}
    for r in lines(results / "timing/quality.jsonl"):
        qid = r["id"]
        native = r["results"]["native640"]["recall"]
        for name, v in r["results"].items():
            key = r["filter"], name
            losses[key] += v["recall"] < native - 1e-12
            short_counts[key] += v["returned_count"] < 10
            stops[key][str(v["checkpoint"])] += 1
            quality[qid, name] = v
    assert len(quality) == 15750 and not any(losses.values())
    for r in lines(results / "work/work.jsonl"):
        assert r["counts"]["start_cpu"] == r["counts"]["end_cpu"]
        work[r["id"], r["family"]] = r["counts"]
    assert len(work) == 15750
    mismatches = {
        k: sum(
            work[q, "noop640"][k] != work[q, "native640"][k] for q, n in quality if n == "native640"
        )
        for k in GRAPH
    }
    assert not any(mismatches.values())
    per_condition = {}
    broad_saved_ms = []
    for ti, t in enumerate(FILTERS):
        base = float(data[:, ti, :, :, 0].mean() / 1e6)
        per_condition[str(t)] = {
            "eligible_rows": len(eligible[str(t)]),
            "eligible_pct": 100 * len(eligible[str(t)]) / 247286,
            "families": {},
        }
        qids = [
            q
            for q, n in quality
            if n == "native640" and q.endswith("-unfiltered" if t < 0 else "-votes" + str(t))
        ]
        assert len(qids) == 450
        for fi, name in enumerate(FAMILIES):
            mean = float(data[:, ti, :, :, fi].mean() / 1e6)
            graph = {}
            for k in GRAPH:
                a = sum(work[q, name][k] for q in qids)
                b = sum(work[q, "native640"][k] for q in qids)
                graph[k] = {"mean_count": a / 450, "reduction_vs_native_pct": 100 * (1 - a / b)}
            per_condition[str(t)]["families"][name] = {
                "mean_ms": mean,
                "speedup_vs_native_pct": 100 * (1 - mean / base),
                "mean_recall": sum(quality[q, name]["recall"] for q in qids) / 450,
                "recall_losses": losses[t, name],
                "short_outputs": short_counts[t, name],
                "first_stop_counts": dict(stops[t, name]),
                "graph_work": graph,
                "mean_feature_passes": sum(work[q, name]["feature_passes"] for q in qids) / 450,
                "mean_membership_probes": sum(work[q, name]["membership_probes"] for q in qids)
                / 450,
                "timer_components_mean_ms": (timer_parts[t, name] / 18000 / 1e6).tolist(),
            }
        if t >= 0:
            broad_saved_ms.append(
                base - per_condition[str(t)]["families"]["broad_c_fixed"]["mean_ms"]
            )
    broad_contribution = broad_saved_ms[-1] / sum(broad_saved_ms)
    assignments = list(lines(results / "timing/assignments.jsonl"))
    pids = {r["pid"] for r in assignments}
    visits = collections.Counter((r["filter"], r["reader"], r["family"]) for r in assignments)
    assert len(assignments) == 1400 and set(visits.values()) == {2}
    cpu_ids = sorted({r["cpu"] for r in assignments})
    for r in assignments:
        assert r["affinity_after"] == [r["cpu"]]
    out = {
        "schema": "reader-attribution-independent-assessment.v1",
        "job_id": "23303080",
        "status": "verified_diagnostic_not_final_performance_claim",
        "timing_records_reconstructed": count,
        "total_attempts": verified["total_attempts"],
        "offline_exact_references": 6300,
        "exact_serving_calls": 0,
        "work_queries": len(work),
        "cpu_ids": cpu_ids,
        "assignment_records": len(assignments),
        "distinct_timing_backend_pids": len(pids),
        "role_repetitions_per_backend": 2,
        "native_noop_per_query_graph_counter_mismatches": mismatches,
        "quality_query_losses": {n: sum(losses[t, n] for t in FILTERS) for n in FAMILIES},
        "native_short_outputs": sum(short_counts[t, "native640"] for t in FILTERS),
        "primary_equal_scalar_summary": summary,
        "per_condition": per_condition,
        "broad_votes32_share_of_net_scalar_ms_saving": broad_contribution,
        "work_counter_summary": analysis["work_counters"],
        "inferential_limit": (
            "20,000 frozen group bootstrap draws conditional on one allocation; "
            "exposed development only. No node/allocation or held-out generalization claim."
        ),
        "cpu_evidence_limit": (
            "Timing uses recorded verified singleton affinity before/after blocks; "
            "direct kernel CPU samples belong only to separate instrumented work queries. "
            "No independent scheduler trace."
        ),
        "prior_control_advantage": (
            "Earlier fixed-reader job's always-continue advantage did not reproduce here. "
            "Node/schedule changed, so the earlier cause is not uniquely identified."
        ),
        "scope": {
            "development_groups": 450,
            "scalar_filters": 6,
            "unfiltered": True,
            "provider_calls": 0,
            "validation_test_outcomes_opened": False,
        },
        "provenance": {
            "kit_binding_sha256": sha(kit / "binding.json"),
            "frozen_verification_sha256": sha(results / "local-verification.json"),
            "frozen_analysis_sha256": sha(results / "diagnostic-analysis.json"),
        },
    }
    (results / "independent-assessment.json").write_text(
        json.dumps(out, sort_keys=True, indent=2) + "\n"
    )
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--kit", type=Path, required=True)
    a = p.parse_args()
    result = assess(a.results, a.kit)
    print(
        json.dumps(
            {
                "status": result["status"],
                "records": result["timing_records_reconstructed"],
                "attempts": result["total_attempts"],
                "graph_mismatches": result["native_noop_per_query_graph_counter_mismatches"],
                "recall_losses": result["quality_query_losses"],
                "votes32_share": result["broad_votes32_share_of_net_scalar_ms_saving"],
            },
            indent=2,
        )
    )
