"""Clean-start discovery using the ordinary broad-stop.v3 deployment language."""

import sys
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[1]
PROJECT = EXPERIMENT.parents[1]
sys.path[:0] = [
    str(PROJECT / "host-vendor"),
    str(PROJECT / "src"),
    str(PROJECT / "experiments/filtered-ann-protocol-v3"),
]
