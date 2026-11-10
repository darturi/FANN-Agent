"""Local package construction and data-only ingestion. Never dispatches jobs."""

import argparse
import json
import shutil
import tarfile
from pathlib import Path

from pp_common import (
    CANDIDATE,
    CELLS,
    CONDITIONING_CALLS,
    COUNTS,
    CRITERIA,
    EPISODE,
    FILTERS,
    NAME,
    P1_MANIFEST,
    P1_RECEIPT,
    P2A_MANIFEST,
    P2A_RECEIPT,
    P2B_MANIFEST,
    P2B_RECEIPT,
    PILOT,
    RECEIPT_HASH,
    ROUNDS,
    SCOPE,
    SOURCE_MANIFEST,
    VARIANTS,
    VERSION,
    inventory,
    lines,
    read,
    safe_file,
    save,
    sha,
    verify,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EPISODE_ROOT = ROOT / "trials/torch-reviews-selective-agent-v1/runs" / EPISODE
SOURCE = EPISODE_ROOT / "packages/pilot" / ("torch-selective-agent-v1-pilot-" + EPISODE)
OUTPUT = ROOT / "trials/torch-reviews-activation-timing-calibration-v1"


def commands(package, archive):
    python = ROOT / "agent/.venv/bin/python"
    return """# MAC: verify and upload the sealed package (no model calls).
(
  set -euo pipefail
  cd '{parent}'
  shasum -a 256 -c '{name}.tar.gz.sha256'
  scp -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519 \\
    -o StrictHostKeyChecking=yes -o UpdateHostKeys=no \\
    '{name}.tar.gz' '{name}.tar.gz.sha256' dar579@dtn012.hpc.nyu.edu:/home/dar579/
)

# TORCH LOGIN: verify, extract once, load existing environment, submit two serial allocations.
(
  set -euo pipefail
  cd /home/dar579
  sha256sum -c '{name}.tar.gz.sha256'
  test ! -e '{name}'
  tar -xzf '{name}.tar.gz'
  source /home/dar579/torch-reviews-first/torch.env
  export TORCH_SLURM_ACCOUNT=torch_pr_288_courant
  PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{name}/pp_control.py submit \\
    /home/dar579/torch-reviews-first /home/dar579/torch-reviews-results
)

# TORCH: these commands work after a fresh login. Do not run submit again.
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{name}/pp_control.py status

# TORCH: after both blocks complete, reconstruct summaries and archive full raw data.
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{name}/pp_control.py collect

# MAC (zsh/bash): download the exact bound campaign; verify and independently analyze data.
(
  set -euo pipefail
  cd '{output}'
  torch_options=(
    -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519
    -o StrictHostKeyChecking=yes -o UpdateHostKeys=no
  )
  ssh -t "${{torch_options[@]}}" dar579@dtn012.hpc.nyu.edu true
  torch_binding="$(mktemp -t fann-p2c-binding)"
  scp "${{torch_options[@]}}" \
    dar579@dtn012.hpc.nyu.edu:/home/dar579/{name}/submission-binding.json "$torch_binding"
  torch_run="$('{python}' -c \\
    'import json,sys; print(json.load(open(sys.argv[1]))["campaign"])' "$torch_binding")"
  rm "$torch_binding"
  scp "${{torch_options[@]}}" "dar579@dtn012.hpc.nyu.edu:${{torch_run}}.tar.gz" \
    "dar579@dtn012.hpc.nyu.edu:${{torch_run}}.tar.gz.sha256" .
  shasum -a 256 -c "${{torch_run##*/}}.tar.gz.sha256"
  PYTHONDONTWRITEBYTECODE=1 '{python}' '{script}' ingest \\
    --archive "${{torch_run##*/}}.tar.gz"
)

# Resources: 2 serial x (4 CPUs, 32 GiB, 3 hours); 592,242 searches total.
# Zero provider calls/confirmation queries. Experimental execution revision only; no deployment.
# A failed/unknown submission remains bound. Inspect status; never delete bindings or reservations.
""".format(
        parent=archive.parent,
        name=NAME,
        output=OUTPUT,
        python=python,
        script=package / "experiment.py",
    )


def transfer_script(package):
    # Interactive SSH owns device authentication; JSON is read from a completed
    # scp file only after successful authentication/transfer.
    template = r"""#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  upload|download) p2c_action="$1" ;;
  *) echo "Usage: bash transfer.sh upload|download" >&2; exit 2 ;;
esac
cd '@OUTPUT@'
p2c_socketdir="$(mktemp -d -t fann-p2c-ssh)"
p2c_binding="${p2c_socketdir}/submission-binding.json"
p2c_options=(
  -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519
  -o StrictHostKeyChecking=yes -o UpdateHostKeys=no
  -o ControlMaster=auto -o ControlPersist=600 -o "ControlPath=${p2c_socketdir}/connection"
)
p2c_cleanup() {
  ssh "${p2c_options[@]}" -O exit dar579@dtn012.hpc.nyu.edu >/dev/null 2>&1 || true
  rm -f "$p2c_binding" "${p2c_socketdir}/connection"
  rmdir "$p2c_socketdir" 2>/dev/null || true
}
trap p2c_cleanup EXIT
if test "$p2c_action" = upload; then
  shasum -a 256 -c '@NAME@.tar.gz.sha256'
fi
ssh -t "${p2c_options[@]}" dar579@dtn012.hpc.nyu.edu true
if test "$p2c_action" = upload; then
  scp "${p2c_options[@]}" '@NAME@.tar.gz' '@NAME@.tar.gz.sha256' \
    dar579@dtn012.hpc.nyu.edu:/home/dar579/
else
  scp "${p2c_options[@]}" \
    dar579@dtn012.hpc.nyu.edu:/home/dar579/@NAME@/submission-binding.json "$p2c_binding"
  p2c_run="$( '@PYTHON@' - "$p2c_binding" <<'PYBIND'
import json, re, sys
value = json.load(open(sys.argv[1]))
if value['package_manifest_sha256'] != '@MANIFEST@':
    raise SystemExit('Binding belongs to another sealed package')
run = value['campaign']
pattern = (r'/home/dar579/torch-reviews-results/reviews-activation-calibration-v1-'
           r'[0-9]{8}T[0-9]{6}Z[.][A-Za-z0-9_-]+')
if not re.fullmatch(pattern, run):
    raise SystemExit('Unexpected campaign path; preserve binding and inspect status')
print(run)
PYBIND
  )"
  scp "${p2c_options[@]}" "dar579@dtn012.hpc.nyu.edu:${p2c_run}.tar.gz" \
    "dar579@dtn012.hpc.nyu.edu:${p2c_run}.tar.gz.sha256" .
  shasum -a 256 -c "${p2c_run##*/}.tar.gz.sha256"
  PYTHONDONTWRITEBYTECODE=1 '@PYTHON@' '@PACKAGE@/experiment.py' ingest \
    --archive "${p2c_run##*/}.tar.gz"
fi
"""
    for key, value in {
        "OUTPUT": str(OUTPUT),
        "NAME": NAME,
        "PYTHON": str(ROOT / "agent/.venv/bin/python"),
        "PACKAGE": str(package),
        "MANIFEST": sha(package / "manifest.json"),
    }.items():
        template = template.replace("@" + key + "@", value)
    return template


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    package = OUTPUT / NAME
    archive = OUTPUT / (NAME + ".tar.gz")
    if package.exists():
        verify(package)
        if (
            not archive.exists()
            or sha(archive) != Path(str(archive) + ".sha256").read_text().split()[0]
        ):
            raise ValueError("Partial/changed package preserved; inspect it instead of overwriting")
        print(str(OUTPUT / "COMMANDS.txt"))
        return package
    receipt_path = ROOT / "agent/docs/verification/selective-agent-v1-pilot-postrun.json"
    if sha(receipt_path) != RECEIPT_HASH or sha(SOURCE / "manifest.json") != SOURCE_MANIFEST:
        raise ValueError("Source receipt/package changed from the roadmap snapshot")
    receipt = read(receipt_path)
    if (
        receipt["status"] != "verified_no_qualified_candidate_agent_abstained"
        or receipt["confirmation_allocations"]
    ):
        raise ValueError("Source episode state differs")
    attribution = ROOT / "agent/docs/verification/execution-cost-attribution-v1-postrun.json"
    attribution_package = (
        ROOT
        / "trials/torch-reviews-execution-cost-attribution-v1/torch-execution-cost-attribution-v1"
    )
    if sha(attribution) != P1_RECEIPT or sha(attribution_package / "manifest.json") != P1_MANIFEST:
        raise ValueError("Verified P1 snapshot changed")
    p2a = (
        ROOT
        / "trials/torch-reviews-prepared-policy-lifecycle-v1/torch-prepared-policy-lifecycle-v1"
    )
    p2a_receipt = ROOT / "agent/docs/verification/prepared-policy-lifecycle-v1-postrun.json"
    if sha(p2a / "manifest.json") != P2A_MANIFEST or sha(p2a_receipt) != P2A_RECEIPT:
        raise ValueError("Verified P2a identity changed")
    for name, expected in read(p2a / "manifest.json")["files"].items():
        if sha(safe_file(p2a, name)) != expected:
            raise ValueError("Frozen P2a package changed: " + name)
    for name, expected in read(p2a_receipt)["raw_files_verified"].items():
        if sha(safe_file(Path(read(p2a_receipt)["raw_campaign"]), name)) != expected:
            raise ValueError("Verified P2a raw data changed: " + name)
    for name in ("pp_backend.py", "pp_session.py"):
        if sha(HERE / name) != sha(p2a / name):
            raise ValueError("P2a reference module changed: " + name)
    p2b = (
        ROOT
        / "trials/torch-reviews-admission-profile-identity-v1/torch-admission-profile-identity-v1"
    )
    p2b_receipt = ROOT / "agent/docs/verification/admission-profile-identity-v1-postrun.json"
    if sha(p2b / "manifest.json") != P2B_MANIFEST or sha(p2b_receipt) != P2B_RECEIPT:
        raise ValueError("Verified P2b identity changed")
    for name, expected in read(p2b / "manifest.json")["files"].items():
        if sha(safe_file(p2b, name)) != expected:
            raise ValueError("Frozen P2b source changed: " + name)
    for name, expected in read(p2b_receipt)["raw_files_verified"].items():
        if sha(safe_file(Path(read(p2b_receipt)["raw_campaign"]), name)) != expected:
            raise ValueError("Verified P2b raw data changed: " + name)
    reference_hashes = {
        n: sha(p2b / n) for n in ("pp_backend.py", "pp_session.py", "pb_policy.py", "pb_session.py")
    }
    reference_hashes["p2b_report_reference.py"] = sha(p2b / "pp_report.py")
    for name, expected in reference_hashes.items():
        if sha(HERE / name) != expected:
            raise ValueError("Frozen execution/gate code changed: " + name)
    attribution_receipt = read(attribution)
    for name, expected in attribution_receipt["raw_files_verified"].items():
        if sha(safe_file(Path(attribution_receipt["raw_campaign"]), name)) != expected:
            raise ValueError("Verified attribution raw data changed: " + name)
    manifest = read(SOURCE / "manifest.json")
    for name, expected in manifest["files"].items():
        if sha(safe_file(SOURCE, name)) != expected:
            raise ValueError("Frozen pilot input changed: " + name)
    previous = EPISODE_ROOT / "returned/pilot" / PILOT
    for name, expected in receipt["raw_files_verified"].items():
        if sha(safe_file(previous, name)) != expected:
            raise ValueError("Original raw result differs: " + name)
    prior_submission = read(previous / "submission.json")
    package.mkdir()
    frozen = package / "frozen"
    frozen.mkdir()
    for name in list(manifest["files"]) + ["manifest.json"]:
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(safe_file(SOURCE, name), target)
    for path in sorted(HERE.iterdir()):
        if path.is_file() and path.suffix in (".py", ".md"):
            shutil.copyfile(path, package / path.name)
    shutil.copyfile(receipt_path, package / "baseline-receipt.json")
    shutil.copyfile(attribution, package / "attribution-receipt.json")
    shutil.copyfile(p2a_receipt, package / "p2a-receipt.json")
    shutil.copyfile(p2a / "manifest.json", package / "p2a-manifest.json")
    shutil.copyfile(p2b_receipt, package / "p2b-receipt.json")
    shutil.copyfile(p2b / "manifest.json", package / "p2b-manifest.json")
    candidates = read(frozen / "candidates.json")
    save(package / "candidate.json", {CANDIDATE: candidates[CANDIDATE]})
    from pp_common import digest

    pins = {}
    with (previous / "blocks/block-0/references.jsonl").open() as handle:
        for line in handle:
            row = json.loads(line)
            if row["query_id"] in pins:
                raise ValueError("Duplicate original reference")
            pins[row["query_id"]] = digest({**row, "states": row["states"]["light19"]})
    if len(pins) != 600:
        raise ValueError("Pinned native/reference inventory differs")
    save(package / "reference-pins.json", pins)
    cfg = {
        "name": NAME,
        "version": VERSION,
        "source_manifest_sha256": SOURCE_MANIFEST,
        "source_attribution_manifest_sha256": P1_MANIFEST,
        "source_attribution_receipt_sha256": P1_RECEIPT,
        "source_p2a_manifest_sha256": P2A_MANIFEST,
        "source_p2a_receipt_sha256": P2A_RECEIPT,
        "p2a_reference_files_sha256": {n: sha(p2a / n) for n in ("pp_backend.py", "pp_session.py")},
        "variants": VARIANTS,
        "cells": CELLS,
        "rounds": ROUNDS,
        "conditioning_calls_per_slot": CONDITIONING_CALLS,
        "source_p2b_manifest_sha256": P2B_MANIFEST,
        "source_p2b_receipt_sha256": P2B_RECEIPT,
        "p2b_reference_files_sha256": reference_hashes,
        "criteria": CRITERIA,
        "measurement_scope": SCOPE,
        "candidate_hash": CANDIDATE,
        "filters": FILTERS,
        "seed": 20261022,
        "counts": COUNTS,
        "blocks": COUNTS["allocations"],
        "maximum_seconds": 10200,
        "resources": {"cpus": 4, "memory_gib": 32, "wall_hours": 3},
        "development_groups": inventory(lines(frozen / "inputs/queries.jsonl")),
        "prior_pilot_package": prior_submission["package"],
        "prior_pilot_raw_sha256": receipt["raw_files_verified"],
        "provider_calls_allowed": 0,
        "confirmation_queries_allowed": 0,
        "synthetic_only": False,
        "candidate_selection_allowed": False,
        "canonical_acceptance_established": False,
        "interpretation": (
            "P2c warm-index policy-activation calibration only, unchanged code/policies. "
            "Fixed native conditioning before each fresh session; adjacent AB/BA crossovers. "
            "No retrospective repair of P2b or serving acceptance."
        ),
    }
    save(package / "experiment.json", cfg)
    (package / "slurm").mkdir()
    with (package / "slurm/measure.sbatch").open("x") as handle:
        handle.write("""#!/usr/bin/env bash
#SBATCH --job-name=fann-calibration-v1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
umask 077
exec python3 "$1/pp_job.py" "$@"
""")
    save(
        package / "manifest.json",
        {
            "version": VERSION,
            "files": {
                str(p.relative_to(package)): sha(p)
                for p in sorted(package.rglob("*"))
                if p.is_file()
            },
        },
    )
    verify(package)
    with tarfile.open(archive, "x:gz") as tar:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=NAME + "/" + str(path.relative_to(package)), recursive=False)
    with Path(str(archive) + ".sha256").open("x") as handle:
        handle.write(sha(archive) + "  " + archive.name + "\n")
    with (OUTPUT / "COMMANDS.txt").open("x") as handle:
        handle.write(commands(package, archive))
    with (OUTPUT / "transfer.sh").open("x") as handle:
        handle.write(transfer_script(package))
    print(
        json.dumps(
            {
                "package": str(package),
                "archive": str(archive),
                "sha256": sha(archive),
                "commands": str(OUTPUT / "COMMANDS.txt"),
                "counts": COUNTS,
            },
            indent=2,
        )
    )
    return package


def extract_data(archive, destination):
    """Never execute returned Python/shell; reject links, traversal and oversized data."""
    archive, destination = Path(archive), Path(destination)
    root_name = archive.name[:-7]
    if not root_name.startswith("reviews-activation-calibration-v1-"):
        raise ValueError("Unexpected campaign archive name")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination / root_name
    if root.exists():
        raise ValueError(
            "Already extracted/partial return preserved; use analyze on the existing data"
        )
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 2 * 1024 * 1024 * 1024:
            raise ValueError("Returned archive exceeds data budget")
        names = set()
        for member in members:
            relative = Path(member.name)
            if relative.parts[0] != root_name or member.name in names or not member.isfile():
                raise ValueError("Archive member is not a unique regular campaign file")
            names.add(member.name)
            target = safe_file(destination, member.name)
            if member.size > 256 * 1024 * 1024:
                raise ValueError("Oversized returned file")
        for member in members:
            target = safe_file(destination, member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
    return root


def parity(left, right, path="result"):
    if type(left) is not type(right):
        raise ValueError("Remote/local type differs: " + path)
    if isinstance(left, dict):
        if set(left) != set(right):
            raise ValueError("Remote/local keys differ: " + path)
        for key in left:
            parity(left[key], right[key], path + "/" + key)
    elif isinstance(left, list):
        if len(left) != len(right):
            raise ValueError("Remote/local lengths differ: " + path)
        for index, (a, b) in enumerate(zip(left, right)):
            parity(a, b, path + "/" + str(index))
    elif isinstance(left, float):
        if (
            not __import__("math").isfinite(left)
            or not __import__("math").isfinite(right)
            or abs(left - right) > 1e-12
        ):
            raise ValueError("Remote/local float differs: " + path)
    elif left != right:
        raise ValueError("Remote/local value differs: " + path)


def analyze(campaign, output=None):
    package = OUTPUT / NAME
    verify(package)
    from pp_report import analyze as report

    if (campaign / "analysis/failure-summary.json").exists():
        print(json.dumps(read(campaign / "analysis/failure-summary.json"), indent=2))
        print("Failed raw campaign preserved at " + str(campaign))
        return
    output = Path(output) if output else OUTPUT / "analysis-local" / campaign.name
    if output.exists() and any(output.iterdir()):
        raise ValueError("Analysis output exists; inspect it or choose a fresh --output directory")
    result = report(campaign, package, output)
    parity(result, read(campaign / "analysis/performance.json"))
    save(
        output / "verification.json",
        {
            "status": "passed",
            "remote_local_parity": True,
            "absolute_float_tolerance": 1e-12,
            "package_manifest_sha256": sha(package / "manifest.json"),
            "provider_calls": 0,
            "confirmation_queries": 0,
            "canonical_acceptance_established": False,
        },
    )
    print(str(output / "report.txt"))
    print(str(output / "calibration.md"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("package")
    p = sub.add_parser("ingest")
    p.add_argument("--archive", required=True, type=Path)
    p = sub.add_parser("analyze")
    p.add_argument("--campaign", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "package":
        build()
    elif args.command == "analyze":
        analyze(args.campaign.resolve(), args.output)
    else:
        archive = args.archive.resolve()
        checksum = Path(str(archive) + ".sha256").read_text().split()
        if len(checksum) != 2 or checksum[1] != archive.name or sha(archive) != checksum[0]:
            raise ValueError("Archive/checksum differs")
        analyze(extract_data(archive, OUTPUT / "returned"))
