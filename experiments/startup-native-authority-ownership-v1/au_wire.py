"""Bounded inherited pipe frames with caller's absolute endpoint."""

import json
import os
import select
import time

from au_kernel import canonical

MAX_FRAME = 32768


class Pipe:
    def __init__(self, read, write):
        self.read, self.write = read, write
        self.buffer = bytearray()
        self.frames = 0
        os.set_blocking(read, False)
        os.set_blocking(write, False)

    def send(self, value, end):
        data = canonical(value) + b"\n"
        if len(data) > MAX_FRAME:
            raise ValueError("Control frame too large")
        offset = 0
        while offset < len(data):
            if time.monotonic() >= end:
                raise TimeoutError("Control write endpoint exhausted")
            if not select.select([], [self.write], [], min(0.05, end - time.monotonic()))[1]:
                continue
            offset += os.write(self.write, data[offset:])

    def receive(self, end, wait=True):
        while True:
            if b"\n" in self.buffer:
                raw, _, rest = self.buffer.partition(b"\n")
                self.buffer = bytearray(rest)
                self.frames += 1
                if self.frames > 65536:
                    raise RuntimeError("Control frame count bound exceeded")
                return json.loads(raw)
            if time.monotonic() >= end:
                raise TimeoutError("Control read endpoint exhausted")
            ready = select.select(
                [self.read], [], [], min(0.05, end - time.monotonic()) if wait else 0
            )[0]
            if not ready:
                if not wait:
                    return None
                continue
            data = os.read(self.read, 4096)
            if not data:
                raise EOFError("Owned control pipe lost")
            self.buffer.extend(data)
            if len(self.buffer) > MAX_FRAME:
                raise ValueError("Control frame exceeds bound")

    def close(self):
        for fd in (self.read, self.write):
            try:
                os.close(fd)
            except OSError:
                pass
