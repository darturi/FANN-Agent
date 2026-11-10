"""Original complete guest phases wired to an explicit serial runner and ready handshake."""

import shutil
import time
from pathlib import Path

from nh_common import A3, MAIN, PHASES, check_time, core, inventory, read
from nh_lifecycle import endpoint, interruptions


def run(context, runner, on_ready, store):
    with interruptions():
        return _run(context, runner, on_ready, store)


def _run(context, runner, on_ready, store):
    inner, w, work, raw = map(
        Path, (context["inner"], context["workspace"], context["work"], context["science"])
    )
    profile = context.get("profile", "local")
    if profile == "target":
        from ni_authority import delegated_ticket

        delegated_ticket()
    original = core(context["original"])
    c = read(inner / "QUALIFICATION-CONTRACT.json")
    from budget import phase
    from proofs import validate

    began = time.monotonic()
    ready = on_ready(context["binding_sha256"], began)
    deadline = ready["guest_end"]
    remaining = list(PHASES)
    ledger = []
    error = None
    result = None
    cleanup_end = None

    def scope(name):
        remaining.remove(name)
        return phase(name, PHASES[name], deadline, ledger, tail=sum(PHASES[n] for n in remaining))

    def suite(label, kind, source, cap, end, candidate=None):
        return runner.suite(
            label,
            kind,
            source,
            "sealed" if label.endswith("sealed") else "source",
            cap,
            end,
            candidate,
        )

    try:
        with scope("preflight") as end:
            original.verify(inner)
            if inventory(w / A3) != c["source_inventory"]:
                raise RuntimeError("Original A3 source differs")
            runner.runtime(end, profile)
        with scope("main_source") as end:
            suite("main-source", "main", w / MAIN, 420, end)
        with scope("candidate_build") as end:
            suite("candidate-build", "build", w / MAIN, 90, end, work / "candidate-main")
            candidate = Path(read(raw / "candidate-build/receipt.json")["candidate"])
            snapshot = work / "candidate-a3"
            shutil.copytree(w / A3, snapshot)
            if inventory(snapshot) != c["source_inventory"]:
                raise RuntimeError("Independent A3 snapshot differs")
        with scope("main_sealed") as end:
            suite("main-sealed", "main", candidate, 420, end)
        with scope("a3_source") as end:
            suite("a3-source", "a3", w / A3, 600, end)
        with scope("a3_sealed") as end:
            suite("a3-sealed", "a3", snapshot, 600, end)
        with scope("cpu") as end:
            suite("cpu", "cpu", w / A3, 180, end)
        result = validate(raw, w, c, profile)
    except BaseException as exc:
        import traceback

        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        try:
            with phase("guest_cleanup", 600, deadline, ledger) as cleanup_end:
                runner.stop(cleanup_end)
                original.verify(inner)
                if inventory(w / A3) != c["source_inventory"]:
                    raise RuntimeError("Protected original source changed")
        except BaseException as exc:
            error = error or {"type": type(exc).__name__, "message": str(exc)}
        status = {
            "status": "complete" if error is None else "failed",
            "error": error,
            "result": result,
            "phases": ledger,
            "started": began,
            "publication_started": time.monotonic(),
            "cleanup_deadline": cleanup_end,
            "completion_requires_successful_exit": True,
            "guest_deadline": deadline,
            "binding_sha256": context["binding_sha256"],
            "native_release": False,
            "ANN_searches": 0,
            "exact_searches": 0,
        }
        if cleanup_end is None:
            raise TimeoutError("Full original cleanup reserve unavailable")
        with endpoint(cleanup_end, time.monotonic):
            store.json("guest-status.json", status)
        status["finished"] = time.monotonic()
        check_time(cleanup_end)
    return status
