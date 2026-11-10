"""Stdlib-only package verification before importing staged research code."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tarfile
from pathlib import Path, PurePosixPath

PACKAGE_NAME = "reviews-persistent-batch-native-v1"
SCHEMA = "reviews-persistent-batch.native-held.v1"
MANIFEST = "manifest.json"
MAX_FILES = 10_000
MAX_FILE = 256 * 1024**2
MAX_TOTAL = 2 * 1024**3


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("ascii")


def write_once(path, data):
    with Path(path).open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def safe_name(name):
    need(
        type(name) is str and re.fullmatch(r"[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*", name),
        "Invalid package path",
    )
    path = PurePosixPath(name)
    need(str(path) == name and not {".", ".."}.intersection(name.split("/")), "Unsafe path")
    return name


def inventory(folder):
    folder = Path(folder)
    need(folder.is_dir() and not folder.is_symlink(), "Package must be a real directory")
    result = {}
    total = 0
    for path in sorted(folder.rglob("*")):
        mode = path.lstat().st_mode
        need(not stat.S_ISLNK(mode), "Package contains a symbolic link")
        if stat.S_ISDIR(mode):
            continue
        name = safe_name(path.relative_to(folder).as_posix())
        need(stat.S_ISREG(mode), f"Unexpected package file type: {name}")
        size = path.stat().st_size
        total += size
        need(
            size <= MAX_FILE and total <= MAX_TOTAL and len(result) < MAX_FILES,
            "Package exceeds its file or byte ceiling",
        )
        result[name] = {"bytes": size, "sha256": sha_file(path)}
    return result


def parse_manifest(raw, expected_sha):
    need(
        type(expected_sha) is str
        and re.fullmatch(r"[0-9a-f]{64}", expected_sha)
        and sha_bytes(raw) == expected_sha,
        "Package manifest pin differs",
    )
    value = json.loads(raw)
    need(
        set(value) == {"schema", "name", "dispatch_released", "files"}
        and value["schema"] == SCHEMA
        and value["name"] == PACKAGE_NAME
        and value["dispatch_released"] is False,
        "Unexpected package scope",
    )
    files = value["files"]
    need(
        type(files) is dict and 0 < len(files) < MAX_FILES and MANIFEST not in files,
        "Invalid sealed inventory",
    )
    total = 0
    for name, record in files.items():
        safe_name(name)
        need(
            set(record) == {"bytes", "sha256"}
            and type(record["bytes"]) is int
            and 0 <= record["bytes"] <= MAX_FILE
            and re.fullmatch(r"[0-9a-f]{64}", record["sha256"]),
            "Invalid file pin",
        )
        total += record["bytes"]
    need(total + len(raw) <= MAX_TOTAL, "Sealed byte ceiling exceeded")
    return files


def verify_directory(folder, expected_sha):
    folder = Path(folder)
    actual = inventory(folder)
    need(
        MANIFEST in actual and actual[MANIFEST]["sha256"] == expected_sha,
        "Missing or changed package manifest",
    )
    del actual[MANIFEST]
    expected = parse_manifest((folder / MANIFEST).read_bytes(), expected_sha)
    need(actual == expected, "Package files differ from their sealed inventory")
    return expected


def seal_directory(folder):
    folder = Path(folder)
    files = inventory(folder)
    need(MANIFEST not in files, "Package is already sealed")
    raw = json_bytes(
        {"schema": SCHEMA, "name": PACKAGE_NAME, "dispatch_released": False, "files": files}
    )
    write_once(folder / MANIFEST, raw)
    expected_sha = sha_bytes(raw)
    verify_directory(folder, expected_sha)
    return expected_sha


def verify_archive(archive, expected_sha):
    actual = {}
    raw_manifest = None
    total = 0
    prefix = PACKAGE_NAME + "/"
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            need(
                member.isfile() and member.name.startswith(prefix) and not member.issparse(),
                "Unexpected archive member",
            )
            name = safe_name(member.name.removeprefix(prefix))
            total += member.size
            need(
                name not in actual
                and 0 <= member.size <= MAX_FILE
                and total <= MAX_TOTAL
                and len(actual) < MAX_FILES,
                "Archive file count, duplicate, or size violation",
            )
            with tar.extractfile(member) as handle:
                if name == MANIFEST:
                    need(member.size <= 4 * 1024**2, "Oversized archive manifest")
                    raw_manifest = handle.read()
                    checksum = sha_bytes(raw_manifest)
                else:
                    checksum = hashlib.file_digest(handle, "sha256").hexdigest()
            actual[name] = {"bytes": member.size, "sha256": checksum}
    need(raw_manifest is not None, "Archive has no manifest")
    del actual[MANIFEST]
    need(actual == parse_manifest(raw_manifest, expected_sha), "Archive payload differs")
    return actual


def make_archive(folder, archive, expected_sha):
    files = verify_directory(folder, expected_sha)
    with tarfile.open(archive, "x:gz") as tar:
        for name in sorted({*files, MANIFEST}):
            tar.add(Path(folder) / name, arcname=f"{PACKAGE_NAME}/{name}", recursive=False)
    verify_archive(archive, expected_sha)
    checksum = sha_file(archive)
    write_once(str(archive) + ".sha256", f"{checksum}  {Path(archive).name}\n".encode("ascii"))
    return checksum
