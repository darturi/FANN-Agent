"""Strict offline archive materialization; no native execution or cleanup."""

import hashlib
import json
import os
import re
import stat
import tarfile
from pathlib import Path, PurePosixPath

from policy import FREE_BYTES, FREE_INODES


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            value.update(block)
    return value.hexdigest()


def verify_tree(root, manifest_sha):
    root = Path(root)
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("Staged/source symlink prohibited")
    if sha(root / "manifest.json") != manifest_sha:
        raise ValueError("Exact manifest identity required")
    files = json.loads((root / "manifest.json").read_text())["files"]
    for name, digest in files.items():
        rel = PurePosixPath(name)
        if (
            rel.is_absolute()
            or ".." in rel.parts
            or name != rel.as_posix()
            or "\\" in name
            or not re.fullmatch("[0-9a-f]{64}", digest)
        ):
            raise ValueError("Unsafe manifest path/hash")
    expected = {**files, "manifest.json": manifest_sha}
    actual = {str(p.relative_to(root)): sha(p) for p in root.rglob("*") if p.is_file()}
    if expected != actual:
        raise ValueError("Complete original file inventory/hash differs")
    return expected


def binding_layout(package, original_root):
    """Reviewable data only; never invokes a mount or container command."""
    package, original_root = Path(package), Path(original_root)
    workspace = package / "workspace"
    payload = (
        workspace
        / "trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1/frozen"
    )
    aliases = json.loads((package / "ASSET-PLAN.json").read_text())["frozen_aliases"]
    result = [
        {"source": str(package), "destination": "/qual", "mode": "ro"},
        {"source": str(workspace), "destination": str(original_root), "mode": "ro"},
    ]
    for name in aliases:
        rel = PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts or name != rel.as_posix():
            raise ValueError("Unsafe frozen alias")
        result.append(
            {
                "source": str(payload),
                "destination": str(original_root / name / "frozen"),
                "mode": "ro",
            }
        )
    return {"bindings": result, "executed": False, "native_release": False}


def stage_exact(archive, source, destination, archive_sha, manifest_sha, semantic_verifier=None):
    if os.environ.get("SLURM_JOB_ID") or os.environ.get("SLURM_ARRAY_JOB_ID"):
        raise RuntimeError("Offline prototype only; all native allowances closed")
    archive, source, destination = map(Path, (archive, source, destination))
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise FileExistsError("Preserve existing or unsafe stage destination")
    for parent in destination.parents:
        if parent.is_symlink():
            raise ValueError("Stage ancestor symlink prohibited")
    parent = destination.parent
    if parent.stat().st_uid != os.getuid() or parent.stat().st_mode & 0o022:
        raise ValueError("Owned non-writable parent required")
    if destination.resolve().is_relative_to(source.resolve()):
        raise ValueError("Stage must be separate from original")
    fs = os.statvfs(parent)
    if fs.f_bavail * fs.f_frsize < FREE_BYTES or fs.f_favail < FREE_INODES:
        raise ValueError("Insufficient local prototype headroom")
    expected = verify_tree(source, manifest_sha)
    if semantic_verifier:
        semantic_verifier(source)
    if sha(archive) != archive_sha:
        raise ValueError("Exact archive identity required")
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        if (
            len(members) != len(expected)
            or len(members) > 1602
            or sum(m.size for m in members) > 1024**3
        ):
            raise ValueError("Complete bounded member inventory required")
        seen = set()
        for member in members:
            rel = PurePosixPath(member.name)
            if (
                not member.isfile()
                or rel.is_absolute()
                or ".." in rel.parts
                or member.name != rel.as_posix()
                or "\\" in member.name
                or len(rel.parts) < 2
                or rel.parts[0] != source.name
                or member.mode & 0o7000
            ):
                raise ValueError("Unsafe/nonregular archive member")
            name = str(rel.relative_to(source.name))
            if (
                name not in expected
                or name in seen
                or member.size != (source / name).stat().st_size
            ):
                raise ValueError("Archive member inventory/size differs")
            seen.add(name)
        if seen != set(expected):
            raise ValueError("Missing archive member")
        destination.mkdir(mode=0o700)
    local_archive = destination / archive.name
    with archive.open("rb") as src, local_archive.open("xb") as dst:
        for block in iter(lambda: src.read(1024**2), b""):
            dst.write(block)
    if sha(local_archive) != archive_sha:
        raise ValueError("Local archive copy differs; partial output preserved")
    package = destination / source.name
    with tarfile.open(local_archive, "r:gz") as handle:
        for member in members:
            name = str(PurePosixPath(member.name).relative_to(source.name))
            target = package / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            value = hashlib.sha256()
            with handle.extractfile(member) as src, target.open("xb") as dst:
                for block in iter(lambda: src.read(1024**2), b""):
                    value.update(block)
                    dst.write(block)
            if value.hexdigest() != expected[name]:
                raise ValueError("Staged member bytes differ; partial output preserved")
            target.chmod(stat.S_IMODE(member.mode))
    verify_tree(package, manifest_sha)
    verify_tree(source, manifest_sha)
    if semantic_verifier:
        semantic_verifier(package)
        semantic_verifier(source)
    if sha(archive) != archive_sha:
        raise ValueError("Archive changed during staging")
    receipt = {
        "status": "complete_offline_stage",
        "package": str(package),
        "archive_sha256": archive_sha,
        "manifest_sha256": manifest_sha,
        "files": len(expected),
        "content_bytes": sum((package / n).stat().st_size for n in expected),
        "full_original_and_staged_verification": True,
        "semantic_verifier_calls": 3 if semantic_verifier else 0,
        "required_native_bind_mode": "read-only",
        "capacity_scope": "local statvfs only; no native mount/quota proof",
        "native_storage_qualified": False,
        "native_release": False,
        "spent_allowances_reusable": False,
        "Torch_jobs": 0,
        "ANN_searches": 0,
        "exact_searches": 0,
    }
    with (destination / "stage-receipt.json").open("x") as out:
        json.dump(receipt, out, indent=2, sort_keys=True)
        out.write("\n")
    return package
