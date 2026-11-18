"""Create a separate engine with v3 dispatch; preserve every existing oracle arm."""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
sys.path[:0] = [str(ROOT / "agent/src"), str(HERE.parent / "filtered-ann-protocol-v3")]
from fannproto3.compiler import compile_programs  # noqa: E402


def replace(text, before, after):
    if text.count(before) != 1:
        raise ValueError("engine patch does not match exactly: " + before)
    return text.replace(before, after)


def sha(p):
    with p.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def build(bindings, destination):
    destination.mkdir()
    original = STUDY / "oracle-variants-v1/runtime-v2/engine"
    engine = destination / "engine"
    shutil.copytree(original, engine, ignore=shutil.ignore_patterns("*.o", "*.so", "*.bc"))
    code, manifest = compile_programs(bindings)
    (engine / "src/compiled_v3.inc").write_text(code)
    shutil.copyfile(HERE / "runtime/broad_runtime.inc", engine / "src/broad_runtime.inc")
    p = engine / "src/hnswutils.c"
    text = p.read_text()
    text = replace(
        text,
        '#include "policy_runtime_v2.inc"',
        '#include "policy_runtime_v2.inc"\n#include "broad_runtime.inc"',
    )
    text = replace(
        text,
        "FannbenchOracleCheckpoint() : 64;",
        "FannbenchOracleCheckpoint() : confirmArm >= 60 ? FannbenchV3Last() : 64;",
    )
    text = replace(
        text,
        "if ((confirmArm == 10 && confirmCheckpoint == confirmLast) ||\n"
        "                    (confirmArm != 10 && confirmArm != 11 &&",
        "if ((confirmArm == 10 && confirmCheckpoint == confirmLast) ||\n"
        "                    (confirmArm >= 60 && "
        "V3Stop(confirmCheckpoint,confirmCount,C,W,base)) ||\n"
        "                    (confirmArm < 60 && confirmArm != 10 && confirmArm != 11 &&",
    )
    text = replace(
        text,
        "\t\t\t\t\tFannbenchConfirmStopped(confirmCheckpoint);\n"
        "\t\t\t\t\tbreak;\n\t\t\t\t}\n\t\t\t}",
        "\t\t\t\t\tFannbenchConfirmStopped(confirmCheckpoint);\n"
        "\t\t\t\t\tbreak;\n\t\t\t\t}\n"
        "                if(confirmArm>=60 && (v3Exhausted||v3Fault)) "
        "confirmLast=confirmCheckpoint;\n\t\t\t}",
    )
    p.write_text(text)
    p = engine / "src/fannbench.c"
    text = replace(
        p.read_text(),
        "(arm > 11 && !FannbenchV2ArmDeclared(arm))",
        "(arm > 11 && !FannbenchV2ArmDeclared(arm) && !FannbenchV3ArmDeclared(arm))",
    )
    text = replace(
        text,
        "    if (confirmationArm >= 20) {",
        "    if (confirmationArm >= 60) {\n"
        "        FannbenchV3Begin(confirmationArm,studyThreshold);\n"
        "        if(!FannbenchV3Enabled()) return 0;\n"
        "    } else if (confirmationArm >= 20) {",
    )
    p.write_text(text)
    p = engine / "src/fannbench.h"
    p.write_text(
        p.read_text() + "\nextern bool FannbenchV3ArmDeclared(int arm);\n"
        "extern void FannbenchV3Begin(int arm,int filter);\n"
        "extern bool FannbenchV3Enabled(void);\nextern int FannbenchV3Last(void);\n"
    )
    changes = {}
    for p in engine.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(engine)
        if not (original / rel).exists() or p.read_bytes() != (original / rel).read_bytes():
            changes[str(rel)] = sha(p)
    assert set(changes) == {
        "src/hnswutils.c",
        "src/fannbench.c",
        "src/fannbench.h",
        "src/compiled_v3.inc",
        "src/broad_runtime.inc",
    }
    (destination / "compiled-v3.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (destination / "source-changes.json").write_text(json.dumps(changes, indent=2) + "\n")
    functions = (STUDY / "oracle-variants-v1/benchmark-kit-v1/functions.sql").read_text()
    functions += "\nCREATE FUNCTION fannagent.v3_audit_enable(boolean) RETURNS void "
    functions += "AS '$libdir/vector','fannbench_v3_audit_enable' LANGUAGE C VOLATILE;\n"
    functions += "CREATE FUNCTION fannagent.v3_audit_read() RETURNS text "
    functions += "AS '$libdir/vector','fannbench_v3_audit_read' LANGUAGE C VOLATILE;\n"
    (destination / "functions.sql").write_text(functions)
    shutil.copyfile(
        ROOT / "agent/src/fannagent/api/broad_policy.py", destination / "broad_contract.py"
    )
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build(json.loads(args.bindings.read_text()), args.output))
