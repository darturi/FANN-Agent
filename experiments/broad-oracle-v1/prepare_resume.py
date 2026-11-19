"""Seal an explicitly resumed comparison with frozen programs and carried costs."""

import json
import shutil
import tarfile
from datetime import UTC, datetime

from prepare_capture import WORK, seal, sha


def main():
    source = WORK / "benchmark-kit-v1"
    target = WORK / "benchmark-kit-v2"
    prior = json.loads((WORK / "resume-accounting-20261119.json").read_text())
    assert prior["job_id"] == "23648495"
    assert "CANCELLED" in prior["accounting"].splitlines()[0]
    assert prior["result_inventory"] == ["exposure.json", "host-exit.json"]
    assert all(
        prior["results_metadata"][n] is None
        for n in (
            "attempts.json",
            "reservation.json",
            "reservation.pending",
            "reservation-final.json",
            "receipt.json",
            "frontier-qualification.json",
        )
    )
    elapsed = max(int(line.split("|")[4]) for line in prior["accounting"].splitlines())
    assert elapsed == 122
    previous = json.loads((source / "binding.json").read_text())
    target.mkdir()
    for name, digest in previous["files"].items():
        assert sha(source / name) == digest, name
        shutil.copyfile(source / name, target / name)
    plan = json.loads((target / "timing-plan.json").read_text())
    assert plan["source_elapsed_seconds"] == 1683
    assert 1683 + elapsed + plan["wall_limit_seconds"] <= 21600
    plan.update(
        explicit_user_resume=True,
        prior_cancelled_elapsed_seconds=elapsed,
        prior_total_allocated_seconds=1683 + elapsed,
        aggregate_max_seconds=1683 + elapsed + plan["wall_limit_seconds"],
        prior_cancelled_job_id="23648495",
        prior_cancelled_ann_queries=0,
        prior_cancelled_extra_reserved_queries=0,
        revision="v2",
    )
    (target / "timing-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    shutil.copyfile(
        WORK / "resume-accounting-20261119.json", target / "prior-cancelled-accounting.json"
    )
    run = (target / "benchmark_run.py").read_text()
    key = '"source_elapsed_seconds": 1683,'
    assert run.count(key) == 1
    run = run.replace(
        key,
        key + '\n            "prior_cancelled_elapsed_seconds": 122,\n'
        '            "explicit_user_resume": True,',
    )
    (target / "benchmark_run.py").write_text(run)
    unchanged = (
        "oracle-module.so",
        "compiled-programs.json",
        "compiled-v3.json",
        "broad_contract.py",
        "broad_support.py",
        "broad_benchmark.py",
        "oracle_feasible-broad-full_workload.json",
        "oracle_feasible-broad-heldout_test.json",
        "full_workload-choices.jsonl",
        "heldout_test-choices.jsonl",
        "source-cases.jsonl",
    )
    for name in unchanged:
        assert sha(target / name) == sha(source / name), name
    resume = {
        "schema": "fannagent.broad-oracle.resume.v1",
        "explicit_user_resume": True,
        "recorded_utc": datetime.now(UTC).isoformat(),
        "prior_cancelled_job_id": "23648495",
        "prior_conservative_allocated_seconds": elapsed,
        "prior_extra_ann_reservations": 0,
        "prior_extra_ann_attempts": 0,
        "source_capture_allocated_seconds": 1683,
        "original_binding_sha256": sha(source / "binding.json"),
        "policy_and_measurement_inputs_unchanged": {n: sha(source / n) for n in unchanged},
        "source_reserved_ann_attempts": 28672,
        "no_partial_timings_used": True,
        "automatic_retry": False,
    }
    (target / "resume-plan.json").write_text(json.dumps(resume, indent=2) + "\n")
    # Seal all inputs locally; ship only changed small files. The remote stage
    # hard-links verified immutable bytes from v1 and never overwrites them.
    seal(target, WORK / "broad-oracle-benchmark-v2.tar.gz")
    changed = [
        p.name
        for p in target.iterdir()
        if p.is_file() and (not (source / p.name).exists() or sha(p) != sha(source / p.name))
    ]
    overlay = WORK / "broad-oracle-benchmark-v2-overlay.tar.gz"
    with tarfile.open(overlay, "x:gz") as handle:
        for name in sorted(changed):
            handle.add(target / name, arcname=name)
    overlay.with_suffix(".gz.sha256").write_text(sha(overlay) + "  " + overlay.name + "\n")
    manifest = {
        "schema": "fannagent.broad-oracle.overlay.v1",
        "changed": sorted(changed),
        "base_binding_sha256": sha(source / "binding.json"),
        "new_binding_sha256": sha(target / "binding.json"),
        "overlay_sha256": sha(overlay),
        "base_files": previous["files"],
        "new_files": json.loads((target / "binding.json").read_text())["files"],
    }
    (WORK / "benchmark-v2-overlay-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "kit": str(target),
                "overlay_bytes": overlay.stat().st_size,
                "prior_seconds": 1805,
                "aggregate_max_seconds": plan["aggregate_max_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
