"""Local capsule/controller/guard checks; never starts a native image or job."""

import argparse
import ast
import sys
import time
import unittest
from pathlib import Path

from common import save, sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", choices=["source", "sealed"], required=True)
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    before = {f.name: sha(f) for f in here.glob("*.py")}
    for f in here.glob("*.py"):
        ast.parse(f.read_text())
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(here), pattern="test_compat.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = {f.name: sha(f) for f in here.glob("*.py")}
    modules = {
        n: str(Path(m.__file__).resolve()) for n, m in sys.modules.items() if n == "test_compat"
    }
    stable = before == after and all(Path(p).parent == here for p in modules.values())
    save(
        a.receipt,
        dict(
            status="pass" if result.wasSuccessful() and stable else "fail",
            tests_run=result.testsRun,
            failures=len(result.failures),
            errors=len(result.errors),
            phase=a.phase,
            source_files_sha256=after,
            source_stable=stable,
            loaded_test_modules=modules,
            elapsed_seconds=time.monotonic() - started,
            new_native_image_executions=0,
            new_Torch_jobs=0,
            new_ANN_searches=0,
            new_exact_searches=0,
            new_SQL=0,
            new_database_connections=0,
        ),
    )
    raise SystemExit(not result.wasSuccessful() or not stable)


if __name__ == "__main__":
    main()
