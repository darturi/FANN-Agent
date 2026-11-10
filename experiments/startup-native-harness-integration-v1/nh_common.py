"""Pinned integration inputs, strict files and a permanently closed native boundary."""

import hashlib
import json
import math
import os
import stat
import time
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
OUT = ROOT / "trials/torch-reviews-startup-native-harness-integration-v1"
INNER = (
    ROOT
    / "trials/torch-reviews-startup-adaptive-x86-qualification-v1/torch-startup-adaptive-x86-qualification-v1"
)
MAIN = "agent/experiments/startup-attribution-v1-image-reference"
A3 = "agent/experiments/startup-exact-vector-startup-integration-v1"
NATIVE_RELEASE = False
PHASES = {
    "preflight": 30,
    "main_source": 420,
    "candidate_build": 90,
    "main_sealed": 420,
    "a3_source": 600,
    "a3_sealed": 600,
    "cpu": 180,
    "guest_cleanup": 600,
}


def read(p):
    return json.loads(Path(p).read_text())


def encoded(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":")).encode()


def digest(v):
    return hashlib.sha256(encoded(v)).hexdigest()


def check_time(deadline, clock=time.monotonic):
    if type(deadline) not in (float, int) or not math.isfinite(deadline) or clock() >= deadline:
        raise TimeoutError("Integration deadline exhausted")


def identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def sha(p, deadline=None, clock=time.monotonic):
    fd = os.open(Path(p), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Regular file required")
        h = hashlib.sha256()
        while True:
            if deadline is not None:
                check_time(deadline, clock)
            b = os.read(fd, 1024**2)
            if not b:
                break
            h.update(b)
        if identity(before) != identity(os.fstat(fd)):
            raise RuntimeError("File changed while hashing")
        return h.hexdigest()
    finally:
        os.close(fd)


def save(p, v):
    with Path(p).open("x") as f:
        json.dump(v, f, sort_keys=True, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def relative(name):
    p = PurePosixPath(name)
    if (
        not isinstance(name, str)
        or not p.parts
        or p.is_absolute()
        or ".." in p.parts
        or str(p) != name
        or any(x in name for x in ("\\", "\n", "\r", "\0"))
    ):
        raise ValueError("Unsafe relative name")
    return p


def private(path):
    p = Path(path)
    if not p.is_absolute() or p.resolve() != p or p.is_symlink():
        raise ValueError("Canonical owned path required")
    s = p.stat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) != 0o700:
        raise ValueError("Private0700 owned directory required")
    return p


def executable_identity(path):
    p = Path(path)
    if not p.is_absolute() or not os.access(p, os.X_OK):
        raise ValueError("Absolute selected executable required")
    before = p.lstat()
    resolved = p.resolve(strict=True)
    value = {
        "path": str(p),
        "resolved": str(resolved),
        "sha256": sha(resolved),
        "alias_inode": before.st_ino,
        "alias_mtime_ns": before.st_mtime_ns,
        "alias_mode": before.st_mode,
        "alias_target": os.readlink(p) if p.is_symlink() else None,
    }
    venv = p.parent.parent / "pyvenv.cfg"
    value["venv_config_sha256"] = sha(venv) if venv.exists() else None
    if p.resolve(strict=True) != resolved or identity(before) != identity(p.lstat()):
        raise RuntimeError("Interpreter alias changed during verification")
    return value


def inventory(root):
    root = Path(root)
    result = {}
    for p in root.rglob("*"):
        if p.is_symlink():
            raise ValueError("Input symlink prohibited")
        if p.is_file():
            result[str(p.relative_to(root))] = sha(p)
    return result


def closed_native(*args, **kwargs):
    raise RuntimeError(
        "Native dispatch closed; every prior allowance is spent; no grant in this integration"
    )


def offline():
    if os.environ.get("SLURM_JOB_ID") or os.environ.get("SLURM_ARRAY_JOB_ID"):
        closed_native()


def config():
    c = read(HERE / "DESIGN-FREEZE.json")
    if (
        c["native_release"] is not False
        or c["phase_seconds"] != PHASES
        or any(type(v) is not int for v in c["phase_seconds"].values())
    ):
        raise ValueError("Frozen integration scope changed")
    for key, value in {
        "allocations": 1,
        "physical_cpus": 4,
        "memory_gib": 32,
        "wall_seconds": 3600,
        "host_pre_seconds": 240,
        "guest_seconds": 3000,
        "host_post_seconds": 240,
        "outer_margin_seconds": 120,
        "guest_cleanup_seconds": 600,
        "raw_bytes": 33554432,
        "home_free_files": 1000,
        "home_return_required_bytes": 134217728,
        "scratch_free_files": 30000,
        "scratch_required_bytes": 8589934592,
    }.items():
        if type(c["limits"][key]) is not int or c["limits"][key] != value:
            raise ValueError("Original limit changed")
    return c


def compat():
    import sys

    sys.path.insert(0, str(HERE / "compat"))
    c = config()
    for name, source in [
        ("policy.py", "startup-adaptive-budget-storage-v1"),
        ("staging.py", "startup-adaptive-budget-storage-v1"),
        ("lifetime.py", "startup-adaptive-budget-storage-v1"),
        ("fast_paths.py", "startup-adaptive-fixture-cost-v1"),
    ]:
        if (
            sha(HERE / "compat" / name)
            != c["inputs_sha256"]["agent/experiments/" + source + "/" + name]
        ):
            raise ValueError("Pinned original compatibility helper changed")


def core(inner):
    import importlib
    import sys

    inner = Path(inner).resolve()
    c = config()
    for p in inner.glob("*.py"):
        name = "agent/experiments/startup-adaptive-x86-qualification-v1/" + p.name
        if sha(p) != c["inputs_sha256"].get(name):
            raise ValueError("Original qualification helper differs")
    sys.path.insert(0, str(inner))
    module = importlib.import_module("common")
    if Path(module.__file__).resolve() != inner / "common.py":
        raise RuntimeError("Wrong original core origin")
    module.verify(inner)
    return module


if __name__ == "__main__":
    closed_native()
