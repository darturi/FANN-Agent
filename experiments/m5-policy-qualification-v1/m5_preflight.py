"""Actual entry imports and native backend/runner/module readiness, without a query."""

import argparse
import json
import runpy
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--phase", choices=("timing", "work"), required=True)
    p.add_argument("--loader-only", action="store_true")
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    entry = runpy.run_path(str(here / "m5_run.py"), run_name="M5_startup_probe")
    sys.path.insert(0, str(a.package))
    from common import require, sha
    from m5_experiment import load_programs
    from rb_native import load_stage

    require(
        "design" not in sys.modules and "fannagent" not in sys.modules,
        "M5 imported a reserved frozen root too early",
    )
    stage = load_stage(a.package, entry["PACKAGE_SHA"])
    require(
        Path(sys.modules["design"].__file__).resolve() == stage.source / "design.py",
        "frozen design shadowed",
    )
    backend_name = None
    if not a.loader_only:
        runner, Backend = stage.frozen.execution.load_backend(stage.source)
        backend_name = Backend.__name__
        require(
            sha(runner.__file__)
            == "266bf3d65acc33f18cb0a9d3455a5a562d4ec2e65b608afe94e680b309ca1550",
            "runner changed",
        )
    from startup import install

    startup = install(stage.frozen.restore)
    binding = json.loads((here / "binding.json").read_text())
    require(
        sha(here / (a.phase + "-module.so"))
        == sha("/opt/postgresql/lib/vector.so")
        == binding[a.phase + "_module_sha256"],
        "wrong preflight module",
    )
    require(stage.index == binding["graph"] and len(load_programs(here)) == 5, "graph/pool changed")
    print(
        json.dumps(
            {
                "status": "M5_native_startup_preflight_passed"
                if not a.loader_only
                else "M5_local_loader_only_passed",
                "phase": a.phase,
                "backend_import_exercised": not a.loader_only,
                "backend": backend_name,
                "runtime_profile": binding["runtime_profile"],
                "programs_sha256": binding["programs_sha256"],
                "module_sha256": binding[a.phase + "_module_sha256"],
                "private_startup": startup,
                "search_attempts": 0,
                "provider_calls": 0,
                "validation_test_outcomes_opened": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
