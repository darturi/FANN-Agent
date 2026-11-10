"""Idempotent cleanup cancellation within the existing absolute work deadline."""

import signal
import time


class CleanupSignals:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.count = 0
        self.records = []
        self.cleanup_started = False

    def begin(self):
        self.cleanup_started = True

    def handle(self, number, stage, deadline):
        now = self.clock()
        if self.cleanup_started:
            stage = "final_cleanup"
        self.count += 1
        if len(self.records) < 8:
            self.records.append(dict(signal=number, stage=stage, time=now, deadline=deadline))
        if number == signal.SIGALRM:
            raise TimeoutError("Native absolute stage/global deadline: " + str(stage))
        # Ordinary cancellation must never raise through an arbitrary finally
        # entry, close, shutdown or receipt write. Existing budget safepoints
        # notice the request; the separately armed deadline remains immediate.

    def check(self, stage):
        if stage != "final_cleanup":
            if self.count:
                raise InterruptedError("Native cancellation requested")

    def proof(self):
        return dict(count=self.count, records=list(self.records), failed=bool(self.count))


def arm_remaining(budget, arm=signal.setitimer):
    """Never restart a phase or perform heavy cleanup after its absolute expiry."""
    budget.check()
    remaining = budget.remaining()
    if remaining <= 0:
        raise TimeoutError("Native cleanup deadline exhausted")
    arm(signal.ITIMER_REAL, remaining)
    return remaining
