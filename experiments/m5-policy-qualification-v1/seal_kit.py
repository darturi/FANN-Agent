"""Require local engineering evidence and seal the one prospective M5 deployment."""

import json
import shutil
import subprocess
import sys
import tarfile

from m5_design import ledger
from package_kit import HERE, KIT, ROOT, RUNTIME, STUDY, sha, sums, sync, write


def smoke(path):
    records = [
        json.loads(line.removeprefix("SMOKE_RECEIPT "))
        for line in path.read_text().splitlines()
        if line.startswith("SMOKE_RECEIPT ")
    ]
    assert len(records) == 1 and records[0]["status"] == "passed"
    r = records[0]
    assert r["programs"] == 5 and r["conditions"] == [-1, 743, 527, 310, 192, 108, 32]
    assert r["exact_serving_calls"] == r["provider_calls"] == 0
    assert r["validation_test_outcomes_opened"] is False
    return r


def main():
    archive = KIT.with_suffix(".tar.gz")
    freeze = STUDY / "freeze/m5-policy-qualification-v1.json"
    assert not archive.exists() and not freeze.exists(), "never overwrite a sealed deployment"
    sync()
    checks = RUNTIME / "checks"
    for script, log in (
        ("test_m5.py", "unit-tests.log"),
        ("check_compiled.py", "compiled-parity.log"),
        ("check_bound_reference.py", "bound-reference-check.log"),
    ):
        r = subprocess.run(
            [sys.executable, "-B", str(HERE / script)], capture_output=True, text=True
        )
        (checks / log).write_text(r.stdout + r.stderr)
        assert r.returncode == 0, log
    smokes = {
        name: smoke(checks / ("smoke-" + name + ".log")) for name in ("timing", "work", "zero")
    }
    assert smokes["timing"]["searches"] == ledger(28, 84, 4)["timing"]
    assert smokes["work"]["searches"] == ledger(28, 84, 4)["work"]
    assert smokes["zero"]["zero_output_nullable_continuation_verified"]
    verifier = json.loads((checks / "local-verifier-check.json").read_text())
    assert verifier["status"] == "passed" and verifier["production_scope_rejects_fixture"]
    assert len(verifier["bad_CPU_order_missing_prefix_work_sample_and_module_rejected"]) == 8
    assert verifier["attempts"]["total"] == 3220 and verifier["timing_records"] == 1344
    cpu = json.loads((checks / "cpu-analysis-regression.json").read_text())
    assert cpu["status"] == "passed" and cpu["comparisons"] == 48
    loaders = {
        phase: json.loads((checks / ("preflight-" + phase + "-loader.log")).read_text())
        for phase in ("timing", "work")
    }
    assert all(
        r["status"] == "M5_local_loader_only_passed"
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
    readiness = {
        "schema": "fannagent.M5-local-readiness.v1",
        "date": "2026-11-16",
        "status": "local_checks_passed_original_graph_and_native_preflight_pending",
        "pre_M5_commit": "bdbcab4",
        "smokes": smokes,
        "loader_checks": loaders,
        "return_verifier": verifier,
        "physical_CPU_analysis": cpu,
        "compiled_decisions": json.loads((checks / "compiled-parity.json").read_text()),
        "bound_reference": json.loads((checks / "bound-reference-check.json").read_text()),
        "native_full_backend_preflight_required_before_sbatch": True,
        "original_graph_M5_qualified": False,
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
        "local_failed_check_disposition": "First synthetic launch omitted the module bind; hash "
        "gate rejected before any query. Log preserved. Module mount corrected. Initial host "
        "compiler invocations used Python3.10; corrected to project Python3.12. "
        "First zero-population fixture retained lower-vote bands; its assertion failed. "
        "That synthetic fixture was preserved and corrected to zero votes for every row. "
        "No study allocation or provider request occurred.",
    }
    write(KIT / "local-readiness.json", readiness)
    sums()
    assert all(p.is_file() for p in KIT.iterdir())
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(KIT, arcname=KIT.name)
    archive.with_suffix(".gz.sha256").write_text(sha(archive) + "  " + archive.name + "\n")
    binding = json.loads((KIT / "binding.json").read_text())
    frozen = {
        "schema": "fannagent.M5-freeze.v1",
        "date": "2026-11-16",
        "status": "sealed_pending_native_preflight_and_user_Torch_submission",
        "pre_M5_commit": "bdbcab4",
        "archive_sha256": sha(archive),
        "archive_bytes": archive.stat().st_size,
        "binding_sha256": sha(KIT / "binding.json"),
        "plan_sha256": sha(KIT / "m5-plan.json"),
        "protocol_sha256": sha(KIT / "m5-protocol.md"),
        "readiness_sha256": sha(KIT / "local-readiness.json"),
        "nominees_sha256": binding["nominees_sha256"],
        "runtime_profile": binding["runtime_profile"],
        "timing_module_sha256": binding["timing_module_sha256"],
        "work_module_sha256": binding["work_module_sha256"],
        "split_sha256": binding["split_manifest_sha256"],
        "attempts": ledger(),
        "resource_ceiling": {"physical_cpus": 4, "memory_gib": 48, "wall_hours": 6},
        "global_attempt_cap": 225000,
        "exact_serving_calls": 0,
        "provider_calls": 0,
        "validation_test_outcomes_opened": False,
        "automatic_submission_or_retry": False,
        "full_native_startup_preflight_required": True,
        "final_policy_selected": False,
    }
    write(freeze, frozen)
    (STUDY / "protocol/m5-policy-qualification-v1.md").write_text(
        (HERE / "PROTOCOL.md").read_text()
    )
    receipts = HERE / "receipts"
    receipts.mkdir(exist_ok=False)
    for source, name in (
        (freeze, "M5-freeze.json"),
        (KIT / "binding.json", "binding.json"),
        (KIT / "m5-plan.json", "M5-plan.json"),
        (KIT / "local-readiness.json", "local-readiness.json"),
        (KIT / "compiled-programs.json", "compiled-programs.json"),
        (KIT / "nominee-source-delta.json", "nominee-source-delta.json"),
    ):
        shutil.copyfile(source, receipts / name)
    print(json.dumps(frozen, indent=2))


if __name__ == "__main__":
    main()
