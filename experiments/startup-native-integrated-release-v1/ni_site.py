"""Existing Slurm/client and kernel allocation checks; no privileged issuer."""

import hashlib
import os
import platform
import re
import selectors
import subprocess
import time
from pathlib import Path, PurePosixPath

from au_kernel import MAX_READ, LinuxKernel
from nh_common import config, sha
from release_policy import SPENT


def trusted_binary(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("Installed executable required")
    for p in (path, *path.parents):
        s = p.stat()
        if s.st_uid != 0 or s.st_mode & 0o002 or (s.st_mode & 0o020 and os.access(p, os.W_OK)):
            raise ValueError("Scheduler client/configuration is user-writable")
    return {
        "path": str(path),
        "sha256": sha(path),
        "device": path.stat().st_dev,
        "inode": path.stat().st_ino,
    }


def clean_environment():
    # The installed site client uses its normal trusted site configuration.
    if any(
        os.environ.get(k) for k in ("SLURM_CONF_SERVER", "SLURM_CONFIG", "LD_PRELOAD", "PYTHONHOME")
    ):
        raise ValueError("Unreviewed scheduler/loader override")
    env = {
        k: v
        for k, v in os.environ.items()
        if k in ("PATH", "LANG", "LC_ALL", "TZ", "HOME", "USER", "LOGNAME")
    }
    env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    if os.environ.get("SLURM_CONF"):
        conf = Path(os.environ["SLURM_CONF"]).resolve(strict=True)
        for entry in (conf, *conf.parents):
            st = entry.stat()
            if (
                st.st_uid != 0
                or st.st_mode & 0o002
                or (st.st_mode & 0o020 and os.access(entry, os.W_OK))
            ):
                raise ValueError("Untrusted Slurm configuration")
        env["SLURM_CONF"] = str(conf)
    libraries = os.environ.get("LD_LIBRARY_PATH", "")
    if libraries:
        for value in libraries.split(":"):
            p = Path(value)
            if not p.is_absolute() or not p.is_dir():
                raise ValueError("Unsafe library search")
            for parent in (p, *p.parents):
                s = parent.stat()
                if (
                    s.st_uid != 0
                    or s.st_mode & 0o002
                    or (s.st_mode & 0o020 and os.access(parent, os.W_OK))
                ):
                    raise ValueError("User-writable scheduler library path")
        env["LD_LIBRARY_PATH"] = libraries
    return env


def bounded_command(argv, timeout=10, maximum=MAX_READ):
    end = time.monotonic() + timeout
    p = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=clean_environment(),
        start_new_session=True,
    )
    result = bytearray()
    selector = selectors.DefaultSelector()
    selector.register(p.stdout, selectors.EVENT_READ)
    try:
        os.set_blocking(p.stdout.fileno(), False)
        while selector.get_map():
            if time.monotonic() >= end:
                raise TimeoutError("Read-only scheduler query deadline")
            for key, mask in selector.select(min(0.05, end - time.monotonic())):
                block = os.read(key.fd, min(8192, maximum + 1 - len(result)))
                if not block:
                    selector.unregister(key.fileobj)
                else:
                    result.extend(block)
                if len(result) > maximum:
                    raise ValueError("Scheduler response bound")
        code = p.wait(timeout=max(0.001, end - time.monotonic()))
        if code:
            raise RuntimeError(
                "Read-only scheduler query failed: " + result.decode(errors="replace")[:512]
            )
        return result.decode("utf-8", "strict")
    finally:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=min(1, max(0.001, end - time.monotonic())))
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=1)
        selector.close()
        p.stdout.close()


def parse_record(text):
    if "\0" in text or len(text.encode()) > MAX_READ:
        raise ValueError("Unsafe scheduler response")
    matches = list(re.finditer(r"(?:^|\s)([A-Za-z][A-Za-z0-9_/]*)=", text.strip()))
    if not matches:
        raise ValueError("Structured scheduler record required")
    rows = {}
    for i, m in enumerate(matches):
        if m[1] in rows:
            raise ValueError("Duplicate scheduler field")
        rows[m[1]] = text.strip()[
            m.end() : matches[i + 1].start() if i + 1 < len(matches) else None
        ].strip()
    return rows


def validate_job(record, job, uid, account, comment, host):
    required = (
        "JobId",
        "UserId",
        "Account",
        "JobState",
        "TimeLimit",
        "NumNodes",
        "NumCPUs",
        "NumTasks",
        "CPUs/Task",
        "NodeList",
        "Comment",
    )
    if any(k not in record for k in required):
        raise ValueError("Incomplete live job record")
    if not isinstance(job, str) or not re.fullmatch("[1-9][0-9]*", job) or job in SPENT:
        raise ValueError("Fresh job identity required")
    user = re.fullmatch(r"[^()\s]+\(([0-9]+)\)", record["UserId"])
    if (
        record["JobId"] != job
        or user is None
        or int(user[1]) != uid
        or record["Account"] != account
        or record["Comment"] != comment
        or record["JobState"] != "RUNNING"
    ):
        raise ValueError("Live scheduler identity differs")
    if record["TimeLimit"] not in ("01:00:00", "1:00:00") or any(
        record[k] != v
        for k, v in {"NumNodes": "1", "NumCPUs": "4", "NumTasks": "1", "CPUs/Task": "4"}.items()
    ):
        raise ValueError("Original allocation limits differ")
    if (
        record.get("Requeue") != "0"
        or record.get("Restarts", "0") != "0"
        or any(k.startswith("Array") for k in record)
    ):
        raise ValueError("Retries/arrays are not an allowance")
    memory = record.get("MinMemoryNode")
    if memory not in ("32G", "32768M", "34359738368"):
        tres = dict(
            x.split("=", 1)
            for x in record.get("TRES", record.get("AllocTRES", "")).split(",")
            if "=" in x
        )
        if tres.get("mem") not in ("32G", "32768M"):
            raise ValueError("Original32GiB request required")
    return {
        "job_id": job,
        "uid": uid,
        "account": account,
        "host": host,
        "comment": comment,
        "limits": config()["limits"],
    }


class SiteClient:
    def __init__(self, path):
        self.identity = trusted_binary(path)
        self.path = self.identity["path"]

    def query(self, *args):
        if trusted_binary(self.path) != self.identity:
            raise RuntimeError("Scheduler client changed")
        value = bounded_command([self.path, "--local", *args])
        if trusted_binary(self.path) != self.identity:
            raise RuntimeError("Scheduler client changed during query")
        return value

    def probe(self):
        version = self.query("--version")
        configuration = self.query("show", "config")
        auth = re.findall(r"^\s*AuthType\s*=\s*(\S+)", configuration, re.M)
        if len(auth) != 1 or auth[0] not in ("auth/munge", "auth/slurm"):
            raise ValueError("Authenticated site controller required")
        return {
            "client": self.identity,
            "version": version.strip(),
            "authentication": auth[0],
            "configuration_sha256": hashlib.sha256(configuration.encode()).hexdigest(),
        }

    def job(self, job, uid, account, comment):
        text = self.query("--oneliner", "show", "job", job)
        record = parse_record(text)
        proof = validate_job(record, job, uid, account, comment, platform.node())
        nodes = self.query("show", "hostnames", record["NodeList"]).split()
        host = platform.node().split(".")[0]
        if len(nodes) != 1 or nodes[0].split(".")[0] != host:
            raise ValueError("Allocated node differs")
        return {
            **proof,
            "record": record,
            "response_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "client": self.identity,
        }


def resolve_scope(cgroup_text, mountinfo, job=None):
    memberships = []
    for line in cgroup_text.splitlines():
        ident, controllers, path = line.split(":", 2)
        if (ident == "0" and controllers == "") or "memory" in controllers.split(","):
            memberships.append((2 if ident == "0" else 1, PurePosixPath(path)))
    if len(memberships) != 1:
        raise ValueError("Unique kernel memory scope required")
    version, group = memberships[0]
    if not group.is_absolute() or ".." in group.parts:
        raise ValueError("Unsafe kernel scope")
    if job is not None:
        components = list(group.parts)
        want = "job_" + job
        if components.count(want) != 1:
            raise ValueError("Kernel scope does not identify this job")
        group = PurePosixPath(*components[: components.index(want) + 1])
    matches = []
    for line in mountinfo.splitlines():
        a, sep, b = line.partition(" - ")
        if not sep:
            continue
        left, right = a.split(), b.split()
        if len(left) < 6 or len(right) < 3 or right[0] != ("cgroup2" if version == 2 else "cgroup"):
            continue
        if version == 1 and "memory" not in right[2].split(","):
            continue
        if "\\" in left[3] + left[4]:
            raise ValueError("Ambiguous escaped cgroup mount")
        root = PurePosixPath(left[3])
        mount = Path(left[4])
        if (
            not root.is_absolute()
            or ".." in root.parts
            or not mount.is_absolute()
            or ".." in mount.parts
        ):
            raise ValueError("Unsafe cgroup mount")
        if group.is_relative_to(root):
            matches.append((len(root.parts), mount / str(group.relative_to(root)), right[0]))
    matches.sort(key=lambda x: x[0], reverse=True)
    if not matches or len(matches) > 1 and matches[0][0] == matches[1][0]:
        raise ValueError("Missing/ambiguous kernel cgroup mount")
    return {
        "path": str(matches[0][1]),
        "version": version,
        "membership": str(group),
        "filesystem": matches[0][2],
    }


class ScopedKernel(LinuxKernel):
    def __init__(self, budget_fd=None, scope=None, privileged_runtime=False):
        super().__init__(budget_fd)
        self.scope = scope
        self.privileged_runtime = privileged_runtime
        if scope is not None:
            actual = resolve_scope(
                self.read(f"{os.getpid()}/cgroup"), self.read(f"{os.getpid()}/mountinfo")
            )
            if not Path(actual["path"]).is_relative_to(scope["path"]):
                raise ValueError("Observer left approved scope")
            s = Path(scope["path"]).stat()
            self.scope_identity = (s.st_dev, s.st_ino)

    def census(self):
        if self.scope is None:
            return super().census()  # explicit local kernel fixtures only
        root = Path(self.scope["path"])
        s = root.stat()
        if (s.st_dev, s.st_ino) != self.scope_identity:
            raise RuntimeError("Kernel scope generation changed")
        scopes = [root]
        seen = []
        ids = set()
        while scopes:
            p = scopes.pop()
            seen.append(p)
            if len(seen) > 16:
                raise RuntimeError("Original cgroup scope bound exceeded")
            if p.is_symlink():
                raise ValueError("Cgroup link prohibited")
            for child in p.iterdir():
                if child.is_dir():
                    scopes.append(child)
            fd = os.open(p / "cgroup.procs", os.O_RDONLY | os.O_NOFOLLOW)
            try:
                self.budget.reserve(reads=1)
                self.budget.reserve(bytes=MAX_READ + 1)
                data = os.read(fd, MAX_READ + 1)
                self.budget.reserve(bytes=len(data) - (MAX_READ + 1))
            finally:
                os.close(fd)
            if len(data) > MAX_READ:
                raise ValueError("Cgroup PID response bound")
            for value in data.split():
                if not value.isdigit() or int(value) <= 0:
                    raise ValueError("Unknown namespace PID")
                ids.add(int(value))
            if len(ids) > 32:
                raise RuntimeError("Original32-process census bound exceeded")
        rows = {}
        from au_kernel import parse_stat

        for pid in ids:
            try:
                rows[pid] = parse_stat(self.read(f"{pid}/stat"))
            except (FileNotFoundError, ProcessLookupError):
                continue
        return rows

    def process(self, pid):
        if not self.privileged_runtime:
            return super().process(pid)
        if type(pid) is not int or pid <= 0:
            raise ValueError("Strict positive PID")
        from au_kernel import parse_stat

        first = parse_stat(self.read(f"{pid}/stat"))
        status = self.read(f"{pid}/status")
        lines = [line for line in status.splitlines() if line.startswith("Uid:")]
        if len(lines) != 1:
            raise RuntimeError("Credential observation missing")
        uids = tuple(map(int, lines[0].split()[1:]))
        owner = os.getuid()
        if len(uids) != 4 or any(u not in (owner, 0) for u in uids):
            raise RuntimeError("Foreign descendant credentials")
        group = self.read(f"{pid}/cgroup")
        last = parse_stat(self.read(f"{pid}/stat"))
        if (first["pid"], first["start"]) != (last["pid"], last["start"]):
            raise RuntimeError("PID generation changed")
        return {
            **last,
            "uid": uids[0],
            "actual_uids": uids,
            "monitor_only": any(u != owner for u in uids),
            "cgroup": group,
        }

    def pin(self, pid, expected=None):
        if not self.privileged_runtime:
            return super().pin(pid, expected)
        before = self.process(pid)
        fd = os.pidfd_open(pid)
        try:
            after = self.process(pid)

            def identity(row):
                return row["pid"], row["start"], row["cgroup"]

            if identity(before) != identity(after) or (
                expected is not None and identity(after) != identity(expected)
            ):
                raise RuntimeError("PID generation/scope changed across descriptor open")
            after["monitor_only"] = (
                before["monitor_only"]
                or after["monitor_only"]
                or bool(expected and expected.get("monitor_only"))
            )
            return fd, after
        except BaseException:
            os.close(fd)
            raise

    def send(self, fd, row, number):
        if not self.privileged_runtime:
            return super().send(fd, row, number)
        if row.get("monitor_only"):
            return
        try:
            current = self.process(row["pid"])
        except (FileNotFoundError, ProcessLookupError):
            return
        if current.get("monitor_only"):
            row["monitor_only"] = True
            return
        return super().send(fd, row, number)
