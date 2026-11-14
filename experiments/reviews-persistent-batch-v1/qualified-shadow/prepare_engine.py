"""Stage a shadow-instrumented copy of the original Reviews engine source."""

import argparse
import json
from pathlib import Path
from shutil import copytree

from rb_plan import ROOT, pinned, require

CAMPAIGN = (
    ROOT
    / "trials/torch-reviews-results"
    / "reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y/package"
)
MANIFEST_SHA = "3a50e8296bdba9dbb8c018ef742af2b2e868ae80f85172c876511a015fd5838c"
HERE = Path(__file__).resolve().parent


def insert(path, anchor, addition, *, after=False):
    original = path.read_text()
    require(original.count(anchor) == 1, f"Native anchor changed: {path.name}")
    path.write_text(original.replace(anchor, anchor + addition if after else addition + anchor))


def stage(output):
    pins = json.loads(pinned(CAMPAIGN / "manifest.json", MANIFEST_SHA))["files"]
    engine = CAMPAIGN / "engine"
    engine_pins = {name: sha for name, sha in pins.items() if name.startswith("engine/")}
    require(
        {str(path.relative_to(CAMPAIGN)) for path in engine.rglob("*") if path.is_file()}
        == engine_pins.keys()
        and not any(path.is_symlink() for path in engine.rglob("*")),
        "Engine source inventory differs",
    )
    for name, sha in engine_pins.items():
        pinned(CAMPAIGN / name, sha)
    copytree(engine, output)
    src = output / "src"
    insert(src / "fannbench.c", '#include "fmgr.h"\n', '#include "executor/spi.h"\n', after=True)
    insert(
        src / "fannbench.c",
        '#include "utils/lsyscache.h"\n',
        '#include "utils/hsearch.h"\n#include "utils/memutils.h"\n',
        after=True,
    )
    insert(
        src / "fannbench.c",
        "typedef struct FannbenchExecutionState\n",
        """
typedef struct ShadowObservation
{
	int checkpoint;
	int count;
	double tenth;
	uint64 nanos;
	uint64 top_tids[10];
	int turnover;
} ShadowObservation;

""",
    )
    insert(
        src / "fannbench.c",
        "typedef struct FannbenchExecutionState\n{\n",
        "\tShadowObservation shadow[3];\n",
        after=True,
    )
    insert(
        src / "fannbench.c",
        "\nbool\nFannbenchHnswObserveDistances(",
        (HERE / "observer.inc").read_text(),
    )
    insert(
        src / "fannbench.c",
        "    ResetExecutionState();\n\tpfree(nonce);",
        "    memcpy(completedShadow, executionState.shadow, sizeof(completedShadow));\n",
    )
    insert(
        src / "fannbench.h",
        "bool\t\tFannbenchHnswObserveDistances(",
        """
int FannbenchShadowCheckpoint(Relation index);
void FannbenchShadowStart(void);
bool FannbenchShadowQualifies(ItemPointer tid);
void FannbenchShadowRecord(int checkpoint, int count, double tenth,
                           const uint64 top_tids[10], uint64 nanos);

""",
    )
    insert(
        src / "hnswutils.c",
        "/*\n * Algorithm 2 from paper\n */",
        (HERE / "retained.inc").read_text(),
    )
    insert(
        src / "hnswutils.c",
        "\t\t\tFannbenchHnswRetained(wlen, ef);",
        "\n\t\tif (lc == 0 && !inserting && index != NULL)\n\t\t\tShadowRetained(index, W, base);",
        after=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    stage(parser.parse_args().output)
