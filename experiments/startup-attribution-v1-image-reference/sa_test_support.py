"""Explicit offline fixture references; never imported by a native entry point."""

from pc_common import HERE, read
from sa_driver import provenance


def reference():
    actual = provenance()
    # Both options are exact. No environment variable, wildcard or new-version fallback.
    for name in ("DRIVER-REFERENCE.json", "IMAGE-REFERENCE.json"):
        expected = read(HERE / name)
        if actual == expected:
            return expected
    raise RuntimeError("Offline fixture interpreter/library provenance is unqualified")
