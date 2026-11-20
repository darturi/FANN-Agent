"""Fresh private PostgreSQL snapshot, fresh exact scoring, and instrumented v3 queries."""

import json
import math
import os
import shutil
import struct
import subprocess
from contextlib import ExitStack
from pathlib import Path
from time import perf_counter_ns

from fannagent.api.broad_policy import (
    COUNT,
    DISTANCE,
    FEATURES,
    FRONTIER,
    TURNOVER,
    Executable,
    compile_graph,
    start,
)

from .core import FILTERS, digest, read, sha, write

FUNCTIONS = """
CREATE SCHEMA IF NOT EXISTS fannagent;
CREATE OR REPLACE FUNCTION fannagent.prewarm_index(regclass) RETURNS bigint
AS '$libdir/vector','fannclean_prewarm_index' LANGUAGE C STRICT VOLATILE;
CREATE OR REPLACE FUNCTION fannagent.study_attach(regclass,regclass,integer,integer,integer)
RETURNS integer AS '$libdir/vector','fannbench_confirm_attach' LANGUAGE C STRICT VOLATILE;
CREATE OR REPLACE FUNCTION fannagent.confirm_last() RETURNS integer
AS '$libdir/vector','fannbench_confirm_last' LANGUAGE C VOLATILE;
CREATE OR REPLACE FUNCTION fannagent.oracle_set(integer) RETURNS integer
AS '$libdir/vector','fannbench_oracle_set' LANGUAGE C STRICT VOLATILE;
CREATE OR REPLACE FUNCTION fannagent.v3_audit_enable(boolean) RETURNS void
AS '$libdir/vector','fannbench_v3_audit_enable' LANGUAGE C VOLATILE;
CREATE OR REPLACE FUNCTION fannagent.v3_audit_read() RETURNS text
AS '$libdir/vector','fannbench_v3_audit_read' LANGUAGE C VOLATILE;
"""


def check_plan(plan, exact):
    nodes = []

    def visit(node):
        nodes.append(node)
        for child in node.get("Plans", []):
            visit(child)

    visit(plan[0]["Plan"])
    scans = [n for n in nodes if n.get("Relation Name") == "reviews"]
    if not scans or any(
        n.get("Parallel Aware") or n.get("Node Type", "").startswith("Gather") for n in nodes
    ):
        raise ValueError("unexpected/parallel task plan")
    if exact:
        if any(n["Node Type"] != "Seq Scan" for n in scans):
            raise ValueError("exact scoring requires a sequential scan")
    elif any(
        n["Node Type"] != "Index Scan" or n.get("Index Name") != "reviews_hnsw" for n in scans
    ):
        raise ValueError("ANN scoring requires the declared HNSW index")


def verify_vm(policy, force, threshold, audit, actual_cp, compiled=None):
    graph, vm = compiled if compiled is not None else (None, None)
    graph = compile_graph(policy) if graph is None else graph
    vm = Executable(graph) if vm is None else vm
    state = start(graph)
    predicate = "unfiltered" if threshold < 0 else f"votes{threshold}"
    steps = graph["programs"].get(predicate, {}).get("steps", {})
    active_points = sorted(k for k, step in steps.items() if step["mask"])
    expected_cp, previous = 0, 0
    for position, frame in enumerate(audit["frames"]):
        if expected_cp:
            raise ValueError("native audit continued after a stop")
        cp, mask = frame["checkpoint"], frame["mask"]
        if cp <= previous or cp not in steps or mask != steps[cp]["mask"]:
            raise ValueError("native audit schedule differs from the compiled graph")
        if position >= len(active_points) or cp != active_points[position]:
            raise ValueError("native audit omitted an active checkpoint")
        values = dict(zip(FEATURES, frame["values"], strict=True))
        if any(v is not None and not math.isfinite(v) for v in values.values()):
            raise ValueError("nonfinite feature in native audit")
        units = frame["count_units"] if mask & COUNT else 0
        units += 16 * int(values["qualifying_count"] or 0) if mask & DISTANCE else 0
        units += int(bool(mask & (DISTANCE | FRONTIER)))
        units += 100 if mask & TURNOVER and values["top10_new_since_previous"] is not None else 0
        decision = vm.step(predicate, cp, values, state, collection_units=units)
        if not frame["exhausted"] and (
            decision != frame["decision"]
            or state.remaining != frame["remaining"]
            or state.registers != frame["state"]
        ):
            raise ValueError("native/reference VM decision, state or fuel differs")
        if state.fault != frame["fault"] or state.exhausted != frame["exhausted"]:
            raise ValueError("native/reference VM fault semantics differ")
        if decision and not force and not expected_cp:
            expected_cp = cp
        previous = cp
    if expected_cp != actual_cp:
        raise ValueError("native stop differs from reference VM")


def membership(path, heap, index, rows, threshold):
    values = []
    for tid, votes, _ in rows:
        block, offset = map(int, str(tid).strip("()").split(","))
        if block < 0 or not 1 <= offset <= 512:
            raise ValueError("invalid tuple location")
        values.append(
            (block, offset - 1, threshold < 0 or votes is not None and votes >= threshold)
        )
    data = bytearray((max(b for b, _, _ in values) + 1) * 128)
    for block, offset, passing in values:
        byte, shift = block * 128 + offset // 4, (offset % 4) * 2
        if data[byte] & (3 << shift):
            raise ValueError("duplicate tuple location")
        data[byte] |= (3 if passing else 1) << shift
    with path.open("xb") as stream:
        stream.write(
            struct.pack("<8sIIII", b"V108MAP1", heap, index, len(rows), sum(v[2] for v in values))
        )
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
        os.fchmod(stream.fileno(), 0o400)


class Postgres:
    """Runs inside a disposable container with this request's compiled module bound in."""

    cleanup_verified = False

    def __init__(self, root, bindings, request_dir):
        self.root, self.bindings, self.directory = Path(root), bindings, Path(request_dir)

    def __enter__(self):
        from psycopg import connect
        from psycopg.conninfo import make_conninfo

        config = read(self.root / "private/backend.json")
        self.config = config
        self.work = self.directory / "work"
        self.work.mkdir()
        self.pgdata = self.work / "pgdata"
        snapshot = Path(config["snapshot"])
        if (
            any(p.is_symlink() for p in snapshot.rglob("*"))
            or (snapshot / "postmaster.pid").exists()
        ):
            raise ValueError("snapshot must be a stopped, regular-file-only static database")
        shutil.copytree(snapshot, self.pgdata)
        os.chmod(self.pgdata, 0o700)
        # The disposable server has no TCP listener. Its socket lives inside this
        # user's private request directory; the source snapshot is never edited.
        (self.pgdata / "pg_hba.conf").write_text("local all all trust\n")
        socket = self.work / "socket"
        socket.mkdir()
        self.pg_ctl = config.get("pg_ctl", "/opt/postgresql/bin/pg_ctl")
        if sha("/opt/postgresql/lib/vector.so") != read(self.directory / "module.json")["sha256"]:
            raise ValueError("bound native module differs from this request")
        self.started = False
        self.stack = ExitStack()
        try:
            subprocess.run(
                [
                    self.pg_ctl,
                    "-D",
                    str(self.pgdata),
                    "-l",
                    str(self.work / "server.log"),
                    "-o",
                    f"-k {socket} -c listen_addresses='' -c port=55432 "
                    "-c max_parallel_workers_per_gather=0 -c autovacuum=off "
                    "-c shared_preload_libraries='' -c session_preload_libraries='' "
                    "-c local_preload_libraries='' -c shared_buffers=4GB",
                    "-w",
                    "start",
                ],
                check=True,
                timeout=120,
                capture_output=True,
            )
            self.started = True
            self.dsn = make_conninfo(
                host=str(socket),
                port=55432,
                dbname=config.get("database", "torch_reviews"),
                user=config.get("database_user"),
            )
            self.keeper = self.stack.enter_context(connect(self.dsn, autocommit=True))
            tables = self.keeper.execute(
                "SELECT schemaname,tablename FROM pg_tables "
                "WHERE schemaname NOT IN ('pg_catalog','information_schema')"
            ).fetchall()
            if set(tables) != {("public", "reviews")}:
                raise ValueError(
                    "snapshot contains non-task tables; no prior empirical tables allowed"
                )
            self.keeper.execute(FUNCTIONS)
            prewarmed = self.keeper.execute(
                "SELECT fannagent.prewarm_index('public.reviews_hnsw'::regclass)"
            ).fetchone()[0]
            write(
                self.directory / "buffer-warmup.json",
                {
                    "shared_buffers": self.keeper.execute("SHOW shared_buffers").fetchone()[0],
                    "index_blocks_read": prewarmed,
                    "purpose": "static index cache preparation outside SQL request timing",
                    "ann_or_exact_queries": 0,
                },
            )
            self.stack.enter_context(self.keeper.transaction())
            self.keeper.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            self.keeper.execute("LOCK TABLE public.reviews IN SHARE MODE NOWAIT")
            self.snapshot = self.keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
            heap, index = self.keeper.execute(
                "SELECT 'public.reviews'::regclass::oid,'public.reviews_hnsw'::regclass::oid"
            ).fetchone()
            rows = self.keeper.execute(
                "SELECT ctid::text,total_votes,id FROM ONLY public.reviews"
            ).fetchall()
            if len(rows) != config.get("rows", 247286) or len(rows) != 247286:
                raise ValueError(
                    "instrumented engine requires the declared 247286-row static corpus"
                )
            self.identity = self.keeper.execute(
                "SELECT oid,relfilenode,relpages FROM pg_class "
                "WHERE oid='public.reviews_hnsw'::regclass"
            ).fetchone()
            self.eligible = {
                t: {i for _, votes, i in rows if t < 0 or votes is not None and votes >= t}
                for t in FILTERS
            }
            for t in FILTERS:
                membership(self.work / f"membership-{t}.bin", heap, index, rows, t)
            self.readers = [
                self.stack.enter_context(connect(self.dsn, autocommit=True)) for _ in range(4)
            ]
            allowed = sorted(os.sched_getaffinity(0))
            if len(allowed) < 4:
                raise ValueError("four available CPUs required")
            for i, c in enumerate(self.readers):
                pid = c.execute("SELECT pg_backend_pid()").fetchone()[0]
                os.sched_setaffinity(pid, {allowed[i]})
                if os.sched_getaffinity(pid) != {allowed[i]}:
                    raise ValueError("reader affinity failed")
            self.arms = read(self.directory / "module.json")["arms"]
            self.compiled = {}
            unique = {}
            for name, (artifact, _) in self.bindings.items():
                key = digest(artifact)
                if key not in unique:
                    graph = compile_graph(artifact)
                    unique[key] = (graph, Executable(graph))
                self.compiled[name] = unique[key]
            self.checked_plans = set()
            return self
        except BaseException:
            self.__exit__(*__import__("sys").exc_info())
            raise

    def execute(self, case, family, *, reader=0, audit=False, checkpoint=None):
        from psycopg import sql

        c, t = self.readers[reader], case["filter"]
        arm = 10 if family == "forced" else self.arms.get(family)
        with c.transaction():
            c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            c.execute(sql.SQL("SET TRANSACTION SNAPSHOT {}").format(sql.Literal(self.snapshot)))
            c.execute("SET LOCAL hnsw.ef_search=640")
            c.execute("SET LOCAL hnsw.iterative_scan=off")
            c.execute("SET LOCAL max_parallel_workers_per_gather=0")
            c.execute("SELECT fannagent.v3_audit_enable(%s)", (audit,))
            if arm is not None:
                c.execute(
                    "SELECT fannagent.study_attach("
                    "'public.reviews','public.reviews_hnsw',%s,%s,%s)",
                    (t, arm, len(self.eligible[t])),
                )
            if family == "forced":
                c.execute("SELECT fannagent.oracle_set(%s)", (checkpoint,))
            if family == "exact":
                for name in ("enable_indexscan", "enable_indexonlyscan", "enable_bitmapscan"):
                    c.execute("SET LOCAL " + name + "=off")
                c.execute("SET LOCAL enable_seqscan=on")
            else:
                c.execute("SET LOCAL enable_seqscan=off")
            vector = "[" + ",".join(format(float(v), ".9g") for v in case["vector"]) + "]"
            query = "SELECT id,embedding <=> %s::vector AS distance FROM public.reviews"
            params = [vector]
            if t >= 0:
                query += " WHERE total_votes >= %s"
                params.append(t)
            query += " ORDER BY embedding <=> %s::vector"
            params.append(vector)
            query += " FETCH FIRST 10 ROWS WITH TIES" if family == "exact" else " LIMIT 10"
            if (family, t) not in self.checked_plans:
                plan = c.execute(
                    "EXPLAIN (FORMAT JSON) " + query, params, prepare=False
                ).fetchone()[0]
                check_plan(plan, family == "exact")
                self.checked_plans.add((family, t))
            begin = perf_counter_ns()
            result = [[i, float(d)] for i, d in c.execute(query, params, prepare=False).fetchall()]
            elapsed = perf_counter_ns() - begin
            if any(i not in self.eligible[t] or not math.isfinite(d) for i, d in result):
                raise ValueError("native output violates the predicate or has nonfinite distances")
            cp = (
                c.execute("SELECT fannagent.confirm_last()").fetchone()[0] if arm is not None else 0
            )
            observed = (
                json.loads(c.execute("SELECT fannagent.v3_audit_read()").fetchone()[0])
                if audit and family in self.bindings
                else {"frames": [], "fault": False, "exhausted": False}
            )
            if audit and family in self.bindings:
                policy, force = self.bindings[family]
                verify_vm(policy, force, t, observed, cp, self.compiled[family])
            return {
                "output": result,
                "checkpoint": cp,
                "request_ns": elapsed,
                "frames": observed["frames"],
                "fault": observed.get("fault", False),
                "exhausted": observed.get("exhausted", False),
            }

    def __exit__(self, kind, error, tb):
        unchanged = not hasattr(self, "identity")
        try:
            if hasattr(self, "identity"):
                unchanged = (
                    self.keeper.execute(
                        "SELECT oid,relfilenode,relpages FROM pg_class "
                        "WHERE oid='public.reviews_hnsw'::regclass"
                    ).fetchone()
                    == self.identity
                )
        finally:
            try:
                if hasattr(self, "stack"):
                    self.stack.close()
            finally:
                if getattr(self, "started", False):
                    subprocess.run(
                        [self.pg_ctl, "-D", str(self.pgdata), "-m", "fast", "-w", "stop"],
                        check=True,
                        timeout=90,
                        capture_output=True,
                    )
        self.cleanup_verified = unchanged and not (self.pgdata / "postmaster.pid").exists()
        if not self.cleanup_verified:
            raise ValueError("private database cleanup/index identity failed")
        write(
            self.directory / "cleanup.json",
            {"verified": True, "index_identity": getattr(self, "identity", None)},
        )
        shutil.rmtree(self.work)
