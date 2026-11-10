"""Relocate unchanged qualified A3 code and observe its original identity delegate."""

import importlib
import json
import platform
import sys
import threading
import time
from pathlib import Path

from pc_common import read, save, sha

_ORIGINAL_FRAMED = None
_CAPTURING = False


def locations(package):
    return Path(package) / "a3", Path(package) / "reference"


def configure(package):
    global _ORIGINAL_FRAMED
    package = Path(package).resolve()
    code, reference = locations(package)
    sys.path[:0] = [str(package), str(code), str(reference / "frozen/vendor"), str(reference)]
    # Load these pinned packages before the historical runner inserts its own paths.
    for name in ("fannagent.snapshot", "fannagent.store", "fannagent_pgvector.backend"):
        importlib.import_module(name)

    import exact_vector as X
    import integration as candidate
    import si_stream

    if (
        Path(X.__file__).resolve() != code / "exact_vector.py"
        or Path(candidate.__file__).resolve() != code / "integration.py"
        or Path(si_stream.__file__).resolve() != reference / "si_stream.py"
    ):
        raise RuntimeError("Qualified A3 module origin differs")
    X.PACKAGE, X.FREEZE = reference, package / "A3-FREEZE.json"
    X.verify_sources()
    expected = read(package / "RESOURCE-FREEZE.json")["qualified_native_correctness"]["code_sha256"]
    if candidate.code_hashes() != expected:
        raise RuntimeError("Qualified A3 source changed")
    if _ORIGINAL_FRAMED is None:
        _ORIGINAL_FRAMED = si_stream.framed
    assert_restored()
    return X, candidate, si_stream


def assert_restored():
    import ev_metadata
    import exact_vector as X
    import integration as candidate
    import si_stream

    import fannagent.snapshot as snapshot
    import fannagent.store as store

    if (
        _CAPTURING
        or ev_metadata._ACTIVE is not None
        or X._ACTIVE is not None
        or candidate._LOADING is not None
        or snapshot.digest is not store.digest
        or (_ORIGINAL_FRAMED is not None and si_stream.framed is not _ORIGINAL_FRAMED)
    ):
        raise RuntimeError("A3 producer/identity/helper bindings are not restored")


def preflight(package, out):
    X, candidate, stream = configure(package)
    from sa_driver import provenance

    cfg = read(Path(package) / "experiment.json")
    _, reference = locations(package)
    actual = provenance()
    target = read(
        reference
        / ("DRIVER-REFERENCE.json" if cfg["synthetic_fixture"] else "IMAGE-REFERENCE.json")
    )
    if actual != target:
        raise RuntimeError("Exact interpreter/private-hook/library reference differs")
    if not cfg["synthetic_fixture"] and platform.python_version() != "3.12.15":
        raise RuntimeError("Exact qualified target CPython required")
    from ev_metadata import preflight as metadata_preflight

    save(
        Path(out) / "ev-metadata-preflight.json",
        metadata_preflight(read(reference / "origin-source.json")["metadata"]),
    )
    if cfg["synthetic_fixture"]:
        # This branch is reachable only in mocked local runtime fixtures: the real
        # runtime rejects synthetic packages before bootstrap/restore/connection.
        from fannagent.store import canonical

        spec = candidate.FixtureSpec(
            cfg["fixture_snapshot_rows"],
            canonical(read(reference / "origin-source.json")["metadata"]),
            cfg["snapshot_identity"],
        )
    else:
        spec = candidate.native_spec(Path(package).resolve())
    proof = dict(
        schema="startup-exact-vector.resource-preflight.v1",
        status="pass",
        synthetic_fixture=cfg["synthetic_fixture"],
        before_restore=True,
        actual_provenance=actual,
        reference_sha256=sha(reference / "IMAGE-REFERENCE.json"),
        code_sha256=candidate.code_hashes(),
        helper_sha256=sha(reference / "si_stream.py"),
        module_origins={
            n: str(Path(importlib.import_module(n).__file__).resolve())
            for n in (
                "exact_vector",
                "integration",
                "si_stream",
                "fannagent.snapshot",
                "fannagent.store",
                "fannagent_pgvector.backend",
            )
        },
        rows=spec.rows,
        identity=spec.identity,
        bindings_restored=True,
        ANN_searches=0,
        exact_searches=0,
    )
    save(Path(out) / "ev-runtime-preflight.json", proof)
    save(Path(out) / "identity-preflight.json", stream.preflight(reference))
    assert_restored()
    return spec


def factory_type():
    import integration

    return integration.factory_type()


def prepare_requests(main, factory, package, notify=lambda *a: None, record=lambda x: None):
    """Delegate unchanged startup; capture just its existing bounded framing result."""
    global _CAPTURING
    import integration as candidate
    import si_stream

    assert_restored()
    if threading.current_thread() is not threading.main_thread() or len(threading.enumerate()) != 1:
        raise RuntimeError("Concurrent framing observation prohibited")
    _, reference = locations(package)
    original = si_stream.framed
    value = dict(
        status="failed",
        invocations=0,
        binding_restored=False,
        digest_completed=False,
        error_type=None,
        provenance=si_stream.provenance(reference),
        qualified_code_sha256=candidate.code_hashes(),
        helper_binding_restored=False,
    )
    start = time.monotonic_ns()

    def framed(*args, **kwargs):
        value["invocations"] += 1
        if value["invocations"] != 1:
            raise RuntimeError("Exactly one original identity framing invocation required")
        notify("snapshot_identity_stream")
        begin = time.monotonic_ns()
        try:
            value["stream"] = original(*args, **kwargs)
            value["digest_completed"] = True
            return value["stream"]
        finally:
            value["elapsed_ns"] = time.monotonic_ns() - begin
            notify("snapshot_identity_stream_end")

    from ev_metadata import View

    metadata = View(main["native640"].backend, factory.spec.fields_json)
    _CAPTURING = True
    si_stream.framed = framed
    result = None
    error = None
    try:
        with metadata:
            result = candidate.prepare_requests(main, factory, package, factory.spec, notify)
    except BaseException as exc:
        error = exc
        value["error_type"] = type(exc).__name__
        raise
    finally:
        intact = si_stream.framed is framed
        # Restore before any proof check or publication, even for KeyboardInterrupt.
        si_stream.framed = original
        _CAPTURING = False
        value["helper_binding_restored"] = intact and si_stream.framed is original
        value["metadata_adapter"] = metadata.record
        value.setdefault("elapsed_ns", time.monotonic_ns() - start)
        try:
            assert_restored()
            value["binding_restored"] = True
            if not intact:
                raise RuntimeError("Framing observer binding changed")
            if result is not None:
                if value["invocations"] != 1 or not value["digest_completed"]:
                    raise RuntimeError("Complete original framing proof required")
                value["status"] = "complete"
        finally:
            if len(json.dumps(value).encode()) > 65536:
                raise RuntimeError("Identity proof byte cap") from error
            record(value)
    return result


def retention(factory, phase):
    """Prove row/root/reader aliases without decoding or releasing any vector."""
    import exact_vector as X

    assert_restored()
    snapshot = factory.snapshot
    spec = factory.spec
    if (
        snapshot is None
        or len(snapshot.rows) != spec.rows
        or snapshot.identity != spec.identity
        or any(type(row["vector"]) is not X.PackedVector for row in snapshot.rows)
        or any(
            r.backend._snapshot is not snapshot
            or r.backend.__dict__.get("_packed_spec") is not spec
            or "snapshot" in r.backend.__dict__
            for r in factory.readers
        )
    ):
        raise RuntimeError("Packed snapshot/root/reader ownership changed")
    return dict(
        phase=phase,
        snapshot_token=id(snapshot),
        rows=len(snapshot.rows),
        identity=snapshot.identity,
        readers=len(factory.readers),
        shared_aliases=len(factory.readers),
        live_readers=sum(not r.closed for r in factory.readers),
        packed_vectors=spec.rows,
        bindings_restored=True,
        retained=True,
    )
