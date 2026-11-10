"""Bounded diagnostic evidence. No SQL, values, arrays, GC, or content inventories."""

import contextlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from pc_common import HERE, read

DESIGN = read(HERE / "ATTRIBUTION-DESIGN.json")
LIMITS = DESIGN["diagnostic_limits"]
CATALOG = {r["id"]: r["scope"] for r in read(HERE / "CHECKPOINTS.json")["checkpoints"]}


class Observation:
    def __init__(self, out, scope, probe):
        self.scope, self.probe = scope, probe
        # Conservative host/runtime partition of the SAME frozen aggregate budget.
        self.caps = (
            dict(
                cpu=3,
                wall=6,
                reads=1024,
                read_bytes=8 * 1024**2,
                raw=2 * 1024**2,
                roles=32,
                entries=5000,
            )
            if scope == "host"
            else dict(
                cpu=12,
                wall=24,
                reads=7168,
                read_bytes=56 * 1024**2,
                raw=14 * 1024**2,
                roles=224,
                entries=45000,
            )
        )
        self.out = Path(out)
        self.path = self.out / ("attribution-" + scope + ".jsonl")
        self.handle = self.path.open("xb")
        self.pending = bytearray()
        self.bytes = self.cpu = self.wall = self.depth = 0
        self.reads = self.read_bytes = self.callbacks = self.lines = 0
        self.roles = self.entries = 0
        self.counts = Counter()
        self.seen = set()
        self.invalid = []
        self.closed = False

    @contextlib.contextmanager
    def charge(self, enforce=True):
        outer = self.depth == 0
        if outer:
            c, w = time.process_time(), time.monotonic()
        self.depth += 1
        try:
            yield
        finally:
            self.depth -= 1
            if outer:
                self.cpu += time.process_time() - c
                self.wall += time.monotonic() - w
                if enforce and (self.cpu > self.caps["cpu"] or self.wall > self.caps["wall"]):
                    raise RuntimeError("Diagnostic overhead ceiling")

    def callback(self, line=False):
        self.callbacks += 1
        self.lines += int(line)
        if self.callbacks > LIMITS["hook_enter_exit_callbacks"] or self.lines > 512:
            raise RuntimeError("Diagnostic callback ceiling")

    def record(self, kind, value, emergency=False):
        with self.charge(enforce=not emergency):
            data = (
                json.dumps(dict(kind=kind, **value), sort_keys=True, allow_nan=False).encode()
                + b"\n"
            )
            cap = LIMITS["record_bytes"].get(kind, LIMITS["record_bytes"]["summary"])
            reserve = 0 if emergency else LIMITS["minimal_failure_reserve_bytes"]
            if len(data) > cap or self.bytes + len(data) > self.caps["raw"] - reserve:
                raise RuntimeError("Diagnostic record/raw ceiling")
            if len(self.pending) + len(data) > LIMITS["pending_writer_bytes"]:
                self.flush()
            self.pending.extend(data)
            self.bytes += len(data)

    def flush(self):
        if self.pending:
            self.handle.write(self.pending)
            self.pending.clear()
        self.handle.flush()  # no per-fetch fsync

    def checkpoint(self, ident, metadata=None):
        with self.charge():
            start = time.monotonic_ns()
            if CATALOG.get(ident) != self.scope or ident in self.seen or len(self.seen) >= 128:
                raise RuntimeError("Unknown/duplicate/excess checkpoint: " + ident)
            value = self.probe(self)
            end = time.monotonic_ns()
            if end - start > 10**9:
                raise RuntimeError("Synchronous checkpoint deadline")
            self.record(
                "checkpoint",
                dict(
                    id=ident,
                    seq=len(self.seen),
                    start_ns=start,
                    end_ns=end,
                    sample=value,
                    metadata=metadata or {},
                ),
            )
            self.seen.add(ident)

    def cleanup_checkpoint(self, ident):
        try:
            self.checkpoint(ident)
        except BaseException as exc:
            self.invalid.append(type(exc).__name__)

    @contextlib.contextmanager
    def boundary(self, ident, role=None):
        self.checkpoint(ident + ".before")
        start = time.monotonic_ns()
        result = {}
        try:
            yield result
        except BaseException:
            raise
        else:
            self.checkpoint(ident + ".after")
            if role:
                self.role(role, start, time.monotonic_ns(), **result)

    def role(self, role, start, end, logical_bytes=None, entries=0, parent=None):
        with self.charge():
            self.roles += 1
            self.entries += entries
            if self.roles > self.caps["roles"] or self.entries > self.caps["entries"]:
                raise RuntimeError("Role/metadata ceiling")
            self.record(
                "role",
                dict(
                    role=role,
                    start_ns=start,
                    end_ns=end,
                    logical_bytes=logical_bytes,
                    parent=parent,
                    entries=entries,
                    unavailable_reason=None
                    if logical_bytes is not None
                    else "original operation supplies no byte count",
                    physical_io="not measured",
                ),
            )

    def read_file(self, path, optional=False):
        with self.charge():
            if self.reads >= self.caps["reads"]:
                raise RuntimeError("Diagnostic read/stat ceiling")
            self.reads += 1
            try:
                with Path(path).open("rb") as h:
                    data = h.read(65537)
            except (FileNotFoundError, PermissionError):
                if optional:
                    return None
                raise
            self.read_bytes += len(data)
            if len(data) > 65536 or self.read_bytes > self.caps["read_bytes"]:
                raise RuntimeError("Diagnostic read-byte ceiling")
            return data.decode()

    def finish(self, complete):
        if self.closed:
            return
        try:
            required = {n for n, s in CATALOG.items() if s == self.scope}
            if complete and self.invalid:
                raise RuntimeError("Observer invalidity prevents completion")
            if complete and self.seen != required:
                raise RuntimeError(
                    "Missing required checkpoints: " + str(sorted(required - self.seen))
                )
            self.record(
                "summary",
                dict(
                    complete=complete,
                    checkpoints=len(self.seen),
                    cpu_seconds=self.cpu,
                    wall_seconds=self.wall,
                    file_reads=self.reads,
                    read_bytes=self.read_bytes,
                    callbacks=self.callbacks,
                    line_callbacks=self.lines,
                    role_records=self.roles,
                    metadata_entries=self.entries,
                    invalid=self.invalid,
                ),
                emergency=True,
            )
            self.flush()
            os.fsync(self.handle.fileno())
        finally:
            self.handle.close()
            self.closed = True


class Probe:
    """Read three Slurm scopes and this process only; no additional inventory."""

    def __init__(self, arrow=None, proc=Path("/proc")):
        self.arrow, self.proc = arrow, Path(proc)
        self.memory = None
        self.starttime = None
        self.mapping = None

    def __call__(self, obs):
        from pc_proc import fields, parse_stat
        from sr_memory import Memory, membership, resolve_scope

        def get(path, optional=False):
            return obs.read_file(path, optional)

        pid = os.getpid()
        group = get(self.proc / "self/cgroup")
        if self.memory is None:
            self.mapping = resolve_scope(group, get(self.proc / "self/mountinfo"))
            paths = [Path(p) for p in self.mapping["ancestors"]]
            jobs = [p for p in paths if p.name == "job_" + os.environ["SLURM_JOB_ID"]]
            users = [p for p in paths if p.name == "user" and p.parent.name.startswith("step_")]
            tasks = [p for p in paths if p.name.startswith("task_")]
            if len(jobs) != 1 or len(users) != 1 or len(tasks) != 1:
                raise RuntimeError("Three unambiguous Slurm scopes required")
            self.paths = dict(job=jobs[0], step_user=users[0], task=tasks[0])
            # Use the qualified read-only scope parser, without sampler initialization/scans.
            self.memory = object.__new__(Memory)
            self.memory.context = self.mapping
            self.memory.previous_events, self.memory.previous_peaks = {}, {}
            self.memory.read = type("Reader", (), {"read": staticmethod(get)})()
        if membership(group) != (
            self.mapping["version"],
            __import__("pathlib").PurePosixPath(self.mapping["membership"]),
        ):
            raise RuntimeError("Diagnostic cgroup changed")
        stat = parse_stat(get(self.proc / "self/stat"))
        if self.starttime is None:
            self.starttime = stat["starttime"]
        if stat["starttime"] != self.starttime:
            raise RuntimeError("Diagnostic process identity changed")
        status = fields(get(self.proc / "self/status"))
        scopes = {n: self.memory.scope(p) for n, p in self.paths.items()}
        for s in scopes.values():
            if s["peak"] is None or s["component_coverage"] != "anon_file_kernel":
                raise RuntimeError("Required memory components unavailable")
        pool = None
        if self.arrow:
            pool = self.arrow.default_memory_pool()
            live, backend = pool.bytes_allocated(), pool.backend_name
            if not isinstance(live, int) or live < 0 or not isinstance(backend, str):
                raise RuntimeError("Required Arrow pool capability unavailable")
            pool = dict(live_bytes=live, backend=backend, high_water_bytes=pool.max_memory())
        smaps = get(self.proc / "self/smaps_rollup", True)
        return dict(
            pid=pid,
            starttime=self.starttime,
            scopes=scopes,
            process=dict(
                stat=stat,
                rss=status.get("VmRSS"),
                hwm=status.get("VmHWM"),
                io=get(self.proc / "self/io"),
            ),
            arrow=pool,
            arrow_unavailable_reason=None
            if pool
            else "host interpreter; runtime pool recorded separately",
            smaps_rollup=smaps,
            smaps_unavailable_reason=None if smaps else "missing or denied",
            python_allocated_blocks=sys.getallocatedblocks(),
            sampling="sequential read window",
        )
