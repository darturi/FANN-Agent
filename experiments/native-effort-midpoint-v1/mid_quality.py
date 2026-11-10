"""Vector-cluster development quality gate, independent of timing outcomes."""

from collections import defaultdict

from mid_common import CRITERIA, FILTERS
from mid_stats import require


def quality_report(refs):
    import numpy as np

    require(
        len(refs) == 600 and len({r["query_id"] for r in refs}) == 600,
        "Incomplete quality inventory",
    )
    results = {}
    for filter_ in ["overall", *FILTERS]:
        selected = [
            r for r in refs if filter_ == "overall" or r["query_id"].endswith("-" + filter_)
        ]
        groups = defaultdict(list)
        for row in selected:
            values = row["outcomes"]
            require(
                set(values) == {"native640", "native480"}
                and all(v["valid"] and v["returned_count"] == 10 for v in values.values()),
                "Invalid/incomplete output; not a quality-negative decision",
            )
            groups[row["group"]].append(
                values["native480"]["recall"] - values["native640"]["recall"]
            )
        require(
            len(groups) == 200
            and all(len(v) == (3 if filter_ == "overall" else 1) for v in groups.values()),
            "Incomplete vector grouping",
        )
        matrix = np.asarray([np.mean(groups[g]) for g in sorted(groups)])
        rng = np.random.default_rng(CRITERIA["bootstrap_seed"])
        boot = np.empty(CRITERIA["bootstrap_samples"])
        for start in range(0, len(boot), 128):
            count = min(128, len(boot) - start)
            boot[start : start + count] = matrix[rng.integers(0, 200, size=(count, 200))].mean(
                axis=1
            )
        ci = np.quantile(boot, [0.025, 0.975]).tolist()
        means = {
            cell: float(np.mean([r["outcomes"][cell]["recall"] for r in selected]))
            for cell in ("native640", "native480")
        }
        checks = {
            "both_native_floors": all(v >= 0.95 for v in means.values()),
            "development_reserve": ci[0] >= -CRITERIA["development_recall_reserve"],
        }
        results[filter_] = {
            "cases": len(selected),
            "independent_vectors": 200,
            "mean_recall": means,
            "recall_delta": float(matrix.mean()),
            "recall_delta_ci95": ci,
            "checks": checks,
            "pass": all(checks.values()),
            "final_margin_diagnostic_only": ci[0]
            >= -CRITERIA["final_recall_margin_diagnostic_only"],
        }
    return {
        "pass": all(v["pass"] for v in results.values()),
        "strata": results,
        "pointwise_intervals": True,
        "independent_confirmation": False,
    }
