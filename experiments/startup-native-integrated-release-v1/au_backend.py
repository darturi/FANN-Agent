"""Concrete Linux guardian controller, isolated from all closed native adapters."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from au_authority import Lease
from au_kernel import digest
from au_wire import Pipe
from nh_common import executable_identity, save, sha
from nh_lifecycle import OwnedGroups

HERE = Path(__file__).resolve().parent


class Handle:
    pass


class OwnedProcess:
    """Popen-like status preserves science exit separately from guardian proof."""

    def __init__(self, controller):
        self.controller = controller
        self.pid = controller.process.pid
        self.token = controller.active
        self.guardian = controller.process
        self.end = controller.cleanup_end
        self.code = None

    def poll(self):
        c = self.controller
        if self.code is not None:
            return self.code
        if c.active is not self.token:
            raise RuntimeError("Stale process handle cannot observe a new child")
        if c.members(self.token):
            return None
        self.code = c.proof["direct_exit_code"]
        return self.code

    @property
    def returncode(self):
        return self.poll()

    def wait(self, timeout=None):
        end = self.end
        if timeout is not None:
            end = min(end, time.monotonic() + timeout)
        while time.monotonic() < end:
            code = self.poll()
            if code is not None:
                self.guardian.wait(timeout=max(0.001, end - time.monotonic()))
                return code
            time.sleep(0.02)
        raise subprocess.TimeoutExpired("owned guardian", timeout)


class LinuxGroups(OwnedGroups):
    def __init__(self, lease, store, work_end, cleanup_end, python=sys.executable):
        if type(lease) is not Lease:
            raise RuntimeError("Live same-process authority capability required")
        grant = lease.check()
        if (
            any(type(v) not in (int, float) for v in (work_end, cleanup_end))
            or not time.monotonic() < work_end <= cleanup_end <= grant["cleanup_deadline"]
            or work_end > grant["work_deadline"]
        ):
            raise ValueError("Existing caller endpoints required")
        self.lease, self.store, self.work_end, self.cleanup_end = (
            lease,
            store,
            work_end,
            cleanup_end,
        )
        self.kernel = lease._owner.kernel
        self.python = str(python)
        self.python_id = executable_identity(self.python)
        self.pins = {
            str(HERE / name): sha(HERE / name)
            for name in (
                "au_guardian.py",
                "au_exec.py",
                "au_kernel.py",
                "au_wire.py",
                "au_budget.py",
            )
        }
        self.active = None
        self.channel = None
        self.process = None
        self.proof = None
        self.fd = None
        self.last_members = ()
        self.failures = []
        self.actions = 0

    def validate(self, context):
        grant = self.lease.check()
        if context.get("binding_sha256") != grant["binding_sha256"]:
            raise RuntimeError("Controller binding differs")
        return True

    def spawn(self, argv, **kwargs):
        grant = self.lease.check(argv)
        if self.active is not None:
            raise RuntimeError("One live owned handle required")
        if kwargs.pop("start_new_session", True) is not True:
            raise ValueError("Independent guardian session required")
        if set(kwargs) - {"stdout", "stderr", "env"}:
            raise ValueError("Unreviewed spawn option")
        if executable_identity(self.python) != self.python_id or any(
            sha(p) != h for p, h in self.pins.items()
        ):
            raise RuntimeError("Pinned guardian/interpreter changed")
        if time.monotonic() >= self.work_end:
            raise TimeoutError("Original spawn endpoint exhausted")
        action = digest(list(argv))
        path = self.lease._owner.root / ("action-" + action + ".claim")
        save(
            path, {"binding": grant["binding_sha256"], "argv_sha256": action, "state": "uncertain"}
        )
        # From this point uncertainty consumes the command. No automatic reuse.
        self.proof = None
        self.failures = []
        self.last_members = ()
        self.actions += 1
        token = Handle()
        self.active = token
        to_read, to_write = os.pipe()
        from_read, from_write = os.pipe()
        self.channel = Pipe(from_read, to_write)
        env = kwargs.pop("env", dict(os.environ))
        env = {
            **env,
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
        identity = {"nonce": grant["nonce"], "binding": grant["binding_sha256"], "action": action}
        self.identity = identity
        try:
            self.process = subprocess.Popen(
                [
                    self.python,
                    "-B",
                    str(HERE / "au_guardian.py"),
                    str(to_read),
                    str(from_write),
                    str(self.work_end),
                    str(self.kernel.budget.fd),
                ],
                pass_fds=(to_read, from_write, self.kernel.budget.fd),
                close_fds=True,
                start_new_session=True,
                env=env,
                **kwargs,
            )
        finally:
            os.close(to_read)
            os.close(from_write)
        try:
            self.fd, self.guardian = self.kernel.pin(self.process.pid)
            self.channel.send(
                {
                    "identity": identity,
                    "argv": list(argv),
                    "env": env,
                    "work_end": self.work_end,
                    "cleanup_end": self.cleanup_end,
                    "parent_pid": os.getpid(),
                },
                self.work_end,
            )
            prepared = self.channel.receive(self.work_end)
            if (
                prepared.get("identity") != identity
                or prepared.get("kind") != "prepared"
                or prepared["guardian"]["pid"] != self.process.pid
                or prepared["guardian"]["start"] != self.guardian["start"]
                or prepared["child"]["ppid"] != self.process.pid
            ):
                raise RuntimeError("Atomic registration handshake differs")
            self.lease.check(argv)
            self.child = prepared["child"]
            self.channel.send({"kind": "release", "identity": identity}, self.work_end)
            running = self.channel.receive(self.work_end)
            if running != {"kind": "running", "identity": identity, "child_pid": self.child["pid"]}:
                raise RuntimeError("Blocked exec release missing")
            self.store.json(
                "owned-" + action[:12] + ".json",
                {
                    "guardian": self.guardian,
                    "child": self.child,
                    "identity": identity,
                    "atomic_registration": True,
                },
            )
            if time.monotonic() >= self.work_end:
                raise TimeoutError("Registration publication exceeded original endpoint")
            return OwnedProcess(self), token
        except BaseException:
            # Preserve uncertain ownership. Pipe EOF makes guardian attempt its
            # bounded cleanup; never claim stopped from an unregistered PID.
            self.channel.close()
            raise

    def _handle(self, handle):
        if handle is not self.active or self.process is None:
            raise RuntimeError("Foreign, stale or uncertain owned handle")
        try:
            self.lease.check(cleanup=True)
        except BaseException:
            self.abort()
            raise

    def drain(self):
        while True:
            try:
                row = self.channel.receive(self.cleanup_end, wait=False)
            except EOFError:
                break
            if row is None:
                break
            if row.get("identity") != self.identity:
                raise RuntimeError("Foreign guardian proof")
            if row["kind"] == "terminal":
                if self.proof is not None:
                    raise RuntimeError("Repeated terminal proof")
                self.proof = row["proof"]
            elif row["kind"] == "failure":
                self.failures.append({**row["error"], "cleanup": row.get("cleanup")})
            elif row["kind"] == "status":
                self.last_members = tuple(row["members"])
            else:
                raise RuntimeError("Unexpected guardian state")

    def members(self, handle):
        self._handle(handle)
        self.store.budget()
        self.drain()
        code = self.process.poll()
        if code is None:
            actual = self.kernel.process(self.process.pid)
            if any(actual[k] != self.guardian[k] for k in ("pid", "start", "uid", "cgroup")):
                raise RuntimeError("Guardian identity lost")
            # Always keep the guardian live in the membership set until its
            # successful exit and terminal ECHILD proof both reconcile.
            return (self.process.pid,)
        self.drain()
        if (
            code != 0
            or self.failures
            or self.proof is None
            or self.proof.get("complete") is not True
            or self.proof.get("kernel_ECHILD") is not True
            or self.proof.get("tracked_live") != 0
            or self.proof["finished"] >= self.cleanup_end
        ):
            raise RuntimeError("Guardian/whole-tree shutdown incomplete")
        return ()

    def send(self, handle, number):
        self._handle(handle)
        if number not in (signal.SIGTERM, signal.SIGKILL):
            raise ValueError("Only original shutdown signals permitted")
        if self.members(handle):
            self.channel.send(
                {"kind": "signal", "identity": self.identity, "number": int(number)},
                self.cleanup_end,
            )

    def finish(self, handle):
        if self.members(handle):
            raise RuntimeError("Owned descendants still live")
        self.process.wait(timeout=max(0.001, self.cleanup_end - time.monotonic()))
        if self.process.returncode != 0:
            raise RuntimeError("Independent guardian exit failed")
        proof = self.proof
        if time.monotonic() >= self.cleanup_end:
            raise TimeoutError("Original terminal publication endpoint exhausted")
        self.store.json("terminal-" + self.identity["action"][:12] + ".json", proof)
        if time.monotonic() >= self.cleanup_end:
            raise TimeoutError("Terminal publication exceeded original endpoint")
        self.channel.close()
        os.close(self.fd)
        self.active = None
        return proof

    def abort(self):
        """No new authority: close our pipe; retain uncertainty and owned handle."""
        if self.channel is not None:
            self.channel.close()
        if self.process is not None:
            remaining = min(15, self.cleanup_end - time.monotonic())
            if remaining > 0:
                try:
                    self.process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    pass
