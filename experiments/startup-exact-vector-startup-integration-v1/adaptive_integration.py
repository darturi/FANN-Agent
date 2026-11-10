"""Adaptive codec in the original startup producer; native release stays closed."""

import threading
from types import MethodType

import exact_codec as codec
import exact_vector as X
import integration as original

_LOADING = None
FixtureSpec = original.FixtureSpec


def code_hashes():
    return original.code_hashes()


def validate_spec(spec):
    if type(spec) is not FixtureSpec:
        raise RuntimeError(
            "Adaptive startup accepts bounded fixture specs only; native qualification absent"
        )
    codec.verify_sources()


def native_spec(package):
    raise RuntimeError("Adaptive startup has no native correctness/release allowance")


class Identity(X.FixtureIdentity):
    def __init__(self, spec):
        super().__init__()
        self.spec = spec

    def canonical(self, value):
        if type(value) is list:
            return self.store.canonical(value)
        return self.store.canonical(codec.plain_row(value))

    def digest(self, payload):
        self.calls += 1
        if (
            X._ACTIVE is not self
            or self.calls != 1
            or type(payload) is not dict
            or set(payload) != {"rows", "fields"}
            or type(payload["rows"]) is not list
            or len(payload["rows"]) != self.spec.rows
            or type(payload["fields"]) is not list
            or self.store.canonical(payload["fields"]) != self.spec.fields_json
        ):
            raise RuntimeError("Integrated identity count/field/scope mismatch")
        self.record = self.stream.framed(payload, self.canonical)
        if self.record["digest"] != self.spec.identity:
            raise RuntimeError("Integrated exact original identity mismatch")
        return self.record["digest"]


def _produce(backend, spec):
    """Original client cursor/SQL/constructor; pack one decoded vector before append."""
    from fannagent_pgvector.profiles import DATA_PROFILE
    from psycopg import sql

    from fannagent.snapshot import Snapshot
    from fannagent.store import canonical

    fields = backend.store.get("source_manifest")["metadata"]
    if canonical(fields) != spec.fields_json:
        raise RuntimeError("Producer metadata changed before connection")
    conn = backend._connect()
    identifiers = [backend.target.id_column, backend.target.vector_column] + [
        f["name"] for f in fields
    ]
    statement = sql.SQL("SELECT {} FROM {} ORDER BY {}").format(
        sql.SQL(",").join(sql.Identifier(n) for n in identifiers),
        backend.relation,
        sql.Identifier(backend.target.id_column),
    )
    rows = []
    with conn.cursor() as cursor:
        cursor.execute(statement)
        for raw in cursor:
            if len(rows) >= spec.rows or len(raw) != 2 + len(fields):
                raise RuntimeError("Producer row count/shape cap")
            vector = codec.pack_json_vector(raw[1])
            rows.append(
                {
                    "source_id": raw[0],
                    "vector": vector,
                    "metadata": dict(zip([f["name"] for f in fields], raw[2:], strict=True)),
                }
            )
    if len(rows) != spec.rows:
        raise RuntimeError("Producer row count differs")
    with Identity(spec):
        result = Snapshot(rows, fields, DATA_PROFILE)
    return result


def load_snapshot(backend, spec):
    """Bind only the selected owned instance, restore before publishing its cache."""
    global _LOADING
    from fannagent_pgvector.backend import NativeBackend

    validate_spec(spec)
    if not isinstance(backend, NativeBackend):
        raise RuntimeError("Only the frozen owned startup backend is allowed")
    X.verify_sources()
    if (
        _LOADING is not None
        or threading.current_thread() is not threading.main_thread()
        or len(threading.enumerate()) != 1
        or "snapshot" in backend.__dict__
    ):
        raise RuntimeError("Nested/concurrent/foreign producer binding")
    previous = backend._snapshot
    if previous is not None:
        if (
            backend.__dict__.get("_packed_spec") is not spec
            or previous.identity != spec.identity
            or len(previous.rows) != spec.rows
            or any(type(r["vector"]) is not codec.ExactVector for r in previous.rows)
        ):
            raise RuntimeError("Cached snapshot is not the qualified packed value")
        return previous
    _LOADING = backend
    bound = MethodType(lambda self: _produce(self, spec), backend)
    backend.snapshot = bound
    candidate = None
    try:
        candidate = backend.snapshot()
        if backend.__dict__.get("snapshot") is not bound or backend._snapshot is not previous:
            raise RuntimeError("Producer instance binding/cache changed during load")
    finally:
        backend.__dict__.pop("snapshot", None)
        backend._snapshot = previous
        _LOADING = None
    # Digest/instance bindings are already restored, and all constructor checks passed.
    backend._snapshot = candidate
    backend._packed_spec = spec
    return candidate


def prepare_requests(main, factory, package, spec, notify=lambda *a: None):
    """Actual integration entry: validate identity, eligibility and admission before aliases."""
    from pc_common import lines
    from pc_results import admit
    from pc_snapshot import validate_snapshot

    if factory.snapshot is not None or factory.requests:
        raise RuntimeError("Startup state already published; never repeat")
    readers = list(main.values())
    if not readers or len(readers) > 10:
        raise RuntimeError("Reader scope differs")
    before = [
        (
            r.backend._snapshot,
            "_packed_spec" in r.backend.__dict__,
            r.backend.__dict__.get("_packed_spec"),
        )
        for r in readers
    ]
    try:
        notify("snapshot_load")
        snapshot = load_snapshot(main["native640"].backend, spec)
        notify("snapshot_identity")
        proof = validate_snapshot(snapshot, package)
        notify("request_admission")
        items = admit(snapshot, lines(package / "queries.jsonl"))
        requests = {row["query"]["id"]: row["query"] for row in items}
        for reader in readers:
            if reader.closed:
                raise RuntimeError("Reader closed before publication")
        factory.snapshot = snapshot
        factory.requests = requests
        for reader in readers:
            reader.backend._snapshot = snapshot
            reader.backend._packed_spec = spec
        return items, proof
    except BaseException:
        factory.snapshot = None
        factory.requests = {}
        for reader, (previous, present, tag) in zip(readers, before, strict=True):
            reader.backend._snapshot = previous
            if present:
                reader.backend._packed_spec = tag
            else:
                reader.backend.__dict__.pop("_packed_spec", None)
        raise


def factory_type():
    """Extend the existing search-prohibited startup factory, without changing its source."""
    from sr_interface import Factory as OriginalFactory

    class Factory(OriginalFactory):
        def __init__(self, *args, spec, **kwargs):
            validate_spec(spec)
            super().__init__(*args, **kwargs)
            self.spec = spec
            self.startup_codec = "adaptive"
            for cell, parent in list(self.classes.items()):

                class PackedStartup(parent):
                    def snapshot(self):
                        return load_snapshot(self, spec)

                self.classes[cell] = PackedStartup

        def create(self, *args, **kwargs):
            reader = super().create(*args, **kwargs)
            if self.snapshot is not None:
                reader.backend._packed_spec = self.spec
            return reader

    return Factory
