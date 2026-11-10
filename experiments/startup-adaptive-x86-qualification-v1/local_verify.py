"""Execute all preserved local suites against an owned mirror of the exact native layout."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from common import read, save, verify
from package import local_view
from paths import A3, MAIN


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    w = local_view(a.package, a.output / "workspace")
    work = a.output / "work"
    work.mkdir()
    out = a.output / "run"
    out.mkdir()
    records = {}

    def run(kind, source, label, phase):
        cmd = [
            sys.executable,
            "-B",
            str(a.package / "child.py"),
            "--workspace",
            str(w),
            "--source",
            str(source),
            "--kind",
            kind,
            "--profile",
            "local",
            "--phase",
            phase,
            "--out",
            str(out / label),
        ]
        if kind == "build":
            cmd += ["--candidate", str(work / "candidate-main")]
        with (out / (label + ".log")).open("x") as log:
            subprocess.run(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=650 if kind == "a3" else 450,
            )
        records[label] = read(out / label / "receipt.json")

    run("main", w / MAIN, "main-source", "source")
    run("build", w / MAIN, "candidate-build", "source")
    candidate = Path(records["candidate-build"]["candidate"])
    run("main", candidate, "main-sealed", "sealed")
    a3 = work / "candidate-a3"
    shutil.copytree(w / A3, a3)
    run("a3", w / A3, "a3-source", "source")
    run("a3", a3, "a3-sealed", "sealed")
    run("cpu", w / A3, "cpu", "source")
    from proofs import validate

    result = validate(out, w, read(a.package / "QUALIFICATION-CONTRACT.json"), "local")
    save(a.output / "local-suites.json", result)
    verify(a.package, require_release=False)
    print(result["status"])


if __name__ == "__main__":
    main()
