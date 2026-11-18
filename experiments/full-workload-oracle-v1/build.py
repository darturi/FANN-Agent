"""Copy a qualified engine and add a checkpoint-only hindsight replay arm."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
BASE = STUDY / "runtime-m1-v1"


def replace_once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def prepare(destination):
    destination.mkdir()
    shutil.copytree(
        BASE / "engine",
        destination / "engine",
        ignore=shutil.ignore_patterns("*.o", "*.so", "*.bc"),
    )
    for name in (
        "common.py",
        "serving.py",
        "sessions.py",
        "support.py",
        "startup.py",
        "fixture.sql",
    ):
        shutil.copyfile(BASE / name, destination / name)
    p = destination / "engine/src/fannbench.c"
    source = p.read_text()
    source = replace_once(
        source,
        "(arm > 9 && !FannbenchV2ArmDeclared(arm))",
        "(arm > 11 && !FannbenchV2ArmDeclared(arm))",
    )
    source += """
/* Evaluator-only. The per-query hindsight choice is supplied outside the timer.
 * Arm 10 stops; arm 11 pays the same checkpoint bookkeeping and continues.
 * No result/feature computation or truth lookup is performed here. */
static int oracleCheckpoint = 0;
PG_FUNCTION_INFO_V1(fannbench_oracle_set);
Datum
fannbench_oracle_set(PG_FUNCTION_ARGS)
{
    int cp = PG_GETARG_INT32(0);
    if ((confirmationArm != 10 && confirmationArm != 11) || cp < 0 || cp > 4096 ||
        executionState.active || !XactReadOnly || !IsolationUsesXactSnapshot())
        elog(ERROR, "oracle target requires the attached evaluator snapshot");
    oracleCheckpoint = cp;
    PG_RETURN_INT32(cp);
}
int FannbenchOracleCheckpoint(void) { return oracleCheckpoint; }
"""
    p.write_text(source)
    p = destination / "engine/src/fannbench.h"
    p.write_text(p.read_text() + "\nextern int FannbenchOracleCheckpoint(void);\n")
    p = destination / "engine/src/hnswutils.c"
    source = p.read_text()
    source = replace_once(
        source,
        "int confirmLast = 64;",
        "int confirmLast = (confirmArm == 10 || confirmArm == 11) ? "
        "FannbenchOracleCheckpoint() : 64;",
    )
    source = replace_once(
        source,
        "if ((confirmCheckpoint == 16 || confirmCheckpoint == 32 || "
        "confirmCheckpoint == 64) &&\n\t\t\t\t\t"
        "ConfirmStop(confirmArm, confirmCheckpoint, C, W, base))",
        "if ((confirmArm == 10 && confirmCheckpoint == confirmLast) ||\n"
        "                    (confirmArm != 10 && confirmArm != 11 &&\n"
        "                     (confirmCheckpoint == 16 || confirmCheckpoint == 32 || "
        "confirmCheckpoint == 64) &&\n"
        "                     ConfirmStop(confirmArm, confirmCheckpoint, C, W, base)))",
    )
    p.write_text(source)
    functions = (BASE / "functions.sql").read_text()
    functions += (
        "\nCREATE FUNCTION fannagent.oracle_set(integer) RETURNS integer AS "
        "'$libdir/vector','fannbench_oracle_set' LANGUAGE C STRICT VOLATILE;\n"
    )
    (destination / "functions.sql").write_text(functions)
    changed = {}
    for p in (destination / "engine").rglob("*"):
        if p.is_file():
            rel = p.relative_to(destination / "engine")
            old = BASE / "engine" / rel
            if p.read_bytes() != old.read_bytes():
                changed[str(rel)] = {
                    "before": hashlib.sha256(old.read_bytes()).hexdigest(),
                    "after": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
    assert set(changed) == {"src/fannbench.c", "src/fannbench.h", "src/hnswutils.c"}
    (destination / "source-delta.json").write_text(json.dumps(changed, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    prepare(parser.parse_args().destination)
