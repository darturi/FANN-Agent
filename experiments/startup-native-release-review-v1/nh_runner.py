"""Owned local Python children only; no native/container/scheduler backend."""

import os
import subprocess
import time
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None  # Target runner below uses only Linux procfs and the standard library.
from nh_binding import require_native_admission
from nh_common import HERE, closed_native, executable_identity, save
from nh_lifecycle import require_groups, stop_owned


class LocalRunner:
    def __init__(self, context, store, python, progress=lambda label: None):
        self.context, self.store, self.python, self.progress = context, store, str(python), progress
        if psutil is None:
            raise RuntimeError("Local observer unavailable; no fallback")
        self.python_identity = executable_identity(self.python)
        self.child = None
        self.records = {}
        self.memory = {"samples": 0, "peak_parent_plus_child_bytes": 0}
        self.allowed = None

    def audit(self, event, args):
        if event in ("socket.connect", "socket.bind"):
            raise RuntimeError("Offline integration network prohibited")
        if event == "subprocess.Popen":
            if self.allowed is None or tuple(map(str, args[1])) != self.allowed:
                raise RuntimeError("Unscheduled local process prohibited")
            self.allowed = None

    def stop(self, end=None):
        if self.child is not None and self.child.poll() is None:
            self.child.terminate()
            try:
                self.child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.child.kill()
                self.child.wait(timeout=5)
        if self.child is not None and self.child.poll() is None:
            raise RuntimeError("Owned child remains live")
        self.child = None

    def execute(self, label, script, args, cap, end):
        if self.child is not None:
            raise RuntimeError("Concurrent test children prohibited")
        self.progress(label)
        begin = time.monotonic()
        deadline = min(begin + cap, end)
        argv = [self.python, "-B", str(script), *map(str, args)]
        self.allowed = tuple(argv)
        if executable_identity(self.python) != self.python_identity:
            raise RuntimeError("Child interpreter identity changed")
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(Path(self.context["work"]) / "tmp"),
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
        with (Path(self.context["science"]) / (label + ".log")).open("x") as log:
            self.child = subprocess.Popen(
                argv, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True
            )
            proc = self.child
            pid = proc.pid
            save(
                Path(self.context["science"]) / (label + "-pid.json"),
                {"pid": pid, "started": begin},
            )
            try:
                owned = psutil.Process(pid)
                parent = psutil.Process()
                while proc.poll() is None:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Original phase deadline: " + label)
                    try:
                        rss = owned.memory_info().rss + parent.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError) as e:
                        try:
                            proc.wait(timeout=max(0.001, min(0.25, deadline - time.monotonic())))
                        except subprocess.TimeoutExpired:
                            raise RuntimeError("Live local RSS missing") from e
                        if proc.returncode:
                            raise RuntimeError("Failed exit at RSS race") from e
                    else:
                        self.memory["samples"] += 1
                        self.memory["peak_parent_plus_child_bytes"] = max(
                            self.memory["peak_parent_plus_child_bytes"], rss
                        )
                        if rss + 4 * 1024**3 > 32 * 1024**3:
                            raise RuntimeError("Original32GiB RSS+reserve guard exceeded locally")
                    self.store.budget()
                    time.sleep(0.1)
                if proc.returncode:
                    raise RuntimeError("Original suite child failed: " + label)
            finally:
                self.stop()
                self.records[label] = {
                    "pid": pid,
                    "exit_code": proc.returncode,
                    "owned_child_stopped": proc.poll() is not None,
                    "wall_seconds": time.monotonic() - begin,
                    "cap_seconds": cap,
                }
        self.store.budget()

    def runtime(self, end, profile="local"):
        c = self.context
        self.execute(
            "runtime",
            HERE / "nh_runtime.py",
            [
                "--inner",
                c["inner"],
                "--workspace",
                c["workspace"],
                "--out",
                Path(c["science"]) / "runtime.json",
                "--profile",
                profile,
            ],
            30,
            end,
        )

    def suite(self, label, kind, source, phase, cap, end, candidate=None):
        c = self.context
        args = [
            "--inner",
            c["inner"],
            "--workspace",
            c["workspace"],
            "--source",
            source,
            "--out",
            Path(c["science"]) / label,
            "--kind",
            kind,
            "--phase",
            phase,
            "--profile",
            c.get("profile", "local"),
        ]
        if candidate:
            args += ["--candidate", candidate]
        bridge = Path(c.get("bridge_snapshot", HERE)) if label.endswith("sealed") else HERE
        self.execute(label, bridge / "nh_bridge.py", args, cap, end)

    def native(self, *args, **kwargs):
        closed_native()


class NativeRunner(LocalRunner):
    """Target process path exists but cannot be entered without a future release."""

    def __init__(self, context, store, python, progress=lambda label: None):
        closed_native()
        require_native_admission(context)
        self.process_control = require_groups(context)
        self.owned_handle = None
        self.context, self.store, self.python, self.progress = context, store, str(python), progress
        self.python_identity = executable_identity(self.python)
        self.child = None
        self.records = {}
        self.allowed = None

    def execute(self, label, script, args, cap, end):
        closed_native()
        require_native_admission(self.context)
        if require_groups(self.context) is not self.process_control:
            raise RuntimeError("Owned controller changed")
        if self.child is not None:
            raise RuntimeError("One test child required")
        begin = time.monotonic()
        deadline = min(begin + cap, end)
        if executable_identity(self.python) != self.python_identity:
            raise RuntimeError("Target interpreter changed")
        argv = [self.python, "-B", str(script), *map(str, args)]
        self.allowed = tuple(argv)
        self.progress(label)
        with (Path(self.context["science"]) / (label + ".log")).open("x") as log:
            self.child, self.owned_handle = self.process_control.spawn(
                argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
            )
            proc = self.child
            save(
                Path(self.context["science"]) / (label + "-pid.json"),
                {"pid": proc.pid, "started": begin},
            )
            try:
                while proc.poll() is None:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Original target phase deadline")
                    self.store.budget()
                    time.sleep(0.1)
                if proc.returncode:
                    raise RuntimeError("Target child failed")
            finally:
                self.stop(end)
                self.records[label] = {
                    "pid": proc.pid,
                    "exit_code": proc.returncode,
                    "owned_child_stopped": proc.poll() is not None,
                    "wall_seconds": time.monotonic() - begin,
                    "cap_seconds": cap,
                }

    def stop(self, end=None):
        if self.child is None:
            return
        if end is None:
            raise RuntimeError("Existing phase/cleanup endpoint required")
        stop_owned(self.process_control, self.owned_handle, self.child, end)
        self.child = None
        self.owned_handle = None
