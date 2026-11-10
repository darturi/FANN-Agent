"""Offline check runner. Never dispatches a job or opens a native database."""

import argparse
import ast
import sys
import time
import unittest
from pathlib import Path

from pc_common import read, save, sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", choices=("source", "sealed"), required=True)
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    for path in here.glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    before = {p.name: sha(p) for p in here.glob("*.py")}
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(here), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = {p.name: sha(p) for p in here.glob("*.py")}
    modules = {
        n: str(Path(m.__file__).resolve())
        for n, m in sys.modules.items()
        if n.startswith("test_") and getattr(m, "__file__", None)
    }
    stable = before == after and all(Path(p).parent == here for p in modules.values())
    baseline_path = Path(
        "/Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-startup-attribution-v1/baseline-regression.json"
    )
    baseline = read(baseline_path)
    baseline_ok = baseline["status"] == "pass" and baseline["tests_run"] == 155
    receipt = dict(
        baseline_regression_pass=baseline_ok,
        baseline_regression_receipt_sha256=sha(baseline_path),
        status="pass" if result.wasSuccessful() and stable and baseline_ok else "fail",
        source_stable_during_checks=stable,
        loaded_test_modules=modules,
        phase=a.phase,
        tests_run=result.testsRun,
        failures=len(result.failures),
        errors=len(result.errors),
        elapsed_seconds=time.monotonic() - started,
        scope="synthetic/offline correctness only",
        native_database_queries=0,
        torch_submissions=0,
        ssh_calls=0,
        provider_calls=0,
        new_fits=0,
        protected_query_values=0,
        source_files_sha256=after,
    )
    save(a.receipt, receipt)
    raise SystemExit(not result.wasSuccessful() or not stable or not baseline_ok)


if __name__ == "__main__":
    main()
