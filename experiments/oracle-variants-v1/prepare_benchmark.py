"""Seal shared-schedule timing only after capture and feasible-policy freezing."""

import argparse
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
WORK = STUDY / "oracle-variants-v1"


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--fit", type=Path, required=True)
    parser.add_argument("--elapsed", type=int, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    source = args.capture
    receipt = json.loads((source / "receipt.json").read_text())
    require(receipt["status"] == "oracle_variants_capture_complete", "incomplete capture")
    require(
        json.loads((source / "host-exit.json").read_text())
        == {"job_id": receipt["job_id"], "exit_code": 0},
        "capture host failed",
    )
    require(
        json.loads((source / "capture-verification.json").read_text())["status"]
        == "legal_action_capture_verified",
        "capture not independently verified",
    )
    for cohort in ("full_workload", "heldout_test"):
        manifest = json.loads((args.fit / (cohort + "-fit-inputs.json")).read_text())
        require(manifest["cases_sha256"] == sha(source / "cases.jsonl"), "fit source differs")
        require(manifest["fitter_source_sha256"] == sha(HERE / "dsl_fit.py"), "fitter changed")
        require(
            sha(args.fit / ("oracle_feasible-" + cohort + ".json"))
            == sha(args.runtime / ("oracle_feasible-" + cohort + ".json")),
            "compiled policy differs from fit",
        )
    wall = min(14400, ((21600 - args.elapsed - 120) // 60) * 60)
    require(wall >= 7200, "less than two hours remains in aggregate envelope")
    target = WORK / ("benchmark-kit-" + args.revision)
    target.mkdir()
    base = WORK / "capture-kit-v2"
    for path in base.iterdir():
        if path.is_file() and path.name not in ("binding.json", "SHA256SUMS"):
            shutil.copyfile(path, target / path.name)
    for old, new in (
        ("cases.jsonl", "source-cases.jsonl"),
        ("capture-freeze.json", "source-capture-freeze.json"),
        ("receipt.json", "source-capture-receipt.json"),
        ("reservation-final.json", "source-capture-budget.json"),
        ("exact-reference.jsonl", "source-exact-reference.jsonl"),
        ("eligibility.json", "source-eligibility.json"),
    ):
        shutil.copyfile(source / old, target / new)
    shutil.copyfile(args.runtime / "engine/vector.so", target / "oracle-module.so")
    with tarfile.open(target / "engine-sources.tar.gz", "w:gz") as handle:
        for path in sorted((args.runtime / "engine").rglob("*")):
            if path.is_file() and path.suffix not in (".o", ".bc", ".so"):
                handle.add(path, arcname="engine/" + str(path.relative_to(args.runtime / "engine")))
    for name in (
        "compiled-programs.json",
        "compiler-certificate.json",
        "oracle_feasible-full_workload.json",
        "oracle_feasible-heldout_test.json",
    ):
        shutil.copyfile(args.runtime / name, target / name)
    for cohort in ("full_workload", "heldout_test"):
        for suffix in ("-fit-certificate.json", "-fit-inputs.json"):
            shutil.copyfile(args.fit / (cohort + suffix), target / (cohort + suffix))
    shutil.copyfile(args.fit / "fit-environment.json", target / "fit-environment.json")
    for name in ("m5_design.py", "m5_experiment.py"):
        shutil.copyfile(HERE.parent / "m5-policy-qualification-v1" / name, target / name)
    for name in (
        "variants_benchmark.py",
        "variants_analyse.py",
        "TIMING-PROTOCOL.md",
        "dsl_fit.py",
    ):
        shutil.copyfile(HERE / name, target / name)
    parent = HERE.parent / "full-workload-oracle-v1"
    run = (parent / "oracle_run.py").read_text()
    run = run.replace(
        "from oracle_experiment import acquire, offline, timing",
        "import oracle_experiment\nimport variants_benchmark\n"
        "from variants_benchmark import acquire, offline, timing\n"
        "oracle_experiment.reserve = variants_benchmark.reserve",
    )
    run = run.replace("with watchdog(19500):", f"with watchdog({wall - 600}):")
    old = 'counter["timed_ann"] == 7000 * 32 and counter["offline_exact"] == 7000'
    require(run.count(old) == 1, "entry coverage assertion changed")
    run = run.replace(
        old, 'counter["timed_ann"] == 7000 * 64 and counter["quality_ann"] == 7000 * 8'
    )
    run = run.replace("full_workload_oracle_complete", "oracle_variants_benchmark_complete")
    run = run.replace("FULL_WORKLOAD_ORACLE_COMPLETE", "ORACLE_VARIANTS_BENCHMARK_COMPLETE")
    run = run.replace(
        '"exact_serving_calls": 0,',
        '"exact_serving_calls": 0, "fresh_exact_queries": 0,\n'
        f'            "source_capture_job_id": "{receipt["job_id"]}",\n'
        f'            "source_elapsed_seconds": {args.elapsed},\n'
        '            "policy_language_feasible": "unchanged agent v2 DSL",',
    )
    (target / "benchmark_run.py").write_text(run)
    preflight = (
        (target / "oracle_preflight.py")
        .read_text()
        .replace('"capture_run.py"', '"benchmark_run.py"')
    )
    (target / "oracle_preflight.py").write_text(preflight)
    for old, new in (
        ("run-capture.sh", "run-benchmark.sh"),
        ("startup-capture.sh", "startup-benchmark.sh"),
        ("submit-capture.sh", "submit-benchmark.sh"),
    ):
        text = (base / old).read_text()
        text = text.replace("capture_run.py", "benchmark_run.py")
        text = text.replace("oracle-variants-capture-$job", "oracle-variants-benchmark-$job")
        text = text.replace("run-capture.sh", "run-benchmark.sh")
        text = text.replace("startup-capture.sh", "startup-benchmark.sh")
        text = text.replace("--time=120", "--time=" + str(wall // 60))
        text = text.replace("7110s", str(wall - 90) + "s")
        text = text.replace("reviews-oracle-capture", "reviews-oracle-benchmark")
        text = text.replace(
            "Submitted oracle variant capture", "Submitted oracle variant benchmark"
        )
        (target / new).write_text(text)
    write(
        target / "timing-plan.json",
        {
            "schema": "fannagent.oracle-variants.timing-plan.v1",
            "source_job": receipt["job_id"],
            "source_elapsed_seconds": args.elapsed,
            "wall_limit_seconds": wall,
            "aggregate_allocation_cap_seconds": 21600,
            "aggregate_max_seconds": args.elapsed + wall,
            "physical_cpus": 4,
            "memory_gib": 48,
            "readers": 8,
            "rotations": 8,
            "timed_queries": 448000,
            "quality_queries": 56000,
            "warmup_queries": 4480,
            "cases": 7000,
            "heldout_cases": 1925,
            "fresh_exact_queries": 0,
            "quality_gate": "per-case native recall; feasible-test gate applies to test cohort",
            "source_reserved_attempts_carried": json.loads(
                (source / "reservation-final.json").read_text()
            )["charged_total"],
            "cumulative_attempt_cap": 2000000,
            "provider_calls": 0,
            "automatic_retry": False,
            "bootstrap_draws": 20000,
            "bootstrap_seed": 20261118,
            "control_band": [0.98, 1.02],
            "control_interval": 0.90,
            "hindsight_fit": True,
            "agent_discovery_or_generalization_claim": False,
        },
    )
    binding = json.loads((base / "binding.json").read_text())
    write(
        target / "binding.json",
        {
            "schema": "fannagent.oracle-variants.benchmark-binding.v1",
            "graph": binding["graph"],
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
    archive = WORK / ("oracle-variants-benchmark-" + args.revision + ".tar.gz")
    with tarfile.open(archive, "x:gz") as handle:
        handle.add(target, arcname="oracle-variants-benchmark-" + args.revision)
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        sha(archive) + "  " + archive.name + "\n"
    )
    print(
        json.dumps(
            {
                "archive": str(archive),
                "sha256": sha(archive),
                "wall_seconds": wall,
                "aggregate_max_seconds": args.elapsed + wall,
            }
        )
    )


if __name__ == "__main__":
    main()
