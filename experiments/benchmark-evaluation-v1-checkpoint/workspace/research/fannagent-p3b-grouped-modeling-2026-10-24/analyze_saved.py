"""Descriptive analysis of locked P3b outputs. No imports of modeling code/fits."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "trials/torch-reviews-grouped-stop-modeling-v1/runs/p3b-20261024-local-v1"
OUT = Path(__file__).with_name("analysis.json")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((RUN / name).read_text())


def summarize(rows):
    n = len(rows)
    return {
        "cases": n,
        "distinct_vectors": len({r["group"] for r in rows}),
        "stops": sum(r["checkpoint"] is not None for r in rows),
        "loss_cases": sum(r["recall_delta"] < -1e-12 for r in rows),
        "incomplete_cases": sum(not r["valid"] or r["returned_count"] != 10 for r in rows),
        "recall_delta": sum(r["recall_delta"] for r in rows) / n,
        "activation_proxy_ms_saved": sum(r["activation_proxy_ms_saved"] for r in rows) / n,
        "reuse_proxy_ms_saved": sum(r["reuse_proxy_ms_saved"] for r in rows) / n,
    }


verification = read("verification.json")
for name, expected in verification["files_sha256"].items():
    assert digest(RUN / name) == expected, name
replay = read("verification-replay.json")
assert replay["status"] == "passed" and replay["new_fits_in_verification"] == 0
performance = read("performance.json")
inner = {}
totals = Counter()
for profile in ("static23", "progress34"):
    inner[profile] = {}
    for method in ("shallow_tree", "extra_trees"):
        counts = Counter()
        by_risk = defaultdict(Counter)
        failures = Counter()
        for path in sorted((RUN / "selection").glob(f"{profile}-{method}-outer*.json")):
            selection = json.loads(path.read_text())
            assert selection["chosen"] is None
            for trial in selection["trials"]:
                a = trial["assessment"]
                b = a["overall"]
                flags = {
                    "trials": True,
                    "recall_pass": a["development_recall_pass"],
                    "positive_both_proxies": b["activation_proxy_ms_saved"] > 0
                    and b["reuse_proxy_ms_saved"] > 0,
                    "any_stop": b["stopped_cases"] > 0,
                    "complete_top10": b["all_valid_complete_top10"],
                    "qualified": a["development_signal"],
                }
                flags["positive_but_recall_fail"] = flags["positive_both_proxies"] and not flags["recall_pass"]
                flags["recall_pass_but_nonpositive_proxy"] = flags["recall_pass"] and not flags["positive_both_proxies"]
                for key, flag in flags.items():
                    counts[key] += int(flag)
                    totals[key] += int(flag)
                    by_risk[str(int(trial["risk"]))][key] += int(flag)
                for f, report in [("overall", b), *a["per_filter"].items()]:
                    if not report["development_recall_pass"]:
                        failures[f] += 1
        inner[profile][method] = {
            "counts": dict(counts),
            "by_risk": {k: dict(v) for k, v in by_risk.items()},
            "failed_recall_gate_by_scope": dict(failures),
        }

errors = {}
loss_sets = {}
for profile in ("static23", "progress34"):
    rows = []
    for path in sorted((RUN / "outer-records").glob(f"{profile}-extra_trees-outer*-fixed_diagnostic.json")):
        rows += json.loads(path.read_text())["rows"]
    assert len(rows) == 600
    bins = defaultdict(list)
    for r in rows:
        # Fixed descriptive bins, never predictor inputs or a new selection rule.
        work = r["native_work"]
        label = "0-4999" if work < 5000 else "5000-9999" if work < 10000 else "10000-19999" if work < 20000 else "20000+"
        bins[label].append(r)
    losses = [r for r in rows if r["recall_delta"] < -1e-12]
    loss_sets[profile] = {r["query_id"] for r in losses}
    errors[profile] = {
        "overall": summarize(rows),
        "by_native_work_descriptive_only": {k: summarize(v) for k, v in sorted(bins.items())},
        "by_checkpoint": {
            str(cp): summarize([r for r in rows if r["checkpoint"] == cp])
            for cp in (16, 32, 64, 128, None)
            if any(r["checkpoint"] == cp for r in rows)
        },
        "loss_rows": losses,
    }

fits = [json.loads(p.read_text()) for p in sorted((RUN / "fits").glob("*.json"))]
fit_summary = {}
for method in ("shallow_tree", "extra_trees"):
    subset = [f for f in fits if f["method"] == method]
    fit_summary[method] = {
        "estimator_fits": len(subset),
        "individual_trees": sum(f["individual_trees"] for f in subset),
        "nodes_before_group_pruning": sum(f["nodes_before_group_pruning"] for f in subset),
        "nodes_after_group_pruning": sum(f["nodes_after_group_pruning"] for f in subset),
        "all_unpruned_prediction_parity_pass": all(f["unpruned_sklearn_prediction_parity"] for f in subset),
    }

result = {
    "version": "grouped-stop-modeling.v1.descriptive-analysis",
    "scope": "Locked existing outputs only; no new model, fit, threshold selection, routing policy or measurement.",
    "inputs": {name: digest(RUN / name) for name in ("performance.json", "verification.json", "verification-replay.json", "design-lock.json")},
    "inner_totals": dict(totals),
    "inner_by_profile_method": inner,
    "fixed_diagnostic_extra_trees": errors,
    "fixed_diagnostic_loss_case_overlap": {
        "static23": len(loss_sets["static23"]),
        "progress34": len(loss_sets["progress34"]),
        "intersection": len(loss_sets["static23"] & loss_sets["progress34"]),
        "union": len(loss_sets["static23"] | loss_sets["progress34"]),
    },
    "fit_summary": fit_summary,
    "new_fits": 0,
    "new_measurements": 0,
    "gate": "No qualified signal from either frozen procedure. This does not identify a universal feature or capacity ceiling.",
    "next_hypothesis": "One prospective risk-separated objective comparison at fixed feature/action/capacity scope; tail-risk versus positive savings is the observed conflict. Cause unestablished; no automatic extra fitting or data acquisition.",
}
assert totals["trials"] == 560 and totals["qualified"] == 0
assert totals["positive_both_proxies"] == totals["positive_but_recall_fail"]
assert totals["recall_pass"] == totals["recall_pass_but_nonpositive_proxy"]
OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({"inner_totals": dict(totals), "fits": fit_summary, "loss_overlap": result["fixed_diagnostic_loss_case_overlap"]}, indent=2))
