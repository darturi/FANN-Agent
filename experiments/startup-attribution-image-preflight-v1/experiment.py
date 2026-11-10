"""Build the small read-only image-inventory capsule; no database or scheduler use."""

import argparse
import json
import shutil
import sys
import tarfile
from pathlib import Path

from inspect_image import IMAGE, NAME, PARENT, file_sha, read_json, verify

ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1"
OUTPUT = ROOT / "trials/torch-reviews-startup-attribution-v1-release"
REFERENCE = (
    "pc_common.py",
    "legacy_common.py",
    "sa_driver.py",
    "sa_monitor.py",
    "CONTRACT.json",
    "RESOURCE-CONTRACT.json",
    "CORRECTION-DESIGN.json",
    "DRIVER-HOOKS.json",
    "DRIVER-REFERENCE.json",
    "frozen/no_models.py",
)


def save(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")


def build(output=OUTPUT, testing=False):
    output = Path(output)
    output.mkdir(exist_ok=True, parents=True)
    package = output / NAME
    if package.exists():
        raise FileExistsError("Preserve existing inventory capsule")
    if not testing:
        checks = read_json(OUTPUT / "local-checks-source.json")
        if (
            checks["status"] != "pass"
            or checks["tests_run"] < 25
            or checks["source_files_sha256"] != {p.name: file_sha(p) for p in HERE.glob("*.py")}
        ):
            raise ValueError("Current source checks are required before handoff packaging")
    if file_sha(SOURCE / "manifest.json") != PARENT:
        raise ValueError("A1 parent seal changed")
    parent = read_json(SOURCE / "manifest.json")
    names = set(REFERENCE) | {n for n in parent["files"] if n.startswith("frozen/vendor/")}
    for n in names:
        if file_sha(SOURCE / n) != parent["files"][n]:
            raise ValueError("A1 reference differs: " + n)
    package.mkdir()
    for n in sorted(names):
        dst = package / "reference" / n
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / n, dst)
    shutil.copyfile(SOURCE / "manifest.json", package / "PARENT-A1-MANIFEST.json")
    for n in (
        "inspect_image.py",
        "run-on-torch.sh",
        "README.md",
        "experiment.py",
        "test_probe.py",
        "run_checks.py",
        "TRANSFER-template.sh",
    ):
        shutil.copyfile(HERE / n, package / n)
    save(
        package / "PROBE-CONTRACT.json",
        dict(
            schema="startup-attribution.image-preflight.v1",
            parent_A1_manifest_sha256=PARENT,
            image_sha256=IMAGE,
            native_handoff_released=False,
            searches=0,
            SQL=0,
            database_connections=0,
            snapshot_calls=0,
            slurm_submissions=0,
            invocations_max=1,
            reference_files_sha256={n: parent["files"][n] for n in sorted(names)},
            limits=dict(
                wall_seconds=30,
                CPU_seconds=15,
                address_space_bytes=2 * 1024**3,
                wrapper_wall_seconds=60,
                wrapper_kill_grace_seconds=5,
                report_bytes=128 * 1024,
                capsule_bytes=16 * 1024**2,
                source_reads=128,
                source_bytes=4 * 1024**2,
                source_file_bytes=65536,
                literal_callbacks=16,
            ),
            decision=(
                "Inventory only; any mismatch holds release for separate compatibility review. "
                "No automatic upgrade, substitution, retry or job."
            ),
            no_data_mounts=True,
            no_proc_cgroup_or_resource_margin_qualification=True,
        ),
    )
    save(
        package / "manifest.json",
        dict(
            schema="startup-attribution.image-capsule.v1",
            files={
                str(p.relative_to(package)): file_sha(p)
                for p in sorted(package.rglob("*"))
                if p.is_file()
            },
        ),
    )
    verify(package)
    archive = output / (NAME + ".tar.gz")
    with tarfile.open(archive, "x:gz") as tar:
        for p in sorted(package.rglob("*")):
            if p.is_file():
                tar.add(p, arcname=NAME + "/" + str(p.relative_to(package)), recursive=False)
    with Path(str(archive) + ".sha256").open("x") as f:
        f.write(file_sha(archive) + "  " + archive.name + "\n")
    if not testing:
        with (output / "transfer.sh").open("x") as f:
            f.write(transfer_script(package, output))
        with (output / "COMMANDS.txt").open("x") as f:
            f.write(commands(package, output))
    return package


def transfer_script(package, output):
    text = (HERE / "TRANSFER-template.sh").read_text()
    for key, value in dict(
        OUTPUT=str(output),
        PACKAGE=str(package),
        NAME=NAME,
        PYTHON=sys.executable,
        MANIFEST=file_sha(package / "manifest.json"),
        ARCHIVE_SHA=file_sha(package.parent / (NAME + ".tar.gz")),
    ).items():
        text = text.replace("@" + key + "@", value)
    return text


def commands(package, output):
    archive_sha = file_sha(package.parent / (NAME + ".tar.gz"))
    return f"""# A2 IMAGE INVENTORY ONLY. No job, database, snapshot, SQL or search.
# MAC: authenticate, then wait for UPLOAD VERIFIED.
bash {output}/transfer.sh upload

# TORCH LOGIN: run this block once after verified upload.
(
  set -euo pipefail
  cd /home/dar579
  printf '%s\\n' '{archive_sha}  {NAME}.tar.gz' | sha256sum -c -
  test ! -e {NAME}
  tar -xzf {NAME}.tar.gz
  bash /home/dar579/{NAME}/run-on-torch.sh
)

# MAC: download the small inventory, even if its exit code was nonzero.
bash {output}/transfer.sh download

# Reply "Downloaded" or paste the exact error. Preserve binding/results.
# Do not submit A2, repeat the inventory, change the image or update dependencies.
# A2 acquisition and full B2f are held pending compatibility review.
"""


def check_return(directory, package=OUTPUT / NAME):
    """Data-only check; this result cannot open the native release gate."""
    directory, package = Path(directory), Path(package)
    verify(package)
    expected = {"image-capability.json", "stderr.log", "exit-code.txt"}
    for p in directory.iterdir():
        if (
            p.is_symlink()
            or not p.is_file()
            or p.name not in expected | {"SHA256SUMS"}
            or p.stat().st_size > (128 * 1024 if p.name == "image-capability.json" else 256 * 1024)
        ):
            raise ValueError("Unexpected/oversize returned evidence")
    rows = (directory / "SHA256SUMS").read_text().splitlines()
    found = set()
    for row in rows:
        h, n = row.split()
        if n not in expected or n in found or file_sha(directory / n) != h:
            raise ValueError("Returned inventory checksum/name differs")
        found.add(n)
    if found != expected:
        raise ValueError("Incomplete return checksum inventory")
    report = read_json(directory / "image-capability.json")
    if (
        report["image_sha256"] != IMAGE
        or report["parent_A1_manifest_sha256"] != PARENT
        or report["capsule_manifest_sha256"] != file_sha(package / "manifest.json")
        or report["native_handoff_released"] is not False
    ):
        raise ValueError("Returned inventory identity differs")
    complete = report["status"] in (
        "inventory_complete_reference_match",
        "inventory_complete_reference_mismatch",
    )
    if not complete and report["status"] != "inventory_incomplete":
        raise ValueError("Unknown inventory status")
    exit_code = int((directory / "exit-code.txt").read_text())
    if complete and exit_code != 0:
        raise ValueError("Complete inventory has failed process exit")
    if complete:
        from inspect_image import compare

        differences = compare(
            report["actual_driver"], read_json(package / "reference/DRIVER-REFERENCE.json")
        )
        if differences != report["A1_reference_differences"]:
            raise ValueError("Returned mismatch accounting differs")
        status = (
            "inventory_complete_reference_mismatch"
            if differences
            else "inventory_complete_reference_match"
        )
        if report["status"] != status:
            raise ValueError("Returned status differs from identities")
        if (
            not report["literal_monitoring"]["restored"]
            or not 0 < report["literal_monitoring"]["events"] <= 16
            or not report["original_function_mapping"]["local_masks_clear"]
            or not report["original_function_mapping"]["original_bindings_unchanged"]
        ):
            raise ValueError("Incomplete mechanism evidence")
        if report["original_function_mapping"]["source_sha256"] != [
            "bc743c14178dbe30ab705dc790db20fc7b045e4c30395e2488da21ab6266834d",
            "0ebac2227ab66c07b7b1271c6aeb294a9061329e6d2817c52dadb63c9b9cf4fa",
        ]:
            raise ValueError("Original function source identity differs")
        for n in (
            "searches",
            "snapshot_calls",
            "database_connections",
            "SQL",
            "slurm_submissions",
            "provider_calls",
        ):
            if report[n] != 0:
                raise ValueError("Inventory action exceeds scope")
    return dict(
        status=report["status"],
        transport_integrity="pass",
        native_handoff_released=False,
        next="Separate compatibility review; no automatic native launch",
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["package", "check-return"])
    p.add_argument("--directory", type=Path)
    a = p.parse_args()
    if a.command == "package":
        print(build())
    else:
        print(json.dumps(check_return(a.directory), indent=2))


if __name__ == "__main__":
    main()
