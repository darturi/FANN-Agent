"""Finite B1b contract and integrity helpers; no providers or dispatch on import."""

import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
NAME = "torch-native-effort-frontier-v1"
VERSION = "native-effort-frontier.v1"
PREFIX = "reviews-native-effort-v1-"
SOURCE_MANIFEST = "082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc"
B1A_RECEIPT = "23b20ef84766584c89fff6da32654618ab4137f620d7393201f2368dd413d1f5"
P2C_RECEIPT = "533adf3dd53e10966c7edb74fbfd570e0e3bdbe8127ccc2f54f393bb893e6aec"
P2C_CAMPAIGN = "reviews-activation-calibration-v1-20261024T025706Z.c8557262"
FILTERS = ["unfiltered", "votes32", "votes108"]
CELLS = ["original640", "wrapped640", "wrapped320", "source"]
REGIMES = ["activation", "reuse"]
LEVELS = (320, 640)
SEED = 20261024
CRITERIA = {
    "aa_absolute_ms": 0.10,
    "aa_ratio": 1.02,
    "wrapper_maximum_overhead_ms": 0.10,
    "wrapper_maximum_ratio": 1.02,
    "minimum_saving_ms": 0.10,
    "maximum_ratio_for_benefit": 0.98,
    "development_recall_reserve": 0.0025,
    "final_recall_margin_diagnostic_only": 0.005,
    "minimum_reference_recall": 0.95,
    "bootstrap_samples": 10000,
    "bootstrap_seed": 20261019,
}
COUNTS = {
    "allocations": 2,
    "vectors": 200,
    "cases": 600,
    "cells": 4,
    "rounds": 2,
    "labels": 2,
    "slots_per_block": 9600,
    "retained_executions_per_block": 38400,
    "discarded_warmups_per_block": 9600,
    "conditioning_searches_per_block": 19200,
    "reference_searches_per_block": 2400,
    "qualification_searches_per_block": 36,
    "searches_per_block": 69636,
    "searches_total": 139272,
    "reader_connections_per_block": 14416,
    "post_slot_setting_audits_per_block": 14400,
}
OPERATIONS = {
    "qualification_exact": 6,
    "qualification_original640": 6,
    "qualification_source": 6,
    "qualification_wrapped": 18,
    "reference_exact": 600,
    "reference_original640": 600,
    "reference_wrapped320": 600,
    "reference_source": 600,
    "conditioning": 19200,
    "measurement": 48000,
}
SCOPE = {
    "shared_state": (
        "private restored database and once-loaded immutable snapshot; "
        "two native640 conditioning calls before every fresh slot"
    ),
    "activation": (
        "fresh reader(s), full constructor/connect/bind/setting cost plus first execution; "
        "both effort readers charged for wrapped cells"
    ),
    "reuse": "same slot's readers, one discarded post-activation warmup, three retained executions",
    "primary_timer": (
        "outer application nanoseconds; includes wrapper validation, "
        "predicate parsing and reader selection"
    ),
    "secondary_timer": "unchanged backend ordinary-native SQL timer; never the acceptance endpoint",
    "excluded_but_recorded": (
        "restore/import/snapshot, references, qualification, fixed conditioning, "
        "diagnostic post-slot settings audit and cleanup"
    ),
    "cold_index_claim": False,
    "production_default_claim": False,
    "router_fitting_allowed": False,
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
    root, relative = Path(root).resolve(), Path(name)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(p in (".", "..") for p in relative.parts)
    ):
        raise ValueError("Unsafe relative path: " + str(name))
    path = root / relative
    for parent in [path] + list(path.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("Symlink in input: " + str(name))
    if root not in path.resolve().parents:
        raise ValueError("Path escapes root")
    return path


def bootstrap(package):
    package = Path(package).resolve()
    sys.path[:0] = [str(package), str(package / "frozen"), str(package / "frozen/vendor")]
    from no_models import enforce

    enforce()


def inventory(items):
    groups = {i["group"] for i in items}
    if len(items) != 600 or len(groups) != 200:
        raise ValueError("Expected 200 already-exposed vectors / 600 cases")
    for group in groups:
        selected = [i for i in items if i["group"] == group]
        if len(selected) != 3 or {i["query"]["id"] for i in selected} != {
            group + "-" + f for f in FILTERS
        }:
            raise ValueError("Incomplete vector/filter group")
    return sorted(groups)


def protocol():
    return {
        "name": NAME,
        "version": VERSION,
        "counts": COUNTS,
        "operations_per_block": OPERATIONS,
        "criteria": CRITERIA,
        "measurement_scope": SCOPE,
        "cells": CELLS,
        "levels": list(LEVELS),
        "seed": SEED,
        "maximum_seconds": 6600,
        "resources": {"cpus": 4, "memory_gib": 32, "wall_hours": 2},
        "provider_calls_allowed": 0,
        "confirmation_queries_allowed": 0,
        "new_fits_allowed": 0,
        "source_manifest_sha256": SOURCE_MANIFEST,
        "b1a_receipt_sha256": B1A_RECEIPT,
        "p2c_receipt_sha256": P2C_RECEIPT,
        "synthetic_only": False,
    }


def verify(package, bundle=None):
    package = Path(package).resolve()
    manifest = read(package / "manifest.json")
    if manifest["version"] != VERSION:
        raise ValueError("Wrong experiment version")
    for name, expected in manifest["files"].items():
        if sha(safe_file(package, name)) != expected:
            raise ValueError("Package changed: " + name)
    cfg = read(package / "experiment.json")
    for key, value in protocol().items():
        if cfg.get(key) != value:
            raise ValueError("Protocol differs: " + key)
    if (
        sha(package / "b1a-receipt.json") != B1A_RECEIPT
        or sha(package / "p2c-receipt.json") != P2C_RECEIPT
    ):
        raise ValueError("Prior evidence receipt changed")
    frozen = package / "frozen"
    if sha(frozen / "manifest.json") != SOURCE_MANIFEST:
        raise ValueError("Frozen original differs")
    for name, expected in read(frozen / "manifest.json")["files"].items():
        if sha(safe_file(frozen, name)) != expected:
            raise ValueError("Frozen input changed: " + name)
    if inventory(lines(frozen / "inputs/queries.jsonl")) != cfg["development_groups"]:
        raise ValueError("Exposed cohort differs")
    if cfg["source_settings"] != read(package / "origin-settings.json"):
        raise ValueError("Origin settings differ")
    if read(package / "origin-source.json")["settings"] != cfg["source_settings"]:
        raise ValueError("Origin binding differs")
    if cfg["source_settings"].get("hnsw.iterative_scan") != "off":
        raise ValueError("Iterative scans must remain off")
    if int(cfg["source_settings"]["hnsw.ef_search"]) not in LEVELS:
        raise ValueError("Source comparator outside the frozen two-level scope")
    if bundle is not None:
        bootstrap(package)
        from control import verify as original_verify

        original_verify(frozen, Path(bundle))
        if read(Path(bundle) / "inputs/local-identity.json")["settings"] != cfg["source_settings"]:
            raise ValueError("Live bundle origin settings differ; do not redefine the baseline")
    return cfg


def protected(package, sources):
    """Hash prior results; never evaluate or load protected query values."""
    package, sources = Path(package), Path(sources)
    cfg = read(package / "experiment.json")
    bootstrap(package)
    prior = Path(cfg["prior_pilot_package"])
    if sha(prior / "manifest.json") != SOURCE_MANIFEST:
        raise ValueError("Original pilot package differs")
    for name, expected in read(package / "frozen/manifest.json")["files"].items():
        if sha(safe_file(prior, name)) != expected:
            raise ValueError("Prior pilot input changed: " + name)
    from protected import check

    result = check(sources, prior)
    for campaign, files in cfg["prior_raw_files"].items():
        for name, expected in files.items():
            if sha(safe_file(sources / campaign, name)) != expected:
                raise ValueError("Prior result changed: " + campaign + "/" + name)
        result[campaign] = files
    return result
