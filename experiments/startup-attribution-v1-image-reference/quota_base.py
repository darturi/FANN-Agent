"""Read-only Torch quota/free-space preflight; conservative display-rounding bounds."""

import decimal
import re


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
    # Torch emits e.g. 30k for home and 5.00M for scratch file limits.
    files = {"": 1, "k": 1000, "K": 1000, "m": 1000**2, "M": 1000**2, "g": 1000**3, "G": 1000**3}
    pattern = (
        r"^(/home|/scratch)\s+\S+\s+\S+\s+([0-9.]+[A-Za-z]+)/([0-9.]+[A-Za-z]*)\s+"
        r"([0-9.]+[A-Za-z]+)\(([0-9.]+)%\)/([0-9.]+[A-Za-z]*)\(([0-9.]+)%\)\s*$"
    )
    for line in text.splitlines():
        # Remove terminal colour only; unknown control sequences still fail closed.
        line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        m = re.fullmatch(pattern, line)
        if not m:
            if "/home" in line or "/scratch" in line:
                raise ValueError("Malformed home/scratch quota row")
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
