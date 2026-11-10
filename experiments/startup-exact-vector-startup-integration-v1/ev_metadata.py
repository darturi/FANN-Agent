"""One bounded ordinary-metadata read; immutable reader state is never modified."""

import hashlib
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

_ACTIVE = None
MAX_BYTES = 16384


class View:
    def __init__(self, backend, expected):
        self.backend, self.expected = backend, expected
        self.store = backend.store
        self.original = self.store.get
        self.source = backend.state["source_manifest"]
        self.record = dict(
            status="failed",
            source_reads=0,
            metadata_bytes=len(expected),
            metadata_sha256=hashlib.sha256(expected).hexdigest(),
            restored_before_producer_connection=False,
            original_state_unchanged=False,
            final_binding_restored=False,
        )
        self.bound = self.get

    def __enter__(self):
        global _ACTIVE
        from pc_interface import FrozenDict, FrozenList

        from fannagent.store import canonical

        if (
            _ACTIVE is not None
            or threading.current_thread() is not threading.main_thread()
            or len(threading.enumerate()) != 1
            or type(self.store) is not SimpleNamespace
            or set(vars(self.store)) != {"get"}
            or type(self.source) is not FrozenDict
            or type(self.source.get("metadata")) is not FrozenList
            or type(self.expected) is not bytes
            or len(self.expected) > MAX_BYTES
            or canonical(self.source["metadata"]) != self.expected
        ):
            raise RuntimeError("Owned frozen metadata adapter scope/type/identity differs")
        self.fields = self.source["metadata"]
        _ACTIVE = self
        self.store.get = self.bound
        return self

    def get(self, key, default=None):
        from fannagent.store import canonical

        value = self.original(key, default)
        if key != "source_manifest":
            return value
        self.record["source_reads"] += 1
        if _ACTIVE is not self or self.record["source_reads"] != 1 or value is not self.source:
            raise RuntimeError("Metadata view read/ownership differs")
        ordinary = json.loads(self.expected)
        if type(ordinary) is not list or canonical(ordinary) != self.expected:
            raise RuntimeError("Ordinary metadata canonical bytes differ")
        result = {**value, "metadata": ordinary}
        # The qualified _produce reads metadata before _connect. Restore here,
        # before returning that read, rather than waiting for cache publication.
        self.store.get = self.original
        self.record["restored_before_producer_connection"] = True
        return result

    def __exit__(self, typ, value, traceback):
        global _ACTIVE
        intact = self.store.get in (self.bound, self.original) and _ACTIVE is self
        self.store.get = self.original
        _ACTIVE = None
        self.record["final_binding_restored"] = self.store.get is self.original
        self.record["original_state_unchanged"] = (
            self.backend.state["source_manifest"] is self.source
            and self.source["metadata"] is self.fields
        )
        if not intact or not self.record["original_state_unchanged"]:
            raise RuntimeError("Frozen metadata ownership/binding changed; original restored")
        if typ is None:
            if (
                self.record["source_reads"] != 1
                or not self.record["restored_before_producer_connection"]
            ):
                raise RuntimeError("Exactly one restored metadata view read required")
            self.record["status"] = "complete"
        return False


def preflight(fields):
    """Eight literal boundary checks, no rows/DB/SQL, in the actual interpreter."""
    from pc_interface import freeze

    from fannagent.store import canonical

    started = time.process_time()
    expected = canonical(fields)

    def backend(metadata=fields):
        state = {"source_manifest": freeze({"metadata": metadata, "fixed": "unchanged"})}
        return SimpleNamespace(
            state=state,
            store=SimpleNamespace(get=lambda key, default=None: state.get(key, default)),
        )

    b = backend()
    original = b.store.get
    with View(b, expected) as view:
        ordinary = b.store.get("source_manifest")
        if (
            type(ordinary["metadata"]) is not list
            or canonical(ordinary["metadata"]) != expected
            or b.store.get is not original
        ):
            raise RuntimeError("Literal metadata conversion/restoration differs")
    if view.record["status"] != "complete":
        raise RuntimeError("Literal metadata view incomplete")
    cases = 1
    for fault in (
        "identity",
        "oversize",
        "unused",
        "type",
        "binding",
        "interrupt_before",
        "interrupt_after",
    ):
        b = backend([{"name": "x" * (MAX_BYTES + 1)}]) if fault == "oversize" else backend()
        original = b.store.get
        if fault == "type":
            b.state["source_manifest"] = {"metadata": fields}
        check = b"[]" if fault == "identity" else canonical(b.state["source_manifest"]["metadata"])
        try:
            with View(b, check):
                if fault == "binding":
                    b.store.get = lambda *a: None
                elif fault == "interrupt_before":
                    raise KeyboardInterrupt("literal before read")
                elif fault == "interrupt_after":
                    b.store.get("source_manifest")
                    raise KeyboardInterrupt("literal after read")
        except (RuntimeError, KeyboardInterrupt):
            if b.store.get is not original or _ACTIVE is not None:
                raise RuntimeError("Literal metadata exception restoration failed") from None
        else:
            raise RuntimeError("Invalid literal metadata adapter scope was accepted")
        cases += 1
    elapsed = time.process_time() - started
    if elapsed > 1:
        raise RuntimeError("Metadata literal preflight CPU ceiling")
    return dict(
        status="pass",
        cases=cases,
        metadata_bytes=len(expected),
        metadata_sha256=hashlib.sha256(expected).hexdigest(),
        cpu_seconds=elapsed,
        helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        original_state_unchanged=True,
        bindings_restored=True,
        real_SQL=0,
    )
