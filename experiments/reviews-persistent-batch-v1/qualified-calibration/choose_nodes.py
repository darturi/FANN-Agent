"""Select eligible CS nodes that match Slurm's hardware description of cs613."""

import re
import sys
from pathlib import Path

REFERENCE = "cs613"
KEYS = (
    "Arch",
    "CPUTot",
    "Sockets",
    "CoresPerSocket",
    "ThreadsPerCore",
    "RealMemory",
    "ActiveFeatures",
)
AVAILABLE = {"IDLE", "MIXED", "ALLOCATED"}


def choose(lines):
    nodes = {}
    for line in lines:
        values = dict(re.findall(r"(?:^|\s)(\w+)=([^\s]*)", line))
        if "NodeName" in values:
            nodes[values["NodeName"]] = values
    reference = nodes.get(REFERENCE)
    if reference is None or any(key not in reference for key in KEYS):
        raise ValueError(f"Cannot identify the scheduler hardware class of {REFERENCE}")
    wanted = tuple(reference[key] for key in KEYS)
    pool = sorted(
        name
        for name, node in nodes.items()
        if "cs" in node.get("Partitions", "").split(",")
        and node.get("State") in AVAILABLE
        and tuple(node.get(key) for key in KEYS) == wanted
        and re.fullmatch(r"cs[0-9]+", name)
    )
    if not pool:
        raise ValueError(f"No eligible CS nodes match {REFERENCE}")
    if REFERENCE in pool:
        pool.remove(REFERENCE)
        pool.insert(0, REFERENCE)
    return [pool[i % len(pool)] for i in range(3)]


if __name__ == "__main__":
    print(*choose(Path(sys.argv[1]).read_text().splitlines()), sep="\n")
