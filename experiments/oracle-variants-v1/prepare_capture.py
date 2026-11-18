"""Seal all-cohort legal-action acquisition on the unchanged qualified engine."""

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
WORK = STUDY / "oracle-variants-v1"
BASE = STUDY / "full-workload-oracle-v1/kit-r2"
SOURCE = STUDY / "full-workload-oracle-v1/return-23567950/results"


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main():
    target = WORK / "capture-kit-v2"
    target.mkdir()
    for path in BASE.iterdir():
        if path.is_file() and path.name not in ("binding.json", "SHA256SUMS"):
            shutil.copyfile(path, target / path.name)
    parent = HERE.parent / "full-workload-oracle-v1"
    shutil.copyfile(parent / "timing_followup.py", target / "timing_followup.py")
    shutil.copyfile(HERE / "variants_capture.py", target / "variants_capture.py")
    shutil.copyfile(HERE / "README.md", target / "VARIANTS-PROTOCOL.md")
    for source, destination in (
        ("quality.jsonl", "source-quality.jsonl"),
        ("trajectories.jsonl", "source-trajectories.jsonl"),
        ("exact-reference.jsonl", "source-exact-reference.jsonl"),
        ("eligibility.json", "source-eligibility.json"),
    ):
        shutil.copyfile(SOURCE / source, target / destination)
    quality = {r["id"]: r for r in map(json.loads, (SOURCE / "quality.jsonl").open())}
    ideals = {}
    seen = {qid: 0 for qid in quality}
    for row in map(json.loads, (SOURCE / "prefixes.jsonl").open()):
        qid = row["id"]
        seen[qid] += 1
        assert row["checkpoint"] == seen[qid] and row["prefix_verified"] is True
        if qid not in ideals and row["recall"] + 1e-12 >= quality[qid]["native_recall"]:
            ideals[qid] = {
                k: row[k] for k in ("checkpoint", "output", "recall", "target", "prefix_sha256")
            }
    with (target / "ideal-recall-choices.jsonl").open("x") as out:
        for qid, row in quality.items():
            assert seen[qid] == row["tested_count"]
            choice = ideals.get(
                qid,
                {
                    "checkpoint": 0,
                    "output": row["native"],
                    "recall": row["native_recall"],
                    "target": None,
                    "prefix_sha256": None,
                },
            )
            out.write(json.dumps({"id": qid, **choice}, separators=(",", ":")) + "\n")
    run = (parent / "oracle_run.py").read_text()
    run = run.replace(
        "from oracle_experiment import acquire, offline, timing",
        "import oracle_experiment\nimport variants_capture\n"
        "from variants_capture import acquire, offline, timing\n"
        "oracle_experiment.reserve = variants_capture.reserve",
    )
    run = run.replace("with watchdog(19500):", "with watchdog(6300):")
    old = 'counter["timed_ann"] == 7000 * 32 and counter["offline_exact"] == 7000'
    assert run.count(old) == 1
    run = run.replace(
        old,
        'counter["canonical_capture"] == 7000 '
        'and counter["native_bridge"] == 14000 and counter["ideal_replay"] == 7000',
    )
    run = run.replace("full_workload_oracle_complete", "oracle_variants_capture_complete")
    run = run.replace("FULL_WORKLOAD_ORACLE_COMPLETE", "ORACLE_VARIANTS_CAPTURE_COMPLETE")
    (target / "capture_run.py").write_text(run)
    preflight = (
        (target / "oracle_preflight.py").read_text().replace('"oracle_run.py"', '"capture_run.py"')
    )
    (target / "oracle_preflight.py").write_text(preflight)
    scripts = {
        "run-capture.sh": """#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
job=${SLURM_JOB_ID:?}
run="$stage/run-$job"
mkdir -m700 "$run" "$run/results" "$run/work"
finish() {
 status=$?
 trap - EXIT
 printf '{"exit_code":%d,"job_id":"%s"}\\n' "$status" "$job" > "$run/results/host-exit.json"
 tar -czf "$run/oracle-variants-capture-$job.tar.gz" -C "$run" results
 (cd "$run" && sha256sum "oracle-variants-capture-$job.tar.gz" \\
  > "oracle-variants-capture-$job.tar.gz.sha256")
 exit "$status"
}
trap finish EXIT
bundle=/home/dar579/torch-reviews-first
prepared=/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286
tar -xzf original-package.tar.gz -C "$run"
package="$run/reviews-persistent-batch-native-v1"
timeout --signal=TERM --kill-after=15s 7110s \\
 /share/apps/apptainer/bin/apptainer exec --cleanenv --containall --no-home --pwd /run \\
 --bind "$package:/patch:ro" --bind "$stage:/qual:ro" \\
 --bind "$stage/oracle-module.so:/opt/postgresql/lib/vector.so:ro" \\
 --bind "$bundle:/bundle:ro" --bind "$prepared:/prepared:ro" \\
 --bind "$run/work:/run:rw" --bind "$run/results:/results:rw" \\
 --env PYTHONPATH=/patch:/qual:/opt/torch-reviews/vendor --env PYTHONDONTWRITEBYTECODE=1 \\
 --env TMPDIR=/tmp --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 --env "SLURM_JOB_ID=$job" \\
 "$bundle/images/runtime.sif" python -B /qual/capture_run.py \\
 --package /patch --bundle /bundle --prepared /prepared --work /run --output /results
""",
        "startup-capture.sh": """#!/bin/bash
set -euo pipefail
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
probe="$stage/.startup-preflight"
mkdir -m700 "$probe"
tar -xzf "$stage/original-package.tar.gz" -C "$probe"
package="$probe/reviews-persistent-batch-native-v1"
/share/apps/apptainer/bin/apptainer exec --cleanenv --containall --no-home --pwd /tmp \\
 --bind "$package:/patch:ro" --bind "$stage:/qual:ro" \\
 --bind "$stage/oracle-module.so:/opt/postgresql/lib/vector.so:ro" \\
 --env PYTHONPATH=/patch:/qual:/opt/torch-reviews/vendor --env PYTHONDONTWRITEBYTECODE=1 \\
 --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 \\
 /home/dar579/torch-reviews-first/images/runtime.sif \\
 python -B /qual/oracle_preflight.py --package /patch > "$probe/check.json" 2> "$probe/check.err"
cat "$probe/check.json"
""",
        "submit-capture.sh": """#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
[[ "${1:-}" = --check || "${1:-}" = --submit ]]
args=(--account=torch_pr_288_courant --partition=cs --job-name=reviews-oracle-capture
 --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=48G --time=120
 --hint=nomultithread --no-requeue --chdir="$stage"
 --output="$stage/slurm-%j.out" --error="$stage/slurm-%j.err"
 --wrap='exec /opt/slurm/bin/srun --ntasks=1 --cpus-per-task=4 \\
 --hint=nomultithread --cpu-bind=cores --kill-on-bad-exit=1 /bin/bash ./run-capture.sh')
/opt/slurm/bin/sbatch --test-only "${args[@]}"
[[ "$1" = --submit ]] || exit 0
bash startup-capture.sh
mkdir .submitted
job=$(/opt/slurm/bin/sbatch --parsable "${args[@]}")
job=${job%%;*}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
printf '%s\\n' "$job" > job-id
printf 'Submitted oracle variant capture %s\\n' "$job"
""",
    }
    for name, text in scripts.items():
        (target / name).write_text(text)
    previous = json.loads((BASE / "binding.json").read_text())
    write(
        target / "plan.json",
        {
            "schema": "fannagent.oracle-variants.capture.v1",
            "cases": 7000,
            "heldout_cases": 1925,
            "fresh_exact_queries": 0,
            "maximum_fresh_queries": 49000,
            "physical_cpus": 4,
            "memory_gib": 48,
            "wall_limit_seconds": 7200,
            "watchdog_seconds": 6300,
            "provider_calls": 0,
            "primary_timing_queries": 0,
            "automatic_retry": False,
            "new_comparison_attempt_cap": 2000000,
            "new_comparison_aggregate_seconds_cap": 21600,
            "source_report_sha256": sha(SOURCE / "report.json"),
            "original_count_preserving_ideal_retained": True,
            "source_prefixes_sha256": sha(SOURCE / "prefixes.jsonl"),
            "source_quality_sha256": sha(SOURCE / "quality.jsonl"),
        },
    )
    write(
        target / "binding.json",
        {
            "schema": "fannagent.oracle-variants.capture-binding.v1",
            "graph": previous["graph"],
            "source_binding_sha256": sha(BASE / "binding.json"),
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
    archive = WORK / "oracle-variants-capture-v2.tar.gz"
    with tarfile.open(archive, "x:gz") as handle:
        handle.add(target, arcname="oracle-variants-capture-v2")
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        sha(archive) + "  " + archive.name + "\n"
    )
    print(
        json.dumps(
            {
                "archive": str(archive),
                "sha256": sha(archive),
                "cases": len(quality),
                "recall_only_ideal_changes": sum(
                    ideals.get(qid, {}).get("checkpoint", 0) != row["checkpoint"]
                    for qid, row in quality.items()
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
