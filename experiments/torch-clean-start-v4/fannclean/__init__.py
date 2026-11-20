"""Clean-start discovery using the ordinary broad-stop.v3 deployment language."""

import platform
import sys
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[1]
PROJECT = EXPERIMENT.parents[1]
sys.path[:0] = [
    str(PROJECT / "src"),
    str(PROJECT / "experiments/filtered-ann-protocol-v3"),
]
if sys.platform == "linux" and platform.machine() in ("x86_64", "amd64"):
    sys.path.insert(0, str(PROJECT / "host-vendor"))
