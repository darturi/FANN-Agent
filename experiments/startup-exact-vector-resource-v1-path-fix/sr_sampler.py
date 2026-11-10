"""Separate host process observes memory through full startup despite client GIL work."""

import argparse
import json
import os
import signal
import time
from pathlib import Path

from pc_common import RESOURCE, read, replace, save
from pc_proc import select_cores
from sr_memory import Memory


def run(out, parent_pid, memory_factory=Memory, clock=time.monotonic, sleep=time.sleep):
    out = Path(out)
    limits = RESOURCE["resources"]
    cpu_start = time.process_time()
    begun = clock()
    count = written = 0
    error = None
    context = None
    ending = False

    def stop(*args):
        nonlocal ending
        ending = True

    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGUSR1]:
        signal.signal(sig, stop)
    trace = out / "memory.jsonl"
    try:
        allocation = select_cores(os.sched_getaffinity(0))
        selected = allocation["selected"]
        os.sched_setaffinity(0, {selected[3]})
        memory = memory_factory(parent_pid)
        if os.sched_getaffinity(0) != {selected[3]}:
            raise RuntimeError("Sampler CPU affinity readback failed")
        context = {
            **memory.context,
            "allocation": allocation,
            "sampler_cpu": selected[3],
            "sample_period_seconds": 1,
        }
        save(out / "memory-context.json", context)
        with trace.open("x") as handle:
            next_sample = clock()
            while True:
                if count >= limits["sampler_samples_max"]:
                    raise RuntimeError("Memory sample-count cap")
                phase = "host_preflight"
                progress = out / "progress.json"
                if progress.exists():
                    phase = read(progress)["phase"]
                row = memory.sample(phase)
                data = json.dumps(row, sort_keys=True, allow_nan=False) + "\n"
                written += len(data.encode())
                if written > limits["sampler_raw_bytes_max"]:
                    raise RuntimeError("Memory trace-byte cap")
                handle.write(data)
                handle.flush()
                count += 1
                cpu = time.process_time() - cpu_start
                if cpu > limits["sampler_cpu_seconds_max"]:
                    raise RuntimeError("Sampler CPU-time cap")
                replace(
                    out / "memory-health.json",
                    dict(
                        status="running",
                        samples=count,
                        last_ns=row["end_ns"],
                        file_reads=memory.read.files,
                        bytes_read=memory.read.bytes,
                        cpu_seconds=cpu,
                    ),
                )
                if ending or (out / "memory-stop.json").exists():
                    break
                if clock() - begun >= 3500:
                    raise RuntimeError("Sampler wall envelope exhausted")
                next_sample += 1
                sleep(max(0, next_sample - clock()))
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc))
    result = dict(
        status="failed" if error else "complete",
        samples=count,
        raw_bytes=written,
        cpu_seconds=time.process_time() - cpu_start,
        elapsed_seconds=clock() - begun,
        error=error,
        file_reads=memory.read.files if context else 0,
        bytes_read=memory.read.bytes if context else 0,
    )
    replace(out / "memory-health.json", result)
    save(out / "memory-summary.json", result)
    if error:
        raise RuntimeError("Memory sampler failed: " + error["message"])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--parent-pid", type=int, required=True)
    a = parser.parse_args()
    run(a.out, a.parent_pid)


if __name__ == "__main__":
    main()
