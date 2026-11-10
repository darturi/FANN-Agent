"""Strict qualification capsule identity, durable publication and closed resource scope."""

import hashlib
import json
import os
from pathlib import Path

NAME = "torch-startup-adaptive-x86-qualification-v1"
PREFIX = "reviews-startup-adaptive-x86-qualification-v1-"
ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
HERE = Path(__file__).resolve().parent
IMAGE = "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a"
FREEZE_SHA = "8da59a6cb15fabe303ec34babc884b168399f7d42e5964eb51e87962b93a20aa"
ASSET_SHA = "5df799d6f72f02c0b674504289f6bd6e89510c077f04a8f672407d1b06ec8c6b"


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1024**2), b""):
            h.update(b)
    return h.hexdigest()


def save(p, value):
    with Path(p).open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def replace(p, value):
    p = Path(p)
    tmp = p.with_name("." + p.name + ".tmp")
    save(tmp, value)
    tmp.replace(p)


def code_map(p):
    return {f.name: sha(f) for f in sorted(Path(p).glob("*.py"))}


def recipe_map(p):
    return {
        f.name: sha(f)
        for f in sorted(Path(p).iterdir())
        if f.is_file()
        and (
            f.suffix == ".py"
            or f.name
            in (
                "LAUNCHER.sh",
                "QUALIFICATION-CONTRACT.json",
                "QUALIFICATION-FREEZE.json",
                "ASSET-PLAN.json",
            )
        )
    }


def inventory(p):
    return {str(f.relative_to(p)): sha(f) for f in sorted(Path(p).rglob("*")) if f.is_file()}


def verify(package, require_release=True):
    p = Path(package)
    m = read(p / "manifest.json")
    files = m["files"]
    actual = set()
    for f in p.rglob("*"):
        if f.is_symlink():
            raise ValueError("Capsule symlink prohibited")
        if f.is_file():
            actual.add(str(f.relative_to(p)))
    expected = set(files) | {"manifest.json"}
    if (p / "submission-binding.json").exists():
        expected.add("submission-binding.json")
    if actual != expected:
        raise ValueError("Capsule inventory differs")
    for n, h in files.items():
        rel = Path(n)
        if rel.is_absolute() or ".." in rel.parts or sha(p / rel) != h:
            raise ValueError("Capsule bytes differ: " + n)
    if (
        sha(p / "QUALIFICATION-FREEZE.json") != FREEZE_SHA
        or sha(p / "ASSET-PLAN.json") != ASSET_SHA
    ):
        raise ValueError("Prospective design/assets differ")
    frozen = read(p / "QUALIFICATION-FREEZE.json")
    c = read(p / "QUALIFICATION-CONTRACT.json")
    if any(c.get(k) != v for k, v in frozen.items()) or c["name"] != NAME or c["prefix"] != PREFIX:
        raise ValueError("Qualification identity/scope differs")
    from budget import validate

    validate(c["limits"], c["phase_seconds"])
    plan = read(p / "ASSET-PLAN.json")
    for n, v in plan["files"].items():
        if files.get(n) != v["sha256"]:
            raise ValueError("Pinned input differs: " + n)
    for n, h in c["main_helpers"].items():
        if sha(p / n) != h:
            raise ValueError("Original fixture guard changed")
    source = p / "workspace" / c["source_scope"]
    if inventory(source) != c["source_inventory"]:
        raise ValueError("Original adaptive source/tests changed")
    if require_release:
        release = read(p / "LOCAL-READINESS.json")
        if (
            release["status"] != "pass"
            or release["code_sha256"] != code_map(p)
            or release["recipe_sha256"] != recipe_map(p)
        ):
            raise RuntimeError("Current local readiness absent")
        if (
            release["Torch_jobs"] != 0
            or release["ANN_searches"] != 0
            or release["exact_searches"] != 0
        ):
            raise RuntimeError("Local readiness scope differs")
        for phase in ("source", "sealed"):
            proof = read(p / ("local-control-" + phase + ".json"))
            if (
                proof["status"] != "pass"
                or proof["failures"]
                or proof["errors"]
                or proof["skipped"]
                or proof["external_attempts"]
            ):
                raise RuntimeError("Incomplete guarded qualification checks")
            if (
                proof["code_sha256"] != code_map(p)
                or proof["test_ids"] != release["control_test_ids"]
            ):
                raise RuntimeError("Qualification check source/IDs differ")
        for name, count in (
            ("main-source", 128),
            ("main-sealed", 128),
            ("a3-source", 276),
            ("a3-sealed", 276),
        ):
            proof = read(p / ("local-" + name + ".json"))
            if (
                proof["status"] != "pass"
                or proof["tests_run"] != count
                or proof["profile"] != "local"
            ):
                raise RuntimeError("Complete preserved local suites required")
        cpu = read(p / "local-cpu.json")
        samples = read(p / "local-cpu-data.json")
        if (
            cpu["status"] != "pass"
            or cpu["profile"] != "local"
            or cpu["code_sha256"] != c["source_inventory"]
            or samples["status"] != "pass"
            or len(samples["measurements"]) != 60
            or samples["total_cpu_seconds"] > 120
            or samples["total_wall_seconds"] > 180
        ):
            raise RuntimeError("Complete bounded local CPU readiness required")
        if release["native_release"] is not False or release["full_B2f"] is not False:
            raise RuntimeError("Resource release prohibited")
    return c
