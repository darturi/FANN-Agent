"""Bind successful local readiness and seal one prospectively bounded M1 deployment."""

import json
import shutil
import subprocess
import sys
import tarfile

from m1_design import ledger
from package_kit import HERE, KIT, ROOT, RUNTIME, STUDY, sha, sums, write


def smoke(path):
    found = [
        json.loads(line.removeprefix("SMOKE_RECEIPT "))
        for line in path.read_text().splitlines()
        if line.startswith("SMOKE_RECEIPT ")
    ]
    assert len(found) == 1 and found[0]["status"] == "passed"
    r = found[0]
    assert r["conditions"] == [-1, 743, 527, 310, 192, 108, 32] and r["programs"] == 21
    assert (
        r["exact_serving_calls"] == r["provider_calls"] == 0
        and r["validation_test_outcomes_opened"] is False
    )
    return r


def main():
    archive = KIT.with_suffix(".tar.gz")
    freeze = STUDY / "freeze/m1-runtime-qualification-v2.json"
    assert not archive.exists() and not freeze.exists(), "preserve sealed deployment"
    for p in HERE.iterdir():
        if p.name.startswith("m1_") and p.suffix == ".py" or p.suffix == ".sh":
            shutil.copyfile(p, KIT / p.name)
    shutil.copyfile(HERE / "PROTOCOL.md", KIT / "m1-protocol.md")
    shutil.copyfile(HERE / "README.md", KIT / "README.md")
    shutil.copyfile(HERE / "COMMANDS.txt", KIT / "COMMANDS.txt")
    (STUDY / "protocol/m1-runtime-qualification-v2.md").write_text(
        (HERE / "PROTOCOL.md").read_text()
    )
    checks = RUNTIME / "checks"
    unit = subprocess.run(
        [sys.executable, "-B", str(HERE / "test_m1.py")], capture_output=True, text=True
    )
    (checks / "unit-tests.log").write_text(unit.stdout + unit.stderr)
    assert unit.returncode == 0
    smokes = {
        "timing": smoke(checks / "smoke-timing-2.log"),
        "work": smoke(checks / "smoke-work.log"),
        "zero": smoke(checks / "smoke-zero.log"),
    }
    assert (
        smokes["timing"]["searches"]["timed_ann"] == 6944
        and smokes["work"]["searches"]["work_ann"] == 728
        and smokes["zero"]["zero_output_stops_verified"]
    )
    verifier = json.loads((checks / "local-verifier-check.json").read_text())
    assert (
        verifier["status"] == "passed"
        and verifier["production_scope_rejects_fixture"]
        and len(verifier["bad_CPU_order_missing_prefix_work_sample_and_module_rejected"]) == 5
    )
    cpu_analysis = json.loads((checks / "cpu-analysis-regression.json").read_text())
    assert cpu_analysis["status"] == "passed" and cpu_analysis["comparisons"] == 248
    loaders = {
        phase: json.loads((checks / ("preflight-" + phase + "-loader.log")).read_text())
        for phase in ("timing", "work")
    }
    assert all(
        r["status"] == "M1_local_loader_only_passed"
        and not r["backend_import_exercised"]
        and r["search_attempts"] == 0
        for r in loaders.values()
    )
    for name in ("timing-module.so", "work-module.so"):
        data = (KIT / name).read_bytes()
        assert data[:4] == b"\x7fELF" and int.from_bytes(data[18:20], "little") == 62
        assert b"fannbench_v2_audit_read" in data
    assert b"fannbench_diagnostic_reset" not in (KIT / "timing-module.so").read_bytes()
    assert b"fannbench_diagnostic_reset" in (KIT / "work-module.so").read_bytes()
    previous = STUDY / "kits/m1-runtime-qualification-v1"
    assert sha(previous.with_suffix(".tar.gz")) == (
        "c4e0c46e04dd1796f063b94c257e48f31bba487594ab222717098d1e7aede532"
    )
    for name in ("timing-module.so", "work-module.so", "compiled-programs.json", "m1-plan.json"):
        assert sha(KIT / name) == sha(previous / name), "analysis amendment changed workload"
    subprocess.run(
        [
            "bash",
            "-n",
            str(KIT / "submit.sh"),
            str(KIT / "run-on-compute.sh"),
            str(KIT / "startup-preflight.sh"),
        ],
        check=True,
    )
    binding = json.loads((KIT / "binding.json").read_text())
    binding["protocol_sha256"] = sha(KIT / "m1-protocol.md")
    write(KIT / "binding.json", binding)
    readiness = {
        "schema": "fannagent.M1-local-readiness.v1",
        "status": (
            "local_semantic_schedule_CPU_work_verifier_passed_"
            "native_preflight_and_original_graph_pending"
        ),
        "date": "2026-11-16",
        "pre_M1_commit": "f96e02d",
        "unit_tests": 8,
        "smokes": smokes,
        "loader_checks": loaders,
        "return_verifier": verifier,
        "physical_CPU_analysis_regression": cpu_analysis,
        "native_full_backend_preflight_required_before_sbatch": True,
        "original_graph_qualified": False,
        "all_six_filters": True,
        "exact_serving_calls": 0,
        "provider_calls": 0,
        "validation_test_outcomes_opened": False,
        "source_sha256": {p.name: sha(p) for p in sorted(HERE.iterdir()) if p.is_file()},
        "external_checks": {
            str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size}
            for p in sorted(checks.iterdir())
            if p.is_file()
        },
        "local_failed_check_disposition": (
            "Missing-session-helper and host helper-path failures retained; "
            "missing helper and host import path corrected before sealing. "
            "No failed study allocation or provider call was made."
        ),
    }
    write(KIT / "local-readiness.json", readiness)
    sums()
    assert all(p.is_file() for p in KIT.iterdir()), "unexpected mutable extra directory in kit"
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(KIT, arcname=KIT.name)
    archive.with_suffix(".gz.sha256").write_text(sha(archive) + "  " + archive.name + "\n")
    frozen = {
        "schema": "fannagent.M1-freeze.v1",
        "date": "2026-11-16",
        "status": "sealed_pending_native_preflight_and_user_Torch_submission",
        "pre_M1_commit": "f96e02d",
        "deployment_version": 2,
        "supersedes_unsubmitted_deployment": {
            "archive": "m1-runtime-qualification-v1.tar.gz",
            "sha256": "c4e0c46e04dd1796f063b94c257e48f31bba487594ab222717098d1e7aede532",
            "source_commit": "9f85f72",
            "reason": "Add physical-CPU analysis summaries; runtime, workload, caps unchanged.",
            "prior_archive_and_freeze_preserved": True,
        },
        "archive_sha256": sha(archive),
        "binding_sha256": sha(KIT / "binding.json"),
        "plan_sha256": sha(KIT / "m1-plan.json"),
        "protocol_sha256": sha(KIT / "m1-protocol.md"),
        "readiness_sha256": sha(KIT / "local-readiness.json"),
        "runtime_profile": binding["runtime_profile"],
        "timing_module_sha256": binding["timing_module_sha256"],
        "work_module_sha256": binding["work_module_sha256"],
        "split_sha256": binding["split_manifest_sha256"],
        "M0_receipt_sha256": binding["M0_receipt_sha256"],
        "attempts": ledger(),
        "global_attempt_cap": 1000000,
        "resource_ceiling": {"physical_cpus": 4, "memory_gib": 48, "wall_hours": 8},
        "prefixes_to_requalify": 9436,
        "missing_partial_prefixes_to_collect": 1496,
        "exact_serving_calls": 0,
        "provider_calls": 0,
        "validation_test_outcomes_opened": False,
        "automatic_submission_or_retry": False,
        "full_native_startup_preflight_required": True,
        "cost_model_automatically_qualified": False,
        "final_policy_selected": False,
    }
    write(freeze, frozen)
    receipts = HERE / "receipts-v2"
    receipts.mkdir(exist_ok=False)
    for source, name in (
        (freeze, "M1-freeze.json"),
        (KIT / "local-readiness.json", "local-readiness.json"),
        (KIT / "m1-plan.json", "M1-plan.json"),
        (checks / "local-verifier-check.json", "local-verifier-check.json"),
        (KIT / "compiled-programs.json", "compiled-programs.json"),
    ):
        shutil.copyfile(source, receipts / name)
    print(
        json.dumps(
            {
                "archive": str(archive),
                "sha256": frozen["archive_sha256"],
                "bytes": archive.stat().st_size,
                "attempts": ledger()["total"],
                "status": frozen["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
