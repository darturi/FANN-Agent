"""Stage development-only M5 inputs, original M1 bridges, sources and prospective plan."""

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

from m5_design import ARMS, EXPECTED_STOPS, GROUPS, SEED, ledger

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
RUNTIME = STUDY / "runtime-m5-v1"
OLD = STUDY / "kits/m1-runtime-qualification-v2"
KIT = STUDY / "kits/m5-policy-qualification-v1"


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def sums():
    (KIT / "SHA256SUMS").write_text(
        "".join(
            sha(p) + "  " + p.name + "\n"
            for p in sorted(KIT.iterdir())
            if p.is_file() and p.name != "SHA256SUMS"
        )
    )


def sync():
    for p in HERE.iterdir():
        if (p.name.startswith("m5_") and p.suffix == ".py") or p.suffix == ".sh":
            shutil.copyfile(p, KIT / p.name)
            if p.suffix == ".py":
                shutil.copyfile(p, RUNTIME / p.name)
    for name in ("PROTOCOL.md", "README.md", "COMMANDS.txt"):
        if (HERE / name).exists():
            shutil.copyfile(
                HERE / name, KIT / ("m5-protocol.md" if name == "PROTOCOL.md" else name)
            )
    if (KIT / "binding.json").exists():
        b = json.loads((KIT / "binding.json").read_text())
        b["protocol_sha256"] = sha(KIT / "m5-protocol.md")
        write(KIT / "binding.json", b)
    sums()


def stage():
    assert not KIT.exists(), "use a fresh deployment; preserve prior kit"
    for line in (OLD / "SHA256SUMS").read_text().splitlines():
        h, name = line.split("  ", 1)
        assert Path(name).name == name and sha(OLD / name) == h, name
    assert (
        sha(STUDY / "reports/m1-assessment-23376796.json")
        == "40cf8fcf245a8bc2a337a88aa8b2eadfcf26f1d8a3887ce2df05c097e845bee5"
    )
    nominee = STUDY / "m4-dollar-budget-v1/assessment-v1/nominees.json"
    receipt = STUDY / "m4-dollar-budget-v1/assessment-v1/receipt.json"
    assert sha(nominee) == "48bf2eca1a66950a68701cd89cd646daa499f9243223a6b9301ea7f2d9befef1"
    assert sha(receipt) == "87328f79ec8cd0354bc03111951763bda48863dde5bfae246f034ef3a6b36948"
    KIT.mkdir()
    for name in (
        "original-package.tar.gz",
        "queries.jsonl",
        "prior-references.jsonl",
        "native-work-reference.jsonl",
        "inherited-package-review.json",
    ):
        shutil.copyfile(OLD / name, KIT / name)
    shutil.copyfile(nominee, KIT / "nominees.json")
    shutil.copyfile(receipt, KIT / "m4-assessment.json")
    quality = STUDY / "returns/job-23376796/results/timing/quality.jsonl"
    qr = json.loads((quality.parent / "receipt.json").read_text())
    assert sha(quality) == qr["raw_sha256"]["quality.jsonl"]
    with (KIT / "expected.jsonl").open("w") as out:
        for line in quality.read_text().splitlines():
            r = json.loads(line)
            out.write(
                json.dumps(
                    {
                        "id": r["id"],
                        "checkpoints": r["checkpoints"],
                        "prefixes": r["prefixes"],
                        "results": {"native640": r["results"]["native640"]},
                    },
                    sort_keys=True,
                )
                + "\n"
            )
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
        "nominee-source-delta.json",
    ):
        shutil.copyfile(RUNTIME / name, KIT / name)
    with tarfile.open(KIT / "engine-sources.tar.gz", "w:gz") as tf:
        for folder in ("engine", "observer-engine"):
            for p in sorted((RUNTIME / folder).rglob("*")):
                if p.is_file() and p.suffix not in (".o", ".bc", ".so"):
                    tf.add(p, arcname=folder + "/" + str(p.relative_to(RUNTIME / folder)))
    plan = {
        "schema": "fannagent.M5-plan.v1",
        "date": "2026-11-16",
        "pre_M5_commit": "bdbcab4",
        "nominees": ["candidate-7", "candidate-8"],
        "candidate_thresholds_modified": False,
        "attempts": ledger(),
        "phase_attempt_caps": {"timing": 200000, "work": 25000},
        "global_attempt_cap": 225000,
        "timing_groups": GROUPS,
        "arms": ARMS,
        "schedule_seed": SEED,
        "reader_pids_per_group": 4,
        "roles_per_pid": "each role twice",
        "cpus": 4,
        "memory_gib": 48,
        "wall_hours": 6,
        "phase_watchdog_seconds": {"timing": 15300, "work": 4500},
        "queries": 3150,
        "source_groups": 450,
        "conditions": [-1, 743, 527, 310, 192, 108, 32],
        "native_ef_search": 640,
        "iterative_scan": "off",
        "new_v2_bindings": 5,
        "quality_work_timed_families": 6,
        "reached_prefixes": 9436,
        "partial_prefixes": 1496,
        "bound_nominee_stop_counts": EXPECTED_STOPS,
        "quality_gate": "zero per-case losses vs raw native640",
        "offline_exact_queries": 6300,
        "exact_serving_calls": 0,
        "provider_calls": 0,
        "validation_test_queries": 0,
        "allocation_repetitions": 1,
        "cycles": 2,
        "observations_per_query_family": 8,
        "group_bootstrap_draws": 20000,
        "bootstrap_seed": 20261116,
        "primary": "equal mean complete-request latency over six scalar filters",
        "empty_native_diagnostic": {"ratio_band": [0.98, 1.02], "interval_probability": 0.90},
        "final_policy_selection": False,
        "automatic_retry": False,
    }
    write(KIT / "m5-plan.json", plan)
    old = json.loads((OLD / "binding.json").read_text())
    b = {
        k: old[k]
        for k in (
            "split_manifest_sha256",
            "queries_sha256",
            "development_source_indices",
            "graph",
            "serving_source_sha256",
            "startup_source_sha256",
            "prior_references_sha256",
        )
    }
    b.update(
        {
            "schema": "fannagent.M5-binding.v1",
            "source_M1_binding_sha256": sha(OLD / "binding.json"),
            "M1_receipt_sha256": sha(STUDY / "reports/m1-assessment-23376796.json"),
            "M1_quality_sha256": sha(quality),
            "nominees_sha256": sha(nominee),
            "M4_receipt_sha256": sha(receipt),
            "evidence_identity": json.loads(nominee.read_text())["evidence_identity"],
            "runtime_profile": json.loads((KIT / "compiled-programs.json").read_text())["profile"][
                "fingerprint"
            ],
        }
    )
    for file, key in (
        ("compiled-programs.json", "programs_sha256"),
        ("expected.jsonl", "expected_sha256"),
        ("native-work-reference.jsonl", "native_work_reference_sha256"),
        ("m5-plan.json", "plan_sha256"),
        ("timing-module.so", "timing_module_sha256"),
        ("work-module.so", "work_module_sha256"),
        ("engine-sources.tar.gz", "engine_source_archive_sha256"),
    ):
        b[key] = sha(KIT / file)
    write(KIT / "binding.json", b)
    sync()
    print(json.dumps({"kit": str(KIT), "attempts": ledger()}))


if __name__ == "__main__":
    stage()
