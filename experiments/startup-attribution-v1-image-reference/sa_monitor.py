"""Local LINE monitoring of two unchanged code objects; never retain frames."""

import ast
import hashlib
import inspect
import sys
import threading
import time
from pathlib import Path

TOOL = 4
MAPS = (
    {
        970: "S00.producer_entry",
        982: "S01.execute_before",
        983: "S02.result_received",
        992: "S12.constructor_complete",
    },
    {
        23: "S05.constructor_entry",
        54: "S05a.matrix_before",
        55: "S06.matrix_ready",
        57: "S07.finite_complete",
        61: "S08.norm_complete",
        89: "S09.metadata_ready",
    },
)
EXPECTED = (
    "bc743c14178dbe30ab705dc790db20fc7b045e4c30395e2488da21ab6266834d",
    "0ebac2227ab66c07b7b1271c6aeb294a9061329e6d2817c52dadb63c9b9cf4fa",
)


def idle():
    if sys.version_info[:2] != (3, 12) or not hasattr(sys, "monitoring"):
        raise RuntimeError("CPython3.12 monitoring required")
    if sys.gettrace() or sys.getprofile():
        raise RuntimeError("Pre-existing tracing/profile")
    for tool in range(6):
        if sys.monitoring.get_tool(tool) is not None or sys.monitoring.get_events(tool):
            raise RuntimeError("Pre-existing monitoring")
    if len(threading.enumerate()) != 1:
        raise RuntimeError("Concurrent Python activity")


def metadata(frame):
    values = frame.f_locals
    out = {}
    rows = values.get("rows")
    if type(rows) is list:
        out["rows"] = len(rows)
    vectors = values.get("vectors")
    if vectors is not None:
        out["matrix"] = dict(
            shape=list(vectors.shape), dtype=str(vectors.dtype), nbytes=vectors.nbytes
        )
    # Scalar aliases only, no object reference escapes.
    return out


class SnapshotMonitor:
    def __init__(self, producer, constructor, obs, source_hashes=None):
        self.functions = producer, constructor
        self.codes = tuple(f.__code__ for f in self.functions)
        self.obs = obs
        self.maps = dict(zip(self.codes, MAPS, strict=True))
        self.source_hashes = source_hashes
        self.seen = set()
        self.active = False
        self.owner = threading.get_ident()
        self.cursor = None
        self.originals = self.codes

    def validate(self):
        for index, f in enumerate(self.functions):
            p = Path(inspect.getsourcefile(f)).resolve()
            text = self.obs.read_file(p)
            source_hash = hashlib.sha256(text.encode()).hexdigest()
            expected = self.source_hashes[index] if self.source_hashes else EXPECTED[index]
            if source_hash != expected:
                raise RuntimeError("Original monitored source changed: " + str(p))
            tree = ast.parse(text)
            nodes = [
                n
                for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef)
                and n.name == f.__name__
                and n.lineno == f.__code__.co_firstlineno
            ]
            if len(nodes) != 1:
                raise RuntimeError("Original function/AST mismatch")
            lines = {line for _, _, line in f.__code__.co_lines()}
            statements = {n.lineno for n in ast.walk(nodes[0]) if isinstance(n, ast.stmt)}
            if not set(MAPS[index]).issubset(lines & statements):
                raise RuntimeError("Original AST/line table mapping mismatch")

    def callback(self, code, line):
        with self.obs.charge():
            self.obs.callback(line=True)
            if threading.get_ident() != self.owner or code not in self.maps:
                raise RuntimeError("Concurrent/unknown monitored code")
            frame = sys._getframe(1)
            if frame.f_code is not code:
                raise RuntimeError("Monitoring frame/code mismatch")
            ident = self.maps[code].get(line)
            if ident and ident not in self.seen:
                if ident == "S00.producer_entry" and frame.f_locals["self"]._snapshot is not None:
                    raise RuntimeError("Snapshot already cached")
                if ident == "S02.result_received":
                    wrapped = frame.f_locals["cursor"]
                    self.cursor = getattr(wrapped, "raw", wrapped)
                self.obs.checkpoint(ident, metadata(frame))
                self.seen.add(ident)
            return sys.monitoring.DISABLE

    def __enter__(self):
        idle()
        for tool in range(6):
            if any(sys.monitoring.get_local_events(tool, c) for c in self.codes):
                raise RuntimeError("Pre-existing local monitoring mask")
        self.validate()
        m = sys.monitoring
        try:
            m.use_tool_id(TOOL, "startup-attribution.v1")
            self.active = True
            previous = m.register_callback(TOOL, m.events.LINE, self.callback)
            if previous is not None:
                m.register_callback(TOOL, m.events.LINE, previous)
                m.free_tool_id(TOOL)
                self.active = False
                raise RuntimeError("Pre-existing callback on unused tool")
            for c in self.codes:
                if m.get_local_events(TOOL, c):
                    raise RuntimeError("Unexpected local monitor mask")
                m.set_local_events(TOOL, c, m.events.LINE)
            return self
        except BaseException:
            self.restore()
            raise

    def cursor_close(self, cursor, original, *args, **kwargs):
        if cursor is not self.cursor:
            return original(cursor, *args, **kwargs)
        self.cursor = None  # don't retain the cursor after its original close
        frame = sys._getframe(1)
        while frame is not None and frame.f_code is not self.codes[0]:
            frame = frame.f_back
        if frame is None:
            raise RuntimeError("Snapshot close outside original producer")
        error = None
        try:
            self.obs.checkpoint("S03.decoded_before_close", metadata(frame))
        except BaseException as exc:
            error = exc
        # Original resource release must run even if observing it failed.
        result = original(cursor, *args, **kwargs)
        if error:
            raise error
        self.obs.checkpoint("S04.cursor_closed", metadata(frame))
        return result

    def restore(self):
        if not self.active:
            return
        m = sys.monitoring
        errors = []
        for c in self.codes:
            try:
                m.set_local_events(TOOL, c, 0)
            except BaseException as exc:
                errors.append(type(exc).__name__)
        m.set_events(TOOL, 0)
        m.register_callback(TOOL, m.events.LINE, None)
        m.free_tool_id(TOOL)
        self.active = False
        self.cursor = None
        if errors or any(m.get_local_events(TOOL, c) for c in self.codes):
            raise RuntimeError("Monitoring restore failure")
        if tuple(f.__code__ for f in self.functions) != self.originals:
            raise RuntimeError("Original monitored bindings changed")
        idle()

    def __exit__(self, *args):
        with self.obs.charge():
            self.restore()


def preflight(obs):
    """Two literals only; no SQL/data arrays; no restart/global monitoring."""
    idle()
    started = time.process_time()

    def first():
        value = 1
        return value

    def second():
        value = 2
        return value

    codes = first.__code__, second.__code__
    calls = 0

    def callback(code, line):
        nonlocal calls
        calls += 1
        obs.callback(line=True)
        if calls > 16 or sys._getframe(1).f_code is not code or code not in codes:
            raise RuntimeError("Literal monitoring capability failed")
        return sys.monitoring.DISABLE

    m = sys.monitoring
    m.use_tool_id(TOOL, "startup-attribution.preflight")
    previous = m.register_callback(TOOL, m.events.LINE, callback)
    if previous is not None:
        m.register_callback(TOOL, m.events.LINE, previous)
        m.free_tool_id(TOOL)
        raise RuntimeError("Pre-existing callback on unused tool")
    try:
        for code in codes:
            m.set_local_events(TOOL, code, m.events.LINE)
        if (first(), second()) != (1, 2) or calls == 0:
            raise RuntimeError("Literal monitoring inactive")
    finally:
        for code in codes:
            m.set_local_events(TOOL, code, 0)
        m.set_events(TOOL, 0)
        m.register_callback(TOOL, m.events.LINE, None)
        m.free_tool_id(TOOL)
    idle()
    if time.process_time() - started > 1:
        raise RuntimeError("Literal preflight CPU ceiling")
    return dict(events=calls, restored=True)
