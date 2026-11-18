"""Export all frozen query roles and seal one reproducible no-provider experiment."""

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

import h5py
import numpy as np
from oracle_design import FILTERS, IMAGE, MAX_ATTEMPTS, MAX_CHECKPOINTS, SEED, require

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
RUNTIME = STUDY / "full-workload-oracle-v1"
KIT = RUNTIME / "kit-r2"


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def export():
    freeze = json.loads((STUDY / "freeze/split-freeze.json").read_text())
    manifest_path = ROOT / freeze["manifest_path"]
    require(sha(manifest_path) == freeze["manifest_sha256"], "split manifest changed")
    manifest = json.loads(manifest_path.read_text())
    for name, expected in freeze["role_file_hashes"].items():
        require(sha(STUDY / "splits" / name) == expected, "role file changed")
    groups = sorted(manifest["assignments"], key=lambda g: g["source_index"])
    require([g["source_index"] for g in groups] == list(range(1000)), "source inventory changed")
    source = ROOT / "harness/downloads/morevec/MoRe_small/queries/queries_flex_reviews_sim_0_0.hdf5"
    inventory = json.loads((STUDY.parent / "inventory/source-inventory.json").read_text())
    expected = next(
        s["sha256"] for s in inventory["sources"] if s["path"] == str(source.relative_to(ROOT))
    )
    require(sha(source) == expected, "source queries changed")
    with h5py.File(source, "r") as handle:
        vectors = np.asarray(handle["test"], dtype=np.float32)
    require(vectors.shape == (1000, 768), "source query dimensions changed")
    roles = {}
    with (KIT / "queries.jsonl").open("x") as out:
        for row, vector in zip(groups, vectors, strict=True):
            require(
                "reviews-small-sha256:" + hashlib.sha256(vector.astype("<f4").tobytes()).hexdigest()
                == row["group"],
                "vector group identity differs",
            )
            for t in FILTERS:
                suffix = "unfiltered" if t < 0 else "votes" + str(t)
                q = {
                    "schema_version": 1,
                    "id": f"reviews-clean-v{row['source_index']:04d}-{suffix}",
                    "vector": vector.astype(float).tolist(),
                    "k": 10,
                }
                if t >= 0:
                    q["filter"] = {"field": "totalvotes", "op": "gte", "value": t}
                roles[q["id"]] = row["role"]
                out.write(json.dumps(q, sort_keys=True, separators=(",", ":")) + "\n")
    write(KIT / "query-roles.json", roles)
    return freeze["manifest_sha256"], expected


def stage():
    require(not KIT.exists(), "preserve existing kit; use a versioned correction")
    require((RUNTIME / "oracle-module.so").is_file(), "compile and smoke-test module first")
    KIT.mkdir()
    for name in (
        "common.py",
        "serving.py",
        "sessions.py",
        "support.py",
        "startup.py",
        "functions.sql",
        "source-delta.json",
        "oracle-module.so",
    ):
        shutil.copyfile(RUNTIME / name, KIT / name)
    shutil.copyfile(
        STUDY / "kits/m1-runtime-qualification-v2/original-package.tar.gz",
        KIT / "original-package.tar.gz",
    )
    for name in (
        "oracle_design.py",
        "oracle_experiment.py",
        "oracle_run.py",
        "oracle_preflight.py",
        "analyse.py",
        "run-on-compute.sh",
        "startup-preflight.sh",
        "submit.sh",
        "PROTOCOL.md",
    ):
        shutil.copyfile(HERE / name, KIT / name)
    split_sha, source_sha = export()
    reference_source = STUDY / "kits/m1-runtime-qualification-v2/expected.jsonl"
    m1_binding = json.loads((STUDY / "kits/m1-runtime-qualification-v2/binding.json").read_text())
    require(
        sha(reference_source) == m1_binding["expected_sha256"], "qualified native reference changed"
    )
    with (KIT / "native-reference.jsonl").open("x") as out:
        for line in reference_source.read_text().splitlines():
            row = json.loads(line)
            out.write(
                json.dumps({"id": row["id"], "output": row["results"]["native640"]["output"]})
                + "\n"
            )
    old = json.loads((STUDY / "kits/m1-runtime-qualification-v2/binding.json").read_text())
    write(
        KIT / "plan.json",
        {
            "schema": "fannagent.full-workload-oracle.v1",
            "split_sha256": split_sha,
            "source_query_sha256": source_sha,
            "image_sha256": IMAGE,
            "seed": SEED,
            "groups": 1000,
            "cases": 7000,
            "test_groups": 275,
            "test_cases": 1925,
            "filters": FILTERS,
            "checkpoints": "every reached ordinal, 64-distance target recurrence",
            "max_checkpoints_per_query": MAX_CHECKPOINTS,
            "max_attempts": MAX_ATTEMPTS,
            "timed_requests": 224000,
            "timing_warmups": 2240,
            "allocations": 1,
            "physical_cpus": 4,
            "memory_gib": 48,
            "wall_hours": 6,
            "oracle_discovery_rule": "first actual stop preserving native recall AND result count",
            "oracle_choices_use_timings": False,
            "oracle_routing_is_free_in_primary": True,
            "oracle_routing_cost_separately_recorded": True,
            "exact_search": "offline reference only, closed before ANN",
            "primary": "equal six-filter mean; also equal seven-condition mean and per-condition",
            "provider_calls": 0,
            "automatic_retry": False,
            "authorization": (
                "User requested oracle measurement on held-out test AND complete benchmark "
                "in this chat"
            ),
            "holdout_exposure": (
                "diagnostic labels excluded from agent training; not confirmatory agent evidence"
            ),
        },
    )
    write(
        KIT / "binding.json",
        {
            "schema": "fannagent.full-workload-oracle.binding.v1",
            "graph": old["graph"],
            "split_sha256": split_sha,
            "files": {p.name: sha(p) for p in sorted(KIT.iterdir()) if p.is_file()},
        },
    )
    with tarfile.open(KIT / "engine-sources.tar.gz", "w:gz") as archive:
        for p in sorted((RUNTIME / "engine").rglob("*")):
            if p.is_file() and p.suffix not in (".o", ".so", ".bc"):
                archive.add(p, arcname="engine/" + str(p.relative_to(RUNTIME / "engine")))
    (KIT / "SHA256SUMS").write_text(
        "".join(
            sha(p) + "  " + p.name + "\n"
            for p in sorted(KIT.iterdir())
            if p.is_file() and p.name != "SHA256SUMS"
        )
    )
    path = RUNTIME / "full-workload-oracle-v1-r2.tar.gz"
    with tarfile.open(path, "x:gz") as archive:
        archive.add(KIT, arcname="full-workload-oracle-v1")
    path.with_suffix(path.suffix + ".sha256").write_text(sha(path) + "  " + path.name + "\n")
    write(
        RUNTIME / "preparation.json",
        {
            "status": "sealed_pending_original_graph_execution",
            "archive": str(path),
            "archive_sha256": sha(path),
            "binding_sha256": sha(KIT / "binding.json"),
            "groups": 1000,
            "cases": 7000,
            "heldout_groups": 275,
            "heldout_cases": 1925,
            "original_graph_measurements": False,
        },
    )
    print(
        json.dumps(
            {"archive": str(path), "sha256": sha(path), "cases": 7000, "heldout_cases": 1925}
        )
    )


if __name__ == "__main__":
    stage()
