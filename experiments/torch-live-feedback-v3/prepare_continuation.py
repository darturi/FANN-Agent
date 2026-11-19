"""Seal a budget-carrying continuation; never launch or authorize an allocation."""

import argparse
import shutil
import tarfile
from pathlib import Path

from limits import read, sha, write

HERE = Path(__file__).resolve().parent


def prepare(previous, target):
    submission = read(previous / "submission.json")
    job = submission["job_id"]
    returned = previous / ("return-" + job)
    accounting = (returned / "accounting.psv").read_text()
    row = accounting.splitlines()[0].split("|")
    if row[1:3] != ["COMPLETED", "0:0"]:
        raise ValueError("prior allocation must be terminal and audited")
    elapsed = max(int(r.split("|")[4]) for r in accounting.splitlines() if r.strip())
    state = read(returned / ("run-" + job) / "state.json")
    old_config = read(previous / "kit/config.json")
    if old_config.get("prior_allocated_seconds", 0):
        raise ValueError("this one-additional-allocation amendment is already used")
    if state["status"] != "stopped_idle":
        raise ValueError("this continuation only repairs the audited idle stop")
    disposition = read(previous / "agent-packet/live/disposition.json")
    budget = disposition["budget"]
    if budget["uncertain_calls"] or any(c["status"] != "settled" for c in budget["calls"]):
        raise ValueError("unsettled prior model charge")
    old_tools = read(previous / "agent-packet/live/tools.json")
    if old_tools["terminal"] != "worker_stopped_or_admission_closed" or old_tools["registry"]:
        raise ValueError("unexpected prior policy or decision; audit separately")
    wall = ((21600 - elapsed - 30) // 60) * 60
    if wall <= 3600:
        raise ValueError("insufficient remaining aggregate compute envelope")
    target.mkdir(parents=True)
    kit = target / "kit"
    shutil.copytree(previous / "kit", kit, copy_function=shutil.copy2)
    for name in ("measurement.py", "compile_batch.py", "analysis.py", "native_batch.py"):
        if sha(HERE / name) != sha(previous / "kit" / name):
            raise ValueError("native measurement behavior changed: " + name)
    for p in HERE.iterdir():
        if p.suffix in (".py", ".sh", ".md") or p.name == "model-profile.json":
            shutil.copyfile(p, kit / p.name)
    config = read(kit / "config.json")
    config.update(
        wall_seconds=wall,
        work_seconds=wall - 600,
        admission_seconds=wall - 1200,
        development_seconds=max(0, 10800 - elapsed),
        prior_attempts=state["attempts"],
        prior_allocated_seconds=elapsed,
    )
    write(kit / "config.json", config)
    submit = (kit / "submit.sh").read_text()
    submit = submit.replace(
        "--time=06:00:00", f"--time={wall // 3600:02d}:{wall // 60 % 60:02d}:00"
    )
    submit = submit.replace("21540s", str(wall - 60) + "s")
    submit = submit.replace("reviews-live-v3", "reviews-live-v3-r2")
    submit = submit.replace("six-hour allocation", f"{wall // 60}-minute continuation allocation")
    (kit / "submit.sh").write_text(submit)
    script = (kit / "job.sh").read_text().replace("21300s", str(wall - 300) + "s")
    (kit / "job.sh").write_text(script)
    shutil.copyfile(previous / "workspace-binding.json", target / "workspace-binding.json")
    write(
        target / "remote-stage.json",
        {
            "host": submission["host"],
            "parent": "/scratch/dar579/fannagent-benchmark-evaluation-v1/agent-v3-20261119-v2",
        },
    )
    write(
        target / "continuation-plan.json",
        {
            "status": "prepared_pending_additional_allocation_approval",
            "prior_job_id": job,
            "prior_allocated_seconds": elapsed,
            "additional_wall_seconds": wall,
            "aggregate_max_allocated_seconds": elapsed + wall,
            "aggregate_seconds_cap": 21600,
            "prior_charged_ann": state["attempts"],
            "aggregate_ann_cap": 300000,
            "carried_model_spend_usd": budget["committed_usd"],
            "model_ceiling_usd": "15",
            "carried_model_requests": len(budget["calls"]),
            "unknown_charges": 0,
            "prior_tools_sha256": sha(previous / "agent-packet/live/tools.json"),
            "prior_disposition_sha256": sha(previous / "agent-packet/live/disposition.json"),
            "workspace_binding_sha256": sha(previous / "workspace-binding.json"),
            "native_policy_language_or_primary_timer_changed": False,
            "automatic_retry": False,
            "requires_explicit_additional_allocation_approval": True,
        },
    )
    paths = sorted(p for p in kit.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (kit / "SHA256SUMS").write_text(
        "".join(sha(p) + "  " + str(p.relative_to(kit)) + "\n" for p in paths)
    )
    archive = target / "kit.tar.gz"
    with tarfile.open(archive, "x:gz") as f:
        f.add(kit, arcname="kit")
    archive.with_suffix(".gz.sha256").write_text(sha(archive) + "  " + archive.name + "\n")
    plan = read(target / "continuation-plan.json")
    plan.update(
        kit_sha256=sha(kit / "SHA256SUMS"),
        archive_sha256=sha(archive),
        remote_stage_sha256=sha(target / "remote-stage.json"),
    )
    write(target / "continuation-plan.json", plan)
    write(
        target / "preparation.json",
        {
            "status": "prepared_not_authorized_not_launched",
            "archive_sha256": sha(archive),
            "kit_sha256": sha(kit / "SHA256SUMS"),
            "continuation_plan_sha256": sha(target / "continuation-plan.json"),
            "new_allocations": 0,
            "new_model_requests": 0,
        },
    )
    return read(target / "continuation-plan.json")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--previous", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(prepare(a.previous, a.output))
