"""Finite native correctness capsule helpers; stdlib only."""

import hashlib
import json
from pathlib import Path

NAME = "torch-startup-attribution-compatibility-v1"
PREFIX = "reviews-startup-attribution-compatibility-v1-"
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
    if c["name"] != NAME or c["image_sha256"] != IMAGE:
        raise ValueError("Contract identity differs")
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
    return c
