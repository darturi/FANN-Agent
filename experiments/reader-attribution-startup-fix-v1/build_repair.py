"""Deploy the unchanged attribution experiment under a non-colliding module name."""

import ast
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
ORIGINAL_ARCHIVE = "5ea46c974ea9e6e2a6d367ab72e025528e08eda9b63834e4cd1b6128d4de826f"
ORIGINAL_FREEZE = "c8e4079c62a22e22c0e831152b82c2756fd3c2e4e502e2fb20a76dd933648d73"
NEW_NAME = "reader-attribution-v1-startup-fix"


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def build():
    old = STUDY / "kits/reader-attribution-v1"
    new = STUDY / "kits" / NEW_NAME
    assert not new.exists(), "preserve existing repair evidence; do not overwrite"
    assert sha(old.with_suffix(".tar.gz")) == ORIGINAL_ARCHIVE
    assert sha(STUDY / "freeze/reader-attribution-v1.json") == ORIGINAL_FREEZE
    for line in (old / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert sha(old / name) == expected, name
    shutil.copytree(old, new)
    (new / "design.py").rename(new / "reader_attribution_design.py")
    changes = {}
    for path in sorted(new.glob("*.py")):
        source = path.read_text()
        changed = source.replace("from design import ", "from reader_attribution_design import ")
        if source != changed:
            before = ast.parse(source)
            after = ast.parse(changed)
            for node in ast.walk(before):
                if isinstance(node, ast.ImportFrom) and node.module == "design":
                    node.module = "reader_attribution_design"
            assert ast.dump(before) == ast.dump(after), path
            path.write_text(changed)
            changes[path.name] = {"before": sha(old / path.name), "after": sha(path)}
    assert set(changes) == {"experiment.py", "verify_return.py", "analyse.py"}
    shutil.copyfile(HERE / "startup_preflight.py", new / "startup_preflight.py")
    shutil.copyfile(HERE / "startup-preflight.sh", new / "startup-preflight.sh")
    submit = new / "submit.sh"
    original_submit = submit.read_text()
    marker = '/opt/slurm/bin/sbatch --test-only "${args[@]}"'
    assert original_submit.count(marker) == 1
    submit.write_text(original_submit.replace(marker, "bash ./startup-preflight.sh\n" + marker))
    metadata = {
        "schema": "reader-attribution-startup-repair.v1",
        "failed_job_id": "23074287",
        "scheduler_state": "FAILED",
        "scheduler_exit_code": "1:0",
        "failure": "frozen loader rejects diagnostic's already-imported design module",
        "evidence_source": "user-pasted scheduler/log output; failed archive verification pending",
        "original_archive_sha256": ORIGINAL_ARCHIVE,
        "original_freeze_sha256": ORIGINAL_FREEZE,
        "changed_python_files": changes,
        "rename": {
            "from": "design.py",
            "to": "reader_attribution_design.py",
            "content_sha256": sha(old / "design.py"),
        },
        "additional_preflight": sha(new / "startup_preflight.py"),
        "additional_native_preflight_launcher": sha(new / "startup-preflight.sh"),
        "submit_change": {
            "before": sha(old / "submit.sh"),
            "after": sha(submit),
            "only_change": "require both native startup preflights before sbatch",
        },
        "serving_timing_work_modules_changed": False,
        "schedule_policies_data_filters_scoring_analysis_changed": False,
        "binding_sha256_unchanged": sha(old / "binding.json"),
        "old_kit_and_failed_run_preserved": True,
        "provider_calls": 0,
        "validation_test_outcomes_opened": False,
        "automatic_submission": False,
    }
    (new / "startup-repair.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    # Every original artifact except the namespace-only imports must remain identical.
    for path in old.iterdir():
        if not path.is_file() or path.name in {*changes, "SHA256SUMS", "submit.sh"}:
            continue
        target = new / ("reader_attribution_design.py" if path.name == "design.py" else path.name)
        assert sha(path) == sha(target), path
    seal_sums(new)
    print(json.dumps({"kit": str(new), "changes": metadata}, indent=2))


def seal_sums(kit):
    (kit / "SHA256SUMS").write_text(
        "".join(
            sha(path) + "  " + path.name + "\n"
            for path in sorted(kit.iterdir())
            if path.is_file() and path.name != "SHA256SUMS"
        )
    )


if __name__ == "__main__":
    build()
