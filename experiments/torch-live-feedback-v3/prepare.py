"""Seal v3 inputs and an isolated, development-only agent workspace before dispatch."""

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from limits import SCHEMA, digest, read, sha, write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
BASE = STUDY / "broad-oracle-v1/benchmark-kit-v3"


def rows(p):
    with p.open() as f:
        for line in f:
            yield json.loads(line)


def prepare(target):
    target.mkdir(parents=True)
    kit = target / "kit"
    kit.mkdir()
    # Verify the completed oracle's sealed input identities, then reuse its graph/runtime helpers.
    binding = read(BASE / "binding.json")
    for name, expected in binding["files"].items():
        if sha(BASE / name) != expected:
            raise ValueError("oracle source changed: " + name)
    helpers = kit / "helpers"
    helpers.mkdir()
    for p in BASE.glob("*.py"):
        shutil.copyfile(p, helpers / p.name)
    for p in HERE.iterdir():
        if p.suffix in (".py", ".sh", ".md") or p.name == "model-profile.json":
            shutil.copyfile(p, kit / p.name)
    for name in [
        "queries.jsonl",
        "query-roles.json",
        "source-cases.jsonl",
        "source-exact-reference.jsonl",
        "source-eligibility.json",
        "full_workload-choices.jsonl",
        "heldout_test-choices.jsonl",
        "functions.sql",
    ]:
        shutil.copyfile(BASE / name, kit / name)
    shutil.copyfile(
        STUDY / "kits/m5-policy-qualification-v1/original-package.tar.gz",
        kit / "original-package.tar.gz",
    )
    with tarfile.open(BASE / "engine-sources.tar.gz") as archive:
        archive.extractall(kit, filter="data")
    shutil.copytree(
        ROOT / "agent/src/fannagent",
        kit / "src/fannagent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        HERE.parent / "filtered-ann-protocol-v3/fannproto3",
        kit / "protocol/fannproto3",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for label, cohort in [("full", "full_workload"), ("test", "heldout_test")]:
        shutil.copyfile(
            HERE.parent / f"broad-oracle-v1/results/oracle_feasible-broad-{cohort}.json",
            kit / f"oracle-{label}.json",
        )
    write(
        kit / "source-binding.json",
        {
            "graph": binding["graph"],
            "original_manifest_sha256": (
                "b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc"
            ),
            "prior_oracle_binding_sha256": sha(BASE / "binding.json"),
        },
    )
    filters = ("unfiltered", "votes743", "votes527", "votes310", "votes192", "votes108", "votes32")
    diagnostic = {
        "schema": "fannagent.broad-stop.v3",
        "name": "causal-continue-diagnostic",
        "rationale": "Unpaid native startup diagnostic, never an agent seed.",
        "fuel": 2000000,
        "state_slots": 1,
        "programs": {
            f: {
                "checkpoints": [1, 2, 16, 32, 64],
                "root": [
                    "lt",
                    ["add", ["feature", "frontier_distance"], ["mul", 0, ["state", 0]]],
                    -1,
                ],
                "updates": {"0": ["add", ["state", 0], 1]},
            }
            for f in filters
        },
    }
    write(kit / "diagnostic-policies.json", [diagnostic])
    write(
        kit / "config.json",
        {
            "schema": SCHEMA,
            "wall_seconds": 21600,
            "admission_seconds": 18900,
            "work_seconds": 20400,
            "idle_seconds": 900,
            "attempt_limit": 300000,
            "cpus": 4,
            "memory_gib": 48,
            "image": "/home/dar579/torch-reviews-first/images/runtime.sif",
            "image_sha256": "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a",
            "bundle": "/home/dar579/torch-reviews-first",
            "prepared": (
                "/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286"
            ),
            "qualification_payload_sha256": digest(
                {"schema": SCHEMA, "policies": [diagnostic], "mode": "qualification"}
            ),
            "automatic_retry": False,
            "automatic_requeue": False,
        },
    )

    workspace = target / "workspace"
    (workspace / "evidence").mkdir(parents=True)
    (workspace / "api").mkdir()
    for name, source in [
        ("broad_contract.py", ROOT / "agent/src/fannagent/api/broad_policy.py"),
        ("broad_support.py", HERE.parent / "broad-oracle-v1/broad_support.py"),
        ("README.md", HERE.parent / "filtered-ann-protocol-v3/README.md"),
    ]:
        shutil.copyfile(source, workspace / "api" / name)
    selected = {r["id"]: r for r in rows(BASE / "source-cases.jsonl") if r["role"] == "development"}
    group_ids = sorted({qid.rsplit("-", 1)[0] for qid in selected})
    aliases = {g: f"development-{i:04d}" for i, g in enumerate(group_ids)}
    labels = {qid: {} for qid in selected}
    prefix = STUDY / "full-workload-oracle-v1/return-23567950/results/prefixes.jsonl"
    for r in rows(prefix):
        if r["id"] in selected:
            labels[r["id"]][str(r["checkpoint"])] = {
                "recall": r["recall"],
                "result_count": len(r["output"]),
                "safe": r["recall"] + 1e-12 >= selected[r["id"]]["native_recall"],
            }
    for r in rows(BASE / "legacy-cases.jsonl"):
        if r["id"] in selected:
            for cp, a in r["actions"].items():
                labels[r["id"]][cp] = {
                    "recall": a["recall"],
                    "result_count": len(a["output"]),
                    "safe": a["safe"],
                }
    with (workspace / "evidence/development.jsonl").open("w") as out:
        for qid, r in selected.items():
            # Query-local TID equality supports turnover replay without real neighbor IDs.
            tids = {}
            frames = []
            for frame in r["frames"]:
                frame = dict(frame)
                for tid in frame["top_tids"]:
                    if str(tid) not in tids:
                        tids[str(tid)] = len(tids) + 1
                frame["top_tids"] = [tids[str(t)] for t in frame["top_tids"]]
                frames.append(frame)
            anon = aliases[qid.rsplit("-", 1)[0]]
            out.write(
                json.dumps(
                    {
                        "id": anon
                        + "-"
                        + ("unfiltered" if r["filter"] < 0 else "votes" + str(r["filter"])),
                        "group": anon,
                        "filter": r["filter"],
                        "native_recall": r["native_recall"],
                        "native_count": len(r["native"]),
                        "native_layer0_work": r["native_layer0_work"],
                        "frames": frames,
                        "labels": labels[qid],
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )
    sys.path[:0] = [str(ROOT / "agent/src")]
    from fannagent.api.broad_policy import FEATURES

    write(
        workspace / "evidence/summary.json",
        {
            "cases": len(selected),
            "vector_groups": len(group_ids),
            "conditions": filters,
            "features": FEATURES,
            "known_prefix_labels": sum(map(len, labels.values())),
            "unknown_prefixes": "unlabeled, not assumed safe",
            "source_ids_exposed": False,
            "protected_outcomes_exposed": False,
            "oracle_policies_exposed": False,
        },
    )
    image = subprocess.check_output(
        [
            "docker",
            "image",
            "inspect",
            "fannagent/torch-reviews-first:20261013",
            "--format",
            "{{.Id}}",
        ],
        text=True,
    ).strip()
    write(
        target / "workspace-binding.json",
        {
            "image": image,
            "workspace": str(workspace.resolve()),
            "files": {
                str(p.relative_to(workspace)): sha(p) for p in workspace.rglob("*") if p.is_file()
            },
            "development_rows": len(selected),
            "protected_rows": 0,
            "oracle_artifacts": 0,
            "source_capture_sha256": sha(BASE / "source-cases.jsonl"),
            "source_prefixes_sha256": sha(prefix),
        },
    )
    paths = sorted(p for p in kit.rglob("*") if p.is_file())
    (kit / "SHA256SUMS").write_text(
        "".join(sha(p) + "  " + str(p.relative_to(kit)) + "\n" for p in paths)
    )
    archive = target / "kit.tar.gz"
    with tarfile.open(archive, "x:gz") as f:
        f.add(kit, arcname="kit")
    archive.with_suffix(".gz.sha256").write_text(sha(archive) + "  " + archive.name + "\n")
    write(
        target / "preparation.json",
        {
            "status": "sealed_not_launched",
            "kit_sha256": sha(kit / "SHA256SUMS"),
            "archive_sha256": sha(archive),
            "workspace_binding_sha256": sha(target / "workspace-binding.json"),
            "baseline_commit": "3939aec",
            "controller_source_sha256": {p.name: sha(p) for p in HERE.glob("*.py")},
            "provider_calls": 0,
            "new_allocations": 0,
        },
    )
    return target


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    print(prepare(p.parse_args().output))
