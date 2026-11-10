"""Linux subreaper; absence is proved by waitpid ECHILD, never proc enumeration."""

import ctypes
import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

from au_wire import Pipe
from ni_site import ScopedKernel as LinuxKernel


def prctl(option, value):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(option, value, 0, 0, 0):
        raise OSError(ctypes.get_errno(), "Required prctl failed")


def owned(rows, root):
    selected = {}
    parents = {root}
    while True:
        found = {pid: row for pid, row in rows.items() if row["ppid"] in parents and pid != root}
        if not set(found) - set(selected):
            break
        selected.update(found)
        parents.update(found)
        if len(selected) + 1 > 32:
            raise RuntimeError("Original32-process ownership bound exceeded")
    return selected


def fresh_owned(kernel, candidates, root, reference):
    valid = {root}
    result = {}
    for pid, candidate in candidates.items():
        try:
            row = kernel.process(pid)
        except (FileNotFoundError, ProcessLookupError):
            continue
        if row["start"] != candidate["start"] or row["ppid"] not in valid:
            raise RuntimeError("Ownership ancestry or PID generation changed")
        if (row["uid"] != reference["uid"] and not row.get("monitor_only")) or row[
            "cgroup"
        ] != reference["cgroup"]:
            raise RuntimeError("Descendant credentials/scope changed")
        result[pid] = row
        valid.add(pid)
    return result


def verify_exited_descriptor(fd):
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    events = poller.poll(0)
    mask = dict(events).get(fd, 0)
    if not mask & select.POLLIN or mask & select.POLLNVAL:
        raise RuntimeError("ECHILD conflicts with a live/unknown retained descriptor")


def main():
    channel = Pipe(int(sys.argv[1]), int(sys.argv[2]))
    config = channel.receive(float(sys.argv[3]))
    identity = config["identity"]
    end = config["work_end"]
    cleanup = config["cleanup_end"]
    if not time.monotonic() < end <= cleanup:
        raise TimeoutError("Existing endpoints unavailable")
    parent = config["parent_pid"]
    if os.getppid() != parent:
        raise RuntimeError("Original parent missing before registration")
    prctl(36, 1)  # PR_SET_CHILD_SUBREAPER
    stopping = [None]

    def interrupted(number, frame):
        stopping[0] = stopping[0] or time.monotonic()

    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGALRM):
        signal.signal(number, interrupted)
    prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
    if os.getppid() != parent:
        raise RuntimeError("Parent changed during ownership setup")
    kernel = LinuxKernel(
        budget_fd=int(sys.argv[4]),
        scope=config.get("scope"),
        privileged_runtime=config.get("privileged_runtime", False),
    )
    tracked = {}
    direct = None
    direct_code = None
    reaped = []
    error = None
    gate = None
    began = time.monotonic()
    sent = set()
    disconnected = False
    monitored = {}

    def emit(kind, **data):
        if not disconnected:
            channel.send({"kind": kind, "identity": identity, **data}, cleanup)

    try:
        before = kernel.snapshot()
        gate_read, gate = os.pipe()
        try:
            direct = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    str(Path(__file__).with_name("au_exec.py")),
                    str(gate_read),
                    str(end),
                    *config["argv"],
                ],
                pass_fds=(gate_read,),
                close_fds=True,
                env=config["env"],
            )
        finally:
            os.close(gate_read)
        descriptor, row = kernel.pin(direct.pid)
        if (
            row["ppid"] != os.getpid()
            or row["uid"] != os.getuid()
            or row["cgroup"] != before["cgroup"]
        ):
            raise RuntimeError("Unowned blocked child")
        tracked[direct.pid] = (descriptor, row)
        emit("prepared", guardian=kernel.process(os.getpid()), child=row)
        release = channel.receive(end)
        if release != {"kind": "release", "identity": identity}:
            raise RuntimeError("Wrong launch release identity")
        os.write(gate, b"1")
        os.close(gate)
        gate = None
        emit("running", child_pid=direct.pid)
        last = 0
        while True:
            now = time.monotonic()
            if now >= cleanup:
                raise TimeoutError("Original cleanup endpoint exhausted")
            if now >= end:
                stopping[0] = stopping[0] or now
            try:
                request = channel.receive(cleanup, wait=False)
            except (EOFError, BrokenPipeError):
                disconnected = True
                request = None
                stopping[0] = stopping[0] or now
            if request is not None:
                if (
                    request.get("identity") != identity
                    or request.get("kind") != "signal"
                    or request.get("number") not in (int(signal.SIGTERM), int(signal.SIGKILL))
                ):
                    raise RuntimeError("Foreign/invalid control request")
                stopping[0] = stopping[0] or now
                if request["number"] == signal.SIGKILL:
                    stopping[0] = min(stopping[0], now - 10)
            # Full bounded proc census discovers candidates; it is never the
            # authority for an empty tree. Kernel ECHILD below is required.
            rows = fresh_owned(kernel, owned(kernel.census(), os.getpid()), os.getpid(), before)
            for pid, row in rows.items():
                if row.get("monitor_only"):
                    monitored[str(pid)] = {
                        "pid": pid,
                        "start": row["start"],
                        "actual_uids": row["actual_uids"],
                    }
                    if pid in tracked:
                        tracked[pid][1]["monitor_only"] = True
                if pid not in tracked:
                    try:
                        tracked[pid] = kernel.pin(pid, row)
                    except (FileNotFoundError, ProcessLookupError):
                        continue
                elif tracked[pid][1]["start"] != row["start"]:
                    raise RuntimeError("Tracked PID reused")
            if len(tracked) + 1 > 32:
                raise RuntimeError("Original32-process bound exceeded")
            if stopping[0] is not None:
                term_end = min(stopping[0] + 10, cleanup - 5)
                number = signal.SIGTERM if now < term_end else signal.SIGKILL
                for pid, (fd, row) in tuple(tracked.items()):
                    key = (pid, row["start"], int(number))
                    if key not in sent:
                        kernel.send(fd, row, number)
                        sent.add(key)
            empty = False
            while True:
                try:
                    pid, status = os.waitpid(-1, os.WNOHANG)
                except ChildProcessError:
                    empty = True
                    break
                if pid == 0:
                    break
                code = os.waitstatus_to_exitcode(status)
                reaped.append({"pid": pid, "exit_code": code})
                if direct is not None and pid == direct.pid:
                    direct_code = code
                    direct.returncode = code
                if pid in tracked:
                    os.close(tracked.pop(pid)[0])
            # Terminal status requires the original direct child AND kernel
            # proof that no adopted/live descendants remain. Never leader-only.
            if empty:
                if direct_code is None:
                    raise RuntimeError("Incomplete direct/reap proof")
                for pid, (fd, row) in tuple(tracked.items()):
                    # Nested descendants may have been reaped by an inner owner.
                    # Require stable descriptor exit evidence, not a stale census.
                    verify_exited_descriptor(fd)
                    os.close(fd)
                    tracked.pop(pid)
                proof = {
                    "direct_exit_code": direct_code,
                    "kernel_ECHILD": True,
                    "tracked_live": 0,
                    "reaped": reaped,
                    "stopping": stopping[0] is not None,
                    "started": began,
                    "finished": time.monotonic(),
                    "cleanup_end": cleanup,
                    "complete": True,
                    "privileged_monitors": monitored,
                    "read_budget": kernel.budget.usage(),
                }
                emit("terminal", proof=proof)
                return 0
            if now - last >= 0.1:
                emit("status", members=[os.getpid(), *sorted(rows)])
                last = now
            time.sleep(0.2)
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        # Cleanup verified owned handles inside the SAME endpoint. Failure
        # remains failure even if ECHILD is subsequently established.
        stop = time.monotonic()
        empty = False
        cleanup_errors = []
        while time.monotonic() < min(stop + 15, cleanup):
            now = time.monotonic()
            try:
                rows = fresh_owned(kernel, owned(kernel.census(), os.getpid()), os.getpid(), before)
                for pid, row in rows.items():
                    if pid not in tracked:
                        tracked[pid] = kernel.pin(pid, row)
            except BaseException as cleanup_error:
                cleanup_errors.append(type(cleanup_error).__name__)
            number = signal.SIGTERM if now < min(stop + 10, cleanup - 5) else signal.SIGKILL
            for pid, (fd, row) in tuple(tracked.items()):
                key = (pid, row["start"], int(number))
                if key not in sent:
                    try:
                        # This fd comes only from the private, previously
                        # proved descendant registry. PID reuse cannot retarget it.
                        if kernel.privileged_runtime:
                            kernel.send(fd, row, number)
                        elif not row.get("monitor_only"):
                            signal.pidfd_send_signal(fd, number)
                        sent.add(key)
                    except BaseException as cleanup_error:
                        cleanup_errors.append(type(cleanup_error).__name__)
            try:
                while True:
                    pid, status = os.waitpid(-1, os.WNOHANG)
                    if pid == 0:
                        break
                    if pid in tracked:
                        os.close(tracked.pop(pid)[0])
            except ChildProcessError:
                empty = True
                break
            time.sleep(0.2)
        try:
            emit(
                "failure",
                error=error,
                cleanup={"kernel_ECHILD": empty, "errors": cleanup_errors[:32]},
            )
        except BaseException:
            pass
        return 1

    finally:
        if gate is not None:
            os.close(gate)
        for fd, row in tracked.values():
            os.close(fd)
        kernel.close()
        channel.close()


if __name__ == "__main__":
    raise SystemExit(main())
