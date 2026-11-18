"""First primary timing allocation, four repetitions for every case and family."""

import json
import os
import sys
from pathlib import Path

import balanced_source
import oracle_experiment
import oracle_run
import timing_followup
from common import sha, write
from oracle_design import require

HERE = Path(__file__).resolve().parent


def main():
    plan = json.loads((HERE / "timing-plan.json").read_text())
    require(plan["source_elapsed_seconds"] + plan["wall_limit_seconds"] <= 21600, "aggregate limit")
    source = Path("/acquisition")
    require(os.statvfs(source).f_flag & os.ST_RDONLY, "source must be read-only")
    manifest = json.loads((HERE / "source-acquisition.json").read_text())
    for name, expected in manifest["files"].items():
        require(sha(source / name) == expected, "source changed: " + name)
    if sys.argv[1:] == ["--check-only"]:
        print(json.dumps({"status": "balanced_source_hashes_passed", "SQL_queries": 0}))
        return
    import rb_native

    original_watchdog = rb_native.watchdog
    rb_native.watchdog = lambda seconds: original_watchdog(min(seconds, plan["watchdog_seconds"]))
    original_timing = oracle_run.timing

    def measured(*args):
        original_timing(*args)
        _, execution_args, _, _, _, counter = args
        execution_args.window_ledger.finish(counter)

    oracle_experiment.reserve = timing_followup.reserve
    oracle_run.offline = balanced_source.load_source
    oracle_run.acquire = balanced_source.reuse_choices
    oracle_run.timing = measured
    oracle_run.main()
    output = Path(sys.argv[sys.argv.index("--output") + 1])
    receipt = json.loads((output / "receipt.json").read_text())
    receipt.update(
        status="full_workload_oracle_balanced_timing_complete",
        acquisition_job_ids=["23544718", "23558871"],
        timing_allocations=1,
        acquisition_allocations=2,
        total_allocations=3,
        fresh_exact_queries=0,
        fresh_qualification_queries=0,
        repetitions_per_case_family=4,
        cycles=1,
        source_elapsed_seconds=plan["source_elapsed_seconds"],
        aggregate_allocation_limit_seconds=21600,
        ledger_includes_prior_uncertain_and_unused_charges=True,
        fresh_replay_checks="all warmup and timed answers; every case/family",
    )
    receipt["raw_sha256"] = {
        str(p.relative_to(output)): sha(p)
        for p in output.rglob("*")
        if p.is_file() and p.name != "receipt.json"
    }
    write(output / "receipt.json", receipt)
    print("FULL_WORKLOAD_ORACLE_BALANCED_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
