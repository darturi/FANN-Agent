"""Read-only stopped-cluster inventories and independent working copies."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

from pc_common import CELLS, CONTRACT, digest, sha
from pc_trace import category


def inventory(root, hash_content=True):
    root = Path(root)
    if not root.is_absolute() or root.resolve() != root or root.is_symlink():
        raise ValueError("Source root must be an absolute, real directory")
    if not root.is_dir() or root.stat().st_uid != os.getuid():
        raise ValueError("Source directory absent/not owned")
    files, seen = {}, set()
    for p in sorted(root.rglob("*")):
        st = p.lstat()
        if stat.S_ISLNK(st.st_mode) or not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)):
            raise ValueError("Symlink/special file in stopped source: " + str(p))
        if st.st_uid != os.getuid():
            raise ValueError("Foreign-owned source entry")
        if p.is_file():
            key = (st.st_dev, st.st_ino)
            if st.st_nlink != 1 or key in seen:
                raise ValueError("Hard-linked/aliased source file")
            seen.add(key)
            files[str(p.relative_to(root))] = dict(
                bytes=st.st_size,
                mode=stat.S_IMODE(st.st_mode),
                uid=st.st_uid,
                sha256=sha(p) if hash_content else None,
            )
    if not files:
        raise ValueError("Empty source inventory")
    return dict(files=files, bytes=sum(v["bytes"] for v in files.values()), file_count=len(files))


def graph_files(work, filepath):
    import re

    if not re.fullmatch(r"base/[0-9]+/[0-9]+", filepath):
        raise ValueError("Unsafe relation path")
    base = Path(work) / "pgdata" / filepath
    out = {}
    for p in sorted(base.parent.glob(base.name + "*")):
        if p.is_symlink() or not p.is_file() or p.stat().st_nlink != 1:
            raise ValueError("Unexpected graph relation-family entry")
        out[p.name] = sha(p)
    return out


def verify_graphs(root):
    root = Path(root)
    for cell in CELLS:
        d = root / cell
        if (d / "pgdata/postmaster.pid").exists():
            raise ValueError("Source/clean working cluster has postmaster.pid")
        if (d / "pgdata/PG_VERSION").read_text().strip() != "17":
            raise ValueError("PostgreSQL major version differs")
        if any((d / "pgdata/pg_tblspc").iterdir()):
            raise ValueError("External tablespaces are not allowed")
        expected = CONTRACT["graphs"]["native640"]
        if graph_files(d, "base/16384/264013") != expected:
            raise ValueError("Original full graph differs")
        partial = graph_files(d, "base/16384/270339")
        if partial != (CONTRACT["graphs"]["partial640"]["partial"] if cell == "partial640" else {}):
            raise ValueError("Partial graph differs or unexpectedly present")


def control_state(pgdata, run=subprocess.run):
    result = run(
        ["pg_controldata", "-D", str(pgdata)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        env={**os.environ, "LC_ALL": "C"},
    )
    fields = {}
    for line in result.stdout.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    if fields.get("Database cluster state") != "shut down":
        raise ValueError("Source cluster was not cleanly shut down")
    if not fields.get("Database system identifier"):
        raise ValueError("Control data system identity missing")
    return dict(stdout=result.stdout, fields=fields)


IDENTITY_SHA = "28a053d17b4b92336923319772baa88c58391450829ff833bed118a124ef5ffe"


def checked_identity(source):
    path = Path(source) / "database-identity.json"
    st = path.lstat()
    if (
        not stat.S_ISREG(st.st_mode)
        or st.st_uid != os.getuid()
        or st.st_nlink != 1
        or st.st_mode & 0o077
        or sha(path) != IDENTITY_SHA
    ):
        raise ValueError("Retained backend identity metadata is not the pinned private file")
    return path


def clone(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise ValueError("Working copy already exists")
    identity = checked_identity(source)
    source_pg = source / "pgdata"
    before = inventory(source_pg)
    destination.mkdir(mode=0o700)
    shutil.copytree(source_pg, destination / "pgdata", copy_function=shutil.copy2)
    if inventory(destination / "pgdata") != before:
        raise ValueError("Whole-cluster copy bytes/layout differ")
    for name in before["files"]:
        a, b = (source_pg / name).stat(), (destination / "pgdata" / name).stat()
        if (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino):
            raise ValueError("Working copy aliases protected source")
    for name in ("admin.pgpass", "reader.pgpass", "pg_hba.conf"):
        p = source / name
        if p.is_symlink() or p.stat().st_mode & 0o077:
            raise ValueError("Private authentication file unsafe")
        shutil.copyfile(p, destination / name)
        (destination / name).chmod(0o600)
    shutil.copyfile(identity, destination / "database-identity.json")
    (destination / "database-identity.json").chmod(0o600)
    if sha(destination / "database-identity.json") != IDENTITY_SHA:
        raise ValueError("Copied backend identity metadata changed")
    for name in ("socket", "tmp"):
        (destination / name).mkdir(mode=0o700)
    (destination / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")
    return dict(
        pgdata_inventory_sha256=digest(before),
        files=before["file_count"],
        bytes=before["bytes"],
        independent_inodes=True,
        database_identity_sha256=IDENTITY_SHA,
    )


def verify_data(conn, bundle):
    """Same complete ID/metadata/float32-bit comparison, existing admin connection."""
    import json

    import numpy as np
    import pyarrow.parquet as pq

    def source_rows():
        for batch in pq.ParquetFile(Path(bundle) / "inputs/reviews.parquet").iter_batches(
            batch_size=512, use_threads=False
        ):
            yield from batch.to_pylist()

    expected, count = source_rows(), 0
    with category("observer"):
        with conn.transaction():
            with conn.cursor(name="b2f_verify_bits") as cursor:
                cursor.execute(
                    "SELECT id,embedding::text,total_votes FROM public.reviews ORDER BY id"
                )
                for identifier, text, votes in cursor:
                    row = next(expected, None)
                    if (
                        row is None
                        or identifier != row["source_id"]
                        or votes != row["metadata"]["total_votes"]
                    ):
                        raise RuntimeError("ID/metadata differs from frozen input")
                    if not np.array_equal(
                        np.asarray(json.loads(text), dtype=np.float32).view(np.uint32),
                        np.asarray(row["vector"], dtype=np.float32).view(np.uint32),
                    ):
                        raise RuntimeError("Vector bits differ from frozen input")
                    count += 1
    if next(expected, None) is not None or count != 247286:
        raise RuntimeError("Full data coverage differs")
    return dict(rows=count, data_bits_verified=True)
