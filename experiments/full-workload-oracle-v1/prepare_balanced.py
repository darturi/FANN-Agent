"""Seal the uniform one-cycle pass after both source allocations have stopped."""

import difflib
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1"


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    base = WORK / "kit-r2"
    target = WORK / "balanced-kit-v3"
    source = WORK / "return-23558871/results"
    target.mkdir()
    for path in base.iterdir():
        if path.is_file() and path.name not in ("binding.json", "SHA256SUMS"):
            shutil.copyfile(path, target / path.name)
    for name in (
        "timing_followup.py",
        "balanced_source.py",
        "balanced_run.py",
        "balanced_analyse.py",
        "smoke_balanced.py",
        "BALANCED-PROTOCOL.md",
    ):
        shutil.copyfile(HERE / name, target / name)
    replacements = {
        "oracle_experiment.py": [("for cycle in (0, 1):", "for cycle in (0,):")],
        "oracle_design.py": [("for cycle in (0, 1):", "for cycle in (0,):")],
        "oracle_run.py": [("7000 * 32", "7000 * 16")],
        "analyse.py": [
            ("7, 4, 2, 4", "7, 4, 1, 4"),
            ("for c in (0, 1)", "for c in (0,)"),
            ("len(queries) * 32", "len(queries) * 16"),
        ],
    }
    patch = []
    for name, pairs in replacements.items():
        before = (target / name).read_text()
        after = before
        for old, new in pairs:
            assert after.count(old) == 1, (name, old)
            after = after.replace(old, new)
        (target / name).write_text(after)
        patch.extend(
            difflib.unified_diff(
                before.splitlines(True),
                after.splitlines(True),
                fromfile="original/" + name,
                tofile="balanced/" + name,
            )
        )
    (target / "uniform-repetitions.patch").write_text("".join(patch))
    # Load the sealed source verifier using the unchanged two-cycle source helpers.
    import sys

    sys.path.insert(0, str(WORK / "oracle-followup-v1"))
    from timing_followup import BASE_OPERATIONS, evidence_counts, source_lines, verify_source

    roles = json.loads((base / "query-roles.json").read_text())
    old_manifest = json.loads((source / "source-acquisition.json").read_text())
    old, _, _, old_usage = verify_source(
        source / "source-acquisition", old_manifest, roles, allow_partial=True
    )
    names = (
        "exact-reference.jsonl",
        "quality.jsonl",
        "prefixes.jsonl",
        "trajectories.jsonl",
        "oracle-freeze.json",
        "eligibility.json",
        "acquisition-counts.json",
        "followup-quality.jsonl",
        "reservation.json",
        "host-exit.json",
        "source-acquisition.json",
    )
    manifest = {"files": {name: sha(source / name) for name in names}}
    choices, truths, eligible, _ = verify_source(
        source, manifest, roles, usage_name="acquisition-counts.json"
    )
    assert len(choices) == len(truths) == 7000
    assert not (source / "timing.jsonl").exists() and not (source / "warmup.jsonl").exists()
    reservation = json.loads((source / "reservation.json").read_text())
    assert reservation["source_charged"] == old_usage["total"]
    torn = []
    quality_path = source / "followup-quality.jsonl"
    last = quality_path.read_bytes().splitlines(keepends=True)[-1]
    try:
        json.loads(last)
    except json.JSONDecodeError:
        assert not last.endswith(b"\n")
        torn.append(quality_path.name)
    partial = list(source_lines(quality_path, torn))
    from common import matches
    from oracle_design import validate_output

    seen = set()
    for row in partial:
        key = row["id"], row["family"]
        assert key not in seen
        seen.add(key)
        ref = choices[row["id"]]
        want = ref["output" if row["family"] == "oracle" else "native"]
        assert matches(row["output"], want)
        assert (
            abs(
                validate_output(row["output"], eligible[row["filter"]], truths[row["id"]])
                - row["recall"]
            )
            < 1e-12
        )
    old_used = evidence_counts(old, 7000)
    incomplete = {
        op: old_usage.get(op, 0) - old_used[op] for op in BASE_OPERATIONS if op != "offline_exact"
    }
    unknown = (
        reservation["reserved_total"]
        - evidence_counts(choices, 7000)["total"]
        - sum(incomplete.values())
        - len(partial)
    )
    assert 0 <= unknown <= 2048
    manifest.update(
        schema="fannagent.oracle.complete-source.v1",
        job_id="23558871",
        source_incomplete_charges=incomplete,
        partial_quality_rows=len(partial),
        unobserved_reserved_charges=unknown,
        prior_reserved_total=reservation["reserved_total"],
        torn_final_record_files=torn,
        primary_timing_observations=0,
        previous_source_binding_sha256=sha(WORK / "oracle-followup-v1/binding.json"),
    )
    write(target / "source-acquisition.json", manifest)
    plan = dict(
        schema="fannagent.oracle.balanced-timing.v1",
        source_elapsed_seconds=17249,
        source_allocations={"23544718": 13194, "23558871": 4055},
        wall_limit_seconds=4200,
        watchdog_seconds=3900,
        aggregate_limit_seconds=21600,
        physical_cpus=4,
        memory_gib=48,
        cases=7000,
        heldout_cases=1925,
        repetitions_per_case_family=4,
        timing_cycles=1,
        timed_queries=112000,
        warmup_queries=1120,
        automatic_retry=False,
        every_case_family_checked_against_frozen_source=True,
        separate_qualification_pass=False,
    )
    write(target / "timing-plan.json", plan)
    original_plan = json.loads((base / "plan.json").read_text())
    write(target / "plan.json", {**original_plan, "allocations": 3, "timing_amendment": plan})
    original_source = (
        "/scratch/dar579/fannagent-benchmark-evaluation-v1/oracle-headroom-20261117-v1/"
        "full-workload-oracle-v1/run-23544718/results"
    )
    current_source = (
        "/scratch/dar579/fannagent-benchmark-evaluation-v1/oracle-bookkeeping-followup-v1/"
        "oracle-followup-v1/run-23558871/results"
    )
    for old, new in (
        ("run-followup.sh", "run-balanced.sh"),
        ("startup-followup.sh", "startup-balanced.sh"),
        ("submit-followup.sh", "submit-balanced.sh"),
    ):
        text = (HERE / old).read_text().replace(original_source, current_source)
        text = text.replace("followup_run.py", "balanced_run.py").replace(
            "followup-plan.json", "timing-plan.json"
        )
        text = text.replace("run-followup.sh", "run-balanced.sh").replace(
            "startup-followup.sh", "startup-balanced.sh"
        )
        text = text.replace("oracle-followup-$job", "oracle-balanced-$job").replace(
            "reviews-oracle-followup", "reviews-oracle-balanced"
        )
        (target / new).write_text(text)
        if new in ("run-balanced.sh", "startup-balanced.sh"):
            assert current_source in text, "source bind path changed during wrapper conversion"
    binding = json.loads((base / "binding.json").read_text())
    write(
        target / "binding.json",
        {
            "schema": "fannagent.oracle.balanced-binding.v1",
            "graph": binding["graph"],
            "original_binding_sha256": sha(base / "binding.json"),
            "files": {p.name: sha(p) for p in sorted(target.iterdir()) if p.is_file()},
        },
    )
    (target / "SHA256SUMS").write_text(
        "".join(
            sha(p) + "  " + p.name + "\n"
            for p in sorted(target.iterdir())
            if p.is_file() and p.name != "SHA256SUMS"
        )
    )
    archive = WORK / "oracle-balanced-v3.tar.gz"
    with tarfile.open(archive, "x:gz") as handle:
        handle.add(target, arcname="oracle-balanced-v3")
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        sha(archive) + "  " + archive.name + "\n"
    )
    write(
        WORK / "balanced-source-verification-v3.json",
        {
            "status": "full_source_verified",
            "cases": 7000,
            "partial_quality_rows": len(partial),
            "unobserved_reserved_charges": unknown,
            "prior_reserved_total": reservation["reserved_total"],
            "primary_timings": 0,
            "archive_sha256": sha(archive),
            "aggregate_max_seconds": 21449,
        },
    )
    print((WORK / "balanced-source-verification-v3.json").read_text())


if __name__ == "__main__":
    main()
