"""Bounded supervisor for host sampler and zero-search container startup."""

import subprocess
import time
from pathlib import Path

from pc_common import read, save


def start_sampler(package, out, python, parent_pid, run=subprocess.Popen):
    process = run(
        [
            str(python),
            str(package / "sr_sampler.py"),
            "--out",
            str(out),
            "--parent-pid",
            str(parent_pid),
        ]
    )
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            health = out / "memory-health.json"
            if health.exists():
                value = read(health)
                if value["status"] != "running":
                    raise RuntimeError("Memory sampler failed before startup")
                return process
            if process.poll() is not None:
                raise RuntimeError("Memory sampler exited before readiness")
            time.sleep(0.1)
        raise RuntimeError("Memory sampler readiness timeout")
    except BaseException:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        else:
            process.wait(timeout=5)
        raise


def monitor(process, sampler, out, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + 3030
    requested = False
    while process.poll() is None:
        unhealthy = sampler.poll() is not None
        path = Path(out) / "memory-health.json"
        if path.exists():
            health = read(path)
            unhealthy = (
                unhealthy
                or health["status"] != "running"
                or time.monotonic_ns() - health.get("last_ns", 0) > 5 * 10**9
            )
        if unhealthy and not requested:
            process.terminate()  # container handler enters bounded cleanup
            requested = True
        if clock() >= deadline:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            raise TimeoutError("Resource runtime envelope exhausted")
        sleep(0.25)
    if requested:
        raise RuntimeError("Required memory sampler lost; startup cannot qualify")
    return process.returncode


def stop_sampler(process, out):
    if process is None:
        return
    stop = Path(out) / "memory-stop.json"
    if not stop.exists():
        save(stop, dict(stop=True))
    if process.poll() is None:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    summary = Path(out) / "memory-summary.json"
    if process.returncode or not summary.exists() or read(summary)["status"] != "complete":
        raise RuntimeError("Memory sampler did not complete")
