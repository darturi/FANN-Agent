"""Prepare code only; source hashes and remaining allocation budget are sealed on Torch."""

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1"
BASE = WORK / "kit-r2"
DEST = WORK / "followup-code-v1"


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    assert not DEST.exists(), "preserve earlier prepared code"
    original = json.loads((BASE / "binding.json").read_text())
    for name, expected in original["files"].items():
        assert sha(BASE / name) == expected, name
    DEST.mkdir()
    for path in BASE.iterdir():
        if path.is_file() and path.name not in ("binding.json", "SHA256SUMS", "plan.json"):
            shutil.copyfile(path, DEST / path.name)
    shutil.copyfile(BASE / "plan.json", DEST / "original-plan.json")
    for name in (
        "timing_followup.py",
        "followup_run.py",
        "followup_analyse.py",
        "finalize_followup.py",
        "run-followup.sh",
        "submit-followup.sh",
        "startup-followup.sh",
        "FOLLOWUP-PROTOCOL.md",
    ):
        shutil.copyfile(HERE / name, DEST / name)
    for name in ("oracle_run.py", "oracle_experiment.py", "oracle_design.py", "analyse.py"):
        assert sha(HERE / name) == sha(BASE / name), "original method changed: " + name
    code = {
        "status": "prepared_not_finalized_not_submitted",
        "original_binding_sha256": sha(BASE / "binding.json"),
        "files": {p.name: sha(p) for p in sorted(DEST.iterdir()) if p.is_file()},
    }
    (DEST / "code-inputs.json").write_text(json.dumps(code, indent=2, sort_keys=True) + "\n")
    archive = WORK / "oracle-followup-code-v1.tar.gz"
    with tarfile.open(archive, "x:gz") as handle:
        handle.add(DEST, arcname="oracle-followup-v1")
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        sha(archive) + "  " + archive.name + "\n"
    )
    print(json.dumps({"archive": str(archive), "sha256": sha(archive), "status": code["status"]}))


if __name__ == "__main__":
    main()
