"""Absolute host envelope; termination and sampler stop consume the 240s post phase."""

import subprocess
import time
from pathlib import Path

from pc_common import read


class Envelope:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.started = clock()
        self.pre_deadline = self.started + 240
        self.final_deadline = self.started + 3480
        self.runtime_started = self.runtime_deadline = self.post_started = self.post_deadline = None

    def check(self, deadline):
        if self.clock() >= deadline:
            raise TimeoutError("Frozen host phase deadline exhausted")

    def runtime(self):
        self.check(self.pre_deadline)
        self.runtime_started = self.clock()
        self.runtime_deadline = min(self.runtime_started + 3000, self.final_deadline - 240)
        return self.runtime_deadline

    def post(self):
        self.post_started = self.clock()
        self.post_deadline = min(self.post_started + 240, self.final_deadline)
        self.check(self.post_deadline)
        return self.post_deadline

    def proof(self):
        self.check(self.post_deadline)
        return dict(
            started=self.started,
            pre_deadline=self.pre_deadline,
            runtime_started=self.runtime_started,
            runtime_deadline=self.runtime_deadline,
            post_started=self.post_started,
            post_deadline=self.post_deadline,
            finished=self.clock(),
            final_deadline=self.final_deadline,
            wall_seconds=3600,
            outer_margin_seconds=120,
            termination_and_sampler_stop_inside_post=True,
        )


def monitor(process, sampler, out, deadline, clock=time.monotonic, sleep=time.sleep):
    requested = False
    while process.poll() is None:
        unhealthy = sampler.poll() is not None
        health_path = Path(out) / "memory-health.json"
        if not health_path.exists():
            unhealthy = True
        else:
            health = read(health_path)
            unhealthy = (
                unhealthy
                or health["status"] != "running"
                or time.monotonic_ns() - health.get("last_ns", 0) > 5 * 10**9
            )
        if unhealthy and not requested:
            process.terminate()
            requested = True
        if clock() >= deadline:
            raise TimeoutError("Container runtime envelope exhausted; bounded host post follows")
        sleep(min(0.25, max(0, deadline - clock())))
    if requested:
        raise RuntimeError("Required memory sampler lost; resource qualification held")
    return process.returncode


def stop_child(process, deadline, clock=time.monotonic):
    if process is None:
        return
    if clock() >= deadline:
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=0)
        except subprocess.TimeoutExpired:
            pass
        raise TimeoutError("No host-post time remains; owned child killed without extra wait")
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=max(0.001, min(10, deadline - clock())))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=max(0.001, min(10, deadline - clock())))
    else:
        process.wait(timeout=max(0.001, min(1, deadline - clock())))
    if clock() >= deadline:
        raise TimeoutError("Child reaping exhausted host-post deadline")
