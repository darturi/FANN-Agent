"""Bounded read-only Linux identity observations and PID-descriptor signals."""

import ctypes
import hashlib
import json
import os
import platform
import signal
import stat
from pathlib import Path

MAX_READ = 65536
MAX_PIDS = 4096


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_fd(fd, maximum=MAX_READ):
    value = bytearray()
    while True:
        block = os.read(fd, min(8192, maximum + 1 - len(value)))
        if not block:
            return bytes(value)
        value.extend(block)
        if len(value) > maximum:
            raise ValueError("Bounded read exceeded")


def trusted_json(path, expected):
    """Root-owned non-writable chain, no symlinks, bounded single stable inode."""
    p = Path(path)
    if not p.is_absolute() or str(p) != str(path) or ".." in p.parts:
        raise ValueError("Canonical anchor required")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in p.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
            s = os.fstat(fd)
            if s.st_uid != 0 or s.st_mode & 0o022:
                raise ValueError("Untrusted anchor parent")
        file = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            before = os.fstat(file)
            if not stat.S_ISREG(before.st_mode) or before.st_uid != 0 or before.st_mode & 0o022:
                raise ValueError("Untrusted anchor file")
            data = read_fd(file)
            after = os.fstat(file)

            def identity(s):
                return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

            if identity(before) != identity(after) or hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Pinned anchor changed")

            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("Duplicate JSON key")
                    result[key] = value
                return result

            return json.loads(
                data,
                object_pairs_hook=unique,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")),
            )
        finally:
            os.close(file)
    finally:
        os.close(fd)


def parse_stat(text):
    close = text.rfind(")")
    if close < 0 or "(" not in text:
        raise ValueError("Invalid proc stat")
    pid = int(text[: text.index("(")].strip())
    fields = text[close + 2 :].split()
    if pid <= 0 or len(fields) < 20:
        raise ValueError("Incomplete proc stat")
    row = dict(
        pid=pid,
        state=fields[0],
        ppid=int(fields[1]),
        pgid=int(fields[2]),
        sid=int(fields[3]),
        start=int(fields[19]),
    )
    if row["start"] <= 0 or row["ppid"] < 0:
        raise ValueError("Invalid process identity")
    return row


class LinuxKernel:
    def __init__(self, budget_fd=None):
        if (
            platform.system() != "Linux"
            or not hasattr(os, "pidfd_open")
            or not hasattr(signal, "pidfd_send_signal")
        ):
            raise RuntimeError("Linux PID descriptors required; no PID fallback")
        from au_budget import ReadBudget

        self.budget = ReadBudget(budget_fd)
        self.proc = os.open("/proc", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            buf = ctypes.create_string_buffer(256)
            if (
                ctypes.CDLL(None, use_errno=True).fstatfs(self.proc, buf)
                or ctypes.c_long.from_buffer(buf).value != 0x9FA0
            ):
                raise RuntimeError("Actual kernel procfs required")
        except BaseException:
            os.close(self.proc)
            raise

    def close(self):
        os.close(self.proc)
        os.close(self.budget.fd)

    def read(self, name):
        self.budget.reserve(reads=1)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.proc)
        try:
            output = bytearray()
            while True:
                count = min(4096, MAX_READ + 1 - len(output))
                self.budget.reserve(bytes=count)
                block = os.read(fd, count)
                self.budget.reserve(bytes=len(block) - count)
                output.extend(block)
                if len(output) > MAX_READ:
                    raise ValueError("Bounded proc read exceeded")
                if not block:
                    return output.decode("utf-8", "surrogateescape")
        finally:
            os.close(fd)

    def process(self, pid):
        if type(pid) is not int or pid <= 0:
            raise ValueError("Strict positive PID")
        before = parse_stat(self.read(f"{pid}/stat"))
        status = self.read(f"{pid}/status")
        uid = [line for line in status.splitlines() if line.startswith("Uid:")]
        if len(uid) != 1:
            raise ValueError("Process UID unavailable")
        uids = tuple(map(int, uid[0].split()[1:]))
        if len(uids) != 4 or len(set(uids)) != 1:
            raise ValueError("Credential transition is not owned")
        cgroup = self.read(f"{pid}/cgroup")
        after = parse_stat(self.read(f"{pid}/stat"))
        if (before["pid"], before["start"]) != (after["pid"], after["start"]):
            raise RuntimeError("PID replacement during observation")
        return {**after, "uid": uids[0], "cgroup": cgroup}

    def pin(self, pid, expected=None):
        before = self.process(pid)
        fd = os.pidfd_open(pid)
        try:
            after = self.process(pid)

            def identity(row):
                return (row["pid"], row["start"], row["uid"], row["cgroup"])

            if identity(before) != identity(after) or (
                expected is not None and identity(after) != identity(expected)
            ):
                raise RuntimeError("PID changed across descriptor open")
            return fd, after
        except BaseException:
            os.close(fd)
            raise

    def census(self):
        ids = [int(name) for name in os.listdir(self.proc) if name.isascii() and name.isdecimal()]
        if len(ids) > MAX_PIDS:
            raise RuntimeError("Proc census bound exceeded")
        rows = {}
        for pid in ids:
            try:
                rows[pid] = parse_stat(self.read(f"{pid}/stat"))
            except (FileNotFoundError, ProcessLookupError):
                continue
        return rows

    def snapshot(self):
        pid = os.getpid()
        row = self.process(pid)
        namespaces = {
            name: os.stat(f"/proc/{pid}/ns/{name}").st_ino for name in ("pid", "mnt", "cgroup")
        }
        return {
            "uid": os.getuid(),
            "host": platform.node(),
            "boot": self.read("sys/kernel/random/boot_id").strip(),
            "cgroup": row["cgroup"],
            "namespaces": namespaces,
            "mountinfo_sha256": hashlib.sha256(self.read(f"{pid}/mountinfo").encode()).hexdigest(),
            "supervisor_pid": pid,
            "supervisor_start": row["start"],
        }

    def send(self, fd, row, number):
        if number not in (signal.SIGTERM, signal.SIGKILL):
            raise ValueError("Only bounded shutdown signals allowed")
        try:
            current = self.process(row["pid"])
        except (FileNotFoundError, ProcessLookupError):
            return
        keys = ("pid", "start", "uid", "cgroup")
        if any(current[k] != row[k] for k in keys):
            raise RuntimeError("Ownership changed before signal")
        try:
            signal.pidfd_send_signal(fd, number)
        except ProcessLookupError:
            pass
