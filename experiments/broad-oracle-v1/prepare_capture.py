"""Seal the prospective v3 causal acquisition before dispatch."""

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
WORK = STUDY / "broad-oracle-v1"
BASE = STUDY / "oracle-variants-v1/capture-kit-v2"


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def seal(target, archive):
    graph = json.loads((BASE / "binding.json").read_text())["graph"]
    (target / "binding.json").write_text(
        json.dumps(
            {
                "schema": "fannagent.broad-oracle.binding.v1",
                "graph": graph,
                "files": {
                    p.name: sha(p)
                    for p in sorted(target.iterdir())
                    if p.is_file() and p.name not in ("binding.json", "SHA256SUMS")
                },
            },
            indent=2,
        )
        + "\n"
    )
    (target / "SHA256SUMS").write_text(
        "".join(
            sha(p) + "  " + p.name + "\n"
            for p in sorted(target.iterdir())
            if p.is_file() and p.name != "SHA256SUMS"
        )
    )
    with tarfile.open(archive, "x:gz") as handle:
        handle.add(target, arcname=archive.name.removesuffix(".tar.gz"))
    archive.with_suffix(".gz.sha256").write_text(sha(archive) + "  " + archive.name + "\n")


def main():
    runtime = WORK / "capture-runtime-v3"
    target = WORK / "capture-kit-v1"
    target.mkdir()
    for p in BASE.iterdir():
        if p.is_file() and p.name not in ("binding.json", "SHA256SUMS"):
            shutil.copyfile(p, target / p.name)
    for name in ("broad_capture.py", "broad_support.py", "PROTOCOL.md"):
        shutil.copyfile(HERE / name, target / name)
    for name in ("functions.sql", "broad_contract.py", "compiled-v3.json"):
        shutil.copyfile(runtime / name, target / name)
    shutil.copyfile(runtime / "engine/vector.so", target / "oracle-module.so")
    shutil.copyfile(WORK / "capture-bindings.json", target / "capture-bindings.json")
    with tarfile.open(target / "engine-sources.tar.gz", "w:gz") as handle:
        for p in sorted((runtime / "engine").rglob("*")):
            if p.is_file() and p.suffix not in (".o", ".bc", ".so"):
                handle.add(p, arcname="engine/" + str(p.relative_to(runtime / "engine")))
    run = (target / "capture_run.py").read_text().replace("variants_capture", "broad_capture")
    run = run.replace(
        'and counter["native_bridge"] == 14000 and counter["ideal_replay"] == 7000',
        'and counter["native_bridge"] == 14000 and counter["broad_capture"] == 7000',
    )
    run = run.replace("oracle_variants_capture_complete", "broad_oracle_capture_complete").replace(
        "ORACLE_VARIANTS_CAPTURE_COMPLETE", "BROAD_ORACLE_CAPTURE_COMPLETE"
    )
    (target / "capture_run.py").write_text(run)
    for name in ("run-capture.sh", "startup-capture.sh", "submit-capture.sh"):
        text = (
            (target / name)
            .read_text()
            .replace("oracle-variants-capture-$job", "broad-oracle-capture-$job")
            .replace("reviews-oracle-capture", "reviews-broad-capture")
        )
        (target / name).write_text(text)
    (target / "plan.json").write_text(
        json.dumps(
            {
                "schema": "fannagent.broad-oracle.capture.v1",
                "cases": 7000,
                "heldout_cases": 1925,
                "physical_cpus": 4,
                "memory_gib": 48,
                "wall_limit_seconds": 7200,
                "watchdog_seconds": 6300,
                "maximum_fresh_queries": 28000,
                "fresh_exact_queries": 0,
                "provider_calls": 0,
                "new_comparison_aggregate_seconds_cap": 21600,
                "new_comparison_attempt_cap": 2000000,
                "automatic_retry": False,
                "core_sha256": sha(runtime / "broad_contract.py"),
                "module_sha256": sha(runtime / "engine/vector.so"),
            },
            indent=2,
        )
        + "\n"
    )
    seal(target, WORK / "broad-oracle-capture-v1.tar.gz")
    print(target)


if __name__ == "__main__":
    main()
