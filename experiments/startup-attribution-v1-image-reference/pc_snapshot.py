"""Startup snapshot guards use the frozen eligibility schema and separate identities."""

from pc_common import digest, lines, read, sha
from pc_results import admit

FIELD_MAP = {"m_000000": "total_votes"}


def validate_snapshot(snapshot, package):
    expected = read(package / "eligibility.json")
    if set(expected) != {"source_ids", "votes"}:
        raise RuntimeError("Frozen eligibility schema differs")
    if snapshot.field_map != FIELD_MAP:
        raise RuntimeError("Snapshot field mapping changed")
    eligibility = dict(
        source_ids=snapshot.source_ids,
        votes=[r["metadata"]["total_votes"] for r in snapshot.rows],
    )
    if digest(eligibility) != sha(package / "eligibility.json"):
        raise RuntimeError("Snapshot eligibility changed")
    identity = read(package / "experiment.json")["snapshot_identity"]
    if snapshot.identity != identity:
        raise RuntimeError("Snapshot data identity changed")
    return dict(
        eligibility_sha256=digest(eligibility),
        snapshot_identity=identity,
        field_map=dict(snapshot.field_map),
        rows=len(snapshot.rows),
    )


def prepare_requests(
    main, factory, package, notify=lambda *a: None, record=lambda x: None, diagnostic=None
):
    """The actual runtime and integration fixtures call this entire startup boundary."""
    notify("snapshot_load")
    import time

    from si_stream import ScopedIdentity, assert_restored

    started = time.monotonic_ns()
    scope = ScopedIdentity(package, notify)
    try:
        from contextlib import nullcontext

        from sa_session import snapshot_monitor

        with scope:
            with snapshot_monitor(main, diagnostic) if diagnostic else nullcontext():
                snapshot = main["native640"].backend.snapshot()
    finally:
        record(scope.record)
    assert_restored()
    if diagnostic:
        diagnostic.obs.role("snapshot_load", started, time.monotonic_ns())
    notify("snapshot_identity")
    proof = validate_snapshot(snapshot, package)
    if diagnostic:
        diagnostic.checkpoint("S13.publication_ready", {"rows": len(snapshot.rows)})
    factory.snapshot = snapshot
    for reader in main.values():
        reader.backend._snapshot = snapshot
    notify("request_admission")
    items = admit(snapshot, lines(package / "queries.jsonl"))
    factory.requests = {r["query"]["id"]: r["query"] for r in items}
    return items, proof
