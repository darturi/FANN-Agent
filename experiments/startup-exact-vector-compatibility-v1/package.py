"""Seal the finite native correctness capsule; safe data-only return ingestion."""

import argparse
import re
import shutil
import tarfile
from pathlib import Path

from common import MAIN, NAME, PREFIX, ROOT, read, save, sha, verify

HERE = Path(__file__).resolve().parent
OUTPUT = ROOT / "trials/torch-reviews-startup-exact-vector-compatibility-v1"
PARENT = ROOT / "trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1"


def build(output=OUTPUT, testing=False):
    output = Path(output)
    output.mkdir(exist_ok=True, parents=True)
    p = output / NAME
    if p.exists():
        raise FileExistsError("Preserve existing capsule")
    contract = read(HERE / "COMPATIBILITY-CONTRACT.json")
    checks = read(
        ROOT
        / "trials/torch-reviews-startup-attribution-v1-image-reference/local-checks-source.json"
    )
    if (
        checks["status"] != "pass"
        or checks["tests_run"] != 128
        or checks["recipe_files_sha256"] != contract["main_recipe_files_sha256"]
    ):
        raise RuntimeError("Current main source readiness required")
    if not testing:
        local = read(OUTPUT / "local-checks-source.json")
        if local["status"] != "pass" or local["source_files_sha256"] != {
            f.name: sha(f) for f in HERE.glob("*.py")
        }:
            raise RuntimeError("Current compatibility source checks required")
    p.mkdir()
    for f in HERE.iterdir():
        if f.is_file() and f.name not in ("manifest.json", "submission-binding.json"):
            shutil.copyfile(f, p / f.name)
    source = p / "workspace/agent/experiments/startup-attribution-v1-image-reference"
    source.mkdir(parents=True)
    for n, h in contract["main_recipe_files_sha256"].items():
        if sha(MAIN / n) != h:
            raise ValueError("Main source differs: " + n)
        shutil.copyfile(MAIN / n, source / n)
    parent = (
        p / "workspace/trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1"
    )
    shutil.copytree(PARENT, parent)
    baseline = parent.parent / "baseline-regression.json"
    shutil.copyfile(PARENT.parent / "baseline-regression.json", baseline)
    first = p / "workspace/trials/torch-reviews-first"
    first.mkdir(parents=True)
    for n, expected in contract["fixture_dependency_files_sha256"].items():
        if sha(ROOT / "trials/torch-reviews-first" / n) != expected:
            raise ValueError("Offline constructor dependency changed: " + n)
        (first / n).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "trials/torch-reviews-first" / n, first / n)
    alias = (
        p
        / "workspace/trials/torch-reviews-startup-resource-stream-v1"
        / "torch-startup-resource-stream-v1"
    )
    alias.mkdir(parents=True)
    (alias / ".read-only-A1-native-file-alias").write_text(
        "Mounted to byte-identical original frozen native files; test path alias only.\n"
    )
    for key, directory in (
        ("integration_files_sha256", contract["integration_source"]),
        ("prototype_files_sha256", contract["prototype_source"]),
        ("reference_files_sha256", contract["reference_view"]),
    ):
        target = p / "workspace" / directory
        target.mkdir(parents=True, exist_ok=True)
        for name, expected in contract[key].items():
            original = ROOT / directory / name
            if sha(original) != expected:
                raise ValueError("A3 input changed: " + name)
            shutil.copyfile(original, target / name)
    view = p / "workspace" / contract["reference_view"] / "frozen"
    view.mkdir()
    (view / "REFERENCE-MOUNT.txt").write_text(
        "Native host binds original frozen files here read-only. Not a runnable A2 package.\n"
    )
    frozen = p / "workspace/trials/torch-reviews-startup-exact-vector-v1"
    frozen.mkdir(parents=True)
    shutil.copyfile(
        ROOT / "trials/torch-reviews-startup-exact-vector-v1/A3-FREEZE.json",
        frozen / "A3-FREEZE.json",
    )
    save(
        p / "manifest.json",
        dict(
            schema=contract["schema"],
            files={str(f.relative_to(p)): sha(f) for f in sorted(p.rglob("*")) if f.is_file()},
        ),
    )
    verify(p)
    archive = output / (NAME + ".tar.gz")
    with tarfile.open(archive, "x:gz") as tar:
        for f in sorted(p.rglob("*")):
            if f.is_file():
                tar.add(f, arcname=NAME + "/" + str(f.relative_to(p)), recursive=False)
    with Path(str(archive) + ".sha256").open("x") as f:
        f.write(sha(archive) + "  " + archive.name + "\n")
    return p


def ingest(archive, package=OUTPUT / NAME):
    verify(package)
    archive = Path(archive)
    if Path(str(archive) + ".sha256").read_text().split() != [sha(archive), archive.name]:
        raise ValueError("Archive checksum differs")
    rootname = archive.name.removesuffix(".tar.gz")
    if not re.fullmatch(re.escape(PREFIX) + r"[0-9]{8}T[0-9]{6}Z\.[A-Za-z0-9_-]+", rootname):
        raise ValueError("Unexpected campaign name")
    destination = OUTPUT / "returned"
    destination.mkdir(exist_ok=True)
    root = destination / rootname
    if root.exists():
        raise FileExistsError("Preserve existing complete/partial return")
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        names = set()
        if len(members) > 128 or sum(m.size for m in members) > 16 * 1024**2:
            raise ValueError("Returned evidence cap")
        for m in members:
            path = Path(m.name)
            if (
                not m.isfile()
                or m.name in names
                or path.is_absolute()
                or ".." in path.parts
                or path.parts[0] != rootname
            ):
                raise ValueError("Unsafe return member")
            names.add(m.name)
        for m in members:
            dest = destination / m.name
            dest.parent.mkdir(exist_ok=True, parents=True)
            with tar.extractfile(m) as src, dest.open("xb") as dst:
                shutil.copyfileobj(src, dst)
    submission = read(root / "submission.json")
    if Path(submission["campaign"]).name != rootname or submission[
        "package_manifest_sha256"
    ] != sha(package / "manifest.json"):
        raise ValueError("Returned submission identity differs")
    if not (root / "run/host-exit.json").exists() or read(root / "run/host-exit.json")["exit_code"]:
        print(
            "Failed/incomplete native compatibility return preserved: "
            + str(root)
            + "; no main A2 release or retry."
        )
        return
    lock = read(root / "run/LOCK.json")
    if not lock["complete"]:
        raise ValueError("Incomplete lock")
    for n, h in lock["files"].items():
        rel = Path(n)
        if rel.is_absolute() or ".." in rel.parts or sha(root / "run" / rel) != h:
            raise ValueError("Raw lock differs")
    if read(root / "run/host-integrity.json")["status"] != "pass":
        raise ValueError("Native final source/image integrity unqualified")
    c = read(package / "COMPATIBILITY-CONTRACT.json")
    expected_code = {**c["integration_files_sha256"], **c["prototype_files_sha256"]}
    image_reference = read(package / "workspace" / c["reference_view"] / "IMAGE-REFERENCE.json")
    for phase in ("source", "sealed"):
        receipt = read(root / "run" / ("integration-" + phase + ".json"))
        guard = read(root / "run" / ("integration-guard-" + phase + ".json"))
        if (
            receipt["status"] != "pass"
            or receipt["tests_run"] != c["integration_tests"]
            or receipt["source_files_sha256"] != expected_code
            or not receipt["source_stable"]
            or not receipt["runtime_reference_pass"]
            or receipt["actual_provenance"] != image_reference
            or receipt["failures"]
            or receipt["errors"]
            or receipt["skipped"]
            or receipt["python"] != "3.12.15"
            or receipt["denied_actions"]
            or guard["exit_code"]
            or guard["error"] is not None
            or guard["denied_connections"]
            or guard["denied_subprocesses"]
            or not guard["connection_bindings_restored"]
        ):
            raise ValueError("A3 integrated source/sealed target proof differs")
    expected = read(package / "COMPATIBILITY-CONTRACT.json")["main_recipe_files_sha256"]
    target = read(
        package
        / "workspace/agent/experiments/startup-attribution-v1-image-reference/IMAGE-REFERENCE.json"
    )
    for phase in ("source", "sealed"):
        r = read(root / "run" / ("target-checks-" + phase + ".json"))
        g = read(root / "run" / ("guard-" + phase + ".json"))
        if (
            r["status"] != "pass"
            or r["tests_run"] != 128
            or r["python"] != "3.12.15"
            or r["recipe_files_sha256"] != expected
            or r["actual_provenance"] != target
            or g["exit_code"]
            or g["denied_connections"]
            or g["denied_subprocesses"]
            or not g["connection_bindings_restored"]
            or g["error"] is not None
            or g["fixture_io"]["clones"] < 1
            or g["fixture_io"]["clones"] != g["fixture_io"]["seeds_verified"]
            or g["fixture_io"]["reseals"] != 10
            or g["fixture_builds"]
            != dict(requests=5, actual_builds=1, reused=4, seed_verifications=6, restored=True)
        ):
            raise ValueError("Exact target correctness incomplete")
    print(
        "Native source/sealed correctness evidence verified: "
        + str(root)
        + "; A3 resource acquisition remains held pending independent release review."
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["build", "ingest"])
    p.add_argument("--archive", type=Path)
    a = p.parse_args()
    if a.command == "build":
        print(build())
    else:
        ingest(a.archive)


if __name__ == "__main__":
    main()
