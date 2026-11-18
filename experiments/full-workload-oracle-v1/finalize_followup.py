"""Seal the prepared followup only after the original acquisition has stopped safely."""

import hashlib
import json
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path(
    "/scratch/dar579/fannagent-benchmark-evaluation-v1/oracle-headroom-20261117-v1/full-workload-oracle-v1"
)
JOB = "23544718"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def main():
    assert not (HERE / "binding.json").exists(), "followup already sealed; preserve it"
    code = json.loads((HERE / "code-inputs.json").read_text())
    for name, expected in code["files"].items():
        assert sha(HERE / name) == expected, "prepared code changed: " + name
    rows = subprocess.check_output(
        [
            "/opt/slurm/bin/sacct",
            "--local",
            "-n",
            "-P",
            "-j",
            JOB,
            "--format=JobIDRaw,State,ExitCode,ElapsedRaw",
        ],
        text=True,
    ).splitlines()
    row = next(r.split("|") for r in rows if r.split("|")[0] == JOB)
    assert row[1] in ("FAILED", "CANCELLED", "COMPLETED"), "source still active"
    elapsed = int(row[3])
    minutes = (21600 - elapsed - 120) // 60
    assert minutes >= 30, "less than30 minutes remains in aggregate six-hour envelope"
    wall = min(150 * 60, minutes * 60)
    results = SOURCE / ("run-" + JOB) / "results"
    handoff = json.loads((SOURCE.parent / "handoff-signal.json").read_text())
    assert handoff["job_id"] == JOB and handoff["signal_sent"] is True
    host = json.loads((results / "host-exit.json").read_text())
    assert host["job_id"] == JOB and host["exit_code"] != 0
    assert (SOURCE / ("run-" + JOB) / ("oracle-" + JOB + ".tar.gz.sha256")).is_file()
    names = (
        "exact-reference.jsonl",
        "quality.jsonl",
        "prefixes.jsonl",
        "trajectories.jsonl",
        "eligibility.json",
        "attempts.json",
    )
    files = {name: sha(results / name) for name in names}
    if (results / "attempts.pending").exists():
        files["attempts.pending"] = sha(results / "attempts.pending")
    usage = json.loads((results / "attempts.json").read_text())
    assert (
        usage["offline_exact"] == 7000
        and usage.get("timed_ann", 0) == usage.get("warmup_ann", 0) == 0
    )
    torn = []
    complete = 0
    for name in ("quality.jsonl", "prefixes.jsonl", "trajectories.jsonl"):
        with (results / name).open() as handle:
            for line in handle:
                try:
                    json.loads(line)
                    complete += name == "quality.jsonl"
                except json.JSONDecodeError:
                    assert not line.endswith("\n") and handle.read(1) == ""
                    torn.append(name)
    assert 0 < complete < 7000, "expected a partial acquisition handoff"
    source_binding = json.loads((SOURCE / "binding.json").read_text())
    assert sha(SOURCE / "binding.json") == code["original_binding_sha256"]
    manifest = {
        "schema": "fannagent.oracle.partial-acquisition.v1",
        "job_id": JOB,
        "partial_acquisition": True,
        "completed_cases": complete,
        "files": files,
        "source_binding_sha256": sha(SOURCE / "binding.json"),
        "unpublished_reservation_charged": (results / "attempts.pending").exists(),
        "source_scheduler": row,
        "handoff": handoff,
        "source_timings_exist": False,
        "torn_final_record_files": torn,
        "source_results": str(results),
    }
    write(HERE / "source-acquisition.json", manifest)
    plan = {
        "schema": "fannagent.oracle.bookkeeping-followup.v1",
        "sealed_utc": datetime.now(timezone.utc).isoformat(),  # noqa: UP017 - host Python3.9
        "source_job": JOB,
        "source_elapsed_seconds": elapsed,
        "wall_limit_seconds": wall,
        "watchdog_seconds": wall - 300,
        "aggregate_allocation_limit_seconds": 21600,
        "physical_cpus": 4,
        "memory_gib": 48,
        "new_allocations": 1,
        "automatic_retry": False,
        "provider_calls": 0,
        "reservation_window": 1024,
        "cumulative_attempt_cap": 2000000,
        "source_partial_completed_cases": complete,
        "full_cases": 7000,
        "heldout_cases": 1925,
        "retain_all_source_results": True,
        "remeasure_only_unfinished_cases": True,
        "serving_timings_in_one_new_allocation": True,
        "oracle_criterion_engine_query_timer_schedule_statistics_unchanged": True,
    }
    write(HERE / "followup-plan.json", plan)
    original_plan = json.loads((HERE / "original-plan.json").read_text())
    write(HERE / "plan.json", {**original_plan, "allocations": 2, "amendment": plan})
    write(
        HERE / "binding.json",
        {
            "schema": "fannagent.oracle.followup-binding.v1",
            "graph": source_binding["graph"],
            "source_binding_sha256": sha(SOURCE / "binding.json"),
            "files": {
                p.name: sha(p)
                for p in sorted(HERE.iterdir())
                if p.is_file() and p.name not in ("SHA256SUMS", "binding.json")
            },
        },
    )
    (HERE / "SHA256SUMS").write_text(
        "".join(
            sha(p) + "  " + p.name + "\n"
            for p in sorted(HERE.iterdir())
            if p.is_file() and p.name != "SHA256SUMS"
        )
    )
    archive = HERE.parent / "oracle-followup-sealed-v1.tar.gz"
    with tarfile.open(archive, "x:gz") as handle:
        handle.add(HERE, arcname="oracle-followup-v1")
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        sha(archive) + "  " + archive.name + "\n"
    )
    print(
        json.dumps(
            {
                "status": "sealed",
                "source_cases": complete,
                "source_elapsed_seconds": elapsed,
                "new_wall_limit_seconds": wall,
                "aggregate_max_seconds": elapsed + wall,
                "archive_sha256": sha(archive),
            }
        )
    )


if __name__ == "__main__":
    main()
