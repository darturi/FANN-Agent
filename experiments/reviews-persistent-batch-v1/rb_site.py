"""Read-only Torch quota/free-space preflight; conservative display-rounding bounds."""

import datetime
import decimal
import hashlib
import json
import os
import platform
import pwd
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


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


ACCOUNT_FIELDS = (
    "JobIDRaw,JobName,User,Account,Partition,State,ExitCode,DerivedExitCode,"
    "AllocCPUS,NNodes,ReqMem,ElapsedRaw,TimelimitRaw,Restarts"
)
USER = "dar579"
ACCOUNT = "torch_pr_288_courant"
PARTITION = "cs"
BUNDLE = Path("/home/dar579/torch-reviews-first")
RESULTS = Path("/home/dar579/torch-reviews-results")
SCRATCH = Path("/scratch/dar579/torch-reviews")
PREPARED = SCRATCH / "torch-reviews-size-sweep.ihFoep/prepared/size-247286"
IMAGE = BUNDLE / "images/runtime.sif"
APPTAINER = Path("/share/apps/apptainer/bin/apptainer")
COMPUTE_TOOL_PATHS = {"scontrol": Path("/opt/slurm/bin/scontrol"), "apptainer": APPTAINER}
MYQUOTA = Path("/share/apps/local/bin/myquota")
BASE_SHA = "5538cb6a4bd03da6a00fae4913fdfe9237b481f902bcd15d98666f2e99af070a"
INDEX_SHA = "28a053d17b4b92336923319772baa88c58391450829ff833bed118a124ef5ffe"
PREPARED_INDEX_SHA = "596775da3b83301364993d99f6d0a4924958ed34ca07d0c1e16ebb720fa7119a"
IMAGE_SHA = "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a"
GRAPH = "90f4a709ab3ee7ce40fe7630009b29d5646f6e1e80ceab8c2246cb970d803484"
ENV = {"PATH": "/opt/slurm/bin:/usr/local/bin:/usr/bin:/bin", "HOME": "/home/dar579", "LC_ALL": "C"}
QUOTA_ENV = {
    "USER": USER,
    "LOGNAME": USER,
    **ENV,
    "PATH": "/share/apps/local/bin:/usr/lpp/mmfs/bin:/usr/local/sbin:/usr/sbin:" + ENV["PATH"],
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha_file(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes())


def now():
    return datetime.datetime.now(datetime.UTC)


def command(argv, timeout=30, *, env=ENV):
    proc = subprocess.run(
        list(map(str, argv)), check=True, text=True, capture_output=True, timeout=timeout, env=env
    )
    need(len(proc.stdout) < 1024**2, "Site response exceeds review ceiling")
    return proc.stdout.strip()


def fields(text, names):
    out = {}
    for name in names:
        matches = re.findall(r"(?:^|\s)" + re.escape(name) + r"=(\S+)", text)
        need(len(matches) == 1, f"Missing or ambiguous Slurm field {name}")
        out[name] = matches[0]
    return out


def binary(path):
    p = Path(path).resolve(strict=True)
    st = p.stat()
    need(
        p.is_file() and st.st_uid == 0 and not st.st_mode & 0o022 and os.access(p, os.X_OK),
        f"Expected a site-owned executable: {p}",
    )
    return {"path": str(p), "sha256": sha_file(p)}


def compute_tool_path(name, record):
    path = Path(record["path"])
    prefix = COMPUTE_TOOL_PATHS[name].parent.parent
    approved_location = path.is_relative_to(prefix) or (
        name == "scontrol" and path == Path("/usr/bin/scontrol")
    )
    need(
        set(record) == {"path", "sha256"}
        and re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
        and approved_location
        and ".." not in path.parts
        and path.name == name,
        f"Unexpected compute installation for {name}",
    )
    return path


def compute_tool(name):
    """Use the installed site tool and fingerprint it on the allocated host."""
    installed = COMPUTE_TOOL_PATHS[name]
    observed = binary(installed)
    path = compute_tool_path(name, observed)
    for component in (path, *path.parents, *installed.parents):
        info = component.stat()
        need(
            info.st_uid != os.getuid()
            and not info.st_mode & stat.S_IWOTH
            and not os.access(component, os.W_OK),
            f"Writable compute tool path: {component}",
        )
    return observed


def retained_inputs():
    manifest = BUNDLE / "manifest.json"
    need(sha_file(manifest) == BASE_SHA, "Retained bundle manifest differs")
    expected = read_json(manifest)["files"]
    names = (
        "images/runtime.sif",
        "inputs/reviews.parquet",
        "inputs/local-identity.json",
        "experiment.json",
    )
    observed = {name: sha_file(BUNDLE / name) for name in names}
    need(
        observed == {name: expected[name] for name in names}
        and observed["images/runtime.sif"] == IMAGE_SHA,
        "Retained bundle input differs",
    )
    ready = PREPARED / "READY.json"
    index = PREPARED / "database-identity.json"
    ready_data = read_json(ready)
    index_sha = sha_file(index)
    need(
        ready_data["architecture"] == "x86_64"
        and ready_data["image_sha256"] == IMAGE_SHA
        and ready_data["index_identity"] == GRAPH
        and index_sha in {INDEX_SHA, PREPARED_INDEX_SHA},
        f"Prepared database identity differs (identity file SHA-256 {index_sha})",
    )
    need(os.access(PREPARED / "admin.pgpass", os.R_OK), "Prepared database passfile is unreadable")
    return {
        "base_manifest_sha256": BASE_SHA,
        "bundle_files": observed,
        "prepared_ready_sha256": sha_file(ready),
        "prepared_index_sha256": index_sha,
        "backup_manifest_sha256": sha_file(PREPARED / "base/backup_manifest"),
    }


def duration_seconds(value):
    days, sep, clock = value.partition("-")
    if not sep:
        days, clock = "0", days
    parts = clock.split(":")
    need(
        len(parts) in (2, 3) and days.isdecimal() and all(p.isdecimal() for p in parts),
        "Unexpected Slurm duration",
    )
    if len(parts) == 2:
        parts.insert(0, "0")
    hours, minutes, seconds = map(int, parts)
    return int(days) * 86400 + hours * 3600 + minutes * 60 + seconds


def association_tools():
    tools = {}
    for name in ("scontrol", "sacctmgr", "sacct", "sbatch", "srun"):
        path = shutil.which(name, path=ENV["PATH"])
        need(path is not None, f"Site tool unavailable on system PATH: {name}")
        tools[name] = binary(path)
    need(sys.version_info[:2] == (3, 12), "Use Torch's /usr/bin/python3.12")
    tools["python"] = binary("/usr/bin/python3.12")
    need(str(Path(sys.executable).resolve()) == tools["python"]["path"], "Python launcher differs")
    tools["myquota"] = binary(MYQUOTA)
    tools["apptainer"] = binary(APPTAINER)
    return tools


def site_check():
    host = platform.node().split(".")[0]
    need(
        platform.system() == "Linux"
        and platform.machine() == "x86_64"
        and re.fullmatch(r"torch-login(?:-[a-z0-9-]+)?", host)
        and pwd.getpwuid(os.getuid()).pw_name == USER
        and not os.environ.get("SLURM_JOB_ID"),
        "Use the named user's x86-64 Torch login, outside a job",
    )
    tools = association_tools()
    config = command([tools["scontrol"]["path"], "--local", "show", "config"])
    cfg = {}
    for line in config.splitlines():
        name, sep, value = line.partition("=")
        if sep and name.strip() in {
            "ClusterName",
            "TaskPlugin",
            "SelectType",
            "SelectTypeParameters",
        }:
            cfg[name.strip()] = value.strip()
    need(
        cfg.get("ClusterName") == "torch"
        and "task/cgroup" in cfg.get("TaskPlugin", "").split(",")
        and "task/affinity" in cfg.get("TaskPlugin", "").split(","),
        "Torch task affinity/cgroup configuration needs review",
    )
    partition = command(
        [tools["scontrol"]["path"], "--local", "--oneliner", "show", "partition", PARTITION]
    )
    part = fields(
        partition, ("PartitionName", "State", "MaxTime", "AllowAccounts", "MaxMemPerNode")
    )
    need(
        part["PartitionName"] == PARTITION
        and part["State"] == "UP"
        and (part["MaxTime"] == "UNLIMITED" or duration_seconds(part["MaxTime"]) >= 7200)
        and (part["AllowAccounts"] == "ALL" or ACCOUNT in part["AllowAccounts"].split(","))
        and not re.search(r"(?:^|\s)DenyAccounts=", partition)
        and part["MaxMemPerNode"] == "UNLIMITED",
        "Partition does not permit the study request",
    )
    rows = command(
        [
            tools["sacctmgr"]["path"],
            "-nP",
            "show",
            "assoc",
            "where",
            f"cluster={cfg['ClusterName']}",
            f"user={USER}",
            f"account={ACCOUNT}",
            "format=Cluster,Account,User,Partition",
        ]
    )
    need(
        any(
            row in (f"torch|{ACCOUNT}|{USER}|", f"torch|{ACCOUNT}|{USER}|{PARTITION}")
            for row in rows.splitlines()
        ),
        "No matching Torch project association",
    )
    accounting = command([tools["sacct"]["path"], "--helpformat"]).split()
    need(
        set(ACCOUNT_FIELDS.split(",")) <= set(accounting), "Scheduler accounting fields unavailable"
    )
    storage = quota_report(command([tools["myquota"]["path"]], env=QUOTA_ENV))
    for fs, path, min_bytes, min_files in (
        ("/home", RESULTS, 128 * 1024**2, 1000),
        ("/scratch", SCRATCH, 8 * 1024**3, 30000),
    ):
        stats = os.statvfs(path)
        need(
            os.access(path, os.W_OK | os.X_OK)
            and min(stats.f_bavail * stats.f_frsize, storage[fs]["space_available_lower"])
            >= min_bytes
            and min(stats.f_favail, storage[fs]["inodes_available_lower"]) >= min_files,
            f"Insufficient verified quota, filesystem space, or access on {fs}",
        )
    return {
        "schema": "reviews-persistent-batch.torch-site.v1",
        "checked_utc": now().isoformat(),
        "host": host,
        "uid": os.getuid(),
        "cluster": cfg,
        "partition": part,
        "account": ACCOUNT,
        "tools": tools,
        "quota": storage,
        "inputs": retained_inputs(),
        "allocations": 0,
        "searches": 0,
    }


if __name__ == "__main__":
    print(json.dumps(site_check(), sort_keys=True, indent=2))
