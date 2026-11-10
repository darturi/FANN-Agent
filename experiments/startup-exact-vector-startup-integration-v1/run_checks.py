"""Guarded source/sealed resource checks; no native DB, process or scheduler calls."""

import argparse
import ast
import json
import platform
import sys
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from pc_common import save


def ids(suite):
    if isinstance(suite, unittest.TestSuite):
        return [value for child in suite for value in ids(child)]
    return [suite.id()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("source", "snapshot"))
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    # Bootstrap only pinned local consumers, before collecting all preserved suites.
    import test_fixtures  # noqa: F401

    modules = (
        "test_exact_vector",
        "test_integration",
        "test_memory_remedy",
        "test_memory",
        "test_resource",
        "test_host_resource",
        "test_lifecycle",
        "test_startup_adaptive",
    )
    locations = {
        name: here
        / ("a3" if name in ("test_exact_vector", "test_integration") else "")
        / (name + ".py")
        for name in modules
    }
    from adaptive_contract import code_map

    before = code_map(here)
    expected = set()
    for name in modules:
        for node in ast.parse(locations[name].read_text()).body:
            if isinstance(node, ast.ClassDef):
                expected.update(
                    name + "." + node.name + "." + method.name
                    for method in node.body
                    if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
                )
    denied = []

    def blocked(*a, **kw):
        denied.append("real connection/process")
        raise RuntimeError("Resource local checks prohibit real connections/processes")

    started = time.monotonic()
    with ExitStack() as stack:
        for name in (
            "psycopg.connect",
            "psycopg.Connection.connect",
            "psycopg.AsyncConnection.connect",
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "subprocess.Popen",
            "subprocess.run",
        ):
            stack.enter_context(patch(name, blocked))
        suites = []
        for name in modules:
            # The unchanged original consumer test imports prepend their frozen
            # reference paths. Restore harness precedence before the next module.
            paths = sys.path[:]
            try:
                suites.append(unittest.defaultTestLoader.loadTestsFromName(name))
            finally:
                sys.path[:] = paths
        suite = unittest.TestSuite(suites)
        cases = ids(suite)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = code_map(here)
    from pc_common import read
    from sa_driver import provenance

    actual = provenance()
    exact_local_reference_pass = actual == read(here / "DRIVER-REFERENCE.json")
    loaded = {name: str(Path(sys.modules[name].__file__).resolve()) for name in modules}
    origins = all(Path(value) == locations[name] for name, value in loaded.items())
    good = (
        result.wasSuccessful()
        and not result.skipped
        and not denied
        and before == after
        and origins
        and set(cases) == expected
        and len(cases) == len(expected)
        and exact_local_reference_pass
    )
    receipt = dict(
        status="pass" if good else "fail",
        phase=args.phase,
        tests_run=result.testsRun,
        expected_tests=len(expected),
        test_ids=cases,
        failures=len(result.failures),
        errors=len(result.errors),
        skipped=len(result.skipped),
        denied_actions=len(denied),
        source_files_sha256=after,
        source_stable=before == after,
        loaded_test_modules=loaded,
        module_origins_verified=origins,
        exact_local_reference_pass=exact_local_reference_pass,
        actual_local_provenance=actual,
        native_target_executed=False,
        python=platform.python_version(),
        elapsed_seconds=time.monotonic() - started,
        ANN_searches=0,
        exact_searches=0,
        real_SQL=0,
        database_connections=0,
        Torch_jobs=0,
        provider_calls=0,
        maximum_fixture_rows=64,
        native_resource_qualified=False,
        full_B2f_released=False,
        scope=(
            "bounded adaptive producer/runtime; all preserved tests; "
            "metadata-only replay, no target execution"
        ),
    )
    save(args.receipt, receipt)
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "phase",
                    "tests_run",
                    "expected_tests",
                    "errors",
                    "failures",
                    "denied_actions",
                )
            },
            indent=2,
        )
    )
    raise SystemExit(not good)


if __name__ == "__main__":
    main()
