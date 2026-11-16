"""Seal a namespace-only deployment repair, with native readiness explicitly pending."""

import io
import json
import shutil
import subprocess
import tarfile
import unittest

from build_repair import HERE, NEW_NAME, ORIGINAL_ARCHIVE, ORIGINAL_FREEZE, STUDY, seal_sums, sha
from test_repair import Repair


def main():
    kit = STUDY / "kits" / NEW_NAME
    archive = kit.with_suffix(".tar.gz")
    freeze = STUDY / "freeze/reader-attribution-startup-fix-v1.json"
    assert not archive.exists() and not freeze.exists(), "preserve previously sealed deployment"
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Repair)
    )
    assert result.wasSuccessful() and result.testsRun == 6, output.getvalue()
    checks = STUDY / "runtime-attribution-startup-fix-v1/checks"
    (checks / "repair-unit-tests.log").write_text(output.getvalue())
    original = json.loads((checks / "original-startup.log").read_text())
    assert original["status"] == "original_failure_reproduced"
    phase_checks = {}
    for phase in ("timing", "work"):
        record = json.loads((checks / ("repaired-" + phase + "-loader.log")).read_text())
        assert record["status"] == "repaired_entrypoint_and_frozen_loader_passed"
        assert record["backend_import_exercised"] is False
        assert record["search_attempts"] == record["provider_calls"] == 0
        phase_checks[phase] = record
    verifier = json.loads((checks / "verifier-check.json").read_text())
    assert verifier["status"] == "passed" and verifier["timing_records"] == 630000
    assert verifier["work_records"] == 15750 and verifier["total_attempts"] == 684950
    assert "pyarrow" in (checks / "repaired-timing-thread-bounds.log").read_text()
    subprocess.run(
        ["bash", "-n", str(kit / "startup-preflight.sh"), str(kit / "submit.sh")], check=True
    )
    receipt = {
        "schema": "reader-attribution-startup-repair-checks.v1",
        "status": "local_loader_and_host_checks_passed_native_backend_preflight_pending",
        "date": "2026-11-15",
        "unit_tests_passed": 6,
        "original_failure": original,
        "phase_loader_checks": phase_checks,
        "fabricated_full_size_return_verifier": verifier,
        "native_backend_preflight_required_before_sbatch": True,
        "local_full_backend_import": "crashed in PyArrow under Mac x86 QEMU; not a pass",
        "checks_sha256": {p.name: sha(p) for p in sorted(checks.glob("*")) if p.is_file()},
        "repair_source_sha256": {p.name: sha(p) for p in sorted(HERE.glob("*")) if p.is_file()},
        "provider_calls": 0,
        "new_Torch_jobs_submitted_by_Codex": 0,
        "validation_test_outcomes_opened": False,
    }
    (kit / "local-startup-readiness.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    shutil.copyfile(HERE / "README.md", kit / "STARTUP-REPAIR.md")
    metadata_path = kit / "startup-repair.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["additional_preflight"] = sha(kit / "startup_preflight.py")
    metadata["additional_native_preflight_launcher"] = sha(kit / "startup-preflight.sh")
    metadata["local_readiness_receipt_sha256"] = sha(kit / "local-startup-readiness.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    seal_sums(kit)
    assert all(path.is_file() for path in kit.iterdir()), "unexpected extra kit directory"
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(kit, arcname=kit.name)
    archive.with_suffix(".gz.sha256").write_text(sha(archive) + "  " + archive.name + "\n")
    frozen = {
        "schema": "reader-attribution-deployment-repair-freeze.v1",
        "date": "2026-11-15",
        "status": "replacement_sealed_native_startup_preflight_required_before_manual_submission",
        "failed_job_id": "23074287",
        "failed_return_archive_verification": "pending_download",
        "kit": NEW_NAME,
        "archive_sha256": sha(archive),
        "original_archive_sha256": ORIGINAL_ARCHIVE,
        "original_freeze_sha256": ORIGINAL_FREEZE,
        "study_binding_sha256_unchanged": sha(kit / "binding.json"),
        "repair_metadata_sha256": sha(metadata_path),
        "local_readiness_receipt_sha256": sha(kit / "local-startup-readiness.json"),
        "planned_attempts_unchanged": 684950,
        "search_modules_schedule_policy_scoring_analysis_unchanged": True,
        "automatic_submission": False,
        "provider_calls": 0,
        "validation_test_outcomes_opened": False,
    }
    freeze.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    receipts = HERE / "receipts"
    receipts.mkdir(exist_ok=False)
    for source, name in (
        (freeze, "deployment-freeze.json"),
        (kit / "local-startup-readiness.json", "local-readiness.json"),
        (metadata_path, "startup-repair.json"),
    ):
        shutil.copyfile(source, receipts / name)
    print(
        json.dumps(
            {
                "archive": str(archive),
                "sha256": frozen["archive_sha256"],
                "bytes": archive.stat().st_size,
                "status": frozen["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
