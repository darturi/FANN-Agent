"""Conservative quota/footprint preflight; no SQL or new index construction."""

import os
import shutil
import subprocess
from pathlib import Path

from pc_restore import inventory, verify_graphs
from quota_base import quota_report


def demands(b0, b1, f0, f1):
    return dict(
        scratch_bytes=(12 * (b0 + b1 + 2 * 1024**3) + 9) // 10,
        scratch_inodes=f0 + f1 + 10000,
        home_bytes=3 * 1024**3,
        home_inodes=10000,
    )


def preflight(source, scratch, results):
    source, scratch, results = map(Path, (source, scratch, results))
    footprints = [inventory(source / c, hash_content=False) for c in ("native640", "partial640")]
    verify_graphs(source)
    need = demands(
        footprints[0]["bytes"],
        footprints[1]["bytes"],
        footprints[0]["file_count"],
        footprints[1]["file_count"],
    )
    binary = shutil.which("myquota")
    if binary is None:
        raise RuntimeError("myquota unavailable")
    result = subprocess.run([binary], capture_output=True, text=True, check=True, timeout=30)
    quota = quota_report(result.stdout)
    for fs, path, bs, fs_count in [
        ("/home", results, need["home_bytes"], need["home_inodes"]),
        ("/scratch", scratch, need["scratch_bytes"], need["scratch_inodes"]),
    ]:
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        quota[fs].update(
            filesystem_free_bytes=free,
            filesystem_free_inodes=st.f_favail,
            required_bytes=bs,
            required_inodes=fs_count,
        )
        if (
            min(free, quota[fs]["space_available_lower"]) < bs
            or min(st.f_favail, quota[fs]["inodes_available_lower"]) < fs_count
        ):
            raise RuntimeError("Insufficient conservative quota/free space/inodes: " + fs)
    return dict(
        memory_gib=32,
        quota=quota,
        source_footprints=footprints,
        myquota_stdout=result.stdout,
        myquota_stderr=result.stderr,
        source=str(source),
        graph_hashes_match=True,
    )
