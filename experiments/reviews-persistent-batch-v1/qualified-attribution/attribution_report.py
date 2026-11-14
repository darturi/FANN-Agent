"""Reconstruct native timing spans and paired diagnostics from the raw return."""

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import correlation, fmean

import numpy as np
from analyze import BATCHES, SIZE, equivalent, matches, quality
from attribution_plan import ARMS, schedule
from rb_plan import file_sha, pinned, pinned_lines, require
from rb_request_timing import request_components
from rb_stats import interval

RAW = {"quality.jsonl", "timing.jsonl", "eligible.json", "counters.json"}
CPU_SOURCES = {"process_cpu_clock", "schedstat", "proc_stat_ticks"}
PRIOR_QUALITY_SHA = "4be2898ad8da3aa3a89c22f418cf66f5a860aa451d8d5a5c6d72b91e6ff65c1c"


def components(request, logged, previous):
    before, after = request["backend"]
    sample_start, sample_end = before["sample_ns"]
    finish_start, finish_end = after["sample_ns"]
    begin, end = request["request_ns"]
    require(
        previous <= sample_start <= sample_end <= begin < end <= finish_start <= finish_end,
        "Backend samples or request timer are out of order",
    )
    require(0 <= before["cpu_ns"] <= after["cpu_ns"], "Backend CPU counter went backwards")
    result = request_components(request, logged)
    result["backend_cpu"] = (after["cpu_ns"] - before["cpu_ns"]) / 1e6
    left, right = before["schedstat"], after["schedstat"]
    wait = switches = None
    if left is not None and right is not None:
        require(
            len(left) == len(right) == 3 and all(0 <= x <= y for x, y in zip(left, right)),
            "Invalid backend scheduler counters",
        )
        wait = (right[1] - left[1]) / 1e6
        switches = right[2] - left[2]
    result["scheduler_wait"] = wait
    return result, switches, finish_end


def read_timing(directory, hashes, reference):
    rows = pinned_lines(directory / "timing.jsonl", hashes["timing.jsonl"])
    values = {}
    setup_ms = {arm: [] for arm in ARMS}
    sources = Counter()
    pids = set()
    active_readers = 0
    previous = 0
    for row, (epoch, batch, arm, order) in zip(rows, schedule(), strict=True):
        require(
            (row["epoch"], row["batch"], row["arm"]) == (epoch, batch, arm),
            "Diagnostic run order differs",
        )
        start, ready, closed = row["session_ns"]
        require(previous <= start < ready < closed, "Invalid diagnostic session timer")
        require(
            type(row["pid"]) is int
            and row["pid"] > 0
            and row["pid"] not in pids
            and row["cpu_source"] in CPU_SOURCES,
            "Invalid native reader identity",
        )
        pids.add(row["pid"])
        sources[row["cpu_source"]] += 1
        setup_ms[arm].append((ready - start) / 1e6)
        request_end = ready
        records = []
        for pos, (req, index) in enumerate(zip(row["requests"], order, strict=True), 1):
            expected = reference[index]
            require(
                req["id"] == expected["id"]
                and matches(req["output"], expected["native"]["output"]),
                "Diagnostic request differs from frozen native output",
            )
            spans, switches, request_end = components(req, arm != "native-C", request_end)
            records.append((pos, spans, switches))
        require(request_end <= closed, "Backend samples exceed session timer")
        # Zero run-queue wait is meaningful if the backend's timeslice or wait counters advanced.
        active = any(switches or spans["scheduler_wait"] for _, spans, switches in records)
        active_readers += bool(active)
        for pos, spans, _ in records:
            if not active:
                spans["scheduler_wait"] = None
            values[epoch, batch, pos, arm] = spans
        previous = closed
    return values, setup_ms, dict(sources), active_readers


def pair_report(pairs):
    report = {}
    keys = set.intersection(*(set(row) for row in pairs))
    for metric in sorted(keys - {"batch"}):
        by_batch = [
            fmean(row[metric] for row in pairs if row["batch"] == b) for b in range(BATCHES)
        ]
        report[metric] = {"gap_ms": fmean(by_batch), "ci95_ms": interval(by_batch)}
    return report


def summarize(values, setup_ms):
    logged_pairs = []
    control_pairs = []
    examples = []
    for (epoch, batch, position, arm), a in values.items():
        if arm != "native-A":
            continue
        b = values[epoch, batch, position, "native-B"]
        c = values[epoch, batch, position, "native-C"]
        diff = {k: b[k] - v for k, v in a.items() if v is not None and b[k] is not None}
        overhead = {
            k: (a[k] + b[k]) / 2 - v
            for k, v in c.items()
            if v is not None and a.get(k) is not None and b.get(k) is not None
        }
        logged_pairs.append({"batch": batch, **diff})
        control_pairs.append({"batch": batch, **overhead})
        examples.append(
            {"epoch": epoch, "batch": batch, "position": position, "B_minus_A_ms": diff}
        )
    stats = {}
    for arm in ARMS:
        requests = [r for (_, _, _, label), r in values.items() if label == arm]
        keys = set.union(*(set(r) for r in requests))
        stats[arm] = {"setup_mean_ms": fmean(setup_ms[arm]), "components_ms": {}}
        for metric in sorted(keys):
            samples = [r[metric] for r in requests if r.get(metric) is not None]
            stats[arm]["components_ms"][metric] = {
                "count": len(samples),
                "mean": fmean(samples) if samples else None,
                "median_p95_max": np.quantile(samples, [0.50, 0.95, 1.0]).tolist()
                if samples
                else None,
            }
        stats[arm]["mean_request_ms_by_position"] = [
            fmean(
                row["request"]
                for (_, _, p, label), row in values.items()
                if p == pos and label == arm
            )
            for pos in range(1, SIZE + 1)
        ]
    correlations = {}
    for metric in (
        "server_execute",
        "server_total",
        "client_execute_residual",
        "backend_cpu",
        "scheduler_wait",
    ):
        pair_values = [(r["request"], r[metric]) for r in logged_pairs if metric in r]
        if len(pair_values) > 1:
            a, b = zip(*pair_values, strict=True)
            if len(set(a)) > 1 and len(set(b)) > 1:
                correlations[metric] = {"r": correlation(a, b), "matched_pairs": len(a)}
    return {
        "arms": stats,
        "logged_B_minus_A_ms": pair_report(logged_pairs),
        "logged_mean_minus_logging_off_ms": pair_report(control_pairs),
        "request_gap_correlations": correlations,
        "largest_identical_path_gaps": sorted(
            examples, key=lambda r: abs(r["B_minus_A_ms"]["request"]), reverse=True
        )[:12],
    }


def reconstruct(directory, hashes):
    require(set(hashes) == RAW, "Unexpected diagnostic raw return inventory")
    for name, digest in hashes.items():
        require(file_sha(directory / name) == digest, f"Return hash differs: {name}")
    require(hashes["quality.jsonl"] == PRIOR_QUALITY_SHA, "Expected the pinned recall reference")
    reference = list(pinned_lines(directory / "quality.jsonl", PRIOR_QUALITY_SHA))
    eligible = set(json.loads(pinned(directory / "eligible.json", hashes["eligible.json"])))
    require(len(eligible) == 49498, "Invalid native eligible cohort")
    counters = json.loads(pinned(directory / "counters.json", hashes["counters.json"]))
    values, setup_ms, sources, active = read_timing(directory, hashes, reference)
    require(len(values) == 1080 and sum(sources.values()) == 108, "Incomplete diagnostic schedule")
    return {
        "sessions": 108,
        "requests": 1080,
        "logged_requests": 720,
        "native_recall_reference": quality(reference, eligible)["native"],
        "cpu_sources_by_reader": sources,
        "kernel_sched_schedstats": counters["kernel_sched_schedstats"],
        "readers_with_active_scheduler_counters": active,
        **summarize(values, setup_ms),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    receipt = json.loads((args.directory / "receipt.json").read_text())
    result = reconstruct(args.directory, receipt["raw_sha256"])
    require(
        equivalent(json.loads(json.dumps(result)), receipt["analysis"]), "Remote analysis differs"
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
