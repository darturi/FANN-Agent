"""Immutable pending-approval package, exact reference tree and bounded transport."""

import json
import tarfile
from pathlib import Path, PurePosixPath

from nh_common import HERE, INNER, config, core, inventory, read, save, sha

NAME = "torch-startup-native-integrated-qualification-v1"
PREFIX = "reviews-startup-native-integrated-qualification-v1-"


def verify(package, semantic=True):
    p = Path(package)
    manifest = read(p / "manifest.json")
    files = manifest["files"]
    if not isinstance(files, dict) or any(
        not isinstance(k, str) or Path(k).is_absolute() or ".." in Path(k).parts or "\\" in k
        for k in files
    ):
        raise ValueError("Strict package inventory required")
    actual = inventory(p)
    if actual != {**files, "manifest.json": sha(p / "manifest.json")}:
        raise RuntimeError("Complete integrated package bytes differ")
    plan = read(p / "PLAN.json")
    c = config()
    if (
        plan["name"] != NAME
        or plan["authorization"] != "pending_explicit_user_approval"
        or plan["native_release"] is not False
        or plan["limits"] != c["limits"]
        or plan["phase_seconds"] != c["phase_seconds"]
        or plan["original_archive_sha256"] != c["original_archive_sha256"]
        or plan["original_manifest_sha256"] != c["original_manifest_sha256"]
        or plan["image_sha256"] != c["image_sha256"]
    ):
        raise RuntimeError("Original scope/limits or pending authorization differs")
    if (
        inventory(p / "integration") != plan["integration_files"]
        or inventory(p / "integration-sealed") != plan["integration_files"]
    ):
        raise RuntimeError("Independent integration copies differ")
    if sha(p / "original.tar.gz") != c["original_archive_sha256"]:
        raise RuntimeError("Exact original archive differs")
    ref = p / "reference" / plan["reference_name"]
    if sha(ref / "manifest.json") != c["original_manifest_sha256"]:
        raise RuntimeError("Exact original manifest differs")
    import ast

    expected_ids = set()
    for module in (
        "test_integration",
        "test_release",
        "au_test_authority",
        "au_test_models",
        "test_native_integration",
    ):
        for cls in ast.parse((p / "integration" / (module + ".py")).read_text()).body:
            if isinstance(cls, ast.ClassDef):
                expected_ids.update(
                    module + "." + cls.name + "." + method.name
                    for method in cls.body
                    if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
                )
    for phase in ("source", "snapshot"):
        proof = read(p / "readiness" / ("complete-" + phase + ".json"))
        if (
            proof["status"] != "pass"
            or proof["tests_run"] != len(expected_ids)
            or len(proof["test_ids"]) != len(expected_ids)
            or set(proof["test_ids"]) != expected_ids
            or proof["code_sha256"] != plan["integration_files"]
            or any(proof[k] for k in ("errors", "failures", "skipped", "external_attempts"))
        ):
            raise RuntimeError("Complete current source/snapshot local checks required")
    local = read(p / "readiness/verification.json")
    if (
        local["status"] != "pass"
        or local["main_cases_per_phase"] != 128
        or local["A3_cases_per_phase"] != 276
        or local["CPU_samples"] != 60
        or any(
            local[k]
            for k in ("Torch_jobs", "ANN_searches", "exact_searches", "provider_calls", "real_SQL")
        )
    ):
        raise RuntimeError("Complete zero-search integrated local replay required")
    if semantic:
        core(ref)
    return plan


def build(destination, copy_tree, receipts):
    p = Path(destination)
    if p.exists():
        raise FileExistsError("Preserve prior package")
    p.mkdir(mode=0o700)
    copy_tree(HERE, p / "integration")
    copy_tree(HERE, p / "integration-sealed")
    (p / "reference").mkdir(mode=0o700)
    copy_tree(INNER, p / "reference" / INNER.name)
    import shutil

    shutil.copyfile(INNER.parent / (INNER.name + ".tar.gz"), p / "original.tar.gz")
    c = config()
    plan = {
        "schema": "a3.integrated.qualification.plan.v1",
        "name": NAME,
        "reference_name": INNER.name,
        "authorization": "pending_explicit_user_approval",
        "native_release": False,
        "full_B2f": False,
        "limits": c["limits"],
        "phase_seconds": c["phase_seconds"],
        "original_archive_sha256": c["original_archive_sha256"],
        "original_manifest_sha256": c["original_manifest_sha256"],
        "image_sha256": c["image_sha256"],
        "integration_files": inventory(HERE),
        "site_authority": "authenticated Slurm + kernel allocation; no privileged issuer",
        "searches": 0,
    }
    save(p / "PLAN.json", plan)
    (p / "readiness").mkdir(mode=0o700)
    for name, path in receipts.items():
        shutil.copyfile(path, p / "readiness" / name)
    save(p / "LAUNCHER.sh.meta.json", {"limits": c["limits"], "authorization": "not issued"})
    launcher = """#!/bin/bash
#SBATCH --job-name=fann-a3-ni
#SBATCH --partition=cs
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --hint=nomultithread
#SBATCH --no-requeue
#SBATCH --signal=B:USR1@120
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
exec "$1" -B "$2/integration/ni_control.py" host "$2" "$3"
"""
    (p / "LAUNCHER.sh").write_text(launcher)
    (p / "LAUNCHER.sh").chmod(0o700)
    save(
        p / "manifest.json",
        {"files": inventory(p), "scope": "immutable pending-approval package; no allowance"},
    )
    verify(p)
    archive = p.parent / (p.name + ".tar.gz")
    with tarfile.open(archive, "x:gz", dereference=False) as t:
        for path in sorted(p.rglob("*")):
            if path.is_file():
                t.add(path, arcname=p.name + "/" + str(path.relative_to(p)), recursive=False)
    if len(inventory(p)) > 2000:
        raise RuntimeError("Outer package member bound exceeded")
    verify_transport(archive, sha(archive))
    verify(p)
    (Path(str(archive) + ".sha256")).write_text(sha(archive) + "  " + archive.name + "\n")
    return archive


def verify_transport(archive, expected):
    if sha(archive) != expected:
        raise ValueError("Transport checksum differs")
    with tarfile.open(archive, "r:gz") as t:
        members = t.getmembers()
        seen = set()
        if len(members) > 2000 or sum(m.size for m in members) > 1024**3:
            raise ValueError("Outer transport bounds exceeded")
        contents = {}
        import hashlib

        for m in members:
            rel = PurePosixPath(m.name)
            if (
                not m.isfile()
                or rel.is_absolute()
                or ".." in rel.parts
                or len(rel.parts) < 2
                or rel.parts[0] != NAME
                or m.name != rel.as_posix()
                or "\\" in m.name
                or m.name in seen
                or m.mode & 0o7000
            ):
                raise ValueError("Unsafe transport member")
            seen.add(m.name)
            h = hashlib.sha256()
            with t.extractfile(m) as f:
                for block in iter(lambda: f.read(1024**2), b""):
                    h.update(block)
            contents[str(rel.relative_to(NAME))] = h.hexdigest()
        member = t.getmember(NAME + "/manifest.json")
        manifest = json.load(t.extractfile(member))["files"]
        if contents != {**manifest, "manifest.json": contents["manifest.json"]}:
            raise ValueError("Archive complete hashes differ")
    return {
        "files": len(members),
        "content_bytes": sum(m.size for m in members),
        "sha256": expected,
    }
