"""New bridge wiring plus serial owned native children; legacy runners untouched."""

import os
import subprocess
import sys
import time
from pathlib import Path

from nh_common import HERE
from nh_lifecycle import stop_owned
from nh_runner import LocalRunner
from ni_groups import LinuxGroups


class Wiring:
    def runtime(self, end, profile="local"):
        c = self.context
        self.execute(
            "runtime",
            HERE / "ni_runtime.py",
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
        self.execute(label, bridge / "ni_bridge.py", args, cap, end)


class IntegratedLocal(Wiring, LocalRunner):
    pass


class IntegratedNative(Wiring):
    def __init__(self, context, store, owner, python=sys.executable):
        self.context, self.store, self.owner, self.python = context, store, owner, str(python)
        self.groups = None
        self.child = None
        self.handle = None
        self.records = {}
        self.allowed = None

    def audit(self, event, args):
        if event in ("socket.connect", "socket.bind"):
            raise RuntimeError("Scientific network prohibited")
        if event == "subprocess.Popen":
            argv = tuple(map(str, args[1]))
            if self.allowed != argv:
                raise RuntimeError("Unplanned scientific process")
            self.allowed = None

    def execute(self, label, script, args, cap, end):
        if self.child is not None:
            raise RuntimeError("One live scientific child required")
        began = time.monotonic()
        deadline = min(end, began + cap)
        argv = [self.python, "-B", str(script), *map(str, args)]
        self.groups = LinuxGroups(
            self.owner.lease, self.store, deadline, self.owner.cleanup_end, self.python
        )
        # Guardian launches the exact permitted original science command after registration.
        self.allowed = tuple(
            [self.python, "-B", str(HERE / "ni_guardian.py"), "FD", "FD", str(deadline), "FD"]
        )
        self.groups.spawn_audit = lambda value: setattr(self, "allowed", tuple(value))
        with (Path(self.context["science"]) / (label + ".log")).open("x") as log:
            self.child, self.handle = self.groups.spawn(
                argv,
                stdout=log,
                stderr=subprocess.STDOUT,
                env={**os.environ, "TMPDIR": str(Path(self.context["work"]) / "tmp")},
            )
            while self.child.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Original scientific phase deadline")
                self.store.budget()
                time.sleep(0.1)
            code = self.child.returncode
            record = {
                "pid": self.child.pid,
                "exit_code": code,
                "owned_child_stopped": True,
                "wall_seconds": time.monotonic() - began,
                "cap_seconds": cap,
            }
            self.groups.finish(self.handle)
            self.records[label] = record
            self.child = None
            self.handle = None
            if code:
                raise RuntimeError("Original suite failed: " + label)

    def stop(self, end=None):
        if self.groups is None or self.child is None:
            return
        if end is None:
            raise RuntimeError("Original cleanup endpoint required")
        stop_owned(self.groups, self.handle, self.child, end)
        self.groups.finish(self.handle)
        self.child = None
        self.handle = None
