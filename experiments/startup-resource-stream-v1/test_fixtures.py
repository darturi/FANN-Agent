"""Synthetic fixtures; actual frozen backend methods, no PostgreSQL/native search."""
# ruff: noqa: E402

import copy
import importlib.util
import json
import os
import shutil
import sys
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import experiment as E
import pc_common as C

C.bootstrap(E.SOURCE)
sys.path.insert(0, str(C.HERE))
import si_stream
import si_verify

assert Path(si_stream.__file__).resolve().parent == E.HERE
assert Path(si_verify.__file__).resolve().parent == E.HERE
import psycopg
from pc_settings import MEMORY_SQL
from pc_trace import (
    AUDIT_SQL,
    BIND_SQL,
    DATA_SQL,
    DIRECTORY_SQL,
    PID_SQL,
    READER_CONTEXT_SQL,
    ROLE_SQL,
    SET_SQL,
    SNAPSHOT_SQL,
    TIMEOUT_SQL,
)

from fannagent.snapshot import Snapshot

VECTOR = [1.0] + [0.0] * 767
META = C.read(E.SOURCE / "origin-source.json")["metadata"]


def rewrite(path, value):
    path.write_bytes(C.encoded(value))


def reseal(package):
    p = package / "manifest.json"
    if p.exists():
        p.unlink()
    C.save(
        p,
        dict(
            version=C.VERSION,
            files={
                str(f.relative_to(package)): C.sha(f)
                for f in package.rglob("*")
                if f.is_file() and f.name != "submission-binding.json"
            },
        ),
    )


def frozen_backend():
    from execution import load_backend

    original = importlib.util.spec_from_file_location
    runner = E.ROOT / "trials/torch-reviews-first/runner.py"
    assert C.sha(runner) == C.read(runner.parent / "manifest.json")["files"]["runner.py"]
    with patch(
        "importlib.util.spec_from_file_location",
        side_effect=lambda name, path, *a, **k: original(
            name, runner if str(path) == "/opt/torch-reviews/runner.py" else path, *a, **k
        ),
    ):
        result = load_backend(E.SOURCE / "frozen")
    sys.path.insert(0, str(C.HERE))
    return result


def snapshot():
    return Snapshot(
        [dict(source_id=i, vector=VECTOR, metadata=dict(total_votes=108)) for i in range(40)], META
    )


def source_cell(path):
    path.mkdir(mode=0o700)
    (path / "pgdata").mkdir(mode=0o700)
    (path / "pgdata/x").write_bytes(b"synthetic pgdata")
    for name in ["admin.pgpass", "reader.pgpass", "pg_hba.conf"]:
        (path / name).write_text("private")
        (path / name).chmod(0o600)
    shutil.copyfile(E.SOURCE / "frozen/source-index.json", path / "database-identity.json")
    (path / "database-identity.json").chmod(0o600)


class Cursor:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, *a, **k):
        self.connection.execute(*a, **k)
        return self

    def __iter__(self):
        return iter(self.connection.rows)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class Connection:
    def __init__(self, cell, work, catalogs, admin=False):
        self.cell, self.work, self.catalogs, self.admin = cell, work, catalogs, admin
        self.adapters = psycopg.adapters
        self.closed = False
        self.autocommit = True
        self.info = SimpleNamespace(
            transaction_status=0, user="torch_owner" if admin else "torch_reader"
        )
        self.pgconn = SimpleNamespace(transaction_status=0)
        self.prepare_threshold = 5
        self.prepared_max = 100
        self.values = {}
        self.rows = []
        self.pid = 30 + C.CELLS.index(cell)
        self.executed = []

    @property
    def connection(self):
        return None

    def close(self):
        self.closed = True

    def cursor(self, *a, **k):
        return Cursor(self)

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return list(self.rows)

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, statement, params=None, **kwargs):
        text = statement.as_string(self) if hasattr(statement, "as_string") else str(statement)
        self.executed.append((text, params))
        if text == ROLE_SQL:
            self.rows = [("torch_reviews", "torch_reader", None, False, False)]
        elif text == BIND_SQL:
            self.rows = [(270339 if self.cell == "partial640" else 264013,)]
        elif text == SET_SQL:
            self.values[params[0]] = params[1]
            self.rows = [(params[1],)]
        elif text == TIMEOUT_SQL:
            self.values["statement_timeout"] = params[0]
            self.rows = [(params[0],)]
        elif text == AUDIT_SQL:
            self.rows = [
                (n, self.values[n], "40" if n == "hnsw.ef_search" else self.values[n], "session")
                for n in sorted(params[0])
            ]
        elif text == READER_CONTEXT_SQL:
            self.rows = [("auto", "on")]
        elif text == SNAPSHOT_SQL:
            self.rows = [
                (
                    0 if getattr(self, "fault", None) == "stream_constructor" else i,
                    json.dumps(VECTOR),
                    108,
                )
                for i in range(40)
            ]
        elif text == DATA_SQL:
            self.rows = [(i, json.dumps(VECTOR), 108) for i in range(40)]
        elif text == DIRECTORY_SQL:
            self.rows = [(self.pid, str(self.work / self.cell / "pgdata"))]
        elif text == PID_SQL:
            self.rows = [(self.pid, "torch_reviews", "torch_reader", None)]
        elif text == "SELECT pg_backend_pid()":
            self.rows = [(self.pid,)]
        elif text == MEMORY_SQL:
            self.rows = [(128 * 1024**2, 16, 4 * 1024**2, "64MB", "0")]
        elif "jsonb_build_object" in text:
            self.rows = [(copy.deepcopy(self.catalogs[self.cell]),)]
        else:
            raise AssertionError("Unexpected or search SQL in fixture: " + text[:100])
        return self


class Proc:
    def __init__(self, budget, emit):
        self.emit = emit
        self.client = 999
        self.client_start = 9990
        self.layout = dict(selected=[0, 1, 2, 3])
        self.n = 0
        emit(
            "placement",
            dict(
                kind="allocation",
                selected=[0, 1, 2, 3],
                allowed=[0, 1, 2, 3],
                topology=[dict(cpu=i, socket=0, core=i) for i in range(4)],
            ),
        )

    def pin(self, *a):
        pass

    def server(self, *a):
        pass

    def freeze_client_threads(self):
        self.emit("placement", dict(kind="client_threads", cpu=0, tids=[999]))

    def bind(self, reader, work, epoch=0):
        self.n += 1
        reader.connection.raw.pid = 100 + self.n
        reader.physical = dict(
            reader=reader.identity,
            cell=reader.mode,
            pid=100 + self.n,
            starttime=1000 + self.n,
            postmaster=10 + C.CELLS.index(reader.mode),
            server=str(work),
            socket=str(work / "socket"),
            epoch=epoch,
            cpu=1 + C.CELLS.index(reader.mode) if epoch == 0 else 2 - C.CELLS.index(reader.mode),
        )
        self.emit("identities", reader.physical)

    def repin(self, reader, epoch):
        reader.physical["epoch"] = epoch

    def charges(self):
        return dict(proc_reads=100, affinity_operations=100, bundles=10, telemetry_seconds=0.1)


def runtime_fixture(root, seed=None, fault=None):
    import pc_runtime as runtime

    assert Path(runtime.__file__).resolve().parent == E.HERE, "Wrong harness runtime imported"

    root = root.resolve()
    package = root / "package"
    if seed:
        shutil.copytree(seed, package)
    else:
        package = E.build(root / "seal", testing=True)
    work, out, source = [root / n for n in ["work", "run", "source"]]
    for folder in [work, out, source]:
        folder.mkdir()
    for cell in C.CELLS:
        source_cell(source / cell)
    mount = root / "mountinfo"
    mount.write_text("1 0 0:1 / /retained ro - test test ro\n")
    cgroup = root / "cgroup"
    cgroup.write_text("0::/job/task\n")
    snap = snapshot()
    elig = dict(source_ids=snap.source_ids, votes=[108] * 40)
    if fault == "eligibility":
        elig["votes"][0] = 109
    (package / "eligibility.json").write_bytes(C.encoded(elig))
    items = C.lines(package / "queries.jsonl")
    for item in items:
        item["query"]["vector"] = VECTOR
    (package / "queries.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
    cfg = C.read(package / "experiment.json")
    cfg.update(
        snapshot_identity=snap.identity,
        queries_sha256=C.sha(package / "queries.jsonl"),
        fixture_snapshot_rows=40,
    )
    if fault == "snapshot_identity":
        cfg["snapshot_identity"] = "changed"
    rewrite(package / "experiment.json", cfg)
    reseal(package)
    rewrite(out / "memory-health.json", dict(status="running", last_ns=time.monotonic_ns()))
    (out / ".memory-health.json.tmp").write_text("synthetic concurrent host atomic write")
    frozen, base = frozen_backend()
    catalogs = C.read(package / "b2d-catalogs.json")
    opened = []
    stopped = []

    def connect(dsn, **kwargs):
        cell = "partial640" if "partial640" in dsn else "native640"
        conn = Connection(cell, work, catalogs, "torch_owner" in dsn)
        conn.fault = fault
        opened.append(conn)
        return conn

    def start(path):
        if fault == "second_server" and path.name == "partial640":
            raise RuntimeError("Injected server failure")
        (path / "pgdata/postmaster.pid").write_text("10\n")

    def stop(path):
        stopped.append(path.name)
        if not path.exists():
            return
        pid = path / "pgdata/postmaster.pid"
        if pid.exists():
            pid.unlink()
        (path / "server.log").write_text("database system is shut down\n")
        if fault == "cleanup" and path.name == "partial640":
            raise RuntimeError("Injected cleanup error")

    def full_data(conn, bundle):
        from pc_trace import category

        with category("observer"):
            conn.execute(DATA_SQL, prepare=False)
        return dict(rows=247286, data_bits_verified=True)

    mapping = {
        "/patch": package,
        "/results": out,
        "/run": work,
        "/retained": source,
        "/bundle": E.ROOT / "trials/torch-reviews-first",
        "/proc/self/mountinfo": mount,
        "/proc/self/cgroup": cgroup,
    }

    def graph(path, relative):
        return (
            C.CONTRACT["graphs"]["native640"]
            if relative.endswith("264013")
            else C.CONTRACT["graphs"]["partial640"]["partial"]
            if Path(path).name == "partial640"
            else {}
        )

    original_notify = runtime.replace

    def replace(path, value):
        original_notify(path, value)
        if Path(path).name == "progress.json" and fault != "sampler":
            rewrite(out / "memory-health.json", dict(status="running", last_ns=time.monotonic_ns()))

    error = None
    with ExitStack() as stack:
        stack.enter_context(patch.object(sys, "path", list(sys.path)))
        patches = [
            ("pc_runtime.Path", dict(side_effect=lambda p: mapping.get(str(p), Path(p)))),
            (
                "pc_runtime.sha",
                dict(
                    side_effect=lambda p: (
                        C.CONTRACT["runtime"]["module_sha256"]
                        if str(p) == "/opt/postgresql/lib/vector.so"
                        else C.sha(p)
                    )
                ),
            ),
            (
                "pc_runtime.os.uname",
                dict(return_value=SimpleNamespace(sysname="Linux", machine="x86_64")),
            ),
            ("pc_runtime.signal.signal", dict()),
            ("pc_runtime.signal.setitimer", dict()),
            (
                "pc_runtime.control_state",
                dict(return_value=dict(fields={"Database cluster state": "shut down"})),
            ),
            ("pc_runtime.verify_graphs", dict()),
            ("pc_runtime.graph_files", dict(side_effect=graph)),
            ("pc_runtime.verify_data", dict(side_effect=full_data)),
            ("pc_runtime.replace", dict(side_effect=replace)),
            ("execution.load_backend", dict(return_value=(frozen, base))),
            ("database.start", dict(side_effect=start)),
            ("database.stop", dict(side_effect=stop)),
            ("pc_proc.Proc", dict(side_effect=Proc)),
            ("psycopg.connect", dict(side_effect=connect)),
            ("sys.argv", dict(new=["pc_runtime.py", "--block", "0"])),
            (
                "subprocess.run",
                dict(
                    side_effect=AssertionError("Real subprocess prohibited in local runtime checks")
                ),
            ),
            ("sys.stdout", dict(new=__import__("io").StringIO())),
        ]
        for name, kw in patches:
            stack.enter_context(patch(name, **kw))
        stack.enter_context(
            patch.dict(
                os.environ,
                SLURM_JOB_ID="test",
                SLURM_CPUS_PER_TASK="4",
                TORCH_IMAGE_SHA256=C.CONTRACT["runtime"]["image_sha256"],
            )
        )
        if fault in {
            "stream_hash",
            "stream_deadline",
            "stream_interrupt",
            "stream_cap",
            "preflight",
        }:
            import si_stream

            original_framed = si_stream.framed

            def framed(payload, *a, **kw):
                if fault == "preflight":
                    raise RuntimeError("Injected parity preflight failure")
                if len(payload.get("rows", [])) == 40:
                    if fault == "stream_deadline":
                        raise TimeoutError("Injected identity deadline")
                    if fault == "stream_interrupt":
                        raise KeyboardInterrupt("Injected identity interrupt")
                    if fault == "stream_cap":
                        kw["maximum"] = 10
                    elif fault == "stream_hash":
                        raise RuntimeError("Injected identity encoding failure")
                return original_framed(payload, *a, **kw)

            stack.enter_context(patch("si_stream.framed", side_effect=framed))
        if fault == "sampler":
            rewrite(out / "memory-health.json", dict(status="failed"))
        try:
            runtime.main()
        except RuntimeError as exc:
            error = exc
    return dict(
        out=out,
        package=package,
        status=C.read(out / "status.json"),
        error=error,
        opened=opened,
        stopped=stopped,
    )


def stat(pid, start=100, ppid=1):
    values = ["0"] * 37
    values[0] = "S"
    values[1] = str(ppid)
    values[19] = str(start)
    return str(pid) + " (python fixture) " + " ".join(values) + "\n"


def memory_fixture(root, version=2):
    root = root.resolve()
    proc = root / "proc"
    mount = root / "cg"
    leaf = mount / "job/task"
    leaf.mkdir(parents=True)
    (proc / "self").mkdir(parents=True)
    text = "0::/job/task\n" if version == 2 else "4:memory:/job/task\n"
    (proc / "self/cgroup").write_text(text)
    (proc / "self/mountinfo").write_text(
        "1 0 0:1 / "
        + str(mount)
        + " rw - "
        + ("cgroup2 cgroup rw" if version == 2 else "cgroup cgroup rw,memory")
        + "\n"
    )
    for pid in [100, 200]:
        p = proc / str(pid)
        p.mkdir()
        (p / "cgroup").write_text(text)
        (p / "stat").write_text(stat(pid, pid * 10))
        (p / "status").write_text(
            "Pid:\t"
            + str(pid)
            + "\nPPid:\t1\nVmRSS:\t100 kB\nVmHWM:\t200 kB\nNSpid:\t"
            + str(pid)
            + "\n"
        )
    (leaf / "cgroup.procs").write_text("100\n200\n")
    for scope in [leaf, leaf.parent]:
        values = (
            {
                "memory.current": str(2 * 1024**3),
                "memory.peak": str(4 * 1024**3),
                "memory.max": str(32 * 1024**3),
                "memory.stat": "anon 1073741824\nfile 1073741824\nkernel 0\n",
                "memory.events": "oom 0\noom_kill 0\nmax 0\nhigh 0\n",
            }
            if version == 2
            else {
                "memory.usage_in_bytes": str(2 * 1024**3),
                "memory.max_usage_in_bytes": str(4 * 1024**3),
                "memory.limit_in_bytes": str(32 * 1024**3),
                "memory.stat": "rss 1073741824\ncache 1073741824\n",
                "memory.failcnt": "0",
                "memory.oom_control": "oom_kill 0\nunder_oom 0\noom_kill_disable 0\n",
            }
        )
        for n, v in values.items():
            (scope / n).write_text(v)
    if version == 1:
        for p in leaf.parent.iterdir():
            if p.is_file():
                shutil.copyfile(p, mount / p.name)
        (mount / "memory.limit_in_bytes").write_text(str(2**63 - 4096))
    return proc, leaf


def complete_return(root, run_result):
    """Data-only verifier fixture. Full-data/graph/process proofs here are synthetic."""
    from test_memory import memory_case

    run = run_result["out"]
    package = run_result["package"]
    shutil.copyfile(E.SOURCE / "eligibility.json", package / "eligibility.json")
    cfg = C.read(package / "experiment.json")
    cfg["snapshot_identity"] = C.read(E.SOURCE / "experiment.json")["snapshot_identity"]
    rewrite(package / "experiment.json", cfg)
    reseal(package)
    rewrite(
        run / "snapshot-qualified.json",
        dict(
            eligibility_sha256=C.sha(package / "eligibility.json"),
            snapshot_identity=cfg["snapshot_identity"],
            field_map={"m_000000": "total_votes"},
            rows=247286,
        ),
    )
    # Data-only complete-return fixture: full-size count/proofs below are synthetic.
    stream = C.read(run / "identity-stream.json")
    n = 247286
    v = stream["stream"]
    v.update(
        digest=cfg["snapshot_identity"],
        rows=n,
        component_calls=n + 1,
        rows_bytes=n * 10000,
        max_row_bytes=10000,
        separator_bytes=n - 1,
        max_pending_bytes=65536,
    )
    v["total_bytes"] = sum(
        v[k] for k in ("rows_bytes", "fields_bytes", "separator_bytes", "framing_bytes")
    )
    v["hash_updates"] = (v["total_bytes"] + 65535) // 65536
    rewrite(run / "identity-stream.json", stream)
    campaign = root / (C.PREFIX + "20261028T010000Z.fixture")
    campaign.mkdir()
    destination = campaign / "run"
    shutil.move(str(run), destination)
    run = destination
    context, base_rows, summary, _, _ = memory_case(root / "memory-fixture")
    phases = C.lines(run / "phases.jsonl")
    begin = phases[0]["time_ns"] - 10**9
    end = phases[-1]["time_ns"] + 2 * 10**9
    rows = []
    tick = begin
    while tick <= end:
        row = copy.deepcopy(base_rows[0])
        row.update(
            start_ns=tick,
            end_ns=tick + 1000,
            phase="host_preflight",
            file_reads=(len(rows) + 1) * 50,
            bytes_read=(len(rows) + 1) * 500,
        )
        prior = [p for p in phases if p["time_ns"] <= tick]
        if prior:
            row["phase"] = prior[-1]["phase"]
        row["processes"].append(
            dict(pid=777, starttime=9990, namespace_pids=[777, 999], VmRSS=100, VmHWM=200)
        )
        rows.append(row)
        tick += 10**9
    (run / "memory.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    summary.update(
        samples=len(rows),
        raw_bytes=(run / "memory.jsonl").stat().st_size,
        file_reads=rows[-1]["file_reads"],
        bytes_read=rows[-1]["bytes_read"],
    )
    rewrite(run / "memory-summary.json", summary)
    rewrite(run / "memory-context.json", context)
    rewrite(
        run / "host-launch.json",
        dict(host_python="/usr/bin/python3.12", step_export="ALL", python_no_bytecode="1"),
    )
    rewrite(
        run / "host-exit.json",
        dict(
            exit_code=0,
            protected_sources_unchanged=True,
            job_id="42",
            array_job_id="42",
            array_task_id="0",
        ),
    )
    for name in ["protected-source-before.json", "protected-source-after.json"]:
        rewrite(run / name, dict(synthetic=True))
    rewrite(campaign / "protected-source-before.json", dict(synthetic=True))
    rewrite(
        campaign / "submission.json",
        dict(
            package_manifest_sha256=C.sha(package / "manifest.json"),
            campaign="/home/dar579/torch-reviews-results/" + campaign.name,
            counts=C.COUNTS,
            jobs={"block-0": "42"},
            dispatch={"block-0": dict(status="submitted", job_id="42")},
            host_python="/usr/bin/python3.12",
        ),
    )
    rewrite(
        campaign / "scheduler-evidence.json",
        dict(sacct_stdout="42_0|COMPLETED|0:0|00:20:00|4|32G|\n", terminal_verified=True),
    )
    relock(run)
    return campaign, package


def relock(run):
    guest = {
        str(p.relative_to(run)): C.sha(p)
        for p in run.rglob("*")
        if p.is_file()
        and p.name not in ["LOCK.json", "HOST-LOCK.json", "job-exit.json"]
        and not p.name.startswith(("memory", "host-", "protected-source-"))
    }
    rewrite(run / "LOCK.json", dict(complete=True, files=guest))
    host = {
        str(p.relative_to(run)): C.sha(p)
        for p in run.rglob("*")
        if p.is_file() and p.name != "HOST-LOCK.json"
    }
    rewrite(run / "HOST-LOCK.json", dict(complete=True, files=host))
