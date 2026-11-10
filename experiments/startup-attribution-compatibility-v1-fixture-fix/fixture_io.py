"""Reduce offline fixture I/O without changing production copies or source bytes."""

import contextlib
import hashlib
import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch

MUTABLE = frozenset(("manifest.json", "experiment.json", "eligibility.json", "queries.jsonl"))


def fingerprint(root):
    root = Path(root)
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("Synthetic seed symlink prohibited")
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            result[str(path.relative_to(root))] = digest.hexdigest()
    return result


@contextlib.contextmanager
def fixture_copies(module):
    """Wrap only the existing runtime fixture, including imported test aliases."""
    original_fixture = module.runtime_fixture
    original_copy = shutil.copytree
    stats = dict(clones=0, linked_files=0, mutable_copies=0, seeds_verified=0)

    def runtime_fixture(root, seed=None, fault=None):
        if seed is None:
            return original_fixture(root, seed, fault)
        seed, destination = Path(seed).resolve(), Path(root).resolve() / "package"
        config = json.loads((seed / "experiment.json").read_text())
        if config.get("synthetic_fixture") is not True:
            raise RuntimeError("Offline clone requires synthetic seed")
        before = fingerprint(seed)
        if not MUTABLE <= set(before):
            raise RuntimeError("Synthetic seed mutable inventory differs")
        used = False

        def clone(src, dst, *args, **kwargs):
            nonlocal used
            if Path(src).resolve() != seed or Path(dst).resolve() != destination:
                return original_copy(src, dst, *args, **kwargs)
            if used or args or kwargs:
                raise RuntimeError("Unexpected synthetic clone invocation")
            used = True

            def copy_file(source, target):
                source, target = Path(source), Path(target)
                if str(source.relative_to(seed)) in MUTABLE:
                    shutil.copyfile(source, target)
                    if os.path.samefile(source, target):
                        raise RuntimeError("Mutable fixture file shares seed inode")
                    stats["mutable_copies"] += 1
                else:
                    # Same temporary scratch filesystem; failure is explicit, never a fallback.
                    os.link(source, target)
                    stats["linked_files"] += 1
                return str(target)

            value = original_copy(src, dst, copy_function=copy_file)
            stats["clones"] += 1
            return value

        try:
            with patch.object(shutil, "copytree", clone):
                return original_fixture(root, seed, fault)
        finally:
            if fingerprint(seed) != before:
                raise RuntimeError("Offline fixture changed immutable seed bytes")
            stats["seeds_verified"] += 1

    module.runtime_fixture = runtime_fixture
    try:
        yield stats
    finally:
        module.runtime_fixture = original_fixture
