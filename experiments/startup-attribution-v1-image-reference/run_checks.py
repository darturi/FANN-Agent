"""Offline correctness on exact local or image reference; no database/search/job."""

import argparse
import ast
import platform
import sys
import time
import unittest
from pathlib import Path

from pc_common import read, save, sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", choices=("source", "sealed"), required=True)
    p.add_argument("--target-image-config")
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    before = {f.name: sha(f) for f in here.glob("*.py")}
    recipe = {n: sha(here / n) for n in read(here / "RECIPE-FILES.json")["files"]}
    for f in here.glob("*.py"):
        ast.parse(f.read_text(), filename=str(f))
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(here), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = {f.name: sha(f) for f in here.glob("*.py")}
    modules = {
        n: str(Path(m.__file__).resolve())
        for n, m in sys.modules.items()
        if n.startswith("test_") and getattr(m, "__file__", None)
    }
    stable = before == after and recipe == {n: sha(here / n) for n in recipe}
    stable = stable and all(Path(path).parent == here for path in modules.values())
    from sa_driver import provenance
    from sa_monitor import idle
    from sa_test_support import reference

    actual = provenance()
    expected = reference()
    idle()
    runtime_ok = actual == expected
    if a.target_image_config:
        runtime_ok = runtime_ok and platform.python_version() == "3.12.15"
        runtime_ok = (
            runtime_ok
            and a.target_image_config
            == "ea7083a544d105d589ac1a3915b7ab8425fe1e867f2afc3ceaf99f0a9a48967f"
        )
        runtime_ok = runtime_ok and actual == read(here / "IMAGE-REFERENCE.json")
    baseline_path = Path(
        "/Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-startup-attribution-v1/baseline-regression.json"
    )
    baseline = read(baseline_path)
    baseline_ok = baseline["status"] == "pass" and baseline["tests_run"] == 155
    good = result.wasSuccessful() and stable and baseline_ok and runtime_ok
    save(
        a.receipt,
        dict(
            status="pass" if good else "fail",
            tests_run=result.testsRun,
            failures=len(result.failures),
            errors=len(result.errors),
            phase=a.phase,
            elapsed_seconds=time.monotonic() - started,
            python=platform.python_version(),
            actual_provenance=actual,
            target_image_config_sha256=a.target_image_config,
            source_stable_during_checks=stable,
            loaded_test_modules=modules,
            source_files_sha256=after,
            recipe_files_sha256=recipe,
            baseline_regression_pass=baseline_ok,
            baseline_regression_receipt_sha256=sha(baseline_path),
            baseline_scope="155 historical unchanged M3 local checks; not rerun here",
            scope=(
                "actual original code/private driver, <=64 rows or metadata-only counts; "
                "synthetic transport/files/resources"
            ),
            native_database_queries=0,
            ANN_searches=0,
            exact_searches=0,
            torch_submissions=0,
            provider_calls=0,
            new_fits=0,
            ssh_calls=0,
            protected_query_values=0,
        ),
    )
    raise SystemExit(not good)


if __name__ == "__main__":
    main()
