"""Owned-process identity, allocation-local affinity and bounded proc observations."""

import os
import time
from pathlib import Path

from pc_common import CONTRACT
from pc_trace import category


def parse_stat(text):
    left, right = text.find("("), text.rfind(")")
    if left < 1 or right <= left:
        raise ValueError("Malformed proc stat")
    pid = int(text[:left].strip())
    f = text[right + 1 :].split()  # first token is field 3, not field 1
    if len(f) < 37:
        raise ValueError("Truncated proc stat")
    result = dict(
        pid=pid,
        state=f[0],
        ppid=int(f[1]),
        minflt=int(f[7]),
        majflt=int(f[9]),
        utime=int(f[11]),
        stime=int(f[12]),
        starttime=int(f[19]),
        processor=int(f[36]),
    )
    if any(
        result[k] < 0
        for k in ("pid", "ppid", "minflt", "majflt", "utime", "stime", "starttime", "processor")
    ):
        raise ValueError("Negative proc counter/identity")
    return result


def fields(text):
    out = {}
    for line in text.splitlines():
        k, sep, v = line.partition(":")
        if not sep or k in out:
            raise ValueError("Malformed/duplicate proc field")
        out[k] = v.strip()
    return out


def cpu_list(value):
    result = set()
    for item in value.split(","):
        pair = item.split("-")
        if len(pair) == 1:
            result.add(int(pair[0]))
        elif len(pair) == 2 and int(pair[0]) <= int(pair[1]):
            result.update(range(int(pair[0]), int(pair[1]) + 1))
        else:
            raise ValueError("Malformed CPU range")
    if not result or min(result) < 0:
        raise ValueError("Empty/negative CPU set")
    return result


def select_cores(allowed, sysroot=Path("/sys/devices/system/cpu")):
    cores = {}
    records = []
    for cpu in sorted(allowed):
        p = sysroot / ("cpu" + str(cpu)) / "topology"
        socket = int((p / "physical_package_id").read_text())
        core = int((p / "core_id").read_text())
        records.append(dict(cpu=cpu, socket=socket, core=core))
        cores.setdefault((socket, core), cpu)
    selected = [cpu for _, cpu in sorted(cores.items())][:4]
    if len(selected) != 4 or len(cores) != 4:
        raise ValueError("Allocation/task mask must expose exactly four distinct physical cores")
    return dict(allowed=sorted(allowed), topology=records, selected=selected)


def observed(method):
    def wrapper(self, *args, **kwargs):
        outer = self.depth == 0
        start = time.perf_counter_ns() if outer else 0
        self.depth += 1
        try:
            return method(self, *args, **kwargs)
        finally:
            self.depth -= 1
            if outer:
                self.elapsed_ns += time.perf_counter_ns() - start
                if self.elapsed_ns > 60 * 10**9:
                    raise RuntimeError("Telemetry wall-time cap exhausted")

    return wrapper


class Proc:
    def __init__(
        self,
        budget,
        emit,
        procroot=Path("/proc"),
        sysroot=Path("/sys/devices/system/cpu"),
        getaffinity=os.sched_getaffinity if hasattr(os, "sched_getaffinity") else None,
        setaffinity=os.sched_setaffinity if hasattr(os, "sched_setaffinity") else None,
    ):
        initialization_started = time.perf_counter_ns()
        if getaffinity is None or setaffinity is None:
            raise RuntimeError("Linux affinity API unavailable")
        self.budget, self.emit = budget, emit
        self.root, self.get, self.set = procroot, getaffinity, setaffinity
        self.reads = self.affinity = self.bundles = self.elapsed_ns = self.depth = 0
        self.client = os.getpid()
        self.identities = {}
        self.optional = {}
        self.previous = {}
        self.context_capability = {}
        self.servers = {}
        self.peak_rss_kib = {}
        self.client_threads = None
        self.layout = select_cores(self.mask(self.client), sysroot)
        self.optional_schedstat = (
            self.optional_read(procroot / str(self.client) / "schedstat") is not None
        )
        enabled = procroot / "sys/kernel/sched_schedstats"
        enabled_value = self.optional_read(enabled)
        self.scheduler_enabled = enabled_value is not None and enabled_value.strip() == "1"
        self.emit(
            "placement",
            dict(
                kind="allocation",
                **self.layout,
                clock_ticks=os.sysconf("SC_CLK_TCK"),
                optional_schedstat=self.optional_schedstat,
                scheduler_wait_accounting_enabled=self.scheduler_enabled,
            ),
        )
        self.pin(self.client, self.layout["selected"][0])
        self.client_start = self.stat(self.client)["starttime"]
        self.elapsed_ns = time.perf_counter_ns() - initialization_started

    @observed
    def freeze_client_threads(self):
        tids = sorted(int(p.name) for p in (self.root / str(self.client) / "task").iterdir())
        for tid in tids:
            self.pin(tid, self.layout["selected"][0])
        self.client_threads = len(tids)
        self.emit(
            "placement", dict(kind="client_threads", tids=tids, cpu=self.layout["selected"][0])
        )

    @observed
    def read(self, path):
        self.budget.check()
        if self.reads >= 44000:
            raise RuntimeError("Proc read cap exhausted")
        self.reads += 1
        return Path(path).read_text()

    def optional_read(self, path):
        try:
            return self.read(path)
        except (FileNotFoundError, PermissionError):
            return None

    def stat(self, pid):
        value = parse_stat(self.read(self.root / str(pid) / "stat"))
        if value["pid"] != pid:
            raise RuntimeError("PID namespace identity differs")
        return value

    @observed
    def mask(self, pid):
        if self.affinity >= 11200:
            raise RuntimeError("Affinity-operation cap exhausted")
        self.affinity += 1
        return set(self.get(pid))

    @observed
    def pin(self, pid, cpu):
        if cpu not in self.layout["allowed"] or self.affinity >= 11200:
            raise RuntimeError("CPU outside allocation/affinity cap")
        self.affinity += 1
        self.set(pid, {cpu})
        if self.mask(pid) != {cpu}:
            raise RuntimeError("Affinity readback differs")

    def cell_cpu(self, cell, epoch):
        key = CONTRACT["cpu_policy"]["epoch" + str(epoch)][cell]
        return self.layout["selected"][int(key[1])]

    @observed
    def bind(self, reader, work, epoch=0):
        r = reader
        with category("observer"):
            pid, database, user, address = r.connection.execute(
                "SELECT pg_backend_pid(),current_database(),current_user,inet_server_addr()",
                prepare=False,
            ).fetchone()
        if (database, user, address) != ("torch_reviews", "torch_reader", None):
            raise RuntimeError("Reader role/database/transport differs")
        postmaster = int((Path(work) / "pgdata/postmaster.pid").read_text().splitlines()[0])
        st = self.stat(pid)
        if st["ppid"] != postmaster or pid in self.identities:
            raise RuntimeError("Backend parent/reused PID differs")
        cpu = self.cell_cpu(r.mode, epoch)
        self.pin(pid, cpu)
        with category("observer"):
            if r.connection.execute("SELECT pg_backend_pid()", prepare=False).fetchone()[0] != pid:
                raise RuntimeError("Connection/backend replaced after affinity")
        record = dict(
            reader=r.identity,
            cell=r.mode,
            pid=pid,
            starttime=st["starttime"],
            postmaster=postmaster,
            server=str(work),
            socket=str(Path(work) / "socket"),
            epoch=epoch,
            cpu=cpu,
        )
        self.identities[pid] = record
        r.physical = record
        # Record capability before this reader's first search. Required reads fail closed.
        self.optional[pid] = (
            self.optional_schedstat
            and self.optional_read(self.root / str(pid) / "schedstat") is not None
        )
        record["schedstat_available"] = self.optional[pid]
        key = "numa/" + str(pid)
        self.context_capability[key] = (
            self.optional_read(self.root / str(pid) / "numa_maps") is not None
        )
        self.sample(r, "admission")
        self.emit("identities", record)
        return record

    @observed
    def repin(self, reader, epoch):
        value = reader.physical
        self.pin(value["pid"], self.cell_cpu(reader.mode, epoch))
        value["epoch"], value["cpu"] = epoch, self.cell_cpu(reader.mode, epoch)
        with category("observer"):
            if (
                reader.connection.execute("SELECT pg_backend_pid()", prepare=False).fetchone()[0]
                != value["pid"]
            ):
                raise RuntimeError("Main connection/backend replaced")
        self.emit("placement", dict(kind="epoch", **value))

    @observed
    def process(self, pid, start, cpu):
        st = self.stat(pid)
        status = fields(self.read(self.root / str(pid) / "status"))
        io = fields(self.read(self.root / str(pid) / "io"))
        mask = self.mask(pid)
        if (
            int(status["Pid"]) != pid
            or int(status["PPid"]) != st["ppid"]
            or status.get("NSpid")
            and int(status["NSpid"].split()[-1]) != pid
            or st["starttime"] != start
            or mask != {cpu}
            or cpu_list(status["Cpus_allowed_list"]) != {cpu}
            or st["processor"] != cpu
            or st["state"] in {"Z", "X"}
            or (pid != self.client and int(status["Threads"]) != 1)
            or (
                pid == self.client
                and self.client_threads is not None
                and int(status["Threads"]) != self.client_threads
            )
        ):
            raise RuntimeError("Process replaced, migrated or unexpected thread/affinity")
        rss = int(status["VmRSS"].split()[0])
        hwm = int(status["VmHWM"].split()[0])
        if min(rss, hwm) < 0 or hwm < rss:
            raise RuntimeError("Invalid process memory counter")
        self.peak_rss_kib[pid] = max(self.peak_rss_kib.get(pid, 0), hwm)
        result = dict(
            stat=st,
            rss_kib=rss,
            high_water_kib=hwm,
            affinity=sorted(mask),
            allowed_cpus=status["Cpus_allowed_list"],
            threads=int(status["Threads"]),
            status_pid=int(status["Pid"]),
            status_ppid=int(status["PPid"]),
            context_switches={
                k: int(status[k]) for k in ("voluntary_ctxt_switches", "nonvoluntary_ctxt_switches")
            },
            namespace_pids=status.get("NSpid"),
            memory_allowed=status["Mems_allowed_list"],
            io={k: int(io[k]) for k in ("read_bytes", "write_bytes")},
        )
        if self.optional.get(pid, self.optional_schedstat):
            values = [int(v) for v in self.read(self.root / str(pid) / "schedstat").split()]
            if len(values) != 3 or min(values) < 0:
                raise ValueError("Invalid optional schedstat counter")
            result["schedstat"] = dict(
                cpu_ns=values[0],
                runqueue_ns=values[1] if self.scheduler_enabled else None,
                timeslices=values[2],
                wait_enabled=self.scheduler_enabled,
            )
        counters = {k: st[k] for k in ("minflt", "majflt", "utime", "stime")}
        counters.update(result["io"])
        counters.update(result["context_switches"])
        counters.update(
            {
                "sched_" + k: v
                for k, v in result.get("schedstat", {}).items()
                if k != "wait_enabled" and v is not None
            }
        )
        key = (pid, start)
        if any(v < 0 or v < self.previous.get(key, {}).get(k, 0) for k, v in counters.items()):
            raise RuntimeError("Invalid/decreasing process counter")
        self.previous[key] = counters
        return result

    @observed
    def server(self, cell, admin_pid, work):
        pm = int((Path(work) / "pgdata/postmaster.pid").read_text().splitlines()[0])
        cpu = self.layout["selected"][3]
        self.pin(pm, cpu)
        for kind, pid in [("postmaster", pm), ("admin", admin_pid)]:
            st = self.stat(pid)
            if kind == "admin" and st["ppid"] != pm:
                raise RuntimeError("Administrator server parent differs")
            self.servers[cell + "/" + kind] = dict(
                pid=pid, starttime=st["starttime"], cpu=cpu, postmaster=pm
            )
        for v in self.servers.values():
            if v["pid"] not in self.optional:
                self.optional[v["pid"]] = (
                    self.optional_schedstat
                    and self.optional_read(self.root / str(v["pid"]) / "schedstat") is not None
                )
        self.emit(
            "placement",
            dict(
                kind="server",
                cell=cell,
                processes={k: v for k, v in self.servers.items() if k.startswith(cell + "/")},
            ),
        )

    @observed
    def context(self, boundary, readers):
        """Optional context only at fixed boundaries; availability never changes work."""
        records = {}
        server_rows = {
            name: self.process(v["pid"], v["starttime"], v["cpu"])
            for name, v in self.servers.items()
        }
        self.emit("server-observations", dict(boundary=boundary, processes=server_rows))
        for pid in sorted({self.client, *(r.physical["pid"] for r in readers)}):
            path = self.root / str(pid) / "numa_maps"
            key = "numa/" + str(pid)
            if key not in self.context_capability:
                value = self.optional_read(path)
                self.context_capability[key] = value is not None
            elif self.context_capability[key]:
                value = self.read(path)
            else:
                value = None
            records[key] = value
        for cpu in self.layout["selected"]:
            for name in ("scaling_governor", "scaling_cur_freq"):
                path = Path("/sys/devices/system/cpu") / ("cpu" + str(cpu)) / "cpufreq" / name
                key = str(cpu) + "/" + name
                if key not in self.context_capability:
                    value = self.optional_read(path)
                    self.context_capability[key] = value is not None
                elif self.context_capability[key]:
                    value = self.read(path)
                else:
                    value = None
                records[key] = value
        self.emit(
            "context",
            dict(boundary=boundary, capability=self.context_capability.copy(), values=records),
        )

    @observed
    def sample(self, reader, boundary, **meta):
        self.budget.check()
        if self.bundles >= 5500:
            raise RuntimeError("Telemetry bundle cap exhausted")
        start = time.perf_counter_ns()
        self.bundles += 1
        record = reader.physical.copy()
        backend = self.process(record["pid"], record["starttime"], record["cpu"])
        if backend["stat"]["ppid"] != record["postmaster"]:
            raise RuntimeError("Backend server/parent changed")
        client = self.process(self.client, self.client_start, self.layout["selected"][0])
        end = time.perf_counter_ns()
        row = dict(
            boundary=boundary,
            identity=record,
            backend=backend,
            client=client,
            start_ns=start,
            end_ns=end,
            outer_ms=(end - start) / 1e6,
            **meta,
        )
        self.emit("telemetry", row)
        if self.elapsed_ns > 60 * 10**9:
            raise RuntimeError("Telemetry wall-time cap exhausted")
        return row

    def charges(self):
        return dict(
            bundles=self.bundles,
            proc_reads=self.reads,
            affinity_operations=self.affinity,
            telemetry_seconds=self.elapsed_ns / 1e9,
            observed_peak_rss_kib=self.peak_rss_kib,
            peak_scope="sampled process high-water values; not simultaneous allocation peak",
        )
