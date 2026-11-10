"""Validate the original two functions and every local mask before any restore."""

import sys

from sa_monitor import EXPECTED, MAPS, SnapshotMonitor, idle

EXPECTED_PROOF = dict(
    source_sha256=list(EXPECTED),
    mapped_lines=[sorted(v) for v in MAPS],
    qualified_names=[
        "fannagent_pgvector.backend.NativeBackend.snapshot",
        "fannagent.snapshot.Snapshot.__init__",
    ],
    local_masks_clear=True,
    original_bindings_unchanged=True,
    before_restore=True,
)


def original_mapping(obs):
    from fannagent_pgvector.backend import NativeBackend

    from fannagent.snapshot import Snapshot

    idle()
    monitor = SnapshotMonitor(NativeBackend.snapshot, Snapshot.__init__, obs)
    monitor.validate()
    for tool in range(6):
        if any(sys.monitoring.get_local_events(tool, code) for code in monitor.codes):
            raise RuntimeError("Pre-existing original local monitoring masks")
    names = [f.__module__ + "." + f.__qualname__ for f in monitor.functions]
    if names != EXPECTED_PROOF["qualified_names"]:
        raise RuntimeError("Original function binding differs before restore")
    # No LINE events on either original function, and neither function is called.
    return {**EXPECTED_PROOF, "qualified_names": names}
