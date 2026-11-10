"""Offline check runner. Never dispatches a job or opens a native database."""

import argparse
import ast
import time
import unittest
from pathlib import Path

from pc_common import save, sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", choices=("source", "sealed"), required=True)
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    for path in here.glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(here), pattern="test_experiment.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = dict(
        status="pass" if result.wasSuccessful() else "fail",
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
        source_files_sha256={p.name: sha(p) for p in sorted(here.glob("*.py"))},
    )
    save(a.receipt, receipt)
    raise SystemExit(not result.wasSuccessful())


if __name__ == "__main__":
    main()
