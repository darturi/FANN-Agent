"""Compile exact M4 nominees into copies of the qualified M1 engines."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
RUNTIME = STUDY / "runtime-m5-v1"
PRIOR = STUDY / "runtime-m1-v1"
NOMINEES = STUDY / "m4-dollar-budget-v1/assessment-v1/nominees.json"
sys.path.insert(0, str(HERE.parent / "filtered-ann-protocol-v2"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    from fannproto.compiler import compile_programs

    assert not RUNTIME.exists(), "preserve existing runtime/checks"
    assert sha(NOMINEES) == "48bf2eca1a66950a68701cd89cd646daa499f9243223a6b9301ea7f2d9befef1"
    nominees = json.loads(NOMINEES.read_text())
    assert nominees["selection_decision"]["status"] == "selected_for_M5"
    assert [n["candidate_id"] for n in nominees["nominees"]] == ["candidate-7", "candidate-8"]
    programs = []
    for n, arm, matched in zip(nominees["nominees"], (20, 21), (30, 31)):
        programs.extend(
            [
                {"arm": arm, "policy": n["policy"], "force_continue": False},
                {"arm": matched, "policy": n["policy"], "force_continue": True},
            ]
        )
    programs.append(
        {
            "arm": 43,
            "force_continue": False,
            "policy": {
                "schema": "fannagent.filtered-ann.v2",
                "name": "M5_empty",
                "rules": {},
                "rationale": "Researcher empty-policy bypass control; not an agent nominee.",
            },
        }
    )
    source, compiled = compile_programs(programs)
    RUNTIME.mkdir()
    (RUNTIME / "checks").mkdir()
    shutil.copyfile(NOMINEES, RUNTIME / "nominees.json")
    changed = {}
    for engine in ("engine", "observer-engine"):
        shutil.copytree(
            PRIOR / engine,
            RUNTIME / engine,
            ignore=shutil.ignore_patterns("*.o", "*.bc", "*.so", "__pycache__"),
        )
        (RUNTIME / engine / "src/compiled_v2.inc").write_text(source)
        changed[engine] = [
            str(p.relative_to(RUNTIME / engine))
            for p in sorted((RUNTIME / engine).rglob("*"))
            if p.is_file()
            and p.read_bytes() != (PRIOR / engine / p.relative_to(RUNTIME / engine)).read_bytes()
        ]
        assert changed[engine] == ["src/compiled_v2.inc"], changed
    for name in (
        "common.py",
        "serving.py",
        "support.py",
        "startup.py",
        "sessions.py",
        "functions.sql",
        "work-functions.sql",
        "fixture.sql",
        "observer-delta.json",
    ):
        shutil.copyfile(PRIOR / name, RUNTIME / name)
    (RUNTIME / "compiled-programs.json").write_text(
        json.dumps(compiled, sort_keys=True, indent=2) + "\n"
    )
    (RUNTIME / "nominee-source-delta.json").write_text(
        json.dumps(
            {
                "source": "qualified M1 runtime; only compiled nominee pool replaced",
                "changed": changed,
                "nominees_sha256": sha(NOMINEES),
                "compiled_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "runtime_profile": compiled["profile"]["fingerprint"],
                "graph_algorithm_changed": False,
                "inherited_observer_delta_sha256": sha(PRIOR / "observer-delta.json"),
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )
    for p in HERE.iterdir():
        if p.name.startswith("m5_") and p.suffix == ".py":
            shutil.copyfile(p, RUNTIME / p.name)
    print(
        json.dumps(
            {"runtime": str(RUNTIME), "bindings": len(compiled["bindings"]), "changed": changed}
        )
    )


if __name__ == "__main__":
    prepare()
