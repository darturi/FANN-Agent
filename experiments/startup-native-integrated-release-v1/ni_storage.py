"""Actual node-private disk admission with read-only kernel quota observation."""

import ctypes
import errno
import os

from nh_common import private
from nh_storage import mount_record


def quota_disabled(device):
    """Q_GETFMT for all three quota types. Unknown is never no-quota."""
    if not device.startswith("/dev/"):
        raise RuntimeError("Actual disk device required for quota query")
    libc = ctypes.CDLL(None, use_errno=True)
    records = []
    for kind in (0, 1, 2):
        fmt = ctypes.c_uint32()
        ctypes.set_errno(0)
        code = libc.quotactl((0x800004 << 8) | kind, device.encode(), 0, ctypes.byref(fmt))
        error = ctypes.get_errno()
        records.append({"type": kind, "returncode": code, "errno": error, "format": fmt.value})
        if code == 0 or error != errno.ESRCH:
            raise RuntimeError("Node disk quota is active or unproven; qualification held")
    return {"status": "not_applicable_verified", "kernel_queries": records}


def node_private(path, mountinfo):
    p = private(path)
    m = mount_record(mountinfo, p)
    if m["filesystem"] not in ("ext4", "xfs"):
        raise RuntimeError("Disk-backed node-local filesystem required")
    selected = []
    for line in mountinfo.splitlines():
        left, sep, right = line.partition(" - ")
        if sep and left.split()[4] == m["mount"]:
            selected.append(right.split()[1])
    if len(selected) != 1:
        raise RuntimeError("Unique node disk source required")
    q = quota_disabled(selected[0])
    s = os.statvfs(p)
    if s.f_bavail * s.f_frsize < 8 * 1024**3 or s.f_favail < 30000:
        raise RuntimeError("Original scratch headroom unavailable")
    return {
        "path": str(p),
        "filesystem": m["filesystem"],
        "device": m["device"],
        "disk_source": selected[0],
        "quota": q,
        "free_bytes": s.f_bavail * s.f_frsize,
        "free_inodes": s.f_favail,
        "node_private": True,
    }
