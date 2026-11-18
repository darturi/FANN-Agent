"""One allocation per episode. All clocks include waiting and compilation."""

import hashlib
import json
import os
import time
from pathlib import Path

WALL_SECONDS = 21600
ADMISSION_SECONDS = 18900
WORK_SECONDS = 20400
IDLE_SECONDS = 900
ATTEMPT_LIMIT = 300000
SCREEN_GROUPS = 64
FILTERS = (-1, 743, 527, 310, 192, 108, 32)
SCHEMA = "fannagent.torch-live.v1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    with Path(path).open("rb") as handle:
        result = hashlib.sha256()
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
        return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    """Publish complete records; preserve an old receipt if a writer is interrupted."""
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(canonical(value).decode() + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


class Deadline:
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self.start = clock()

    def remaining(self):
        return max(0, WORK_SECONDS - (self.clock() - self.start))

    def admit(self):
        if self.clock() - self.start >= ADMISSION_SECONDS:
            raise TimeoutError("no new batch after 5h15m; this allocation is never extended")
