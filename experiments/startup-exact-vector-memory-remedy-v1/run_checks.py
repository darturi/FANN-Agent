"""Old56 cases plus new memory-component checks, with real external calls denied."""

import argparse
import ast
import hashlib
import json
import platform
import sys
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
REFERENCE = (
    ROOT
    / "trials/torch-reviews-startup-attribution-v1-image-reference"
    / "torch-startup-attribution-v1-image-reference"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    return {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob("*.py"))}


def ids(suite):
    if isinstance(suite, unittest.TestSuite):
        return [name for child in suite for name in ids(child)]
    return [suite.id()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("source", "snapshot"), required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    sys.path[:0] = [
        str(HERE),
        str(HERE / "baseline"),
        str(REFERENCE),
        str(REFERENCE / "frozen/vendor"),
    ]
    modules = dict(
        test_exact_vector=HERE / "baseline/test_exact_vector.py",
        test_integration=HERE / "baseline/test_integration.py",
        test_memory_remedy=HERE / "test_memory_remedy.py",
    )
    expected = set()
    for module, path in modules.items():
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.ClassDef):
                expected.update(
                    module + "." + node.name + "." + method.name
                    for method in node.body
                    if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
                )
    before = inventory()
    denied = []

    def block(*a, **kw):
        denied.append("real connection/process")
        raise AssertionError("Offline memory checks forbid SQL/network/processes")

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
            stack.enter_context(patch(name, block))
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in modules)
        cases = ids(suite)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    from sa_driver import provenance

    actual = provenance()
    reference = json.loads((REFERENCE / "DRIVER-REFERENCE.json").read_text())
    origins = {name: str(Path(sys.modules[name].__file__).resolve()) for name in modules}
    after = inventory()
    good = (
        result.wasSuccessful()
        and not result.skipped
        and not denied
        and before == after
        and len(cases) == len(expected)
        and set(cases) == expected
        and all(Path(origins[n]) == p for n, p in modules.items())
        and actual == reference
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
        loaded_test_modules=origins,
        module_origins_verified=all(Path(origins[n]) == p for n, p in modules.items()),
        actual_provenance=actual,
        exact_local_reference_pass=actual == reference,
        python=platform.python_version(),
        elapsed_seconds=time.monotonic() - started,
        original_A3_cases=56,
        maximum_fixture_rows=64,
        dimensions=768,
        real_SQL=0,
        database_connections=0,
        subprocesses=0,
        SSH=0,
        Torch_jobs=0,
        ANN_searches=0,
        exact_searches=0,
        native_producer_integration=False,
        native_correctness_qualified=False,
        native_memory_qualified=False,
        full_B2f_released=False,
        scope=(
            "bounded component/consumer correctness and structural allocation; "
            "not native peak or latency"
        ),
    )
    with args.receipt.open("x") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write("\n")
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "phase",
                    "tests_run",
                    "failures",
                    "errors",
                    "denied_actions",
                    "exact_local_reference_pass",
                )
            },
            indent=2,
        )
    )
    raise SystemExit(not good)


if __name__ == "__main__":
    main()
