"""Reduce offline fixture I/O without changing production copies or source bytes."""

import contextlib
import hashlib
import json
import os
import shutil
import tempfile
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


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@contextlib.contextmanager
def prepared_seed(builder, emit=lambda *a: None):
    """Run the real synthetic builder once; retain full hash checks on every reuse."""
    original = builder.build
    stats = dict(requests=0, actual_builds=0, reused=0, seed_verifications=0, restored=False)
    seed = archive = baseline = archive_hash = checksum_hash = None
    requested = set()
    with tempfile.TemporaryDirectory(prefix="cc-seed-") as temporary:

        def check():
            emit("fixture_stage", "shared_seed_verify.before")
            if fingerprint(seed) != baseline or file_sha(archive) != archive_hash:
                raise RuntimeError("Prepared synthetic seed/archive changed")
            if file_sha(Path(str(archive) + ".sha256")) != checksum_hash:
                raise RuntimeError("Prepared synthetic archive checksum changed")
            stats["seed_verifications"] += 1
            emit("fixture_stage", "shared_seed_verify.after")

        def build(output=None, testing=False):
            nonlocal seed, archive, baseline, archive_hash, checksum_hash
            if testing is not True or output is None:
                raise RuntimeError("Prepared seed only accepts explicit offline synthetic builds")
            target = Path(output).resolve()
            if target in requested or target.exists():
                raise FileExistsError("Preserve existing synthetic build target")
            requested.add(target)
            stats["requests"] += 1
            if seed is None:
                emit("fixture_stage", "seed_build.before")
                seed = Path(original(Path(temporary) / "seed", testing=True))
                if not seed.resolve().is_relative_to(Path(temporary).resolve()):
                    raise RuntimeError("Builder returned seed outside owned scratch")
                if (
                    json.loads((seed / "experiment.json").read_text()).get("synthetic_fixture")
                    is not True
                ):
                    raise RuntimeError("Builder returned a native seed")
                archive = seed.parent / (seed.name + ".tar.gz")
                archive_hash = file_sha(archive)
                if Path(str(archive) + ".sha256").read_text().split() != [
                    archive_hash,
                    archive.name,
                ]:
                    raise RuntimeError("Prepared archive checksum differs")
                baseline = fingerprint(seed)
                checksum_hash = file_sha(Path(str(archive) + ".sha256"))
                stats["actual_builds"] += 1
                emit("fixture_stage", "seed_build.after")
            else:
                stats["reused"] += 1
            check()
            return seed

        builder.build = build
        try:
            yield stats
        finally:
            builder.build = original
            stats["restored"] = builder.build is original
            if baseline is not None:
                check()


@contextlib.contextmanager
def fixture_copies(module, emit=lambda *a: None):
    """Wrap only the existing runtime fixture, including imported test aliases."""
    original_fixture = module.runtime_fixture
    original_copy = shutil.copytree
    original_reseal = module.reseal
    stats = dict(clones=0, linked_files=0, mutable_copies=0, seeds_verified=0, reseals=0)

    def runtime_fixture(root, seed=None, fault=None):
        if seed is None:
            return original_fixture(root, seed, fault)
        seed, destination = Path(seed).resolve(), Path(root).resolve() / "package"
        config = json.loads((seed / "experiment.json").read_text())
        if config.get("synthetic_fixture") is not True:
            raise RuntimeError("Offline clone requires synthetic seed")
        emit("fixture_stage", "fixture_seed_hash.before")
        before = fingerprint(seed)
        emit("fixture_stage", "fixture_seed_hash.after")
        if not MUTABLE <= set(before):
            raise RuntimeError("Synthetic seed mutable inventory differs")
        used = False

        def reseal(package):
            package = Path(package).resolve()
            if package != destination:
                return original_reseal(package)
            emit("fixture_stage", "fixture_reseal.before")
            # The immutable files are the same hardlinked bytes already hashed above.
            # Recompute every mutable content hash; reject new, missing or detached files.
            paths = {str(p.relative_to(package)): p for p in package.rglob("*") if p.is_file()}
            if set(paths) != set(before) or any(p.is_symlink() for p in package.rglob("*")):
                raise RuntimeError("Synthetic reseal inventory changed")
            for name, path in paths.items():
                if name not in MUTABLE and not os.path.samefile(seed / name, path):
                    raise RuntimeError("Synthetic immutable file detached from seed")
            manifest = paths["manifest.json"]
            manifest.unlink()
            value = dict(
                version=module.C.VERSION,
                files={
                    name: file_sha(path) if name in MUTABLE else before[name]
                    for name, path in paths.items()
                    if name != "manifest.json" and path.name != "submission-binding.json"
                },
            )
            module.C.save(manifest, value)
            stats["reseals"] += 1
            emit("fixture_stage", "fixture_reseal.after")

        def clone(src, dst, *args, **kwargs):
            nonlocal used
            if Path(src).resolve() != seed or Path(dst).resolve() != destination:
                return original_copy(src, dst, *args, **kwargs)
            if used or args or kwargs:
                raise RuntimeError("Unexpected synthetic clone invocation")
            used = True
            emit("fixture_stage", "fixture_clone.before")

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
            emit("fixture_stage", "fixture_clone.after")
            return value

        try:
            with patch.object(shutil, "copytree", clone), patch.object(module, "reseal", reseal):
                return original_fixture(root, seed, fault)
        finally:
            emit("fixture_stage", "fixture_final_seed_hash.before")
            if fingerprint(seed) != before:
                raise RuntimeError("Offline fixture changed immutable seed bytes")
            stats["seeds_verified"] += 1
            emit("fixture_stage", "fixture_final_seed_hash.after")

    module.runtime_fixture = runtime_fixture
    try:
        yield stats
    finally:
        module.runtime_fixture = original_fixture
