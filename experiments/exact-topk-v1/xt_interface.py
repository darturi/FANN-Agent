"""Single-reader ownership; only bind/settings views override the frozen backend."""

import copy
import time

from xt_common import COUNTS, MODES, digest, effective


def immutable(*args, **kwargs):
    raise TypeError("Privately admitted state is immutable")


class FrozenDict(dict):
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = immutable

    def __deepcopy__(self, memo):
        return {copy.deepcopy(k, memo): copy.deepcopy(v, memo) for k, v in self.items()}


class FrozenList(list):
    __setitem__ = __delitem__ = append = clear = extend = insert = pop = remove = reverse = sort = (
        __iadd__
    ) = __imul__ = immutable

    def __deepcopy__(self, memo):
        return [copy.deepcopy(v, memo) for v in self]


def freeze(value):
    if isinstance(value, dict):
        return FrozenDict({k: freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return FrozenList([freeze(v) for v in value])
    return value


def bound_class(Base, level):
    if type(level) is not str or level not in MODES:
        raise ValueError("Fixed reader mode must be native640 or exact10")

    class BoundBackend(Base):
        def _settings(self, conn, *, local=True, source=None):
            return super()._settings(
                conn,
                local=local,
                source=effective(
                    self.state["source_manifest"] if source is None else source, level
                ),
            )

        def _bind(self, conn, source):
            return super()._bind(conn, effective(source, level))

    return BoundBackend


class OwnedReader:
    def __init__(self, backend, level, identity):
        self.backend, self.mode, self.identity = backend, level, identity
        self.connection = backend._connect()
        backend.state["source_manifest"] = self.origin = freeze(backend.state["source_manifest"])
        backend._binding = self.binding = freeze(backend._binding)
        expected = effective(self.origin, level)
        if self.binding != expected:
            self.close()
            raise RuntimeError("Effective binding differs")
        self.closed = False
        self.check()

    def check(self):
        b, c = self.backend, self.connection
        if (
            self.closed
            or b.conn is not c
            or c.closed
            or not c.autocommit
            or c.info.transaction_status != 0
            or b._binding_conn is not c
            or b._binding is not self.binding
            or b.state["source_manifest"] is not self.origin
        ):
            raise RuntimeError("Reader closed/connection or immutable binding changed; no replay")

    def native(self, query, budget, operation):
        try:
            self.check()
            budget.reserve(operation)
            result = self.backend.execute_probe(query, mode="native")
            self.check()
            return result
        except BaseException:
            self.close()
            raise

    def exact(self, query, budget, operation):
        try:
            self.check()
            budget.reserve(operation)
            result = self.backend.exact_reference(query)
            self.check()
            return result
        except BaseException:
            self.close()
            raise

    def close(self):
        self.closed = True
        self.backend.close()


class Factory:
    def __init__(self, Base, bundle, work):
        self.Base, self.bundle, self.work = Base, bundle, work
        self.classes = {level: bound_class(Base, level) for level in MODES}
        self.readers, self.admissions, self.snapshot = [], [], None
        self.maximum_live = 0
        from xt_metadata import Observer

        self.observer = Observer()

    def create(self, level, role):
        if type(level) is not str or level not in MODES or len(self.readers) >= 14:
            raise ValueError("Reader admission limit/type/level")
        if sum(not r.closed for r in self.readers) >= COUNTS["maximum_live_readers"]:
            raise ValueError("Live reader ceiling")
        start = time.perf_counter_ns()
        backend = self.classes[level](self.bundle, self.work)
        if self.snapshot is not None:
            backend._snapshot = self.snapshot
        try:
            reader = OwnedReader(backend, level, role)
        except BaseException:
            backend.close()
            raise
        reader.observer = self.observer
        self.readers.append(reader)
        self.maximum_live = max(self.maximum_live, sum(not r.closed for r in self.readers))
        end = time.perf_counter_ns()
        self.admissions.append(
            {
                "reader": role,
                "mode": level,
                "start_ns": start,
                "end_ns": end,
                "outer_ms": (end - start) / 1e6,
                "origin": reader.origin,
                "effective": reader.binding,
                "origin_sha256": digest(reader.origin),
                "effective_sha256": digest(reader.binding),
                "inherited_explicit_startup_execute_calls": 17,
            }
        )
        return reader

    def close(self):
        for reader in self.readers:
            reader.close()


def audit(reader):
    reader.check()
    names = sorted(set(reader.origin["settings"]) | {"statement_timeout"})
    rows = reader.connection.execute(
        "SELECT name,setting,unit,boot_val,reset_val,source,context,vartype,min_val,max_val "
        "FROM pg_settings WHERE name=ANY(%s) ORDER BY name",
        (names,),
    ).fetchall()
    if [r[0] for r in rows] != names:
        raise RuntimeError("Settings audit incomplete")
    settings = {
        r[0]: dict(
            zip(
                (
                    "value",
                    "unit",
                    "boot_val",
                    "reset_val",
                    "source",
                    "context",
                    "type",
                    "min",
                    "max",
                ),
                r[1:],
            )
        )
        for r in rows
    }
    if {k: v["value"] for k, v in settings.items()} != {
        **reader.binding["settings"],
        "statement_timeout": "30000",
    }:
        raise RuntimeError("Actual session settings leaked")
    reader.check()
    return {
        "reader": reader.identity,
        "mode": reader.mode,
        "origin": reader.origin,
        "effective": reader.binding,
        "settings": settings,
    }
