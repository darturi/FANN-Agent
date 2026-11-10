"""Data-only budget/storage admission; never grants a native allowance."""

import math
import re
from pathlib import PurePosixPath

FREE_BYTES = 8 * 1024**3
FREE_INODES = 30000


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def launch_admission(started, now):
    if not finite(started) or not finite(now) or now < started or now + 30 > started + 240:
        raise RuntimeError("Full startup reserve does not fit original preflight")
    return {
        "last_launch": started + 210,
        "guest_ready_deadline": started + 240,
        "native_release": False,
    }


def ready_admission(started, now):
    if (
        not finite(started)
        or not finite(now)
        or now < started
        or now + 3000 + 240 + 120 > started + 3600
    ):
        raise RuntimeError("Complete guest/post/outer reserve unavailable")
    return {
        "guest_end": now + 3000,
        "post_deadline": started + 3480,
        "whole_deadline": started + 3600,
        "guest_cleanup_included_seconds": 600,
        "native_release": False,
    }


def assess_storage(observed, plan, uid):
    required = {
        "path",
        "filesystem",
        "device",
        "mount_device",
        "uid",
        "mode",
        "free_bytes",
        "free_inodes",
        "allocation_block_bytes",
        "ram_backed",
        "shared",
        "quota_status",
        "quota_free_bytes",
        "quota_free_inodes",
        "synthetic",
    }
    if set(observed) != required:
        raise ValueError("Complete storage observation required")
    path = PurePosixPath(observed["path"])
    if (
        not path.is_absolute()
        or ".." in path.parts
        or observed["filesystem"] not in ("ext4", "xfs")
    ):
        raise ValueError("Admitted disk filesystem and absolute path required")
    if (
        type(observed["uid"]) is not int
        or observed["uid"] != uid
        or type(observed["mode"]) is not int
        or observed["mode"] != 0o700
    ):
        raise ValueError("Private owned job directory required")
    if (
        type(observed["device"]) is not str
        or not re.fullmatch(r"[0-9]+:[0-9]+", observed["device"])
        or observed["device"] != observed["mount_device"]
    ):
        raise ValueError("Mount/device identity differs")
    if (
        observed["ram_backed"] is not False
        or observed["shared"] is not False
        or type(observed["synthetic"]) is not bool
    ):
        raise ValueError("Disk-backed unshared evidence required")
    for key in ("free_bytes", "free_inodes", "allocation_block_bytes"):
        if type(observed[key]) is not int or observed[key] <= 0:
            raise ValueError("Strict positive storage counters required")
    if not 512 <= observed["allocation_block_bytes"] <= 4096 or observed[
        "allocation_block_bytes"
    ] & (observed["allocation_block_bytes"] - 1):
        raise ValueError("Recompute plan for allocation block")
    if observed["quota_status"] == "finite_verified":
        quota = observed["quota_free_bytes"]
        if type(quota) is not int or quota < 0:
            raise ValueError("Finite user quota required")
        if type(observed["quota_free_inodes"]) is not int or observed["quota_free_inodes"] < 0:
            raise ValueError("Finite user inode quota required")
        available = min(quota, observed["free_bytes"])
        available_inodes = min(observed["quota_free_inodes"], observed["free_inodes"])
    elif (
        observed["quota_status"] == "not_applicable_verified"
        and observed["quota_free_bytes"] is None
        and observed["quota_free_inodes"] is None
    ):
        available = observed["free_bytes"]
        available_inodes = observed["free_inodes"]
    else:
        raise ValueError("Unknown user quota cannot be admitted")
    if (
        type(plan["planned_bytes"]) is not int
        or type(plan["planned_inodes"]) is not int
        or not 0 < plan["planned_bytes"] <= FREE_BYTES
        or not 0 < plan["planned_inodes"] <= FREE_INODES
    ):
        raise ValueError("Plan exceeds unchanged capacity guards")
    if available < FREE_BYTES or available_inodes < FREE_INODES:
        raise ValueError("Insufficient unchanged storage headroom")
    return {
        "conditional_capacity_policy_pass": True,
        "synthetic": observed["synthetic"],
        "native_storage_qualified": False,
        "native_release": False,
    }
