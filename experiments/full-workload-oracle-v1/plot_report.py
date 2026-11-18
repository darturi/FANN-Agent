"""Plot verified original-graph headroom; no query or policy-selection authority."""

import argparse
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot(results):
    data = json.loads((results / "report.json").read_text())
    if data["fixture"]:
        raise ValueError("Do not present fixture latency as benchmark headroom")
    metrics = (
        "equal_six_filters",
        "equal_seven_conditions",
        "-1",
        "743",
        "527",
        "310",
        "192",
        "108",
        "32",
    )
    labels = (
        "Six filters (primary)",
        "All seven conditions",
        "Unfiltered",
        "Votes ≥ 743",
        "Votes ≥ 527",
        "Votes ≥ 310",
        "Votes ≥ 192",
        "Votes ≥ 108",
        "Votes ≥ 32",
    )
    fig, ax = plt.subplots(figsize=(11.5, 7.8))
    fig.subplots_adjust(left=0.22, right=0.98, top=0.85, bottom=0.20)
    colors = ("#2563eb", "#ea580c")
    y = np.arange(len(metrics))
    for index, (cohort, title) in enumerate(
        (
            ("full_workload", "Full benchmark · 1,000 vectors"),
            ("heldout_test", "Held-out subset · 275 vectors"),
        )
    ):
        stats = data["cohorts"][cohort]["latency"]
        values = np.array([stats[k]["latency_reduction_percent"] for k in metrics])
        limits = np.array([stats[k]["reduction_percent_conditional95_interval"] for k in metrics])
        ax.barh(
            y + (index - 0.5) * 0.32,
            values,
            height=0.3,
            color=colors[index],
            label=title,
            xerr=np.stack((values - limits[:, 0], limits[:, 1] - values)),
            capsize=2,
            error_kw={"linewidth": 1, "ecolor": "#334155"},
        )
    ax.axvline(0, color="#64748b", linewidth=1)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Latency reduction versus native640 (%)")
    fig.suptitle(
        "Oracle stopping headroom at native retrieval quality",
        x=0.22,
        y=0.97,
        ha="left",
        fontsize=16,
        weight="bold",
    )
    ax.grid(axis="x", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    handles, titles = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        titles,
        loc="upper left",
        bbox_to_anchor=(0.21, 0.93),
        ncol=2,
        frameon=False,
        fontsize=9,
    )
    controls = all(row["all_condition_controls_pass"] for row in data["cohorts"].values())
    note = (
        "95% paired vector-group intervals, conditional on one allocation. "
        "Free hindsight choice; native recall and count preserved."
    )
    if not controls:
        note += (
            " Some timing controls are inconclusive/outside the 2% band; estimates are descriptive."
        )
    fig.text(0.02, 0.035, textwrap.fill(note, width=145), va="bottom", fontsize=9, color="#475569")
    target = results / "oracle-headroom.png"
    fig.savefig(target, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(target.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    plot(parser.parse_args().results)
