"""Verify saved oracle decisions and build the held development-only Torch preflight kit."""

import json
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from dataclasses import replace
from pathlib import Path

import rb_oracle
from rb_evidence import ACQUIRE, PILOT_PROOFS, PILOT_REFS, expected_outcome, outcome, stop_proofs
from rb_native import MODULE, load_stage
from rb_package import HERE, OUTPUT, PACKAGE_NAME, REQUEST_TIMING_BASE, copy_bytes
from rb_plan import PILOT_BLOCK, ROOT, digest, file_sha, pinned, pinned_lines, require
from rb_seal import json_bytes, make_archive, seal_directory, verify_directory, write_once
from rb_stats import exact_truth, quality, result_score

NAME = "oracle-persistent-v1"
PARENT = OUTPUT / "persistent-reader-v1" / PACKAGE_NAME
HOST = OUTPUT / "request-timing-v1"
HOST_PINS = {
    "rb_host.py": "1bf344bb3cc85ad14ddcc6ddce9c60387db1025514a37370121464882527a020",
    "rb_site.py": "8c934d6c22d85d2de2c5caf214830c10f8c63357f1d31262b83fc1ad7c039099",
    "rb_seal.py": "3d0cae1765c2f8fc23e23bfdc1ec939a0c750ae57c455782e45ba38f2bf45557",
}
PREFLIGHT_PIN = "f3a6b5de656e9e799148ac2448abb4a8e18aefbfdf31a2f204e68743ec0b1936"
FEATURE_MANIFEST = "3a50e8296bdba9dbb8c018ef742af2b2e868ae80f85172c876511a015fd5838c"
FEATURE_POSTRUN = "04f1ca692bfae165761fa09be739cdec45a6b0dd49d26b8598b2df8de80ff620"
REPLACEMENTS = {"rb_native.py", "rb_measure.py", "rb_calibration.py", "rb_persistent.py"}


def engine_pins():
    """Bind the static checkpoint proof to the same binary used for the saved traces."""
    receipt = json.loads(
        pinned(
            ROOT / "agent/docs/verification/feature-data-ablation-v1-postrun.json", FEATURE_POSTRUN
        )
    )
    require(
        receipt["package_manifest_sha256"] == FEATURE_MANIFEST
        and receipt["module_sha256"] == MODULE,
        "Saved engine binding differs",
    )
    package = ROOT / ACQUIRE.parent / "package"
    files = json.loads(pinned(package / "manifest.json", FEATURE_MANIFEST))["files"]
    paths = ("engine/src/fannbench.c", "engine/src/hnswutils.c", "engine/src/hnswscan.c")
    sources = [pinned(package / path, files[path]).decode() for path in paths]
    c, utils, scan = sources
    require(
        "#define FANNBENCH_CHECKPOINT_INTERVAL 64" in c
        and "(executionState.distanceEvaluations / FANNBENCH_CHECKPOINT_INTERVAL + 1)" in c
        and "executionState.distanceEvaluations >= executionState.fixedBudget" in c
        and "return executionState.fixedBudgetStopped || executionState.policyStopped;" in c
        and "FannbenchHnswObserveDistances(unvisitedLength," in utils
        and "so->w = GetScanItems(scan, value);" in scan,
        "Native stopping boundary differs",
    )
    return dict(zip(paths, (files[path] for path in paths), strict=True))


def build_replay(stage):
    plan, frozen, base = stage.plan, stage.frozen, stage.evidence
    proofs = stop_proofs(ROOT)
    oracle_proofs = {}
    for row in pinned_lines(ROOT / PILOT_BLOCK / "proofs.jsonl", PILOT_PROOFS):
        if row["arm"] == "sparse-oracle":
            qid = row["query_id"]
            require(
                qid not in oracle_proofs and row["native_bypass"] is False,
                "Duplicate oracle proof or unexpected bypass",
            )
            oracle_proofs[qid] = row
    require(oracle_proofs.keys() == plan.cases.keys(), "Incomplete oracle proof cohort")

    trees = {}
    outcomes = {}
    stops = Counter()
    total_work = 0
    for row in pinned_lines(ROOT / PILOT_BLOCK / "references.jsonl", PILOT_REFS):
        qid = row["query_id"]
        case, ref = plan.cases[qid], base.references[qid]
        states = row["states"]["light19"]
        require(
            qid not in outcomes
            and row["group"] == case.group
            and ref["continues"]["light19"] == {"length": len(states), "digest": digest(states)}
            and digest(outcome(row, "native")) == digest(ref["native"]),
            "Oracle reference differs from retained native evidence",
        )
        proof = oracle_proofs[qid]
        cp = proof["checkpoint"]
        if cp not in trees:
            root = (
                "continue"
                if cp is None
                else {
                    "if": {"op": "eq", "args": [{"feature": "checkpoint_index"}, {"int": cp}]},
                    "then": "stop",
                    "else": "continue",
                }
            )
            trees[cp], _ = frozen.policy.validate(
                frozen.policy.compose("sparse-oracle", root, "light19"), plan.config
            )
        expected = expected_outcome(frozen, trees[cp], case, ref, states, proofs)
        stop_info = rb_oracle.checkpoint_budget(states, cp)
        require(
            expected["stop"] is (cp is not None)
            and expected["checkpoint_count"] == stop_info["checkpoint_count"]
            and expected["prefix"] == proof["observed_prefix_sha256"]
            and digest(expected["output"]) == digest(outcome(proof, "policy")),
            "Original interpreter, first stop, or saved oracle output differs",
        )
        truth = exact_truth(frozen, ref, base.eligible[case.stratum])
        native_score, native_valid = result_score(frozen, truth, ref["native"])
        oracle_score, oracle_valid = result_score(frozen, truth, expected["output"])
        require(
            native_valid and oracle_valid and oracle_score == native_score,
            "Oracle lost recall or changed validity",
        )
        total_work += stop_info["last_checkpoint_distances"]
        stops[str(cp)] += 1
        outcomes[qid] = {**expected, **stop_info}

    require(
        outcomes.keys() == oracle_proofs.keys()
        and sum(stops.values()) == 600
        and stops["None"] == 16
        and total_work == 1317671,
        "Saved oracle work or coverage changed",
    )
    evidence = replace(base, outcomes={**base.outcomes, "oracle": outcomes})
    score = quality(plan, frozen, evidence, "oracle")
    require(score["passes"] and score["stops"] == 584, "Saved oracle quality differs")
    return {
        "schema": rb_oracle.SCHEMA,
        "identity": digest(outcomes),
        "outcomes": outcomes,
        "recall": score,
        "stops_by_checkpoint": {("continue" if cp == "None" else cp): n for cp, n in stops.items()},
        "observed_layer0_distances": total_work,
        "inputs_sha256": {
            "pilot_proofs": PILOT_PROOFS,
            "pilot_references": PILOT_REFS,
            "feature_package_manifest": FEATURE_MANIFEST,
            "feature_postrun_receipt": FEATURE_POSTRUN,
            "vector.so": MODULE,
            **engine_pins(),
        },
        "scope": "Saved first-stop/output proof and checkpoint budget translation. "
        "Native fixed-budget parity is a runtime gate.",
    }


def substitute_assignment(body, name, value):
    updated, count = re.subn(rf"(?m)^{name} = .+$", f"{name} = {value}", body)
    require(count == 1, f"Host constant {name} differs")
    return updated


def build_host(output, archive, manifest, identity):
    body = pinned(HOST / "rb_host.py", HOST_PINS["rb_host.py"]).decode()
    for name, value in {
        "RESERVATION": f'NAME + "-{NAME}-reservation"',
        "MANIFEST": json.dumps(manifest),
        "ARCHIVE": json.dumps(file_sha(archive)),
        "CANDIDATE": json.dumps(identity),
        "JOB_NAME": '"fann-reviews-oracle-v1"',
        "COMMENT": '"rboracle1-" + MANIFEST[:24]',
    }.items():
        body = substitute_assignment(body, name, value)
    copy_bytes(output / "rb_host.py", body.encode())
    for name in ("rb_site.py", "rb_seal.py"):
        copy_bytes(output / name, pinned(HOST / name, HOST_PINS[name]))
    preflight = pinned(HOST / "TORCH-PREFLIGHT.sh", PREFLIGHT_PIN).decode()
    previous = (
        "63c3e09ff355f256a08fee36bc1866010782325e16064e43409e609d7e7f801c"
        "  $results/$name-persistent-reader-v1-reservation/reservation.json"
    )
    latest = (
        "e8b1c4c89f7af82c497438d17c74be32ca6982363b75f5ed4994377c5c7627bf"
        "  $results/$name-request-timing-v1-reservation/reservation.json"
    )
    require(preflight.count(previous) == 1, "Previous reservation pins differ")
    preflight = preflight.replace("request-timing-v1", NAME).replace(
        previous, previous + "\n" + latest
    )
    copy_bytes(output / "TORCH-PREFLIGHT.sh", preflight.encode())
    upload = output / f"torch-upload-{NAME}.tar"
    with tarfile.open(upload, "x") as tar:
        for name in (*HOST_PINS, "TORCH-PREFLIGHT.sh", archive.name):
            tar.add(output / name, arcname=name, recursive=False)
    # Exercise the exact staged host controller without site or scheduler calls.
    with tempfile.TemporaryDirectory() as scratch:
        stage = Path(scratch)
        with tarfile.open(upload) as tar:
            for name in (*HOST_PINS, archive.name):
                copy_bytes(stage / name, tar.extractfile(name).read())
        raw = subprocess.check_output(
            [sys.executable, "-EsB", str(stage / "rb_host.py"), "stage", str(stage / archive.name)],
            text=True,
            timeout=60,
        )
        receipt = json.loads(raw)
        require(
            receipt["status"] == "staged_held" and receipt["package_manifest_sha256"] == manifest,
            "Held host stage differs",
        )
    return upload, receipt["host_kit_sha256"]


def assemble(output, replay):
    output.mkdir(mode=0o700)
    package = output / PACKAGE_NAME
    package.mkdir(mode=0o700)
    for name, record in verify_directory(PARENT, REQUEST_TIMING_BASE).items():
        data = (
            (HERE / name).read_bytes()
            if name in REPLACEMENTS
            else pinned(PARENT / name, record["sha256"])
        )
        copy_bytes(package / name, data)
    copy_bytes(package / "rb_oracle.py", (HERE / "rb_oracle.py").read_bytes())
    copy_bytes(package / "oracle-replay.json", json_bytes(replay))
    manifest = seal_directory(package)
    raw = subprocess.check_output(
        [sys.executable, "-EsB", str(package / "rb_native.py"), "verify", str(package), manifest],
        text=True,
        timeout=90,
    )
    review = json.loads(raw)
    require(
        review
        == {
            "status": "verified_held",
            "candidate": replay["identity"],
            "sessions": 60,
            "cases": 600,
            "oracle_diagnostic": True,
            "dispatch_released": False,
        },
        "Sealed guest review differs",
    )
    archive = output / f"{PACKAGE_NAME}.tar.gz"
    archive_sha = make_archive(package, archive, manifest)
    upload, kit = build_host(output, archive, manifest, replay["identity"])
    result = {
        **review,
        "previous_package_manifest_sha256": REQUEST_TIMING_BASE,
        "package_manifest_sha256": manifest,
        "archive_sha256": archive_sha,
        "host_kit_sha256": kit,
        "upload_archive": upload.name,
        "upload_sha256": file_sha(upload),
        "saved_replay": {k: v for k, v in replay.items() if k != "outcomes"},
        "limits": {
            "allocation": 1,
            "no_retry": True,
            "physical_cores": 4,
            "memory_gib": 32,
            "wall_minutes": 120,
            "timed_searches": 10800,
            "exact_searches": 0,
            "timed_reader_lifetimes": 180,
            "reference_readers": 1,
            "seed_installs": 60,
            "oracle_installs": 0,
            "provider_calls": 0,
            "confirmation_queries": 0,
        },
        "primary_endpoint": "Wall time per request on batches 2 through 6 of an open reader",
        "gates": {
            "paired_AA": "Every family within original ±0.10 ms/request and ±log(1.02) intervals",
            "recall": "Original tie-aware recall, complete top-10, 95% native recall per filter "
            "and lower CI >= -0.25 pp overall and per filter",
            "oracle_headroom": "Both upper 95% steady log-ratio bounds below log(0.90) "
            "versus native and seed, plus savings in every epoch",
        },
        "next_gate": "Zero-allocation Torch preflight. Fresh approval required for dispatch.",
        "offline_accounting": {
            "allocations": 0,
            "searches": 0,
            "fits": 0,
            "confirmation_queries": 0,
            "provider_calls": 0,
        },
    }
    write_once(output / "PACKAGE-REVIEW.json", json_bytes(result))
    return result


def build():
    target = OUTPUT / NAME
    require(
        not target.exists() and not target.is_symlink(), "Refusing to overwrite an oracle study"
    )
    stage = load_stage(PARENT, REQUEST_TIMING_BASE)
    replay = build_replay(stage)
    with tempfile.TemporaryDirectory(dir=OUTPUT, prefix=".oracle-build-") as work:
        output = Path(work) / NAME
        result = assemble(output, replay)
        require(
            not target.exists() and not target.is_symlink(), "Oracle study appeared during build"
        )
        output.rename(target)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    build()
