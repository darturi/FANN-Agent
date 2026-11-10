"""Bounded admission reads within a prepaid slice of the original shared ledger."""

import os
from au_kernel import MAX_READ

PROCESS_READ_LIMIT = 8
CONTROL_RESERVE_READS = 128
CONTROL_RESERVE_BYTES = CONTROL_RESERVE_READS * (MAX_READ + 1)
_reads = 0
_ALLOWED = frozenset(("self/mountinfo", "self/cgroup", "sys/kernel/random/boot_id"))


def control_read(name):
    global _reads
    if name not in _ALLOWED:
        raise ValueError("Only frozen admission proc files allowed")
    if _reads >= PROCESS_READ_LIMIT:
        raise RuntimeError("Original prepaid control-read slice exhausted")
    _reads += 1
    fd = os.open("/proc/" + name, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        data = bytearray()
        while True:
            block = os.read(fd, min(4096, MAX_READ + 1 - len(data)))
            data.extend(block)
            if len(data) > MAX_READ:
                raise RuntimeError("Original64KiB per-proc-file limit exceeded")
            if not block:
                return data.decode("utf-8", "surrogateescape")
    finally:
        os.close(fd)


def prepay(ledger):
    ledger.reserve(reads=CONTROL_RESERVE_READS, bytes=CONTROL_RESERVE_BYTES)
    return {
        "reads": CONTROL_RESERVE_READS,
        "bytes": CONTROL_RESERVE_BYTES,
        "maximum_control_processes": 9,
        "per_process_reads": PROCESS_READ_LIMIT,
        "same_original_combined_ledger": True,
    }
