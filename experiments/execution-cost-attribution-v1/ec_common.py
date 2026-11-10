"""Pinned P1 attribution protocol and provider-free integrity helpers."""

import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
NAME = "torch-execution-cost-attribution-v1"
VERSION = "execution-cost-attribution.v1"
SOURCE_MANIFEST = "082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc"
RECEIPT_HASH = "f5ee1f8a9a5090b687d619487c9a02883441c8e1e993673b030b2ff230e04d91"
CANDIDATE = "a014a290966444a86614f1e5be1960dad2fb8684044e85e9df82899911062b0d"
EPISODE = "20261022T192817Z-66ed81d6"
PILOT = "reviews-selective-agent-v1-pilot-20261022T202240Z.j9ackcxc"
FILTERS = ["unfiltered", "votes32", "votes108"]
ARMS = ["candidate", "matched-continue", "routed-native"]
COUNTS = {
    "allocations": 3,
    "development_vectors": 200,
    "cases": 600,
    "diagnostic_vectors": 60,
    "diagnostic_cases": 180,
    "arms": 3,
    "getter_searches": 921,
    "reuse_repetitions": 3,
    "main_searches": 22521,
    "diagnostic_searches": 5400,
    "searches_per_block": 27921,
    "searches_total": 83763,
    "retained_pairs_per_block": 7200,
    "warmups_per_block": 1800,
    "diagnostic_pairs_per_block": 2160,
    "diagnostic_warmups_per_block": 540,
    "control_evictions_per_block": 2340,
}


def read(path):
    return json.loads(Path(path).read_text())


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def save(path, value):
    with Path(path).open("xb") as handle:
        handle.write(encoded(value))


def replace(path, value):
    path = Path(path)
    temporary = path.with_name("." + path.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(encoded(value))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def safe_file(root, name):
    root = Path(root).resolve()
    relative = Path(name)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(p in (".", "..") for p in relative.parts)
    ):
        raise ValueError("Unsafe relative path: " + name)
    path = root / relative
    for parent in [path] + list(path.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("Symlink in input: " + name)
    if root not in path.resolve().parents:
        raise ValueError("Path escapes root: " + name)
    return path


def bootstrap(package):
    package = Path(package).resolve()
    sys.path[:0] = [str(package), str(package / "frozen"), str(package / "frozen/vendor")]
    from no_models import enforce

    enforce()


def diagnostic_groups(items):
    groups = sorted({i["group"] for i in items}, key=lambda g: digest(["diagnostic-v1", g]))
    if len(groups) != 200 or len(items) != 600:
        raise ValueError("Expected the original 200 development vectors / 600 cases")
    for group in groups:
        selected = [i for i in items if i["group"] == group]
        if {i["query"]["id"].rsplit("-", 1)[-1] for i in selected} != set(FILTERS) or len(
            selected
        ) != 3:
            raise ValueError("Incomplete vector/filter cluster")
    return groups[:60]


def verify(package, bundle=None):
    package = Path(package).resolve()
    manifest = read(package / "manifest.json")
    if manifest["version"] != VERSION:
        raise ValueError("Wrong experiment version")
    for name, expected in manifest["files"].items():
        if sha(safe_file(package, name)) != expected:
            raise ValueError("Package changed: " + name)
    cfg = read(package / "experiment.json")
    for key, expected in [
        ("name", NAME),
        ("version", VERSION),
        ("counts", COUNTS),
        ("provider_calls_allowed", 0),
        ("confirmation_queries_allowed", 0),
        ("source_manifest_sha256", SOURCE_MANIFEST),
        ("candidate_hash", CANDIDATE),
        ("synthetic_only", False),
        ("blocks", 3),
        ("maximum_seconds", 6600),
        ("seed", 20261022),
        ("filters", FILTERS),
        ("candidate_selection_allowed", False),
        ("resources", {"cpus": 4, "memory_gib": 32, "wall_hours": 2}),
    ]:
        if cfg.get(key) != expected:
            raise ValueError("Protocol differs: " + key)
    frozen = package / "frozen"
    if sha(frozen / "manifest.json") != SOURCE_MANIFEST:
        raise ValueError("Frozen source manifest differs")
    for name, expected in read(frozen / "manifest.json")["files"].items():
        if sha(safe_file(frozen, name)) != expected:
            raise ValueError("Frozen input changed: " + name)
    items = lines(frozen / "inputs/queries.jsonl")
    if diagnostic_groups(items) != cfg["diagnostic_groups"]:
        raise ValueError("Diagnostic sample differs")
    if set(read(package / "candidate.json")) != {CANDIDATE}:
        raise ValueError("Candidate changed")
    if read(package / "candidate.json")[CANDIDATE] != read(frozen / "candidates.json")[CANDIDATE]:
        raise ValueError("Candidate is not byte-equivalent data from the frozen pilot")
    if bundle is not None:
        bootstrap(package)
        from control import verify as original_verify

        original_verify(frozen, Path(bundle))
    return cfg


def protected(package, sources):
    """Preserve original studies and the completed pilot; never read holdout values."""
    package, sources = Path(package), Path(sources)
    cfg = read(package / "experiment.json")
    bootstrap(package)
    prior = Path(cfg["prior_pilot_package"])
    if sha(prior / "manifest.json") != SOURCE_MANIFEST:
        raise ValueError("Prior remote pilot package differs")
    for name, expected in read(package / "frozen/manifest.json")["files"].items():
        if sha(safe_file(prior, name)) != expected:
            raise ValueError("Prior remote pilot input differs: " + name)
    from protected import check

    result = check(sources, prior)
    pilot = sources / PILOT
    for name, expected in cfg["prior_pilot_raw_sha256"].items():
        if sha(safe_file(pilot, name)) != expected:
            raise ValueError("Completed pilot raw result changed: " + name)
    result["execution-cost-source-pilot"] = cfg["prior_pilot_raw_sha256"]
    result["execution-cost-source-package"] = SOURCE_MANIFEST
    return result
