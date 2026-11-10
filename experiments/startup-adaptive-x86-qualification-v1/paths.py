"""Owned local workspace mirrors native absolute read-only mounts; source bytes unchanged."""

import importlib
import sys
from pathlib import Path

MAIN = "agent/experiments/startup-attribution-v1-image-reference"
A3 = "agent/experiments/startup-exact-vector-startup-integration-v1"
REF = (
    "trials/torch-reviews-startup-attribution-v1-image-reference/"
    "torch-startup-attribution-v1-image-reference"
)
STREAM = "trials/torch-reviews-startup-resource-stream-v1/torch-startup-resource-stream-v1"
A1 = "trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1"
AUDIT = "trials/torch-reviews-startup-exact-vector-compatibility-v1/postrun-audit-2026-10-31"


def configure(workspace, source, kind):
    w = Path(workspace).resolve()
    source = Path(source).resolve()
    ref = w / REF
    sys.path[:0] = [str(source), str(source / "a3"), str(ref / "frozen/vendor"), str(ref)]
    e = importlib.import_module("experiment")
    if Path(e.__file__).resolve() != source / "experiment.py":
        raise RuntimeError("Wrong relocated builder origin")
    e.ROOT = w
    e.SOURCE = w / (A1 if kind == "main" else STREAM)
    e.OUTPUT = w / (
        "trials/torch-reviews-startup-attribution-v1-image-reference"
        if kind == "main"
        else "trials/torch-reviews-startup-exact-vector-startup-integration-v1"
    )
    if kind != "main":
        e.REFERENCE = ref
        e.QUALIFIED = w / AUDIT
        x = importlib.import_module("exact_vector")
        x.ROOT = w
        x.PACKAGE = ref
        x.FREEZE = source / "A3-FREEZE.json"
    return e
