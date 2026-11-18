"""Prepare a new kit from verified M5 inputs. Never upload, submit or call a provider."""

import argparse
import shutil
import tarfile
from pathlib import Path

from limits import FILTERS, SCHEMA, SCREEN_GROUPS, digest, read, sha, write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = (
    ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/m5-policy-qualification-v1"
)


def package(target):
    for line in (SOURCE / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if Path(name).name != name or sha(SOURCE / name) != expected:
            raise ValueError("sealed M5 source changed: " + name)
    target.mkdir(parents=True, exist_ok=False)
    for path in HERE.iterdir():
        if path.suffix in (".py", ".sh", ".md") or path.name in (
            "COMMANDS.txt",
            "verification.json",
        ):
            shutil.copyfile(path, target / path.name)
    if (HERE / "checks").is_dir():
        shutil.copytree(HERE / "checks", target / "checks")
    for name in (
        "original-package.tar.gz",
        "queries.jsonl",
        "expected.jsonl",
        "prior-references.jsonl",
    ):
        shutil.copyfile(SOURCE / name, target / name)
    binding = read(SOURCE / "binding.json")
    diagnostics = [n["policy"] for n in read(SOURCE / "nominees.json")["nominees"]]
    write(target / "diagnostic-policies.json", diagnostics)
    write(
        target / "source-binding.json",
        {
            "M5_binding_sha256": sha(SOURCE / "binding.json"),
            "graph": binding["graph"],
            "development_source_indices": binding["development_source_indices"],
            "split_manifest_sha256": binding["split_manifest_sha256"],
            "original_manifest_sha256": (
                "b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc"
            ),
        },
    )
    measurement = target / "measurement"
    measurement.mkdir()
    for name in (
        "m5_experiment.py",
        "m5_design.py",
        "common.py",
        "support.py",
        "sessions.py",
        "serving.py",
        "startup.py",
        "functions.sql",
    ):
        shutil.copyfile(SOURCE / name, measurement / name)
    sources = target / ".engine-sources"
    with tarfile.open(SOURCE / "engine-sources.tar.gz") as archive:
        archive.extractall(sources, filter="data")
    shutil.move(str(sources / "engine"), target / "engine")
    shutil.rmtree(sources)
    shutil.copytree(
        ROOT / "agent/src/fannagent",
        target / "src/fannagent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        HERE.parent / "filtered-ann-protocol-v2/fannproto",
        target / "protocol/fannproto",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    write(
        target / "config.json",
        {
            "schema": "fannagent.torch-live.v1",
            "wall_seconds": 21600,
            "admission_seconds": 18900,
            "work_seconds": 20400,
            "idle_seconds": 900,
            "attempt_limit": 300000,
            "cpus": 4,
            "memory_gib": 48,
            "screen_groups": SCREEN_GROUPS,
            "conditions": FILTERS,
            "image": "/home/dar579/torch-reviews-first/images/runtime.sif",
            "image_sha256": "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a",
            "bundle": "/home/dar579/torch-reviews-first",
            "prepared": (
                "/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286"
            ),
            "model_calls_on_Torch": 0,
            "qualification_payload_sha256": digest({"schema": SCHEMA, "policies": diagnostics}),
            "automatic_retry": False,
            "automatic_requeue": False,
        },
    )
    paths = sorted(p for p in target.rglob("*") if p.is_file())
    (target / "SHA256SUMS").write_text(
        "".join(sha(path) + "  " + path.relative_to(target).as_posix() + "\n" for path in paths)
    )
    archive_path = target.with_suffix(".tar.gz")
    if archive_path.exists():
        raise FileExistsError(archive_path)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(target, arcname=target.name)
    archive_path.with_suffix(archive_path.suffix + ".sha256").write_text(
        sha(archive_path) + "  " + archive_path.name + "\n"
    )
    return archive_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    print(package(parser.parse_args().output))
