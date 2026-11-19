"""Publish compact verified evidence, normal policy artifacts and comparison."""
# ruff: noqa: E501

import argparse
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from prepare_capture import HERE, ROOT, WORK, sha  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def allocated(path):
    cells = path.read_text().splitlines()[0].split("|")
    assert cells[1:3] == ["COMPLETED", "0:0"]
    return int(cells[4])


def plot(report, target):
    variants = (
        "oracle_ideal",
        "oracle_constrained",
        "oracle_feasible_narrow",
        "oracle_feasible_broad",
    )
    labels = ("Ideal", "Constrained (16/32/64)", "Feasible · narrow v2", "Feasible · broad v3")
    colors = ("#a9bbc8", "#7798ae", "#376e93", "#007d72")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharex=True)
    for ax, cohort, title in zip(
        axes,
        ("heldout_test", "full_workload"),
        ("Held-out · 1,925 cases", "Full workload · 7,000 cases"),
        strict=True,
    ):
        data = report["cohorts"][cohort]["latency"]["equal_seven_conditions"]["variants"]
        for i, (variant, label, color) in enumerate(zip(variants, labels, colors, strict=True)):
            row = data[variant]
            mean = row["savings_percent"]
            lo, hi = row["savings_percent_conditional95_interval"]
            ax.barh(i, mean, color=color, height=0.57)
            ax.errorbar(
                mean,
                i,
                xerr=[[max(0, mean - lo)], [max(0, hi - mean)]],
                fmt="none",
                ecolor="#183746",
                capsize=3,
                lw=1,
            )
            ax.text(
                max(mean, hi) + 1.2, i, f"{mean:.1f}%", va="center", fontsize=11, fontweight="bold"
            )
        ax.set_yticks(range(4), labels)
        ax.invert_yaxis()
        ax.set_xlim(0, 100)
        ax.set_xlabel("Mean latency savings vs native (%)")
        ax.set_title(title, loc="left", fontweight="bold", pad=15)
        ax.xaxis.grid(True, alpha=0.15)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis="y", length=0)
    fig.suptitle(
        "Broader deployable policy language: hindsight capacity",
        x=0.02,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    controls_pass = all(r["all_condition_controls_pass"] for r in report["cohorts"].values())
    fig.text(
        0.02,
        0.055,
        "Descriptive estimates: timing controls did not establish ±2% equivalence."
        if not controls_pass
        else "Timing controls established ±2% equivalence.",
        fontsize=9,
        color="#7b4926" if not controls_pass else "#4d5c63",
    )
    fig.text(
        0.02,
        0.015,
        "Seven conditions. Whiskers: conditional 95% vector-cluster intervals. Policies fitted with hindsight.",
        fontsize=9,
        color="#4d5c63",
    )
    fig.tight_layout(rect=(0, 0.13, 1, 0.93), w_pad=2.5)
    fig.savefig(target / "oracle-comparison.png", dpi=180)
    fig.savefig(target / "oracle-comparison.svg")
    plt.close(fig)
    svg = target / "oracle-comparison.svg"
    svg.write_text("\n".join(s.rstrip() for s in svg.read_text().splitlines()) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--fit", type=Path, required=True)
    parser.add_argument("--kit", type=Path, default=WORK / "benchmark-kit-v1")
    args = parser.parse_args()
    args.capture = args.capture.resolve(strict=True)
    args.results = args.results.resolve(strict=True)
    args.fit = args.fit.resolve(strict=True)
    args.kit = args.kit.resolve(strict=True)
    kit = args.kit
    report = read(args.results / "report.json")
    cap_seconds = allocated(args.capture.parent / "accounting.psv")
    bench_seconds = allocated(args.results.parent / "accounting.psv")
    plan = read(kit / "timing-plan.json")
    assert cap_seconds == plan["source_elapsed_seconds"]
    prior_seconds = plan.get("prior_cancelled_elapsed_seconds", 0)
    failed_seconds = plan.get("prior_failed_elapsed_seconds", 0)
    total_seconds = cap_seconds + prior_seconds + failed_seconds + bench_seconds
    assert total_seconds <= 21600
    receipt = read(args.results / "receipt.json")
    budget = read(args.results / "reservation-final.json")
    assert budget["charged_total"] <= 2000000 and receipt["provider_calls"] == 0
    target = HERE / "results"
    target.mkdir()
    for name in (
        "report.json",
        "frontier-qualification.json",
        "policy-freeze.json",
        "reservation-final.json",
    ):
        shutil.copyfile(args.results / name, target / name)
    shutil.copyfile(args.capture.parent / "accounting.psv", target / "capture-accounting.psv")
    shutil.copyfile(args.results.parent / "accounting.psv", target / "benchmark-accounting.psv")
    if prior_seconds:
        cancelled = read(kit / "prior-cancelled-accounting.json")
        assert (
            max(int(r.split("|")[4]) for r in cancelled["accounting"].splitlines()) == prior_seconds
        )
        shutil.copyfile(
            kit / "prior-cancelled-accounting.json", target / "prior-cancelled-accounting.json"
        )
        shutil.copyfile(kit / "resume-plan.json", target / "resume-plan.json")
    if failed_seconds:
        failure = read(kit / "prior-failed-accounting.json")
        assert (
            max(int(r.split("|")[4]) for r in failure["accounting"].splitlines()) == failed_seconds
        )
        shutil.copyfile(
            kit / "prior-failed-accounting.json", target / "prior-failed-accounting.json"
        )
        shutil.copyfile(
            kit / "frontier-projection-fixture.json", target / "frontier-projection-fixture.json"
        )
    for p in args.fit.iterdir():
        if (
            p.is_file()
            and not p.name.endswith("-choices.jsonl")
            and p.name != "causal-collisions.json"
        ):
            shutil.copyfile(p, target / p.name)
    shutil.copyfile(WORK / "checks/local-validation.json", target / "local-validation.json")
    shutil.copyfile(
        WORK / "fixture-v2/checks/v3-smoke/receipt.json", target / "native-fixture-receipt.json"
    )
    shutil.copyfile(kit / "timing-plan.json", target / "timing-plan.json")
    compiled = read(kit / "compiled-v3.json")
    certificate = {k: v for k, v in compiled.items() if k != "bindings"}
    certificate["bindings"] = [
        {k: v for k, v in b.items() if k not in ("policy", "plans")} for b in compiled["bindings"]
    ]
    (target / "compiler-certificate.json").write_text(json.dumps(certificate, indent=2) + "\n")
    failed_charge = receipt["searches"].get("prior_failed_reserved", 0)
    actual = (
        receipt["searches"]["total"]
        - receipt["searches"].get("previous_unused_reserved", 0)
        - failed_charge
    )
    count_bounds = [actual + int(bool(failed_charge)), actual + failed_charge]
    accounting = {
        "checkpoint_commit": "795db05",
        "capture_allocated_seconds": cap_seconds,
        "benchmark_allocated_seconds": bench_seconds,
        "prior_cancelled_allocated_seconds": prior_seconds,
        "prior_failed_allocated_seconds": failed_seconds,
        "total_allocated_seconds": total_seconds,
        "allocated_seconds_cap": 21600,
        "physical_cpus": 4,
        "memory_gib": 48,
        "fresh_ann_queries": actual if not failed_charge else None,
        "known_completed_stage_ann_queries": actual,
        "failed_stage_reserved_queries_charged": failed_charge,
        "fresh_ann_query_count_bounds": count_bounds,
        "charged_ann_reservations": budget["charged_total"],
        "ann_reservation_cap": 2000000,
        "provider_calls": 0,
        "fresh_exact_queries": 0,
        "automatic_retries": 0,
        "explicit_user_resumes": int(bool(prior_seconds)),
        "supervised_validation_repairs": int(bool(failed_seconds)),
        "raw_evidence": {
            str(p.relative_to(ROOT)): sha(p)
            for p in (
                args.capture / "receipt.json",
                args.capture / "cases.jsonl",
                args.results / "receipt.json",
                args.results / "quality.jsonl",
                args.results / "timing.jsonl",
                kit / "binding.json",
                kit / "oracle-module.so",
            )
        },
        "source_hashes": {
            str(p.relative_to(ROOT)): sha(p)
            for p in (
                ROOT / "agent/src/fannagent/api/broad_policy.py",
                HERE / "fit_broad.py",
                HERE / "broad_benchmark.py",
                HERE / "broad_analyse.py",
                HERE.parent / "filtered-ann-protocol-v3/fannproto3/compiler.py",
            )
        },
    }
    (target / "accounting.json").write_text(json.dumps(accounting, indent=2) + "\n")
    plot(report, target)
    lines = [
        "# Broader feasible oracle results",
        "",
        "The prior work was committed as `795db05` before implementation.",
        "",
        "Both broader policies are ordinary `fannagent.broad-stop.v3` artifacts, submitted through the agent tool and executed by its trusted native compiler/VM. They use hindsight on their respective reported cohort. This measures representational capacity, not agent discovery or generalization.",
        "",
        "| Oracle | Held-out savings | Full-workload savings |",
        "|---|---:|---:|",
    ]
    for name, label in (
        ("oracle_ideal", "oracle_ideal"),
        ("oracle_constrained", "oracle_constrained"),
        ("oracle_feasible_narrow", "oracle_feasible · narrow v2"),
        ("oracle_feasible_broad", "oracle_feasible · broad v3"),
    ):
        values = [
            report["cohorts"][c]["latency"]["equal_seven_conditions"]["variants"][name][
                "savings_percent"
            ]
            for c in ("heldout_test", "full_workload")
        ]
        lines.append(f"| {label} | {values[0]:.2f}% | {values[1]:.2f}% |")
    lines += [
        "",
        "Fresh measurements share one balanced allocation and native baseline. Savings use the ratio of mean latency, equally weighted over all seven conditions. The historical narrow-policy values were 27.20% held-out and 17.98% full; the table reruns those same policies in the new comparison.",
        "",
        "Strict control equivalence failed in both cohorts. Treat these as descriptive hindsight estimates. Unresolved timing bias prevents interpreting the broader full-workload policy's apparent lead over the ideal oracle as a real advantage. The broader interface expands expressions, causal feature access, and checkpoints beyond 16/32/64; its gains reflect all three changes.",
        "",
        "![Oracle comparison](oracle-comparison.png)",
        "",
        "| Cohort | Native mean | Broader mean | Broader saving, conditional 95% interval | Gain over narrow |",
        "|---|---:|---:|---:|---:|",
    ]
    for cohort, label in (
        ("heldout_test", "Held-out: 1,925 cases"),
        ("full_workload", "Full: 7,000 cases"),
    ):
        row = report["cohorts"][cohort]
        data = row["latency"]["equal_seven_conditions"]
        broad = data["variants"]["oracle_feasible_broad"]
        lo, hi = broad["savings_percent_conditional95_interval"]
        lines.append(
            f"| {label} | {data['native_mean_ms']:.3f} ms | {broad['mean_ms']:.3f} ms | {lo:.2f}–{hi:.2f}% | {data['broad_improvement_percentage_points']:.2f} pp |"
        )
    lines += [
        "",
        "| Six filtered conditions only | Ideal | Constrained | Narrow feasible | Broad feasible |",
        "|---|---:|---:|---:|---:|",
    ]
    for cohort, label in (("heldout_test", "Held-out"), ("full_workload", "Full")):
        v = report["cohorts"][cohort]["latency"]["equal_six_filters"]["variants"]
        lines.append(
            "| "
            + label
            + " | "
            + " | ".join(
                f"{v[n]['savings_percent']:.2f}%"
                for n in (
                    "oracle_ideal",
                    "oracle_constrained",
                    "oracle_feasible_narrow",
                    "oracle_feasible_broad",
                )
            )
            + " |"
        )
    lines += [
        "",
        "The fitter first constructs balanced threshold trees over causal frontier distance; ambiguous values use richer cost-guided trees. Such fine thresholds can memorize a finite cohort through causal observations. No query IDs, truth labels or future observations are runtime inputs. An agent with the authorized offline evidence and workspace could generate these exact JSON artifacts. Quality on future workloads is not established.",
        "",
        "| Cohort | Broader stops | Matches ideal stop | Native recall losses | Result-count losses | All-condition control equivalence |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for cohort, label in (("heldout_test", "Held-out"), ("full_workload", "Full")):
        cert = read(args.fit / (cohort + "-certificate.json"))
        row = report["cohorts"][cohort]
        q = row["quality"]["oracle_feasible_broad"]
        lines.append(
            f"| {label} | {cert['stops']} | {cert['matches_ideal_checkpoint']} / {cert['cases']} | {sum(r['recall_losses'] for r in q.values())} | {sum(r['result_count_losses'] for r in q.values())} | {'Passed' if row['all_condition_controls_pass'] else 'Not established'} |"
        )
    transfers = report["test_policy_outside_cohort_recall_losses"]
    qualification = report["qualification"]
    lines += [
        "",
        f"Outside the held-out fitting cohort, test-fitted recall losses are retained: narrow {transfers['narrow']}, broad {transfers['broad']} / 5,075 cases. The quality gate applies to each policy's intended cohort.",
        "",
        "The ideal oracle chooses hindsight stops without policy collection/VM costs; constrained restricts those choices to 16/32/64/continue; narrow feasible uses the prior three-clause/four-comparison language; broad feasible uses one complete v3 policy. Policies are best found fits. Earliest safe work stops and these timings do not prove a mathematical wall-clock optimum.",
        "",
        "All source cases and full prefix chains were bridged on the original graph. An independent canonical execution verified frontier/work at every captured checkpoint. Before timing, all 84,000 family/case outputs and compiled decisions were checked. Timing retained 336,000 requests: four samples per family/case, with every family on every reader. Feature collection and VM execution are inside the primary timer; ideal lookup routing is outside. No samples or outliers were removed.",
        "",
        f"The canonical logger retains raw floating-point cosine values while the native collector clips them into [0,2]. Qualification checks the existing native projection, requiring agreement within 1e-12 and boundary corrections no larger than 1e-6. All {qualification['frames']:,} checkpoint observations passed; {qualification.get('boundary_roundoff_events', 0):,} boundary roundoff events were recorded (maximum {qualification.get('boundary_roundoff_max_abs', 0):.3g}). The initial unprojected comparison failed before quality/timing; its evidence and entire reservation are retained. This repair did not change the native module, fitted policies or primary timing method.",
        "",
        "Uncertainty uses 20,000 fixed-seed vector-cluster draws, conditional on the fitted policies and one allocation. Strict control equivalence requires every condition's 90% interval for each empty-language/native-clone control inside ±2%. Where that fails, treat the table as descriptive estimates. Bootstrap intervals omit fitting uncertainty and variability between allocations.",
        "",
        f"New runs used {total_seconds:,} allocated seconds, including {prior_seconds} seconds from the user-cancelled allocation and {failed_seconds} seconds from failed qualification. Completed stages issued {actual:,} known ANN requests; the failed stage adds between {int(bool(failed_charge))} and {failed_charge:,} requests, with its entire reserved window charged. All {budget['charged_total']:,} charged reservations and allocated time remain within the predeclared six-hour/two-million envelope. The user explicitly resumed after pausing; frozen policies and the primary timing method were unchanged. Four physical CPUs and 48 GiB per allocation; zero provider calls, fresh exact queries or automatic retries.",
        "",
        "See `report.json` for condition-level quality, savings, uncertainty and control results; `accounting.json` for hashes and raw evidence locations; normal policy JSON, fit certificates and `agent-submission.json` for deployment artifacts. Raw archives remain outside Git.",
        "",
    ]
    (target / "REPORT.md").write_text("\n".join(lines))
    (target / "SHA256SUMS").write_text(
        "".join(
            sha(p) + "  " + p.name + "\n"
            for p in sorted(target.iterdir())
            if p.is_file() and p.name != "SHA256SUMS"
        )
    )
    print(target)


if __name__ == "__main__":
    main()
