"""Stage a copied v2 engine; never modify qualified/installed historical modules."""

import argparse
import ast
import hashlib
import json
import shutil
from pathlib import Path

from fannproto.compiler import compile_programs
from fannproto.policy import FILTERS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"


def fixtures():
    old = json.loads((STUDY / "runtime-agent-v1/eligible-policies.json").read_text())["policies"]
    programs = []
    for i, p in enumerate(old):
        v = {"schema": "fannagent.filtered-ann.v2", **p}
        programs.extend(
            [
                {"arm": 20 + i, "policy": v, "force_continue": False},
                {"arm": 30 + i, "policy": v, "force_continue": True},
            ]
        )
    for cp, arm in ((16, 40), (32, 41), (64, 42)):
        programs.append(
            {
                "arm": arm,
                "policy": {
                    "schema": "fannagent.filtered-ann.v2",
                    "name": "qualification_partial" + str(cp),
                    "rules": {
                        f: [{"cp": cp, "conditions": [["qualifying_count", ">=", 0]]}]
                        for f in FILTERS
                    },
                    "rationale": "researcher qualification probe only; not an agent proposal",
                },
                "force_continue": False,
            }
        )
    for arm, name, rules in (
        (43, "empty", {}),
        (
            44,
            "turnover_dependency",
            {"votes32": [{"cp": 64, "conditions": [["top10_new_since_previous", "<=", 10]]}]},
        ),
        (
            45,
            "partial_condition",
            {"votes743": [{"cp": 16, "conditions": [["qualifying_count", "<=", 9]]}]},
        ),
        (
            46,
            "distance_only",
            {"votes32": [{"cp": 64, "conditions": [["tenth_distance", "<=", 2.0]]}]},
        ),
    ):
        programs.append(
            {
                "arm": arm,
                "policy": {
                    "schema": "fannagent.filtered-ann.v2",
                    "name": "qualification_" + name,
                    "rules": rules,
                    "rationale": "researcher qualification probe only; not an agent proposal",
                },
                "force_continue": False,
            }
        )
    return programs


def prepare(destination):
    if destination.exists():
        raise FileExistsError("use a fresh staging directory")
    old = STUDY / "runtime-agent-v1/engine"
    shutil.copytree(
        old,
        destination / "engine",
        ignore=lambda p, n: [x for x in n if x.endswith((".o", ".so", ".bc"))],
    )
    source, manifest = compile_programs(fixtures())
    (destination / "engine/src/compiled_v2.inc").write_text(source)
    shutil.copyfile(
        HERE / "runtime/policy_runtime_v2.inc", destination / "engine/src/policy_runtime_v2.inc"
    )
    p = destination / "engine/src/hnswutils.c"
    s = p.read_text()
    anchor = '#include "compiled_study_policies.inc"'
    assert s.count(anchor) == 1
    s = s.replace(
        anchor,
        anchor + '\n#include "fmgr.h"\n#include "lib/stringinfo.h"\n#include "uti'
        'ls/builtins.h"\n#include "compiled_v2.inc"\n#include "policy_r'
        'untime_v2.inc"',
    )
    # Use function-local exact anchor rather than matching an unrelated frontier variable.
    start = s.index("ConfirmStop(int arm,")
    position = s.index("\n\tif (pairingheap_is_empty(pending))", start)
    s = (
        s[:position]
        + "\n    if (arm >= 20) return V2Stop(arm, checkpoint, pending, retained, base);\n"
        + s[position:]
    )
    p.write_text(s)
    p = destination / "engine/src/fannbench.h"
    p.write_text(
        p.read_text() + "\nextern bool FannbenchV2ArmDeclared(int arm);\nextern bool Fa"
        "nnbenchV2EnabledForPredicate(int arm,int filter);\nextern voi"
        "d FannbenchV2Begin(int arm);\n"
    )
    p = destination / "engine/src/fannbench.c"
    s = p.read_text()
    assert s.count("arm > 9") == 1
    s = s.replace("arm > 9", "(arm > 9 && !FannbenchV2ArmDeclared(arm))")
    needle = "\tconfirmationStop = 0;\n\treturn confirmationArm;"
    assert s.count(needle) == 1
    s = s.replace(
        needle,
        "\tconfirmationStop = 0;\n    if (confirmationArm >= 20) {\n    "
        "    FannbenchV2Begin(confirmationArm);\n        if (!Fannbenc"
        "hV2EnabledForPredicate(confirmationArm,studyThreshold)) retu"
        "rn 0;\n    }\n\treturn confirmationArm;",
    )
    p.write_text(s)
    changes = {}
    for p in old.rglob("*"):
        if p.is_file() and p.suffix in (".c", ".h", ".inc"):
            target = destination / "engine" / p.relative_to(old)
            if p.read_bytes() != target.read_bytes():
                changes[str(p.relative_to(old))] = {
                    "before": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "after": hashlib.sha256(target.read_bytes()).hexdigest(),
                }
    assert set(changes) == {"src/hnswutils.c", "src/fannbench.h", "src/fannbench.c"}
    manifest.update(
        source_changes=changes,
        legacy_programs_unchanged=True,
        graph_changes=False,
        status="local prototype; original-graph qualification and M0 attribution gate pending",
    )
    (destination / "compiled-programs.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    sql = (
        (STUDY / "runtime-agent-v1/functions.sql").read_text()
        + "\nCREATE FUNCTION fannagent.v2_audit_enable(boolean) RETURNS "
        "void AS '$libdir/vector','fannbench_v2_audit_enable' LANGUAG"
        "E C VOLATILE PARALLEL UNSAFE;\nCREATE FUNCTION fannagent.v2_a"
        "udit_read() RETURNS text AS '$libdir/vector','fannbench_v2_a"
        "udit_read' LANGUAGE C VOLATILE PARALLEL UNSAFE;\n"
    )
    (destination / "functions.sql").write_text(sql)
    for name in ("common.py", "support.py", "startup.py", "serving.py"):
        shutil.copyfile(STUDY / "runtime-unguarded-v1" / name, destination / name)
    fixture_tree = ast.parse((STUDY / "runtime-agent-v1/smoke.py").read_text())
    fixture_sql = next(
        ast.literal_eval(node.value)
        for node in fixture_tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "SQL" for t in node.targets)
    )
    (destination / "fixture.sql").write_text(fixture_sql)
    shutil.copyfile(HERE / "smoke_runtime.py", destination / "smoke_runtime.py")
    manifest["runtime_source_sha256"] = {
        str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.rglob("*"))
        if p.is_file() and p.suffix in (".c", ".h", ".inc", ".py", ".sql")
    }
    (destination / "compiled-programs.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--destination", type=Path, required=True)
    a = p.parse_args()
    m = prepare(a.destination)
    print(
        json.dumps(
            {
                "destination": str(a.destination),
                "programs": len(m["bindings"]),
                "profile": m["profile"]["fingerprint"],
            },
            indent=2,
        )
    )
