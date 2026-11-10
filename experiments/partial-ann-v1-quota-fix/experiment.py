"""Build a new immutable package and ingest data; never submits or builds a local index."""

# ruff: noqa: E501 -- generated absolute shell commands retain their literal form.
import argparse
import json
import shutil
import tarfile
from pathlib import Path

from pa_common import (
    PREFIX,
    VERSION,
    campaign_identity,
    inventory,
    lines,
    parity,
    protocol,
    read,
    safe_file,
    save,
    sha,
    verify,
)
from pa_measure import order_manifest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "trials/torch-reviews-exact-topk-v1-catalog-fix/torch-exact-topk-v1-catalog-fix"
OUTPUT = ROOT / "trials/torch-reviews-partial-ann-v1-quota-fix"
# Packaging alias only: protocol name/prefix and the one-allocation reservation stay original.
PACKAGE_NAME = "torch-partial-ann-v1-quota-fix"
SOURCE_SHA = "6b2bb0f4a2797f01b70edcf256c518fe20f5cc00598d755ada04f216c9c6f842"


def commands():
    return f"""# MAC: upload; this verifies the local checksum, transfers both files, verifies remote checksum.
bash {OUTPUT}/transfer.sh upload

# TORCH LOGIN: run ONCE, only after UPLOAD VERIFIED.
(
  set -euo pipefail
  cd /home/dar579
  test ! -e torch-partial-ann-v1/submission-binding.json
  test ! -e torch-reviews-results/.torch-partial-ann-v1-reservation.json
  sha256sum -c {PACKAGE_NAME}.tar.gz.sha256
  test ! -e {PACKAGE_NAME}
  tar -xzf {PACKAGE_NAME}.tar.gz
  source /home/dar579/torch-reviews-first/torch.env
  export TORCH_SLURM_ACCOUNT=torch_pr_288_courant
  PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{PACKAGE_NAME}/pa_control.py submit \\
    /home/dar579/torch-reviews-first /home/dar579/torch-reviews-results
)

# TORCH: status is safe after reconnect, and takes no environment/path arguments.
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{PACKAGE_NAME}/pa_control.py status

# TORCH: once terminal, collect (including failure/early-stop evidence).
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{PACKAGE_NAME}/pa_control.py collect

# MAC: after collect prints Download archive and checksum.
bash {OUTPUT}/transfer.sh download

# One3h4CPU32GiB allocation;24-vector cost screen, full quality, conditional two-block A/A.
# Caps:202 cost stop /802 quality stop /16802 full search attempts; no providers/fits/protected queries.
# myquota/free-space/memory/native gates must pass. Unknown format fails closed before submission.
# If any step fails, retain extraction/binding/reservation; use status and report the error.
# Never rerun submit or delete/overwrite a reservation, package or failed campaign.
"""


def transfer_script(package):
    # Same explicit MFA/transfer/checksum sequence as the already repaired transfer helper.
    template = (ROOT / "agent/experiments/exact-topk-v1-catalog-fix/experiment.py").read_text()
    start = template.index('    template = r"""') + len('    template = r"""')
    end = template.index('\n"""', start)
    text = template[start:end] + "\n"
    text = text.replace("torch-exact-topk-v1-catalog-fix", PACKAGE_NAME).replace(
        "reviews-exact-topk-v1-catalog-fix-", PREFIX
    )
    for k, v in dict(
        OUTPUT=str(OUTPUT),
        NAME=PACKAGE_NAME,
        PYTHON=str(ROOT / "agent/.venv/bin/python"),
        PACKAGE=str(package),
        MANIFEST=sha(package / "manifest.json"),
    ).items():
        text = text.replace("@" + k + "@", v)
    return text


def extract_data(archive, destination):
    archive, destination = map(Path, (archive, destination))
    rootname = archive.name[:-7]
    if not archive.name.endswith(".tar.gz") or not rootname.startswith(PREFIX):
        raise ValueError("Unexpected archive name")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination / rootname
    if root.exists():
        raise ValueError("Existing return preserved; analyze it, never overwrite")
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
            with tar.extractfile(m) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
    return root


def build(output=None, testing=False):
    output = Path(output) if output else OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    package = output / PACKAGE_NAME
    archive = output / (PACKAGE_NAME + ".tar.gz")
    if package.exists():
        verify(package)
        if not archive.is_file() or Path(str(archive) + ".sha256").read_text().split() != [
            sha(archive),
            archive.name,
        ]:
            raise ValueError("Existing partial/changed package preserved")
        return package
    if sha(SOURCE / "manifest.json") != SOURCE_SHA:
        raise ValueError("Corrected B2b seal differs")
    for n, h in read(SOURCE / "manifest.json")["files"].items():
        if sha(safe_file(SOURCE, n)) != h:
            raise ValueError("Corrected B2b source differs: " + n)
    if not testing:
        checks = read(OUTPUT / "local-checks-source.json")
        if checks["status"] != "pass" or checks["tests_run"] < 30:
            raise ValueError("Passing local check record required before sealing")
    items = [
        i
        for i in lines(SOURCE / "frozen/inputs/queries.jsonl")
        if i["query"].get("filter") == dict(field="m_000000", op="gte", value=108)
    ]
    groups = inventory(items)
    package.mkdir()
    shutil.copytree(SOURCE / "frozen", package / "frozen")
    for p in HERE.iterdir():
        if p.is_file() and p.suffix in [".py", ".md"]:
            shutil.copyfile(p, package / p.name)
    for name in [
        "origin-settings.json",
        "origin-source.json",
        "baseline-results.json",
        "eligibility.json",
        "prior-exact-manifest.json",
        "b1b-manifest.json",
        "b1b2-manifest.json",
    ]:
        shutil.copyfile(SOURCE / name, package / name)
    shutil.copyfile(SOURCE / "manifest.json", package / "prior-corrected-manifest.json")
    evidence = [
        (ROOT / "research/fannagent-partial-ann-v1-design-2026-10-26.md", "DESIGN.md"),
        (
            ROOT / "research/fannagent-partial-ann-v1-implementation-addendum-2026-10-26.md",
            "IMPLEMENTATION-ADDENDUM.md",
        ),
        (ROOT / "agent/docs/verification/b2c-ann-alternatives-audit-v1.json", "b2c-receipt.json"),
        (
            ROOT / "agent/docs/verification/exact-topk-v1-catalog-fix-partial-postrun.json",
            "b2b-partial-receipt.json",
        ),
    ]
    for src, name in evidence:
        shutil.copyfile(src, package / name)
    if not testing:
        shutil.copyfile(OUTPUT / "local-checks-source.json", package / "LOCAL_CHECKS.json")
    cfg = read(SOURCE / "experiment.json")
    raw = cfg["prior_raw_files"].copy()
    partial = read(
        ROOT
        / "trials/torch-reviews-exact-topk-v1-catalog-fix/partial-review-2026-10-26/analysis.json"
    )
    raw[partial["campaign"]] = partial["raw_files_sha256"]
    old_failure = read(ROOT / "agent/docs/verification/exact-topk-v1-failure-postrun.json")
    old_verification = (
        ROOT
        / "trials/torch-reviews-exact-topk-v1-catalog-fix/failed-v1-verification-2026-10-26/verification.json"
    )
    if (
        sha(old_verification)
        != old_failure["artifacts_sha256"][str(old_verification.relative_to(ROOT))]
    ):
        raise ValueError("Original failed raw verification changed")
    old_raw = read(old_verification)
    raw[old_failure["campaign"]] = old_raw["raw_files_sha256"]
    selected_pins = read(SOURCE / "baseline-results.json")
    save(
        package / "selected-baseline-results.json",
        {i["query"]["id"]: selected_pins[i["query"]["id"]] for i in items},
    )
    (package / "queries.jsonl").write_text(
        "".join(json.dumps(i, sort_keys=True) + "\n" for i in items)
    )
    save(package / "order.json", order_manifest(items))
    save(
        package / "experiment.json",
        {
            **{
                key: cfg[key]
                for key in (
                    "source_settings",
                    "prior_pilot_package",
                    "prior_b1b_package",
                    "prior_b1b2_package",
                    "snapshot_identity",
                )
            },
            **protocol(),
            "development_groups": groups,
            "prior_raw_files": raw,
            "prior_corrected_manifest_sha256": SOURCE_SHA,
            "synthetic_fixture": testing,
            "pinned_evidence_sha256": {name: sha(package / name) for _, name in evidence},
            "local_readiness": "synthetic_test_fixture" if testing else "source_checks_passed",
            "canonical_acceptance_established": False,
            "independent_confirmation": False,
        },
    )
    (package / "slurm").mkdir()
    (package / "slurm/measure.sbatch").write_text("""#!/usr/bin/env bash
#SBATCH --job-name=fann-partial-ann-v1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
umask 077
exec python3 "$1/pa_job.py" "$@"
""")
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
                tar.add(p, arcname=PACKAGE_NAME + "/" + str(p.relative_to(package)), recursive=False)
    Path(str(archive) + ".sha256").write_text(sha(archive) + "  " + archive.name + "\n")
    if output == OUTPUT:
        (output / "COMMANDS.txt").write_text(commands())
        (output / "transfer.sh").write_text(transfer_script(package))
    return package


def analyze(campaign, output=None):
    package = OUTPUT / PACKAGE_NAME
    verify(package)
    name = campaign_identity(campaign, package)
    if (campaign / "analysis/failure-summary.json").exists():
        print(
            "Failed/incomplete raw preserved: "
            + str(campaign)
            + "; no performance verdict or automatic retry."
        )
        return
    from pa_report import analyze as replay

    output = Path(output) if output else OUTPUT / "analysis-local" / name
    result = replay(campaign, package, output)
    parity(result, read(campaign / "analysis/performance.json"))
    save(
        output / "verification.json",
        dict(
            status="passed",
            campaign=name,
            remote_local_parity=True,
            absolute_float_tolerance=1e-12,
            package_manifest_sha256=sha(package / "manifest.json"),
        ),
    )
    print(str(output / "report.txt"))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("package")
    a = sub.add_parser("ingest")
    a.add_argument("--archive", type=Path, required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--campaign", type=Path, required=True)
    a.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.command != "package" and HERE != OUTPUT / PACKAGE_NAME:
        import subprocess
        import sys

        verify(OUTPUT / PACKAGE_NAME)
        raise SystemExit(
            subprocess.call([sys.executable, str(OUTPUT / PACKAGE_NAME / "experiment.py"), *sys.argv[1:]])
        )
    if a.command == "package":
        print(build())
    elif a.command == "analyze":
        analyze(a.campaign.resolve(), a.output)
    else:
        archive = a.archive.resolve()
        require = Path(str(archive) + ".sha256").read_text().split()
        if require != [sha(archive), archive.name]:
            raise ValueError("Archive checksum differs")
        campaign = extract_data(archive, OUTPUT / "returned")
        if campaign.name != campaign_identity(campaign, OUTPUT / PACKAGE_NAME):
            raise ValueError("Archive root/submission identity differs")
        analyze(campaign)
