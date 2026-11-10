"""Owned experimental readers; public target validation and native code untouched."""

import copy
import time

from pc_common import MODES, context, effective
from pc_metadata import expected_statement
from pc_trace import category


class FrozenDict(dict):
    def blocked(*args, **kwargs):
        raise TypeError("Privately admitted state is immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = blocked

    def __deepcopy__(self, memo):
        return {copy.deepcopy(k, memo): copy.deepcopy(v, memo) for k, v in self.items()}


class FrozenList(list):
    __setitem__ = __delitem__ = append = clear = extend = insert = pop = remove = reverse = sort = (
        __iadd__
    ) = __imul__ = FrozenDict.blocked

    def __deepcopy__(self, memo):
        return [copy.deepcopy(v, memo) for v in self]


def freeze(v):
    if isinstance(v, dict):
        return FrozenDict({k: freeze(x) for k, x in v.items()})
    if isinstance(v, list):
        return FrozenList([freeze(x) for x in v])
    return v


def bound_class(Base, mode, target):
    if mode not in MODES:
        raise ValueError("Unsupported fixed mode")

    class Backend(Base):
        def __init__(self, bundle, work):
            super().__init__(bundle, work)
            self.state["source_manifest"] = copy.deepcopy(self.state["source_manifest"])
            self.state["source_manifest"]["index"] = copy.deepcopy(target["index"])
            self.state["prepared"]["index_identity"] = target["index_identity"]

        def _settings(self, conn, *, local=True, source=None):
            return super()._settings(
                conn,
                local=local,
                source=effective(self.state["source_manifest"] if source is None else source, mode),
            )

        def _bind(self, conn, source):
            return super()._bind(conn, effective(source, mode))

        def _statement(self, q, *, exact=False):
            context(q)
            if exact and mode != "native640":
                raise RuntimeError("Truth belongs to baseline full-table reader")
            statement, params = super()._statement(q, exact=exact)
            if statement.as_string(self.conn) != expected_statement(q, "native640", exact):
                raise RuntimeError("Inherited SQL shape differs")
            if mode == "partial640" and not exact:
                from psycopg import sql

                statement = sql.SQL(expected_statement(q, mode))
            return statement, params

    return Backend


class OwnedReader:
    def __init__(self, backend, mode, identity, factory):
        self.backend = backend
        self.mode = mode
        self.identity = identity
        self.factory = factory
        self.connection = backend._connect()
        self.closed = False
        backend.state["source_manifest"] = self.origin = freeze(backend.state["source_manifest"])
        backend._binding = self.binding = freeze(backend._binding)
        if self.binding != effective(self.origin, mode):
            raise RuntimeError("Effective binding differs")
        self.check()

    def check(self, q=None):
        b = self.backend
        c = self.connection
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
            raise RuntimeError("Stale/closed/replaced connection or binding; no replay")
        if q is not None:
            context(q)
            if self.factory.requests.get(q["id"]) is not q:
                raise RuntimeError("Request not privately admitted")

    def native(self, q, budget, operation):
        try:
            self.check(q)
            budget.reserve(operation)
            with category("startup", expected_statement(q, self.mode)):
                result = self.backend.execute_probe(q, mode="native")
            self.check(q)
            return result
        except BaseException:
            self.close()
            raise

    def exact(self, q, budget, operation):
        try:
            self.check(q)
            if self.mode != "native640":
                raise RuntimeError("Candidate cannot generate authoritative truth")
            budget.reserve(operation)
            with category("truth_helper", expected_statement(q, "native640", True)):
                result = self.backend.exact_reference(q)
            self.check(q)
            return result
        except BaseException:
            self.close()
            raise

    def close(self):
        self.closed = True
        self.backend.close()


class Factory:
    def __init__(self, Base, bundle, works, targets, observer, budget, emit):
        self.Base = Base
        self.bundle = bundle
        self.works = works
        self.targets = targets
        self.observer = observer
        self.budget = budget
        self.emit = emit
        self.snapshot = None
        self.requests = {}
        self.readers = []
        self.admissions = []
        self.maximum_live = 0
        self.classes = {m: bound_class(Base, m, targets[m]) for m in MODES}
        if works["native640"] == works["partial640"]:
            raise ValueError("Baseline/candidate copies must differ")

    def create(self, mode, role):
        if (
            mode not in MODES
            or len(self.readers) >= 10
            or sum(not r.closed for r in self.readers) >= 6
        ):
            raise RuntimeError("Reader/mode admission ceiling")
        start = time.perf_counter_ns()
        backend = self.classes[mode](self.bundle, self.works[mode])
        if self.snapshot is not None:
            backend._snapshot = self.snapshot
        try:
            r = OwnedReader(backend, mode, role, self)
        except BaseException:
            backend.close()
            raise
        r.observer = self.observer
        self.readers.append(r)
        self.maximum_live = max(self.maximum_live, sum(not r.closed for r in self.readers))
        row = dict(
            reader=role,
            mode=mode,
            copy=mode,
            start_ns=start,
            end_ns=time.perf_counter_ns(),
            origin=r.origin,
            effective=r.binding,
        )
        row["outer_ms"] = (row["end_ns"] - start) / 1e6
        self.admissions.append(row)
        self.emit("admissions", row)
        return r

    def close(self):
        errors = []
        for r in self.readers:
            try:
                r.close()
            except BaseException as e:
                errors.append(str(e))
        if errors:
            raise RuntimeError("Reader cleanup failed: " + repr(errors))


def audit(reader):
    reader.check()
    names = sorted(set(reader.origin["settings"]) | {"statement_timeout"})
    with category("observer"):
        rows = reader.connection.execute(
            "SELECT name,setting,boot_val,source FROM pg_settings WHERE name=ANY(%s) ORDER BY name",
            (names,),
            prepare=False,
        ).fetchall()
    if (
        [r[0] for r in rows] != names
        or {r[0]: r[1] for r in rows}
        != {**reader.binding["settings"], "statement_timeout": "30000"}
        or next(r[2] for r in rows if r[0] == "hnsw.ef_search") != "40"
        or any(r[3] != "session" for r in rows)
    ):
        raise RuntimeError("Session settings/source/boot metadata changed")
    reader.check()
    return dict(reader=reader.identity, mode=reader.mode, values={r[0]: r[1:] for r in rows})
