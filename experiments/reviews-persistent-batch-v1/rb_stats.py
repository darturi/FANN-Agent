"""Recall and complete-session timing gates for the frozen development design."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import fmean
from types import SimpleNamespace

import numpy as np
from rb_plan import ARMS, DRAWS, FAMILIES, FILTERS, SEED, SESSION_LENGTH, require

RECALL_RESERVE = -0.0025
NATIVE_FLOOR = 0.95
ABSOLUTE_EQUIVALENCE_MS = 0.10
RELATIVE_EQUIVALENCE = math.log(1.02)


def aa_equivalent(cell):
    abs_lo, abs_hi = cell["gap_ci95_ms"]
    log_lo, log_hi = cell["log_ratio_ci95"]
    return (
        -ABSOLUTE_EQUIVALENCE_MS <= abs_lo <= abs_hi <= ABSOLUTE_EQUIVALENCE_MS
        and -RELATIVE_EQUIVALENCE <= log_lo <= log_hi <= RELATIVE_EQUIVALENCE
    )


def interval(cluster_values):
    values = np.asarray(cluster_values, dtype=float)
    require(len(values) > 1 and bool(np.isfinite(values).all()), "Invalid bootstrap input")
    rng = np.random.default_rng(SEED)
    boot = values[rng.integers(0, len(values), size=(DRAWS, len(values)))].mean(axis=1)
    return np.quantile(boot, (0.025, 0.975), axis=0).tolist()


def exact_truth(frozen, ref, eligible):
    truth = ref["truth"]
    return frozen.exact_truth(
        len(eligible), truth["k"], frozenset(truth["strict"]), frozenset(truth["ties"]), eligible
    )


def result_score(frozen, truth, output):
    ids, distances = output
    require(
        len(ids) == len(distances)
        and all(type(i) is int for i in ids)
        and all(type(d) in (int, float) and math.isfinite(d) for d in distances),
        "Invalid returned IDs or distances",
    )
    scored = frozen.score(truth, SimpleNamespace(ids=ids))
    return scored["recall"], bool(scored["valid"] and len(ids) == 10)


def quality(plan, frozen, evidence, family):
    rows = []
    for qid, case in plan.cases.items():
        ref = evidence.references[qid]
        result = evidence.outcomes[family][qid]
        truth = exact_truth(frozen, ref, evidence.eligible[case.stratum])
        native, native_ok = result_score(frozen, truth, ref["native"])
        policy, policy_ok = result_score(frozen, truth, result["output"])
        rows.append((case.group, case.stratum, native, policy, native_ok and policy_ok))
    report = {}
    for filt in ("overall", *FILTERS):
        selected = [r for r in rows if filt == "overall" or r[1] == filt]
        groups = defaultdict(list)
        for group, _, native, policy, _ in selected:
            groups[group].append(policy - native)
        require(len(groups) == 200, "Incomplete recall vector groups")
        values = [fmean(groups[group]) for group in sorted(groups)]
        lower, upper = interval(values)
        native_mean = fmean(row[2] for row in selected)
        valid = all(row[4] for row in selected)
        report[filt] = {
            "case_count": len(selected),
            "native_recall": native_mean,
            "policy_recall": fmean(row[3] for row in selected),
            "recall_delta": fmean(values),
            "recall_delta_ci95": [lower, upper],
            "valid_top10": valid,
            "passes": valid
            and lower >= RECALL_RESERVE
            and (filt == "overall" or native_mean >= NATIVE_FLOOR),
        }
    stops = sum(record["stop"] for record in evidence.outcomes[family].values())
    return {
        "passes": stops > 0 and all(r["passes"] for r in report.values()),
        "stops": stops,
        "recall": report,
    }


def quality_reports(plan, frozen, evidence):
    candidate = quality(plan, frozen, evidence, "candidate")
    seed = quality(plan, frozen, evidence, "seed")
    return {
        "candidate": candidate,
        "seed": seed,
        "passes": candidate["passes"] and seed["recall"]["overall"]["valid_top10"],
    }


def timing(plan, rows, *, aa_only=False):
    """Reconstruct intervals from a complete, ordered, independently checked return."""
    cells = {}
    by_position = defaultdict(list)
    first_eligible = defaultdict(list)
    for row, (epoch, session, arm) in zip(rows, plan.timed(), strict=True):
        require(
            (row["epoch"], row["session_id"], row["arm"]) == (epoch, session.id, arm),
            "Timed schedule changed",
        )
        times = row["boundary_ns"]
        require(
            len(times) == 5
            and all(type(ns) is int for ns in times)
            and times == sorted(times)
            and times[0] < times[-1],
            "Invalid timed session boundaries",
        )
        require(len(row["requests"]) == SESSION_LENGTH, "Incomplete timed session")
        previous = times[2]
        for pos, (record, case) in enumerate(zip(row["requests"], session.cases, strict=True), 1):
            start, end = record["request_ns"]
            require(
                record["query_id"] == case.id
                and type(start) is int
                and type(end) is int
                and previous <= start < end <= times[3],
                "Invalid timed request sequence",
            )
            previous = end
            by_position[arm, pos].append((end - start) / 1e6)
            if record["installations"]:
                first_eligible[arm].append((end - start) / 1e6)
        cells[epoch, session.id, arm] = (times[-1] - times[0]) / 1e6

    aa = defaultdict(lambda: defaultdict(list))
    direct = defaultdict(lambda: defaultdict(list))
    epoch_gaps = defaultdict(lambda: defaultdict(list))
    pairs = (("candidate", "native"), ("seed", "native"), ("candidate", "seed"))
    for epoch in range(2):
        for session in plan.sessions:
            means = {}
            for family in FAMILIES:
                a, b = (cells[epoch, session.id, f"{family}-{label}"] for label in "AB")
                aa[family][session.block].append(((b - a) / SESSION_LENGTH, math.log(b / a)))
                means[family] = (a + b) / 2
            if not aa_only:
                for left, right in pairs:
                    key = f"{left}_vs_{right}"
                    a, b = means[left], means[right]
                    direct[key][session.block].append((a - b, math.log(a / b)))
                    epoch_gaps[key][epoch].append(a - b)

    def summarize(blocks):
        require(
            set(blocks) == set(range(20)) and all(len(v) == 6 for v in blocks.values()),
            "Incomplete timing bootstrap blocks",
        )
        values = [list(map(fmean, zip(*blocks[b], strict=True))) for b in sorted(blocks)]
        lo, hi = interval(values)
        return {
            "gap_ms": fmean(v[0] for v in values),
            "gap_ci95_ms": [lo[0], hi[0]],
            "log_ratio": fmean(v[1] for v in values),
            "log_ratio_ci95": [lo[1], hi[1]],
        }

    aa_report = {family: summarize(blocks) for family, blocks in aa.items()}
    for cell in aa_report.values():
        cell["passes"] = aa_equivalent(cell)
    aa_pass = all(cell["passes"] for cell in aa_report.values())
    if aa_only:
        return {"aa_pass": aa_pass, "aa_per_request": aa_report}
    contrasts = {key: summarize(blocks) for key, blocks in direct.items()}
    for key, cell in contrasts.items():
        cell["epoch_gap_ms"] = [fmean(epoch_gaps[key][e]) for e in range(2)]
    primary = contrasts["candidate_vs_native"]
    faster = primary["log_ratio_ci95"][1] < 0 and all(g < 0 for g in primary["epoch_gap_ms"])
    return {
        "aa_pass": aa_pass,
        "latency_pass": faster,
        "aa_per_request": aa_report,
        "session_contrasts": contrasts,
        "mean_ms_by_position": {
            arm: [fmean(by_position[arm, pos]) for pos in range(1, SESSION_LENGTH + 1)]
            for arm in ARMS
        },
        "mean_first_eligible_ms": {arm: fmean(values) for arm, values in first_eligible.items()},
    }
