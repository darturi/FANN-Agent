"""Build and locally verify the held Torch kit for the reader switch diagnostic."""

import json
import tempfile
from pathlib import Path

import rb_interleave
import rb_switch
from rb_interleave_prepare import HostSource, build_host, command
from rb_native import load_stage
from rb_package import HERE, OUTPUT, PACKAGE_NAME, copy_bytes
from rb_plan import SESSION_LENGTH, file_sha, pinned, require
from rb_seal import json_bytes, make_archive, seal_directory, verify_directory, write_once

NAME = "reader-switch-v1"
PRIOR = OUTPUT / "interleaved-aa-v1"
PARENT = PRIOR / PACKAGE_NAME
PARENT_MANIFEST = "72fcd7580e2ccc056a3f5a9874926fbe693ab102fc10cc0933b5ee32a1883e53"
HOST = HostSource(
    PRIOR,
    {
        "rb_host.py": "4486ded4e2f3284da50e1c21d4c649ac0bdc4087f5061f9af3c9e9ee00aaaa2c",
        "rb_site.py": "8c934d6c22d85d2de2c5caf214830c10f8c63357f1d31262b83fc1ad7c039099",
        "rb_seal.py": "3d0cae1765c2f8fc23e23bfdc1ec939a0c750ae57c455782e45ba38f2bf45557",
    },
    "af6dd71b2dd96d41560bc3d8375a81afbd4c795282fef82b8820108637e552f1",
    "interleaved-aa-v1",
    "9543a173031c0462062c382cd1cfcdf239905f8f4b5611472d83f7be321a927b"
    "  $results/$name-interleaved-aa-v1-reservation/reservation.json",
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
    copy_bytes(package / "rb_switch.py", (HERE / "rb_switch.py").read_bytes())
    manifest = seal_directory(package)
    review = command(package / "rb_native.py", "verify", package, manifest)
    require(
        review
        == {
            "status": "verified_held",
            "candidate": identity,
            "sessions": 60,
            "cases": 600,
            "reader_switch_diagnostic": True,
            "dispatch_released": False,
        },
        "Sealed switch diagnostic guest review differs",
    )
    archive = output / f"{PACKAGE_NAME}.tar.gz"
    archive_sha = make_archive(package, archive, manifest)
    upload, kit = build_host(
        output,
        archive,
        manifest,
        identity,
        study=NAME,
        job_name="fann-reviews-switch-v1",
        comment_prefix="rbswitch1-",
        source=HOST,
    )
    measured = (
        rb_switch.WORKLOADS * rb_switch.CHUNKS * len(rb_switch.CONDITIONS) * 2 * rb_interleave.CHUNK
    )
    return {
        **review,
        "previous_package_manifest_sha256": PARENT_MANIFEST,
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
            "search_attempts": rb_switch.Meter.search_limits["timing"],
            "measured_searches": measured,
            "warmup_searches": rb_switch.WORKLOADS * 2 * SESSION_LENGTH,
            "conditioning_searches": measured // 2,
            "reference_readers": 1,
            "timed_reader_lifetimes": rb_switch.Meter.reader_limits["timing"],
            "max_concurrent_timed_readers": 2,
            "max_concurrent_searches": 1,
            "seed_installs": rb_switch.Meter.install_limits["timing"],
            "exact_searches": 0,
            "provider_calls": 0,
            "confirmation_queries": 0,
        },
        "study": {
            "families": list(rb_interleave.FAMILIES),
            "workloads": [
                f"reader-workload-{block + 1:02}" for block in rb_interleave.PROBE_BLOCKS
            ],
            "patterns": list(rb_switch.PATTERNS),
            "conditioned_on": list(rb_interleave.LABELS),
            "requests_per_chunk": rb_interleave.CHUNK,
            "matched_chunks_per_workload_family": rb_switch.CHUNKS,
            "conditions_per_chunk": len(rb_switch.CONDITIONS),
            "conditioning": "Execute the preceding five queries on the assigned entering reader",
            "contrast": "Compare switch versus stay at each order position and repeat versus first "
            "at each switch state. Match within each workload, family, chunk, and query "
            "position and balance the measured reader labels.",
            "instrumentation": "Per-request PostgreSQL command duration, backend CPU and wait "
            "counters, and CPU before and after the request. Count user-space "
            "cycles, instructions and cache misses if the kernel permits.",
            "purpose": "Development diagnosis. Results guide the schedule for formal calibration.",
        },
        "next_gate": "Zero-allocation Torch preflight. Fresh approval required for dispatch.",
        "offline_accounting": {"allocations": 0, "searches": 0, "confirmation_queries": 0},
    }


def build():
    destination = OUTPUT / NAME
    require(not destination.exists() and not destination.is_symlink(), "Study already exists")
    stage = load_stage(PARENT, PARENT_MANIFEST)
    rb_switch.attach(stage)
    with tempfile.TemporaryDirectory(dir=OUTPUT, prefix=".switch-build-") as work:
        output = Path(work) / NAME
        review = assemble(output, stage.study_identity)
        write_once(output / "PACKAGE-REVIEW.json", json_bytes(review))
        require(not destination.exists() and not destination.is_symlink(), "Study appeared")
        output.rename(destination)
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    build()
