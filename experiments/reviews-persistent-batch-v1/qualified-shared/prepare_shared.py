"""Stage the shared membership variant of the frozen live stop module."""

import argparse
import sys
from pathlib import Path

from rb_plan import require

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "qualified-confirmation"))
from prepare_live import insert, prepare  # noqa: E402


def stage(output):
    prepare(output)
    c = output / "src/fannbench.c"
    insert(c, "#include <errno.h>\n", "#include <fcntl.h>\n#include <sys/mman.h>\n", after=True)
    insert(c, "static void\nShadowEndTransaction(", (HERE / "shared_lookup.inc").read_text())
    insert(c, "\t\tshadowMembers = NULL;\n", "\t\tConfirmUnmap();\n")
    lookup = "\tShadowMember *member = hash_search(shadowMembers, &key, HASH_FIND, NULL);"
    insert(
        c,
        lookup,
        "\tShadowMember *member;\n\n\tif (confirmMap)\n\t\treturn ConfirmQualifies(tid);\n",
        after=False,
    )
    insert(
        c, "PG_FUNCTION_INFO_V1(fannbench_confirm_last);", (HERE / "shared_attach.inc").read_text()
    )
    old = "if (!shadowMembers || executionState.active || !XactReadOnly ||"
    text = c.read_text()
    require(text.count(old) == text.count(lookup) == 1, "Unexpected live confirmation guard")
    c.write_text(
        text.replace(old, old.replace("!shadowMembers", "(!shadowMembers && !confirmMap)")).replace(
            lookup, lookup.replace("ShadowMember *", "")
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    stage(parser.parse_args().output)
