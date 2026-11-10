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
SOURCE = ROOT / "trials/torch-reviews-startup-resource-stream-v1/torch-startup-resource-stream-v1"
OUTPUT = ROOT / "trials/torch-reviews-startup-attribution-v1"
RAW = (
    ROOT
    / "trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/returned"
    / CONTRACT["source_campaign"]
)
SOURCE_SHA = "26a7d66b67137e77d5208d7b851b19d980a8a64060defc25cbe418db17190354"


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
    if package.exists():
        verify(package)
        if not archive.is_file() or Path(str(archive) + ".sha256").read_text().split() != [
            sha(archive),
            archive.name,
        ]:
            raise ValueError("Existing partial/changed seal preserved")
        return package
    if sha(SOURCE / "manifest.json") != SOURCE_SHA:
        raise ValueError("Prior startup seal differs")
    baseline = read(SOURCE / "manifest.json")
    for n, h in baseline["files"].items():
        if sha(safe_file(SOURCE, n)) != h:
            raise ValueError("Prior startup source differs: " + n)
    if not testing:
        checks = read(OUTPUT / "local-checks-source.json")
        actual = {p.name: sha(p) for p in HERE.glob("*.py")}
        if (
            checks["status"] != "pass"
            or checks["tests_run"] < 80
            or not checks["baseline_regression_pass"]
            or checks["source_files_sha256"] != actual
        ):
            raise ValueError("Current thorough source checks required")
    package.mkdir()
    for n in baseline["files"]:
        if "/" not in n and n.startswith("test_"):
            continue
        dst = package / n
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / n, dst)
    (package / "LOCAL_CHECKS.json").unlink(missing_ok=True)
    for p in HERE.iterdir():
        if (
            p.is_file()
            and p.name
            not in (
                "manifest.json",
                "experiment.json",
                "LOCAL_CHECKS.json",
                "submission-binding.json",
            )
            and (
                p.suffix in (".py", ".md", ".json")
                or p.name
                in (
                    "CONTRACT.json",
                    "RESOURCE-CONTRACT.json",
                    "CORRECTION-DESIGN.json",
                    "SCHEDULE.json",
                    "LAUNCHER.sh",
                    "COMMANDS-template.txt",
                )
            )
        ):
            shutil.copyfile(p, package / p.name)
    # Bind every original A0 input by value in the new seal; no old evidence is edited.
    for n, h in read(HERE / "ATTRIBUTION-SOURCE-PINS.json")["files_sha256"].items():
        source = ROOT / n
        if sha(source) != h:
            raise ValueError("A0 source changed: " + n)
        dst = package / "attribution-evidence" / n
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dst)
    from pc_common import STREAM

    pins = {}
    for n, h in STREAM["source_files_sha256"].items():
        source = ROOT / n
        if sha(source) != h:
            raise ValueError("Stream design source changed: " + n)
        dst = package / "stream-evidence" / n
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dst)
        pins[n] = dict(file=str(dst.relative_to(package)), sha256=h)
    (package / "STREAM-SOURCE-PINS.json").unlink(missing_ok=True)
    save(package / "STREAM-SOURCE-PINS.json", pins)
    shutil.copyfile(SOURCE / "manifest.json", package / "prior-stream-manifest.json")
    evidence = (
        ROOT
        / "trials/torch-reviews-startup-resource-v1"
        / "postrun-audit-2026-10-28/archive-verification.json"
    )
    prior_return = read(evidence)
    if (
        prior_return["archive_sha256"]
        != "312bf5c02959a1e90514f6ec556914303095eb30c2f87acd9b182010a28320e7"
    ):
        raise ValueError("Prior startup return differs")
    raw_root = (
        ROOT
        / "trials/torch-reviews-startup-resource-v1/returned"
        / "reviews-startup-resource-v1-20261028T020546Z.zdsnk75c"
    )
    for n, h in prior_return["raw_files_sha256"].items():
        if sha(safe_file(raw_root, n)) != h:
            raise ValueError("Prior startup raw differs: " + n)
    shutil.copyfile(evidence, package / "BASELINE-STARTUP-VERIFICATION.json")
    cfg = read(SOURCE / "experiment.json")
    cfg.update(protocol())
    cfg["prior_raw_files"][raw_root.name] = prior_return["raw_files_sha256"]
    stream_return_path = (
        ROOT
        / "trials/torch-reviews-startup-resource-stream-v1"
        / "postrun-audit-2026-10-28/archive-verification.json"
    )
    stream_return = read(stream_return_path)
    if (
        stream_return["archive_sha256"]
        != "63ff9b4800faab0a0ece6955ccabfb9c512548a35909cbca0e9b175a73ab3fef"
    ):
        raise ValueError("Prior stream return changed")
    cfg["prior_raw_files"][stream_return["campaign"]] = stream_return["raw_files_sha256"]
    shutil.copyfile(stream_return_path, package / "BASELINE-STREAM-VERIFICATION.json")
    cfg.update(
        synthetic_fixture=testing,
        local_readiness="synthetic_fixture" if testing else "source_checks_passed",
    )
    (package / "experiment.json").unlink()
    save(package / "experiment.json", cfg)
    if not testing:
        shutil.copyfile(OUTPUT / "local-checks-source.json", package / "LOCAL_CHECKS.json")
        shutil.copyfile(OUTPUT / "baseline-regression.json", package / "BASELINE_REGRESSION.json")
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
    with tarfile.open(archive, "x:gz") as tar:
        for p in sorted(package.rglob("*")):
            if p.is_file():
                tar.add(p, arcname=NAME + "/" + str(p.relative_to(package)), recursive=False)
    with Path(str(archive) + ".sha256").open("x") as h:
        h.write(sha(archive) + "  " + archive.name + "\n")
    if output == OUTPUT:
        (output / "READINESS.txt").write_text(
            "A1 local readiness only. A2 native handoff unreleased.\n"
        )
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
