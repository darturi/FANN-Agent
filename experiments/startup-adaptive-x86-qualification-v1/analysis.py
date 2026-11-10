"""Trusted data-only native return verification; never imports returned code."""

import argparse
import math
import re
from pathlib import Path

from common import read, save, sha, verify
from proofs import validate


def lock(root, name, excluded):
    p = Path(root)
    v = read(p / name)
    if v["complete"] is not True:
        raise ValueError("Incomplete lock: " + name)
    actual = {str(f.relative_to(p)) for f in p.rglob("*") if f.is_file() and not excluded(f)}
    if set(v["files"]) != actual:
        raise ValueError("Lock coverage differs: " + name)
    for n, h in v["files"].items():
        rel = Path(n)
        if rel.is_absolute() or ".." in rel.parts or sha(p / rel) != h:
            raise ValueError("Lock bytes/path differ")
    return v


def analyze(campaign, package):
    campaign = Path(campaign)
    package = Path(package)
    c = verify(package)
    run = campaign / "run"
    submission = read(campaign / "submission.json")
    job = submission["job_id"]
    if (
        not re.fullmatch(r"[1-9][0-9]*", job)
        or submission["package_manifest_sha256"] != sha(package / "manifest.json")
        or submission["dispatch"] != {"status": "submitted", "job_id": job}
    ):
        raise ValueError("Submission/capsule identity differs")
    sched = read(campaign / "scheduler-evidence.json")
    rows = [line.split("|") for line in sched["sacct_stdout"].splitlines()]
    if sched["terminal_verified"] is not True or not any(
        len(r) >= 3 and r[0] == job and r[1] == "COMPLETED" and r[2] == "0:0" for r in rows
    ):
        raise ValueError("Successful terminal native allocation proof required")
    if any(p.is_symlink() for p in campaign.rglob("*")):
        raise ValueError("Returned symlink")
    lock(run, "HOST-LOCK.json", lambda p: p.name == "HOST-LOCK.json")
    lock(
        run,
        "GUEST-LOCK.json",
        lambda p: (
            p.name.startswith("host-")
            or p.name in ("GUEST-LOCK.json", "HOST-LOCK.json", "guest-terminal.json")
        ),
    )
    status = read(run / "status.json")
    host = read(run / "host-exit.json")
    launch = read(run / "host-launch.json")
    integrity = read(run / "host-integrity.json")
    if (
        status["status"] != "complete"
        or status["exit_code"] != 0
        or host["exit_code"] != 0
        or host["job_id"] != job
        or launch["job_id"] != job
    ):
        raise ValueError("Native completion failed")
    if (
        integrity["status"] != "pass"
        or integrity["manifest_sha256"] != sha(package / "manifest.json")
        or integrity["image_sha256"] != c["image_sha256"]
    ):
        raise ValueError("Final source/image preservation failed")
    for path in (
        [run / "host-launch.json", run / "guest-hardware.json"]
        + [
            run / (k + "-" + phase) / "hardware.json"
            for k in ("main", "a3")
            for phase in ("source", "sealed")
        ]
        + [run / "cpu/hardware.json"]
    ):
        h = read(path)
        h = h.get("hardware", h)
        if (
            h["machine"] != "x86_64"
            or h["elf_machine"] != 62
            or h["vendor"] not in ("GenuineIntel", "AuthenticAMD")
            or h["emulation_detected"] is not False
            or len(h["selected"]) != 4
            or len(set(tuple(v) for v in h["physical_pairs"])) != 4
        ):
            raise ValueError("Native physical x86 evidence differs")
    t = read(run / "guest-timing.json")
    terminal = read(run / "guest-terminal.json")
    ht = read(run / "host-timing.json")
    if set(v["phase"] for v in t["phases"]) != set(c["phase_seconds"]):
        raise ValueError("Complete phase accounting required")
    for value in [
        t["started"],
        t["deadline"],
        t["finished"],
        terminal["finished"],
        terminal["publication_deadline"],
        ht["started"],
        ht["finished"],
        ht["post_deadline"],
        ht["guest_deadline"],
    ]:
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("Finite native timing required")
    for phase in t["phases"]:
        cap = c["phase_seconds"][phase["phase"]]
        if (
            phase["status"] != "pass"
            or not 0 <= phase["elapsed_seconds"] <= cap
            or phase["deadline"] != phase["started"] + cap
        ):
            raise ValueError("Phase cap/proof failed")
    if (
        terminal["exit_code"] != 0
        or terminal["finished"] >= terminal["publication_deadline"]
        or terminal["publication_deadline"] != t["cleanup_publication_deadline"]
        or terminal["finished"] - t["started"] > 3000
    ):
        raise ValueError("Cleanup publication/runtime budget failed")
    if (
        ht["finished"] >= ht["post_deadline"]
        or ht["post_deadline"] != ht["started"] + 3480
        or ht["guest_deadline"] != ht["started"] + 3240
    ):
        raise ValueError("Whole host envelope failed")
    result = validate(run, package / "workspace", c, "target")
    result.update(
        native_capsule_manifest_sha256=sha(package / "manifest.json"),
        job_id=job,
        all_spent_allowances_closed=True,
        new_qualification_allowance="spent by this allocation; no retry",
        native_resource_release=False,
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--campaign", type=Path, required=True)
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    save(a.output, analyze(a.campaign, a.package))
