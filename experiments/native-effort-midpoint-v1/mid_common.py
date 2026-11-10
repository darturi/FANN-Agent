"""Fixed B1b2 protocol; standard-library helpers, no execution on import."""

import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
NAME = "torch-native-effort-midpoint-v1"
VERSION = "native-effort-midpoint.v1"
PREFIX = "reviews-native-midpoint-v1-"
SOURCE_MANIFEST = "082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc"
ANCHOR_MANIFEST = "35a09d4e2fd71598a023f6479e418d9e8bc90434d764a53564c60a5436b69c1f"
DESIGN_SHA = "09176883e515ccad645523cab67fa756757230713a82a144959fe3b447102ed7"
REVIEW_SHA = "02a522d229b178941014b1cb6b9060bead759ca9ff305db0662f8867f202c39d"
B1B_RECEIPT_SHA = "df715ce4beea66e6d96b17e14807eb4a75d5504e3b83a8af66118e3248f2266a"
PROFILE_SHA = "b2974c2c65d40780d207109d9bbd298b2628ea58abde673c0dd479c1a0e52ed3"
FILTERS = ["unfiltered", "votes32", "votes108"]
CELLS = ["native640", "native480"]
LEVELS = (480, 640)
SEED = 20261025
CRITERIA = {
    "aa_absolute_ms": 0.10,
    "aa_ratio": 1.02,
    "minimum_saving_ms": 0.10,
    "maximum_ratio_for_benefit": 0.98,
    "development_recall_reserve": 0.0025,
    "final_recall_margin_diagnostic_only": 0.005,
    "minimum_reference_recall": 0.95,
    "bootstrap_samples": 10000,
    "bootstrap_seed": 20261019,
}
COUNTS = {
    "allocations": 1,
    "temporal_blocks": 2,
    "vectors": 200,
    "cases": 600,
    "qualification_searches": 30,
    "reference_searches": 1800,
    "quality_stop_searches": 1830,
    "slots_per_block": 4800,
    "retained_executions_per_block": 14400,
    "discarded_warmups_per_block": 4800,
    "conditioning_searches_per_block": 9600,
    "timing_searches_per_block": 28800,
    "searches_total": 59430,
    "reader_admissions_quality_stop": 10,
    "reader_admissions_total": 14,
    "maximum_live_readers": 5,
    "aa_interval_checks": 16,
}
QUALITY_OPERATIONS = {
    "qualification_exact": 6,
    "qualification_native640": 12,
    "qualification_native480": 12,
    "reference_exact": 600,
    "reference_native640": 600,
    "reference_native480": 600,
}
OPERATIONS = {**QUALITY_OPERATIONS, "conditioning": 19200, "warmup": 9600, "measurement": 28800}
SCOPE = {
    "primary_timer": (
        "Full outer guarded ordinary-native warm query; both arms prevalidated identically"
    ),
    "shared_state": (
        "One private restore/snapshot; fixed owned reader per arm/label across two temporal blocks"
    ),
    "separately_charged": (
        "restore/import/snapshot/request admission, reader startup, qualification/references, "
        "conditioning, warmups, audits, cleanup"
    ),
    "activation_qualification": False,
    "cold_index_claim": False,
    "production_default_claim": False,
    "router_fitting_allowed": False,
    "independent_confirmation": False,
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
    with Path(path).open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


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


def context(query):
    if type(query["k"]) is not int or query["k"] != 10:
        raise ValueError("Requires k10")
    predicate = query.get("filter")
    if predicate is None:
        return "unfiltered"
    if (
        isinstance(predicate, dict)
        and set(predicate) == {"field", "op", "value"}
        and predicate["field"] == "m_000000"
        and predicate["op"] == "gte"
        and type(predicate["value"]) is int
        and predicate["value"] in (32, 108)
    ):
        return "votes" + str(predicate["value"])
    raise ValueError("Outside the sealed three-context inventory")


def inventory(items):
    groups = sorted({i["group"] for i in items})
    if len(items) != 600 or len(groups) != 200:
        raise ValueError("Requires the existing200 vectors/600 cases")
    for group in groups:
        selected = [i for i in items if i["group"] == group]
        if (
            len(selected) != 3
            or {context(i["query"]) for i in selected} != set(FILTERS)
            or any(i["query"]["id"] != group + "-" + context(i["query"]) for i in selected)
            or any(i["query"]["vector"] != selected[0]["query"]["vector"] for i in selected)
        ):
            raise ValueError("Cohort/filter/vector identity differs")
    return groups


def bootstrap(package):
    package = Path(package).resolve()
    sys.path[:0] = [str(package), str(package / "frozen"), str(package / "frozen/vendor")]
    from no_models import enforce

    enforce()


def protocol():
    return {
        "name": NAME,
        "version": VERSION,
        "counts": COUNTS,
        "operations": OPERATIONS,
        "quality_operations": QUALITY_OPERATIONS,
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
        "b1b_manifest_sha256": ANCHOR_MANIFEST,
        "design_sha256": DESIGN_SHA,
        "review_receipt_sha256": REVIEW_SHA,
        "b1b_receipt_sha256": B1B_RECEIPT_SHA,
        "synthetic_only": False,
    }


def verify(package, bundle=None):
    package = Path(package).resolve()
    manifest = read(package / "manifest.json")
    if manifest["version"] != VERSION:
        raise ValueError("Wrong package version")
    for name, expected in manifest["files"].items():
        if sha(safe_file(package, name)) != expected:
            raise ValueError("Package changed: " + name)
    cfg = read(package / "experiment.json")
    for key, expected in protocol().items():
        if cfg.get(key) != expected:
            raise ValueError("Contract differs: " + key)
    for name, expected in (
        ("DESIGN.md", DESIGN_SHA),
        ("review-receipt.json", REVIEW_SHA),
        ("b1b-receipt.json", B1B_RECEIPT_SHA),
        ("b1b-manifest.json", ANCHOR_MANIFEST),
        ("frozen/manifest.json", SOURCE_MANIFEST),
    ):
        if sha(package / name) != expected:
            raise ValueError("Pinned evidence differs: " + name)
    for name, expected in read(package / "frozen/manifest.json")["files"].items():
        if sha(safe_file(package / "frozen", name)) != expected:
            raise ValueError("Frozen execution changed: " + name)
    groups = inventory(lines(package / "frozen/inputs/queries.jsonl"))
    if groups != cfg["development_groups"]:
        raise ValueError("Exposed cohort differs")
    if (
        cfg["source_settings"] != read(package / "origin-settings.json")
        or read(package / "origin-source.json")["settings"] != cfg["source_settings"]
        or cfg["source_settings"]["hnsw.ef_search"] != "320"
        or cfg["source_settings"]["hnsw.iterative_scan"] != "off"
    ):
        raise ValueError("Origin/source scope changed")
    from mid_measure import order_manifest

    if read(package / "order.json") != order_manifest(
        lines(package / "frozen/inputs/queries.jsonl")
    ):
        raise ValueError("Schedule differs")
    if bundle is not None:
        bootstrap(package)
        from control import verify as original_verify

        original_verify(package / "frozen", Path(bundle))
        if read(Path(bundle) / "inputs/local-identity.json")["settings"] != cfg["source_settings"]:
            raise ValueError("Live origin settings differ")
    return cfg


def protected(package, sources):
    package, sources = Path(package), Path(sources)
    cfg = read(package / "experiment.json")
    bootstrap(package)
    prior = Path(cfg["prior_pilot_package"])
    if sha(prior / "manifest.json") != SOURCE_MANIFEST:
        raise ValueError("Prior pilot changed")
    for name, expected in read(package / "frozen/manifest.json")["files"].items():
        if sha(safe_file(prior, name)) != expected:
            raise ValueError("Prior source changed: " + name)
    from protected import check

    result = check(sources, prior)
    for campaign, files in cfg["prior_raw_files"].items():
        for name, expected in files.items():
            if sha(safe_file(sources / campaign, name)) != expected:
                raise ValueError("Prior result changed: " + campaign + "/" + name)
        result[campaign] = files
    anchor = Path(cfg["prior_b1b_package"])
    if sha(anchor / "manifest.json") != ANCHOR_MANIFEST:
        raise ValueError("Prior B1b package changed")
    for name, expected in read(package / "b1b-manifest.json")["files"].items():
        if sha(safe_file(anchor, name)) != expected:
            raise ValueError("Prior B1b source changed: " + name)
    result["b1b_sealed_package"] = {"manifest_sha256": ANCHOR_MANIFEST}
    return result


def campaign_identity(campaign, package):
    record = read(Path(campaign) / "submission.json")
    name = Path(record["campaign"]).name
    if (
        not re.fullmatch(re.escape(PREFIX) + r"[0-9]{8}T[0-9]{6}Z\.[A-Za-z0-9_-]+", name)
        or record["package_manifest_sha256"] != sha(Path(package) / "manifest.json")
        or record["counts"] != COUNTS
        or set(record["jobs"]) != {"block-0"}
        or record["dispatch"].get("block-0")
        != {"status": "submitted", "job_id": record["jobs"]["block-0"]}
    ):
        raise ValueError("Campaign/submission/package/job identity differs")
    return name


def parity(left, right, path="result"):
    if type(left) is not type(right):
        raise ValueError("Remote/local type differs: " + path)
    if isinstance(left, dict):
        if set(left) != set(right):
            raise ValueError("Remote/local keys differ: " + path)
        for key in left:
            parity(left[key], right[key], path + "/" + key)
    elif isinstance(left, list):
        if len(left) != len(right):
            raise ValueError("Remote/local length differs: " + path)
        for index, (a, b) in enumerate(zip(left, right)):
            parity(a, b, path + "/" + str(index))
    elif isinstance(left, float):
        if not math.isfinite(left) or not math.isfinite(right) or abs(left - right) > 1e-12:
            raise ValueError("Remote/local float differs: " + path)
    elif left != right:
        raise ValueError("Remote/local value differs: " + path)


class Budget:
    def __init__(self):
        self.calls, self.operations, self.started = 0, Counter(), time.monotonic()

    def check(self):
        if time.monotonic() - self.started > 6600:
            raise RuntimeError("Work deadline exhausted")

    def reserve(self, operation):
        self.check()
        if (
            operation not in OPERATIONS
            or self.calls >= COUNTS["searches_total"]
            or self.operations[operation] >= OPERATIONS[operation]
        ):
            raise RuntimeError("Search/operation ceiling exhausted")
        self.operations[operation] += 1
        self.calls += 1
