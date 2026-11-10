"""Build one sealed B1b package or ingest data; never dispatch jobs locally."""

import argparse
import json
import math
import shutil
import tarfile
from pathlib import Path

from ef_common import (
    B1A_RECEIPT,
    COUNTS,
    NAME,
    P2C_CAMPAIGN,
    P2C_RECEIPT,
    PREFIX,
    SOURCE_MANIFEST,
    VERSION,
    inventory,
    lines,
    protocol,
    read,
    safe_file,
    save,
    sha,
    verify,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = (
    ROOT
    / "trials/torch-reviews-activation-timing-calibration-v1/torch-activation-timing-calibration-v1"
)
OUTPUT = ROOT / "trials/torch-reviews-native-effort-frontier-v1"


def transfer_script(package):
    template = r"""#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  upload|download) b1b_action="$1" ;;
  *) echo "Usage: bash transfer.sh upload|download" >&2; exit 2 ;;
esac
cd '@OUTPUT@'
b1b_socketdir="$(mktemp -d -t fann-b1b-ssh)"
b1b_binding="${b1b_socketdir}/submission-binding.json"
b1b_options=(
  -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519
  -o StrictHostKeyChecking=yes -o UpdateHostKeys=no
  -o ControlMaster=auto -o ControlPersist=600 -o "ControlPath=${b1b_socketdir}/connection"
)
b1b_cleanup() {
  ssh "${b1b_options[@]}" -O exit dar579@dtn012.hpc.nyu.edu >/dev/null 2>&1 || true
  rm -f "$b1b_binding" "${b1b_socketdir}/connection"
  rmdir "$b1b_socketdir" 2>/dev/null || true
}
trap b1b_cleanup EXIT
if test "$b1b_action" = upload; then
  shasum -a 256 -c '@NAME@.tar.gz.sha256'
fi
ssh -t "${b1b_options[@]}" dar579@dtn012.hpc.nyu.edu true
if test "$b1b_action" = upload; then
  scp "${b1b_options[@]}" '@NAME@.tar.gz' '@NAME@.tar.gz.sha256' \
    dar579@dtn012.hpc.nyu.edu:/home/dar579/
else
  scp "${b1b_options[@]}" \
    dar579@dtn012.hpc.nyu.edu:/home/dar579/@NAME@/submission-binding.json "$b1b_binding"
  b1b_run="$( '@PYTHON@' - "$b1b_binding" <<'PYBIND'
import json, re, sys
value = json.load(open(sys.argv[1]))
if value['package_manifest_sha256'] != '@MANIFEST@':
    raise SystemExit('Binding belongs to another sealed package')
run = value['campaign']
pattern = (r'/home/dar579/torch-reviews-results/reviews-native-effort-v1-'
           r'[0-9]{8}T[0-9]{6}Z[.][A-Za-z0-9_-]+')
if not re.fullmatch(pattern, run):
    raise SystemExit('Unexpected campaign path; preserve binding and inspect status')
print(run)
PYBIND
  )"
  scp "${b1b_options[@]}" "dar579@dtn012.hpc.nyu.edu:${b1b_run}.tar.gz" \
    "dar579@dtn012.hpc.nyu.edu:${b1b_run}.tar.gz.sha256" .
  shasum -a 256 -c "${b1b_run##*/}.tar.gz.sha256"
  PYTHONDONTWRITEBYTECODE=1 '@PYTHON@' '@PACKAGE@/experiment.py' ingest \
    --archive "${b1b_run##*/}.tar.gz"
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


def commands():
    return f"""# MAC: verify/upload through one interactive MFA session.
bash {OUTPUT}/transfer.sh upload

# TORCH LOGIN: run this ONCE after upload; both serial jobs are submitted together.
(
  set -euo pipefail
  cd /home/dar579
  sha256sum -c '{NAME}.tar.gz.sha256'
  test ! -e '{NAME}'
  tar -xzf '{NAME}.tar.gz'
  source /home/dar579/torch-reviews-first/torch.env
  export TORCH_SLURM_ACCOUNT=torch_pr_288_courant
  PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{NAME}/ef_control.py submit \
    /home/dar579/torch-reviews-first /home/dar579/torch-reviews-results
)

# TORCH: safe after a fresh login; no path arguments/environment sourcing needed.
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{NAME}/ef_control.py status

# TORCH: after both jobs have finished; collect preserves failed raw campaigns too.
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{NAME}/ef_control.py collect

# MAC: only after collect prints the archive; checksum + sealed data-only replay.
bash {OUTPUT}/transfer.sh download

# Two serial allocations, each4CPUs/32GiB/2hours,139272 search ceiling total.
# Zero providers/fits/protected queries. Native conformance and performance remain unmeasured.
# A failed/unknown dispatch consumes the allowance. Use status; never delete a binding/reservation.
# If extraction succeeded but submit failed, keep the package and report the error.
# Do not rerun this whole block.
"""


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    package, archive = OUTPUT / NAME, OUTPUT / (NAME + ".tar.gz")
    if package.exists():
        verify(package)
        if (
            not archive.exists()
            or sha(archive) != Path(str(archive) + ".sha256").read_text().split()[0]
        ):
            raise ValueError("Partial/changed package preserved; inspect instead of overwriting")
        print(str(OUTPUT / "COMMANDS.txt"))
        return package
    b1a = ROOT / "agent/docs/verification/b1a-search-effort-audit-v1.json"
    p2c = ROOT / "agent/docs/verification/activation-timing-calibration-v1-postrun.json"
    if sha(b1a) != B1A_RECEIPT or sha(p2c) != P2C_RECEIPT:
        raise ValueError("B1a/P2c evidence changed")
    if (
        sha(SOURCE / "manifest.json")
        != "6b6f216977482287838d4c9fbc06e8bb113cb283ff5c8a911ab9055cd7ae6fc0"
    ):
        raise ValueError("P2c package differs")
    for name, expected in read(SOURCE / "manifest.json")["files"].items():
        if sha(safe_file(SOURCE, name)) != expected:
            raise ValueError("P2c source changed: " + name)
    frozen = SOURCE / "frozen"
    if sha(frozen / "manifest.json") != SOURCE_MANIFEST:
        raise ValueError("Original source differs")
    returned = SOURCE.parent / "returned" / P2C_CAMPAIGN
    for name, expected in read(p2c)["raw_files_sha256"].items():
        if sha(safe_file(returned, name)) != expected:
            raise ValueError("Verified P2c raw source changed: " + name)
    original_bundle = ROOT / "trials/torch-reviews-first"
    parquet = original_bundle / "inputs/reviews.parquet"
    if sha(parquet) != "06eae31a43ecfd63a647f6fa93a9c00bcb2350ca6fe2f2bcd35d007c13b2e4ee":
        raise ValueError("Source dataset differs")
    prior_cfg = read(SOURCE / "experiment.json")
    prior_raw = {
        P2C_CAMPAIGN: read(p2c)["raw_files_sha256"],
        "reviews-selective-agent-v1-pilot-20261022T202240Z.j9ackcxc": prior_cfg[
            "prior_pilot_raw_sha256"
        ],
    }
    for name, filename in [
        ("reviews-execution-cost-v1-20261023T044408Z.a08qpwdi", "attribution-receipt.json"),
        ("reviews-prepared-policy-v1-20261023T161756Z.8uq_covr", "p2a-receipt.json"),
        ("reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0", "p2b-receipt.json"),
    ]:
        prior_raw[name] = read(SOURCE / filename)["raw_files_verified"]
    pins = {}
    for row in lines(returned / "blocks/block-0/references.jsonl"):
        pins[row["query_id"]] = {k: row[k] for k in ("truth_strict", "truth_ties", "truth_k")}
        pins[row["query_id"]]["original640"] = {
            "ids": row["native_ids"],
            "distances": row["native_distances"],
            "recall": row["native_recall"],
            "valid": True,
            "returned_count": 10,
            "duplicate_count": 0,
            "predicate_violation_count": 0,
        }
    items = lines(frozen / "inputs/queries.jsonl")
    if set(pins) != {i["query"]["id"] for i in items}:
        raise ValueError("Pinned reference inventory differs")
    import pyarrow.parquet as pq

    rows = pq.read_table(parquet, columns=["source_id", "metadata"]).to_pylist()
    rows.sort(key=lambda r: r["source_id"])
    eligibility = {
        "source_ids": [r["source_id"] for r in rows],
        "votes": [r["metadata"]["total_votes"] for r in rows],
    }
    if len(rows) != 247286 or len(set(eligibility["source_ids"])) != len(rows):
        raise ValueError("Metadata/ID coverage differs")
    package.mkdir()
    shutil.copytree(frozen, package / "frozen")
    for path in sorted(HERE.iterdir()):
        if path.is_file() and path.suffix in (".py", ".md"):
            shutil.copyfile(path, package / path.name)
    shutil.copyfile(b1a, package / "b1a-receipt.json")
    shutil.copyfile(p2c, package / "p2c-receipt.json")
    source_settings = read(original_bundle / "inputs/local-identity.json")["settings"]
    save(package / "origin-settings.json", source_settings)
    save(
        package / "origin-source.json",
        {
            "settings": source_settings,
            "metadata": read(original_bundle / "inputs/local-identity.json")["binding"]["metadata"],
            "index": {
                "oid": read(frozen / "source-index.json")["index_oid"],
                "relname": "reviews_hnsw",
            },
        },
    )
    save(package / "baseline-results.json", pins)
    save(package / "eligibility.json", eligibility)
    cfg = {
        **protocol(),
        "development_groups": inventory(items),
        "source_settings": source_settings,
        "prior_pilot_package": prior_cfg["prior_pilot_package"],
        "prior_raw_files": prior_raw,
        "independent_confirmation": False,
        "canonical_acceptance_established": False,
    }
    save(package / "experiment.json", cfg)
    (package / "slurm").mkdir()
    (package / "slurm/measure.sbatch").write_text("""#!/usr/bin/env bash
#SBATCH --job-name=fann-effort-v1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
umask 077
exec python3 "$1/ef_job.py" "$@"
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
    Path(str(archive) + ".sha256").write_text(sha(archive) + "  " + archive.name + "\n")
    (OUTPUT / "COMMANDS.txt").write_text(commands())
    (OUTPUT / "transfer.sh").write_text(transfer_script(package))
    print(
        json.dumps(
            {
                "package": str(package),
                "archive": str(archive),
                "sha256": sha(archive),
                "counts": COUNTS,
            },
            indent=2,
        )
    )
    return package


def extract_data(archive, destination):
    archive, destination = Path(archive), Path(destination)
    root_name = archive.name[:-7]
    if not archive.name.endswith(".tar.gz") or not root_name.startswith(PREFIX):
        raise ValueError("Unexpected campaign archive name")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination / root_name
    if root.exists():
        raise ValueError("Already extracted/partial return preserved; use analyze on existing data")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 2 * 1024**3:
            raise ValueError("Returned archive exceeds data budget")
        names = set()
        for member in members:
            relative = Path(member.name)
            if (
                not relative.parts
                or relative.parts[0] != root_name
                or member.name in names
                or not member.isfile()
            ):
                raise ValueError("Member is not a unique regular campaign file")
            names.add(member.name)
            safe_file(destination, member.name)
            if member.size > 256 * 1024**2:
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
        if not math.isfinite(left) or not math.isfinite(right) or abs(left - right) > 1e-12:
            raise ValueError("Remote/local float differs: " + path)
    elif left != right:
        raise ValueError("Remote/local value differs: " + path)


def analyze(campaign, output=None):
    # Execute only sealed local code, even if the mutable development script is used.
    package = OUTPUT / NAME
    verify(package)
    import importlib.util
    import sys

    sys.path.insert(0, str(package))
    spec = importlib.util.spec_from_file_location("sealed_b1b_report", package / "ef_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if (campaign / "analysis/failure-summary.json").exists():
        # Failure is not treated as verified performance evidence.
        print(
            "Failed/incomplete campaign preserved at "
            + str(campaign)
            + "; no performance verdict or automatic retry."
        )
        return
    output = Path(output) if output else OUTPUT / "analysis-local" / campaign.name
    if output.exists() and any(output.iterdir()):
        raise ValueError("Analysis output exists; inspect it or choose a fresh --output")
    result = module.analyze(campaign, package, output)
    parity(result, read(campaign / "analysis/performance.json"))
    save(
        output / "verification.json",
        {
            "status": "passed",
            "remote_local_parity": True,
            "absolute_float_tolerance": 1e-12,
            "package_manifest_sha256": sha(package / "manifest.json"),
            "canonical_acceptance_established": False,
        },
    )
    print(str(output / "report.txt"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("package")
    p = sub.add_parser("ingest")
    p.add_argument("--archive", type=Path, required=True)
    p = sub.add_parser("analyze")
    p.add_argument("--campaign", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command != "package" and HERE != OUTPUT / NAME:
        # Restart from sealed local code so mutable modules cannot stay cached.
        import subprocess
        import sys

        verify(OUTPUT / NAME)
        raise SystemExit(
            subprocess.call([sys.executable, str(OUTPUT / NAME / "experiment.py"), *sys.argv[1:]])
        )
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
