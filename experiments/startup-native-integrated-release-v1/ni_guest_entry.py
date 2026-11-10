"""Container entry and exact serial command recipe; authority comes from owned host."""

import argparse
import os
import sys
import time
from pathlib import Path

from nh_common import A3, HERE, MAIN, ROOT
from nh_lifecycle import endpoint, interruptions
from nh_retention import RawStore
from nh_storage import ready_admission
from ni_authority import delegated_ticket, guest_owner
from ni_guest import run
from ni_runner import IntegratedNative


def commands(context, python):
    def args(kind, source, label, candidate=None):
        bridge = Path(context.get("bridge_snapshot", HERE)) if label.endswith("sealed") else HERE
        value = [
            str(python),
            "-B",
            str(bridge / "ni_bridge.py"),
            "--inner",
            str(context["inner"]),
            "--workspace",
            str(context["workspace"]),
            "--source",
            str(source),
            "--out",
            str(Path(context["science"]) / label),
            "--kind",
            kind,
            "--phase",
            "sealed" if label.endswith("sealed") else "source",
            "--profile",
            context.get("profile", "local"),
        ]
        if candidate:
            value += ["--candidate", str(candidate)]
        return value

    w, work = Path(context["workspace"]), Path(context["work"])
    return [
        [
            str(python),
            "-B",
            str(HERE / "ni_runtime.py"),
            "--inner",
            str(context["inner"]),
            "--workspace",
            str(w),
            "--out",
            str(Path(context["science"]) / "runtime.json"),
            "--profile",
            context.get("profile", "local"),
        ],
        args("main", w / MAIN, "main-source"),
        args("build", w / MAIN, "candidate-build", work / "candidate-main"),
        args(
            "main",
            work / "candidate-main/torch-startup-attribution-v1-image-reference",
            "main-sealed",
        ),
        args("a3", w / A3, "a3-source"),
        args("a3", work / "candidate-a3", "a3-sealed"),
        args("cpu", w / A3, "cpu"),
    ]


def recipe(context):
    return commands(context, "$PYTHON")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ticket", required=True)
    p.add_argument("--expected", required=True)
    a = p.parse_args()
    ticket = delegated_ticket(a.ticket, a.expected, native=True)
    os.environ["NI_TICKET"] = a.ticket
    os.environ["NI_TICKET_SHA"] = a.expected
    context = {
        "original": "/qual",
        "inner": "/qual",
        "workspace": str(ROOT),
        "work": "/work",
        "science": "/results/science",
        "profile": "target",
        "binding_sha256": ticket["binding_sha256"],
        "bridge_snapshot": "/integration-sealed",
    }
    if ticket["commands"] != recipe(context):
        raise RuntimeError("Frozen scientific command recipe differs")
    budget = ready_admission(ticket["host_started"], time.monotonic())
    ticket = dict(ticket)
    ticket["commands"] = commands(context, sys.executable)
    owner = guest_owner(ticket, context["binding_sha256"], budget["guest_end"], budget["guest_end"])
    store = RawStore.existing(Path("/results"))
    runner = IntegratedNative(context, store, owner)
    sys.addaudithook(runner.audit)

    def ready(key, began):
        actual = ready_admission(ticket["host_started"], began)
        store.json(
            "native-ready.json",
            {
                "binding_sha256": key,
                "guest_started": began,
                "pid": os.getpid(),
                "start": owner.origin["supervisor_start"],
                "nonce": ticket["nonce"],
                "budget": actual,
            },
        )
        return actual

    try:
        result = run(context, runner, ready, store)
        with interruptions(), endpoint(result["cleanup_deadline"]):
            store.json(
                "native-runner.json",
                {
                    "records": runner.records,
                    "shared_budget": owner.kernel.budget.usage(),
                    "children_finalized": runner.child is None,
                },
            )
        raise SystemExit(0 if result["status"] == "complete" else 1)
    finally:
        owner.kernel.close()


if __name__ == "__main__":
    main()
