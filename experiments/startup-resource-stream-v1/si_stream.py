"""Bounded original-canonical components; one scoped snapshot digest binding."""

import hashlib
import importlib
import inspect
import json
import platform
import sys
import threading
import time
from pathlib import Path

from pc_common import read, sha

FIELDS_MAX = 16 * 1024
ROW_MAX = BUFFER_MAX = 64 * 1024
TOTAL_MAX = 16 * 1024**3
_ACTIVE = None


class Writer:
    def __init__(self, sink=None, maximum=TOTAL_MAX, buffer_max=BUFFER_MAX):
        self.hash = hashlib.sha256()
        self.sink, self.maximum, self.buffer_max = sink, maximum, buffer_max
        self.buffer = bytearray()
        self.total = self.high = self.updates = 0

    def feed(self, data):
        if type(data) is not bytes or self.total + len(data) > self.maximum:
            raise RuntimeError("Identity stream byte/type cap")
        self.total += len(data)
        view = memoryview(data)
        while view:
            count = min(self.buffer_max - len(self.buffer), len(view))
            self.buffer.extend(view[:count])
            view = view[count:]
            self.high = max(self.high, len(self.buffer))
            if len(self.buffer) == self.buffer_max:
                self.flush()

    def flush(self):
        if self.buffer:
            self.hash.update(self.buffer)
            if self.sink is not None:
                self.sink(bytes(self.buffer))
            self.updates += 1
            self.buffer.clear()

    def finish(self):
        self.flush()
        return self.hash.hexdigest()


def framed(payload, canonical, *, sink=None, maximum=TOTAL_MAX, buffer_max=BUFFER_MAX):
    if type(payload) is not dict or set(payload) != {"rows", "fields"}:
        raise RuntimeError("Identity document must contain exactly rows/fields")
    rows, fields = payload["rows"], payload["fields"]
    if not isinstance(rows, list) or not isinstance(fields, list):
        raise RuntimeError("Identity document arrays required")
    writer = Writer(sink, maximum, buffer_max)
    writer.feed(b'{"fields":')
    encoded = canonical(fields)
    if len(encoded) > FIELDS_MAX:
        raise RuntimeError("Identity fields component cap")
    fields_bytes = len(encoded)
    writer.feed(encoded)
    del encoded
    writer.feed(b',"rows":[')
    rows_bytes = row_high = 0
    calls = 1
    for index, row in enumerate(rows):
        if index:
            writer.feed(b",")
        encoded = canonical(row)
        if len(encoded) > ROW_MAX:
            raise RuntimeError("Identity row component cap")
        calls += 1
        rows_bytes += len(encoded)
        row_high = max(row_high, len(encoded))
        writer.feed(encoded)
        del encoded
    writer.feed(b"]}")
    identity = writer.finish()
    return dict(
        digest=identity,
        rows=len(rows),
        component_calls=calls,
        fields_bytes=fields_bytes,
        rows_bytes=rows_bytes,
        separator_bytes=max(0, len(rows) - 1),
        framing_bytes=len(b'{"fields":') + len(b',"rows":[') + len(b"]}"),
        total_bytes=writer.total,
        max_row_bytes=row_high,
        max_pending_bytes=writer.high,
        hash_updates=writer.updates,
    )


def provenance(package):
    import fannagent.snapshot as snapshot
    import fannagent.store as store

    package = Path(package)
    sources = {}
    for key, module, relative in (
        ("snapshot", snapshot, "frozen/vendor/fannagent/snapshot.py"),
        ("store", store, "frozen/vendor/fannagent/store.py"),
    ):
        actual = sha(Path(module.__file__))
        if actual != sha(package / relative):
            raise RuntimeError("Effective frozen identity source differs: " + key)
        sources[key] = actual
    if platform.python_implementation() != "CPython" or sys.version_info[:2] != (3, 12):
        raise RuntimeError("Pinned CPython 3.12 runtime family required")
    encoder = Path(inspect.getsourcefile(json.JSONEncoder))
    return dict(
        implementation=platform.python_implementation(),
        python_version=sys.version,
        cache_tag=sys.implementation.cache_tag,
        encoder_sha256=sha(encoder),
        json_module_sha256=sha(Path(json.__file__)),
        helper_sha256=sha(Path(__file__)),
        sources=sources,
        binding_module="fannagent.snapshot",
        binding_name="digest",
        original="fannagent.store.digest",
    )


class ScopedIdentity:
    def __init__(self, package, notify=lambda *a: None):
        self.package, self.notify = Path(package), notify
        cfg = read(self.package / "experiment.json")
        self.expected_rows = (
            cfg.get("fixture_snapshot_rows", 247286) if cfg["synthetic_fixture"] else 247286
        )
        self.expected_identity = cfg["snapshot_identity"]
        self.fields = read(self.package / "origin-source.json")["metadata"]
        self.module = importlib.import_module("fannagent.snapshot")
        self.store = importlib.import_module("fannagent.store")
        self.original = self.store.digest
        self.canonical = self.store.canonical
        self.bound = self.digest
        self.record = dict(
            status="failed",
            invocations=0,
            binding_restored=False,
            digest_completed=False,
            error_type=None,
            provenance=provenance(self.package),
        )
        self.entered = False

    def __enter__(self):
        global _ACTIVE
        if (
            _ACTIVE is not None
            or threading.current_thread() is not threading.main_thread()
            or len(threading.enumerate()) != 1
            or self.module.digest is not self.original
        ):
            raise RuntimeError("Unexpected/concurrent/nested snapshot identity binding")
        try:
            _ACTIVE = self
            self.module.digest = self.bound
            self.entered = True
            return self
        except BaseException:
            self.module.digest = self.original
            _ACTIVE = None
            raise

    def digest(self, payload):
        self.record["invocations"] += 1
        if self.record["invocations"] != 1 or _ACTIVE is not self:
            raise RuntimeError("Identity invocation/scope differs")
        if (
            type(payload) is not dict
            or set(payload) != {"fields", "rows"}
            or payload["fields"] != self.fields
            or type(payload["rows"]) is not list
            or len(payload["rows"]) != self.expected_rows
            or any(
                type(r) is not dict
                or set(r) != {"source_id", "vector", "metadata"}
                or type(r["source_id"]) is not int
                or type(r["vector"]) is not list
                or len(r["vector"]) != 768
                or type(r["metadata"]) is not dict
                or set(r["metadata"]) != {"total_votes"}
                or type(r["metadata"]["total_votes"]) is not int
                for r in payload["rows"]
            )
        ):
            raise RuntimeError("Identity frozen row/field scope differs")
        self.notify("snapshot_identity_stream")
        start = time.monotonic_ns()
        try:
            self.record["stream"] = framed(payload, self.canonical)
            if self.record["stream"]["digest"] != self.expected_identity:
                raise RuntimeError("Streamed snapshot identity differs")
            self.record["digest_completed"] = True
            return self.record["stream"]["digest"]
        finally:
            self.record["elapsed_ns"] = time.monotonic_ns() - start
            self.notify("snapshot_identity_stream_end")

    def __exit__(self, typ, value, traceback):
        global _ACTIVE
        intact = self.module.digest is self.bound and _ACTIVE is self
        # Restore before any validation, notification or summary write can fail.
        self.module.digest = self.original
        _ACTIVE = None
        self.record["binding_restored"] = (
            self.module.digest is self.store.digest is self.original
            and self.store.canonical is self.canonical
        )
        self.record["error_type"] = typ.__name__ if typ else None
        if not intact or not self.record["binding_restored"]:
            raise RuntimeError("Identity binding changed or restoration failed")
        if typ is None:
            if (
                self.record["invocations"] != 1
                or not self.record["digest_completed"]
                or "stream" not in self.record
            ):
                raise RuntimeError("Exactly one full identity invocation required")
            self.record["status"] = "complete"
        return False


def preflight(package):
    """Small fixed literal byte parity in the actual interpreter, no database work."""
    import fannagent.store as store

    assert_restored()
    start = time.process_time()
    cases = [
        dict(fields=[], rows=[]),
        dict(rows=[dict(vector=[-0.0, 0, 0.0, 1e-30], source_id=1, metadata={})], fields=[]),
        dict(fields=[dict(name='\u03bb\n"', nullable=False)], rows=[{"b": True, "a": None}]),
        dict(fields=[], rows=[dict(v=1.0000000000000002), dict(v=-1.7976931348623157e308)]),
        dict(fields=[], rows=[dict(v=5e-324), dict(v=1e20), dict(v=10**20)]),
        dict(fields=[], rows=[dict(v="\U0001f600\\/\t"), dict(v=[1, 2, False, None])]),
        dict(fields=[dict(b=2, a=1)], rows=[dict(z={"b": 2, "a": 1})]),
        dict(fields=[], rows=[dict(v=-2.2250738585072014e-308), dict(v=1e-6)]),
    ]
    total = 0
    for payload in cases:
        oracle = store.canonical(payload)
        total += len(oracle)
        if total > 1024**2 or time.process_time() - start > 5:
            raise RuntimeError("Literal encoder preflight cap")
        position = 0

        def compare(chunk):
            nonlocal position
            if chunk != oracle[position : position + len(chunk)]:
                raise RuntimeError("Literal canonical byte parity differs")
            position += len(chunk)

        result = framed(payload, store.canonical, sink=compare)
        if position != len(oracle) or result["digest"] != hashlib.sha256(oracle).hexdigest():
            raise RuntimeError("Literal encoder parity differs")
    elapsed = time.process_time() - start
    if elapsed > 5:
        raise RuntimeError("Literal encoder preflight CPU cap")
    assert_restored()
    return dict(
        status="pass",
        cases=len(cases),
        oracle_bytes=total,
        cpu_seconds=elapsed,
        provenance=provenance(package),
    )


def assert_restored():
    import fannagent.snapshot as snapshot
    import fannagent.store as store

    if _ACTIVE is not None or snapshot.digest is not store.digest:
        raise RuntimeError("Identity scope remains active after snapshot acquisition")
