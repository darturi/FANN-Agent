"""Descriptive locked P3c analysis; no model imports, fits or new selections."""

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = (
    ROOT
    / "trials/torch-reviews-risk-separated-stop-modeling-v1/runs/p3c-20261024-local-v1"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((RUN / name).read_text())


def summary(rows):
    n = len(rows)
    return {
        "cases": n,
        "distinct_vectors": len({r["group"] for r in rows}),
        "stops": sum(r["checkpoint"] is not None for r in rows),
        "loss_cases": sum(r["recall_delta"] < -1e-12 for r in rows),
        "incomplete_cases": sum(
            not r["valid"] or r["returned_count"] != 10 for r in rows
        ),
        "recall_delta": sum(r["recall_delta"] for r in rows) / n,
        "activation_proxy_ms_saved": sum(r["activation_proxy_ms_saved"] for r in rows)
        / n,
        "reuse_proxy_ms_saved": sum(r["reuse_proxy_ms_saved"] for r in rows) / n,
    }


verification = read("verification.json")
for name, digest in verification["files_sha256"].items():
    assert sha(RUN / name) == digest, name
assert read("verification-replay.json")["status"] == "passed"
p = read("performance.json")
totals = Counter()
inner = defaultdict(dict)
transfers = []
for profile in ["static23", "progress34"]:
    for method in ["shallow_tree", "extra_trees"]:
        counts = Counter()
        scopes = Counter()
        for path in sorted((RUN / "selection").glob(f"{profile}-{method}-outer*.json")):
            cell = json.loads(path.read_text())
            for trial in cell["trials"]:
                a = trial["assessment"]
                o = a["overall"]
                positive = (
                    o["activation_proxy_ms_saved"] > 0 and o["reuse_proxy_ms_saved"] > 0
                )
                flags = {
                    "trials": True,
                    "recall_pass": a["development_recall_pass"],
                    "positive_both_proxies": positive,
                    "any_stop": o["stopped_cases"] > 0,
                    "qualified": a["development_signal"],
                    "complete_top10": o["all_valid_complete_top10"],
                    "positive_but_recall_fail": positive
                    and not a["development_recall_pass"],
                    "recall_pass_but_nonpositive_proxy": a["development_recall_pass"]
                    and not positive,
                }
                for key, flag in flags.items():
                    counts[key] += int(flag)
                    totals[key] += int(flag)
                for scope, report in [("overall", o), *a["per_filter"].items()]:
                    if not report["development_recall_pass"]:
                        scopes[scope] += 1
            chosen = cell["chosen"]
            if chosen is not None:
                candidate = next(
                    t
                    for t in cell["trials"]
                    if all(t[k] == v for k, v in chosen.items())
                )
                records = read("outer-records/" + path.stem + "-calibrated.json")[
                    "rows"
                ]
                transfers.append(
                    {
                        "profile": profile,
                        "method": method,
                        "outer_fold": cell["outer_fold"],
                        "chosen": chosen,
                        "inner_oof": candidate["assessment"],
                        "outer_heldout_descriptive": summary(records),
                    }
                )
        inner[profile][method] = {
            "counts": dict(counts),
            "failed_recall_gate_by_scope": dict(scopes),
        }

errors = {}
for phase in ["calibrated", "fixed_diagnostic"]:
    errors[phase] = {}
    for profile in ["static23", "progress34"]:
        rows = []
        for path in sorted(
            (RUN / "outer-records").glob(f"{profile}-extra_trees-outer*-{phase}.json")
        ):
            rows += json.loads(path.read_text())["rows"]
        assert len(rows) == 600
        bins = defaultdict(list)
        for r in rows:
            work = r["native_work"]
            bins[
                "0-4999"
                if work < 5000
                else "5000-9999"
                if work < 10000
                else "10000-19999"
                if work < 20000
                else "20000+"
            ].append(r)
        errors[phase][profile] = {
            "overall": summary(rows),
            "by_filter": {
                f: summary([r for r in rows if r["stratum"] == f])
                for f in ["unfiltered", "votes32", "votes108"]
            },
            "by_native_work_descriptive_only": {
                k: summary(v) for k, v in sorted(bins.items())
            },
            "by_checkpoint": {
                cp: summary([r for r in rows if str(r["checkpoint"]) == cp])
                for cp in sorted({str(r["checkpoint"]) for r in rows})
            },
            "loss_rows": [r for r in rows if r["recall_delta"] < -1e-12],
        }

fits = [json.loads(path.read_text()) for path in sorted((RUN / "fits").glob("*.json"))]
fit_summary = {}
for method in ["shallow_tree", "extra_trees"]:
    subset = [f for f in fits if f["method"] == method]
    fit_summary[method] = {
        "estimator_fits": len(subset),
        "individual_trees": sum(f["individual_trees"] for f in subset),
        "nodes_before_group_pruning": sum(
            f["nodes_before_group_pruning"] for f in subset
        ),
        "nodes_after_group_pruning": sum(
            f["nodes_after_group_pruning"] for f in subset
        ),
        "all_risk_prediction_parity_pass": all(
            f["unpruned_sklearn_risk_prediction_parity"] for f in subset
        ),
    }

result = {
    "version": "risk-separated-stop-modeling.v1.descriptive-analysis",
    "scope": "Saved frozen outputs only. No new models, fits, thresholds, subgroup routing or measurements.",
    "inputs_sha256": {
        name: sha(RUN / name)
        for name in [
            "performance.json",
            "verification.json",
            "verification-replay.json",
            "design-lock.json",
        ]
    },
    "inner_totals": dict(totals),
    "inner_by_profile_method": inner,
    "chosen_inner_to_outer_transfers": transfers,
    "extra_trees_errors": errors,
    "fit_summary": fit_summary,
    "paired_p3c_minus_p3b": p["paired_p3c_minus_frozen_p3b"],
    "new_fits": 0,
    "new_measurements": 0,
    "decision": "Close finite P3c formulation allowance negatively. Retain original execution; no qualifying family or universal information ceiling.",
    "recommended_next_scope": "B1a: read-only feasibility/design audit of query-dependent search effort at fixed index, including actual backend knobs, cheap qualified inputs, timing boundary, matched native baseline and finite comparison. Proposed only; no B1 implementation/measurement authorized by this analysis.",
    "rationale": "Risk-separated fixed diagnostics reduce observed recall losses but do not cover activation costs; calibrated risk gates fail the joint heldout gate, while shallow policies abstain. No new native timing exists. More tuning or indiscriminate label collection on the same scope is not justified; fresh development diversity remains an alternative requiring a precise hypothesis and new entitlement contract.",
}
assert totals["trials"] == 980 and len(transfers) == 4
Path(__file__).with_name("analysis.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n"
)
print(
    json.dumps(
        {
            "inner_totals": dict(totals),
            "fits": fit_summary,
            "transfers": [
                {
                    "profile": t["profile"],
                    "outer_fold": t["outer_fold"],
                    "chosen": t["chosen"],
                    "inner_activation": t["inner_oof"]["overall"][
                        "activation_proxy_ms_saved"
                    ],
                    "outer": t["outer_heldout_descriptive"],
                }
                for t in transfers
            ],
        },
        indent=2,
    )
)
