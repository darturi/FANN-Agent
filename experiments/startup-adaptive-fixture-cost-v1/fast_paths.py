"""Equivalent fresh POSIX path checks, scoped to the offline A3 harness."""

import hashlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path

PIN = "2e15a53db8bf89d2294907b50613c522e2c5ef7fda9ff5e1e8915b6cffa504c7"
ACTIVE = False


def make_checker(original, counters):
    def safe_file(root, name):
        counters["calls"] += 1
        if os.name != "posix":
            counters["fallbacks"] += 1
            return original(root, name)
        try:
            counters["root_resolves"] += 1
            root, relative = Path(root).resolve(), Path(name)
            if (
                relative.is_absolute()
                or not relative.parts
                or any(p in (".", "..") for p in relative.parts)
            ):
                raise ValueError("Unsafe relative path: " + str(name))
            path = root / relative
            parent = path
            while parent != root:
                counters["symlink_checks"] += 1
                if parent.is_symlink():
                    raise ValueError("Symlink in input: " + str(name))
                parent = parent.parent
            counters["path_resolves"] += 1
            resolved = path.resolve()
            # POSIX proper-descendant relation, including filesystem root.
            # Both paths have just been resolved; separators avoid sibling-prefix
            # collisions. No ancestor list, filesystem result or digest is cached.
            prefix = str(root).rstrip("/") + "/"
            if resolved == root or not str(resolved).startswith(prefix):
                raise ValueError("Path escapes root")
            return path
        except BaseException:
            counters["errors"] += 1
            raise

    return safe_file


def stats():
    return dict(
        calls=0,
        fallbacks=0,
        root_resolves=0,
        path_resolves=0,
        symlink_checks=0,
        errors=0,
        installed_aliases=0,
        new_aliases_restored=0,
        restored=False,
    )


@contextmanager
def scoped(common, workspace, source, counters):
    global ACTIVE
    if ACTIVE:
        raise RuntimeError("Nested offline path scope prohibited")
    original = common.safe_file
    origin = Path(original.__code__.co_filename).resolve()
    if (
        origin != Path(source).resolve() / "legacy_common.py"
        or hashlib.sha256(origin.read_bytes()).hexdigest() != PIN
        or original.__name__ != "safe_file"
        or original.__globals__.get("Path") is not Path
    ):
        raise RuntimeError("Pinned original path checker required")
    roots = (Path(workspace).resolve(), Path(source).resolve())

    def owned(module):
        filename = getattr(module, "__file__", None)
        return bool(filename) and any(
            Path(filename).resolve().is_relative_to(root) for root in roots
        )

    checker = make_checker(original, counters)
    tracked = []
    ACTIVE = True
    try:
        for module in list(sys.modules.values()):
            if module is not None and vars(module).get("safe_file") is original:
                if not owned(module):
                    raise RuntimeError("Path alias outside owned fixture workspace")
                tracked.append(module)
                module.safe_file = checker
        if common not in tracked:
            raise RuntimeError("Original common alias not installed")
        counters["installed_aliases"] = len(tracked)
        yield counters
    finally:
        lost = any(vars(module).get("safe_file") is not checker for module in tracked)
        foreign = False
        for module in list(sys.modules.values()):
            if module is not None and vars(module).get("safe_file") is checker:
                foreign |= not owned(module)
                module.safe_file = original
                counters["new_aliases_restored"] += module not in tracked
        for module in tracked:
            module.safe_file = original
        ACTIVE = False
        counters["restored"] = all(module.safe_file is original for module in tracked)
        if lost or foreign:
            raise RuntimeError("Offline path checker binding lost or escaped")


if __name__ == "__main__":
    raise RuntimeError("Offline helper only; no native command or allowance")
