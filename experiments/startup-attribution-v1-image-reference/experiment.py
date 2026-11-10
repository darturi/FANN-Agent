"""Seal the isolated B2f implementation or verify returned data offline."""

import argparse
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from pc_common import (
    CONTRACT,
    NAME,
    PREFIX,
    VERSION,
    campaign_identity,
    protocol,
    read,
    safe_file,
    save,
    sha,
    verify,
)

HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
SOURCE = ROOT / "trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1"
OUTPUT = ROOT / "trials/torch-reviews-startup-attribution-v1-image-reference"
RAW = (
    ROOT
    / "trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/returned"
    / CONTRACT["source_campaign"]
)
SOURCE_SHA = "065022eb9428e4a7607b1eafa5784855103e184b174b4b5ac5abd6389827b96a"


def commands():
    return (HERE / "COMMANDS-template.txt").read_text().replace("@OUTPUT@", str(OUTPUT))


def transfer_script(package):
    template = (ROOT / "agent/experiments/exact-topk-v1-catalog-fix/experiment.py").read_text()
    start = template.index('    template = r"""') + len('    template = r"""')
    end = template.index('\n"""', start)
    text = template[start:end] + "\n"
    text = text.replace("torch-exact-topk-v1-catalog-fix", NAME).replace(
        "reviews-exact-topk-v1-catalog-fix-", PREFIX
    )
    for key, value in dict(
        OUTPUT=str(OUTPUT),
        NAME=NAME,
        PYTHON=str(ROOT / "agent/.venv/bin/python"),
        PACKAGE=str(package),
        MANIFEST=sha(package / "manifest.json"),
    ).items():
        text = text.replace("@" + key + "@", value)
    return text


def extract_data(archive, destination):
    archive, destination = map(Path, (archive, destination))
    rootname = archive.name[:-7]
    if not archive.name.endswith(".tar.gz") or not re.fullmatch(
        re.escape(PREFIX) + r"[0-9]{8}T[0-9]{6}Z\.[A-Za-z0-9_-]+", rootname
    ):
        raise ValueError("Unexpected archive name")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination / rootname
    if root.exists():
        raise ValueError("Existing complete/partial return preserved; use analyze on it")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 2 * 1024**3:
            raise ValueError("Archive data cap")
        names = set()
        for m in members:
            rel = Path(m.name)
            if (
                not rel.parts
                or rel.parts[0] != rootname
                or m.name in names
                or not m.isfile()
                or m.size > 256 * 1024**2
            ):
                raise ValueError("Unsafe/nonunique/nonregular/oversize member")
            names.add(m.name)
            safe_file(destination, m.name)
        for m in members:
            target = safe_file(destination, m.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(m) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
    return root


def build(output=None, testing=False):
    output = Path(output) if output else OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    package = output / NAME
    archive = output / (NAME + ".tar.gz")
    if package.exists() or archive.exists():
        raise FileExistsError("Preserve the existing complete/partial artifact")
    if sha(SOURCE / "manifest.json") != SOURCE_SHA:
        raise ValueError("Immutable A1 source seal differs")
    baseline = read(SOURCE / "manifest.json")
    for n, h in baseline["files"].items():
        if sha(safe_file(SOURCE, n)) != h:
            raise ValueError("A1 source changed: " + n)
    if not testing:
        code = {p.name: sha(p) for p in HERE.glob("*.py")}
        recipe = {n: sha(HERE / n) for n in read(HERE / "RECIPE-FILES.json")["files"]}
        for filename in ("local-checks-source.json", "target-checks-source.json"):
            checks = read(OUTPUT / filename)
            if (
                checks["status"] != "pass"
                or checks["tests_run"] < 120
                or not checks["baseline_regression_pass"]
                or checks["source_files_sha256"] != code
                or checks["recipe_files_sha256"] != recipe
            ):
                raise ValueError("Current source and exact-target readiness are required")
        if checks["python"] != "3.12.15":
            raise ValueError("Target interpreter correctness is unqualified")
    package.mkdir()
    for n in baseline["files"]:
        dst = package / n
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / n, dst)
    for n in ("experiment.json", "LOCAL_CHECKS.json"):
        (package / n).unlink()
    for name in read(HERE / "RECIPE-FILES.json")["files"]:
        shutil.copyfile(HERE / name, package / name)
    shutil.copyfile(SOURCE / "manifest.json", package / "parent-A1-manifest.json")
    cfg = read(SOURCE / "experiment.json")
    cfg.update(protocol())
    cfg.update(
        synthetic_fixture=testing,
        local_readiness="synthetic_fixture" if testing else "source_and_target_checks_passed",
    )
    save(package / "experiment.json", cfg)
    if not testing:
        shutil.copyfile(OUTPUT / "local-checks-source.json", package / "LOCAL_CHECKS.json")
        shutil.copyfile(OUTPUT / "target-checks-source.json", package / "TARGET_CHECKS.json")
    shutil.copyfile(HERE / "LAUNCHER.sh", package / "slurm/measure.sbatch")
    save(
        package / "manifest.json",
        dict(
            version=VERSION,
            files={
                str(p.relative_to(package)): sha(p)
                for p in sorted(package.rglob("*"))
                if p.is_file()
            },
        ),
    )
    verify(package)
    if not testing:
        from pc_common import readiness

        readiness(package)
    with tarfile.open(archive, "x:gz") as tar:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=NAME + "/" + str(path.relative_to(package)), recursive=False)
    with Path(str(archive) + ".sha256").open("x") as h:
        h.write(sha(archive) + "  " + archive.name + "\n")
    if output == OUTPUT and not testing:
        with (output / "transfer.sh").open("x") as h:
            h.write(transfer_script(package))
        with (output / "COMMANDS.txt").open("x") as h:
            h.write(commands())
    return package


def analyze(campaign, output=None):
    package = OUTPUT / NAME
    verify(package)
    name = campaign_identity(campaign, package)
    # Failed/incomplete raw stays collectible and readable, never a selected-subset verdict.
    if (
        not (campaign / "run/status.json").exists()
        or read(campaign / "run/status.json")["status"] != "complete"
        or not (campaign / "run/host-exit.json").exists()
        or read(campaign / "run/host-exit.json")["exit_code"]
    ):
        print(
            "Failed/incomplete startup raw preserved: "
            + str(campaign)
            + "; no resource verdict or automatic retry."
        )
        return
    from sa_report import analyze as replay

    dest = Path(output) if output else OUTPUT / "analysis-local" / name
    result = replay(campaign, package, dest)
    print(str(dest / "attribution.json"))
    return result


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("package")
    a = sub.add_parser("ingest")
    a.add_argument("--archive", type=Path, required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--campaign", type=Path, required=True)
    a.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.command != "package" and HERE != OUTPUT / NAME:
        verify(OUTPUT / NAME)
        raise SystemExit(
            subprocess.call([sys.executable, str(OUTPUT / NAME / "experiment.py"), *sys.argv[1:]])
        )
    if a.command == "package":
        print(build())
    elif a.command == "analyze":
        analyze(a.campaign.resolve(), a.output)
    else:
        archive = a.archive.resolve()
        if Path(str(archive) + ".sha256").read_text().split() != [sha(archive), archive.name]:
            raise ValueError("Archive checksum differs")
        campaign = extract_data(archive, OUTPUT / "returned")
        if campaign.name != campaign_identity(campaign, OUTPUT / NAME):
            raise ValueError("Archive root/submission identity differs")
        analyze(campaign)


if __name__ == "__main__":
    main()
