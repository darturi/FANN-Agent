"""Read-only Torch quota/free-space preflight; conservative display-rounding bounds."""

import decimal
import os
import re
import shutil
import subprocess
from pathlib import Path

from pa_common import INDEX_BYTES


def bounds(text, units):
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([A-Za-z]*)", text)
    if not m or m[2] not in units:
        raise ValueError("Unrecognized quota unit: " + text)
    n = decimal.Decimal(m[1])
    scale = units[m[2]]
    step = decimal.Decimal(10) ** (-len(m[1].split(".")[1]) if "." in m[1] else 0)
    # Whole integer file counts are exact; displayed storage/abbreviations rounded.
    margin = step if m[2] else decimal.Decimal(0)
    return int(max(0, n - margin) * scale), int((n + margin) * scale)


def quota_report(text):
    result = {}
    size = {
        "B": 1,
        "KB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "TB": 1000**4,
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "TiB": 1024**4,
    }
    files = {"": 1, "K": 1000, "M": 1000**2, "G": 1000**3}
    pattern = (
        r"^(/home|/scratch)\s+\S+\s+\S+\s+([0-9.]+[A-Za-z]+)/([0-9.]+[A-Za-z]*)\s+"
        r"([0-9.]+[A-Za-z]+)\(([0-9.]+)%\)/([0-9.]+[A-Za-z]*)\(([0-9.]+)%\)\s*$"
    )
    for line in text.splitlines():
        m = re.fullmatch(pattern, line.strip())
        if not m:
            continue
        fs, limit, count, used, usedpct, usedcount, usedfilespct = m.groups()
        if fs in result:
            raise ValueError("Duplicate quota row")
        lower_limit, upperlimit = bounds(limit, size)
        _, u = bounds(used, size)
        f, _ = bounds(count, files)
        _, uf = bounds(usedcount, files)
        digits = len(usedpct.split(".")[1]) if "." in usedpct else 0
        pct_upper = decimal.Decimal(usedpct) + decimal.Decimal(10) ** (-digits)
        u = min(
            u, int((pct_upper * upperlimit / 100).to_integral_value(rounding=decimal.ROUND_CEILING))
        )
        result[fs] = dict(
            space_limit_lower=lower_limit,
            space_usage_upper=u,
            space_available_lower=max(0, lower_limit - u),
            inode_limit_lower=f,
            inode_usage_upper=uf,
            inodes_available_lower=max(0, f - uf),
        )
    if set(result) != {"/home", "/scratch"}:
        raise ValueError(
            "Cannot prove home/scratch quota from myquota; preserve output, do not submit"
        )
    return result


def footprint(prepared):
    total = count = 0
    for p in (Path(prepared) / "base").rglob("*"):
        if p.is_symlink():
            raise ValueError("Symlink in prepared backup")
        if p.is_file():
            total += p.stat().st_size
            count += 1
    if total <= 0 or count <= 0:
        raise ValueError("Prepared backup footprint missing")
    return total, count


def preflight(prepared, scratch, results):
    prepared, scratch, results = map(Path, (prepared, scratch, results))
    if not str(scratch).startswith("/scratch/") or not str(results).startswith("/home/"):
        raise ValueError("Expected scratch/home evidence roots")
    cmd = shutil.which("myquota")
    if cmd is None:
        raise RuntimeError("myquota unavailable; quota must be established before allocation")
    p = subprocess.run([cmd], capture_output=True, text=True, check=True, timeout=30)
    try:
        q = quota_report(p.stdout)
    except ValueError as e:
        raise ValueError(str(e) + "\nCaptured myquota output:\n" + p.stdout) from e
    B, F = footprint(prepared)
    required = (12 * (2 * B + INDEX_BYTES + 3 * 1024**3) + 9) // 10
    demands = {
        "/scratch": (required, 2 * F + 10000, scratch),
        "/home": (3 * 1024**3, 10000, results),
    }
    for key, (space, inodes, path) in demands.items():
        v = os.statvfs(path)
        free = v.f_bavail * v.f_frsize
        available = v.f_favail
        q[key].update(
            filesystem_free_bytes=free,
            filesystem_free_inodes=available,
            required_bytes=space,
            required_inodes=inodes,
        )
        if (
            min(free, q[key]["space_available_lower"]) < space
            or min(available, q[key]["inodes_available_lower"]) < inodes
        ):
            raise RuntimeError("Insufficient conservative disk/inode quota: " + key)
    return dict(
        prepared_bytes=B,
        prepared_files=F,
        quota=q,
        myquota_stdout=p.stdout,
        myquota_stderr=p.stderr,
        units="decimal quota display, binary GiB reserves; conservative rounding",
        memory_gib=32,
    )
