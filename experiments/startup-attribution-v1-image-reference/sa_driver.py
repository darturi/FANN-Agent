"""Version-pinned nine-hook driver ledger; Python dispatches, never wire packets."""

import ast
import contextlib
import contextvars
import functools
import hashlib
import importlib
import inspect
import re
import time
from collections import Counter
from pathlib import Path

from pc_common import HERE, digest, read

ACTIVE = None
API = contextvars.ContextVar("sa_api", default=None)
HELPER = contextvars.ContextVar("sa_helper", default=None)
CATALOG = read(HERE / "DRIVER-HOOKS.json")["hooks"]
CAPS = dict(
    api_execution=600,
    verification_fetch=9892,
    verification_close=4,
    transaction_control=32,
    cursor_existence_probe=4,
    deallocate_sql=600,
    prepare=600,
    portal_describe=4,
    prepared_close=600,
)


def bindings(reader=None):
    result = []
    for row in CATALOG:
        module, cls, name = row["qualified_name"].rsplit(".", 2)
        owner = getattr(importlib.import_module(module), cls)
        original = getattr(owner, name)
        if inspect.isgeneratorfunction(original) != (row["kind"] == "generator"):
            raise RuntimeError("Driver callable kind changed")
        path = Path(inspect.getsourcefile(original))
        text = reader(path) if reader else path.read_text()
        nodes = [
            n
            for n in ast.walk(ast.parse(text))
            if isinstance(n, ast.FunctionDef)
            and n.name == name
            and n.lineno == original.__code__.co_firstlineno
        ]
        if len(nodes) != 1:
            raise RuntimeError("Driver source/code mapping differs")
        node = nodes[0]
        function_text = "".join(text.splitlines(keepends=True)[node.lineno - 1 : node.end_lineno])
        result.append(
            (
                owner,
                name,
                original,
                dict(
                    qualified_name=row["qualified_name"],
                    kind=row["kind"],
                    signature=str(inspect.signature(original)),
                    file=path.name,
                    file_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    function_sha256=hashlib.sha256(function_text.encode()).hexdigest(),
                ),
            )
        )
    return result


def query_parser_provenance(reader=None):
    from psycopg._queries import _query2pg_nocache

    fn = _query2pg_nocache
    path = Path(inspect.getsourcefile(fn))
    text = reader(path) if reader else path.read_text()
    node = next(
        n
        for n in ast.walk(ast.parse(text))
        if isinstance(n, ast.FunctionDef)
        and n.name == fn.__name__
        and n.lineno == fn.__code__.co_firstlineno
    )
    body = "".join(text.splitlines(keepends=True)[node.lineno - 1 : node.end_lineno])
    return dict(
        qualified_name=fn.__module__ + "." + fn.__qualname__,
        signature=str(inspect.signature(fn)),
        file=path.name,
        file_sha256=hashlib.sha256(text.encode()).hexdigest(),
        function_sha256=hashlib.sha256(body.encode()).hexdigest(),
        scope="uncached pure template validation; no parameter dumping or cache priming",
    )


def provenance(reader=None):
    import platform
    import sys

    import numpy
    import psycopg
    import pyarrow
    from psycopg import pq

    return dict(
        python=platform.python_version(),
        implementation=sys.implementation.name,
        psycopg=psycopg.__version__,
        numpy=numpy.__version__,
        pyarrow=pyarrow.__version__,
        libpq_version=pq.version(),
        libpq_implementation=pq.__impl__,
        hooks=[v for *_, v in bindings(reader)],
        query_parser=query_parser_provenance(reader),
    )


class Driver:
    def __init__(self, obs, reference=None, sockets=None):
        self.obs = obs
        self.sockets = sockets or {c: "/run/" + c + "/socket" for c in ("native640", "partial640")}
        self.routes = Counter()
        self.reference = reference or read(HERE / "IMAGE-REFERENCE.json")
        self.originals = []
        self.connections = {}  # bounded owned original connection references, no rows
        self.admissions = 0
        self.pending_connect = False
        self.current_pass = None
        self.passes = {}
        self.counts = Counter()
        self.pending = {}
        self.attempts = 0
        self.api_attempts = self.api_completed = 0
        self.monitor = None
        self.installed = False
        self.invalid = []
        self.cleanup_used = 0

    def install(self):
        global ACTIVE
        if ACTIVE is not None:
            raise RuntimeError("Driver already active")
        actual = provenance(self.obs.read_file)
        self.capability = actual
        for k in (
            "python",
            "implementation",
            "psycopg",
            "numpy",
            "pyarrow",
            "hooks",
            "query_parser",
        ):
            if actual[k] != self.reference[k]:
                raise RuntimeError("Driver/runtime provenance mismatch: " + k)
        # libpq may expose different cleanup routes; freeze the actual capability too.
        for k in ("libpq_version", "libpq_implementation"):
            if actual[k] != self.reference[k]:
                raise RuntimeError("libpq capability mismatch: " + k)
        try:
            for owner, name, original, info in bindings(self.obs.read_file):
                wrapper = self.wrap(name, original, info["kind"])
                self.originals.append((owner, name, original, wrapper))
                setattr(owner, name, wrapper)
            wrapper_sha = hashlib.sha256(self.obs.read_file(Path(__file__)).encode()).hexdigest()
            self.binding_proof = [
                dict(
                    owner=owner.__module__ + "." + owner.__qualname__,
                    name=name,
                    original_module=original.__module__,
                    original_qualname=original.__qualname__,
                    wrapper_source_sha256=wrapper_sha,
                    wrapper_code_qualname=wrapper.__code__.co_qualname,
                    original_link_intact=wrapper.__wrapped__ is original,
                    binding_active=getattr(owner, name) is wrapper,
                )
                for owner, name, original, wrapper in self.originals
            ]
            ACTIVE = self
            self.installed = True
        except BaseException:
            self.restore()
            raise
        return self

    def restore(self):
        global ACTIVE
        changed = []
        for owner, name, original, wrapper in reversed(self.originals):
            if getattr(owner, name) is not wrapper:
                changed.append(name)
            setattr(owner, name, original)
        self.originals.clear()
        self.installed = False
        if ACTIVE is self:
            ACTIVE = None
        if changed:
            raise RuntimeError("Driver binding changed: " + str(changed))

    @contextlib.contextmanager
    def connect(self, dsn=None):
        if dsn is not None:
            from psycopg.conninfo import conninfo_to_dict

            cfg = conninfo_to_dict(dsn)
            matches = [c for c, path in self.sockets.items() if cfg.get("host") == path]
            if (
                len(matches) != 1
                or cfg.get("dbname") != "torch_reviews"
                or cfg.get("port") != "5432"
                or cfg.get("user") not in ("torch_owner", "torch_reader")
                or cfg.get("require_auth") != "scram-sha-256"
                or cfg.get("connect_timeout") != "10"
                or set(cfg)
                != {"host", "port", "dbname", "user", "passfile", "require_auth", "connect_timeout"}
            ):
                raise RuntimeError("Connection outside exact two owned sockets/roles")
            cell, user = matches[0], cfg["user"]
            expected_pass = str(
                Path(self.sockets[cell]).parent
                / ("admin.pgpass" if user == "torch_owner" else "reader.pgpass")
            )
            if cfg["passfile"] != expected_pass or self.routes[(cell, user)] >= (
                1 if user == "torch_owner" else 5
            ):
                raise RuntimeError("Connection role/source admission ceiling")
            self.routes[(cell, user)] += 1
        if self.pending_connect or self.admissions >= 12:
            raise RuntimeError("Connection admission ceiling/nesting")
        self.pending_connect = True
        try:
            yield
        finally:
            self.pending_connect = False

    def own(self, conn):
        if not self.pending_connect or id(conn) in self.connections:
            raise RuntimeError("Connection outside pending admission")
        live = sum(not c.closed for c in self.connections.values())
        if self.admissions >= 12 or live >= 8:
            raise RuntimeError("Connection admission/live ceiling")
        self.connections[id(conn)] = conn
        self.admissions += 1

    def owned(self, obj):
        conn = getattr(obj, "_conn", obj)
        if id(conn) not in self.connections or self.connections[id(conn)] is not conn:
            raise RuntimeError("Unowned driver connection")
        if getattr(conn, "_pipeline", None):
            raise RuntimeError("Pipeline prohibited")
        return conn

    @contextlib.contextmanager
    def api(self, target, text, params=None):

        from psycopg._queries import _query2pg_nocache

        with self.obs.charge():
            conn = getattr(target, "_conn", target)
            self.owned(conn)
            if API.get() is not None:
                raise RuntimeError("Nested API attempt")
            self.api_attempts += 1
            token = dict(
                id=self.api_attempts,
                connection=id(conn),
                text=text,
                expected_query=(
                    _query2pg_nocache(text.encode(conn.pgconn._encoding), conn.pgconn._encoding)[0]
                    if params is not None
                    else text.encode(conn.pgconn._encoding)
                ),
                statement_sha256=digest(text),
                links=0,
                names=set(),
                finished=False,
            )
            reset = API.set(token)
        try:
            yield
            with self.obs.charge():
                if token["links"] != 1:
                    raise RuntimeError("API requires exactly one execution dispatch")
                token["finished"] = True
                self.api_completed += 1
        finally:
            with self.obs.charge():
                API.reset(reset)

    @contextlib.contextmanager
    def verification(self, phase, cell):
        name = "V." + phase + "." + cell
        if self.current_pass is not None or name in self.passes or len(self.passes) >= 4:
            raise RuntimeError("Verification pass nesting/repetition")
        p = dict(
            name=name,
            fetches=0,
            rows=0,
            full=0,
            tail=0,
            begin=0,
            commit=0,
            rollback=0,
            close=0,
            describe=0,
            cursor=None,
            failed=False,
        )
        self.passes[name] = p
        self.current_pass = p
        try:
            yield
            expected = dict(
                fetches=2473,
                rows=247286,
                full=2472,
                tail=86,
                begin=1,
                commit=1,
                rollback=0,
                close=1,
                describe=1,
            )
            if any(p[k] != n for k, n in expected.items()):
                raise RuntimeError("Verification page/transaction coverage differs")
        except BaseException:
            p["failed"] = True
            raise
        finally:
            p["cursor"] = None
            self.current_pass = None

    def reserve(self, family, api=None, operation=None):
        with self.obs.charge():
            if family not in CAPS or self.counts[family] >= CAPS[family] or self.attempts >= 12936:
                raise RuntimeError("Driver dispatch family/envelope ceiling")
            self.counts[family] += 1
            self.attempts += 1
            ident = self.attempts
            self.pending[ident] = dict(
                id=ident,
                family=family,
                api=api,
                operation=operation,
                pass_id=(self.current_pass or {}).get("name"),
                reserved_ns=time.monotonic_ns(),
                statement_sha256=(API.get() or {}).get("statement_sha256"),
            )
            return ident

    def complete(self, ident, start, error=None, rows=None):
        with self.obs.charge():
            row = self.pending[ident]
            self.obs.record(
                "command",
                dict(
                    event="dispatch",
                    **row,
                    start_ns=start,
                    end_ns=time.monotonic_ns(),
                    error=error,
                    rows=rows,
                ),
            )
            del self.pending[ident]

    def text(self, value, conn):
        if hasattr(value, "as_bytes"):
            value = value.as_bytes(conn)
        if isinstance(value, bytes):
            value = value.decode("utf8")
        if not isinstance(value, str) or len(value) > 16384:
            raise RuntimeError("Unknown command encoding")
        return value

    def classify(self, name, obj, args):
        conn = self.owned(obj)
        token, p = API.get(), self.current_pass
        if name in ("_execute_send", "_send_query_prepared", "_send_prepare"):
            if token is None or token["connection"] != id(conn):
                raise RuntimeError("Cursor dispatch outside API capability")
            pgq = args[1] if name in ("_send_prepare", "_send_query_prepared") else args[0]
            query = self.text(pgq.query, conn)
            expected = token["text"]
            # Server cursor generates this exact DECLARE around the existing DATA API.
            if p and name == "_execute_send" and expected == __import__("pc_trace").DATA_SQL:
                valid = query == 'DECLARE "b2f_verify_bits" CURSOR FOR ' + expected
            else:
                # The real driver doesn't publish cursor._query until _execute_send.
                # Validate exact converted template bytes, never mutable cursor state.
                valid = pgq.query == token["expected_query"]
            if not valid:
                raise RuntimeError("Execution template changed")
            if name == "_send_prepare":
                statement = args[0]
                names = self.names(conn)
                if (
                    not isinstance(statement, bytes)
                    or not re.fullmatch(rb"_pg3_[0-9]+", statement)
                    or len(names) >= 600
                ):
                    raise RuntimeError("Prepared name registry ceiling/template")
                names.add(statement)
                return "prepare"
            if name == "_send_query_prepared" and args[0] not in self.names(conn):
                raise RuntimeError("Unowned prepared name")
            token["links"] += 1
            if token["links"] > 1:
                raise RuntimeError("Duplicate API execution")
            return "api_execution"
        if name == "_describe_gen":
            self.cursor(obj)
            p["describe"] += 1
            return "portal_describe"
        if name == "_exec_command":
            text = self.text(args[0], conn)
            if p and text in ("BEGIN", "COMMIT", "ROLLBACK"):
                key = text.lower()
                if text == "ROLLBACK" and not (p["failed"] or __import__("sys").exc_info()[0]):
                    raise RuntimeError("Rollback outside failure cleanup")
                p[key] += 1
                if p[key] > 1:
                    raise RuntimeError("Repeated transaction command")
                return "transaction_control"
            if (
                p
                and text == 'FETCH FORWARD 100 FROM "b2f_verify_bits"'
                and HELPER.get() == "_fetch_gen"
            ):
                return "verification_fetch"
            if p and text == 'CLOSE "b2f_verify_bits"':
                p["close"] += 1
                return "verification_close"
            if (
                p
                and p["failed"]
                and text == "SELECT 1 FROM pg_catalog.pg_cursors WHERE name = 'b2f_verify_bits'"
            ):
                return "cursor_existence_probe"
            if text.startswith("DEALLOCATE ") and HELPER.get() == "_deallocate":
                return "deallocate_sql"
            raise RuntimeError("Unknown/internal SQL blocked before dispatch")
        if name == "_deallocate":
            from psycopg._connection_base import _HAS_SEND_CLOSE

            statement = args[0]
            if statement is None or statement not in self.names(conn):
                raise RuntimeError("Unowned deallocation")
            return "prepared_close" if _HAS_SEND_CLOSE else None
        return None

    def names(self, conn):
        if not hasattr(self, "prepared"):
            self.prepared = {}
        return self.prepared.setdefault(id(conn), set())

    def cursor(self, obj):
        p = self.current_pass
        if not p or obj._name != "b2f_verify_bits" or obj.itersize != 100:
            raise RuntimeError("Unknown server cursor/name/size")
        if p["cursor"] is None:
            p["cursor"] = id(obj)
        if p["cursor"] != id(obj):
            raise RuntimeError("Verification cursor changed")

    def enter(self, name, obj, args):
        self.obs.callback()
        if name in ("_declare_gen", "_fetch_gen"):
            self.owned(obj)
            self.cursor(obj)
            if name == "_fetch_gen" and (args != (100,) or self.current_pass["fetches"] >= 2473):
                raise RuntimeError("Unknown/extra FETCH")
            return None
        return self.classify(name, obj, args)

    def safe_teardown(self, name, obj, args):
        try:
            conn = self.owned(obj)
            if name == "_exec_command" and self.current_pass:
                return self.text(args[0], conn) in ("ROLLBACK", 'CLOSE "b2f_verify_bits"')
            if name == "_deallocate":
                return args[0] is not None and args[0] in self.names(conn)
        except BaseException:
            return False
        return False

    def wrap(self, name, original, kind):
        if kind == "normal":

            @functools.wraps(original)
            def normal(obj, *args, **kwargs):
                if name == "_close":
                    observer_error = None
                    try:
                        with self.obs.charge():
                            self.obs.callback()
                    except BaseException as exc:
                        observer_error = exc
                        self.invalid.append(type(exc).__name__)
                    try:
                        if self.monitor and self.monitor.active and observer_error is None:
                            result = self.monitor.cursor_close(obj, original, *args, **kwargs)
                        else:
                            result = original(obj, *args, **kwargs)
                        if observer_error:
                            raise observer_error
                        return result
                    finally:
                        with self.obs.charge():
                            self.obs.callback()
                with self.obs.charge():
                    family = self.enter(name, obj, args)
                    ident = (
                        self.reserve(
                            family,
                            (API.get() or {}).get("id"),
                            operation=(
                                self.text(args[0], self.owned(obj)).split()[0]
                                if name == "_exec_command"
                                else name
                            ),
                        )
                        if family
                        else None
                    )
                start = time.monotonic_ns()
                error = None
                try:
                    return original(obj, *args, **kwargs)
                except BaseException as exc:
                    error = type(exc).__name__
                    raise
                finally:
                    self.obs.callback()
                    if ident:
                        self.complete(ident, start, error)

            return normal

        @functools.wraps(original)
        def generator(obj, *args, **kwargs):
            error, ident, returned_rows, family = None, None, None, None
            # Establish the helper scope across yield/send/throw/close using yield from.
            reset = HELPER.set(name) if name in ("_fetch_gen", "_deallocate") else None
            start = time.monotonic_ns()
            try:
                observer_error = None
                try:
                    with self.obs.charge():
                        family = self.enter(name, obj, args)
                        ident = (
                            self.reserve(
                                family,
                                (API.get() or {}).get("id"),
                                operation=(
                                    self.text(args[0], self.owned(obj)).split()[0]
                                    if name == "_exec_command"
                                    else name
                                ),
                            )
                            if family
                            else None
                        )
                except BaseException as exc:
                    if not self.safe_teardown(name, obj, args) or self.cleanup_used >= 64:
                        raise
                    self.cleanup_used += 1
                    observer_error = exc
                    self.invalid.append(type(exc).__name__)
                    self.obs.invalid.append("minimal teardown lane used")
                start = time.monotonic_ns()
                try:
                    result = yield from original(obj, *args, **kwargs)
                except BaseException as exc:
                    if observer_error:
                        raise BaseExceptionGroup(
                            "Observer and original cleanup errors", [observer_error, exc]
                        )
                    raise
                if name == "_exec_command" and family == "verification_fetch":
                    returned_rows = result.ntuples
                if observer_error:
                    raise observer_error
                if name == "_fetch_gen":
                    with self.obs.charge():
                        p = self.current_pass
                        count = len(result)  # don't copy/retain rows
                        p["fetches"] += 1
                        p["rows"] += count
                        if count == 100:
                            p["full"] += 1
                        else:
                            p["tail"] = count
                        if p["fetches"] in (1, 1237, 2473):
                            self.obs.checkpoint(p["name"] + ".fetch_return." + str(p["fetches"]))
                return result
            except BaseException as exc:
                error = type(exc).__name__
                if self.current_pass:
                    self.current_pass["failed"] = True
                raise
            finally:
                if reset is not None:
                    HELPER.reset(reset)
                with self.obs.charge():
                    self.obs.callback()
                    if ident:
                        self.complete(ident, start, error, returned_rows)

        return generator

    def finish(self):
        if (
            self.pending
            or self.invalid
            or self.admissions != 12
            or any(not c.closed for c in self.connections.values())
        ):
            raise RuntimeError("Incomplete driver/connection accounting")
        if (
            self.api_completed != self.api_attempts
            or self.counts["api_execution"] != self.api_attempts
        ):
            raise RuntimeError("Incomplete API/dispatch linking")
        if len(self.passes) != 4 or self.counts["verification_fetch"] != 9892:
            raise RuntimeError("Incomplete verification accounting")
        return dict(
            attempts=self.attempts,
            api_attempts=self.api_attempts,
            bindings_restored=not self.installed and ACTIVE is None,
            counts=dict(self.counts),
            pending=0,
            admissions=self.admissions,
            passes=self.passes,
            meaning="observed Python-driver dispatches, not network packets",
        )
