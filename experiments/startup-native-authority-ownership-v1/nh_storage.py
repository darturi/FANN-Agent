"""Strict observation reconciliation and verified staging composition."""

import os
import re
from pathlib import Path

from nh_common import closed_native, compat, config, private

compat()
from policy import assess_storage
from policy import launch_admission as launch_admission
from policy import ready_admission as ready_admission
from staging import binding_layout, stage_exact


def mount_record(text, path):
    path = Path(path)
    records = []
    for line in text.splitlines():
        parts = line.split()
        separator = parts.index("-") if "-" in parts else -1
        if separator < 6 or len(parts) < separator + 4:
            raise ValueError("Incomplete mountinfo")
        mount = parts[4]
        if "\\" in mount:
            raise ValueError("Escaped/ambiguous mount path not admitted")
        if not Path(mount).is_absolute() or not re.fullmatch("[0-9]+:[0-9]+", parts[2]):
            raise ValueError("Invalid mount identity")
        if path == Path(mount) or path.is_relative_to(mount):
            records.append({"mount": mount, "device": parts[2], "filesystem": parts[separator + 1]})
    if not records:
        raise ValueError("No covering mount")
    records.sort(key=lambda r: len(r["mount"]), reverse=True)
    if len(records) > 1 and records[0]["mount"] == records[1]["mount"]:
        raise ValueError("Ambiguous covering mount")
    return records[0]


def admit_observation(observed, mountinfo, plan, uid):
    m = mount_record(mountinfo, observed["path"])
    if (
        m["device"] != observed["device"]
        or m["device"] != observed["mount_device"]
        or m["filesystem"] != observed["filesystem"]
    ):
        raise ValueError("Observed device/filesystem differs from mountinfo")
    return assess_storage(observed, plan, uid)


def observe_candidate(path, mountinfo, quota, placement, job_id):
    """Read-only local counters; supplied site authority remains explicit/unqualified."""
    p = private(path)
    s = p.stat()
    fs = os.statvfs(p)
    if (
        not isinstance(job_id, str)
        or not re.fullmatch("[1-9][0-9]*", job_id)
        or placement
        != {"path": str(p), "job_id": job_id, "node_local": True, "authority": "site_verified"}
    ):
        raise ValueError("Job-private placement authority required")
    m = mount_record(mountinfo, p)
    device = str(os.major(s.st_dev)) + ":" + str(os.minor(s.st_dev))
    if device != m["device"]:
        raise ValueError("Actual stat device differs from mount record")
    if (
        quota.get("uid") != os.getuid()
        or quota.get("device") != device
        or quota.get("authority") != "site_verified"
    ):
        raise ValueError("User/device quota authority required")
    return {
        "path": str(p),
        "filesystem": m["filesystem"],
        "device": device,
        "mount_device": m["device"],
        "uid": s.st_uid,
        "mode": s.st_mode & 0o777,
        "free_bytes": fs.f_bavail * fs.f_frsize,
        "free_inodes": fs.f_favail,
        "allocation_block_bytes": fs.f_frsize,
        "ram_backed": False,
        "shared": False,
        "quota_status": quota["status"],
        "quota_free_bytes": quota["free_bytes"],
        "quota_free_inodes": quota["free_inodes"],
        "synthetic": False,
    }


def admit_persistent(observed, uid):
    required = {
        "uid",
        "mode",
        "free_bytes",
        "free_inodes",
        "quota_status",
        "quota_free_bytes",
        "quota_free_inodes",
    }
    if (
        set(observed) != required
        or type(observed["uid"]) is not int
        or observed["uid"] != uid
        or observed["mode"] != 0o700
    ):
        raise ValueError("Complete owned persistent observation required")
    for key in ("free_bytes", "free_inodes", "quota_free_bytes", "quota_free_inodes"):
        if type(observed[key]) is not int or observed[key] < 0:
            raise ValueError("Strict persistent capacity counters required")
    if observed["quota_status"] != "finite_verified":
        raise ValueError("Authoritative persistent user quota required")
    if (
        min(observed["free_bytes"], observed["quota_free_bytes"]) < 128 * 1024**2
        or min(observed["free_inodes"], observed["quota_free_inodes"]) < 1000
    ):
        raise ValueError("Original persistent quota/headroom insufficient")
    return {"conditional_persistent_policy_pass": True, "native_release": False}


def stage(archive, original, destination, semantic_verifier):
    c = config()
    private(Path(destination).parent)
    materialize = stage_exact
    if os.environ.get("SLURM_JOB_ID") or os.environ.get("SLURM_ARRAY_JOB_ID"):
        closed_native()
        from nh_materialize import stage_exact as materialize
    return materialize(
        archive,
        original,
        destination,
        c["original_archive_sha256"],
        c["original_manifest_sha256"],
        semantic_verifier,
    )


def draft_command(package, integration, result, work, image, executable, deadline):
    c = config()
    if type(deadline) not in (float, int):
        raise ValueError("Finite deadline required")
    from math import isfinite

    if not isfinite(deadline) or deadline <= 0:
        raise ValueError("Finite deadline required")
    bindings = binding_layout(package, Path("/Users/danielarturi/Developer/JinyangLiWork"))[
        "bindings"
    ]
    bindings += [
        {"source": str(integration), "destination": "/integration", "mode": "ro"},
        {"source": str(result), "destination": "/results", "mode": "rw"},
        {"source": str(work), "destination": "/work", "mode": "rw"},
    ]
    argv = [str(executable), "exec", "--cleanenv", "--containall", "--no-home", "--pwd", "/work"]
    for row in bindings:
        for p in (row["source"], row["destination"]):
            if not Path(p).is_absolute() or any(x in p for x in (":", ",", "\n", "\r")):
                raise ValueError("Unsafe bind")
        argv += ["--bind", row["source"] + ":" + row["destination"] + ":" + row["mode"]]
    for p in (image, executable):
        if not Path(p).is_absolute() or any(x in str(p) for x in (":", ",", "\n", "\r")):
            raise ValueError("Unsafe image/executable path")
    argv += [
        "--env",
        "PYTHONPATH=/integration:/qual:/opt/torch-reviews/vendor",
        "--env",
        "PYTHONUNBUFFERED=1",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "OPENBLAS_NUM_THREADS=1",
        "--env",
        "OMP_NUM_THREADS=1",
        "--env",
        "TMPDIR=/work/tmp",
        "--env",
        "QX_DEADLINE=" + str(deadline),
        str(image),
        "python",
        "/integration/nh_guest.py",
    ]
    return {
        "argv": argv,
        "bindings": bindings,
        "dispatchable": False,
        "executed": False,
        "native_release": False,
        "limits": c["limits"],
    }


if __name__ == "__main__":
    closed_native()
