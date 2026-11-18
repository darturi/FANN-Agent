"""Import the real frozen backend and patched module without allocating or querying."""

import argparse
import json
import runpy
import sys
from pathlib import Path

from common import sha
from oracle_design import PACKAGE_SHA, require


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    runpy.run_path(str(here / "oracle_run.py"), run_name="oracle_startup_probe")
    sys.path.insert(0, str(args.package))
    from rb_native import load_stage

    stage = load_stage(args.package, PACKAGE_SHA)
    _, Backend = stage.frozen.execution.load_backend(stage.source)
    from startup import install

    install(stage.frozen.restore)
    binding = json.loads((here / "binding.json").read_text())
    require(stage.index == binding["graph"], "graph changed")
    require(
        sha("/opt/postgresql/lib/vector.so") == sha(here / "oracle-module.so"), "module changed"
    )
    for name, expected in binding["files"].items():
        require(sha(here / name) == expected, "changed input: " + name)
    print(
        json.dumps(
            {
                "status": "oracle_native_startup_preflight_passed",
                "backend": Backend.__name__,
                "module_sha256": sha(here / "oracle-module.so"),
                "searches": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
