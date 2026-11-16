"""Bind verified complete M1 evidence after the fixed M2 models fail qualification."""

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
DEST = STUDY / "evidence-m2-v1"
RESULTS = STUDY / "returns/job-23376796/results"
KIT = STUDY / "kits/m1-runtime-qualification-v2"
sys.path.insert(0, str(HERE.parent / "filtered-ann-protocol-v2"))
from fannproto.evidence import GRAPH, Evidence  # noqa: E402
from fannproto.policy import FILTERS, PROFILE  # noqa: E402


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


def main():
    assert not (DEST / "bound-evidence.json").exists(), "preserve sealed binding"
    qualification = json.loads((DEST / "model-qualification.json").read_text())
    assert qualification["status"] == "negative_no_cost_model_qualified"
    assert not qualification["cost_ranking_enabled"] and qualification["selected_model"] is None
    for path, h in qualification["source_sha256"].items():
        assert sha(ROOT / path) == h
    plan = json.loads((DEST / "prospective-plan.json").read_text())
    for path, h in plan["inputs"].items():
        assert sha(ROOT / path) == h
    bundle = deepcopy(json.loads((RESULTS / "development-prefix-evidence.json").read_text()))
    original = Evidence(bundle)
    assert original.identity == qualification["input_evidence_identity"]
    source_ids = sorted(
        {int(r["id"].split("-v")[1].split("-")[0]) for r in lines(KIT / "queries.jsonl")}
    )
    gi = {source: i for i, source in enumerate(source_ids)}
    assert set(source_ids) == set(
        json.loads((KIT / "binding.json").read_text())["development_source_indices"]
    )
    work = {}
    for r in lines(RESULTS / "work/work.jsonl"):
        group = gi[int(r["id"].split("-v")[1].split("-")[0])]
        f = "unfiltered" if r["filter"] < 0 else "votes" + str(r["filter"])
        work[group, f, r["family"]] = r["counts"]
    facts = json.loads((RESULTS / "serving-cost-library.json").read_text())
    transfers = {}
    for block, name in enumerate(("v2_conservative", "v2_moderate", "v2_broad")):
        stats = facts["timing_groups"][str(block)]["families"]
        value = stats[name]
        transfers[name] = {
            "same_block_native_ratio": value["ratio_to_same_block_native"],
            "conditional95pct_interval": value["native_ratio_conditional95pct_interval"],
            "per_filter_native_ratio": {
                f: value["per_filter_mean_ms"][str(-1 if f == "unfiltered" else int(f[5:]))]
                / stats["native640"]["per_filter_mean_ms"][
                    str(-1 if f == "unfiltered" else int(f[5:]))
                ]
                for f in FILTERS
            },
        }
    anchors = [
        block["families"]["native640"]["equal_scalar_mean_ms"]
        for block in facts["timing_groups"].values()
    ]
    bundle["cost_status"] = "unqualified_M2_models_failed"
    bundle["evidence_qualification"] = {
        "status": "qualified_complete_original_graph_development_labels_and_prefix_work",
        "M1_outcome_freeze_sha256": sha(STUDY / "freeze/m1-assessment-v1.json"),
        "M2_model_qualification_sha256": sha(DEST / "model-qualification.json"),
        "original_evidence_sha256": sha(RESULTS / "development-prefix-evidence.json"),
    }
    bundle["cost_guidance"] = {
        "status": "measured_plan_facts_only_cost_ranking_disabled",
        "failed_model_hypotheses": list(qualification["models"]),
        "measured_historical_transfers": transfers,
        "paired_complete_plan_differences": facts["paired_complete_plan_differences"],
        "native_primary_ms_range_across_blocks": [min(anchors), max(anchors)],
        "limits": "One allocation and exposed development. Each contrast uses its own native "
        "block. Complete-plan differences are not universal additive operation prices. Search "
        "work is not milliseconds. Neither M2 model passed the frozen error limits; new-program "
        "latency estimation, deterministic cost shortlisting and paid generation remain blocked.",
    }
    per_filter = {}
    for f in FILTERS:
        per_filter[f] = {
            "queries": 450,
            "prefixes": {},
            "eligible_rows": len(
                json.loads((RESULTS / "timing/eligibility.json").read_text())[
                    str(-1 if f == "unfiltered" else int(f[5:]))
                ]
            ),
        }
    for row in bundle["rows"]:
        g, f = row["group"], row["filter"]
        row["work"] = {
            "graph": {"full": {key: work[g, f, "native640"][key] for key in GRAPH}},
            "membership_per_checkpoint": {},
        }
        for cp, proof in row["proofs"].items():
            row["work"]["graph"][cp] = {key: work[g, f, "bare_stop" + cp][key] for key in GRAPH}
            row["work"]["membership_per_checkpoint"][cp] = work[g, f, "count_stop" + cp][
                "membership_probes"
            ]
            stats = per_filter[f]["prefixes"].setdefault(
                cp,
                {
                    "reached": 0,
                    "partial": 0,
                    "zero": 0,
                    "preserving": 0,
                    "losing": 0,
                    "feature_available": {key: 0 for key in row["observations"][cp]},
                },
            )
            stats["reached"] += 1
            stats["partial"] += proof["returned_count"] < 10
            stats["zero"] += proof["returned_count"] == 0
            preserving = proof["recall"] >= row["native_recall"] - 1e-12
            stats["preserving"] += preserving
            stats["losing"] += not preserving
            for key, value in row["observations"][cp].items():
                stats["feature_available"][key] += value is not None
    bundle["development_prefix_summary"] = per_filter
    bound = Evidence(bundle)
    empirical_work_checks = 0
    programs = json.loads((KIT / "compiled-programs.json").read_text())["bindings"]
    arms = json.loads((KIT / "m1-plan.json").read_text())["arms"]
    for entry in programs:
        name = next(name for name, arm in arms.items() if arm == entry["arm"])
        replay = bound.work_estimate(entry["policy"], force_continue=entry["force_continue"])
        for f in FILTERS:
            for key in GRAPH + ("feature_passes", "membership_probes"):
                target = sum(work[g, f, name][key] for g in range(450)) / 450
                assert abs(replay["per_filter_means"][f][key] - target) < 1e-10, (name, f, key)
                empirical_work_checks += 1
    summary = bound.summary()
    summary["prefix_opportunity"] = per_filter
    assert summary["cost_ranking_enabled"] is False
    assert len(json.dumps(summary).encode()) < 24000, "compact bounded inspection contract"
    write(DEST / "bound-evidence.json", bundle)
    write(DEST / "compact-summary.json", summary)
    old_gates = json.loads((STUDY / "reports/protocol-v2-gates-after-M1.json").read_text())
    assert (
        old_gates["M1"]["status"]
        == "verified_original_graph_runtime_partial_prefix_labels_and_empirical_serving_cost_library"  # noqa: E501
    )
    gates = {
        **old_gates,
        "M1": {
            **old_gates["M1"],
            "status": "verified_original_graph",
            "runtime_profile": PROFILE.fingerprint,
            "upstream_status": old_gates["M1"]["status"],
        },
        "M2": {
            "status": "complete_evidence_bound_cost_model_qualification_failed",
            "evidence_hash": bound.identity,
            "receipt_sha256": sha(DEST / "model-qualification.json"),
            "cost_ranking_enabled": False,
            "prefix_labels": 9436,
            "partial_prefix_labels": 1496,
        },
        "generation_blocked_by": [
            "No M2 cost model met the frozen qualification limits",
            "New concrete provider episode not authorized",
        ],
    }
    write(DEST / "bound-gates.json", gates)
    primer = [
        "# Frozen development evidence, M2",
        "",
        "450 exposed vector groups; all six scalar predicates plus unfiltered. "
        "All five folds are exposed development.",
        "Preserve each case's actual unguarded native640 recall. Exact truth is scoring only; "
        "short results remain misses.",
        "All9,436 actual prefix labels are available, including1,496 partial labels. "
        "No validation/test access.",
        "Runtime features: qualifying_count, tenth_distance, frontier_gap and "
        "top10_new_since_previous at16/32/64.",
        "Missing comparisons are false; turnover needs the preceding scheduled full top ten. "
        "Predicates without rules continue without avoidable observations.",
        "Search-work feedback replays measured prefix counts; it never converts graph work "
        "into milliseconds.",
        "COST RANKING DISABLED: neither predeclared model met the frozen error limits. "
        "Measured historical-plan facts remain contextual diagnostics.",
        "No new policy has measured latency. The existing controller must abstain from an "
        "unsupported cost shortlist.",
        "",
        "| Condition | Native recall | Short /450 | Reached prefix labels | Partial labels |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for f in FILTERS:
        stat = summary["per_filter"][f]
        reached = sum(s["reached"] for s in per_filter[f]["prefixes"].values())
        partial = sum(s["partial"] for s in per_filter[f]["prefixes"].values())
        primer.append(
            f"| {f} | {stat['native_mean_recall']:.4f} | {stat['short_native']} "
            f"| {reached} | {partial} |"
        )
    primer.extend(
        [
            "",
            "These recall/work summaries are offline research feedback, never executable "
            "features. Native-relative oracle opportunity is not an executable policy or "
            "a universal safety guarantee.",
            "No provider episode is authorized by this binding.",
            "",
        ]
    )
    (DEST / "primer.md").write_text("\n".join(primer))
    receipt = {
        "schema": "filtered-ann.M2-evidence-binding.v1",
        "date": "2026-11-16",
        "status": "complete_labels_and_work_bound_cost_qualification_negative",
        "evidence_identity": bound.identity,
        "evidence_sha256": sha(DEST / "bound-evidence.json"),
        "model_qualification_sha256": sha(DEST / "model-qualification.json"),
        "empirical_per_filter_work_checks": empirical_work_checks,
        "cost_ranking_enabled": False,
        "counts": {
            "groups": 450,
            "conditions": 7,
            "rows": 3150,
            "prefixes": 9436,
            "partial_prefixes": 1496,
            "missing": 0,
        },
        "external_requests": 0,
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
        "source_sha256": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                HERE / "bind.py",
                HERE.parent / "filtered-ann-protocol-v2/fannproto/evidence.py",
            ]
        },
        "artifact_sha256": {
            name: sha(DEST / name)
            for name in [
                "bound-evidence.json",
                "bound-gates.json",
                "compact-summary.json",
                "primer.md",
            ]
        },
    }
    write(DEST / "binding-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
