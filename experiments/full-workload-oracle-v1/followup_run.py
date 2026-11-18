"""Prospectively amended timing-only pass; original module and serving loop unchanged."""

import json
import os
import sys
from pathlib import Path

import oracle_experiment
import oracle_run
import timing_followup
from common import sha, write
from oracle_design import require

HERE = Path(__file__).resolve().parent


def main():
    plan = json.loads((HERE / "followup-plan.json").read_text())
    require(
        plan["source_elapsed_seconds"] + plan["wall_limit_seconds"] <= 21600,
        "aggregate six-hour allocation envelope exceeded",
    )
    require(0 < plan["watchdog_seconds"] < plan["wall_limit_seconds"], "invalid watchdog")
    source = Path("/acquisition")
    require(os.statvfs(source).f_flag & os.ST_RDONLY, "source acquisition must be read-only")
    manifest = json.loads((HERE / "source-acquisition.json").read_text())
    for name, expected in manifest["files"].items():
        require(sha(source / name) == expected, "source file changed: " + name)
    if sys.argv[1:] == ["--check-only"]:
        print(
            json.dumps(
                {
                    "status": "followup_source_hashes_passed",
                    "SQL_queries": 0,
                    "source_job": manifest["job_id"],
                    "fresh_timing_allocations": 1,
                }
            )
        )
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
    oracle_run.offline = timing_followup.load_acquisition
    oracle_run.acquire = timing_followup.resume_and_qualify
    oracle_run.timing = measured
    oracle_run.main()
    output = Path(sys.argv[sys.argv.index("--output") + 1])
    receipt = json.loads((output / "receipt.json").read_text())
    receipt["status"] = "full_workload_oracle_timing_followup_complete"
    receipt["acquisition_job_id"] = manifest["job_id"]
    receipt["acquisition_manifest_sha256"] = sha(HERE / "source-acquisition.json")
    receipt["fresh_exact_queries"] = 0
    receipt["fresh_qualification_queries"] = 28000
    receipt["timing_allocations"] = 1
    receipt["acquisition_allocations"] = 2
    receipt["source_elapsed_seconds"] = plan["source_elapsed_seconds"]
    receipt["aggregate_allocation_limit_seconds"] = 21600
    receipt["raw_sha256"] = {
        str(p.relative_to(output)): sha(p)
        for p in output.rglob("*")
        if p.is_file() and p.name != "receipt.json"
    }
    write(output / "receipt.json", receipt)
    print("FULL_WORKLOAD_ORACLE_FOLLOWUP_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
