"""Count explicit nonsearch execute calls without altering driver/SQL preparation."""

import contextlib
import contextvars
import time

from pc_common import digest

CATEGORY = contextvars.ContextVar("pc_sql_category", default="startup")
SEARCH = contextvars.ContextVar("pc_expected_search", default=None)


@contextlib.contextmanager
def category(name, expected_search=None):
    a = CATEGORY.set(name)
    b = SEARCH.set(expected_search)
    try:
        yield
    finally:
        SEARCH.reset(b)
        CATEGORY.reset(a)


class Cursor:
    def __init__(self, raw, trace):
        self.raw = raw
        self.trace = trace

    def __getattr__(self, key):
        return getattr(self.raw, key)

    def __iter__(self):
        return iter(self.raw)

    def __enter__(self):
        self.raw.__enter__()
        return self

    def __exit__(self, *args):
        return self.raw.__exit__(*args)

    def execute(self, statement, params=None, **kwargs):
        self.trace.call(self.raw, statement, params, kwargs)
        return self


class Connection:
    def __init__(self, raw, trace):
        self.raw = raw
        self.trace = trace

    def __getattr__(self, key):
        return getattr(self.raw, key)

    @property
    def connection(self):
        return self.raw.connection

    def __enter__(self):
        self.raw.__enter__()
        return self

    def __exit__(self, *args):
        return self.raw.__exit__(*args)

    def execute(self, statement, params=None, **kwargs):
        return self.trace.call(self.raw, statement, params, kwargs)

    def cursor(self, *args, **kwargs):
        return Cursor(self.raw.cursor(*args, **kwargs), self.trace)

    @contextlib.contextmanager
    def transaction(self, *args, **kwargs):
        self.trace.event("transaction_enter")
        try:
            with self.raw.transaction(*args, **kwargs):
                yield
        finally:
            self.trace.event("transaction_exit")


class Trace:
    def __init__(self, budget, emit):
        self.budget = budget
        self.emit = emit
        self.search_sql = 0

    def event(self, kind):
        self.emit("sql", dict(kind=kind, stage=self.budget.stage, time_ns=time.perf_counter_ns()))

    def call(self, target, statement, params, kwargs):
        text = (
            statement.as_string(target.connection)
            if hasattr(statement, "as_string")
            else str(statement)
        )
        expected = SEARCH.get()
        if expected is not None and text == expected:
            self.search_sql += 1
            return target.execute(statement, params, **kwargs)
        kind = CATEGORY.get()
        # Only explicit helper/observer/setup calls use the corresponding SQL cap.
        self.budget.sql_reserve(kind)
        start = time.perf_counter_ns()
        error = None
        try:
            return target.execute(statement, params, **kwargs)
        except BaseException as e:
            error = type(e).__name__
            raise
        finally:
            self.emit(
                "sql",
                dict(
                    category=kind,
                    stage=self.budget.stage,
                    statement_sha256=digest(text),
                    prepare=kwargs.get("prepare"),
                    start_ns=start,
                    end_ns=time.perf_counter_ns(),
                    error=error,
                ),
            )

    def install(self, psycopg):
        original = psycopg.connect

        def connect(*args, **kwargs):
            return Connection(original(*args, **kwargs), self)

        psycopg.connect = connect
        return original
