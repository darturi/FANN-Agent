"""Build and locally verify the held Torch kit for the interleaved A/A calibration."""

import json
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

import rb_interleave
from rb_native import load_stage
from rb_oracle_prepare import substitute_assignment
from rb_package import HERE, OUTPUT, PACKAGE_NAME, REQUEST_TIMING_BASE, copy_bytes
from rb_plan import file_sha, pinned, require
from rb_seal import json_bytes, make_archive, seal_directory, verify_directory, write_once

NAME = "interleaved-aa-v1"
PARENT = OUTPUT / "persistent-reader-v1" / PACKAGE_NAME
HOST = OUTPUT / "oracle-persistent-v1"
HOST_PINS = {
    "rb_host.py": "92652780b07279ca7c12931cb8a2c1afb37ce1c5a9c581f05997e23323b9f54e",
    "rb_site.py": "8c934d6c22d85d2de2c5caf214830c10f8c63357f1d31262b83fc1ad7c039099",
    "rb_seal.py": "3d0cae1765c2f8fc23e23bfdc1ec939a0c750ae57c455782e45ba38f2bf45557",
}
PREFLIGHT_PIN = "9e123f9fe721a86ad00088a42069fd1cc9ba2a62b907786b13b49bad0b2b997a"
PRIOR_RESERVATION = (
    "29343aaf1925ffe76308ac23d8c9997d7fd93e47b472e52de3a2ca8818917d67"
    "  $results/$name-oracle-persistent-v1-reservation/reservation.json"
)


@dataclass(frozen=True)
class HostSource:
    folder: Path
    file_pins: dict
    preflight_pin: str
    prior_name: str
    reservation_line: str


INTERLEAVED_HOST_SOURCE = HostSource(
    HOST, HOST_PINS, PREFLIGHT_PIN, "oracle-persistent-v1", PRIOR_RESERVATION
)


def command(*args):
    return json.loads(
        subprocess.check_output([sys.executable, "-EsB", *map(str, args)], text=True, timeout=90)
    )


def build_host(
    output,
    archive,
    manifest,
    identity,
    *,
    study=NAME,
    job_name="fann-reviews-aa-v1",
    comment_prefix="rbaa1-",
    source=INTERLEAVED_HOST_SOURCE,
):
    body = pinned(source.folder / "rb_host.py", source.file_pins["rb_host.py"]).decode()
    for key, value in {
        "RESERVATION": f'NAME + "-{study}-reservation"',
        "MANIFEST": json.dumps(manifest),
        "ARCHIVE": json.dumps(file_sha(archive)),
        "CANDIDATE": json.dumps(identity),
        "JOB_NAME": json.dumps(job_name),
        "COMMENT": f"{json.dumps(comment_prefix)} + MANIFEST[:24]",
    }.items():
        body = substitute_assignment(body, key, value)
    copy_bytes(output / "rb_host.py", body.encode())
    for name in ("rb_site.py", "rb_seal.py"):
        copy_bytes(output / name, pinned(source.folder / name, source.file_pins[name]))
    preflight = pinned(source.folder / "TORCH-PREFLIGHT.sh", source.preflight_pin).decode()
    # Replace stage and current reservation names, preserving old checksum paths.
    preflight = preflight.replace(
        f"reviews-{source.prior_name}.XXXXXXXX", f"reviews-{study}.XXXXXXXX"
    ).replace(
        f'next="$results/$name-{source.prior_name}-reservation"',
        f'next="$results/$name-{study}-reservation"',
    )
    require(preflight.count("\nREVIEWS_CHECKSUMS\n") == 1, "Expected one reservation pin block")
    preflight = preflight.replace(
        "\nREVIEWS_CHECKSUMS\n", f"\n{source.reservation_line}\nREVIEWS_CHECKSUMS\n"
    )
    copy_bytes(output / "TORCH-PREFLIGHT.sh", preflight.encode())
    subprocess.run(["bash", "-n", str(output / "TORCH-PREFLIGHT.sh")], check=True)
    upload = output / f"torch-upload-{study}.tar"
    names = (*source.file_pins, "TORCH-PREFLIGHT.sh", archive.name)
    with tarfile.open(upload, "x") as tar:
        for name in names:
            tar.add(output / name, arcname=name, recursive=False)
    with tempfile.TemporaryDirectory() as scratch:
        stage = Path(scratch)
        with tarfile.open(upload) as tar:
            for name in (*source.file_pins, archive.name):
                copy_bytes(stage / name, tar.extractfile(name).read())
        receipt = command(stage / "rb_host.py", "stage", stage / archive.name)
    require(
        receipt["status"] == "staged_held" and receipt["package_manifest_sha256"] == manifest,
        "Held host stage differs",
    )
    return upload, receipt["host_kit_sha256"]


def assemble(output, identity):
    output.mkdir(mode=0o700)
    package = output / PACKAGE_NAME
    package.mkdir(mode=0o700)
    replacements = {"rb_native.py", "rb_measure.py"}
    for name, record in verify_directory(PARENT, REQUEST_TIMING_BASE).items():
        data = (
            (HERE / name).read_bytes()
            if name in replacements
            else pinned(PARENT / name, record["sha256"])
        )
        copy_bytes(package / name, data)
    copy_bytes(package / "rb_interleave.py", (HERE / "rb_interleave.py").read_bytes())
    manifest = seal_directory(package)
    review = command(package / "rb_native.py", "verify", package, manifest)
    require(
        review
        == {
            "status": "verified_held",
            "candidate": identity,
            "sessions": 60,
            "cases": 600,
            "interleaved_calibration": True,
            "dispatch_released": False,
        },
        "Sealed calibration guest review differs",
    )
    archive = output / f"{PACKAGE_NAME}.tar.gz"
    archive_sha = make_archive(package, archive, manifest)
    upload, kit = build_host(output, archive, manifest, identity)
    return {
        **review,
        "previous_package_manifest_sha256": REQUEST_TIMING_BASE,
        "package_manifest_sha256": manifest,
        "archive_sha256": archive_sha,
        "host_kit_sha256": kit,
        "upload_archive": upload.name,
        "upload_sha256": file_sha(upload),
        "limits": {
            "allocations": 1,
            "physical_cores": 4,
            "memory_gib": 32,
            "wall_minutes": 120,
            "no_retry": True,
            "timed_searches": rb_interleave.Meter.search_limits["timing"],
            "primary_searches": rb_interleave.MAIN_PAIRS * 120,
            "instrumented_searches": rb_interleave.PROBE_PAIRS * 120,
            "reference_readers": 1,
            "timed_reader_lifetimes": 2 * rb_interleave.PAIR_COUNT,
            "max_concurrent_timed_readers": 2,
            "max_concurrent_searches": 1,
            "seed_installs": rb_interleave.Meter.install_limits["timing"],
            "exact_searches": 0,
            "provider_calls": 0,
            "confirmation_queries": 0,
        },
        "study": {
            "families": list(rb_interleave.FAMILIES),
            "epochs": 3,
            "workloads": 10,
            "requests_per_reader": 60,
            "warmup_requests_per_reader": 10,
            "requests_per_alternation": rb_interleave.CHUNK,
            "instrumented_workloads": [
                f"reader-workload-{block + 1:02}" for block in rb_interleave.PROBE_BLOCKS
            ],
            "primary_endpoint": "Sum of ten active steady chunk intervals per reader "
            "divided by 50 requests",
            "aa_gate": "Both arms must pass the original clustered absolute and relative "
            "95% equivalence intervals of ±0.10 ms/request and ±log(1.02)",
            "instrumentation": "Per-request PostgreSQL command duration and backend CPU, "
            "run-queue delay when enabled, and context switch counts. "
            "These runs follow the uninstrumented calibration.",
        },
        "next_gate": "Zero-allocation Torch preflight. Fresh approval required for dispatch.",
        "offline_accounting": {"allocations": 0, "searches": 0, "confirmation_queries": 0},
    }


def build():
    destination = OUTPUT / NAME
    require(not destination.exists() and not destination.is_symlink(), "Study already exists")
    stage = load_stage(PARENT, REQUEST_TIMING_BASE)
    rb_interleave.attach(stage)
    with tempfile.TemporaryDirectory(dir=OUTPUT, prefix=".interleaved-build-") as work:
        output = Path(work) / NAME
        review = assemble(output, stage.study_identity)
        write_once(output / "PACKAGE-REVIEW.json", json_bytes(review))
        require(not destination.exists() and not destination.is_symlink(), "Study appeared")
        output.rename(destination)
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    build()
