"""Verify the warm-up test and reconstruct both timing conditions from raw data."""

import argparse
import json
import math
from pathlib import Path
from statistics import fmean

from analyze import BATCHES, FAMILIES, SIZE, equivalent, matches, quality
from rb_plan import file_sha, pinned, pinned_lines, require
from rb_stats import aa_equivalent, interval
from warmup_plan import schedule

RAW = {"quality.jsonl", "timing.jsonl", "eligible.json", "lookup.json"}
MIRRORS = (False, True)
LABELS = "AB"
COUNTS = (0, 2)


def request_times(requests, order, reference, family, start, end):
    times = []
    for request, index in zip(requests, order, strict=True):
        begin, finish = request["request_ns"]
        case = reference[index]
        require(start <= begin < finish <= end, "Invalid request timer")
        require(
            request["id"] == case["id"] and matches(request["output"], case[family]["output"]),
            "Timed request changed a frozen output",
        )
        times.append((finish - begin) / 1e6)
        start = finish
    return times


def read_timing(directory, hashes, rows, lookup):
    attach_times = iter(lookup["timed_attaches"])
    cells = {}
    previous = 0
    timed = pinned_lines(directory / "timing.jsonl", hashes["timing.jsonl"])
    for record, plan in zip(timed, schedule(), strict=True):
        batch, count, mirror, slot, arm, warmup, scored = plan
        require(
            (
                record["batch"],
                record["warmup_count"],
                record["mirror"],
                record["slot"],
                record["arm"],
            )
            == (batch, count, mirror, slot, arm),
            "Timing order differs from the frozen schedule",
        )
        start, ready, warmed, closed = record["session_ns"]
        require(
            previous <= start < ready <= warmed < closed and (warmed > ready) == bool(count),
            "Invalid session or warm-up timer",
        )
        previous = closed
        family, label = arm.rsplit("-", 1)
        warming = request_times(record["warmup"], warmup, rows, family, ready, warmed)
        measured = request_times(record["queries"], scored, rows, family, warmed, closed)
        attach = None
        if family != "native":
            sample = next(attach_times)
            attach_ns = sample["attach_ns"]
            require(
                sample["family"] == family
                and type(attach_ns) is int
                and 0 < attach_ns <= ready - start,
                "Invalid shared lookup attach timer",
            )
            attach = attach_ns / 1e6
        cells[batch, count, mirror, family, label] = {
            "query_ms": fmean(measured),
            "first_query_ms": measured[0],
            "second_query_ms": measured[1],
            "queries_3_to_10_ms": fmean(measured[2:]),
            "startup_ms": (ready - start) / 1e6,
            "attach_ms": attach,
            "warmup_ms": (warmed - ready) / 1e6,
            "warmup_request_ms": sum(warming),
            "full_session_ms": (closed - start) / 1e6,
            "full_session_per_query_ms": (closed - start) / (SIZE * 1e6),
        }
    require(next(attach_times, None) is None, "Unexpected extra lookup attachments")
    return cells


def paired(blocks):
    gaps = [fmean(a - b for a, b in pairs) for pairs in blocks]
    logs = [fmean(math.log(a / b) for a, b in pairs) for pairs in blocks]
    return {
        "gap_ms": fmean(gaps),
        "gap_ci95_ms": interval(gaps),
        "gap_by_batch_ms": gaps,
        "log_ratio": fmean(logs),
        "log_ratio_ci95": interval(logs),
    }


def summarize(cells, count):
    means = {}
    for f in FAMILIES:
        sessions = [x for (_, n, _, family, _), x in cells.items() if n == count and family == f]
        means[f] = {
            key: None if value is None else fmean(x[key] for x in sessions)
            for key, value in sessions[0].items()
        }

    def aa(family, metric, mirrors):
        return paired(
            [
                [
                    (
                        cells[b, count, m, family, "B"][metric],
                        cells[b, count, m, family, "A"][metric],
                    )
                    for m in mirrors
                ]
                for b in range(BATCHES)
            ]
        )

    metrics = ("query_ms", "full_session_per_query_ms")
    controls = {k: {f: aa(f, k, MIRRORS) for f in FAMILIES} for k in metrics}
    return {
        "means_ms": means,
        "aa_controls": controls,
        "aa_pass_by_family": {
            k: {f: aa_equivalent(stats) for f, stats in controls[k].items()} for k in metrics
        },
        "query_aa_by_order": {
            name: {f: aa(f, "query_ms", (mirror,)) for f in FAMILIES}
            for mirror, name in ((False, "original"), (True, "mirrored"))
        },
        "paired_contrasts": {
            metric: {
                f"{left}_vs_{right}": paired(
                    [
                        [
                            (
                                cells[b, count, m, left, label][metric],
                                cells[b, count, m, right, label][metric],
                            )
                            for m in MIRRORS
                            for label in LABELS
                        ]
                        for b in range(BATCHES)
                    ]
                )
                for left, right in (
                    ("candidate", "native"),
                    ("baseline", "native"),
                    ("candidate", "baseline"),
                )
            }
            for metric in metrics
        },
    }


def reconstruct(directory, hashes):
    require(set(hashes) == RAW, "Unexpected raw return inventory")
    for name, digest in hashes.items():
        require(file_sha(directory / name) == digest, f"Return hash differs: {name}")
    lookup = json.loads(pinned(directory / "lookup.json", hashes["lookup.json"]))
    build = lookup["build"]
    parts = [build[k] for k in ("open_and_lock_ns", "fetch_ns", "pack_publish_ns")]
    require(
        all(type(x) is int and x > 0 for x in parts)
        and sum(parts) == build["total_ns"]
        and build["rows"] == 247286
        and build["qualifying"] == 49498,
        "Invalid build timer or cohort",
    )
    rows = list(pinned_lines(directory / "quality.jsonl", hashes["quality.jsonl"]))
    eligible = set(json.loads(pinned(directory / "eligible.json", hashes["eligible.json"])))
    require(len(eligible) == 49498, "Invalid eligibility inventory")
    recall = quality(rows, eligible)
    cells = read_timing(directory, hashes, rows, lookup)
    require(len(cells) == 144, "Invalid session count")

    def warmup_effect(family, metric):
        return paired(
            [
                [
                    (cells[b, 2, m, family, label][metric], cells[b, 0, m, family, label][metric])
                    for m in MIRRORS
                    for label in LABELS
                ]
                for b in range(BATCHES)
            ]
        )

    return {
        "scope": "One diagnostic allocation with the same 60 frozen queries",
        "timed_sessions": len(cells),
        "scored_requests": len(cells) * SIZE,
        "warmup_requests": sum(count for _, count, _, _, _ in cells),
        "build": build,
        "prior_job": lookup["prior_job"],
        "prior_quality_sha256": lookup["prior_quality_sha256"],
        "recall": recall,
        "conditions": {str(count): summarize(cells, count) for count in COUNTS},
        "warmup_effect_two_minus_zero": {
            f: {
                metric: warmup_effect(f, metric)
                for metric in ("query_ms", "first_query_ms", "full_session_ms")
            }
            for f in FAMILIES
        },
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
