"""Exercise actual entrypoint imports and the unmodified frozen loader without any query."""

import argparse
import hashlib
import json
import runpy
import sys
from pathlib import Path


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--phase", choices=("timing", "work"), required=True)
    parser.add_argument("--expect-rejection", action="store_true")
    parser.add_argument("--kit", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--loader-only", action="store_true")
    args = parser.parse_args()
    kit = args.kit.resolve()
    # run_name deliberately skips main(), while reproducing its actual import tree.
    entry = runpy.run_path(str(kit / "run_diagnostic.py"), run_name="attribution_startup_probe")
    sys.path.insert(0, str(args.package))
    from rb_native import load_stage

    prior_design = sys.modules.get("design")
    try:
        stage = load_stage(args.package, entry["PACKAGE_SHA"])
    except ValueError as error:
        if not args.expect_rejection or str(error) != "Use a clean process":
            raise
        assert prior_design is not None
        print(
            json.dumps(
                {
                    "status": "original_failure_reproduced",
                    "phase": args.phase,
                    "error": str(error),
                    "conflicting_module": prior_design.__file__,
                    "search_attempts": 0,
                    "provider_calls": 0,
                },
                sort_keys=True,
            )
        )
        return
    assert not args.expect_rejection, "original import collision was not reproduced"
    assert prior_design is None, "diagnostic imported a reserved frozen root"
    assert Path(sys.modules["design"].__file__).resolve() == stage.source / "design.py"
    import reader_attribution_design as schedule
    from experiment import run_timing, run_work
    from startup import install

    assert run_timing is entry["run_timing"] and run_work is entry["run_work"]
    assert Path(schedule.__file__).resolve() == kit / "reader_attribution_design.py"
    backend_name = None
    if not args.loader_only:
        runner, backend = stage.frozen.execution.load_backend(stage.source)
        backend_name = backend.__name__
        assert (
            sha(Path(runner.__file__))
            == "266bf3d65acc33f18cb0a9d3455a5a562d4ec2e65b608afe94e680b309ca1550"
        )
    startup = install(stage.frozen.restore)
    binding = json.loads((kit / "binding.json").read_text())
    assert sha(kit / (args.phase + "-module.so")) == binding[args.phase + "_module_sha256"]
    assert sha(Path("/opt/postgresql/lib/vector.so")) == binding[args.phase + "_module_sha256"]
    assert stage.index == binding["graph"]
    assert schedule.TOTAL_ATTEMPTS == 684950
    print(
        json.dumps(
            {
                "status": "repaired_entrypoint_and_frozen_loader_passed",
                "phase": args.phase,
                "frozen_design_module": sys.modules["design"].__file__,
                "diagnostic_design_module": schedule.__file__,
                "package_manifest_sha256": sha(args.package / "manifest.json"),
                "phase_module_sha256": binding[args.phase + "_module_sha256"],
                "backend": backend_name,
                "backend_import_exercised": not args.loader_only,
                "graph_identity": stage.index,
                "private_startup": startup,
                "search_attempts": 0,
                "provider_calls": 0,
                "validation_test_outcomes_opened": False,
                "limit": "Startup/import readiness only; no original-graph experiment executed.",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
