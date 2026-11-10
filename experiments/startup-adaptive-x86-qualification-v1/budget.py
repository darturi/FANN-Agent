"""Original 1h/4CPU/32GiB envelope and full 600-second cleanup reserve."""

import math
import signal
import time
from contextlib import contextmanager

PHASES = {
    "preflight": 30,
    "main_source": 420,
    "candidate_build": 90,
    "main_sealed": 420,
    "a3_source": 600,
    "a3_sealed": 600,
    "cpu": 180,
    "guest_cleanup": 600,
}


def validate(limits, phases):
    if phases != PHASES or any(type(v) is not int or v <= 0 for v in phases.values()):
        raise ValueError("Exact complete phase caps required")
    for k, v in {
        "allocations": 1,
        "wall_seconds": 3600,
        "physical_cpus": 4,
        "memory_gib": 32,
        "host_pre_seconds": 240,
        "guest_seconds": 3000,
        "host_post_seconds": 240,
        "outer_margin_seconds": 120,
        "guest_cleanup_seconds": 600,
    }.items():
        if type(limits[k]) is not int or limits[k] != v:
            raise ValueError("Original resource limit changed: " + k)
    if (
        sum(phases.values()) != 2940
        or limits["host_pre_seconds"]
        + limits["guest_seconds"]
        + limits["host_post_seconds"]
        + limits["outer_margin_seconds"]
        != 3600
    ):
        raise ValueError("Complete budget does not close")
    return limits


def admit(now, seconds, latest, tail=0):
    if (
        not all(type(v) in (float, int) and math.isfinite(v) for v in (now, seconds, latest, tail))
        or seconds <= 0
        or tail < 0
        or now + seconds + tail > latest
    ):
        raise TimeoutError("Insufficient full phase and cleanup reserve")
    return now + seconds


@contextmanager
def phase(name, seconds, deadline, ledger, tail=0):
    start = time.monotonic()
    end = admit(start, seconds, deadline, tail)
    row = dict(phase=name, started=start, deadline=end, status="running")
    ledger.append(row)
    signal.alarm(max(1, math.ceil(end - time.monotonic())))
    try:
        yield end
        if time.monotonic() >= end:
            raise TimeoutError("Qualification phase deadline: " + name)
        row["status"] = "pass"
    except BaseException as e:
        row.update(status="failed", error=type(e).__name__)
        raise
    finally:
        signal.alarm(0)
        row["elapsed_seconds"] = time.monotonic() - start
