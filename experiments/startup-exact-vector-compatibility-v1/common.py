"""Finite native correctness capsule helpers; stdlib only."""

import hashlib
import json
from pathlib import Path

NAME = "torch-startup-exact-vector-compatibility-v1"
PREFIX = "reviews-startup-exact-vector-compatibility-v1-"
ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
MAIN = ROOT / "agent/experiments/startup-attribution-v1-image-reference"
IMAGE = "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a"


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def save(p, v):
    with Path(p).open("x") as f:
        json.dump(v, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        __import__("os").fsync(f.fileno())


def replace(p, v):
    p = Path(p)
    tmp = p.with_name("." + p.name + ".tmp")
    save(tmp, v)
    tmp.replace(p)


def verify(package):
    p = Path(package)
    m = read(p / "manifest.json")
    names = set()
    for f in p.rglob("*"):
        if f.is_symlink():
            raise ValueError("Capsule symlink")
        if f.is_file():
            names.add(str(f.relative_to(p)))
    if names != set(m["files"]) | {"manifest.json"} | (
        {"submission-binding.json"} if (p / "submission-binding.json").exists() else set()
    ):
        raise ValueError("Capsule file inventory differs")
    for n, h in m["files"].items():
        rel = Path(n)
        if rel.is_absolute() or ".." in rel.parts or sha(p / rel) != h:
            raise ValueError("Capsule file changed: " + n)
    c = read(p / "COMPATIBILITY-CONTRACT.json")
    from budget import validate

    validate(c["limits"])
    for name, key in (
        ("BUDGET-REVIEW.json", "budget_review_sha256"),
        ("BUDGET-FREEZE.json", "budget_freeze_sha256"),
    ):
        if sha(p / name) != c[key]:
            raise ValueError("Budget design identity differs: " + name)
    if c["name"] != NAME or c["image_sha256"] != IMAGE:
        raise ValueError("Contract identity differs")
    for n, expected in c["fixture_dependency_files_sha256"].items():
        dep = p / "workspace/trials/torch-reviews-first" / n
        if sha(dep) != expected:
            raise ValueError("Offline constructor dependency changed: " + n)
    main = p / "workspace/agent/experiments/startup-attribution-v1-image-reference"
    if {n: sha(main / n) for n in c["main_recipe_files_sha256"]} != c["main_recipe_files_sha256"]:
        raise ValueError("Corrected main source changed")
    parent = (
        p / "workspace/trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1"
    )
    if sha(parent / "manifest.json") != c["parent_A1_manifest_sha256"]:
        raise ValueError("A1 parent identity differs")
    for n, h in read(parent / "manifest.json")["files"].items():
        if sha(parent / n) != h:
            raise ValueError("A1 parent changed: " + n)
    for key, directory in (
        ("integration_files_sha256", c["integration_source"]),
        ("prototype_files_sha256", c["prototype_source"]),
        ("reference_files_sha256", c["reference_view"]),
    ):
        for name, expected in c[key].items():
            if sha(p / "workspace" / directory / name) != expected:
                raise ValueError("A3 source/reference view differs: " + name)
    for name, expected in c["inherited_helpers_sha256"].items():
        if sha(p / name) != expected:
            raise ValueError("Inherited correctness guard differs")
    if (
        sha(p / "workspace/trials/torch-reviews-startup-exact-vector-v1/A3-FREEZE.json")
        != c["A3_freeze_sha256"]
    ):
        raise ValueError("Original A3 design changed")
    if sha(p / "NATIVE-GATE-AMENDMENT.json") != c["native_gate_amendment_sha256"]:
        raise ValueError("Native gate amendment changed")
    return c
