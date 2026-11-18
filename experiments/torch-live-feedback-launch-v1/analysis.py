"""Paired exposed-group bootstrap. Every result is an adaptive development screen."""

import random
import statistics

from limits import FILTERS


def summarize(quality, timings, families, *, draws=1000):
    losses = {name: 0 for name in families}
    stops = {name: {str(t): 0 for t in FILTERS} for name in families}
    for row in quality:
        native = row["results"]["native640"]["recall"]
        for name in families:
            result = row["results"][name]
            losses[name] += result["recall"] < native - 1e-12
            stops[name][str(row["filter"])] += bool(result["checkpoint"])
    result = {
        "quality_loss_cases": losses,
        "stop_counts": stops,
        "latency": None,
        "performance_claim": False,
        "scope": "adaptive development only; no held-out or allocation-general claim",
    }
    if not timings:
        return result
    values = {}
    groups = set()
    for row in timings:
        group = row["id"].rsplit("-", 1)[0]
        groups.add(group)
        values.setdefault((group, row["filter"], row["family"]), []).append(row["request_ns"])
    groups = sorted(groups)
    expected = {(g, t, name) for g in groups for t in FILTERS for name in families}
    if set(values) != expected or any(len(v) != 8 for v in values.values()):
        raise ValueError("incomplete balanced live timing; do not rank partial returns")
    means = {key: statistics.mean(v) for key, v in values.items()}

    def mean(sample, name, filters):
        return statistics.mean(means[g, t, name] for g in sample for t in filters)

    rng = random.Random(20261117)
    samples = [rng.choices(groups, k=len(groups)) for _ in range(draws)]
    estimates = {}
    for name in families:
        ratios = sorted(
            mean(s, name, FILTERS[1:]) / mean(s, "native640", FILTERS[1:]) for s in samples
        )
        estimates[name] = {
            "scalar_ratio_to_native": mean(groups, name, FILTERS[1:])
            / mean(groups, "native640", FILTERS[1:]),
            "conditional95_interval": [ratios[int(0.025 * draws)], ratios[int(0.975 * draws)]],
            "conditional90_interval": [ratios[int(0.05 * draws)], ratios[int(0.95 * draws)]],
            "per_filter_ratio_to_native": {
                str(t): mean(groups, name, (t,)) / mean(groups, "native640", (t,)) for t in FILTERS
            },
        }
        if name.startswith("candidate"):
            estimates[name]["practical_5pct_target_met"] = (
                estimates[name]["scalar_ratio_to_native"] <= 0.95
            )
            matched = "matched" + name.removeprefix("candidate")
            paired = sorted(
                mean(s, name, FILTERS[1:]) / mean(s, matched, FILTERS[1:]) for s in samples
            )
            estimates[name]["scalar_ratio_to_matched"] = mean(groups, name, FILTERS[1:]) / mean(
                groups, matched, FILTERS[1:]
            )
            estimates[name]["matched_conditional95_interval"] = [
                paired[int(0.025 * draws)],
                paired[int(0.975 * draws)],
            ]
    result["latency"] = estimates
    result["timed_development_groups"] = len(groups)
    result["interpretation"] = (
        "Measured complete-request times; intervals omit adaptive selection "
        "and allocation variability. An independent frozen evaluation is still required."
    )
    return result
