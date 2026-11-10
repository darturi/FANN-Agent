"""Local package construction and data-only ingestion. Never dispatches jobs."""

import argparse
import json
import shutil
import tarfile
from pathlib import Path

from ec_common import (
    CANDIDATE,
    COUNTS,
    EPISODE,
    FILTERS,
    NAME,
    PILOT,
    RECEIPT_HASH,
    SOURCE_MANIFEST,
    VERSION,
    diagnostic_groups,
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
OUTPUT = ROOT / "trials/torch-reviews-execution-cost-attribution-v1"


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

# TORCH LOGIN: verify, extract once, load existing environment, submit three serial allocations.
(
  set -euo pipefail
  cd /home/dar579
  sha256sum -c '{name}.tar.gz.sha256'
  test ! -e '{name}'
  tar -xzf '{name}.tar.gz'
  source /home/dar579/torch-reviews-first/torch.env
  export TORCH_SLURM_ACCOUNT=torch_pr_288_courant
  PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{name}/ec_control.py submit \\
    /home/dar579/torch-reviews-first /home/dar579/torch-reviews-results
)

# TORCH: these commands work after a fresh login. Do not run submit again.
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{name}/ec_control.py status

# TORCH: after all three blocks complete, reconstruct summaries and archive full raw data.
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{name}/ec_control.py collect

# MAC (zsh/bash): download the exact bound campaign; verify and independently analyze data.
(
  set -euo pipefail
  cd '{output}'
  torch_options=(
    -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519
    -o StrictHostKeyChecking=yes -o UpdateHostKeys=no
  )
  torch_run="$(ssh "${{torch_options[@]}}" dar579@dtn012.hpc.nyu.edu \\
    'cat /home/dar579/{name}/submission-binding.json' | \\
    '{python}' -c 'import json,sys; print(json.load(sys.stdin)["campaign"])')"
  scp "${{torch_options[@]}}" "dar579@dtn012.hpc.nyu.edu:${{torch_run}}.tar.gz" \\
    "dar579@dtn012.hpc.nyu.edu:${{torch_run}}.tar.gz.sha256" .
  shasum -a 256 -c "${{torch_run##*/}}.tar.gz.sha256"
  PYTHONDONTWRITEBYTECODE=1 '{python}' '{script}' ingest \\
    --archive "${{torch_run##*/}}.tar.gz"
)

# Resources: 3 serial x (4 CPUs, 32 GiB, 2 hours); 83,763 searches total.
# Zero provider calls, zero confirmation queries. No optimization or deployment occurs.
# A failed/unknown submission remains bound. Inspect status; never delete bindings or reservations.
""".format(
        parent=archive.parent,
        name=NAME,
        output=OUTPUT,
        python=python,
        script=HERE / "experiment.py",
    )


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
    candidates = read(frozen / "candidates.json")
    save(package / "candidate.json", {CANDIDATE: candidates[CANDIDATE]})
    from ec_common import digest

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
        "candidate_hash": CANDIDATE,
        "filters": FILTERS,
        "seed": 20261022,
        "counts": COUNTS,
        "blocks": 3,
        "maximum_seconds": 6600,
        "resources": {"cpus": 4, "memory_gib": 32, "wall_hours": 2},
        "diagnostic_groups": diagnostic_groups(lines(frozen / "inputs/queries.jsonl")),
        "prior_pilot_package": prior_submission["package"],
        "prior_pilot_raw_sha256": receipt["raw_files_verified"],
        "provider_calls_allowed": 0,
        "confirmation_queries_allowed": 0,
        "synthetic_only": False,
        "candidate_selection_allowed": False,
        "canonical_acceptance_established": False,
        "interpretation": (
            "P1 attribution only; no optimized runtime or policy. "
            "Diagnostic pass is separately profiled."
        ),
    }
    save(package / "experiment.json", cfg)
    (package / "slurm").mkdir()
    with (package / "slurm/measure.sbatch").open("x") as handle:
        handle.write("""#!/usr/bin/env bash
#SBATCH --job-name=fann-cost-v1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
umask 077
exec python3 "$1/ec_job.py" "$@"
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
    if not root_name.startswith("reviews-execution-cost-v1-"):
        raise ValueError("Unexpected campaign archive name")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination / root_name
    if root.exists():
        raise ValueError(
            "Already extracted/partial return preserved; use analyze on the existing data"
        )
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 512 * 1024 * 1024:
            raise ValueError("Returned archive exceeds data budget")
        names = set()
        for member in members:
            relative = Path(member.name)
            if relative.parts[0] != root_name or member.name in names or not member.isfile():
                raise ValueError("Archive member is not a unique regular campaign file")
            names.add(member.name)
            target = safe_file(destination, member.name)
            if member.size > 128 * 1024 * 1024:
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
    from ec_report import analyze as report

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
    print(str(output / "attribution.md"))


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
