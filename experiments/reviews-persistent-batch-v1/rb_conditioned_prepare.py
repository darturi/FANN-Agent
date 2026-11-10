"""Build and locally verify the held Torch kit for same-reader A/A calibration."""

import json
import tempfile
from pathlib import Path

import rb_conditioned
import rb_interleave as paired
from rb_interleave_prepare import HostSource, build_host, command
from rb_native import load_stage
from rb_package import HERE, OUTPUT, PACKAGE_NAME, copy_bytes
from rb_persistent import EPOCHS, STEADY_REQUESTS, WORKLOADS
from rb_plan import PHASE_SECONDS, SESSION_LENGTH, file_sha, pinned, require
from rb_seal import json_bytes, make_archive, seal_directory, verify_directory, write_once

NAME = "conditioned-aa-v1"
PARENT = OUTPUT / "interleaved-aa-v1" / PACKAGE_NAME
PARENT_MANIFEST = "72fcd7580e2ccc056a3f5a9874926fbe693ab102fc10cc0933b5ee32a1883e53"
HOST = HostSource(
    OUTPUT / "reader-switch-v1",
    {
        "rb_host.py": "cdddb4df51c26bf00a43eeff33ec36036f62988a3d2a23be1b912f33f0e83a11",
        "rb_site.py": "8c934d6c22d85d2de2c5caf214830c10f8c63357f1d31262b83fc1ad7c039099",
        "rb_seal.py": "3d0cae1765c2f8fc23e23bfdc1ec939a0c750ae57c455782e45ba38f2bf45557",
    },
    "bb56348234a6a030dd4a54db184ad381b354776e61f308e38a2cdcec099591d1",
    "reader-switch-v1",
    "fc37bb24711c04d5ebbf4f4f425c6306e522e561469d8b3bcb036624655d0bdd"
    "  $results/$name-reader-switch-v1-reservation/reservation.json",
)


def assemble(output, identity):
    output.mkdir(mode=0o700)
    package = output / PACKAGE_NAME
    package.mkdir(mode=0o700)
    replacements = {"rb_native.py", "rb_interleave.py"}
    for name, record in verify_directory(PARENT, PARENT_MANIFEST).items():
        data = (
            (HERE / name).read_bytes()
            if name in replacements
            else pinned(PARENT / name, record["sha256"])
        )
        copy_bytes(package / name, data)
    copy_bytes(package / "rb_conditioned.py", (HERE / "rb_conditioned.py").read_bytes())
    manifest = seal_directory(package)
    review = command(package / "rb_native.py", "verify", package, manifest)
    require(
        review
        == {
            "status": "verified_held",
            "candidate": identity,
            "sessions": 60,
            "cases": 600,
            "conditioned_calibration": True,
            "dispatch_released": False,
        },
        "Sealed conditioned calibration guest review differs",
    )
    archive = output / f"{PACKAGE_NAME}.tar.gz"
    archive_sha = make_archive(package, archive, manifest)
    upload, kit = build_host(
        output,
        archive,
        manifest,
        identity,
        study=NAME,
        job_name="fann-reviews-conditioned-aa-v1",
        comment_prefix="rbcond1-",
        source=HOST,
    )
    meter = rb_conditioned.Meter
    readers = meter.reader_limits["timing"]
    measured = readers * STEADY_REQUESTS
    return {
        **review,
        "guest_parent_manifest_sha256": PARENT_MANIFEST,
        "reader_switch_diagnostic_job_id": "22491143",
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
            "timing_seconds": PHASE_SECONDS["timing"],
            "no_retry": True,
            "search_attempts": meter.search_limits["timing"],
            "measured_searches": measured,
            "conditioning_searches": measured,
            "initial_warmup_searches": readers * SESSION_LENGTH,
            "reference_readers": meter.reader_limits["reference"],
            "timed_reader_lifetimes": readers,
            "max_concurrent_timed_readers": meter.timing_reader_capacity,
            "max_concurrent_searches": 1,
            "seed_installs": meter.install_limits["timing"],
            "exact_searches": 0,
            "provider_calls": 0,
            "confirmation_queries": 0,
        },
        "study": {
            "families": list(paired.FAMILIES),
            "workloads": WORKLOADS,
            "epochs": EPOCHS,
            "initial_warmup_per_reader": SESSION_LENGTH,
            "requests_per_timed_block": paired.CHUNK,
            "conditioning": "Replay the preceding five queries on the same reader immediately "
            "before each timed block. Keep both readers open and preserve balanced block order.",
            "primary_endpoint": "Sum of active steady block intervals divided by 50 requests "
            "per reader. Retain the first request of every block. Exclude initial warmup and "
            "conditioning symmetrically.",
            "aa_gate": "Both families must pass the original clustered 95% intervals of "
            "±0.10 ms/request and ±log(1.02).",
            "quality_gate": "Check every result and route against sealed development evidence "
            "and apply the original seed recall gate.",
            "purpose": "Qualify the conditioned timing setup for a later development comparison.",
        },
        "next_gate": "Zero-allocation Torch preflight. Fresh approval required for dispatch.",
        "offline_accounting": {"allocations": 0, "searches": 0, "confirmation_queries": 0},
    }


def build():
    destination = OUTPUT / NAME
    require(not destination.exists() and not destination.is_symlink(), "Study already exists")
    stage = load_stage(PARENT, PARENT_MANIFEST)
    rb_conditioned.attach(stage)
    with tempfile.TemporaryDirectory(dir=OUTPUT, prefix=".conditioned-build-") as work:
        output = Path(work) / NAME
        review = assemble(output, stage.study_identity)
        write_once(output / "PACKAGE-REVIEW.json", json_bytes(review))
        require(not destination.exists() and not destination.is_symlink(), "Study appeared")
        output.rename(destination)
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    build()
