"""Guarded original suites from verified local staging; no native entry."""

import argparse
import contextlib
import cProfile
import hashlib
import json
import os
import pstats
import sys
import time
from pathlib import Path
from unittest.mock import patch

from lifetime import observe

ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
OUTPUT = ROOT / "trials/torch-reviews-startup-adaptive-budget-storage-v1"
OLD = ROOT / "agent/experiments/startup-adaptive-x86-qualification-v1"
FAST = ROOT / "agent/experiments/startup-adaptive-fixture-cost-v1"
sys.dont_write_bytecode = True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--kind", choices=("a3", "main", "build"), required=True)
    p.add_argument("--phase", choices=("source", "sealed"), required=True)
    p.add_argument("--candidate", type=Path)
    a = p.parse_args()
    if (
        os.environ.get("SLURM_JOB_ID")
        or not a.workspace.resolve().is_relative_to(OUTPUT)
        or not a.out.resolve().is_relative_to(OUTPUT)
    ):
        raise RuntimeError("Offline owned staging only; no native allowance")
    expected = json.loads(
        (
            ROOT / "trials/torch-reviews-startup-adaptive-fixture-cost-v1/verification.json"
        ).read_text()
    )["code_sha256"]["fast_paths.py"]
    if hashlib.sha256((FAST / "fast_paths.py").read_bytes()).hexdigest() != expected:
        raise RuntimeError("Frozen D123 path helper changed")
    sys.path.insert(0, str(FAST))
    import fast_paths

    if Path(fast_paths.__file__).resolve() != FAST / "fast_paths.py":
        raise RuntimeError("Wrong path helper origin")
    frozen = json.loads((OUTPUT / "REVIEW-FREEZE.json").read_text())

    def source_map():
        return {
            str(p.relative_to(a.source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in a.source.rglob("*")
            if p.is_file()
        }

    if a.kind == "a3" and source_map() != frozen["source_inventory"]:
        raise RuntimeError("Original A3 source inventory differs")

    sys.path.insert(0, str(OLD))
    import child

    configure_original = child.configure
    counters, life = fast_paths.stats(), {}
    profile = cProfile.Profile() if a.kind == "a3" else None
    started = time.perf_counter()
    with contextlib.ExitStack() as stack:

        def configure(workspace, source, kind):
            e = configure_original(workspace, source, kind)
            if kind == "a3":
                import pc_common

                stack.enter_context(fast_paths.scoped(pc_common, workspace, source, counters))
                import test_fixtures

                stack.enter_context(observe(test_fixtures, life))
            return e

        argv = [
            str(OLD / "child.py"),
            "--workspace",
            str(a.workspace),
            "--source",
            str(a.source),
            "--out",
            str(a.out),
            "--kind",
            a.kind,
            "--phase",
            a.phase,
            "--profile",
            "local",
        ]
        if a.candidate:
            argv += ["--candidate", str(a.candidate)]
        stack.enter_context(patch.object(child, "configure", configure))
        stack.enter_context(patch.object(sys, "argv", argv))
        try:
            if profile:
                profile.enable()
            child.main()
        finally:
            if profile:
                profile.disable()
    if a.kind == "a3" and (
        not counters["restored"]
        or not life["restored"]
        or life["calls"] != 50
        or life["peak_live_roots"] != 1
    ):
        raise RuntimeError("Frozen fixture lifetime/restoration differs")
    if a.kind == "a3" and source_map() != frozen["source_inventory"]:
        raise RuntimeError("Original A3 source changed")
    functions = []
    if profile:
        profile.dump_stats(str(a.out / "profile.pstats"))
        for (filename, line, name), (_, calls, self_s, total_s, _) in pstats.Stats(
            profile
        ).stats.items():
            functions.append(
                {
                    "file": filename,
                    "line": line,
                    "function": name,
                    "calls": calls,
                    "self_seconds": self_s,
                    "cumulative_seconds": total_s,
                }
            )
    value = {
        "status": "pass",
        "local_only": True,
        "kind": a.kind,
        "phase": a.phase,
        "wall_seconds": time.perf_counter() - started,
        "path_helper": counters,
        "fixture_lifetime": life,
        "functions": functions,
        "native_budget_qualified": False,
        "native_storage_qualified": False,
        "native_release": False,
        "Torch_jobs": 0,
        "ANN_searches": 0,
        "exact_searches": 0,
    }
    with (a.out / "storage-replay.json").open("x") as out:
        json.dump(value, out, indent=2, sort_keys=True)
        out.write("\n")


if __name__ == "__main__":
    main()
