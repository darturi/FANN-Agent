"""Freeze v3 fitted artifacts and a shared comparison before any timing."""

import argparse
import json
import shutil
import tarfile
from pathlib import Path

from build_runtime import build
from prepare_capture import BASE, HERE, STUDY, WORK, seal, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--fit", type=Path, required=True)
    parser.add_argument("--elapsed", type=int, required=True)
    parser.add_argument("--phase", choices=("build", "seal"), required=True)
    args = parser.parse_args()
    runtime = WORK / "benchmark-runtime-v1"
    receipt = json.loads((args.capture / "receipt.json").read_text())
    assert receipt["status"] == "oracle_broad_capture_complete"
    assert json.loads((args.capture / "host-exit.json").read_text()) == {
        "exit_code": 0,
        "job_id": receipt["job_id"],
    }
    assert json.loads((args.fit / "source-verification.json").read_text())["cases_sha256"] == sha(
        args.capture / "cases.jsonl"
    )
    if args.phase == "build":
        bindings = []
        for cohort, arm in (("full_workload", 60), ("heldout_test", 61)):
            policy = json.loads(
                (args.fit / ("oracle_feasible-broad-" + cohort + ".json")).read_text()
            )
            cert = json.loads((args.fit / (cohort + "-certificate.json")).read_text())
            assert cert["cases_sha256"] == sha(args.capture / "cases.jsonl")
            assert cert["fitter_sha256"] == sha(HERE / "fit_broad.py")
            bindings.extend(
                [
                    {"arm": arm, "policy": policy, "force_continue": False},
                    {"arm": arm + 10, "policy": policy, "force_continue": True},
                ]
            )
        bindings.append(
            {
                "arm": 85,
                "policy": {
                    "schema": "fannagent.broad-stop.v3",
                    "name": "empty-v3",
                    "rationale": "Native-output empty language control.",
                    "fuel": 2000000,
                    "state_slots": 0,
                    "programs": {},
                },
                "force_continue": False,
            }
        )
        build(bindings, runtime)
        print(runtime)
        return
    wall = min(14400, ((21600 - args.elapsed - 120) // 60) * 60)
    assert wall >= 7200, "insufficient remaining prospective allocation envelope"
    target = WORK / "benchmark-kit-v1"
    target.mkdir()
    for p in (WORK / "capture-kit-v1").iterdir():
        if p.is_file() and p.name not in ("binding.json", "SHA256SUMS"):
            shutil.copyfile(p, target / p.name)
    for old, new in (
        ("cases.jsonl", "source-cases.jsonl"),
        ("capture-freeze.json", "source-capture-freeze.json"),
        ("receipt.json", "source-capture-receipt.json"),
        ("reservation-final.json", "source-capture-budget.json"),
        ("exact-reference.jsonl", "source-exact-reference.jsonl"),
        ("eligibility.json", "source-eligibility.json"),
    ):
        shutil.copyfile(args.capture / old, target / new)
    shutil.copyfile(
        STUDY / "oracle-variants-v1/return-23604734/results/cases.jsonl",
        target / "legacy-cases.jsonl",
    )
    shutil.copyfile(
        STUDY / "oracle-variants-v1/benchmark-kit-v1/compiled-programs.json",
        target / "compiled-programs.json",
    )
    for name in ("functions.sql", "broad_contract.py", "compiled-v3.json"):
        shutil.copyfile(runtime / name, target / name)
    shutil.copyfile(runtime / "engine/vector.so", target / "oracle-module.so")
    with tarfile.open(target / "engine-sources.tar.gz", "w:gz") as handle:
        for p in sorted((runtime / "engine").rglob("*")):
            if p.is_file() and p.suffix not in (".o", ".bc", ".so"):
                handle.add(p, arcname="engine/" + str(p.relative_to(runtime / "engine")))
    for name in ("broad_benchmark.py", "broad_support.py", "PROTOCOL.md"):
        shutil.copyfile(HERE / name, target / name)
    for name in ("m5_design.py", "m5_experiment.py"):
        shutil.copyfile(HERE.parent / "m5-policy-qualification-v1" / name, target / name)
    shutil.copyfile(
        HERE.parent / "oracle-variants-v1/variants_benchmark.py", target / "variants_benchmark.py"
    )
    for p in args.fit.iterdir():
        if p.is_file():
            shutil.copyfile(p, target / p.name)
    run = (HERE.parent / "full-workload-oracle-v1/oracle_run.py").read_text()
    run = run.replace(
        "from oracle_experiment import acquire, offline, timing",
        "import oracle_experiment\nimport broad_benchmark\n"
        "from broad_benchmark import acquire, offline, timing\n"
        "oracle_experiment.reserve = broad_benchmark.reserve",
    )
    run = run.replace("with watchdog(19500):", f"with watchdog({wall - 600}):")
    old = 'counter["timed_ann"] == 7000 * 32 and counter["offline_exact"] == 7000'
    assert run.count(old) == 1
    run = run.replace(
        old, 'counter["timed_ann"] == 7000 * 48 and counter["quality_ann"] == 7000 * 12'
    )
    run = run.replace("full_workload_oracle_complete", "broad_oracle_benchmark_complete").replace(
        "FULL_WORKLOAD_ORACLE_COMPLETE", "BROAD_ORACLE_BENCHMARK_COMPLETE"
    )
    run = run.replace(
        '"exact_serving_calls": 0,',
        '"exact_serving_calls": 0, "fresh_exact_queries": 0,\n'
        f'            "source_elapsed_seconds": {args.elapsed},',
    )
    (target / "benchmark_run.py").write_text(run)
    (target / "oracle_preflight.py").write_text(
        (target / "oracle_preflight.py")
        .read_text()
        .replace('"capture_run.py"', '"benchmark_run.py"')
    )
    for old, new in (
        ("run-capture.sh", "run-benchmark.sh"),
        ("startup-capture.sh", "startup-benchmark.sh"),
        ("submit-capture.sh", "submit-benchmark.sh"),
    ):
        text = (
            (BASE / old)
            .read_text()
            .replace("capture_run.py", "benchmark_run.py")
            .replace("oracle-variants-capture-$job", "broad-oracle-benchmark-$job")
        )
        text = text.replace("run-capture.sh", "run-benchmark.sh").replace(
            "startup-capture.sh", "startup-benchmark.sh"
        )
        text = text.replace("reviews-oracle-capture", "reviews-broad-benchmark").replace(
            "--time=120", "--time=" + str(wall // 60)
        )
        text = text.replace("7110s", str(wall - 90) + "s")
        (target / new).write_text(text)
    plan = {
        "schema": "fannagent.broad-oracle.timing.v1",
        "cases": 7000,
        "heldout_cases": 1925,
        "families": 12,
        "readers": 4,
        "rotations": 12,
        "samples_per_case_family": 4,
        "timed_queries": 336000,
        "quality_queries": 84000,
        "canonical_frontier_qualification_queries": 7000,
        "warmup_queries": 3360,
        "transfer_prefix_queries_max": 5075,
        "physical_cpus": 4,
        "memory_gib": 48,
        "source_job_id": receipt["job_id"],
        "source_elapsed_seconds": args.elapsed,
        "wall_limit_seconds": wall,
        "aggregate_allocation_cap_seconds": 21600,
        "aggregate_max_seconds": args.elapsed + wall,
        "cumulative_attempt_cap": 2000000,
        "source_reserved_attempts_carried": json.loads(
            (args.capture / "reservation-final.json").read_text()
        )["charged_total"],
        "fresh_exact_queries": 0,
        "provider_calls": 0,
        "automatic_retry": False,
        "bootstrap_draws": 20000,
        "bootstrap_seed": 20261118,
        "control_band": [0.98, 1.02],
        "control_interval": 0.90,
        "hindsight_fit": True,
        "agent_generalization_claim": False,
        "schedule": (
            "family=(5*rotation+3*reader+filter_index)%12; "
            "six seeded orders mirrored; balanced reader order"
        ),
    }
    (target / "timing-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    seal(target, WORK / "broad-oracle-benchmark-v1.tar.gz")
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
