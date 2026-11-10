"""Seal a new finite qualification capsule; materialize only owned local mount mirrors."""

import argparse
import os
import re
import shutil
import tarfile
from pathlib import Path

from common import (
    HERE,
    NAME,
    PREFIX,
    ROOT,
    code_map,
    inventory,
    read,
    recipe_map,
    save,
    sha,
    verify,
)

OUTPUT = ROOT / "trials/torch-reviews-startup-adaptive-x86-qualification-v1"


def reseal(p):
    (p / "manifest.json").unlink(missing_ok=True)
    save(p / "manifest.json", {"schema": "a3.adaptive-x86.capsule.v1", "files": inventory(p)})


def build(output=OUTPUT):
    output = Path(output)
    output.mkdir(exist_ok=True, parents=True)
    p = output / NAME
    p.mkdir()
    for src in HERE.iterdir():
        if src.is_file():
            shutil.copyfile(src, p / src.name)
    assets = read(HERE / "ASSET-PLAN.json")
    for n, v in assets["files"].items():
        src = ROOT / v["source"]
        if sha(src) != v["sha256"]:
            raise RuntimeError("Frozen input changed: " + str(src))
        dest = p / n
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    for n in assets["frozen_aliases"]:
        d = p / "workspace" / n / "frozen"
        d.mkdir(parents=True, exist_ok=True)
        (d / "FROZEN-ALIAS.txt").write_text(
            "Read-only bind to byte-identical pinned A1 frozen payload.\n"
        )
    reseal(p)
    verify(p, require_release=False)
    return p


def local_view(package, destination):
    p = Path(package)
    d = Path(destination)
    verify(p, require_release=False)

    def copy(src, dst):
        if Path(src).stat().st_size > 1024**2:
            os.link(src, dst)
            return dst
        return shutil.copyfile(src, dst)

    shutil.copytree(p / "workspace", d, copy_function=copy)
    plan = read(p / "ASSET-PLAN.json")
    payload = d / "trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1/frozen"
    for n, m in plan["frozen_aliases"].items():
        target = d / n / "frozen"
        shutil.rmtree(target)
        target.mkdir()
        for rel, h in m.items():
            src = payload / Path(rel).relative_to("frozen")
            dest = target / Path(rel).relative_to("frozen")
            if sha(src) != h:
                raise RuntimeError("Frozen alias source differs")
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.link(src, dest)
    return d


def release(package, source_control, sealed_control, local_suites):
    p = Path(package)
    for phase, receipt in [("source", source_control), ("sealed", sealed_control)]:
        shutil.copyfile(receipt, p / ("local-control-" + phase + ".json"))
    for name, path in local_suites.items():
        shutil.copyfile(path, p / ("local-" + name + ".json"))
    a = read(source_control)
    b = read(sealed_control)
    if (
        a["status"] != "pass"
        or b["status"] != "pass"
        or a["test_ids"] != b["test_ids"]
        or a["code_sha256"] != code_map(p)
        or b["code_sha256"] != code_map(p)
    ):
        raise RuntimeError("Current complete local control checks required")
    save(
        p / "LOCAL-READINESS.json",
        dict(
            status="pass",
            code_sha256=code_map(p),
            recipe_sha256=recipe_map(p),
            control_test_ids=a["test_ids"],
            Torch_jobs=0,
            ANN_searches=0,
            exact_searches=0,
            native_release=False,
            full_B2f=False,
        ),
    )
    reseal(p)
    verify(p)
    archive = p.parent / (NAME + ".tar.gz")
    with tarfile.open(archive, "x:gz", dereference=True) as t:
        for f in sorted(p.rglob("*")):
            if f.is_file():
                t.add(f, arcname=NAME + "/" + str(f.relative_to(p)), recursive=False)
    with Path(str(archive) + ".sha256").open("x") as f:
        f.write(sha(archive) + "  " + archive.name + "\n")
    return archive


def ingest(archive, output=OUTPUT):
    archive = Path(archive)
    if Path(str(archive) + ".sha256").read_text().split() != [sha(archive), archive.name]:
        raise ValueError("Returned archive checksum differs")
    rootname = archive.name.removesuffix(".tar.gz")
    if not re.fullmatch(re.escape(PREFIX) + r"[0-9]{8}T[0-9]{6}Z\.[A-Za-z0-9_-]+", rootname):
        raise ValueError("Unexpected campaign")
    dest = Path(output) / "returned"
    dest.mkdir(exist_ok=True)
    root = dest / rootname
    if root.exists():
        raise FileExistsError("Preserve existing complete/partial return")
    with tarfile.open(archive) as t:
        members = t.getmembers()
        names = set()
        if len(members) > 256 or sum(m.size for m in members) > 32 * 1024**2:
            raise ValueError("Return size/member cap")
        for m in members:
            rel = Path(m.name)
            if (
                not m.isfile()
                or m.name in names
                or rel.is_absolute()
                or ".." in rel.parts
                or rel.parts[0] != rootname
            ):
                raise ValueError("Unsafe returned member")
            names.add(m.name)
        for m in members:
            p = dest / m.name
            p.parent.mkdir(parents=True, exist_ok=True)
            with t.extractfile(m) as src, p.open("xb") as dst:
                shutil.copyfileobj(src, dst)
    return root


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("build", "ingest"))
    p.add_argument("--archive", type=Path)
    a = p.parse_args()
    print(build() if a.command == "build" else ingest(a.archive))
