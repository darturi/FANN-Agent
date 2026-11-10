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
    lines,
    protocol,
    read,
    safe_file,
    save,
    sha,
    verify,
)

HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
SOURCE = ROOT / "trials/torch-reviews-partial-ann-v1-settings-fix/torch-partial-ann-v1-settings-fix"
OUTPUT = ROOT / "trials/torch-reviews-partial-calibration-v1-identity-fix"
RAW = (
    ROOT
    / "trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/returned"
    / CONTRACT["source_campaign"]
)
SOURCE_SHA = "c77efca4cbf297092a73c3921948209a1762b95a328ba1411154bea1ab4f89b4"


def commands():
    return "# RELEASE HOLD: no upload or submit commands are released.\n"


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
        raise ValueError("B2d seal differs")
    for n, h in read(SOURCE / "manifest.json")["files"].items():
        if sha(safe_file(SOURCE, n)) != h:
            raise ValueError("B2d package differs: " + n)
    if not testing:
        raise ValueError(
            "Release held: full startup/cleanup audit and memory feasibility review required"
        )
    from identity_repair import verify_failure

    failure = verify_failure()
    package.mkdir()
    shutil.copytree(SOURCE / "frozen", package / "frozen")
    for p in HERE.iterdir():
        if p.is_file() and (
            p.suffix in (".py", ".md")
            or p.name in ("CONTRACT.json", "SCHEDULE.json", "LAUNCHER.sh")
        ):
            shutil.copyfile(p, package / p.name)
    for n in (
        "origin-settings.json",
        "origin-source.json",
        "baseline-results.json",
        "eligibility.json",
        "queries.jsonl",
        "prior-exact-manifest.json",
        "b1b-manifest.json",
        "b1b2-manifest.json",
    ):
        shutil.copyfile(SOURCE / n, package / n)
    shutil.copyfile(SOURCE / "manifest.json", package / "prior-b2d-manifest.json")
    shutil.copyfile(RAW / "run/references.jsonl", package / "b2d-references.jsonl")
    cats = {
        r["copy"]: r["value"]
        for r in lines(RAW / "run/catalogs.jsonl")
        if r["phase"] == "final" and r["session_user"] == "torch_owner"
    }
    if set(cats) != {"native640", "partial640"}:
        raise ValueError("B2d final catalog coverage")
    save(package / "b2d-catalogs.json", cats)
    pins = {}
    for n, h in CONTRACT["source_files_sha256"].items():
        src = ROOT / n
        if sha(src) != h:
            raise ValueError("Frozen source changed: " + n)
        dst = package / "design-evidence" / n
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        pins[n] = dict(file=str(dst.relative_to(package)), sha256=h)
    save(package / "SOURCE-PINS.json", pins)
    cfg = read(SOURCE / "experiment.json")
    keep = {
        k: cfg[k]
        for k in (
            "source_settings",
            "prior_pilot_package",
            "prior_b1b_package",
            "prior_b1b2_package",
            "snapshot_identity",
            "prior_raw_files",
        )
    }
    raw = keep["prior_raw_files"].copy()
    raw["reviews-partial-calibration-v1-20261027T155119Z.6rd0lmkp"] = read(
        ROOT
        / "trials/torch-reviews-partial-calibration-v1-launch-fix/failed-archive-verification.json"
    )["raw_files_sha256"]
    raw["reviews-partial-calibration-v1-launch-fix-20261027T185901Z.98dd224c"] = read(
        ROOT
        / "trials/torch-reviews-partial-calibration-v1-metadata-fix"
        / "failed-archive-verification.json"
    )["raw_files_sha256"]
    raw[failure["campaign"]] = failure["raw_files_sha256"]
    shutil.copyfile(
        ROOT
        / "trials/torch-reviews-partial-calibration-v1-launch-fix"
        / "torch-partial-calibration-v1-launch-fix/manifest.json",
        package / "prior-launch-fix-manifest.json",
    )
    shutil.copyfile(
        OUTPUT / "failed-archive-verification.json", package / "FAILED-IDENTITY-VERIFICATION.json"
    )
    shutil.copyfile(
        ROOT
        / "trials/torch-reviews-partial-calibration-v1-metadata-fix"
        / "torch-partial-calibration-v1-metadata-fix/manifest.json",
        package / "prior-metadata-fix-manifest.json",
    )
    shutil.copyfile(
        ROOT
        / "trials/torch-reviews-partial-calibration-v1/torch-partial-calibration-v1/manifest.json",
        package / "prior-b2f-manifest.json",
    )
    raw[CONTRACT["source_campaign"]] = {
        str(p.relative_to(RAW)): sha(p)
        for p in sorted(RAW.rglob("*"))
        if p.is_file() and "analysis" not in p.relative_to(RAW).parts
    }
    save(
        package / "experiment.json",
        dict(
            **keep,
            **protocol(),
            prior_b2d_package="/home/dar579/torch-partial-ann-v1-settings-fix",
            prior_b2d_manifest_sha256=SOURCE_SHA,
            queries_sha256=sha(package / "queries.jsonl"),
            synthetic_fixture=testing,
            local_readiness="synthetic_fixture" if testing else "source_checks_passed",
        ),
    )
    # Retain all completed raw evidence as a mandatory read-only dependency.
    cfg2 = read(package / "experiment.json")
    cfg2["prior_raw_files"] = raw
    (package / "experiment.json").unlink()
    save(package / "experiment.json", cfg2)
    if not testing:
        shutil.copyfile(OUTPUT / "local-checks-source.json", package / "LOCAL_CHECKS.json")
    (package / "slurm").mkdir()
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
        (output / "COMMANDS.txt").write_text(commands())
        (output / "transfer.sh").write_text(transfer_script(package))
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
            "Failed/incomplete raw preserved: "
            + str(campaign)
            + "; no calibration verdict or automatic retry."
        )
        return
    from pc_report import analyze as replay

    dest = Path(output) if output else OUTPUT / "analysis-local" / name
    result = replay(campaign, package, dest)
    print(str(dest / "report.txt"))
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
