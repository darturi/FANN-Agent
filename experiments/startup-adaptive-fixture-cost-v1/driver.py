"""Local-only unchanged suites with the prospectively frozen path helper."""

import argparse
import collections
import contextlib
import cProfile
import hashlib
import json
import pstats
import resource
import sys
import time
from pathlib import Path
from unittest.mock import patch

import fast_paths

ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
OUTPUT = ROOT / "trials/torch-reviews-startup-adaptive-fixture-cost-v1"
OLD = ROOT / "agent/experiments/startup-adaptive-x86-qualification-v1"
sys.dont_write_bytecode = True


def inventory(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--kind", choices=("a3", "main", "build"), required=True)
    parser.add_argument("--profile", choices=("local",), default="local")
    parser.add_argument("--phase", choices=("source", "sealed"), required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--measure", action="store_true")
    args = parser.parse_args()
    if not args.out.resolve().is_relative_to(OUTPUT) or not args.workspace.resolve().is_relative_to(
        OUTPUT
    ):
        raise RuntimeError("Owned offline review paths required")
    frozen = json.loads((OUTPUT / "REVIEW-FREEZE.json").read_text())
    if args.kind == "a3" and inventory(args.source) != frozen["source_inventory"]:
        raise RuntimeError("Every original A3 file must be unchanged")
    sys.path.insert(0, str(OLD))
    import child

    original_configure = child.configure
    counters = fast_paths.stats()
    counts = collections.Counter()
    copies = collections.Counter()
    sizes = collections.Counter()

    def observe(event, values):
        if event in (
            "open",
            "os.scandir",
            "os.listdir",
            "os.link",
            "os.remove",
            "os.mkdir",
            "shutil.copyfile",
            "shutil.copytree",
            "socket.connect",
            "socket.bind",
            "subprocess.Popen",
        ):
            counts[event] += 1
        if event == "shutil.copyfile":
            src = Path(values[0])
            key = src.name if src.stat().st_size > 1024**2 else "small_files"
            copies[key] += 1
            sizes[key] += src.stat().st_size

    if args.measure:
        sys.addaudithook(observe)
    profile = cProfile.Profile() if args.measure else None
    started, cpu = time.perf_counter(), time.process_time()
    code, error = 1, None
    with contextlib.ExitStack() as stack:

        def configure(workspace, source, kind):
            experiment = original_configure(workspace, source, kind)
            if kind == "a3":
                import pc_common

                stack.enter_context(fast_paths.scoped(pc_common, workspace, source, counters))
            return experiment

        stack.enter_context(patch.object(child, "configure", configure))
        argv = [
            str(OLD / "child.py"),
            "--workspace",
            str(args.workspace),
            "--source",
            str(args.source),
            "--kind",
            args.kind,
            "--profile",
            "local",
            "--phase",
            args.phase,
            "--out",
            str(args.out),
        ]
        if args.candidate:
            argv += ["--candidate", str(args.candidate)]
        stack.enter_context(patch.object(sys, "argv", argv))
        try:
            if profile:
                profile.enable()
            child.main()
            code = 0
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            if profile:
                profile.disable()
    if args.kind == "a3" and (
        inventory(args.source) != frozen["source_inventory"] or not counters["restored"]
    ):
        raise RuntimeError("Original source or path binding restoration failed")
    rows = []
    if profile:
        profile.dump_stats(str(args.out / "profile.pstats"))
        for (filename, line, name), (primitive, calls, self_s, cumulative_s, _) in pstats.Stats(
            profile
        ).stats.items():
            rows.append(
                {
                    "file": filename,
                    "line": line,
                    "function": name,
                    "primitive_calls": primitive,
                    "calls": calls,
                    "self_seconds": self_s,
                    "cumulative_seconds": cumulative_s,
                }
            )
    value = {
        "status": "pass" if code == 0 else "failed",
        "error": error,
        "diagnostic_only": True,
        "native_qualification": False,
        "profile": "local",
        "phase": args.phase,
        "kind": args.kind,
        "wall_seconds": time.perf_counter() - started,
        "process_cpu_seconds": time.process_time() - cpu,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        * (1 if sys.platform == "darwin" else 1024),
        "path_helper": counters,
        "audit_counts": dict(counts),
        "copy_calls": dict(copies),
        "copy_requested_bytes": dict(sizes),
        "functions": sorted(rows, key=lambda x: x["cumulative_seconds"], reverse=True),
        "ANN_searches": 0,
        "exact_searches": 0,
        "real_SQL": 0,
        "Torch_jobs": 0,
    }
    with (args.out / "fixture-cost.json").open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")
    print("complete_local_fixture_cost_checks")


if __name__ == "__main__":
    main()
