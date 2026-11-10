"""Explicit Torch installation-prefix policy; no generic non-root exception."""

import os
import stat
from pathlib import Path

import ni_site
from nh_common import digest, sha

ROOT_BINARY = ni_site.trusted_binary
POLICY = {
    "schema": "a3.torch.site.prefix.v1",
    "prefix": "/opt/slurm",
    "uid": 1001,
    "gid": 1001,
    "mode": 0o755,
    "clients": ["scontrol", "sbatch", "sacctmgr", "sacct", "squeue"],
    "basis": "NYU-published client prefix and independently observed root leaf/bin/parent layout",
}


def eligible(path, role):
    base = Path(POLICY["prefix"])
    if role == "binary":
        return path.parent == base / "bin" and path.name in POLICY["clients"]
    if role == "configuration":
        return path == base / "etc/slurm.conf"
    if role == "library":
        return path in (base / "lib", base / "lib64")
    return False


def exception_chain(path, role):
    path = Path(path).resolve(strict=True)
    if not eligible(path, role):
        raise ValueError("Outside the frozen site-prefix scope")
    if os.getuid() in (0, POLICY["uid"]):
        raise ValueError("Installation owner/privileged caller cannot use this exemption")
    rows = []
    exception = False
    for component in (path, *path.parents):
        info = component.stat()
        if component.is_symlink() or os.access(component, os.W_OK) or info.st_mode & 0o022:
            raise ValueError("Writable, linked or mutable site component: " + str(component))
        if component == Path(POLICY["prefix"]):
            if (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) != (
                POLICY["uid"],
                POLICY["gid"],
                POLICY["mode"],
            ) or not stat.S_ISDIR(info.st_mode):
                raise ValueError("Frozen installation owner/mode differs")
            exception = True
        elif info.st_uid != 0:
            raise ValueError("Root-owned leaf and all other ancestors required")
        rows.append(
            {
                "path": str(component),
                "uid": info.st_uid,
                "gid": info.st_gid,
                "mode": stat.S_IMODE(info.st_mode),
                "device": info.st_dev,
                "inode": info.st_ino,
                "ctime_ns": info.st_ctime_ns,
            }
        )
    if not exception:
        raise ValueError("Observed prefix was not present")
    return path, rows


def trusted_binary(path):
    try:
        return ROOT_BINARY(path)
    except ValueError:
        target, before = exception_chain(path, "binary")
        if not target.is_file() or not os.access(target, os.X_OK):
            raise ValueError("Root-owned installed executable required")
        value = sha(target)
        _, after = exception_chain(target, "binary")
        if before != after:
            raise RuntimeError("Site component generation changed during observation")
        s = target.stat()
        return {
            "path": str(target),
            "sha256": value,
            "device": s.st_dev,
            "inode": s.st_ino,
            "site_policy_sha256": digest(POLICY),
            "components": after,
        }


def trusted_data(path, role):
    p = Path(path).resolve(strict=True)
    try:
        for component in (p, *p.parents):
            s = component.stat()
            if (
                s.st_uid != 0
                or s.st_mode & 0o002
                or (s.st_mode & 0o020 and os.access(component, os.W_OK))
            ):
                raise ValueError("Original root data-path rule rejected")
        return p
    except ValueError:
        target, _ = exception_chain(p, role)
        return target


def clean_environment():
    if any(
        os.environ.get(k) for k in ("SLURM_CONF_SERVER", "SLURM_CONFIG", "LD_PRELOAD", "PYTHONHOME")
    ):
        raise ValueError("Unreviewed scheduler/loader override")
    env = {
        k: v
        for k, v in os.environ.items()
        if k in ("PATH", "LANG", "LC_ALL", "TZ", "HOME", "USER", "LOGNAME")
    }
    env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    if os.environ.get("SLURM_CONF"):
        env["SLURM_CONF"] = str(trusted_data(os.environ["SLURM_CONF"], "configuration"))
    libraries = os.environ.get("LD_LIBRARY_PATH", "")
    if libraries:
        for value in libraries.split(":"):
            p = Path(value)
            if not p.is_absolute() or not p.is_dir():
                raise ValueError("Unsafe library search")
            trusted_data(p, "library")
        env["LD_LIBRARY_PATH"] = libraries
    return env


def install():
    import ni_control
    import ni_native

    ni_site.trusted_binary = trusted_binary
    ni_site.clean_environment = clean_environment
    ni_control.trusted_binary = trusted_binary
    ni_native.trusted_binary = trusted_binary
