"""Experimental native-only effort envelope; frozen public API is untouched."""

import copy
import threading

from ef_common import LEVELS, digest

ENVELOPE_VERSION = "native-effort-request.v1"


def context(query):
    """Use actual validated query semantics, never its ID or evaluator label."""
    predicate = query.get("filter")
    if query["k"] != 10:
        return None
    if predicate is None:
        return "unfiltered"
    if (
        isinstance(predicate, dict)
        and set(predicate) == {"field", "op", "value"}
        and predicate["field"] == "m_000000"
        and predicate["op"] == "gte"
        and type(predicate["value"]) is int
        and predicate["value"] in (32, 108)
    ):
        return "votes" + str(predicate["value"])
    return None


def envelope(query, effort):
    return {"version": ENVELOPE_VERSION, "effort": effort, "query": query}


def bound_class(Base, level):
    if type(level) is not int or level not in LEVELS:
        raise ValueError("Effort must be integer320 or640")

    class EffortBackend(Base):
        """Binding view only. SQL/execution/timer methods remain inherited unchanged."""

        def _view(self, source):
            value = copy.deepcopy(source)
            value["settings"]["hnsw.ef_search"] = str(level)
            if value["settings"].get("hnsw.iterative_scan") != "off":
                raise RuntimeError("Iterative scans must remain off")
            return value

        def _settings(self, conn, *, local=True, source=None):
            return super()._settings(
                conn,
                local=local,
                source=self._view(self.state["source_manifest"] if source is None else source),
            )

        def _bind(self, conn, source):
            return super()._bind(conn, self._view(source))

    return EffortBackend


def factory(Base, bundle, work, snapshot):
    classes = {n: bound_class(Base, n) for n in LEVELS}

    def create(level=None):
        reader = (Base if level is None else classes[level])(bundle, work)
        reader._snapshot = snapshot
        create.created += 1
        return reader

    create.created = 0
    return create


class Pool:
    """Two private readers, eager charged admission, no transparent reconnect/retry."""

    def __init__(self, create):
        self._readers, self._connections, self._origins, self._bindings = {}, {}, {}, {}
        self._closed = False
        self._lock = threading.RLock()
        try:
            for level in LEVELS:
                reader = create(level)
                self._readers[level] = reader
                self._origins[level] = copy.deepcopy(reader.state["source_manifest"])
                conn = reader._connect()
                self._connections[level] = conn
                self._bindings[level] = copy.deepcopy(reader._binding)
                expected = copy.deepcopy(self._origins[level])
                expected["settings"]["hnsw.ef_search"] = str(level)
                if reader._binding != expected:
                    raise RuntimeError("Effective binding differs")
            if self._origins[320] != self._origins[640]:
                raise RuntimeError("Readers have different origin manifests")
        except BaseException:
            self.close()
            raise

    def close(self):
        self._closed = True
        for reader in self._readers.values():
            reader.close()

    def _check(self):
        if self._closed:
            raise RuntimeError("Effort session is closed; explicitly create a new session")
        for level, reader in self._readers.items():
            conn = self._connections[level]
            if (
                reader.conn is not conn
                or conn.closed
                or reader._binding_conn is not conn
                or reader._binding != self._bindings[level]
                or reader.state["source_manifest"] != self._origins[level]
            ):
                raise RuntimeError("Effort session connection/binding changed")

    def query(self, request, budget, operation="measurement"):
        with self._lock:
            try:
                self._check()
                if (
                    not isinstance(request, dict)
                    or set(request) != {"version", "effort", "query"}
                    or request["version"] != ENVELOPE_VERSION
                    or type(request["effort"]) is not int
                    or request["effort"] not in LEVELS
                ):
                    raise ValueError("Invalid experimental effort request")
                query = self._readers[640].snapshot().query(request["query"])
                ctx = context(query)
                level = request["effort"] if ctx is not None else 640
                budget.reserve(operation)
                result = self._readers[level].execute_probe(query, mode="native")
                return result, {
                    "requested_effort": request["effort"],
                    "effective_effort": level,
                    "context": ctx,
                    "fallback_to640": ctx is None,
                }
            except BaseException:
                self.close()
                raise

    def audit(self):
        self._check()
        return {
            str(n): {
                "origin": self._origins[n],
                "effective": self._bindings[n],
                "origin_sha256": digest(self._origins[n]),
                "effective_sha256": digest(self._bindings[n]),
                "settings": settings(r),
            }
            for n, r in self._readers.items()
        }


def settings(reader):
    names = sorted(set(reader.state["source_manifest"]["settings"]) | {"statement_timeout"})
    rows = (
        reader._connect()
        .execute(
            "SELECT name,setting,unit,boot_val,reset_val,source,context,vartype,min_val,max_val "
            "FROM pg_settings WHERE name=ANY(%s) ORDER BY name",
            (names,),
        )
        .fetchall()
    )
    if [r[0] for r in rows] != names:
        raise RuntimeError("Declared PostgreSQL setting unavailable")
    result = {
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
    expected = {
        **reader._binding["settings"],
        "statement_timeout": str(int(reader.config.query_timeout_seconds * 1000)),
    }
    if {k: v["value"] for k, v in result.items()} != expected:
        raise RuntimeError("Actual PostgreSQL settings differ from effective binding")
    return result


def session(create, cell):
    if cell in ("wrapped320", "wrapped640"):
        return Pool(create)
    if cell in ("original640", "source"):
        reader = create(640 if cell == "original640" else None)
        try:
            reader._connect()
        except BaseException:
            reader.close()
            raise
        return reader
    raise ValueError("Unknown cell")


def execute(session_, cell, query, budget, operation="measurement"):
    if cell not in ("wrapped320", "wrapped640"):
        raise ValueError("Plain baselines must call inherited execute_probe directly")
    request = envelope(query, 320 if cell == "wrapped320" else 640)
    return session_.query(request, budget, operation)


def audit_session(session_, cell):
    if cell.startswith("wrapped"):
        return session_.audit()
    return {
        "plain": {
            "origin": copy.deepcopy(session_.state["source_manifest"]),
            "effective": copy.deepcopy(session_._binding),
            "settings": settings(session_),
        }
    }
