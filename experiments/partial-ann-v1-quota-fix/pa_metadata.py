"""Strict catalogs and actual fresh/cached plans for separate physical targets."""

import copy
import json
import re
import time
from collections import Counter

from legacy_metadata import (
    CACHE_SQL,
    compact_plan,
    diagnostic_charge,
    parameters,
    validate_charge,
)
from legacy_metadata import (
    CATALOG_SQL as OLD_CATALOG_SQL,
)
from legacy_metadata import (
    validate_catalog as full_catalog,
)
from pa_common import INDEX, INDEX_BYTES, context, digest
from pa_trace import category

CATALOG_SQL = OLD_CATALOG_SQL.replace(
    "c.reloptions,pg_relation_size",
    "pg_get_expr(i.indpred,i.indrelid) AS predicate,"
    "pg_relation_filepath(c.oid) AS filepath,c.reloptions,pg_relation_size",
)


def expected_statement(q, mode="native640", exact=False):
    context(q)
    return (
        'SELECT "id", "embedding" <=> %s::vector AS distance FROM "public"."reviews" WHERE '
        '"total_votes" >= %s'
        + (' AND "total_votes" >= 108' if mode == "partial640" and not exact else "")
        + ' ORDER BY "embedding" <=> %s::vector'
        + ("" if exact else " LIMIT %s")
    )


def validate_catalog(value, candidate=False):
    names = [i["relname"] for i in value["indexes"]]
    expected = {"reviews_pkey", "reviews_hnsw"} | ({INDEX} if candidate else set())
    if len(names) != len(expected) or set(names) != expected:
        raise ValueError("Unexpected complete index catalog")
    baseline = copy.deepcopy(value)
    baseline["indexes"] = [i for i in baseline["indexes"] if i["relname"] != INDEX]
    full_catalog(baseline)
    if any(i.get("predicate") is not None for i in baseline["indexes"]):
        raise ValueError("Original predicate changed")
    if not candidate:
        return
    i = next(i for i in value["indexes"] if i["relname"] == INDEX)
    wanted = dict(
        amname="hnsw",
        keys=["embedding"],
        opclasses=["vector_cosine_ops"],
        indisvalid=True,
        indisready=True,
        indisunique=False,
        indisprimary=False,
        partial=True,
        expression=False,
        indnatts=1,
        indnkeyatts=1,
        predicate="(total_votes >= 108)",
    )
    for k, v in wanted.items():
        if type(i.get(k)) is not type(v) or i[k] != v:
            raise ValueError("Partial index catalog differs: " + k)
    if (
        sorted(i["reloptions"] or []) != ["ef_construction=64", "m=16"]
        or type(i["oid"]) is not str
        or not re.fullmatch(r"[1-9][0-9]*", i["oid"])
        or i["oid"] == "264013"
        or type(i["bytes"]) is not int
        or not 0 < i["bytes"] <= INDEX_BYTES
        or not re.fullmatch(r"base/[0-9]+/[0-9]+", i["filepath"])
    ):
        raise ValueError("Partial identity/options/storage invalid")


def plan_matches(value, mode):
    if mode not in ("native640", "partial640") or not isinstance(value, list) or len(value) != 1:
        return False
    root = value[0].get("Plan", {})
    nodes = []

    def walk(x):
        if isinstance(x, dict):
            if "Node Type" in x:
                nodes.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(root)
    scans = [n for n in nodes if "Scan" in n.get("Node Type", "")]
    return (
        root.get("Node Type") == "Limit"
        and len(scans) == 1
        and scans[0].get("Node Type") == "Index Scan"
        and scans[0].get("Index Name") == ("reviews_hnsw" if mode == "native640" else INDEX)
        and scans[0].get("Relation Name") == "reviews"
    )


def validate_packet(p, q, mode):
    validate_charge(p["charge"])
    text = expected_statement(q, mode)
    params = parameters(q)
    counter = iter(range(1, 5))
    prepared = re.sub("%s", lambda m: "$" + str(next(counter)), text)
    if (
        p["mode"] != mode
        or p["statement"] != text
        or p["statement_sha256"] != digest(text)
        or p["parameters_sha256"] != digest(params)
        or p["prepared_statement"] != prepared
        or p["driver"]["prepare_threshold"] != 5
        or p["driver"]["prepared_max"] != 100
        or len(p["cached"]) > 1
        or (p["must_be_cached"] and not p["cached"])
        or not plan_matches(p["fresh"], mode)
    ):
        raise ValueError("Statement/cache/fresh plan differs")
    for c in p["cached"]:
        if (
            c["statement_sha256"] != digest(prepared)
            or c["generic_plans"] < 0
            or c["custom_plans"] < 0
            or not plan_matches(c["plan"], mode)
        ):
            raise ValueError("Cached plan differs")


class Observer:
    def __init__(self, budget, emit):
        self.budget = budget
        self.emit = emit
        self.catalogs = []
        self.plan_packets = 0
        self.operations = Counter()

    def execute(self, conn, kind, statement, params=None):
        self.operations[kind] += 1
        with category("observer"):
            return conn.execute(statement, params, prepare=False)

    def catalog(self, conn, copy_name, phase, candidate=False, stable=True):
        start = time.perf_counter_ns()
        v = self.execute(conn, "catalog", CATALOG_SQL).fetchone()[0]
        if isinstance(v, str):
            v = json.loads(v)
        record = dict(
            copy=copy_name,
            session_user=conn.info.user,
            phase=phase,
            value=v,
            sha256=digest(v),
            charge=diagnostic_charge(start),
            candidate=candidate,
        )
        self.emit("catalogs", record)  # raw is durable BEFORE any validator can raise
        validate_catalog(v, candidate)
        prior = [
            c
            for c in self.catalogs
            if c["copy"] == copy_name
            and c["candidate"] == candidate
            and c["session_user"] == record["session_user"]
        ]
        if stable and prior and prior[0]["value"] != v:
            raise RuntimeError("Catalog/statistics/environment changed during comparison")
        self.catalogs.append(record)
        return v

    def plan(self, reader, q, must_be_cached=False):
        import psycopg
        from psycopg import sql

        start = time.perf_counter_ns()
        reader.check()
        conn = reader.connection
        statement, params = reader.backend._statement(q)
        text = statement.as_string(conn)
        if text != expected_statement(q, reader.mode) or params != parameters(q):
            raise RuntimeError("SQL/formatter differs")
        rows = self.execute(conn, "cache_inventory", CACHE_SQL).fetchall()
        counter = iter(range(1, 5))
        prepared = re.sub("%s", lambda m: "$" + str(next(counter)), text)
        fresh = self.execute(
            conn, "fresh_explain", sql.SQL("EXPLAIN (FORMAT JSON) ") + statement, params
        ).fetchone()[0]
        if isinstance(fresh, str):
            fresh = json.loads(fresh)
        matching = [r for r in rows if r[1] == prepared]
        if len(matching) > 1:
            raise RuntimeError("Duplicate matching prepared query shapes")
        cached = []
        for name, source, types, generic, custom in matching:
            command = sql.SQL("EXPLAIN (FORMAT JSON) EXECUTE {} ({})").format(
                sql.Identifier(name), sql.SQL(",").join(sql.Literal(v) for v in params)
            )
            v = self.execute(conn, "cached_explain", command).fetchone()[0]
            if isinstance(v, str):
                v = json.loads(v)
            cached.append(
                dict(
                    name=name,
                    statement_sha256=digest(source),
                    parameter_types=types,
                    generic_plans=generic,
                    custom_plans=custom,
                    plan=compact_plan(v, q),
                )
            )
        p = dict(
            mode=reader.mode,
            statement=text,
            statement_sha256=digest(text),
            parameters_sha256=digest(params),
            prepared_statement=prepared,
            driver=dict(
                psycopg=psycopg.__version__,
                prepare_threshold=conn.prepare_threshold,
                prepared_max=conn.prepared_max,
            ),
            fresh=compact_plan(fresh, q),
            cached=cached,
            must_be_cached=must_be_cached,
            charge=diagnostic_charge(start),
        )
        self.emit(
            "plans",
            dict(query_id=q["id"], reader=reader.identity, stage=self.budget.stage, packet=p),
        )
        validate_packet(p, q, reader.mode)
        self.plan_packets += 1
        reader.check()
        return p
