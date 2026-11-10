"""Original complete guest phases wired to an explicit serial runner and ready handshake."""

import shutil
import time
from pathlib import Path

from nh_common import A3, MAIN, PHASES, closed_native, core, inventory, read


def run(context, runner, on_ready, store):
    inner, w, work, raw = map(
        Path, (context["inner"], context["workspace"], context["work"], context["science"])
    )
    profile = context.get("profile", "local")
    if profile == "target":
        closed_native()
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
            with phase("guest_cleanup", 600, deadline, ledger):
                runner.stop()
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
            "finished": time.monotonic(),
            "guest_deadline": deadline,
            "binding_sha256": context["binding_sha256"],
            "native_release": False,
            "ANN_searches": 0,
            "exact_searches": 0,
        }
        store.json("guest-status.json", status)
    return status


def main():
    closed_native()
    import os
    import sys

    from nh_common import ROOT, digest
    from nh_retention import RawStore
    from nh_runner import NativeRunner
    from nh_storage import ready_admission

    store = RawStore.existing(Path("/results"))
    binding = read(store.root / "binding.json")
    if digest(binding["binding"]) != binding["sha256"]:
        raise RuntimeError("Immutable binding differs")
    from nh_common import HERE, sha

    actual = {
        str(p.relative_to(HERE)): sha(p)
        for p in HERE.rglob("*")
        if p.is_file() and p.suffix in (".py", ".json")
    }
    if actual != binding["binding"]["integration_files"]:
        raise RuntimeError("Bound integration code differs")
    context = {
        "original": "/qual",
        "inner": "/qual",
        "workspace": str(ROOT),
        "work": "/work",
        "science": "/results/science",
        "profile": "target",
        "binding_sha256": binding["sha256"],
    }
    runner = NativeRunner(context, store, sys.executable)
    sys.addaudithook(runner.audit)

    def ready(key, began):
        budget = ready_admission(float(os.environ["NX_HOST_STARTED"]), began)
        store.json(
            "native-ready.json",
            {"binding_sha256": key, "guest_started": began, "pid": os.getpid(), "budget": budget},
        )
        return budget

    result = run(context, runner, ready, store)
    raise SystemExit(0 if result["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
