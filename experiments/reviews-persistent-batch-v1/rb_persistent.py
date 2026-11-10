"""Measure six consecutive Reviews batches per reader on the frozen development workload."""

import math
from collections import defaultdict
from statistics import fmean

import rb_calibration
from rb_calibration import make_backend as make_backend
from rb_measure import check_timed
from rb_plan import ARMS, FAMILIES, SESSION_LENGTH, WILLIAMS_ROW, Session, require
from rb_stats import aa_equivalent, interval, quality_reports
from rb_verify import check_identity, check_requests

WORKLOADS = 10
BATCHES = 6
EPOCHS = 3
REQUESTS = BATCHES * SESSION_LENGTH
STEADY_REQUESTS = REQUESTS - SESSION_LENGTH
TIMED_READERS = WORKLOADS * EPOCHS * len(ARMS)
VERDICTS = (
    "measurement_inconclusive",
    "closed_negative_quality",
    "closed_negative_latency",
    "would_pass",
)


class Meter(rb_calibration.Meter):
    search_limits = {"timing": TIMED_READERS * REQUESTS}
    install_limits = {"timing": WORKLOADS * EPOCHS * 4}
    reader_limits = {"reference": 1, "timing": TIMED_READERS}


def schedule(plan, evidence, *, arms=ARMS):
    require(len(plan.sessions) == WORKLOADS * BATCHES, "Persistent workload size changed")
    for epoch in range(EPOCHS):
        workloads = range(WORKLOADS)
        for group in reversed(workloads) if epoch == 1 else workloads:
            batches = plan.sessions[group * BATCHES : (group + 1) * BATCHES]
            require(
                [batch.block for batch in batches] == [2 * group] * 3 + [2 * group + 1] * 3
                and all(len(batch.cases) == SESSION_LENGTH for batch in batches),
                "Persistent workload split a vector block",
            )
            offset = 2 * epoch
            ordered = batches[offset:] + batches[:offset]
            require(
                all(
                    any(case.stratum in policy["eligible"] for case in ordered[0].cases)
                    for policy in evidence.policies.values()
                ),
                "First batch cannot install both policies",
            )
            session = Session(
                f"reader-workload-{group + 1:02}",
                group,
                offset,
                tuple(case for batch in ordered for case in batch.cases),
            )
            shift = group + 2 * epoch
            for label in WILLIAMS_ROW:
                yield epoch, session, arms[(label + shift) % len(ARMS)]


def capture(plan, frozen, evidence, backend, meter, output, *, synthetic_only, after_snapshot):
    require(isinstance(meter, Meter), "Persistent measurement requires its own meter")
    rb_calibration.capture(
        plan,
        frozen,
        evidence,
        backend,
        meter,
        output,
        synthetic_only=synthetic_only,
        after_snapshot=after_snapshot,
        schedule=tuple(schedule(plan, evidence)),
        batch_size=SESSION_LENGTH,
    )


def measurements(row, previous_close):
    start, opened, admitted, closing, closed = row["boundary_ns"]
    ends = row["batch_end_ns"]
    timeline = [start, opened, admitted, *ends, closing, closed]
    require(
        len(ends) == BATCHES
        and all(type(ns) is int for ns in timeline)
        and previous_close <= start
        and timeline == sorted(timeline)
        and closed > start
        and len(row["requests"]) == REQUESTS,
        "Persistent reader or batch boundaries changed",
    )
    previous = admitted
    for position, record in enumerate(row["requests"]):
        begin, end = record["request_ns"]
        batch = position // SESSION_LENGTH
        require(
            type(begin) is int and type(end) is int and previous <= begin < end <= ends[batch],
            "Request escaped its persistent batch",
        )
        previous = ends[batch] if (position + 1) % SESSION_LENGTH == 0 else end
    rb_calibration.setup_durations(row)
    return {
        "reader_setup_ms": (opened - start) / 1e6,
        "first_batch_ms": (ends[0] - opened) / 1e6,
        "steady_ms": (ends[-1] - ends[0]) / 1e6,
        "lifetime_ms": (closed - start) / 1e6,
        "close_ms": (closed - closing) / 1e6,
    }


def paired(cells, left, right):
    blocks = []
    epochs = defaultdict(list)
    for group in range(WORKLOADS):
        gaps, logs = [], []
        for epoch in range(EPOCHS):
            a = fmean(cells[epoch, group, arm]["steady_ms"] for arm in left)
            b = fmean(cells[epoch, group, arm]["steady_ms"] for arm in right)
            gap = (a - b) / STEADY_REQUESTS
            gaps.append(gap)
            logs.append(math.log(a / b))
            epochs[epoch].append(gap)
        blocks.append((fmean(gaps), fmean(logs)))
    lo, hi = interval(blocks)
    return {
        "gap_ms": fmean(pair[0] for pair in blocks),
        "gap_ci95_ms": [lo[0], hi[0]],
        "log_ratio": fmean(pair[1] for pair in blocks),
        "log_ratio_ci95": [lo[1], hi[1]],
        "epoch_gap_ms": [fmean(epochs[epoch]) for epoch in range(EPOCHS)],
    }


def reconstruct(directory, plan, frozen, evidence, *, synthetic_only):
    rows, accounting = rb_calibration.completed_timing(directory, evidence, synthetic_only)
    cells = {}
    seen = set()
    installations = 0
    previous_close = 0
    for row, (epoch, session, arm) in zip(rows, schedule(plan, evidence), strict=True):
        require(
            (row["epoch"], row["session_id"], row["arm"]) == (epoch, session.id, arm),
            "Persistent schedule changed",
        )
        cells[epoch, session.block, arm] = measurements(row, previous_close)
        previous_close = row["boundary_ns"][-1]
        family = arm.split("-")[0]
        check_identity(row, seen)
        installations += check_requests(session, family, evidence, row)
        for record in row["requests"]:
            check_timed(evidence, evidence.outcomes, family, record)
    rb_calibration.check_accounting(accounting, Meter, installations)
    aa = {}
    for family in FAMILIES:
        cell = paired(cells, (f"{family}-B",), (f"{family}-A",))
        cell["passes"] = aa_equivalent(cell)
        aa[family] = cell
    aa_pass = all(cell["passes"] for cell in aa.values())
    quality = quality_reports(plan, frozen, evidence)
    contrasts = {}
    verdict = "measurement_inconclusive"
    if aa_pass:
        verdict = "closed_negative_quality"
        if quality["passes"]:
            for reference in ("native", "seed"):
                cell = paired(
                    cells, ("candidate-A", "candidate-B"), (f"{reference}-A", f"{reference}-B")
                )
                cell["passes"] = cell["log_ratio_ci95"][1] < 0 and all(
                    gap < 0 for gap in cell["epoch_gap_ms"]
                )
                contrasts[f"candidate_vs_{reference}"] = cell
            verdict = (
                "would_pass"
                if all(c["passes"] for c in contrasts.values())
                else ("closed_negative_latency")
            )
    means = {
        family: {
            metric: fmean(
                cell[metric] for (_, _, arm), cell in cells.items() if arm.startswith(family + "-")
            )
            for metric in next(iter(cells.values()))
        }
        for family in FAMILIES
    }
    return {
        "persistent_reader": True,
        "synthetic_only": synthetic_only,
        "development_qualifier": False,
        "provisional_verdict": verdict,
        "accounting": accounting,
        "quality": quality,
        "aa_pass": aa_pass,
        "aa_per_steady_request": aa,
        "steady_contrasts_per_request": contrasts,
        "mean_lifetime_components_ms": means,
    }
