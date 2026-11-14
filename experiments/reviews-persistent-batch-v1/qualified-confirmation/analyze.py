"""Reconstruct the fresh-query recall and latency gates from the raw return."""

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import fmean

from rb_plan import WILLIAMS_ROW, file_sha, pinned_lines, require
from rb_stats import aa_equivalent, interval

FAMILIES = ("native", "baseline", "candidate")
ARMS = tuple(f"{family}-{label}" for family in FAMILIES for label in "AB")
EPOCHS = 6
BATCHES = 6
SIZE = 10
RECALL_MARGIN = -0.005
NATIVE_FLOOR = 0.95
CHECKPOINTS = {"native": {0}, "baseline": {0, 32}, "candidate": {0, 16, 32, 64}}


def schedule():
    for epoch in range(EPOCHS):
        for position in range(BATCHES):
            batch = (epoch + (-position if epoch % 2 else position)) % BATCHES
            arms = [ARMS[(i + batch + epoch) % len(ARMS)] for i in WILLIAMS_ROW]
            order = [(i + epoch * 2) % SIZE for i in range(SIZE)]
            for arm in arms:
                yield epoch, batch, arm, order


def score(exact, output, eligible):
    require(
        len(exact) >= SIZE
        and len({i for i, _ in exact}) == len(exact)
        and all(i in eligible and math.isfinite(d) for i, d in exact)
        and all(a[1] <= b[1] for a, b in zip(exact, exact[1:]))
        and exact[-1][1] == exact[SIZE - 1][1],
        "Invalid exact reference",
    )
    boundary = exact[SIZE - 1][1]
    strict = {i for i, d in exact if d < boundary}
    ties = {i for i, d in exact if d == boundary}
    ids = {i for i, _ in output}
    valid = len(output) == len(ids) == SIZE and all(
        i in eligible and math.isfinite(d) for i, d in output
    )
    return (len(ids & strict) + min(SIZE - len(strict), len(ids & ties))) / SIZE, valid


def matches(a, b):
    return len(a) == len(b) and all(
        i == j and math.isfinite(d) and math.isfinite(e) and abs(d - e) <= 1e-12
        for (i, d), (j, e) in zip(a, b)
    )


def quality(rows, eligible):
    require(len(rows) == len({r["id"] for r in rows}) == BATCHES * SIZE, "Incomplete quality")
    rec = {f: [score(r["exact"], r[f]["output"], eligible) for r in rows] for f in FAMILIES}
    native = [r for r, _ in rec["native"]]
    native_valid = all(valid for _, valid in rec["native"])
    summary = {}
    for family, scored in rec.items():
        values = [r for r, _ in scored]
        deltas = [r - n for r, n in zip(values, native, strict=True)]
        lo, hi = interval(deltas)
        cps = [r[family]["checkpoint"] for r in rows]
        require(set(cps) <= CHECKPOINTS[family], "Unexpected stop checkpoint")
        for row in rows:
            if not row[family]["checkpoint"]:
                require(
                    matches(row[family]["output"], row["native"]["output"]),
                    "A continue changed native output",
                )
        valid = all(ok for _, ok in scored)
        summary[family] = {
            "recall": fmean(values),
            "delta_vs_native": fmean(deltas),
            "delta_ci95": [lo, hi],
            "valid_top10": valid,
            "stops_by_checkpoint": dict(sorted(Counter(cp for cp in cps if cp).items())),
            "queries_losing_recall": sum(d < 0 for d in deltas),
            "passes": (
                valid
                and native_valid
                and fmean(native) >= NATIVE_FLOOR
                and lo >= RECALL_MARGIN - 1e-12
                and (family == "native" or any(cps))
            ),
        }
    return summary


def timing(quality_rows, timed, *, query_controls=False):
    cells = {}
    for record, (epoch, batch, arm, order) in zip(timed, schedule(), strict=True):
        require(
            (record["epoch"], record["batch"], record["arm"]) == (epoch, batch, arm),
            "Timing schedule differs",
        )
        cases = [quality_rows[batch * SIZE + i] for i in order]
        start, ready, closed = record["session_ns"]
        require(start < ready < closed, "Invalid complete-session timer")
        prev = ready
        elapsed = []
        family = arm.rsplit("-", 1)[0]
        for req, expected in zip(record["queries"], cases, strict=True):
            begin, end = req["request_ns"]
            require(prev <= begin < end <= closed, "Invalid request timer")
            require(
                req["id"] == expected["id"] and matches(req["output"], expected[family]["output"]),
                "Timed result differs from the quality pass",
            )
            elapsed.append(end - begin)
            prev = end
        cells[epoch, batch, arm] = ((closed - start) / SIZE, fmean(elapsed), ready - start)

    def summarize(contrasts):
        gap = [
            fmean((left - right) / 1e6 for left, right in contrasts[batch])
            for batch in range(BATCHES)
        ]
        logs = [
            fmean(math.log(left / right) for left, right in contrasts[batch])
            for batch in range(BATCHES)
        ]
        return {
            "gap_ms": fmean(gap),
            "gap_ci95_ms": interval(gap),
            "log_ratio": fmean(logs),
            "log_ratio_ci95": interval(logs),
        }

    def contrast(left, right, metric):
        pairs = {}
        by_epoch = []
        for epoch in range(EPOCHS):
            epoch_gaps = []
            for batch in range(BATCHES):
                a = fmean(cells[epoch, batch, arm][metric] for arm in left)
                b = fmean(cells[epoch, batch, arm][metric] for arm in right)
                pairs.setdefault(batch, []).append((a, b))
                epoch_gaps.append((a - b) / 1e6)
            by_epoch.append(fmean(epoch_gaps))
        return {**summarize(pairs), "epoch_gap_ms": by_epoch}

    controls = {f: contrast([f"{f}-B"], [f"{f}-A"], 0) for f in FAMILIES}
    comparison = {}
    for metric, label in enumerate(("session_per_query", "request")):
        comparison[label] = {
            f"{left}_vs_{right}": contrast(
                [f"{left}-A", f"{left}-B"], [f"{right}-A", f"{right}-B"], metric
            )
            for left, right in (
                ("candidate", "native"),
                ("baseline", "native"),
                ("candidate", "baseline"),
            )
        }
    averages = {
        family: {
            "session_per_query_ms": fmean(v[0] for k, v in cells.items() if k[2].startswith(family))
            / 1e6,
            "request_ms": fmean(v[1] for k, v in cells.items() if k[2].startswith(family)) / 1e6,
            "startup_ms": fmean(v[2] for k, v in cells.items() if k[2].startswith(family)) / 1e6,
        }
        for family in FAMILIES
    }
    result = {
        "paired_batches": BATCHES,
        "epochs": EPOCHS,
        "sessions": len(cells),
        "ann_requests": len(cells) * SIZE,
        "means": averages,
        "session_aa": controls,
        "aa_pass": all(aa_equivalent(control) for control in controls.values()),
        "comparison": comparison,
    }
    if query_controls:
        request_aa = {f: contrast([f"{f}-B"], [f"{f}-A"], 1) for f in FAMILIES}
        result["request_aa"] = request_aa
        result["request_aa_pass_by_family"] = {
            f: aa_equivalent(control) for f, control in request_aa.items()
        }
    return result


def report(directory, hashes, *, query_controls=False):
    quality_rows = list(pinned_lines(directory / "quality.jsonl", hashes["quality.jsonl"]))
    eligible = set(json.loads((directory / "eligible.json").read_text()))
    require(len(eligible) == 49498, "Eligibility coverage differs")
    recall = quality(quality_rows, eligible)
    latency = timing(
        quality_rows,
        pinned_lines(directory / "timing.jsonl", hashes["timing.jsonl"]),
        query_controls=query_controls,
    )
    primary = latency["comparison"]["session_per_query"]["candidate_vs_native"]
    faster = primary["log_ratio_ci95"][1] < 0 and all(g < 0 for g in primary["epoch_gap_ms"])
    return {
        "recall": recall,
        "latency": latency,
        "candidate_passes_recall_and_native_latency": (
            recall["candidate"]["passes"] and latency["aa_pass"] and faster
        ),
    }


def equivalent(a, b):
    if type(a) is float:
        return type(b) is float and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(a, dict):
        return (
            isinstance(b, dict)
            and a.keys() == b.keys()
            and all(equivalent(value, b[key]) for key, value in a.items())
        )
    if isinstance(a, list):
        return (
            isinstance(b, list)
            and len(a) == len(b)
            and all(equivalent(x, y) for x, y in zip(a, b, strict=True))
        )
    return type(a) is type(b) and a == b


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    remote = json.loads((args.directory / "receipt.json").read_text())
    hashes = remote["raw_sha256"]
    require(
        set(hashes) == {"quality.jsonl", "timing.jsonl", "eligible.json"},
        "Unexpected raw return inventory",
    )
    for name, digest in hashes.items():
        require(file_sha(args.directory / name) == digest, f"Return hash differs: {name}")
    result = report(args.directory, hashes)
    # Normalize JSON map keys before comparison. libm and NumPy can differ by an ulp.
    require(
        equivalent(json.loads(json.dumps(result)), remote["analysis"]),
        "Remote result did not reproduce",
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
