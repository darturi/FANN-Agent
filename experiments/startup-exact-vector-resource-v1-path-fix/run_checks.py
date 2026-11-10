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

from pc_common import save, sha


def ids(suite):
    if isinstance(suite, unittest.TestSuite):
        return [value for child in suite for value in ids(child)]
    return [suite.id()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("source", "sealed"))
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    modules = ("test_memory", "test_resource", "test_host_resource")
    before = {p.name: sha(p) for p in here.glob("*.py")}
    expected = set()
    for name in modules:
        for node in ast.parse((here / (name + ".py")).read_text()).body:
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
        suite = unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromName(name) for name in modules
        )
        cases = ids(suite)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = {p.name: sha(p) for p in here.glob("*.py")}
    loaded = {name: str(Path(sys.modules[name].__file__).resolve()) for name in modules}
    origins = all(Path(value).parent == here for value in loaded.values())
    good = (
        result.wasSuccessful()
        and not result.skipped
        and not denied
        and before == after
        and origins
        and set(cases) == expected
        and len(cases) == len(expected)
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
        scope="mocked resource entry/host/controller and metadata-only replay correctness",
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
