"""Closed SQL allowlist: reject search/unknown SQL before reaching the driver."""

import contextlib
import contextvars
import time
from collections import Counter

from pc_common import CONTRACT, digest

CATEGORY = contextvars.ContextVar("pc_sql_category", default="startup")
SEARCH = contextvars.ContextVar("pc_expected_search", default=None)
ROLE_SQL = (
    "SELECT current_database(),current_user,inet_server_addr(),"
    "(SELECT rolsuper FROM pg_roles WHERE rolname=current_user),"
    "has_table_privilege(current_user,'public.reviews','INSERT')"
)
SNAPSHOT_SQL = 'SELECT "id","embedding","total_votes" FROM "public"."reviews" ORDER BY "id"'
DATA_SQL = "SELECT id,embedding::text,total_votes FROM public.reviews ORDER BY id"
BIND_SQL = "SELECT fannagent.bind_target(%s::regclass,%s,%s,%s::regclass)"
SET_SQL = "SELECT set_config(%s,%s,%s)"
TIMEOUT_SQL = "SELECT set_config('statement_timeout',%s,%s)"
AUDIT_SQL = "SELECT name,setting,boot_val,source FROM pg_settings WHERE name=ANY(%s) ORDER BY name"
PID_SQL = "SELECT pg_backend_pid(),current_database(),current_user,inet_server_addr()"
READER_CONTEXT_SQL = (
    "SELECT current_setting('plan_cache_mode'),current_setting('default_transaction_read_only')"
)
DIRECTORY_SQL = "SELECT pg_backend_pid(),current_setting('data_directory')"


@contextlib.contextmanager
def category(name, expected_search=None):
    a, b = CATEGORY.set(name), SEARCH.set(expected_search)
    try:
        yield
    finally:
        SEARCH.reset(b)
        CATEGORY.reset(a)


def allowed(text, params):
    from pc_metadata import CATALOG_SQL
    from pc_settings import MEMORY_SQL

    fixed = {
        ROLE_SQL,
        SNAPSHOT_SQL,
        DATA_SQL,
        AUDIT_SQL,
        PID_SQL,
        DIRECTORY_SQL,
        READER_CONTEXT_SQL,
        "SELECT pg_backend_pid()",
        CATALOG_SQL,
        MEMORY_SQL,
    }
    if text in fixed:
        return
    if text == SET_SQL:
        settings = dict(CONTRACT["targets"]["native640"].get("settings", {}))
        # The original settings are pinned by both actual readers and audit();
        # only these known session names are admitted at this SQL boundary.
        from pc_common import HERE, read

        settings = read(HERE / "origin-settings.json")
        settings = settings.get("settings", settings)
        settings = {**settings, "hnsw.ef_search": "640"}
        if (
            params
            and len(params) == 3
            and params[0] in settings
            and str(params[1]) == str(settings[params[0]])
            and params[2] is False
        ):
            return
    if text == TIMEOUT_SQL and tuple(params or ()) == ("30000", False):
        return
    if (
        text == BIND_SQL
        and params
        and len(params) == 4
        and tuple(params[:3]) == ('"public"."reviews"', "id", "embedding")
        and params[3] in ('"public"."reviews_hnsw"', '"public"."reviews_hnsw_votes108_v1"')
    ):
        return
    raise RuntimeError("SQL outside startup-only allowlist; blocked before execution")


class Cursor:
    def __init__(self, raw, trace):
        self.raw, self.trace = raw, trace

    def __getattr__(self, key):
        return getattr(self.raw, key)

    def __iter__(self):
        return iter(self.raw)

    def executemany(self, *args, **kwargs):
        raise RuntimeError("Bulk SQL prohibited")

    def copy(self, *args, **kwargs):
        raise RuntimeError("COPY prohibited")

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
        self.raw, self.trace = raw, trace

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
        self.budget, self.emit = budget, emit
        self.search_sql = self.prohibited = 0
        self.scans = Counter()

    def event(self, kind):
        self.emit("sql", dict(kind=kind, stage=self.budget.stage, time_ns=time.perf_counter_ns()))

    def call(self, target, statement, params, kwargs):
        text = (
            statement.as_string(target.connection)
            if hasattr(statement, "as_string")
            else str(statement)
        )
        try:
            if SEARCH.get() is not None:
                raise RuntimeError("Search reservation prohibited")
            allowed(text, params)
        except BaseException:
            self.prohibited += 1
            self.emit("blocked-sql", dict(statement_sha256=digest(text), stage=self.budget.stage))
            raise
        key = "snapshot" if text == SNAPSHOT_SQL else "data" if text == DATA_SQL else None
        if key:
            if self.scans[key] >= {"snapshot": 1, "data": 4}[key]:
                raise RuntimeError("Full-table scan cap exhausted")
            self.scans[key] += 1
        kind = CATEGORY.get()
        self.budget.sql_reserve(kind)
        start, error = time.monotonic_ns(), None
        try:
            import sa_driver

            if sa_driver.ACTIVE:
                with sa_driver.ACTIVE.api(target, text, params):
                    return target.execute(statement, params, **kwargs)
            return target.execute(statement, params, **kwargs)
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            self.emit(
                "sql",
                dict(
                    category=kind,
                    stage=self.budget.stage,
                    statement=text,
                    statement_sha256=digest(text),
                    parameters=params,
                    prepare=kwargs.get("prepare"),
                    start_ns=start,
                    end_ns=time.monotonic_ns(),
                    error=error,
                ),
            )

    def install(self, psycopg):
        original = psycopg.connect

        def connect(*args, **kwargs):
            import sa_driver

            if sa_driver.ACTIVE:
                with sa_driver.ACTIVE.connect(args[0] if args else kwargs.get("conninfo", "")):
                    raw = original(*args, **kwargs)
                    try:
                        sa_driver.ACTIVE.own(raw)
                    except BaseException:
                        raw.close()
                        raise
                return Connection(raw, self)
            return Connection(original(*args, **kwargs), self)

        psycopg.connect = connect
        return original
