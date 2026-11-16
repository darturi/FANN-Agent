"""Check physical-CPU summaries against raw CPU-keyed actual synthetic SQL timings."""

import collections
import math
import sys

from package_kit import RUNTIME, sha, write


def run():
    sys.path.append(str(RUNTIME))
    from m1_analyse import analyse
    from m1_design import GROUPS
    from m1_verify import lines

    root = RUNTIME / "checks/verifier-fixture"
    results = root / "results"
    report = analyse(results, root / "kit")
    assert report["status"] == "M1_fixture_cost_library_only"
    values = collections.defaultdict(list)
    for row in lines(results / "timing/timing.jsonl"):
        if row["filter"] >= 0:
            values[row["group"], row["family"], row["cpu"]].append(row["request_ns"] / 1e6)
    cpus = sorted({key[2] for key in values})
    assert len(cpus) == 4
    means = {key: math.fsum(samples) / len(samples) for key, samples in values.items()}
    comparisons = 0
    for group, names in enumerate(GROUPS):
        for name in names:
            stats = report["timing_groups"][str(group)]["families"][name]
            for cpu in cpus:
                expected = means[group, name, cpu]
                ratio = expected / means[group, "native640", cpu]
                assert math.isclose(
                    stats["per_cpu_primary_mean_ms"][str(cpu)], expected, rel_tol=1e-12
                )
                assert math.isclose(
                    stats["per_cpu_primary_native_ratio"][str(cpu)], ratio, rel_tol=1e-12
                )
                comparisons += 2
    assert comparisons == 248
    receipt = {
        "status": "passed",
        "comparisons": comparisons,
        "check": "Independent raw CPU-keyed aggregation matches tensor-based "
        "physical-CPU means/ratios",
        "source_timings_sha256": sha(results / "timing/timing.jsonl"),
        "conditions": "all six scalar filters, equal weight; unfiltered excluded from primary",
        "fixture_only": True,
        "SQL_searches_or_provider_calls": 0,
        "validation_test_outcomes_opened": False,
    }
    write(RUNTIME / "checks/cpu-analysis-regression.json", receipt)
    print(receipt)


if __name__ == "__main__":
    run()
