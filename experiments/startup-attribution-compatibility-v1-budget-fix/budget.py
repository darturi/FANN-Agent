"""C2B finite compatibility time contract; no changes to the main A2 budget."""

import math
import signal
import time
from contextlib import contextmanager

LIMITS = dict(
    allocations=1,
    physical_cpus=2,
    memory_gib=4,
    wall_seconds=1260,
    host_startup_seconds=90,
    guest_preflight_seconds=30,
    source_suite_seconds=420,
    candidate_build_seconds=90,
    sealed_suite_seconds=420,
    guest_cleanup_seconds=30,
    guest_seconds=990,
    termination_seconds=15,
    host_cleanup_seconds=60,
    outer_margin_seconds=105,
    raw_bytes=4194304,
    scratch_required_bytes=4294967296,
    home_return_required_bytes=134217728,
)


def validate(limits):
    if limits != LIMITS or any(type(v) is not int or v <= 0 for v in limits.values()):
        raise ValueError("Exact frozen C2B limits required")
    guest = sum(
        limits[k]
        for k in (
            "guest_preflight_seconds",
            "source_suite_seconds",
            "candidate_build_seconds",
            "sealed_suite_seconds",
            "guest_cleanup_seconds",
        )
    )
    host = sum(
        limits[k]
        for k in (
            "host_startup_seconds",
            "guest_seconds",
            "termination_seconds",
            "host_cleanup_seconds",
            "outer_margin_seconds",
        )
    )
    if guest != limits["guest_seconds"] or host != limits["wall_seconds"]:
        raise ValueError("Critical-path budget does not close")
    return limits


def admit(now, seconds, latest, tail=0):
    """Never shorten a required phase to fit the envelope."""
    if not all(math.isfinite(x) for x in (now, seconds, latest, tail)):
        raise ValueError("Finite monotonic deadlines required")
    if seconds <= 0 or tail < 0 or now + seconds + tail > latest:
        raise TimeoutError("Insufficient full phase/cleanup reserve")
    return now + seconds


@contextmanager
def phase(name, seconds, latest, ledger, tail=0, began=None):
    start = time.monotonic() if began is None else began
    end = admit(start, seconds, latest, tail)
    record = dict(
        phase=name,
        budget_seconds=seconds,
        started_monotonic=start,
        deadline_monotonic=end,
        status="running",
    )
    ledger.append(record)
    if time.monotonic() >= end:
        raise TimeoutError("Phase deadline before entry: " + name)
    signal.alarm(max(1, math.ceil(end - time.monotonic())))
    try:
        yield end
        if time.monotonic() >= end:
            raise TimeoutError("Phase deadline: " + name)
        record["status"] = "pass"
    except BaseException as e:
        record.update(status="failed", error_type=type(e).__name__, message=str(e)[:2048])
        raise
    finally:
        signal.alarm(0)
        record["elapsed_seconds"] = time.monotonic() - start
