"""Pinned P2c calibration protocol and provider-free integrity helpers."""

import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
NAME = "torch-activation-timing-calibration-v1"
VERSION = "activation-timing-calibration.v1"
SOURCE_MANIFEST = "082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc"
RECEIPT_HASH = "f5ee1f8a9a5090b687d619487c9a02883441c8e1e993673b030b2ff230e04d91"
CANDIDATE = "a014a290966444a86614f1e5be1960dad2fb8684044e85e9df82899911062b0d"
EPISODE = "20261022T192817Z-66ed81d6"
PILOT = "reviews-selective-agent-v1-pilot-20261022T202240Z.j9ackcxc"
FILTERS = ["unfiltered", "votes32", "votes108"]
P2B_MANIFEST = "7c82194d375a77f29356e3620d2f011b2b0e452b9954defcb75aaec90f29350d"
P2B_RECEIPT = "ba3f5116ab2583d61fac024dbb899112803fcc7fad18687a9ed64bc5f374a88f"
P2B_CAMPAIGN = "reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0"
P2A_MANIFEST = "c4c00e12a08963751ab20aed3f195ed3af2a515be40c0bdd619ce57209bca60c"
P2A_RECEIPT = "5b2449a02ec55ad4c4670e210dbff9ab51ec9b50a9b7c2312306c206826bfdb5"
P2A_CAMPAIGN = "reviews-prepared-policy-v1-20261023T161756Z.8uq_covr"
VARIANTS = ["original", "owned", "admission"]
SEMANTIC_ARMS = ["candidate", "matched-continue", "routed-native"]
CELLS = [v + "/" + a for a in SEMANTIC_ARMS for v in VARIANTS] + ["native/native"]
ARMS = [v + "-" + label + "/" + a for v, a in (c.split("/") for c in CELLS) for label in ("a", "b")]
CONDITIONING_CALLS = 2
ROUNDS = 2
P1_MANIFEST = "4c2f475664784b1851b1274a5c696bccbc55ee41c659a469c3643eb0ca0109c0"
P1_RECEIPT = "16647a2486df6f191a764f4600e17ee2437f01352edc76eb3646490ca3b90378"
P1_CAMPAIGN = "reviews-execution-cost-v1-20261023T044408Z.a08qpwdi"
CRITERIA = {
    "activation_minimum_saving_ms": 0.10,
    "activation_maximum_ratio": 0.98,
    "candidate_reuse_minimum_saving_ms": 0.10,
    "candidate_reuse_maximum_ratio": 0.98,
    "maximum_regression_ms": 0.10,
    "maximum_regression_ratio": 1.02,
    "aa_equivalence_ms": 0.10,
    "aa_equivalence_ratio": 1.02,
    "require_activation_saving_in_each_block": True,
}
SCOPE = {
    "shared_query_state": "exactly_two_ordinary_native_conditioning_calls_per_slot",
    "policy_session": "fresh_after_conditioning",
    "python_policy_cache": "cleared_before_conditioning",
    "active_installation": "eviction_sentinel_before_conditioning",
    "admission_and_first_execution": "fully_charged",
    "cold_index_claim": False,
    "retroactive_P2b_qualification": False,
}
COUNTS = {
    "allocations": 2,
    "development_vectors": 200,
    "cases": 600,
    "diagnostic_cases": 0,
    "arms": 20,
    "cells": 10,
    "rounds": 2,
    "conditioning_calls_per_slot": 2,
    "getter_searches": 921,
    "reuse_repetitions": 3,
    "main_searches": 296121,
    "searches_per_block": 296121,
    "searches_total": 592242,
    "retained_pairs_per_block": 96000,
    "warmups_per_block": 24000,
    "conditioning_searches_per_block": 48000,
    "slots_per_block": 24000,
    "proof_executions_per_block": 5400,
    "control_evictions_per_block": 24000,
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


def inventory(items):
    groups = {i["group"] for i in items}
    if len(groups) != 200 or len(items) != 600:
        raise ValueError("Expected the original 200 exposed vectors / 600 cases")
    for group in groups:
        selected = [i for i in items if i["group"] == group]
        if len(selected) != 3 or {i["query"]["id"].rsplit("-", 1)[-1] for i in selected} != set(
            FILTERS
        ):
            raise ValueError("Incomplete vector/filter group")
    return sorted(groups)


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
        ("blocks", COUNTS["allocations"]),
        ("maximum_seconds", 10200),
        ("seed", 20261022),
        ("filters", FILTERS),
        ("candidate_selection_allowed", False),
        ("criteria", CRITERIA),
        ("measurement_scope", SCOPE),
        ("source_attribution_manifest_sha256", P1_MANIFEST),
        ("source_attribution_receipt_sha256", P1_RECEIPT),
        ("source_p2a_manifest_sha256", P2A_MANIFEST),
        ("source_p2a_receipt_sha256", P2A_RECEIPT),
        ("variants", VARIANTS),
        ("cells", CELLS),
        ("rounds", ROUNDS),
        ("conditioning_calls_per_slot", CONDITIONING_CALLS),
        ("source_p2b_manifest_sha256", P2B_MANIFEST),
        ("source_p2b_receipt_sha256", P2B_RECEIPT),
        ("resources", {"cpus": 4, "memory_gib": 32, "wall_hours": 3}),
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
    if inventory(items) != cfg["development_groups"]:
        raise ValueError("Development group inventory differs")
    if set(read(package / "candidate.json")) != {CANDIDATE}:
        raise ValueError("Candidate changed")
    if read(package / "candidate.json")[CANDIDATE] != read(frozen / "candidates.json")[CANDIDATE]:
        raise ValueError("Candidate is not byte-equivalent data from the frozen pilot")
    if sha(package / "attribution-receipt.json") != P1_RECEIPT:
        raise ValueError("Attribution receipt changed")
    if sha(package / "p2a-receipt.json") != P2A_RECEIPT:
        raise ValueError("P2a receipt changed")
    if sha(package / "p2a-manifest.json") != P2A_MANIFEST:
        raise ValueError("Frozen P2a manifest changed")
    reference_hashes = {
        n: read(package / "p2a-manifest.json")["files"][n]
        for n in ("pp_backend.py", "pp_session.py")
    }
    if cfg["p2a_reference_files_sha256"] != reference_hashes:
        raise ValueError("P2a reference file pins differ")
    for name in ("pp_backend.py", "pp_session.py"):
        if sha(package / name) != cfg["p2a_reference_files_sha256"][name]:
            raise ValueError("Frozen P2a reference changed: " + name)
    if (
        sha(package / "p2b-manifest.json") != P2B_MANIFEST
        or sha(package / "p2b-receipt.json") != P2B_RECEIPT
    ):
        raise ValueError("Verified P2b sources differ")
    expected = {
        n: read(package / "p2b-manifest.json")["files"][n]
        for n in ("pp_backend.py", "pp_session.py", "pb_policy.py", "pb_session.py")
    }
    expected["p2b_report_reference.py"] = read(package / "p2b-manifest.json")["files"][
        "pp_report.py"
    ]
    if cfg["p2b_reference_files_sha256"] != expected:
        raise ValueError("P2b reference file pins differ")
    for name, value in expected.items():
        if sha(package / name) != value:
            raise ValueError("Frozen execution/gate reference changed: " + name)
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
    attribution = read(package / "attribution-receipt.json")
    for name, expected in attribution["raw_files_verified"].items():
        if sha(safe_file(sources / P1_CAMPAIGN, name)) != expected:
            raise ValueError("Completed attribution result changed: " + name)
    result["prepared-policy-source-attribution"] = attribution["raw_files_verified"]
    p2a = read(package / "p2a-receipt.json")
    for name, expected in p2a["raw_files_verified"].items():
        if sha(safe_file(sources / P2A_CAMPAIGN, name)) != expected:
            raise ValueError("Completed P2a result changed: " + name)
    result["admission-source-p2a"] = p2a["raw_files_verified"]
    p2b = read(package / "p2b-receipt.json")
    for name, expected in p2b["raw_files_verified"].items():
        if sha(safe_file(sources / P2B_CAMPAIGN, name)) != expected:
            raise ValueError("Completed P2b result changed: " + name)
    result["calibration-source-p2b"] = p2b["raw_files_verified"]
    return result
