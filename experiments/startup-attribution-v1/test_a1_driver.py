"""Actual Psycopg methods with a synthetic send/result transport, no connection."""

import contextlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import sa_driver as D
from pc_trace import DATA_SQL
from psycopg import pq
from psycopg._connection_base import BaseConnection
from psycopg._server_cursor_base import ServerCursorMixin
from sa_observe import Observation


def finish(gen):
    while True:
        try:
            gen.send(None)
        except StopIteration as end:
            return end.value


class PGconn:
    status = pq.ConnStatus.OK
    transaction_status = pq.TransactionStatus.INTRANS
    _encoding = "utf-8"

    def __init__(self):
        self.sent = []
        self.next_rows = 0

    def send_query(self, text):
        self.sent.append(("query", text))

    def send_query_params(self, text, params, **kwargs):
        self.sent.append(("params", text))

    def send_prepare(self, name, query, **kwargs):
        self.sent.append(("prepare", name))

    def send_query_prepared(self, name, *args, **kwargs):
        self.sent.append(("prepared", name))

    def send_describe_portal(self, name):
        self.sent.append(("describe", name))

    def send_close_prepared(self, name):
        self.sent.append(("close_prepared", name))


class Conn(BaseConnection):
    def __init__(self):
        super().__init__(PGconn())

    def close(self):
        self.pgconn.status = pq.ConnStatus.BAD


def render(query):
    """Render only fixed synthetic Composable tokens; no real escaping/connection."""
    from psycopg import sql

    if isinstance(query, str):
        return query
    if isinstance(query, bytes):
        return query.decode()
    if isinstance(query, sql.Composed):
        return "".join(render(v) for v in query._obj)
    if isinstance(query, sql.SQL):
        return query._obj
    if isinstance(query, sql.Identifier):
        return ".".join('"' + v.replace('"', '""') + '"' for v in query._obj)
    if isinstance(query, sql.Literal):
        return str(query._obj) if isinstance(query._obj, int) else "'" + query._obj + "'"
    raise AssertionError(type(query))


def execute(pg):
    if False:
        yield
    return [
        SimpleNamespace(
            status=pq.ExecStatus.COMMAND_OK,
            ntuples=pg.next_rows,
            command_status=b"SELECT 1",
            command_tuples=1,
        )
    ]


class Page:
    """Metadata-only page for full-count ledger checks; holds no generated rows."""

    def __init__(self, count):
        self.count = count

    def __len__(self):
        return self.count


class Cursor(ServerCursorMixin):
    def __init__(self, conn):
        self._conn = conn
        self._pgconn = conn.pgconn
        self._closed = False
        self._query = None
        self._name = "b2f_verify_bits"
        self._described = True
        self._scrollable = None
        self._withhold = False
        self.itersize = 100
        self.format = self._format = pq.Format.TEXT
        self._tx = SimpleNamespace(
            set_pgresult=lambda *a, **k: None, load_rows=lambda a, n, fn: Page(n)
        )
        self._make_row = None
        super()._reset()

    def _start_query(self, *args):
        if False:
            yield

    def _convert_query(self, query, params=None):
        pgq = SimpleNamespace(query=render(query).encode(), params=params, types=(), formats=())
        if params is not None:
            from psycopg._queries import _query2pg_nocache

            pgq.query = _query2pg_nocache(pgq.query, "utf-8")[0]
        return pgq

    def _check_results(self, result):
        pass

    def _select_current_result(self, *args, **kwargs):
        pass

    def _reset(self, **kwargs):
        pass


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.obs = Observation(self.tmp.name, "runtime", lambda o: {"fixture": True})
        self.addCleanup(lambda: self.obs.finish(False))
        self.driver = D.Driver(self.obs).install()
        self.addCleanup(self.driver.restore)
        self.conn = Conn()
        self.addCleanup(self.conn.close)
        with self.driver.connect():
            self.driver.own(self.conn)
        self.cursor = Cursor(self.conn)
        self.addCleanup(lambda: setattr(self.cursor, "_closed", True))
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch("psycopg.generators.execute", execute))
        self.stack.enter_context(patch("psycopg._server_cursor_base.execute", execute))
        self.stack.enter_context(patch("psycopg._cursor_base.execute", execute))
        self.stack.enter_context(patch.object(D.Driver, "text", lambda s, q, c: render(q)))
        self.stack.enter_context(
            patch("psycopg.sql.Composed.as_bytes", lambda q, context=None: render(q).encode())
        )

    def pass_state(self):
        p = dict(
            name="V.initial.native640",
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
        self.driver.current_pass = p
        return p

    def test_actual_unprepared_send(self):
        q = self.cursor._convert_query("SELECT pg_backend_pid()")
        with self.driver.api(self.cursor, q.query.decode()):
            self.cursor._execute_send(q)
        self.assertEqual(self.driver.counts["api_execution"], 1)
        self.assertEqual(self.conn.pgconn.sent[-1], ("query", q.query))

    def test_actual_prepared_send(self):
        q = self.cursor._convert_query("SELECT pg_backend_pid()")
        with self.driver.api(self.cursor, q.query.decode()):
            self.cursor._send_prepare(b"_pg3_0", q)
            self.cursor._send_query_prepared(b"_pg3_0", q)
        self.assertEqual(self.driver.counts, dict(prepare=1, api_execution=1))

    def test_actual_declare_and_describe_once(self):
        self.pass_state()
        self.cursor._described = False
        with self.driver.api(self.cursor, DATA_SQL):
            finish(self.cursor._declare_gen(DATA_SQL))
        self.assertEqual(self.driver.counts, dict(api_execution=1, portal_describe=1))
        self.assertEqual(len(self.conn.pgconn.sent), 2)

    def test_actual_2473_fetches_no_extra_page(self):
        p = self.pass_state()
        for i in range(2473):
            self.conn.pgconn.next_rows = 100 if i < 2472 else 86
            page = finish(self.cursor._fetch_gen(100))
            self.assertEqual(len(page), self.conn.pgconn.next_rows)
        self.assertEqual((p["fetches"], p["full"], p["tail"], p["rows"]), (2473, 2472, 86, 247286))
        before = len(self.conn.pgconn.sent)
        with self.assertRaises(RuntimeError):
            finish(self.cursor._fetch_gen(100))
        self.assertEqual(len(self.conn.pgconn.sent), before)

    def test_actual_begin_commit_close(self):
        self.pass_state()
        finish(self.conn._exec_command(b"BEGIN"))
        finish(self.cursor._close_gen())
        finish(self.conn._exec_command(b"COMMIT"))
        self.assertEqual(self.driver.counts, dict(transaction_control=2, verification_close=1))

    def test_actual_protocol_deallocation(self):
        self.driver.names(self.conn).add(b"_pg3_1")
        finish(self.conn._deallocate(b"_pg3_1"))
        self.assertEqual(self.driver.counts["prepared_close"], 1)
        self.assertEqual(self.driver.counts["deallocate_sql"], 0)

    def test_actual_sql_deallocation_fallback(self):
        self.driver.names(self.conn).add(b"_pg3_1")
        with patch("psycopg._connection_base._HAS_SEND_CLOSE", False):
            finish(self.conn._deallocate(b"_pg3_1"))
        self.assertEqual(self.driver.counts["prepared_close"], 0)
        self.assertEqual(self.driver.counts["deallocate_sql"], 1)

    def test_no_deallocate_all(self):
        with self.assertRaises(RuntimeError):
            finish(self.conn._deallocate(None))
        self.assertEqual(self.conn.pgconn.sent, [])

    def test_unknown_internal_sql_before_dispatch(self):
        for text in (b"SELECT 1", b"SAVEPOINT x", b"COPY reviews TO STDOUT", b"EXPLAIN SELECT 1"):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                finish(self.conn._exec_command(text))
        self.assertEqual(self.conn.pgconn.sent, [])

    def test_unowned_connection_rejected(self):
        conn = Conn()
        try:
            with self.assertRaises(RuntimeError):
                finish(conn._exec_command(b"BEGIN"))
        finally:
            conn.close()

    def test_pipeline_rejected(self):
        self.conn._pipeline = object()
        self.pass_state()
        with self.assertRaises(RuntimeError):
            finish(self.conn._exec_command(b"BEGIN"))
        self.conn._pipeline = None

    def test_fetch_wrong_size_rejected(self):
        self.pass_state()
        with self.assertRaises(RuntimeError):
            finish(self.cursor._fetch_gen(101))

    def test_fetch_wrong_name_rejected(self):
        self.pass_state()
        self.cursor._name = "other"
        with self.assertRaises(RuntimeError):
            finish(self.cursor._fetch_gen(100))

    def test_api_without_dispatch_rejected(self):
        with (
            self.assertRaises(RuntimeError),
            self.driver.api(self.cursor, "SELECT pg_backend_pid()"),
        ):
            pass

    def test_api_double_dispatch_rejected(self):
        q = self.cursor._convert_query("SELECT pg_backend_pid()")
        with self.assertRaises(RuntimeError), self.driver.api(self.cursor, q.query.decode()):
            self.cursor._execute_send(q)
            self.cursor._execute_send(q)
        self.assertEqual(len(self.conn.pgconn.sent), 1)

    def test_close_observer_failure_still_delegates(self):
        self.pass_state()
        with patch.object(self.driver, "reserve", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                finish(self.cursor._close_gen())
        self.assertEqual(self.conn.pgconn.sent, [("query", b'CLOSE "b2f_verify_bits"')])
        self.assertTrue(self.driver.invalid)

    def test_rollback_observer_failure_still_delegates(self):
        self.pass_state()["failed"] = True
        with patch.object(self.driver, "reserve", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                finish(self.conn._exec_command(b"ROLLBACK"))
        self.assertEqual(self.conn.pgconn.sent, [("query", b"ROLLBACK")])

    def test_generator_send_throw_close_return_preserved(self):
        events = []

        def original(obj):
            try:
                value = yield "ready"
                events.append(value)
                try:
                    yield "second"
                except ValueError:
                    events.append("throw")
                return 71
            finally:
                events.append("closed")

        wrapped = self.driver.wrap("_deallocate", original, "generator")
        with patch.object(self.driver, "enter", return_value=None):
            g = wrapped(self.conn)
            self.assertEqual(next(g), "ready")
            self.assertEqual(g.send(5), "second")
            with self.assertRaises(StopIteration) as end:
                g.throw(ValueError())
            self.assertEqual(end.exception.value, 71)
            self.assertEqual(events, [5, "throw", "closed"])
            g = wrapped(self.conn)
            next(g)
            g.close()
            self.assertEqual(events[-1], "closed")

    def test_bindings_restored(self):
        originals = [(o, n, f) for o, n, f, _ in self.driver.originals]
        self.driver.restore()
        self.assertTrue(all(getattr(o, n) is f for o, n, f in originals))
        self.assertIsNone(D.ACTIVE)

    def test_observer_and_original_cleanup_errors_both_preserved(self):
        self.pass_state()
        with patch.object(self.driver, "reserve", side_effect=OSError("observer")):
            with patch.object(self.conn.pgconn, "send_query", side_effect=ValueError("transport")):
                with self.assertRaises(BaseExceptionGroup) as group:
                    finish(self.cursor._close_gen())
        self.assertEqual([type(e) for e in group.exception.exceptions], [OSError, ValueError])

    def test_wrong_socket_rejected_before_connect(self):
        with (
            self.assertRaises(RuntimeError),
            self.driver.connect("host=other dbname=torch_reviews"),
        ):
            self.fail("admitted unknown socket")

    def actual_parameterized(self, prepare):
        from types import MethodType

        from pc_trace import SET_SQL
        from psycopg._cursor_base import BaseCursor
        from psycopg._queries import PostgresQuery
        from psycopg.adapt import Transformer

        self.cursor._tx = Transformer()
        self.cursor._query_cls = PostgresQuery
        self.cursor._convert_query = MethodType(BaseCursor._convert_query, self.cursor)
        self.cursor._query = None
        params = ("hnsw.ef_search", "640", False)
        # This is the original converter: it must NOT publish _query before send.
        q = self.cursor._convert_query(SET_SQL, params)
        self.assertIsNone(self.cursor._query)
        self.assertEqual(q.query, b"SELECT set_config($1,$2,$3)")
        with self.driver.api(self.cursor, SET_SQL, params):
            finish(self.cursor._execute_gen(SET_SQL, params, prepare=prepare))
        self.assertEqual(self.driver.counts["api_execution"], 1)
        self.assertEqual(self.driver.counts["prepare"], int(prepare))

    def test_actual_parameterized_execute_gen_unprepared(self):
        self.actual_parameterized(False)

    def test_actual_parameterized_execute_gen_prepared(self):
        self.actual_parameterized(True)

    def test_poisoned_cursor_query_state_cannot_bypass_template(self):
        from pc_trace import SET_SQL

        q = self.cursor._convert_query("SELECT unknown_source")
        self.cursor._query = q
        with (
            self.assertRaises(RuntimeError),
            self.driver.api(self.cursor, SET_SQL, ("a", "b", False)),
        ):
            self.cursor._execute_send(q)
        self.assertEqual(self.conn.pgconn.sent, [])
