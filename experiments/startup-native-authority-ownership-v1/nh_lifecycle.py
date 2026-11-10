"""Deadline and interruption scopes; native group control has no supplied backend."""

import signal
import time
from contextlib import contextmanager

from nh_common import check_time

INTERRUPTS = (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGALRM)


@contextmanager
def interruptions():
    previous = {s: signal.getsignal(s) for s in INTERRUPTS}

    def interrupted(number, frame):
        raise TimeoutError("Integration signal/deadline " + str(number))

    try:
        for s in INTERRUPTS:
            signal.signal(s, interrupted)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for s, handler in previous.items():
            signal.signal(s, handler)


@contextmanager
def endpoint(end, clock=time.monotonic):
    check_time(end, clock)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, end - clock()))
    try:
        yield
        check_time(end, clock)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


class OwnedGroups:
    """Future authority interface, deliberately without a native implementation.

    A qualified backend must atomically spawn/register and validate allocation,
    binding, identity and complete group membership before each signal. A PID or
    site_verified string is insufficient. Tests supply only in-memory models.
    """

    def validate(self, context):
        raise RuntimeError("Authoritative owned-group backend unavailable")

    def spawn(self, argv, **kwargs):
        raise RuntimeError("Authoritative owned-group backend unavailable")

    def members(self, handle):
        raise RuntimeError("Authoritative owned-group backend unavailable")

    def send(self, handle, number):
        raise RuntimeError("Authoritative owned-group backend unavailable")


def require_groups(context):
    controller = context.get("process_control")
    if not isinstance(controller, OwnedGroups) or controller.validate(context) is not True:
        raise RuntimeError("Qualified owned-group controller required before spawn")
    return controller


def stop_owned(controller, handle, proc, end, clock=time.monotonic, pause=time.sleep):
    """Bounded whole-group shutdown, including an already-exited leader."""

    def members():
        value = controller.members(handle)
        if (
            not isinstance(value, tuple)
            or len(value) > 32
            or any(type(n) is not int or n <= 0 for n in value)
            or len(set(value)) != len(value)
        ):
            raise RuntimeError("Unknown/invalid owned-group membership")
        return value

    live = members()
    for number, cap in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        if not live:
            break
        check_time(end, clock)
        controller.send(handle, number)
        until = min(clock() + cap, end)
        while live and clock() < until:
            pause(min(0.05, until - clock()))
            live = members()
    if live:
        raise RuntimeError("Owned process group remains live")
    check_time(end, clock)
    proc.wait(timeout=min(5, end - clock()))
    check_time(end, clock)
    if proc.poll() is None or members():
        raise RuntimeError("Owned group/direct child not fully stopped")
    return {"whole_group_absent": True, "direct_child_reaped": True}
