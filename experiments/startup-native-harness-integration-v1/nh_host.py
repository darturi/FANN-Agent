"""Offline-verifiable host/ready/guest/post integration with closed native dispatch."""

import os
import signal
import time

from nh_binding import Campaign, specification
from nh_common import (
    check_time,
    closed_native,
    config,
    offline,
    private,
    read,
)
from nh_retention import RawStore, capture
from nh_storage import launch_admission, ready_admission


def execute(root, prepare, guest, verify_final, clock=time.monotonic, initial_context=None):
    offline()
    started = clock()
    root = private(root)
    if not root.name.startswith("local-"):
        raise ValueError("Only local campaign namespace is permitted")
    c = config()
    fs = os.statvfs(root)
    if (
        fs.f_bavail * fs.f_frsize < c["limits"]["home_return_required_bytes"]
        or fs.f_favail < c["limits"]["home_free_files"]
    ):
        raise RuntimeError("Original persistent return headroom unavailable")
    store = RawStore(root)
    campaign = None
    context = initial_context
    ready = None
    status = None
    error = None
    launch = None
    retention = None
    old_handler = signal.getsignal(signal.SIGALRM)

    def timeout(number, frame):
        raise TimeoutError("Integration host deadline")

    signal.signal(signal.SIGALRM, timeout)
    try:
        signal.setitimer(signal.ITIMER_REAL, max(0.001, started + 210 - clock()))
        context = prepare(started, store)
        context["host_started"] = started
        binding = specification(
            context["original"], context["inner"], root, context["workspace"], c["image_sha256"]
        )
        binding["storage_evidence"] = context.get("storage_evidence")
        binding["persistent_references"] = context.get("persistent_references", {})
        binding["runtime"] = context.get("runtime")
        campaign = Campaign(root, binding)
        key = campaign.key
        context["binding_sha256"] = key
        launch = launch_admission(started, clock())
        signal.setitimer(signal.ITIMER_REAL, max(0.001, started + 240 - clock()))

        def on_ready(actual, began):
            nonlocal ready
            if ready is not None or actual != key or began > clock():
                raise RuntimeError("Stale/repeated/wrong readiness")
            ready = ready_admission(started, began)
            campaign.append("running")
            store.json(
                "readiness.json", {"binding_sha256": key, "guest_started": began, "budget": ready}
            )
            signal.setitimer(signal.ITIMER_REAL, 0)
            return ready

        def begin(bound, key):
            return guest(context, on_ready, store)

        status = campaign.launch_once(begin)
        if ready is None or status["status"] != "complete":
            raise RuntimeError("Guest incomplete or missing readiness")
    except BaseException as exc:
        import traceback

        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        post_started = clock()
        post_end = min(post_started + 240, started + 3480)
        try:
            check_time(post_end, clock)
            signal.setitimer(signal.ITIMER_REAL, max(0.001, post_end - clock()))
            try:
                verify_final(context, post_end)
            except BaseException as exc:
                error = error or {"type": type(exc).__name__, "message": str(exc)}
            if context is not None and error is not None:
                retention = capture(
                    context.get("capture_root", context["work"]),
                    context["original"],
                    store,
                    post_end,
                    clock,
                    extras=context.get("persistent_references"),
                )
                if not retention["complete"]:
                    raise RuntimeError("Failed work retention incomplete")
            if campaign:
                last = read(sorted(root.glob("event-*.json"))[-1])["state"]
                if last == "running":
                    campaign.append("terminal")
                    campaign.append("retained")
            store.budget()
            check_time(post_end, clock)
        except BaseException as exc:
            error = error or {"type": type(exc).__name__, "message": str(exc)}
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
        result = {
            "status": "pass" if error is None else "failed",
            "error": error,
            "guest": status,
            "started": started,
            "finished": clock(),
            "post_started": post_started,
            "post_deadline": post_end,
            "launch_admission": launch,
            "ready_admission": ready,
            "retention_complete": None if retention is None else retention["complete"],
            "native_release": False,
            "Torch_jobs": 0,
            "ANN_searches": 0,
            "exact_searches": 0,
            "provider_calls": 0,
            "real_SQL": 0,
        }
        check_time(post_end, clock)
        store.control(result)
        store.seal(error is None)
        check_time(post_end, clock)
    return result


if __name__ == "__main__":
    closed_native()
