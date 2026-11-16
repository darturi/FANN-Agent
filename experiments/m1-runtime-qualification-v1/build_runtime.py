"""Copy the versioned v2 engine, extend only its compiled probe pool, add separate observers."""

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
V2 = HERE.parent / "filtered-ann-protocol-v2"
sys.path.insert(0, str(V2))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(destination):
    from fannproto.compiler import compile_programs
    from fannproto.policy import FILTERS

    spec = importlib.util.spec_from_file_location("v2_stager", V2 / "prepare_runtime.py")
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    prior.prepare(destination)
    programs = prior.fixtures()
    for arm, name, condition in (
        (47, "count_continue", [["qualifying_count", ">=", 0]]),
        (48, "ranked_continue", [["tenth_distance", ">=", 0.0]]),
        (49, "turnover_continue", [["top10_new_since_previous", "<=", 10]]),
        (50, "decision_continue", []),
        (
            54,
            "four_compare_continue",
            [
                ["qualifying_count", ">=", 0],
                ["tenth_distance", ">=", 0.0],
                ["frontier_gap", ">=", -2.0],
                ["top10_new_since_previous", "<=", 10],
            ],
        ),
    ):
        programs.append(
            {
                "arm": arm,
                "force_continue": True,
                "policy": {
                    "schema": "fannagent.filtered-ann.v2",
                    "name": "M1_" + name,
                    "rules": {
                        f: [{"cp": cp, "conditions": condition} for cp in (16, 32, 64)]
                        for f in FILTERS
                    },
                    "rationale": "Researcher cost/semantic probe only; not an agent candidate.",
                },
            }
        )
    for cp, arm in ((16, 51), (32, 52), (64, 53)):
        programs.append(
            {
                "arm": arm,
                "force_continue": False,
                "policy": {
                    "schema": "fannagent.filtered-ann.v2",
                    "name": "M1_bare_stop" + str(cp),
                    "rules": {f: [{"cp": cp, "conditions": []}] for f in FILTERS},
                    "rationale": (
                        "Researcher no-observation prefix cost/label probe; actual0..10 output."
                    ),
                },
            }
        )
    source, compiled = compile_programs(programs)
    assert len(programs) == 21
    (destination / "engine/src/compiled_v2.inc").write_text(source)
    (destination / "compiled-programs.json").write_text(
        json.dumps(compiled, sort_keys=True, indent=2) + "\n"
    )
    shutil.copytree(destination / "engine", destination / "observer-engine")
    engine = destination / "observer-engine"
    p = engine / "src/fannbench.c"
    s = p.read_text()
    anchor = '#include "utils/snapmgr.h"'
    assert s.count(anchor) == 1
    s = s.replace(
        anchor,
        anchor
        + '\n#include <sched.h>\n#include <sys/syscall.h>\n#include "diagnostic_counters.inc"',
    )
    observer = STUDY / "runtime-attribution-v1"
    shutil.copyfile(observer / "sessions.py", destination / "sessions.py")
    old_delta = json.loads((observer / "work-source-change.json").read_text())
    for signature, statement in old_delta["hooks"].items():
        needle = signature + "\n{"
        assert s.count(needle) == 1
        s = s.replace(needle, needle + "\n    if (diagnosticEnabled) { " + statement + " }")
    p.write_text(s)
    shutil.copyfile(
        observer / "engine/src/diagnostic_counters.inc", engine / "src/diagnostic_counters.inc"
    )
    marker = "CREATE FUNCTION fannagent.diagnostic_reset"
    diagnostics = marker + (observer / "work-functions.sql").read_text().split(marker, 1)[1]
    (destination / "work-functions.sql").write_text(
        (destination / "functions.sql").read_text() + "\n" + diagnostics
    )
    changed = []
    for q in (destination / "engine").rglob("*"):
        if q.is_file() and q.suffix in (".c", ".h", ".inc"):
            if q.read_bytes() != (engine / q.relative_to(destination / "engine")).read_bytes():
                changed.append(str(q.relative_to(destination / "engine")))
    assert changed == ["src/fannbench.c"], changed
    (destination / "observer-delta.json").write_text(
        json.dumps(
            {
                "source": "existing M0 hooks only; no graph/policy changes",
                "changed_source": changed,
                "before": sha(destination / "engine/src/fannbench.c"),
                "after": sha(engine / "src/fannbench.c"),
                "added_include_sha256": sha(engine / "src/diagnostic_counters.inc"),
                "counter_definitions": old_delta["counter_definitions"],
                "instrumented_times_enter_primary": False,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )
    for name in (
        "m1_design.py",
        "m1_experiment.py",
        "m1_run.py",
        "m1_verify.py",
        "m1_analyse.py",
        "m1_smoke.py",
        "m1_preflight.py",
        "startup-preflight.sh",
        "submit.sh",
        "run-on-compute.sh",
    ):
        if (HERE / name).exists():
            shutil.copyfile(HERE / name, destination / name)
    return compiled


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--destination", type=Path, required=True)
    a = p.parse_args()
    r = prepare(a.destination)
    print(json.dumps({"bindings": len(r["bindings"]), "profile": r["profile"]["fingerprint"]}))
