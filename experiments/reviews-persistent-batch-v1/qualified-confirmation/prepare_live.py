"""Build an opt-in live policy on the exact qualified checkpoint implementation."""

import argparse
import json
import sys
from pathlib import Path

from rb_plan import pinned, require

HERE = Path(__file__).resolve().parent
FREEZE_SHA = "97356451b79ee0fbfec82018efb8e39fca38d4bf384741a03d63d0938e212c31"
sys.path.insert(0, str(HERE.parent / "qualified-shadow"))
from prepare_engine import insert, stage  # noqa: E402


def decision_function(freeze):
    checks = []
    for arm, key in enumerate(("baseline", "candidate"), 1):
        for clause in freeze[key]:
            predicates = [f"arm == {arm}", f"checkpoint == {clause['cp']}"]
            for feature, op, threshold in clause["conditions"]:
                require(feature in ("frontier_gap", "tenth_distance"), "Unexpected rule feature")
                require(op in ("<=", ">=") and type(threshold) is float, "Unexpected comparison")
                value = "gap" if feature == "frontier_gap" else "tenth"
                predicates.append(f"{value} {op} {threshold!r}")
            checks.append("(" + " && ".join(predicates) + ")")
    return (
        "static bool\nConfirmationRule(int arm, int checkpoint, double gap, double tenth)\n"
        "{\n\treturn " + " ||\n\t\t".join(checks) + ";\n}\n\n"
    )


def prepare(output):
    freeze = json.loads(pinned(HERE / "freeze.json", FREEZE_SHA))
    stage(output)
    src = output / "src"
    c = src / "fannbench.c"
    insert(c, '#include "catalog/pg_am.h"\n', '#include "catalog/index.h"\n')
    insert(
        c,
        "static uint64 shadowGeneration;",
        """
static Oid confirmationIndex = InvalidOid;
static int confirmationArm;
static int confirmationStop;
""",
    )
    insert(
        c,
        "\t\tshadowMembers = NULL;\n",
        """
		confirmationIndex = InvalidOid;
		confirmationArm = 0;
		confirmationStop = -1;
""",
    )
    insert(c, "\nbool\nFannbenchHnswObserveDistances(", (HERE / "live_state.inc").read_text())
    insert(
        src / "fannbench.h",
        "int FannbenchShadowCheckpoint(Relation index);",
        "int FannbenchConfirmArm(Relation index);\nvoid FannbenchConfirmStopped(int checkpoint);\n",
    )
    hnsw = src / "hnswutils.c"
    insert(
        hnsw,
        "/*\n * Algorithm 2 from paper\n */",
        decision_function(freeze) + (HERE / "live_layer.inc").read_text() + "\n",
    )
    insert(
        hnsw,
        "\tint\t\t\tunvisitedLength;\n",
        """	int confirmArm = lc == 0 && !inserting && index != NULL
		? FannbenchConfirmArm(index) : 0;
	int confirmCount = 0;
	int confirmTarget = 64;
	int confirmCheckpoint = 0;
	int confirmLast = confirmArm == 1 ? 32 : 64;
""",
        after=True,
    )
    insert(
        hnsw,
        "\t/* Add entry points to v, C, and W */",
        """
	if (confirmArm)
	{
		if (discarded != NULL || !initVisited || list_length(ep) != 1 ||
			DatumGetPointer(q->value) == NULL)
			elog(ERROR, "confirmation requires a single non-iterative cosine scan");
		/* The original scorer charges the first entry only when the graph starts at layer 0. */
		confirmCount =
			HnswPtrAccess(base, ((HnswSearchCandidate *) linitial(ep))->element)->level == 0;
	}

""",
    )
    insert(
        hnsw,
        "\t\tif (lc == 0 && !inserting &&\n\t\t\tFannbenchHnswQueueSnapshotNeeded(0))",
        """		if (confirmArm && confirmCheckpoint < confirmLast)
		{
			confirmCount += unvisitedLength;
			/* Same expanded-neighborhood boundary and target update as the shadow. */
			if (confirmCount >= confirmTarget)
			{
				confirmCheckpoint++;
				confirmTarget = (confirmCount / 64 + 1) * 64;
				if ((confirmCheckpoint == 32 ||
					(confirmArm == 2 && (confirmCheckpoint == 16 || confirmCheckpoint == 64))) &&
					ConfirmStop(confirmArm, confirmCheckpoint, C, W, base))
				{
					FannbenchConfirmStopped(confirmCheckpoint);
					break;
				}
			}
		}

""",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    prepare(parser.parse_args().output)
