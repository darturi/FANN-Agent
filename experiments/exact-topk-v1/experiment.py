"""Build/ingest the sealed B2b package; no local dispatch or native acquisition."""

import argparse
import json
import shutil
import tarfile
from pathlib import Path

from xt_common import (
    ANCHOR_MANIFEST,
    B1B_RECEIPT_SHA,
    COUNTS,
    DESIGN_SHA,
    MID_MANIFEST_SHA,
    MID_RECEIPT_SHA,
    NAME,
    PREFIX,
    REVIEW_SHA,
    VERSION,
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
from xt_measure import order_manifest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "trials/torch-reviews-native-effort-frontier-v1/torch-native-effort-frontier-v1"
OUTPUT = ROOT / "trials/torch-reviews-exact-topk-v1"


def transfer_script(package):
    template = r"""#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  upload|download) xt_action="$1" ;;
  *) echo "Usage: bash transfer.sh upload|download" >&2; exit 2 ;;
esac
cd '@OUTPUT@'
xt_socketdir="$(mktemp -d -t fann-xt-ssh)"
xt_binding="${xt_socketdir}/submission-binding.json"
xt_options=(
  -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519
  -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -o PubkeyAuthentication=no
  -o ControlMaster=auto -o ControlPersist=600 -o "ControlPath=${xt_socketdir}/connection"
)
xt_cleanup() {
  ssh "${xt_options[@]}" -O exit dar579@dtn012.hpc.nyu.edu >/dev/null 2>&1 || true
  rm -f "$xt_binding" "${xt_socketdir}/connection"
  rmdir "$xt_socketdir" 2>/dev/null || true
}
trap xt_cleanup EXIT
if test "$xt_action" = upload; then
  printf '%s\n' 'LOCAL package checksum:'
  shasum -a 256 -c 'torch-exact-topk-v1.tar.gz.sha256'
fi
printf '%s\n' 'Connecting to Torch DTN for authentication; file transfer follows.'
if ! ssh -t "${xt_options[@]}" dar579@dtn012.hpc.nyu.edu true; then
  printf '%s\n' 'SSH connection/authentication failed before transfer. No job was submitted.' >&2
  exit 1
fi
if test "$xt_action" = upload; then
  printf '%s\n' 'Uploading archive and checksum to /home/dar579/ ...'
  scp "${xt_options[@]}" 'torch-exact-topk-v1.tar.gz' 'torch-exact-topk-v1.tar.gz.sha256' \
    dar579@dtn012.hpc.nyu.edu:/home/dar579/
  printf '%s\n' 'REMOTE package checksum on Torch:'
  ssh "${xt_options[@]}" dar579@dtn012.hpc.nyu.edu 'set -e
cd /home/dar579
sha256sum -c torch-exact-topk-v1.tar.gz.sha256'
  printf '%s\n' 'UPLOAD VERIFIED: both files are in /home/dar579/ on Torch. No job submitted.'
else
  scp "${xt_options[@]}" \
    dar579@dtn012.hpc.nyu.edu:/home/dar579/torch-exact-topk-v1/submission-binding.json "$xt_binding"
  xt_run="$( '@PYTHON@' - "$xt_binding" <<'PYBIND'
import json, re, sys
value = json.load(open(sys.argv[1]))
if value['package_manifest_sha256'] != '@MANIFEST@':
    raise SystemExit('Binding belongs to another sealed package')
run = value['campaign']
pattern = (r'/home/dar579/torch-reviews-results/reviews-exact-topk-v1-'
           r'[0-9]{8}T[0-9]{6}Z[.][A-Za-z0-9_-]+')
if not re.fullmatch(pattern, run):
    raise SystemExit('Unexpected campaign path; preserve binding and inspect status')
print(run)
PYBIND
  )"
  scp "${xt_options[@]}" "dar579@dtn012.hpc.nyu.edu:${xt_run}.tar.gz" \
    "dar579@dtn012.hpc.nyu.edu:${xt_run}.tar.gz.sha256" .
  shasum -a 256 -c "${xt_run##*/}.tar.gz.sha256"
  PYTHONDONTWRITEBYTECODE=1 '@PYTHON@' '@PACKAGE@/experiment.py' ingest \
    --archive "${xt_run##*/}.tar.gz"
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

# TORCH LOGIN: run this ONCE after upload; one job contains both temporal blocks.
(
  set -euo pipefail
  cd /home/dar579
  sha256sum -c '{NAME}.tar.gz.sha256'
  test ! -e '{NAME}'
  tar -xzf '{NAME}.tar.gz'
  source /home/dar579/torch-reviews-first/torch.env
  export TORCH_SLURM_ACCOUNT=torch_pr_288_courant
  PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{NAME}/xt_control.py submit \
    /home/dar579/torch-reviews-first /home/dar579/torch-reviews-results
)

# TORCH: safe after a fresh login; no path arguments/environment sourcing needed.
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{NAME}/xt_control.py status

# TORCH: after the job has finished; collect preserves failed raw campaigns too.
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/{NAME}/xt_control.py collect

# MAC: only after collect prints the archive; checksum + sealed data-only replay.
bash {OUTPUT}/transfer.sh download

# One allocation,4CPUs/32GiB/2hours; stop by1830 on quality failure, maximum40230 searches.
# Zero providers/fits/protected queries. Native conformance and performance remain unmeasured.
# A failed/unknown dispatch consumes the allowance. Use status; never delete a binding/reservation.
# If extraction succeeded but submit failed, keep the package and report the error.
# Do not rerun this whole block.
"""


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


def build(output=None):
    output = Path(output) if output is not None else OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    package, archive = output / NAME, output / (NAME + ".tar.gz")
    if package.exists():
        verify(package)
        if (
            not archive.exists()
            or sha(archive) != Path(str(archive) + ".sha256").read_text().split()[0]
        ):
            raise ValueError("Partial/changed package preserved; do not overwrite")
        print(str(output / "COMMANDS.txt"))
        return package
    if sha(SOURCE / "manifest.json") != ANCHOR_MANIFEST:
        raise ValueError("Sealed B1b anchor differs")
    for name, expected in read(SOURCE / "manifest.json")["files"].items():
        if sha(safe_file(SOURCE, name)) != expected:
            raise ValueError("B1b anchor changed: " + name)
    review = ROOT / "agent/docs/verification/b2a-plan-scope-audit-v1.json"
    postrun = ROOT / "agent/docs/verification/native-effort-frontier-v1-postrun.json"
    design = ROOT / "research/fannagent-exact-topk-v1-design-2026-10-25.md"
    if sha(review) != REVIEW_SHA or sha(postrun) != B1B_RECEIPT_SHA or sha(design) != DESIGN_SHA:
        raise ValueError("Pre-measurement design/review/results evidence differs")
    midpoint = (
        ROOT / "trials/torch-reviews-native-effort-midpoint-v1/torch-native-effort-midpoint-v1"
    )
    mid_receipt = ROOT / "agent/docs/verification/native-effort-midpoint-v1-postrun.json"
    if sha(midpoint / "manifest.json") != MID_MANIFEST_SHA or sha(mid_receipt) != MID_RECEIPT_SHA:
        raise ValueError("B1b2 evidence changed")
    for name, expected in read(midpoint / "manifest.json")["files"].items():
        if sha(safe_file(midpoint, name)) != expected:
            raise ValueError("B1b2 anchor file changed")
    returned = SOURCE.parent / "returned" / read(postrun)["campaign"]
    for name, expected in read(postrun)["raw_files_sha256"].items():
        if sha(safe_file(returned, name)) != expected:
            raise ValueError("Verified B1b raw source changed: " + name)
    items = lines(SOURCE / "frozen/inputs/queries.jsonl")
    groups = inventory(items)
    package.mkdir()
    shutil.copytree(SOURCE / "frozen", package / "frozen")
    for p in sorted(HERE.iterdir()):
        if p.is_file() and p.suffix in (".py", ".md") and p.name != "DESIGN.md":
            shutil.copyfile(p, package / p.name)
    for src, dest in (
        (review, "review-receipt.json"),
        (postrun, "b1b-receipt.json"),
        (design, "DESIGN.md"),
        (SOURCE / "manifest.json", "b1b-manifest.json"),
        (midpoint / "manifest.json", "b1b2-manifest.json"),
        (mid_receipt, "b1b2-receipt.json"),
    ):
        shutil.copyfile(src, package / dest)
    for name in (
        "origin-settings.json",
        "origin-source.json",
        "baseline-results.json",
        "eligibility.json",
    ):
        shutil.copyfile(SOURCE / name, package / name)
    cfg = read(SOURCE / "experiment.json")
    prior_raw = cfg["prior_raw_files"].copy()
    prior_raw[read(postrun)["campaign"]] = read(postrun)["raw_files_sha256"]
    mid_evidence = read(mid_receipt)
    mid_performance = next(
        k for k in mid_evidence["artifacts_sha256"] if k.endswith("/replay/performance.json")
    )
    if sha(ROOT / mid_performance) != mid_evidence["artifacts_sha256"][mid_performance]:
        raise ValueError("Verified B1b2 replay evidence changed")
    prior_raw[mid_evidence["campaign"]] = read(ROOT / mid_performance)["raw_files_sha256"]
    save(
        package / "experiment.json",
        {
            **protocol(),
            "development_groups": groups,
            "source_settings": cfg["source_settings"],
            "prior_pilot_package": cfg["prior_pilot_package"],
            "prior_b1b_package": "/home/dar579/torch-native-effort-frontier-v1",
            "prior_b1b2_package": "/home/dar579/torch-native-effort-midpoint-v1",
            "prior_raw_files": prior_raw,
            "snapshot_identity": read(returned / "blocks/block-0/shared-initialization.json")[
                "snapshot_identity"
            ],
            "canonical_acceptance_established": False,
            "independent_confirmation": False,
        },
    )
    save(package / "order.json", order_manifest(items))
    (package / "slurm").mkdir()
    (package / "slurm/measure.sbatch").write_text("""#!/usr/bin/env bash
#SBATCH --job-name=fann-exact-v1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
umask 077
exec python3 "$1/xt_job.py" "$@"
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
        for p in sorted(package.rglob("*")):
            if p.is_file():
                tar.add(p, arcname=NAME + "/" + str(p.relative_to(package)), recursive=False)
    Path(str(archive) + ".sha256").write_text(sha(archive) + "  " + archive.name + "\n")
    if output == OUTPUT:
        (output / "COMMANDS.txt").write_text(commands())
        (output / "transfer.sh").write_text(transfer_script(package))
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


def analyze(campaign, output=None):
    package = OUTPUT / NAME
    verify(package)
    from xt_common import campaign_identity

    name = campaign_identity(campaign, package)
    if (campaign / "analysis/failure-summary.json").exists():
        print(
            "Failed/incomplete raw campaign preserved: "
            + str(campaign)
            + "; no performance verdict or automatic retry."
        )
        return
    output = Path(output) if output else OUTPUT / "analysis-local" / name
    if output.exists() and any(output.iterdir()):
        raise ValueError(
            "Analysis output exists; choose a fresh --output or inspect preserved results"
        )
    from xt_report import analyze as replay

    result = replay(campaign, package, output)
    parity(result, read(campaign / "analysis/performance.json"))
    save(
        output / "verification.json",
        {
            "status": "passed",
            "remote_local_parity": True,
            "campaign": name,
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
        campaign = extract_data(archive, OUTPUT / "returned")
        from xt_common import campaign_identity

        if campaign.name != campaign_identity(campaign, OUTPUT / NAME):
            raise ValueError("Archive root differs from proven submission identity")
        analyze(campaign)
