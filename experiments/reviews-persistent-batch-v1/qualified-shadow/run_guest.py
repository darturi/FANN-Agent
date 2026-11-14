"""Restore the original graph and collect a development-only shadow return."""

import argparse
import json
import os
from pathlib import Path

from capture import capture, reference_rows
from rb_native import IMAGE, load_stage, memory_events, resource_limits, watchdog
from rb_plan import file_sha, load_plan, require

HERE = Path(__file__).resolve().parent
MODULE = Path("/opt/postgresql/lib/vector.so")


def run(args):
    require(
        os.uname().sysname == "Linux"
        and os.uname().machine == "x86_64"
        and os.environ.get("SLURM_JOB_ID", "").isdigit()
        and os.environ.get("TORCH_IMAGE_SHA256") == IMAGE,
        "Shadow capture requires the original runtime on an x86_64 compute allocation",
    )
    stage = load_stage(args.package, args.package_sha)
    require(file_sha(args.bundle / "images/runtime.sif") == IMAGE, "Original runtime image differs")
    require(file_sha(MODULE) == args.module_sha, "Shadow module mount differs")
    require(args.work.is_dir() and not any(args.work.iterdir()), "Use a new private work directory")
    require(
        args.output.is_dir() and not any(args.output.iterdir()), "Use an empty output directory"
    )
    limits, memory_group = resource_limits()
    before = memory_events(memory_group)
    runner, backend_type = stage.frozen.execution.load_backend(stage.source)
    require(
        args.work.stat().st_uid == os.getuid() and not args.work.stat().st_mode & 0o077,
        "Work directory must be owned by this job user and private",
    )
    (args.work / "socket").mkdir(mode=0o700)
    with (args.work / ".torch-owned").open("x") as marker:
        marker.write(f"{os.environ['SLURM_JOB_ID']}\n")
    backend = None
    with watchdog(6000):
        try:
            restored = stage.frozen.restore(
                stage.source,
                args.bundle,
                args.prepared,
                args.work,
                runner,
                extra_sql=(HERE / "functions.sql").read_text(),
            )
            require(restored == stage.index, "Restored physical index identity differs")
            backend = backend_type(args.bundle, args.work)
            backend.state["source_manifest"]["settings"]["hnsw.ef_search"] = "640"
            receipt = capture(
                stage.plan,
                stage.frozen,
                stage.evidence,
                backend,
                args.output / "shadow.jsonl",
                args.reference,
                args.reference_sha,
                args.module_sha,
            )
            backend.close()
            backend = None
            stage.frozen.verify_import(runner, args.bundle, args.work)
        finally:
            if backend is not None:
                backend.close()
            stage.frozen.stop(args.work)
        stage.frozen.verify_index(args.work, stage.index)
    require(memory_events(memory_group) == before, "Memory limit event during capture")
    receipt.update(
        package_sha256=args.package_sha,
        original_image_sha256=IMAGE,
        resources=limits,
        physical_index_verified_before_and_after=True,
        data_verified_before_and_after=True,
    )
    with (args.output / "receipt.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    references = commands.add_parser("references", help="Stage the 200 saved trace and output pins")
    references.add_argument("output", type=Path)
    guest = commands.add_parser("capture", help="Run only on the guarded research guest")
    for name in ("package", "bundle", "prepared", "work", "output", "reference"):
        guest.add_argument(f"--{name}", required=True, type=Path)
    for name in ("package-sha", "reference-sha", "module-sha"):
        guest.add_argument(f"--{name}", required=True)
    args = parser.parse_args()
    if args.command == "references":
        rows = reference_rows(load_plan())
        require(len(rows) == 200, "Unexpected staged reference count")
        with args.output.open("x") as stream:
            json.dump(rows, stream, indent=2, sort_keys=True, allow_nan=False)
        print(file_sha(args.output))
    else:
        run(args)


if __name__ == "__main__":
    main()
