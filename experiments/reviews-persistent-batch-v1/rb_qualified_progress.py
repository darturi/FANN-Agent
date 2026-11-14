"""Score a verified votes108 shadow return against the saved checkpoint-32 stops."""

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import fmean

from rb_evidence import PILOT_REFS, Evidence
from rb_feedback import DevelopmentReplay
from rb_plan import PILOT_BLOCK, ROOT, digest, pinned_lines, require
from rb_stats import NATIVE_FLOOR, RECALL_RESERVE, interval, quality

CHECKPOINTS = (16, 32)
FILTER = "votes108"
THRESHOLDS = (0.0, 0.001, 0.005, 0.01)
FRONTIER_THRESHOLDS = (-0.20, -0.10, -0.05, -0.02, -0.01, 0.0, 0.01, 0.02, 0.05, 0.10, 0.20)


def read_shadow(path, sha, replay):
    expected = {qid for qid, case in replay.plan.cases.items() if case.stratum == FILTER}
    trace_digests = {
        row["query_id"]: digest(row["states"]["light19"])
        for row in pinned_lines(ROOT / PILOT_BLOCK / "references.jsonl", PILOT_REFS)
        if row["query_id"] in expected
    }
    rows = {}
    for row in pinned_lines(path, sha):
        qid = row["query_id"]
        require(qid in expected and qid not in rows, "Unexpected or duplicate shadow case")
        require(
            row["output"] == replay.references[qid]["native"]
            and row["light19_trace_sha256"] == trace_digests[qid],
            "Shadow changed the output or original traversal trace",
        )
        samples = row["checkpoints"]
        reached = [cp for cp in CHECKPOINTS if cp in replay.traces[qid]["light19"]]
        require([sample["checkpoint"] for sample in samples] == reached, "Checkpoint mismatch")
        for sample in samples:
            count, distance = sample["qualifying_count"], sample["tenth_distance"]
            require(
                type(count) is int
                and count >= 0
                and (
                    distance is None
                    if count < 10
                    else (
                        type(distance) in (int, float) and math.isfinite(distance) and distance >= 0
                    )
                )
                and type(sample["collection_ns"]) is int
                and sample["collection_ns"] >= 0
                and type(sample["extra_heap_fetches"]) is int
                and sample["extra_heap_fetches"] == 0,
                "Invalid observation or extra heap access",
            )
        rows[qid] = samples
    require(rows.keys() == expected, "Incomplete shadow cohort")
    return rows


def signal(samples):
    if len(samples) != 2 or any(sample["tenth_distance"] is None for sample in samples):
        return None
    before, after = (sample["tenth_distance"] for sample in samples)
    return abs(before - after)


def choose_threshold(qids, values, scores, native, grid=THRESHOLDS):
    """Choose the highest coverage that meets the recall reserve in training groups."""
    if fmean(native[q] for q in qids) < NATIVE_FLOOR:
        return None
    feasible = []
    for threshold in grid:
        stops = {q for q in qids if values[q] is not None and values[q] <= threshold}
        if not stops or any(not scores[q][1] for q in stops):
            continue
        deltas = [scores[q][0] - native[q] if q in stops else 0.0 for q in qids]
        if interval(deltas)[0] >= RECALL_RESERVE:
            feasible.append((len(stops), -threshold))
    return -max(feasible)[1] if feasible else None


def assess(replay, rows, *, frontier=False):
    count_ready = {qid for qid, samples in rows.items() if signal(samples) is not None}
    values = {qid: signal(samples) for qid, samples in rows.items()}
    grid = THRESHOLDS
    if frontier:
        # Negate the signed gap so the same threshold selector can use <=.
        grid = FRONTIER_THRESHOLDS
        for qid, samples in rows.items():
            tenth = next((s["tenth_distance"] for s in samples if s["checkpoint"] == 32), None)
            trace = replay.traces[qid]["light19"].get(32)
            pending = trace["features"].get("frontier_distance_min") if trace else None
            values[qid] = tenth - pending if tenth is not None and pending is not None else None
    scored = count_ready | {qid for qid, value in values.items() if value is not None}
    require(
        all(
            replay.proofs["progress34", qid, 32][1] == replay.proofs["static23", qid, 32][1]
            for qid in scored
        ),
        "Saved checkpoint-32 outcomes disagree across profiles",
    )
    scores = {qid: replay.stop_scores["progress34", qid, 32] for qid in scored}
    native = replay.native_scores
    thresholds = {}
    stop_ids = set()
    folds = {}
    for fold in range(5):
        test = sorted(q for q in rows if replay.folds[replay.plan.cases[q].group] == fold)
        train = sorted(rows.keys() - set(test))
        threshold = choose_threshold(train, values, scores, native, grid)
        thresholds[fold] = threshold
        selected = {
            q
            for q in test
            if threshold is not None and values[q] is not None and values[q] <= threshold
        }
        stop_ids.update(selected)
        folds[fold] = {
            "cases": len(test),
            "signal_available": sum(values[q] is not None for q in test),
            "selected_stops": len(selected),
            "recall_losses": sum(scores[q][0] < native[q] for q in selected),
            "invalid_top10": sum(not scores[q][1] for q in selected),
        }

    def replay_rule(stops):
        outcomes = {}
        for qid, case in replay.plan.cases.items():
            if case.stratum == FILTER:
                cp = 32 if qid in stops else None
                profile = "progress34"
            else:
                cp = replay.first_stop(replay.seed, qid)
                profile = "light19"
            output = (
                replay.references[qid]["native"]
                if cp is None
                else replay.proofs[profile, qid, cp][1]
            )
            outcomes[qid] = {"stop": cp is not None, "output": output}
        evidence = Evidence(replay.references, replay.eligible, {}, {}, {"checked": outcomes})
        report = quality(replay.plan, replay.frozen, evidence, "checked")
        report["votes108_stops"] = len(stops)
        report["votes108_safe_stops"] = sum(
            scores[q][1] and scores[q][0] >= native[q] for q in stops
        )
        report["votes108_recall_losing_stops"] = sum(
            scores[q][1] and scores[q][0] < native[q] for q in stops
        )
        report["votes108_incomplete_or_invalid_stops"] = sum(not scores[q][1] for q in stops)
        return report

    count_only = replay_rule(count_ready)
    conditional = replay_rule(stop_ids)
    costs = {}
    for label, selected in (
        ("all", rows.keys()),
        ("would_stop", stop_ids),
        ("would_continue", rows.keys() - stop_ids),
    ):
        totals = [
            sum(s["collection_ns"] for s in rows[q] if not frontier or s["checkpoint"] == 32)
            for q in selected
        ]
        costs[label] = {
            "requests": len(totals),
            "mean_collection_ns": fmean(totals) if totals else None,
        }
    # The distance rule is a subset of count-only stops. Its opportunity is to rescue
    # recall when counting alone fails.
    has_signal = conditional["passes"] and bool(stop_ids) and not count_only["passes"]
    diagnostics = {}
    if frontier:
        classes = {}
        for label in ("safe", "recall_loss", "invalid"):
            gaps = sorted(
                -value
                for q, value in values.items()
                if value is not None
                and label
                == (
                    "invalid"
                    if not scores[q][1]
                    else "safe"
                    if scores[q][0] >= native[q]
                    else "recall_loss"
                )
            )
            classes[label] = {
                "count": len(gaps),
                "quantiles_0_25_50_75_100": [
                    gaps[round((len(gaps) - 1) * p)] for p in (0, 0.25, 0.5, 0.75, 1)
                ]
                if gaps
                else [],
            }
        diagnostics = {
            "gap_definition": "nearest pending distance minus tenth qualifying distance",
            "stop_condition": "gap >= threshold",
            "gap_by_outcome": classes,
            "gap_sign_by_outcome": dict(
                Counter(
                    ("positive" if value < 0 else "nonpositive")
                    + "_"
                    + (
                        "invalid"
                        if not scores[q][1]
                        else "safe"
                        if scores[q][0] >= native[q]
                        else "recall_loss"
                    )
                    for q, value in values.items()
                    if value is not None
                )
            ),
        }
    return {
        **diagnostics,
        "scope": "Exposed development shadow observations joined to saved stop proofs",
        "threshold_grid": sorted(-t for t in grid) if frontier else grid,
        "threshold_by_fold": {f: -t if t is not None else None for f, t in thresholds.items()}
        if frontier
        else thresholds,
        "folds": folds,
        "count_only": count_only,
        ("frontier_gap" if frontier else "distance_change"): conditional,
        "shadow_collection_cost": costs,
        "status": "signal_screen_pass" if has_signal else "abstain",
        "measured_policy_latency": None,
        "independent_confirmation": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shadow_return", type=Path)
    parser.add_argument("--sha256", required=True, help="Digest from the verified return manifest")
    parser.add_argument(
        "--frontier", action="store_true", help="Replay the checkpoint-32 signed gap"
    )
    args = parser.parse_args()
    replay = DevelopmentReplay()
    rows = read_shadow(args.shadow_return, args.sha256, replay)
    print(json.dumps(assess(replay, rows, frontier=args.frontier), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
