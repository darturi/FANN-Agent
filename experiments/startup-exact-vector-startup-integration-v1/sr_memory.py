"""Read-only cgroup v1/v2 discovery and bounded memory observations, host-side."""

import os
import re
import time
from pathlib import Path, PurePosixPath

from pc_common import RESOURCE
from pc_proc import fields, parse_stat

LIMITS = RESOURCE["resources"]


class ProcessObservationError(ValueError):
    def __init__(self, message, observation):
        super().__init__(message)
        self.observation = observation


def path_value(text):
    path = PurePosixPath(text)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe cgroup path")
    return path


def membership(text):
    rows = []
    for line in text.splitlines():
        ident, controllers, path = line.split(":", 2)
        if ident == "0" and controllers == "":
            rows.append((2, path_value(path)))
        elif "memory" in controllers.split(","):
            rows.append((1, path_value(path)))
    if len(rows) != 1:
        raise ValueError("Unique memory cgroup membership required")
    return rows[0]


def unescape(text):
    return re.sub(r"\\(040|011|012|134)", lambda m: chr(int(m[1], 8)), text)


def resolve_scope(cgroup_text, mount_text):
    version, group = membership(cgroup_text)
    matches = []
    for line in mount_text.splitlines():
        before, sep, after = line.partition(" - ")
        if not sep:
            continue
        left, right = before.split(), after.split()
        if len(left) < 6 or len(right) < 3:
            continue
        if right[0] != ("cgroup2" if version == 2 else "cgroup"):
            continue
        if version == 1 and "memory" not in right[2].split(","):
            continue
        root, mount = path_value(unescape(left[3])), Path(unescape(left[4]))
        if not mount.is_absolute() or ".." in mount.parts:
            raise ValueError("Unsafe cgroup mount")
        if group.is_relative_to(root):
            matches.append((len(root.parts), root, mount))
    if not matches:
        raise ValueError("Memory cgroup is not covered by a visible mount")
    matches.sort(key=lambda x: x[0], reverse=True)
    if len(matches) > 1 and matches[0][0] == matches[1][0]:
        raise ValueError("Ambiguous memory cgroup mount")
    _, root, mount = matches[0]
    leaf = mount / str(group.relative_to(root))
    ancestors = []
    current = leaf
    while True:
        ancestors.append(current)
        if len(ancestors) > LIMITS["cgroup_ancestors_max"]:
            raise ValueError("Cgroup ancestor cap")
        if current == mount:
            break
        current = current.parent
        if not current.is_relative_to(mount):
            raise ValueError("Cgroup escaped mount")
    return dict(
        version=version,
        membership=str(group),
        mount_root=str(root),
        mount=str(mount),
        leaf=str(leaf),
        ancestors=[str(p) for p in ancestors],
    )


def integers(text):
    result = {}
    for line in text.splitlines():
        key, value = line.split()
        if key in result:
            raise ValueError("Duplicate memory counter")
        number = int(value)
        if number < 0:
            raise ValueError("Negative memory counter")
        result[key] = number
    return result


class Reader:
    def __init__(self):
        self.files = self.bytes = 0

    def read(self, path, optional=False):
        if self.files >= LIMITS["sampler_file_reads_max"]:
            raise RuntimeError("Memory file-read cap")
        self.files += 1
        try:
            with Path(path).open("rb") as h:
                data = h.read(LIMITS["sampler_file_bytes_max"] + 1)
        except (FileNotFoundError, PermissionError):
            if optional:
                return None
            raise
        if len(data) > LIMITS["sampler_file_bytes_max"]:
            raise ValueError("Oversize memory/proc file")
        self.bytes += len(data)
        if self.bytes > LIMITS["sampler_read_bytes_max"]:
            raise RuntimeError("Memory byte-read cap")
        return data.decode("utf-8")


class Memory:
    def __init__(self, parent_pid, reader=None, proc=Path("/proc")):
        self.read = reader or Reader()
        self.proc = Path(proc)
        self.parent_pid = int(parent_pid)
        self.self_membership = self.read.read(self.proc / "self/cgroup")
        parent = self.read.read(self.proc / str(parent_pid) / "cgroup")
        if membership(parent) != membership(self.self_membership):
            raise RuntimeError("Sampler and host parent cgroups differ")
        self.parent_start = parse_stat(self.read.read(self.proc / str(parent_pid) / "stat"))[
            "starttime"
        ]
        self.context = resolve_scope(parent, self.read.read(self.proc / "self/mountinfo"))
        self.context.update(
            parent_cgroup_text=parent,
            sampler_cgroup_text=self.self_membership,
            host_mountinfo=self.read.read(self.proc / "self/mountinfo"),
            parent_pid=self.parent_pid,
            parent_starttime=self.parent_start,
            sampler_pid=os.getpid(),
            peak_origin="kernel cgroup lifetime high-water; never reset",
        )
        self.initial_limits = None
        self.previous_events = {}
        self.previous_peaks = {}
        self.process_starts = {}

    def process(self, pid):
        """Bracket identity; only demonstrated exits may lack RSS counters."""
        attempts = []
        initial = None
        for attempt in range(2):
            try:
                before = parse_stat(self.read.read(self.proc / str(pid) / "stat"))
                status = fields(self.read.read(self.proc / str(pid) / "status"))
                member = membership(self.read.read(self.proc / str(pid) / "cgroup"))
                after = parse_stat(self.read.read(self.proc / str(pid) / "stat"))
            except FileNotFoundError:
                return dict(pid=pid, availability="exited_during_sample")
            missing = [name for name in ("VmRSS", "VmHWM") if name not in status]
            attempts.append(
                dict(
                    starttime=before["starttime"],
                    state=before["state"],
                    final_starttime=after["starttime"],
                    final_state=after["state"],
                    missing=missing,
                )
            )
            diagnostic = dict(pid=pid, attempts=attempts)
            if before["pid"] != pid or after["pid"] != pid:
                raise ProcessObservationError("Proc PID differs", diagnostic)
            if initial is None:
                initial = before["starttime"]
            if before["starttime"] != after["starttime"] or initial != after["starttime"]:
                self.process_starts[pid] = after["starttime"]
                return dict(pid=pid, availability="pid_reused_during_sample", attempts=attempts)
            if member != membership(self.self_membership):
                raise RuntimeError("Observed PID left task cgroup")
            if before["state"] == "Z" and after["state"] != "Z":
                raise ProcessObservationError("Terminal process state reversed", diagnostic)
            if missing and after["state"] != "Z":
                if attempt == 0:
                    continue
                raise ProcessObservationError("Live process lacks RSS counters", diagnostic)
            reused = pid in self.process_starts and self.process_starts[pid] != initial
            self.process_starts[pid] = initial
            row = dict(
                pid=pid,
                starttime=initial,
                state=before["state"],
                final_state=after["state"],
                pid_reused=reused,
                namespace_pids=[int(n) for n in status["NSpid"].split()]
                if "NSpid" in status
                else None,
                observation_attempts=len(attempts),
            )
            if missing:
                row["availability"] = "terminal_during_sample"
            for name in ("VmRSS", "VmHWM"):
                value = status.get(name)
                if value is None:
                    row[name] = None
                else:
                    parts = value.split()
                    if len(parts) != 2 or parts[1] != "kB" or int(parts[0]) < 0:
                        raise ProcessObservationError("Invalid process RSS", diagnostic)
                    row[name] = int(parts[0])
            return row
        raise AssertionError("Unreachable bounded process observation")

    def scope(self, path):
        path = Path(path)
        v = self.context["version"]
        root = str(path) == self.context["mount"] and self.context["mount_root"] == "/"

        def get(name, optional=False):
            return self.read.read(path / name, optional=optional)

        def num(name, optional=False, limit=False):
            raw = get(name, optional)
            if raw is None:
                return None
            raw = raw.strip()
            if limit and raw == "max":
                return None
            value = int(raw)
            if value < 0:
                raise ValueError("Negative memory value")
            if limit and v == 1 and value >= 2**60:
                return None
            return value

        if v == 2:
            if root and get("memory.current", True) is None:
                return dict(
                    path=str(path),
                    current=None,
                    peak=None,
                    limit=None,
                    stat={},
                    events={},
                    availability="system_root_no_memory_interface",
                )
            row = dict(
                path=str(path),
                current=num("memory.current"),
                peak=num("memory.peak", True),
                limit=num("memory.max", root, True),
                stat=integers(get("memory.stat")),
                events=integers(get("memory.events")),
                swap_current=num("memory.swap.current", True),
                swap_limit=num("memory.swap.max", True, True),
                pressure=get("memory.pressure", True),
            )
            if not {"anon", "file", "kernel"}.issubset(row["stat"]):
                # Older v2 kernels expose kernel subfields without aggregate kernel.
                row["component_coverage"] = "kernel_aggregate_unavailable"
            else:
                row["component_coverage"] = "anon_file_kernel"
        else:
            oom = get("memory.oom_control", True)
            row = dict(
                path=str(path),
                current=num("memory.usage_in_bytes"),
                peak=num("memory.max_usage_in_bytes"),
                limit=num("memory.limit_in_bytes", False, True),
                stat=integers(get("memory.stat")),
                events=dict(failcnt=num("memory.failcnt")),
                swap_current=num("memory.memsw.usage_in_bytes", True),
                swap_limit=num("memory.memsw.limit_in_bytes", True, True),
                pressure=None,
                component_coverage="v1_rss_cache; inspect total_ prefixes separately",
            )
            if oom is not None:
                row["events"].update(integers(oom))
        if row["peak"] is not None and row["peak"] < row["current"]:
            # current and peak are separate reads; re-read peak once for allocation race.
            row["peak"] = num("memory.peak" if v == 2 else "memory.max_usage_in_bytes")
            if row["peak"] < row["current"]:
                raise ValueError("Kernel peak below current charge")
        previous = self.previous_events.get(str(path), {})
        if any(
            k in previous and n < previous[k]
            for k, n in row["events"].items()
            if k not in {"under_oom", "oom_kill_disable"}
        ):
            raise RuntimeError("Memory event counter decreased")
        old = self.previous_peaks.get(str(path))
        if old is not None and row["peak"] is not None and row["peak"] < old:
            raise RuntimeError("Memory peak reset/decreased")
        self.previous_events[str(path)] = row["events"].copy()
        self.previous_peaks[str(path)] = row["peak"]
        return row

    def sample(self, phase):
        started = time.monotonic_ns()
        if membership(self.read.read(self.proc / str(self.parent_pid) / "cgroup")) != membership(
            self.self_membership
        ):
            raise RuntimeError("Host cgroup membership changed")
        if (
            parse_stat(self.read.read(self.proc / str(self.parent_pid) / "stat"))["starttime"]
            != self.parent_start
        ):
            raise RuntimeError("Host PID replaced")
        scopes = [self.scope(p) for p in self.context["ancestors"]]
        limits = {p["path"]: p["limit"] for p in scopes}
        if self.initial_limits is None:
            if not any(n is not None and n > 0 for n in limits.values()):
                raise RuntimeError("No visible finite cgroup memory limit")
            self.initial_limits = limits
        elif limits != self.initial_limits:
            raise RuntimeError("Cgroup memory limits changed")
        leaf = Path(self.context["leaf"])
        # All descendants inherit this task's cgroup. Unexpected nested groups are explicit.
        if any(p.is_dir() for p in leaf.iterdir()):
            raise RuntimeError("Nested task cgroups require a new observation contract")
        pids = sorted(set(map(int, self.read.read(leaf / "cgroup.procs").split())))
        if len(pids) > LIMITS["processes_max"]:
            raise RuntimeError("Task process-count ceiling")
        processes = []
        for pid in pids:
            processes.append(self.process(pid))
        return dict(
            start_ns=started,
            end_ns=time.monotonic_ns(),
            phase=phase,
            scopes=scopes,
            processes=processes,
            file_reads=self.read.files,
            bytes_read=self.read.bytes,
        )
