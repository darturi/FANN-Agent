"""Static scientific figure from independently verified production measurements."""

import argparse
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def plot(folder):
    report = json.loads((folder / "report.json").read_text())
    if report["fixture"]:
        raise ValueError("Synthetic fixture timings are not benchmark evidence")
    names = ("oracle_ideal", "oracle_constrained", "oracle_feasible")
    labels = ("Ideal\nany checkpoint", "Constrained\n16 / 32 / 64", "Feasible\nagent DSL")
    colors = ("#2563eb", "#0f766e", "#c2410c")
    all_bounds = [
        v["savings_percent_conditional95_interval"][0]
        for c in report["cohorts"].values()
        for metric in ("equal_six_filters", "equal_seven_conditions")
        for v in c["latency"][metric]["variants"].values()
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 9.4), sharey=True)
    fig.subplots_adjust(left=0.08, right=0.98, bottom=0.18, top=0.82, hspace=0.65, wspace=0.18)
    for row, (cohort, title) in enumerate(
        (
            ("full_workload", "Full workload · 7,000 cases"),
            ("heldout_test", "Held-out subset · 1,925 cases"),
        )
    ):
        data = report["cohorts"][cohort]
        for column, (metric, subtitle) in enumerate(
            (
                ("equal_six_filters", "Six filtered conditions"),
                ("equal_seven_conditions", "All seven conditions"),
            )
        ):
            ax = axes[row, column]
            stats = data["latency"][metric]
            v = [stats["variants"][n] for n in names]
            values = np.array([r["savings_percent"] for r in v])
            bounds = np.array([r["savings_percent_conditional95_interval"] for r in v])
            ax.bar(
                np.arange(3),
                values,
                width=0.63,
                color=colors,
            )
            for x, (low, high) in enumerate(bounds):
                ax.vlines(x, low, high, color="#334155", linewidth=1)
                ax.hlines((low, high), x - 0.04, x + 0.04, color="#334155", linewidth=1)
            for x, y in enumerate(values):
                ax.annotate(
                    f"{y:.1f}%",
                    (x, y),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha="center",
                    fontsize=10,
                    weight="bold",
                )
            ax.set_xticks(range(3), labels)
            ax.set_title(title + "\n" + subtitle, fontsize=11, loc="left", pad=12)
            ax.axhline(0, color="#64748b", linewidth=0.8)
            ax.grid(axis="y", color="#e2e8f0", linewidth=0.7)
            ax.set_axisbelow(True)
            ax.set_ylim(min(-5, min(all_bounds) - 8), 100)
            if column == 0:
                ax.set_ylabel("Latency savings versus native640 (%)")
            for spine in ("top", "right", "left"):
                ax.spines[spine].set_visible(False)
    fig.suptitle(
        "Hindsight oracle latency headroom", x=0.08, y=0.96, ha="left", fontsize=18, weight="bold"
    )
    fig.text(
        0.08,
        0.915,
        "Same graph and per-case native Recall@10 gate; "
        "feasible policies fitted separately by cohort",
        fontsize=10,
        color="#475569",
    )
    note = (
        "Error bars: 95% paired vector-cluster intervals, "
        "conditional on one allocation and fixed policies. "
        "Ideal/constrained decisions are free; feasible feature and rule costs are included. "
        "Feasible is best found in the agent DSL, not a proven latency optimum."
    )
    if not all(r["all_condition_controls_pass"] for r in report["cohorts"].values()):
        note += " Timing equivalence controls did not all pass; estimates are descriptive."
    fig.text(0.04, 0.035, textwrap.fill(note, 145), fontsize=9, color="#475569", va="bottom")
    for extension in ("png", "svg"):
        fig.savefig(folder / ("oracle-variants." + extension), dpi=180, facecolor="white")
    plt.close(fig)
    print((folder / "oracle-variants.png").resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, required=True)
    plot(parser.parse_args().folder)
