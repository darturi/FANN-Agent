"""Counted read-only catalog and current/cached plan inspection; never runs ANALYZE."""

import json
import math
import re
import struct
import time
from collections import Counter

from xt_common import digest, save

CATALOG_SQL = """SELECT jsonb_build_object(
 'server_version_num',current_setting('server_version_num'),
 'vector_version',(SELECT extversion FROM pg_extension WHERE extname='vector'),
 'relation',(SELECT to_jsonb(t) FROM (SELECT c.oid,c.relkind,c.relrowsecurity,c.relfilenode,
 c.relpages,c.reltuples,c.relallvisible FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relname='reviews') t),
 'columns',(SELECT jsonb_agg(to_jsonb(t) ORDER BY attnum) FROM (SELECT a.attnum,a.attname,
 a.attnotnull,typ.typname,a.atttypmod FROM pg_attribute a JOIN pg_type typ ON typ.oid=a.atttypid
 WHERE a.attrelid='public.reviews'::regclass AND a.attnum>0 AND NOT a.attisdropped) t),
 'indexes',(SELECT jsonb_agg(to_jsonb(t) ORDER BY relname) FROM (SELECT c.oid,c.relname,
 am.amname,i.indisvalid,i.indisready,i.indisunique,i.indisprimary,
 i.indpred IS NOT NULL AS partial,i.indexprs IS NOT NULL AS expression,i.indnatts,i.indnkeyatts,
 c.reloptions,pg_relation_size(c.oid) AS bytes,pg_get_indexdef(c.oid) AS definition,
 ARRAY(SELECT a.attname FROM unnest(i.indkey::smallint[]) WITH ORDINALITY AS k(attnum,ord)
 JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum ORDER BY k.ord) AS keys,
 ARRAY(SELECT op.opcname FROM unnest(i.indclass::oid[]) WITH ORDINALITY AS k(opoid,ord)
 JOIN pg_opclass op ON op.oid=k.opoid ORDER BY k.ord) AS opclasses
 FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_am am ON am.oid=c.relam
 WHERE i.indrelid='public.reviews'::regclass) t),
 'statistics',(SELECT jsonb_agg(to_jsonb(t) ORDER BY attname) FROM (SELECT attname,null_frac,
 avg_width,n_distinct,correlation,most_common_vals::text,most_common_freqs,histogram_bounds::text
 FROM pg_stats WHERE schemaname='public' AND tablename='reviews'
 AND attname IN ('id','total_votes')) t),
 'environment',(SELECT jsonb_object_agg(name,setting) FROM pg_settings WHERE name=ANY(ARRAY[
 'plan_cache_mode','jit','jit_above_cost','jit_inline_above_cost','jit_optimize_above_cost',
 'max_parallel_workers_per_gather','max_parallel_workers','max_worker_processes',
 'work_mem','parallel_setup_cost','parallel_tuple_cost','min_parallel_table_scan_size',
 'min_parallel_index_scan_size','shared_buffers','track_io_timing','default_transaction_read_only']))
)"""
CACHE_SQL = """SELECT name,statement,parameter_types::text,generic_plans,custom_plans
FROM pg_prepared_statements ORDER BY name"""


def expected_statement(query):
    predicate = "TRUE" if query.get("filter") is None else '"total_votes" >= %s'
    return (
        'SELECT "id", "embedding" <=> %s::vector AS distance FROM "public"."reviews" WHERE '
        + predicate
        + ' ORDER BY "embedding" <=> %s::vector LIMIT %s'
    )


def parameters(query):
    vector = "[" + ",".join(format(float(v), ".9g") for v in query["vector"]) + "]"
    return [
        vector,
        *([] if query.get("filter") is None else [query["filter"]["value"]]),
        vector,
        query["k"],
    ]


def compact_plan(value, query):
    """Remove only verified float32-equivalent vector literals, never plan structure."""
    if isinstance(value, list):
        return [compact_plan(v, query) for v in value]
    if isinstance(value, dict):
        return {k: compact_plan(v, query) for k, v in value.items()}
    if isinstance(value, str):

        def redact(match):
            values = json.loads(match.group(1))
            if len(values) != 768 or [struct.pack("<f", v) for v in values] != [
                struct.pack("<f", v) for v in query["vector"]
            ]:
                raise RuntimeError("EXPLAIN literal differs from the admitted float32 query")
            return "'<sealed_vector>'::vector"

        return re.sub(r"'(\[[^']*\])'::vector", redact, value)
    return value


def plan_matches(value, mode):
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        return False
    root = value[0].get("Plan", {})
    if root.get("Node Type") != "Limit":
        return False
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
    if mode == "native640":
        return (
            len(scans) == 1
            and scans[0].get("Node Type") == "Index Scan"
            and scans[0].get("Index Name") == "reviews_hnsw"
            and scans[0].get("Relation Name") == "reviews"
        )
    return (
        mode == "exact10"
        and bool(scans)
        and all(
            n.get("Node Type") == "Seq Scan" and n.get("Relation Name") == "reviews" for n in scans
        )
    )


def validate_catalog(value):
    if value.get("server_version_num") != "170011" or value.get("vector_version") != "0.8.6":
        raise ValueError("Catalog runtime version differs")
    relation = value["relation"]
    if relation["relkind"] != "r" or relation["relrowsecurity"]:
        raise ValueError("Relation is not the unchanged ordinary non-RLS target")
    columns = [(r["attnum"], r["attname"], r["typname"], r["attnotnull"]) for r in value["columns"]]
    if (
        columns
        != [
            (1, "id", "int8", True),
            (2, "embedding", "vector", True),
            (3, "total_votes", "int8", True),
        ]
        or value["columns"][1]["atttypmod"] != 768
    ):
        raise ValueError("Column/metric/data layout changed")
    indexes = {r["relname"]: r for r in value["indexes"]}
    if len(value["indexes"]) != 2 or set(indexes) != {"reviews_pkey", "reviews_hnsw"}:
        raise ValueError("Unexpected index catalog; no normalization/rebuild allowed")
    for r in indexes.values():
        if (
            not r["indisvalid"]
            or not r["indisready"]
            or r["partial"]
            or r["expression"]
            or r["indnatts"] != 1
            or r["indnkeyatts"] != 1
        ):
            raise ValueError("Invalid/expression/partial/additional index key")
    primary = indexes["reviews_pkey"]
    graph = indexes["reviews_hnsw"]
    if (
        primary["amname"] != "btree"
        or primary["keys"] != ["id"]
        or not primary["indisunique"]
        or not primary["indisprimary"]
    ):
        raise ValueError("Identifier index changed")
    # PostgreSQL to_jsonb(oid) uses JSON text, not JSON numeric conversion.
    # Keep an exact value and type check; no coercion or graph-identity waiver.
    expected = {
        "amname": "hnsw",
        "oid": "264013",
        "keys": ["embedding"],
        "opclasses": ["vector_cosine_ops"],
        "indisunique": False,
        "indisprimary": False,
        "bytes": 1012678656,
        "reloptions": ["ef_construction=64", "m=16"],
    }
    actual = {k: graph.get(k) for k in expected}
    actual["reloptions"] = sorted(actual["reloptions"] or [])
    differences = {
        k: {"expected": v, "actual": actual[k], "actual_type": type(actual[k]).__name__}
        for k, v in expected.items()
        if type(actual[k]) is not type(v) or actual[k] != v
    }
    if differences:
        raise ValueError(
            "HNSW catalog differs from frozen source: " + json.dumps(differences, sort_keys=True)
        )
    if {v["attname"] for v in value["statistics"] or []} != {"id", "total_votes"}:
        raise ValueError("Scalar statistics incomplete")
    env = value["environment"]
    if (
        env["plan_cache_mode"] != "auto"
        or env["jit"] != "on"
        or env["max_parallel_workers_per_gather"] != "2"
        or env["work_mem"] != "16384"
    ):
        raise ValueError("JIT/parallel/work_mem/cache tuning is outside this treatment")


def validate_packet(row, query, mode):
    validate_charge(row["charge"])
    if (
        row["mode"] != mode
        or row["statement"] != expected_statement(query)
        or row["statement_sha256"] != digest(row["statement"])
        or row["parameters_sha256"] != digest(parameters(query))
    ):
        raise ValueError("Statement/query/plan identity differs")
    counter = iter(range(1, len(parameters(query)) + 1))
    prepared = re.sub(r"%s", lambda m: "$" + str(next(counter)), expected_statement(query))
    if row["prepared_statement"] != prepared or len({p["name"] for p in row["cached"]}) != len(
        row["cached"]
    ):
        raise ValueError("Prepared query identity differs")
    if row["driver"]["prepare_threshold"] != 5 or row["driver"]["prepared_max"] != 100:
        raise ValueError("Automatic preparation was tuned or unsupported")
    if not plan_matches(row["fresh"], mode) or any(
        not plan_matches(p["plan"], mode) for p in row["cached"]
    ):
        raise ValueError("Unexpected fresh/cached execution plan")
    if row["must_be_cached"] and not row["cached"]:
        raise ValueError("Expected actual prepared query missing")
    for p in row["cached"]:
        if (
            p["statement_sha256"] != digest(row["prepared_statement"])
            or p["generic_plans"] < 0
            or p["custom_plans"] < 0
        ):
            raise ValueError("Cached statement identity/counter differs")


def validate_charge(row):
    if (
        type(row["start_ns"]) is not int
        or type(row["end_ns"]) is not int
        or not 0 <= row["start_ns"] < row["end_ns"]
        or not math.isfinite(row["outer_ms"])
        or abs(row["outer_ms"] - (row["end_ns"] - row["start_ns"]) / 1e6) > 1e-9
    ):
        raise ValueError("Diagnostic outer timer arithmetic differs")


def diagnostic_charge(start):
    end = time.perf_counter_ns()
    return {"start_ns": start, "end_ns": end, "outer_ms": (end - start) / 1e6}


class Observer:
    def __init__(self):
        self.operations = Counter()
        self.catalogs = []
        self.plan_packets = 0
        self.budget = None
        self.rejected_catalog = None

    def execute(self, conn, kind, statement, params=None):
        if self.budget is not None:
            self.budget.check()
        if sum(self.operations.values()) >= 40000:
            raise RuntimeError("Observer SQL ceiling exhausted")
        self.operations[kind] += 1
        return conn.execute(statement, params, prepare=False)

    def catalog(self, reader, phase):
        start = time.perf_counter_ns()
        reader.check()
        value = self.execute(reader.connection, "catalog", CATALOG_SQL).fetchone()[0]
        if isinstance(value, str):
            value = json.loads(value)
        try:
            validate_catalog(value)
            if self.catalogs and value != self.catalogs[0]["value"]:
                raise RuntimeError("Catalog/statistics/environment changed during comparison")
        except Exception as error:
            self.rejected_catalog = {
                "phase": phase,
                "value": value,
                "sha256": digest(value),
                "charge": diagnostic_charge(start),
                "validation_passed": False,
                "error": {"type": type(error).__name__, "message": str(error)},
                "previous_accepted_catalog_sha256": (
                    self.catalogs[0]["sha256"] if self.catalogs else None
                ),
            }
            raise
        self.catalogs.append(
            {
                "phase": phase,
                "value": value,
                "sha256": digest(value),
                "charge": diagnostic_charge(start),
            }
        )
        reader.check()
        return self.catalogs[-1]

    def persist_failure(self, out):
        if self.rejected_catalog is not None:
            save(out / "catalog-failure.json", self.rejected_catalog)

    def plan(self, reader, query, must_be_cached=False):
        import psycopg
        from psycopg import sql

        start = time.perf_counter_ns()
        reader.check()
        conn = reader.connection
        statement, params = reader.backend._statement(query)
        text = statement.as_string(conn)
        if text != expected_statement(query) or params != parameters(query):
            raise RuntimeError("Native SQL/formatter changed")
        driver = {
            "psycopg": psycopg.__version__,
            "prepare_threshold": conn.prepare_threshold,
            "prepared_max": conn.prepared_max,
        }
        rows = self.execute(conn, "cache_inventory", CACHE_SQL).fetchall()
        counter = iter(range(1, len(params) + 1))
        prepared = re.sub(r"%s", lambda m: "$" + str(next(counter)), text)
        fresh = self.execute(
            conn, "fresh_explain", sql.SQL("EXPLAIN (FORMAT JSON) ") + statement, params
        ).fetchone()[0]
        if isinstance(fresh, str):
            fresh = json.loads(fresh)
        cached = []
        for name, source, types, generic, custom in rows:
            if source != prepared:
                continue
            command = sql.SQL("EXPLAIN (FORMAT JSON) EXECUTE {} ({})").format(
                sql.Identifier(name), sql.SQL(",").join(sql.Literal(v) for v in params)
            )
            value = self.execute(conn, "cached_explain", command).fetchone()[0]
            if isinstance(value, str):
                value = json.loads(value)
            cached.append(
                {
                    "name": name,
                    "statement_sha256": digest(source),
                    "parameter_types": types,
                    "generic_plans": generic,
                    "custom_plans": custom,
                    "plan": compact_plan(value, query),
                }
            )
        packet = {
            "mode": reader.mode,
            "statement": text,
            "statement_sha256": digest(text),
            "parameters_sha256": digest(params),
            "prepared_statement": prepared,
            "driver": driver,
            "fresh": compact_plan(fresh, query),
            "cached": cached,
            "must_be_cached": must_be_cached,
            "charge": diagnostic_charge(start),
        }
        validate_packet(packet, query, reader.mode)
        reader.check()
        self.plan_packets += 1
        return packet
