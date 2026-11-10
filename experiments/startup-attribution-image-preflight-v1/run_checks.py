"""Source/sealed offline inspection tests; no image, database or scheduler execution."""

import argparse
import ast
import json
import sys
import time
import unittest
from pathlib import Path

from inspect_image import file_sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", choices=["source", "sealed"], required=True)
    args = p.parse_args()
    here = Path(__file__).resolve().parent
    before = {p.name: file_sha(p) for p in here.glob("*.py")}
    for path in here.glob("*.py"):
        ast.parse(path.read_text())
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(here), pattern="test_probe.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = {p.name: file_sha(p) for p in here.glob("*.py")}
    modules = {
        n: str(Path(m.__file__).resolve()) for n, m in sys.modules.items() if n == "test_probe"
    }
    stable = before == after and all(Path(p).parent == here for p in modules.values())
    record = dict(
        status="pass" if result.wasSuccessful() and stable else "fail",
        tests_run=result.testsRun,
        failures=len(result.failures),
        errors=len(result.errors),
        phase=args.phase,
        source_stable=stable,
        source_files_sha256=after,
        loaded_test_modules=modules,
        elapsed_seconds=time.monotonic() - started,
        ANN_searches=0,
        exact_searches=0,
        database_queries=0,
        native_image_executions=0,
        jobs=0,
        SSH=0,
        scope="source definitions and two literal monitoring functions; local libraries only",
    )
    with args.receipt.open("x") as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write("\n")
    raise SystemExit(record["status"] != "pass")


if __name__ == "__main__":
    main()
