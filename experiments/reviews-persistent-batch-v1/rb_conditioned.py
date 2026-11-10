"""Held A/A calibration with same-reader conditioning before each timed chunk."""

from functools import partial

import rb_interleave as paired
from rb_interleave import VERDICTS as VERDICTS
from rb_interleave import make_backend as make_backend
from rb_persistent import REQUESTS, STEADY_REQUESTS
from rb_plan import digest


class Meter(paired.Meter):
    reader_limits = {"reference": 1, "timing": 2 * paired.MAIN_PAIRS}
    search_limits = {"timing": reader_limits["timing"] * (REQUESTS + STEADY_REQUESTS)}
    install_limits = {"timing": paired.MAIN_PAIRS}


def attach(stage):
    paired.attach(stage)
    stage.study_identity = digest(
        {
            "schema": "reviews-persistent-batch.conditioned-aa.v1",
            "interleaved": stage.study_identity,
            "conditioning": "preceding_chunk_on_same_reader",
            "pairs": paired.MAIN_PAIRS,
            "search_cap": Meter.search_limits["timing"],
        }
    )


def schedule(plan, evidence):
    return (item for item in paired.schedule(plan, evidence) if not item[0])


capture = partial(
    paired.capture, run_schedule=schedule, collector=partial(paired.collect_pair, conditioned=True)
)


def reconstruct(directory, plan, frozen, evidence, *, synthetic_only):
    report = paired.reconstruct(
        directory,
        plan,
        frozen,
        evidence,
        synthetic_only=synthetic_only,
        run_schedule=schedule,
        meter_type=Meter,
        conditioned=True,
    )
    return {**report, "conditioned_calibration": True}
