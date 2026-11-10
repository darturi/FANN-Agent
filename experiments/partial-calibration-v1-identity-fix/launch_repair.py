"""Verify the completed pre-Python failure; no automatic additional allocation."""

import hashlib
import json
import tarfile
from pathlib import Path

from pc_common import COUNTS, read, safe_file, sha

ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
OLD = ROOT / "trials/torch-reviews-partial-calibration-v1"
OUTPUT = ROOT / "trials/torch-reviews-partial-calibration-v1-launch-fix"
CAMPAIGN = "reviews-partial-calibration-v1-20261027T155119Z.6rd0lmkp"
MANIFEST = "41b4e47890ee1134eabbd1836a628954e93ee91e7e7fafb29da63e4da68ae42a"


def verify_failure():
    archive = OLD / (CAMPAIGN + ".tar.gz")
    campaign = OLD / "returned" / CAMPAIGN
    if Path(str(archive) + ".sha256").read_text().split() != [sha(archive), archive.name]:
        raise ValueError("Failed archive checksum differs")
    original = OLD / "torch-partial-calibration-v1"
    if sha(original / "manifest.json") != MANIFEST:
        raise ValueError("Original B2f seal differs")
    for name, h in read(original / "manifest.json")["files"].items():
        if sha(safe_file(original, name)) != h:
            raise ValueError("Failed B2f package changed")
    raw = {}
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar.getmembers():
            rel = Path(m.name)
            if not m.isfile() or rel.parts[0] != CAMPAIGN:
                raise ValueError("Unsafe failure archive")
            key = str(rel.relative_to(CAMPAIGN))
            if key in raw:
                raise ValueError("Duplicate failure member")
            h = hashlib.sha256(tar.extractfile(m).read()).hexdigest()
            if sha(safe_file(campaign, key)) != h:
                raise ValueError("Failed extraction differs")
            raw[key] = h
    if raw != {str(f.relative_to(campaign)): sha(f) for f in campaign.rglob("*") if f.is_file()}:
        raise ValueError("Failed raw inventory differs")
    if any(n.startswith("run/") for n in raw):
        raise ValueError("Runtime evidence exists; pre-Python-only repair scope invalid")
    record = read(campaign / "submission.json")
    if (
        record["package_manifest_sha256"] != MANIFEST
        or record["counts"] != COUNTS
        or record["jobs"] != {"block-0": "21111616"}
        or Path(record["campaign"]).name != CAMPAIGN
    ):
        raise ValueError("Failed submission identity differs")
    log = (campaign / "logs/block-0-21111616-0.log").read_text()
    if not all(
        s in log
        for s in (
            "execve(): python3: No such file or directory",
            "task 0: Exited with exit code 2",
            "StepId=21111616.0",
        )
    ):
        raise ValueError("Different launcher failure")
    accounting = read(campaign / "scheduler-evidence.json")["sacct_stdout"]
    if not any(
        line.split("|")[:3] == ["21111616_0", "FAILED", "2:0"] for line in accounting.splitlines()
    ):
        raise ValueError("Failed terminal scheduler evidence missing")
    result = dict(
        status="verified_pre_python_launch_failure",
        campaign=CAMPAIGN,
        job="21111616_0",
        archive_sha256=sha(archive),
        original_package_manifest_sha256=MANIFEST,
        archive_files=len(raw),
        raw_files_sha256=raw,
        experiment_python_started=False,
        native_searches=0,
        allocation_spent=True,
        calibration_verdict=False,
        correction_scope=(
            "absolute host interpreter plus explicit srun environment; unchanged scientific design"
        ),
        automatic_retry_authorized=False,
    )
    target = OUTPUT / "failed-archive-verification.json"
    if target.exists():
        if read(target) != result:
            raise ValueError("Existing verification differs")
    else:
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(verify_failure(), indent=2))
