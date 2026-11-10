"""Construct and review a candidate-bound archive without contacting Torch."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from rb_evidence import load_evidence, load_frozen
from rb_native import CANDIDATE, DISPOSITION, GRAPH, IMAGE, MODULE, PROPOSAL
from rb_plan import PACKAGE, PILOT_MANIFEST, PINS, ROOT, load_plan, pinned, require
from rb_seal import (
    PACKAGE_NAME,
    json_bytes,
    make_archive,
    seal_directory,
    verify_directory,
    write_once,
)
from rb_stats import quality

HERE = Path(__file__).resolve().parent
EPISODE = ROOT / "trials/reviews-persistent-batch-proposal-v1/episode"
OUTPUT = ROOT / "trials" / PACKAGE_NAME
CALIBRATION_BASE = "f31ff3fc13cb2443c1a60565c30d856d15a98f3cd6e14f5b1ff71924b443464d"
PERSISTENT_BASE = "0e3b5175e95913280b8cf9fede6dc1c5ad2ffb776987ff9d73fb2996b3c483ea"
REQUEST_TIMING_BASE = "25e6fc07a9bf4c55b024d66112dcbdab71bcb23d0bdba0408f7325d0721396a3"
CALIBRATION_REPLACEMENTS = ("rb_measure.py", "rb_native.py", "rb_stats.py", "rb_verify.py")
RUNTIME = (
    "rb_evidence.py",
    "rb_measure.py",
    "rb_native.py",
    "rb_plan.py",
    "rb_seal.py",
    "rb_stats.py",
    "rb_verify.py",
)
PILOT_FILES = (
    "experiment.json",
    "source-index.json",
    "candidates.json",
    "inputs/queries.jsonl",
    "inputs/qualification.jsonl",
    "contract.py",
    "legacy_contract.py",
    "legacy_execution.py",
    "reference_backend.py",
    "fd_contract.py",
    "fd_execution.py",
    "fd_policy_tools.py",
    "policy.py",
    "execution.py",
    "no_models.py",
    "database.py",
    "runtime_base.py",
    "design.py",
)


def copy_bytes(output, data):
    output.parent.mkdir(parents=True, exist_ok=True)
    write_once(output, data)


def build():
    require(not OUTPUT.exists(), "Package directory already exists; preserve and inspect it")
    candidate_bytes = pinned(EPISODE / "proposal.json", PROPOSAL)
    disposition = json.loads(pinned(EPISODE / "disposition.json", DISPOSITION))
    freeze = json.loads((EPISODE / "candidate-freeze.json").read_bytes())
    require(
        freeze["candidate_sha256"] == PROPOSAL
        and freeze["frozen_design_inputs_sha256"] == PINS
        and freeze["policy_semantic_sha256"] == CANDIDATE
        and freeze["proposal_disposition_sha256"] == DISPOSITION
        and freeze["torch_released"] is False
        and disposition["decision"] == "offline_screen_pass",
        "Frozen disposition changed",
    )
    plan = load_plan(ROOT)
    frozen = load_frozen(ROOT)
    evidence = load_evidence(plan, frozen, json.loads(candidate_bytes), ROOT)
    saved_recall = quality(plan, frozen, evidence, "candidate")
    require(
        evidence.identities["candidate"] == CANDIDATE
        and saved_recall == disposition["saved_development_replay"]
        and saved_recall["passes"],
        "Independent saved-data screen changed",
    )
    source = ROOT / PACKAGE
    pilot_bytes = pinned(source / "manifest.json", PILOT_MANIFEST)
    pilot_pins = json.loads(pilot_bytes)["files"]
    module = pinned(source / "modules/vector.so", MODULE)
    require(
        module[:6] == b"\x7fELF\x02\x01" and int.from_bytes(module[18:20], "little") == 62,
        "Expected the pinned x86_64 ELF module",
    )

    OUTPUT.mkdir(mode=0o700)
    package = OUTPUT / PACKAGE_NAME
    package.mkdir(mode=0o700)
    root = package / "inputs"
    for name in RUNTIME:
        copy_bytes(package / name, (HERE / name).read_bytes())
    for name, expected in PINS.items():
        copy_bytes(root / name, pinned(ROOT / name, expected))
    staged_source = root / PACKAGE
    copy_bytes(staged_source / "manifest.json", pilot_bytes)
    for name in (*PILOT_FILES, *(n for n in pilot_pins if n.startswith("vendor/"))):
        copy_bytes(staged_source / name, pinned(source / name, pilot_pins[name]))
    copy_bytes(package / "modules/vector.so", module)
    copy_bytes(package / "proposal.json", candidate_bytes)
    copy_bytes(package / "candidate-freeze.json", (EPISODE / "candidate-freeze.json").read_bytes())
    copy_bytes(
        package / "native-inputs.json",
        json_bytes(
            {
                "identities": evidence.identities,
                "references": evidence.references,
                "eligible": {filt: sorted(ids) for filt, ids in evidence.eligible.items()},
                "outcomes": evidence.outcomes,
                "saved_recall": saved_recall,
            }
        ),
    )
    checksum = seal_directory(package)
    # Exercise the exact staged entry in a fresh process before archiving its bytes.
    result = subprocess.run(
        [sys.executable, "-B", str(package / "rb_native.py"), "verify", str(package), checksum],
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
        env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
    )
    review = json.loads(result.stdout)
    require(
        review
        == {
            "status": "verified_held",
            "candidate": CANDIDATE,
            "sessions": 60,
            "cases": 600,
            "dispatch_released": False,
        },
        "Unexpected staged package review",
    )
    archive = OUTPUT / f"{PACKAGE_NAME}.tar.gz"
    archive_sha = make_archive(package, archive, checksum)
    receipt = {
        **review,
        "archive": archive.name,
        "archive_sha256": archive_sha,
        "package_manifest_sha256": checksum,
        "image_sha256": IMAGE,
        "module_sha256": MODULE,
        "index_identity": GRAPH,
        "files": len(json.loads((package / "manifest.json").read_bytes())["files"]),
        "offline_replay_stops": saved_recall["stops"],
        "staged_verification_stdout": result.stdout.strip(),
        "torch_access": 0,
        "provider_calls": 0,
        "ann_searches": 0,
        "exact_searches": 0,
        "new_fits": 0,
        "confirmation_queries": 0,
        "allocations": 0,
        "native_entry_exercised": False,
    }
    write_once(OUTPUT / "PACKAGE-REVIEW.json", json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


def build_variant(prior_name, prior_sha, output_name, replacements, added, mode):
    prior = OUTPUT / prior_name / PACKAGE_NAME
    files = verify_directory(prior, prior_sha)
    output = OUTPUT / output_name
    output.mkdir(mode=0o700)
    package = output / PACKAGE_NAME
    package.mkdir(mode=0o700)
    for name, record in files.items():
        data = (
            (HERE / name).read_bytes()
            if name in replacements
            else pinned(prior / name, record["sha256"])
        )
        copy_bytes(package / name, data)
    require(added not in files, "Experiment entry already present")
    copy_bytes(package / added, (HERE / added).read_bytes())
    checksum = seal_directory(package)
    result = subprocess.run(
        [sys.executable, "-EsB", str(package / "rb_native.py"), "verify", str(package), checksum],
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    review = json.loads(result.stdout)
    require(
        review
        == {
            "status": "verified_held",
            "candidate": CANDIDATE,
            "sessions": 60,
            "cases": 600,
            mode: True,
            "dispatch_released": False,
        },
        "Unexpected experiment package review",
    )
    archive = output / f"{PACKAGE_NAME}.tar.gz"
    receipt = {
        **review,
        "previous_package_manifest_sha256": prior_sha,
        "package_manifest_sha256": checksum,
        "archive_sha256": make_archive(package, archive, checksum),
        "archive": archive.name,
        "files": len(files) + 1,
        "allocations": 0,
        "native_searches": 0,
        "confirmation_queries": 0,
    }
    write_once(output / "PACKAGE-REVIEW.json", json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--calibration", action="store_true", help="Build the held timing guest")
    mode.add_argument("--persistent", action="store_true", help="Build the held six-batch guest")
    mode.add_argument("--request-timing", action="store_true", help="Build the held diagnostic")
    args = parser.parse_args()
    if args.calibration:
        build_variant(
            "startup-memory-gate-v1",
            CALIBRATION_BASE,
            "timing-calibration-v1",
            CALIBRATION_REPLACEMENTS,
            "rb_calibration.py",
            "calibration_only",
        )
    elif args.persistent:
        build_variant(
            "timing-calibration-v1",
            PERSISTENT_BASE,
            "persistent-reader-v1",
            ("rb_calibration.py", "rb_measure.py", "rb_native.py", "rb_stats.py"),
            "rb_persistent.py",
            "persistent_reader",
        )
    elif args.request_timing:
        build_variant(
            "persistent-reader-v1",
            REQUEST_TIMING_BASE,
            "request-timing-v1",
            ("rb_calibration.py", "rb_native.py"),
            "rb_request_timing.py",
            "request_attribution",
        )
    else:
        build()
