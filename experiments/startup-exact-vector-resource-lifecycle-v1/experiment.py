"""Build a distinct resource seal and ingest returned files strictly as data."""

import argparse
import re
import shutil
import tarfile
from pathlib import Path

from pc_common import NAME, PREFIX, VERSION, protocol, read, safe_file, save, sha, verify

HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
OUTPUT = ROOT / "trials/torch-reviews-startup-exact-vector-resource-v1-path-fix"
SOURCE = ROOT / "trials/torch-reviews-startup-resource-stream-v1/torch-startup-resource-stream-v1"
REFERENCE = (
    HERE / "reference"
    if (HERE / "reference").exists()
    else ROOT
    / "trials"
    / "torch-reviews-startup-attribution-v1-image-reference"
    / "torch-startup-attribution-v1-image-reference"
)
QUALIFIED = (
    ROOT / "trials/torch-reviews-startup-exact-vector-compatibility-v1/postrun-audit-2026-10-31"
)


def copy_verified(source, destination, manifest):
    destination.mkdir(parents=True)
    for name, expected in manifest.items():
        original = safe_file(source, name)
        if sha(original) != expected:
            raise ValueError("Immutable builder input changed: " + str(original))
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)


def additions():
    main_output = ROOT / "trials/torch-reviews-startup-attribution-v1-image-reference"
    main_campaign = "reviews-startup-attribution-v1-image-reference-20261030T213446Z.cmd7zvbo"
    correctness = ROOT / "trials/torch-reviews-startup-exact-vector-compatibility-v1"
    correctness_campaign = read(QUALIFIED / "returned-verification.json")["campaign"]
    result = {}
    for label, package, remote, campaign, output, reservation in [
        (
            "completed_main_A2",
            REFERENCE,
            Path("/home/dar579/torch-startup-attribution-v1-image-reference"),
            main_campaign,
            main_output,
            ".torch-startup-attribution-v1-reservation.json",
        ),
        (
            "completed_A3_correctness",
            correctness / "torch-startup-exact-vector-compatibility-v1",
            Path(
                "/scratch/dar579/torch-reviews/a3-correctness-packages/torch-startup-exact-vector-compatibility-v1"
            ),
            correctness_campaign,
            correctness,
            ".torch-startup-exact-vector-compatibility-v1-reservation.json",
        ),
    ]:
        manifest = read(package / "manifest.json")
        result[label] = dict(
            directory=str(remote),
            files_sha256={**manifest["files"], "manifest.json": sha(package / "manifest.json")},
            binding=dict(
                campaign="/home/dar579/torch-reviews-results/" + campaign,
                package_manifest_sha256=sha(package / "manifest.json"),
            ),
            reservation_name=reservation,
        )
        raw = output / "returned" / campaign
        result[label + "_return"] = dict(
            directory="/home/dar579/torch-reviews-results/" + campaign,
            files_sha256={
                str(p.relative_to(raw)): sha(p) for p in sorted(raw.rglob("*")) if p.is_file()
            },
        )
    return result


def build(output=OUTPUT, testing=False):
    if not testing:
        raise RuntimeError("Offline correction: production capsule creation is disabled")
    output = Path(output)
    output.mkdir(exist_ok=True, parents=True)
    package = output / NAME
    if package.exists():
        raise FileExistsError("Preserve the existing complete/partial resource seal")
    freeze = read(HERE / "RESOURCE-FREEZE.json")
    source = ROOT / freeze["baseline"]["resource_package"]
    reference = ROOT / freeze["baseline"]["reference_package"]
    if sha(source / "manifest.json") != freeze["baseline"]["manifest_sha256"]:
        raise ValueError("Frozen resource baseline differs")
    if sha(reference / "manifest.json") != freeze["baseline"]["reference_manifest_sha256"]:
        raise ValueError("Frozen qualified main reference differs")
    if not testing:
        checks = read(OUTPUT / "local-checks-source.json")
        if (
            checks["status"] != "pass"
            or checks["source_files_sha256"] != {p.name: sha(p) for p in HERE.glob("*.py")}
            or checks["failures"]
            or checks["errors"]
            or checks["skipped"]
            or checks["denied_actions"]
        ):
            raise RuntimeError("Complete current guarded source checks required")
    copy_verified(source, package, freeze["baseline"]["files_sha256"])
    # Historical stream tests are preserved in their old seal, never relabeled
    # as new resource tests. Only the explicit new suite is collected below.
    for p in list(package.glob("test_*.py")) + [
        package / "si_stream.py",
        package / "LOCAL_CHECKS.json",
    ]:
        p.unlink(missing_ok=True)
    copy_verified(reference, package / "reference", freeze["baseline"]["reference_files_sha256"])
    shutil.copyfile(reference / "manifest.json", package / "reference/manifest.json")
    # Explicit source recipes exclude generated release/receipt/submission state.
    recipes = (
        "B2F-DESIGN.md",
        "COMMANDS-template.txt",
        "CONTRACT.json",
        "CORRECTION-DESIGN.json",
        "DESIGN.md",
        "DRIVER-HOOKS.json",
        "DRIVER-REFERENCE.json",
        "IMAGE-REFERENCE.json",
        "LAUNCHER.sh",
        "README.md",
        "RESOURCE-AMENDMENT-1.json",
        "RESOURCE-CONTRACT.json",
        "RESOURCE-DESIGN.md",
        "RESOURCE-FREEZE.json",
        "PATH-FIX-FREEZE.json",
        "SCHEDULE.json",
        "ev_host.py",
        "ev_cleanup.py",
        "OFFLINE-FREEZE.json",
        "OFFLINE-AMENDMENT-1.json",
        "OFFLINE-AMENDMENT-2.json",
        "test_lifecycle.py",
        "ev_metadata.py",
        "ev_report.py",
        "ev_startup.py",
        "experiment.py",
        "identity_repair.py",
        "legacy_common.py",
        "legacy_metadata.py",
        "origin-settings.json",
        "pc_common.py",
        "pc_control.py",
        "pc_interface.py",
        "pc_job.py",
        "pc_metadata.py",
        "pc_proc.py",
        "pc_resources.py",
        "pc_restore.py",
        "pc_results.py",
        "pc_runtime.py",
        "pc_settings.py",
        "pc_snapshot.py",
        "pc_trace.py",
        "quota_base.py",
        "run_checks.py",
        "si_verify.py",
        "sr_host.py",
        "sr_interface.py",
        "sr_memory.py",
        "sr_report.py",
        "sr_sampler.py",
        "test_fixtures.py",
        "test_host_resource.py",
        "test_memory.py",
        "test_resource.py",
    )
    for name in recipes:
        shutil.copyfile(HERE / name, package / name)
    shutil.copytree(HERE / "a3", package / "a3")
    shutil.copyfile(
        ROOT / "trials/torch-reviews-startup-exact-vector-v1/A3-FREEZE.json",
        package / "A3-FREEZE.json",
    )
    for name, expected in freeze["qualified_native_correctness"]["proof_packet_sha256"].items():
        original = QUALIFIED / "qualified-receipts" / name
        if sha(original) != expected:
            raise ValueError("Authentic target proof changed")
        shutil.copyfile(original, package / name)
    save(package / "PROTECTED-ADDITIONS.json", additions())
    save(
        package / "NATIVE-RELEASE.json",
        dict(
            schema="startup-exact-vector.resource-release.v1",
            name=NAME,
            integration_tests=56,
            code_sha256=freeze["qualified_native_correctness"]["code_sha256"],
            full_B2f_released=False,
            qualification_audit_sha256=sha(package / "QUALIFICATION-AUDIT.json"),
            resource_freeze_sha256=sha(package / "RESOURCE-FREEZE.json"),
            scope=dict(
                allocations=1,
                wall_seconds=3600,
                physical_cpus=4,
                memory_gib=32,
                ANN_searches=0,
                exact_searches=0,
                snapshot_scans=1,
                data_verification_scans=4,
                reserve_bytes=2 * 1024**3,
                workspace_bytes=2 * 1024**3,
                positive_limit_events_allowed=False,
                cache_subtraction=False,
            ),
        ),
    )
    cfg = read(source / "experiment.json")
    cfg.update(protocol())
    cfg.update(
        synthetic_fixture=testing,
        local_readiness="synthetic_fixture" if testing else "source_and_target_checks_passed",
    )
    (package / "experiment.json").unlink()
    save(package / "experiment.json", cfg)
    if not testing:
        shutil.copyfile(OUTPUT / "local-checks-source.json", package / "LOCAL_CHECKS.json")
        shutil.copyfile(OUTPUT / "local-checks-sealed.json", package / "SEALED_CHECKS.json")
    shutil.copyfile(HERE / "LAUNCHER.sh", package / "slurm/measure.sbatch")
    reseal(package)
    verify(package)
    if not testing:
        from pc_common import require_native_release

        require_native_release(package)
        archive = output / (NAME + ".tar.gz")
        with tarfile.open(archive, "x:gz") as tar:
            for p in sorted(package.rglob("*")):
                if p.is_file():
                    tar.add(p, arcname=NAME + "/" + str(p.relative_to(package)), recursive=False)
        with Path(str(archive) + ".sha256").open("x") as handle:
            handle.write(sha(archive) + "  " + archive.name + "\n")
    return package


def reseal(package):
    path = package / "manifest.json"
    path.unlink(missing_ok=True)
    save(
        path,
        dict(
            version=VERSION,
            files={
                str(p.relative_to(package)): sha(p)
                for p in sorted(package.rglob("*"))
                if p.is_file() and p.name != "submission-binding.json"
            },
        ),
    )


def extract_data(archive, destination):
    archive, destination = Path(archive), Path(destination)
    rootname = archive.name.removesuffix(".tar.gz")
    if not archive.name.endswith(".tar.gz") or not re.fullmatch(
        re.escape(PREFIX) + r"[0-9]{8}T[0-9]{6}Z\.[A-Za-z0-9_-]+", rootname
    ):
        raise ValueError("Unexpected resource campaign archive")
    destination.mkdir(exist_ok=True, parents=True)
    root = destination / rootname
    if root.exists():
        raise FileExistsError("Preserve existing complete/partial returned evidence")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 512 * 1024**2:
            raise ValueError("Returned whole-campaign raw cap")
        names = set()
        for m in members:
            p = Path(m.name)
            if (
                not m.isfile()
                or m.name in names
                or not p.parts
                or p.parts[0] != rootname
                or m.size > 256 * 1024**2
            ):
                raise ValueError("Unsafe/nonregular/duplicate returned member")
            safe_file(destination, m.name)
            names.add(m.name)
        for m in members:
            target = safe_file(destination, m.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(m) as source, target.open("xb") as out:
                shutil.copyfileobj(source, out)
    return root


def analyze(campaign, output=None, package=None):
    from ev_report import validate
    from pc_common import campaign_identity
    from sr_report import analyze as replay

    package = Path(package) if package else OUTPUT / NAME
    verify(package)
    campaign = Path(campaign)
    name = campaign_identity(campaign, package)
    run = campaign / "run"
    if (
        not (run / "status.json").exists()
        or read(run / "status.json")["status"] != "complete"
        or not (run / "host-exit.json").exists()
        or read(run / "host-exit.json")["exit_code"]
    ):
        print(
            "Failed/incomplete resource raw preserved; no margin verdict or retry: " + str(campaign)
        )
        return
    proof = validate(campaign, package)
    destination = Path(output) if output else OUTPUT / "analysis-local" / name
    result = replay(campaign, package, destination)
    save(destination / "A3-startup-proof.json", proof)
    print(str(destination / "report.txt"))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("package", "ingest", "analyze"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--campaign", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "package":
        print(build())
    elif args.command == "ingest":
        archive = args.archive.resolve()
        if Path(str(archive) + ".sha256").read_text().split() != [sha(archive), archive.name]:
            raise ValueError("Returned archive checksum differs")
        campaign = extract_data(archive, OUTPUT / "returned")
        analyze(campaign)
    else:
        analyze(args.campaign.resolve(), args.output)


if __name__ == "__main__":
    main()
