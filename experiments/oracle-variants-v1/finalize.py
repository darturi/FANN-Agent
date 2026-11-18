"""Publish verified measurements, ordinary DSL artifacts, and explicit search gaps."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

VARIANTS = ("oracle_ideal", "oracle_constrained", "oracle_feasible")
COHORTS = ("full_workload", "heldout_test")


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def finalize(results, kit, fit, output, accounting):
    report = json.loads((results / "report.json").read_text())
    assert not report["fixture"]
    output.mkdir()
    policies = output / "policies"
    policies.mkdir()
    submissions = output / "agent-submissions"
    submissions.mkdir()
    cases = [json.loads(line) for line in (kit / "source-cases.jsonl").open()]
    registry = {
        "schema": "fannagent.oracle-variants.artifacts.v1",
        "cohorts": {},
        "quality_gate": report["quality_gate"],
        "hindsight_fit": True,
        "latency_optimality_proven": False,
        "agent_discovery_or_generalization_claim": False,
        "benchmark_binding_sha256": sha(kit / "binding.json"),
        "raw_receipt_sha256": sha(results / "receipt.json"),
        "report_sha256": sha(results / "report.json"),
    }
    gaps = {}
    for cohort in COHORTS:
        selected = [r for r in cases if cohort == "full_workload" or r["role"] == "test"]
        native_work = sum(r["native_layer0_work"] for r in selected)
        certificate = json.loads((fit / (cohort + "-fit-certificate.json")).read_text())
        actual = json.loads((kit / ("oracle_feasible-" + cohort + ".json")).read_text())
        assert sha(fit / ("oracle_feasible-" + cohort + ".json")) == sha(
            kit / ("oracle_feasible-" + cohort + ".json")
        )
        assert set(actual) == {"schema", "name", "rules", "rationale"}
        write(submissions / ("evaluate_candidates-" + cohort + ".json"), {"policies": [actual]})
        artifacts = {}
        for name in VARIANTS:
            path = policies / (name + "-" + cohort + ".json")
            if name == "oracle_feasible":
                shutil.copyfile(kit / path.name, path)
            else:
                choices = {}
                for row in selected:
                    if name == "oracle_ideal":
                        cp = row["ideal"]["checkpoint"]
                    else:
                        cp = next(
                            (
                                cp
                                for cp in (16, 32, 64)
                                if str(cp) in row["actions"] and row["actions"][str(cp)]["safe"]
                            ),
                            0,
                        )
                    choices[row["id"]] = cp
                write(
                    path,
                    {
                        "schema": "fannagent.evaluator-only.hindsight-lookup.v1",
                        "variant": name,
                        "cohort": cohort,
                        "choices": choices,
                        "agent_dsl_expressible": False,
                        "exact_serving_calls": 0,
                    },
                )
            artifacts[name] = {
                "path": str(path.resolve()),
                "sha256": sha(path),
                "agent_dsl_expressible": name == "oracle_feasible",
            }
        lower = certificate["work_saved"]
        upper = sum(r["work_saved_upper_bound"] for r in certificate["per_filter"])
        gaps[cohort] = {
            "native_layer0_work": native_work,
            "best_found_work_saved": lower,
            "work_saved_upper_bound": upper,
            "absolute_work_gap": upper - lower,
            "work_saved_percent": 100 * lower / native_work,
            "work_saved_percent_upper_bound": 100 * upper / native_work,
            "work_optimality_proven": lower == upper,
            "latency_optimality_proven": False,
        }
        registry["cohorts"][cohort] = {
            "cases": len(selected),
            "artifacts": artifacts,
            "search": gaps[cohort],
        }
        for suffix in ("-fit-inputs.json", "-fit-certificate.json"):
            shutil.copyfile(fit / (cohort + suffix), output / (cohort + suffix))
    write(output / "registry.json", registry)
    shutil.copyfile(results / "report.json", output / "report.json")
    for name in (
        "compiler-certificate.json",
        "compiled-programs.json",
        "timing-plan.json",
        "TIMING-PROTOCOL.md",
        "fit-environment.json",
    ):
        shutil.copyfile(kit / name, output / name)
    rows = []
    for path in accounting:
        for line in path.read_text().splitlines():
            fields = line.split("|")
            if fields and fields[0].isdigit():
                assert fields[1:3] == ["COMPLETED", "0:0"]
                rows.append(
                    {
                        "job_id": fields[0],
                        "state": fields[1],
                        "exit_code": fields[2],
                        "elapsed_seconds": int(fields[3]),
                        "cpus": int(fields[4]),
                    }
                )
        shutil.copyfile(path, output / path.name)
    assert len(rows) == 2 and len({r["job_id"] for r in rows}) == 2
    assert all(r["cpus"] == 4 for r in rows)
    assert sum(r["elapsed_seconds"] for r in rows) <= 21600
    write(
        output / "allocation-accounting.json",
        {"jobs": rows, "aggregate_allocated_seconds": sum(r["elapsed_seconds"] for r in rows)},
    )
    text = [
        "# Hindsight oracle comparison",
        "",
        "All results use the original 247,286-row cosine graph, k=10, native ef=640, "
        "and iterative scans off. Every reported policy preserves native Recall@10 "
        "on every case in its intended cohort. Each cohort's feasible policy was fitted "
        "using that cohort's outcomes. This is a hindsight capability diagnostic.",
        "",
    ]
    for label, key in (
        ("All seven conditions", "equal_seven_conditions"),
        ("Six filtered conditions (primary)", "equal_six_filters"),
    ):
        text += [
            "## " + label,
            "",
            "| Cohort | Native ms | Variant | Oracle ms | Savings | Conditional 95% interval |",
            "| --- | ---: | --- | ---: | ---: | ---: |",
        ]
        for cohort in COHORTS:
            stats = report["cohorts"][cohort]["latency"][key]
            for name in VARIANTS:
                v = stats["variants"][name]
                lo, hi = v["savings_percent_conditional95_interval"]
                text.append(
                    f"| {cohort} | {stats['native_mean_ms']:.4f} | `{name}` | "
                    f"{v['mean_ms']:.4f} | {v['savings_percent']:.2f}% | [{lo:.2f}%, {hi:.2f}%] |"
                )
        text += [""]
    for cohort in COHORTS:
        text += [
            "## Per-condition savings: " + cohort,
            "",
            "| Condition | Native ms | Ideal | Constrained | Feasible |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for condition in ("-1", "743", "527", "310", "192", "108", "32"):
            stats = report["cohorts"][cohort]["latency"][condition]
            label = "Unfiltered" if condition == "-1" else "Votes ≥ " + condition
            percentages = " | ".join(
                f"{stats['variants'][v]['savings_percent']:.2f}%" for v in VARIANTS
            )
            text.append(f"| {label} | {stats['native_mean_ms']:.4f} | {percentages} |")
        text += [""]
    text += [
        "## Meaning and limits",
        "",
        "`oracle_ideal` chooses the earliest safe reached checkpoint separately per case. "
        "`oracle_constrained` restricts that hindsight lookup to 16/32/64/continue. "
        "Both receive free query-specific decisions outside the primary timer.",
        "",
        "`oracle_feasible` is one ordinary policy per cohort, accepted by the agent's "
        "unchanged v2 parser and compiler and executed through the same compiled path. "
        "It uses only causal features and the bounded rule language. Feature collection "
        "and rule evaluation are included in request latency. The agent can hypothetically "
        "emit these artifacts; this experiment does not show that it can discover them "
        "from its usual feedback or generalize them to new queries.",
        "",
        "The feasible optimizer maximizes captured layer-0 work saved and retains safe "
        "incumbents at its search limits. These are best-found expressible policies, not "
        "certified latency maxima. Earliest safe checkpoints likewise do not prove minimum "
        "wall time. The following bounds apply to traversal work only:",
        "",
        "| Cohort | Best-found work saved | Work upper bound | Work optimum proven |",
        "| --- | ---: | ---: | --- |",
    ]
    for cohort in COHORTS:
        g = gaps[cohort]
        text.append(
            f"| {cohort} | {g['work_saved_percent']:.2f}% | "
            f"{g['work_saved_percent_upper_bound']:.2f}% | {g['work_optimality_proven']} |"
        )
    text += [
        "",
        "Intervals bootstrap 20,000 query-vector clusters and retain paired conditions "
        "and readers. They are conditional on one allocation and fixed hindsight policies; "
        "the two cohorts overlap. Allocation and policy-selection uncertainty are omitted.",
        "",
        "The empty/native 90% interval must fall entirely within [0.98, 1.02] "
        "in every condition to pass the timing-control criterion. Full control "
        "intervals, matched-continue costs and reader ratios are retained in `report.json`.",
        "",
    ]
    for cohort in COHORTS:
        row = report["cohorts"][cohort]
        failed = [
            t
            for t in ("-1", "743", "527", "310", "192", "108", "32")
            if not row["latency"][t]["empty_control_within_2pct"]
        ]
        losses = {v: sum(r["recall_losses"] for r in row["quality"][v].values()) for v in VARIANTS}
        count_losses = {
            v: sum(r["result_count_losses"] for r in row["quality"][v].values()) for v in VARIANTS
        }
        text += [
            f"**{cohort}:** {row['interpretation']}. Conditions failing the strict "
            f"empty/native 90% interval equivalence criterion: {failed}. "
            f"Per-case recall losses: {losses}. "
            f"Result-count losses under the recall-only gate: {count_losses}.",
            "",
        ]
    text += [
        f"The test-fitted policy has {report['test_policy_outside_cohort_recall_losses']} "
        "recall losses outside its fitted cohort; these transfer outcomes are retained.",
        "",
        "The earlier `oracle_ideal` results retain their additional native-result-count "
        "constraint and historical allocation. The new recall-only gate changes three "
        "ideal choices in 7,000 cases. Historical evidence is preserved separately.",
        "",
        "## Artifacts",
        "",
        "Ordinary feasible policies and evaluator-only lookup policies are under `policies/`. "
        "`registry.json` distinguishes their schemas and records hashes. Compiler and fit "
        "certificates, the frozen timing protocol, full per-condition report, and allocation "
        "accounting accompany this file. The raw returns remain in the parent study directory.",
        "",
        "New comparison aggregate allocated time: "
        f"{sum(r['elapsed_seconds'] for r in rows)} seconds. "
        "No provider calls or fresh exact queries were made.",
        "",
    ]
    (output / "REPORT.md").write_text("\n".join(text))
    study_registry = output.parent / "registry.json"
    if study_registry.exists():
        prior = json.loads(study_registry.read_text())
        prior["new_comparison"] = {
            "status": "completed_and_independently_verified",
            "artifacts": str(output.resolve()),
            "report_sha256": sha(output / "report.json"),
            "jobs": rows,
            "feasible_policies": "one normal agent DSL artifact fitted per reported cohort",
            "latency_optimality_proven": False,
        }
        write(study_registry, prior)
    print(output.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("results", "kit", "fit", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--accounting", type=Path, nargs=2, required=True)
    args = parser.parse_args()
    finalize(args.results, args.kit, args.fit, args.output, args.accounting)
