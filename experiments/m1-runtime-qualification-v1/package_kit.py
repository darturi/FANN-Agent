"""Stage/seal the single bounded M1 kit after local module, runtime and verifier checks."""

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

from m1_design import ARMS, GROUPS, SEED, ledger

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
RUNTIME = STUDY / "runtime-m1-v1"
OLD = STUDY / "kits/reader-attribution-v1-startup-fix"
KIT = STUDY / "kits/m1-runtime-qualification-v2"


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sums():
    (KIT / "SHA256SUMS").write_text(
        "".join(
            sha(p) + "  " + p.name + "\n"
            for p in sorted(KIT.iterdir())
            if p.is_file() and p.name != "SHA256SUMS"
        )
    )


def stage():
    require(not KIT.exists(), "use a fresh kit version")
    require(
        sha(OLD.with_suffix(".tar.gz"))
        == "53935023770b6ed68145d490579b5a68c57efbd7b3f2014a8b22ad487be0800f",
        "inherited sealed kit changed",
    )
    for line in (OLD / "SHA256SUMS").read_text().splitlines():
        h, n = line.split("  ", 1)
        require(sha(OLD / n) == h, "inherited input changed")
    gate = json.loads((STUDY / "reports/protocol-v2-gates-after-M0.json").read_text())["M0"]
    require(
        gate["status"] == "verified_attribution_resolved"
        and sha(STUDY / "reports/reader-attribution-assessment-23303080.json")
        == gate["receipt_sha256"],
        "M0 verification gate changed",
    )
    KIT.mkdir()
    for name in (
        "original-package.tar.gz",
        "queries.jsonl",
        "prior-references.jsonl",
        "expected.jsonl",
        "eligible-policies.json",
        "compiled-policies.json",
        "inherited-package-review.json",
        "base-config.json",
        "base-study-protocol.md",
    ):
        shutil.copyfile(OLD / name, KIT / name)
    for name in (
        "common.py",
        "serving.py",
        "support.py",
        "startup.py",
        "sessions.py",
        "functions.sql",
        "work-functions.sql",
        "timing-module.so",
        "work-module.so",
        "compiled-programs.json",
        "observer-delta.json",
    ):
        shutil.copyfile(RUNTIME / name, KIT / name)
    for p in HERE.iterdir():
        if p.name.startswith("m1_") and p.suffix == ".py" or p.suffix == ".sh":
            shutil.copyfile(p, KIT / p.name)
    shutil.copyfile(HERE / "PROTOCOL.md", KIT / "m1-protocol.md")
    (STUDY / "protocol/m1-runtime-qualification-v2.md").write_text(
        (HERE / "PROTOCOL.md").read_text()
    )
    queries = [json.loads(line) for line in (KIT / "queries.jsonl").read_text().splitlines()]
    m0 = STUDY / "returns/job-23303080/results/work"
    raw = json.loads((m0 / "receipt.json").read_text())["raw_sha256"]["work.jsonl"]
    require(sha(m0 / "work.jsonl") == raw, "M0 work reference digest differs")
    with (KIT / "native-work-reference.jsonl").open("w") as out:
        for line in (m0 / "work.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["family"] == "native640":
                out.write(
                    json.dumps(
                        {
                            "id": r["id"],
                            "counts": {
                                k: v
                                for k, v in r["counts"].items()
                                if k not in ("pid", "start_cpu", "end_cpu")
                            },
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
    fold = json.loads((STUDY / "protocol/development-folds.json").read_text())["folds"]
    fold_map = {str(i): int(f) for f, values in fold.items() for i in values}
    old = json.loads((OLD / "binding.json").read_text())
    require(
        set(map(int, fold_map)) == set(old["development_source_indices"]), "fold membership changed"
    )
    write(KIT / "fold-map.json", fold_map)
    plan = {
        "schema": "fannagent.M1-plan.v1",
        "date": "2026-11-16",
        "pre_M1_commit": "f96e02d",
        "M0_job": "23303080",
        "attempts": ledger(),
        "phase_attempt_caps": {"timing": 920000, "work": 90000},
        "global_attempt_cap": 1000000,
        "timing_groups": GROUPS,
        "arms": ARMS,
        "schedule_seed": SEED,
        "reader_pids_per_group": 4,
        "roles_per_pid": "each group role twice",
        "cpus": 4,
        "memory_gib": 48,
        "wall_hours": 8,
        "phase_watchdog_seconds": {"timing": 22500, "work": 4500},
        "queries": len(queries),
        "source_groups": 450,
        "conditions": [-1, 743, 527, 310, 192, 108, 32],
        "native_ef_search": 640,
        "new_v2_bindings": 21,
        "quality_and_work_families": 26,
        "timed_families": 23,
        "reached_prefixes": 9436,
        "missing_partial_prefixes_to_measure": 1496,
        "offline_exact_queries": 6300,
        "exact_serving_calls": 0,
        "provider_calls": 0,
        "validation_test_queries": 0,
        "negative_probe_losses_retained": True,
        "cost_library_automatically_qualifies_additive_estimator": False,
        "final_policy_selection": False,
        "automatic_retry": False,
    }
    # Pool counts are computed, not hand-maintained.
    plan["timed_families"] = len({name for group in GROUPS for name in group})
    write(KIT / "m1-plan.json", plan)
    with tarfile.open(KIT / "engine-sources.tar.gz", "w:gz") as tf:
        for folder in ("engine", "observer-engine"):
            for p in sorted((RUNTIME / folder).rglob("*")):
                if p.is_file() and p.suffix not in (".o", ".so", ".bc"):
                    tf.add(p, arcname=folder + "/" + str(p.relative_to(RUNTIME / folder)))
    programs = json.loads((KIT / "compiled-programs.json").read_text())
    binding = {
        **{
            key: old[key]
            for key in (
                "split_manifest_sha256",
                "queries_sha256",
                "development_source_indices",
                "graph",
                "serving_source_sha256",
                "startup_source_sha256",
                "prior_references_sha256",
                "expected_sha256",
                "compiled_policies_sha256",
            )
        },
        "source_M0_binding_sha256": sha(OLD / "binding.json"),
        "schema": "fannagent.M1-binding.v1",
        "runtime_profile": programs["profile"]["fingerprint"],
        "programs_sha256": sha(KIT / "compiled-programs.json"),
        "timing_module_sha256": sha(KIT / "timing-module.so"),
        "work_module_sha256": sha(KIT / "work-module.so"),
        "plan_sha256": sha(KIT / "m1-plan.json"),
        "protocol_sha256": sha(KIT / "m1-protocol.md"),
        "native_work_reference_sha256": sha(KIT / "native-work-reference.jsonl"),
        "fold_map_sha256": sha(KIT / "fold-map.json"),
        "engine_source_archive_sha256": sha(KIT / "engine-sources.tar.gz"),
        "M0_receipt_sha256": gate["receipt_sha256"],
    }
    write(KIT / "binding.json", binding)
    sums()
    print(
        json.dumps(
            {
                "kit": str(KIT),
                "attempts": ledger(),
                "status": "staged_not_sealed_local_checks_pending",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    stage()
