# ruff: noqa: E402 -- pinned vendor imports follow bootstrap.
"""Synthetic SQL fixtures copied from the immutable B2d local checks; no live services."""

import copy
import re
from contextlib import contextmanager
from types import SimpleNamespace

import experiment
import pc_common as C
import pc_settings as settings
from pc_trace import Connection

C.bootstrap(experiment.SOURCE)
from fannagent_pgvector.backend import NativeBackend
from reference_backend import ExactReferenceMixin

from fannagent.snapshot import Snapshot

SETTINGS = C.read(experiment.SOURCE / "origin-settings.json")
METADATA = C.read(experiment.SOURCE / "origin-source.json")["metadata"]
VECTOR = [1.0] + [0.0] * 767


class Clock:
    value = 10**9

    def now(self):
        self.value += 1000
        return self.value

    def advance(self, ms):
        self.value += int(ms * 1e6)


CLOCK = Clock()


class SqlFailure(Exception):
    sqlstate = "22012"


def catalog(candidate=False, admin=False):
    base = dict(
        server_version_num="170011",
        vector_version="0.8.6",
        relation=dict(oid="264000", relkind="r", relrowsecurity=False),
        columns=[
            dict(attnum=1, attname="id", typname="int8", attnotnull=True, atttypmod=-1),
            dict(attnum=2, attname="embedding", typname="vector", attnotnull=True, atttypmod=768),
            dict(attnum=3, attname="total_votes", typname="int8", attnotnull=True, atttypmod=-1),
        ],
        indexes=[],
        statistics=[dict(attname="id"), dict(attname="total_votes")],
        environment=dict(
            plan_cache_mode="auto", jit="on", max_parallel_workers_per_gather="2", work_mem="16384"
        ),
    )
    if admin:
        base["environment"] = copy.deepcopy(settings.ADMIN_ENVIRONMENT)
    for name, am, oid, keys, ops, unique, primary, bs in [
        ("reviews_pkey", "btree", "264001", ["id"], ["int8_ops"], True, True, 1024),
        (
            "reviews_hnsw",
            "hnsw",
            "264013",
            ["embedding"],
            ["vector_cosine_ops"],
            False,
            False,
            1012678656,
        ),
    ]:
        base["indexes"].append(
            dict(
                oid=oid,
                relname=name,
                amname=am,
                indisvalid=True,
                indisready=True,
                indisunique=unique,
                indisprimary=primary,
                partial=False,
                expression=False,
                indnatts=1,
                indnkeyatts=1,
                keys=keys,
                opclasses=ops,
                bytes=bs,
                reloptions=["m=16", "ef_construction=64"] if am == "hnsw" else None,
                predicate=None,
                filepath="base/16384/" + oid,
                definition="synthetic",
            )
        )
    if candidate:
        i = copy.deepcopy(base["indexes"][-1])
        i.update(
            oid="270000",
            relname=C.INDEX,
            partial=True,
            predicate="(total_votes >= 108)",
            filepath="base/16384/270000",
            bytes=100000,
        )
        base["indexes"].append(i)
    return base


def snapshot():
    return Snapshot(
        [dict(source_id=i, vector=VECTOR, metadata=dict(total_votes=108)) for i in range(40)],
        METADATA,
    )


class FakeConnection:
    def __init__(self, mode):
        self.adapters = __import__("psycopg").adapters
        self.mode = mode
        self.closed = False
        self.autocommit = True
        self.info = SimpleNamespace(transaction_status=0, user="torch_reader")
        self.pgconn = SimpleNamespace(transaction_status=0)
        self.prepare_threshold = 5
        self.prepared_max = 100
        self.values = {}
        self.rows = []
        self.native_calls = 0
        self.native_sql = ""
        self.generic = False
        self.bad_cache = False

    @property
    def connection(self):
        return None

    @contextmanager
    def transaction(self):
        old = self.values.copy()
        try:
            yield
        finally:
            self.values = old

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def cursor(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter(self.rows)

    def execute(self, statement, params=None, prepare=None):
        text = statement.as_string(self) if hasattr(statement, "as_string") else str(statement)
        if "jsonb_build_object" in text:
            self.rows = [(catalog(self.mode == "partial640"),)]
        elif "pg_prepared_statements" in text:
            self.rows = (
                [
                    (
                        "mock_" + self.mode,
                        self.native_sql,
                        "{vector,smallint,vector,smallint}",
                        self.native_calls if self.generic else 0,
                        0 if self.generic else self.native_calls,
                    )
                ]
                if self.native_calls >= 6
                else []
            )
        elif "EXPLAIN" in text:
            self.rows = [
                (
                    [
                        {
                            "Plan": {
                                "Node Type": "Limit",
                                "Plans": [
                                    {
                                        "Node Type": "Index Scan",
                                        "Relation Name": "reviews",
                                        "Index Name": "reviews_hnsw"
                                        if self.mode == "native640" or self.bad_cache
                                        else C.INDEX,
                                    }
                                ],
                            }
                        }
                    ],
                )
            ]
            if "LIMIT" not in text and "EXECUTE" not in text:
                self.rows = [([{"Plan": {"Node Type": "Seq Scan", "Relation Name": "reviews"}}],)]
        elif "set_config" in text:
            args = re.search(r"set_config\((%s|'[^']*'),\s*(%s|'[^']*')", text).groups()
            it = iter(params or [])
            name, value = [next(it) if a == "%s" else a.strip("'") for a in args]
            self.values[name] = value
            self.rows = [(value,)]
        elif "FROM pg_settings" in text:
            self.rows = [
                (n, self.values[n], "40" if n == "hnsw.ef_search" else self.values[n], "session")
                for n in sorted(params[0])
            ]
        elif "1/0" in text:
            raise SqlFailure()
        elif "bind_target" in text:
            self.rows = [(270000 if self.mode == "partial640" else 264013,)]
        elif "current_database" in text:
            self.rows = [("torch_reviews", "torch_reader", None, False, False)]
        elif text == "SELECT 1":
            self.rows = [(1,)]
        elif text.startswith('SELECT "id", "embedding" <=>'):
            exact = " LIMIT " not in text
            ids = list(range(40 if exact else 10))
            if not exact:
                self.native_calls += 1
                count = iter(range(1, 5))
                self.native_sql = re.sub("%s", lambda m: "$" + str(next(count)), text)
                if self.mode == "partial640" and FakeBase.behavior == "quality":
                    ids[-1] = 10
            self.rows = [(i, i / 20) for i in ids]
            CLOCK.advance(
                1
                if exact
                else (12 if FakeBase.behavior == "futility" else 4)
                if self.mode == "partial640"
                else 5
            )
        else:
            raise AssertionError("Unexpected SQL: " + text[:140])
        return self

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


class FakeBase(ExactReferenceMixin):
    trace = None
    behavior = "good"
    fail = False

    def __init__(self, bundle, work):
        self.work = work
        self.state = dict(
            source_manifest=dict(
                settings=copy.deepcopy(SETTINGS),
                metadata=copy.deepcopy(METADATA),
                index=dict(oid=264013, relname="reviews_hnsw"),
            ),
            prepared=dict(index_identity="original"),
        )
        self.target = SimpleNamespace(
            schema_name="public", resource="reviews", id_column="id", vector_column="embedding"
        )
        self.config = SimpleNamespace(query_timeout_seconds=30)
        self._snapshot = snapshot()
        self.conn = self._binding = self._binding_conn = None

    relation = NativeBackend.relation
    _statement = NativeBackend._statement
    _settings = NativeBackend._settings

    def snapshot(self):
        return self._snapshot

    def _connect(self):
        if self.conn is None or self.conn.closed:
            self.close()
            mode = (
                "partial640"
                if self.state["source_manifest"]["index"]["relname"] == C.INDEX
                else "native640"
            )
            self.conn = Connection(FakeConnection(mode), self.trace)
            self.conn.execute("SELECT current_database()")
            self._bind(self.conn, self.state["source_manifest"])
        return self.conn

    def _bind(self, conn, source):
        conn.execute("SELECT fannagent.bind_target()")
        self._settings(conn, local=False, source=source)
        self._binding = copy.deepcopy(source)
        self._binding_conn = conn

    def close(self):
        if self.conn:
            self.conn.close()
        self.conn = self._binding = self._binding_conn = None

    def execute_probe(self, q, *, mode):
        if self.fail:
            raise RuntimeError("synthetic native failure")
        assert mode == "native"
        statement, params = self._statement(q)
        start = CLOCK.now()
        rows = self._connect().execute(statement, params).fetchall()
        end = CLOCK.now()
        return SimpleNamespace(
            ids=[r[0] for r in rows],
            distances=[r[1] for r in rows],
            latency_ms=(end - start) / 1e6,
            metadata={},
            evidence=None,
        )

    def exact_reference(self, q):
        return self._exact_reference(q)
