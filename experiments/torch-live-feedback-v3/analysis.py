"""Paired vector-cluster summaries; quality and failed controls are never suppressed."""

import numpy as np
from limits import FILTERS


def summarize(quality, timings, families, *, draws=1000):
    losses = {f: 0 for f in families}
    counts = {f: 0 for f in families}
    stops = {f: {str(t): 0 for t in FILTERS} for f in families}
    for r in quality:
        f = r["family"]
        losses[f] += int(r["recall"] + 1e-12 < r["native_recall"])
        counts[f] += int(len(r["output"]) < r["native_count"])
        stops[f][str(r["filter"])] += int(bool(r["checkpoint"]))
    result = {
        "quality_loss_cases": losses,
        "result_count_loss_cases": counts,
        "stop_counts": stops,
        "latency": None,
        "performance_claim": False,
        "scope": "adaptive development screen",
    }
    if not timings:
        return result
    groups = sorted({r["id"].rsplit("-", 1)[0] for r in timings})
    gi = {g: i for i, g in enumerate(groups)}
    ti = {t: i for i, t in enumerate(FILTERS)}
    fi = {f: i for i, f in enumerate(families)}
    values = {}
    readers = {}
    for r in timings:
        key = (r["id"].rsplit("-", 1)[0], r["filter"], r["family"])
        values.setdefault(key, []).append(r["request_ns"])
        readers.setdefault(key, set()).add(r["reader"])
    expected = {(g, t, f) for g in groups for t in FILTERS for f in families}
    if (
        set(values) != expected
        or any(len(v) != 4 for v in values.values())
        or any(v != {0, 1, 2, 3} for v in readers.values())
    ):
        raise ValueError("incomplete four-reader timing; do not rank partial returns")
    cube = np.empty((len(groups), len(FILTERS), len(families)))
    for (g, t, f), v in values.items():
        cube[gi[g], ti[t], fi[f]] = np.mean(v)
    rng = np.random.default_rng(20261119)
    samples = rng.integers(0, len(groups), size=(draws, len(groups)), dtype=np.int32)
    native = fi["native640"]
    estimates = {}
    controls = {}
    for label, indices in [("all_seven", list(range(7))), ("six_filters", list(range(1, 7)))] + [
        (str(t), [ti[t]]) for t in FILTERS
    ]:
        group_means = cube[:, indices, :].mean(axis=1)
        base = group_means[:, native]
        base_draws = base[samples].mean(axis=1)
        summary = {}
        for f in families:
            vals = group_means[:, fi[f]]
            ratios = vals[samples].mean(axis=1) / base_draws
            ratio = float(vals.mean() / base.mean())
            ci95 = np.quantile(ratios, [0.025, 0.975]).tolist()
            ci90 = np.quantile(ratios, [0.05, 0.95]).tolist()
            entry = {
                "mean_ms": float(vals.mean() / 1e6),
                "native_ratio": ratio,
                "savings_percent": 100 * (1 - ratio),
                "conditional95_ratio_interval": ci95,
                "conditional90_ratio_interval": ci90,
                "conditional95_savings_interval": [100 * (1 - ci95[1]), 100 * (1 - ci95[0])],
            }
            if f.startswith("candidate"):
                matched = "matched" + f.removeprefix("candidate")
                paired = vals[samples].mean(axis=1) / group_means[:, fi[matched]][samples].mean(
                    axis=1
                )
                entry["matched_conditional95_interval"] = np.quantile(
                    paired, [0.025, 0.975]
                ).tolist()
            summary[f] = entry
        estimates[label] = summary
        if label not in ("all_seven", "six_filters"):
            controls[label] = {
                f: (
                    0.98 <= summary[f]["conditional90_ratio_interval"][0]
                    and summary[f]["conditional90_ratio_interval"][1] <= 1.02
                )
                for f in ("empty", "native_clone")
                if f in fi
            }
    result["aggregates"] = estimates
    result["control_equivalence_by_condition"] = controls
    result["all_condition_controls_pass"] = all(v for d in controls.values() for v in d.values())
    result["timed_vector_groups"] = len(groups)
    result["bootstrap_draws"] = draws
    result["latency"] = {
        f: {
            "scalar_ratio_to_native": estimates["six_filters"][f]["native_ratio"],
            "all_seven_savings_percent": estimates["all_seven"][f]["savings_percent"],
            "conditional95_interval": estimates["six_filters"][f]["conditional95_ratio_interval"],
            **(
                {
                    "matched_conditional95_interval": estimates["six_filters"][f][
                        "matched_conditional95_interval"
                    ]
                }
                if f.startswith("candidate")
                else {}
            ),
        }
        for f in families
    }
    result["interpretation"] = (
        "Conditional on fixed policies, exposed query groups and one allocation; "
        "excludes selection and allocation uncertainty. Failed controls make latency descriptive."
    )
    return result
