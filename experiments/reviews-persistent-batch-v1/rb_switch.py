"""Held diagnostic for reader switches and repeated chunk order."""

import ctypes
import os
import struct
from collections import Counter, defaultdict
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from functools import partial
from pathlib import Path
from statistics import fmean
from typing import NamedTuple

import rb_calibration
import rb_interleave as paired
import rb_persistent
from rb_measure import check_timed
from rb_plan import SESSION_LENGTH, digest, require
from rb_verify import check_identity, check_requests

PATTERNS = ("AA", "BB", "AB", "BA")
CONDITIONS = tuple((enter, pair) for enter in paired.LABELS for pair in PATTERNS)
ORDER = (0, 1, 7, 2, 6, 3, 5, 4)
VERDICTS = ("reader_switch_diagnostic_complete",)
WORKLOADS = len(paired.PROBE_BLOCKS) * len(paired.FAMILIES)
CHUNKS = rb_persistent.STEADY_REQUESTS // paired.CHUNK
EVENTS = ("cycles", "instructions", "cache_misses")
PERF_CONFIGS = (0, 1, 3)
PERF_READ = struct.Struct("=6Q")
# Linux x86-64 perf_event_open, PERF_FORMAT_GROUP plus enabled and running times.
PERF_SYSCALL = 298
PERF_READ_FORMAT = 1 | 2 | 8
PERF_USER_ONLY = (1 << 5) | (1 << 6)
PERF_CLOSE_ON_EXEC = 1 << 3
OBSERVATIONS = ("wall_ns", "server_command_us", *paired.COUNTERS, *EVENTS)


class Meter(paired.Meter):
    reader_limits = {"reference": 1, "timing": 2 * WORKLOADS}
    search_limits = {
        "timing": WORKLOADS * (2 * SESSION_LENGTH + CHUNKS * len(CONDITIONS) * 3 * paired.CHUNK)
    }
    install_limits = {"timing": 2 * len(paired.PROBE_BLOCKS)}


class Step(NamedTuple):
    label: str
    offset: int
    count: int
    condition: str
    phase: str


def attach(stage):
    paired.attach(stage)
    stage.study_identity = digest(
        {
            "schema": "reviews-persistent-batch.reader-switch.v1",
            "seed": stage.evidence.identities["seed"],
            "blocks": paired.PROBE_BLOCKS,
            "chunk": paired.CHUNK,
            "conditions": CONDITIONS,
            "order": ORDER,
            "search_cap": Meter.search_limits["timing"],
        }
    )


def schedule(plan, evidence):
    for epoch, session, arm in rb_persistent.schedule(plan, evidence):
        if epoch != 0:
            break
        if arm == "native-A" and session.block in paired.PROBE_BLOCKS:
            for family in paired.family_order(epoch, session.block):
                yield True, epoch, session, family


def steps(session, family):
    index = paired.PROBE_BLOCKS.index(session.block) * len(paired.FAMILIES) + paired.FAMILIES.index(
        family
    )
    labels = paired.LABELS if index % 2 == 0 else paired.LABELS[::-1]
    for label in labels:
        yield Step(label, 0, SESSION_LENGTH, "warmup", "warmup")
    for chunk in range(CHUNKS):
        offset = SESSION_LENGTH + chunk * paired.CHUNK
        shift = chunk + 2 * index
        for slot in ORDER:
            entering, pattern = CONDITIONS[(slot + shift) % len(CONDITIONS)]
            condition = f"{entering}:{pattern}"
            yield Step(entering, offset - paired.CHUNK, paired.CHUNK, condition, "condition")
            yield Step(pattern[0], offset, paired.CHUNK, condition, "first")
            yield Step(pattern[1], offset, paired.CHUNK, condition, "second")


def last_cpu(pid):
    # The processor field is field 39. The split begins at field 3 after comm.
    try:
        stat = (Path("/proc") / str(pid) / "stat").read_text()
        return int(stat.rsplit(")", 1)[1].split()[36])
    except (OSError, ValueError, IndexError):
        return None


def perf_snapshot(fd):
    if fd is None:
        return None
    try:
        raw = os.read(fd, PERF_READ.size)
    except OSError:
        return None
    if len(raw) != PERF_READ.size:
        return None
    count, enabled, running, *values = PERF_READ.unpack(raw)
    require(count == len(EVENTS), "Backend performance counter group changed")
    return (enabled, running, *values)


def perf_delta(before, after):
    if before is None or after is None:
        return None
    enabled, running, *values = (b - a for a, b in zip(before, after, strict=True))
    require(0 <= running <= enabled and min(values) >= 0, "Invalid performance counter delta")
    return {
        "enabled_ns": enabled,
        "running_ns": running,
        **dict(zip(EVENTS, values, strict=True)),
    }


@contextmanager
def perf_group(pid):
    """Open unprivileged user-space counting events on this private backend only."""
    if os.uname().sysname != "Linux" or os.uname().machine != "x86_64":
        yield None, "unsupported_platform"
        return
    syscall = ctypes.CDLL(None, use_errno=True).syscall
    syscall.restype = ctypes.c_long
    with ExitStack() as stack:
        leader = -1
        for config in PERF_CONFIGS:
            # PERF_ATTR_SIZE_VER0 is the stable 64-byte prefix.
            raw = struct.pack(
                "=IIQQQQQIIQ", 0, 64, config, 0, 0, PERF_READ_FORMAT, PERF_USER_ONLY, 0, 0, 0
            )
            attr = ctypes.create_string_buffer(raw)
            fd = syscall(
                ctypes.c_long(PERF_SYSCALL),
                ctypes.byref(attr),
                ctypes.c_int(pid),
                ctypes.c_int(-1),
                ctypes.c_int(leader),
                ctypes.c_ulong(PERF_CLOSE_ON_EXEC),
            )
            if fd < 0:
                reason = f"errno_{ctypes.get_errno()}"
                stack.close()
                yield None, reason
                return
            stack.callback(os.close, fd)
            if leader < 0:
                leader = fd
        yield leader, "opened"


class Diagnostics(paired.Diagnostics):
    def __init__(self, runner, work):
        super().__init__(runner, work)
        self.fds = {}

    @contextmanager
    def monitor(self, pid):
        with perf_group(pid) as (fd, status):
            self.fds[pid] = fd
            try:
                yield status
            finally:
                del self.fds[pid]

    def before(self, pid):
        return super().before(pid), last_cpu(pid), perf_snapshot(self.fds[pid])

    def after(self, pid, before):
        original, processor, counters = before
        end_counters = perf_snapshot(self.fds[pid])
        end_processor = last_cpu(pid)
        return {
            **super().after(pid, original),
            "last_cpu_before": processor,
            "last_cpu_after": end_processor,
            "perf": perf_delta(counters, end_counters),
        }


make_backend = partial(paired.make_backend, diagnostics_class=Diagnostics)


def collect(plan, frozen, evidence, readers, meter, item, diagnostics):
    _, epoch, session, family = item
    policy = evidence.policies.get(family)
    plan_steps = tuple(steps(session, family))
    clock = meter.clock
    started = clock()
    chunks = []
    with ExitStack() as stack:
        for step in plan_steps[:2]:
            stack.enter_context(readers[step.label].reader("timing"))
        require(meter.live_readers == 2, "Both readers must be admitted")
        identities = {label: readers[label]._identity for label in paired.LABELS}
        require(identities["A"] != identities["B"], "Reader connections are not distinct")
        availability = {
            label: stack.enter_context(diagnostics.monitor(identities[label][0]))
            for label in paired.LABELS
        }
        bound = (
            {
                label: frozen.execution.session(readers[label], policy, plan.config)
                for label in paired.LABELS
            }
            if policy
            else {}
        )
        admitted = clock()
        for step in plan_steps:
            cases = session.cases[step.offset : step.offset + step.count]
            probe = diagnostics if step.phase in {"first", "second"} else None
            block = paired.collect_chunk(
                frozen,
                evidence,
                readers[step.label],
                bound.get(step.label),
                meter,
                family,
                cases,
                probe,
            )
            chunks.append({"step": list(step), **block})
        closing = clock()
    return {
        "epoch": epoch,
        "session_id": session.id,
        "family": family,
        "identities": identities,
        "perf_availability": availability,
        "boundary_ns": [started, admitted, closing, clock()],
        "chunks": chunks,
    }


capture = partial(paired.capture, run_schedule=schedule, collector=collect)


def observations(record, active, availability):
    raw = record["diagnostics"]
    if not active:
        paired.verify_diagnostic(record, False)
        return {}
    extras = {"last_cpu_before", "last_cpu_after", "perf"}
    require(extras <= raw.keys(), "Missing processor observations")
    ordinary = {key: value for key, value in raw.items() if key not in extras}
    paired.verify_diagnostic({**record, "diagnostics": ordinary}, True)
    processors = [raw["last_cpu_before"], raw["last_cpu_after"]]
    require(
        all(cpu is None or (type(cpu) is int and cpu >= 0) for cpu in processors),
        "Invalid processor observation",
    )
    values = {key: ordinary[key] for key in ("server_command_us", *paired.COUNTERS)}
    begin, end = record["request_ns"]
    values["wall_ns"] = end - begin
    perf = raw["perf"]
    if perf is not None:
        require(
            availability == "opened"
            and set(perf) == {"enabled_ns", "running_ns", *EVENTS}
            and all(type(v) is int and v >= 0 for v in perf.values())
            and perf["running_ns"] <= perf["enabled_ns"],
            "Invalid performance sample",
        )
        if 0 < perf["running_ns"] == perf["enabled_ns"]:
            values.update({key: perf[key] for key in EVENTS})
    return {key: value for key, value in values.items() if value is not None}


def verify_pair(row, item, evidence, seen, previous):
    _, epoch, session, family = item
    require(
        (row["epoch"], row["session_id"], row["family"]) == (epoch, session.id, family),
        "Switch diagnostic schedule changed",
    )
    start, admitted, closing, closed = row["boundary_ns"]
    require(previous <= start <= admitted < closing <= closed, "Pair boundaries changed")
    require(
        set(row["identities"]) == set(row["perf_availability"]) == set(paired.LABELS),
        "Pair identities changed",
    )
    for label in paired.LABELS:
        check_identity({"reader": row["identities"][label]}, seen)
    expected = {label: [] for label in paired.LABELS}
    actual = {label: [] for label in paired.LABELS}
    cells = defaultdict(list)
    placement = Counter()
    cpus = {label: Counter() for label in paired.LABELS}
    previous = admitted
    last_reader = None
    for entry, step in zip(row["chunks"], steps(session, family), strict=True):
        require(entry["step"] == list(step), "Switch condition order changed")
        begin, end = entry["span_ns"]
        require(previous <= begin < end <= closing, "Chunks overlap or escape pair")
        measured = step.phase in {"first", "second"}
        for position, (case, record) in enumerate(
            zip(
                session.cases[step.offset : step.offset + step.count],
                entry["requests"],
                strict=True,
            ),
            1,
        ):
            left, right = record["request_ns"]
            require(
                begin <= left < right <= end and case.id == record["query_id"],
                "Request order or timing changed",
            )
            check_timed(evidence, evidence.outcomes, family, record)
            values = observations(record, measured, row["perf_availability"][step.label])
            if measured:
                require(
                    record["installations"] == 0 and last_reader in paired.LABELS,
                    "Measured request installed a policy or lost reader continuity",
                )
                switched = last_reader != step.label
                for name, value in values.items():
                    cells[step.offset, position, name, step.phase, switched].append(value)
                raw = record["diagnostics"]
                a, b = raw["last_cpu_before"], raw["last_cpu_after"]
                if a is not None and b is not None:
                    placement["endpoint_pairs"] += 1
                    placement["different_cpu_endpoints"] += int(a != b)
                if b is not None:
                    cpus[step.label][str(b)] += 1
            expected[step.label].append(case)
            actual[step.label].append(record)
            begin = right
        last_reader = step.label
        previous = end
    installs = sum(
        check_requests(
            replace(session, cases=tuple(expected[label])),
            family,
            evidence,
            {"requests": actual[label]},
        )
        for label in paired.LABELS
    )
    return (
        closed,
        installs,
        cells,
        {
            "endpoint_pairs": placement["endpoint_pairs"],
            "different_cpu_endpoints": placement["different_cpu_endpoints"],
            "last_cpu_after_by_reader": {label: dict(counts) for label, counts in cpus.items()},
        },
    )


def summarize(cells):
    by_position = {}
    for position in range(1, paired.CHUNK + 1):
        result = {}
        for name in OBSERVATIONS:
            contrasts = defaultdict(list)
            for chunk in range(CHUNKS):
                offset = SESSION_LENGTH + chunk * paired.CHUNK
                values = [
                    cells.get((offset, position, name, phase, switched), [])
                    for phase in ("first", "second")
                    for switched in (False, True)
                ]
                if not all(len(v) == 4 for v in values):
                    continue
                first_stay, first_switch, second_stay, second_switch = map(fmean, values)
                contrasts["switch_cost_first"].append(first_switch - first_stay)
                contrasts["switch_cost_second"].append(second_switch - second_stay)
                contrasts["repeat_cost_stay"].append(second_stay - first_stay)
                contrasts["repeat_cost_switch"].append(second_switch - first_switch)
                contrasts["interaction"].append(
                    (second_switch - second_stay) - (first_switch - first_stay)
                )
            coverage = len(contrasts.get("switch_cost_first", ()))
            if name in {"wall_ns", "cpu_ns", "server_command_us"} or coverage:
                result[name] = {
                    "complete_matched_chunks": coverage,
                    "effects": {key: fmean(values) for key, values in contrasts.items()},
                }
        by_position[str(position)] = result
    return by_position


def reconstruct(directory, plan, _frozen, evidence, *, synthetic_only):
    rows, accounting = rb_calibration.completed_timing(directory, evidence, synthetic_only)
    seen, reports = set(), {}
    previous = installs = 0
    for row, item in zip(rows, schedule(plan, evidence), strict=True):
        previous, count, cells, placement = verify_pair(row, item, evidence, seen, previous)
        installs += count
        reports.setdefault(row["family"], {})[row["session_id"]] = {
            "perf_availability": row["perf_availability"],
            "processor_endpoint_coverage": placement,
            "matched_contrasts_by_request_position": summarize(cells),
        }
    rb_calibration.check_accounting(accounting, Meter, installs)
    return {
        "provisional_verdict": VERDICTS[0],
        "development_qualifier": False,
        "reader_switch_diagnostic": True,
        "synthetic_only": synthetic_only,
        "accounting": accounting,
        "workloads": reports,
    }
