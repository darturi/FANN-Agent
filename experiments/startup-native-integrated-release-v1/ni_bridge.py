"""Fresh original child with only the pinned equivalent path/lifetime scopes."""

import argparse
import contextlib
import cProfile
import pstats
import sys
from pathlib import Path
from unittest.mock import patch

from nh_common import compat, core, inventory, offline, read, save


def main():
    offline()
    p = argparse.ArgumentParser()
    for name in ("inner", "workspace", "source", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--kind", choices=("main", "a3", "build", "cpu"), required=True)
    p.add_argument("--phase", choices=("source", "sealed"), required=True)
    p.add_argument("--profile", choices=("local", "target"), required=True)
    p.add_argument("--candidate", type=Path)
    a = p.parse_args()
    if a.profile != "local":
        from ni_authority import delegated_ticket

        delegated_ticket()
    compat()
    import fast_paths
    from lifetime import observe

    core(a.inner)
    import child

    if Path(child.__file__).resolve() != a.inner.resolve() / "child.py":
        raise RuntimeError("Wrong original child")
    original = child.configure
    counters = fast_paths.stats()
    life = {}
    profile = cProfile.Profile() if a.kind == "a3" else None
    source_inventory = read(a.inner / "QUALIFICATION-CONTRACT.json")["source_inventory"]
    if a.kind == "a3" and inventory(a.source) != source_inventory:
        raise RuntimeError("Original source differs")
    with contextlib.ExitStack() as stack:

        def configure(w, s, kind):
            e = original(w, s, kind)
            if a.kind == "a3":
                import pc_common

                stack.enter_context(fast_paths.scoped(pc_common, w, s, counters))
                import test_fixtures

                stack.enter_context(observe(test_fixtures, life))
            return e

        argv = [
            str(a.inner / "child.py"),
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
            a.profile,
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
    if a.kind == "a3":
        if (
            inventory(a.source) != source_inventory
            or not counters["restored"]
            or not life["restored"]
            or life["calls"] != 50
            or life["peak_live_roots"] != 1
        ):
            raise RuntimeError("Original fixture/path lifetime or bindings differ")
        profile.dump_stats(str(a.out / "profile.pstats"))
        rows = [
            {
                "file": f,
                "line": line,
                "function": name,
                "calls": values[1],
                "self_seconds": values[2],
                "cumulative_seconds": values[3],
            }
            for (f, line, name), values in pstats.Stats(profile).stats.items()
        ]
        if (
            sum(
                r["calls"]
                for r in rows
                if r["function"] == "sha" and r["file"].endswith("/legacy_common.py")
            )
            != 292688
        ):
            raise RuntimeError("Original full hash observations differ")
        save(
            a.out / "integration-child.json",
            {
                "status": "pass",
                "path_helper": counters,
                "fixture_lifetime": life,
                "functions": rows,
                "native_release": False,
            },
        )


if __name__ == "__main__":
    main()
