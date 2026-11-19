"""Seal a supervised verification repair, preserving all programs and costs."""

import ast
import hashlib
import json
import shutil
import tarfile
from datetime import UTC, datetime

from prepare_capture import HERE, WORK, seal, sha


def measurement_ast(path):
    names = {
        "timing",
        "ordered",
        "reader_order",
        "family_for",
        "schedule",
        "quality_required",
        "FAMILIES",
        "ARMS",
        "SEED",
        "ROTATIONS",
        "READERS",
    }
    selected = {}
    for node in ast.parse(path.read_text()).body:
        name = (
            node.name
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            else (
                node.targets[0].id
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                else None
            )
        )
        if name in names:
            selected[name] = hashlib.sha256(
                ast.dump(node, include_attributes=False).encode()
            ).hexdigest()
    assert set(selected) == names
    return selected


def main():
    source = WORK / "benchmark-kit-v2"
    target = WORK / "benchmark-kit-v3"
    failed = WORK / "return-23716630"
    reservation = json.loads((failed / "results/reservation.json").read_text())
    assert reservation["source_charged"] == 28672 and reservation["reserved_total"] == 29696
    assert reservation["actual_total_at_reservation"] == 28672 and reservation["reservations"] == 1
    assert not any(
        (failed / "results" / n).exists()
        for n in ("quality.jsonl", "timing.jsonl", "attempts.json", "receipt.json")
    )
    accounting = (failed / "accounting.psv").read_text()
    assert accounting.splitlines()[0].split("|")[1:3] == ["FAILED", "1:0"]
    elapsed = max(int(r.split("|")[4]) for r in accounting.splitlines())
    assert elapsed == 207
    fixture = WORK / "fixture-v2/checks/frontier-projection-v1.json"
    assert (
        json.loads(fixture.read_text())["status"]
        == "independent_frontier_projection_fixture_passed"
    )
    assert measurement_ast(source / "broad_benchmark.py") == measurement_ast(
        HERE / "broad_benchmark.py"
    )
    previous = json.loads((source / "binding.json").read_text())
    target.mkdir()
    for name, digest in previous["files"].items():
        assert sha(source / name) == digest, name
        shutil.copyfile(source / name, target / name)
    for name in ("broad_benchmark.py", "canonical_features.py", "PROTOCOL.md"):
        shutil.copyfile(HERE / name, target / name)
    shutil.copyfile(fixture, target / "frontier-projection-fixture.json")
    evidence = {
        "schema": "fannagent.broad-oracle.failed-stage.v1",
        "job_id": "23716630",
        "accounting": accounting,
        "conservative_allocated_seconds": elapsed,
        "reservation": reservation,
        "extra_reserved_queries_charged": 1024,
        "actual_ann_query_count_known": False,
        "actual_ann_query_count_bounds": [1, 1024],
        "quality_or_latency_samples_collected": False,
        "raw_archive_sha256": sha(failed / "broad-oracle-benchmark-23716630.tar.gz"),
        "raw_results": str(failed / "results"),
        "stderr_sha256": sha(failed / "slurm-23716630.err"),
        "automatic_retry": False,
        "supervised_validation_repair": True,
    }
    (target / "prior-failed-accounting.json").write_text(json.dumps(evidence, indent=2) + "\n")
    plan = json.loads((target / "timing-plan.json").read_text())
    plan.update(
        revision="v3",
        prior_failed_elapsed_seconds=elapsed,
        prior_failed_job_id="23716630",
        prior_failed_extra_reserved_queries=1024,
        source_reserved_attempts_carried=29696,
        prior_total_allocated_seconds=2012,
        aggregate_max_seconds=2012 + plan["wall_limit_seconds"],
        supervised_validation_repair=True,
    )
    assert plan["aggregate_max_seconds"] <= 21600
    (target / "timing-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    run = (target / "benchmark_run.py").read_text()
    key = '"prior_cancelled_elapsed_seconds": 122,'
    assert run.count(key) == 1
    run = run.replace(
        key,
        key + '\n            "prior_failed_elapsed_seconds": 207,\n'
        '            "supervised_validation_repair": True,',
    )
    (target / "benchmark_run.py").write_text(run)
    resume = json.loads((target / "resume-plan.json").read_text())
    old_benchmark = resume["policy_and_measurement_inputs_unchanged"].pop("broad_benchmark.py")
    assert old_benchmark == sha(source / "broad_benchmark.py")
    for name, digest in resume["policy_and_measurement_inputs_unchanged"].items():
        assert sha(target / name) == digest, name
    resume.update(
        recorded_utc=datetime.now(UTC).isoformat(),
        supervised_validation_repair=True,
        prior_failed_job_id="23716630",
        prior_failed_conservative_allocated_seconds=207,
        prior_failed_extra_reserved_queries=1024,
        primary_measurement_ast_unchanged=measurement_ast(target / "broad_benchmark.py"),
        prior_benchmark_source_sha256=old_benchmark,
        repaired_benchmark_source_sha256=sha(target / "broad_benchmark.py"),
        repair_scope=(
            "Canonical feature projection and carried accounting only; frozen native module, "
            "policies, cohorts, schedule and primary timing are unchanged."
        ),
    )
    (target / "resume-plan.json").write_text(json.dumps(resume, indent=2) + "\n")
    seal(target, WORK / "broad-oracle-benchmark-v3.tar.gz")
    changed = [
        p.name
        for p in target.iterdir()
        if p.is_file() and (not (source / p.name).exists() or sha(p) != sha(source / p.name))
    ]
    overlay = WORK / "broad-oracle-benchmark-v3-overlay.tar.gz"
    with tarfile.open(overlay, "x:gz") as handle:
        for name in sorted(changed):
            handle.add(target / name, arcname=name)
    overlay.with_suffix(".gz.sha256").write_text(sha(overlay) + "  " + overlay.name + "\n")
    submission = json.loads((WORK / "benchmark-v2-submission.json").read_text())
    manifest = {
        "schema": "fannagent.broad-oracle.overlay.v1",
        "changed": sorted(changed),
        "base_binding_sha256": sha(source / "binding.json"),
        "new_binding_sha256": sha(target / "binding.json"),
        "overlay_sha256": sha(overlay),
        "base_files": previous["files"],
        "new_files": json.loads((target / "binding.json").read_text())["files"],
        "base_stage": submission["stage"],
        "prior_failed_job_id": "23716630",
    }
    (WORK / "benchmark-v3-overlay-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "kit": str(target),
                "overlay_bytes": overlay.stat().st_size,
                "prior_seconds": 2012,
                "source_charged_ann_reservations": 29696,
                "aggregate_max_seconds": plan["aggregate_max_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
