"""Source/sealed A3 integration correctness; no real SQL, network or subprocesses."""

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
PROTO = (
    HERE
    if (HERE / "exact_vector.py").exists()
    else ROOT / "agent/experiments/startup-exact-vector-v1"
)
REFERENCE = (
    ROOT
    / "trials/torch-reviews-startup-attribution-v1-image-reference"
    / "torch-startup-attribution-v1-image-reference"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids(node):
    if isinstance(node, unittest.TestSuite):
        return [name for child in node for name in ids(child)]
    return [node.id()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("source", "sealed"), required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--target-image-config")
    args = parser.parse_args()
    sys.path[:0] = [str(HERE), str(PROTO), str(REFERENCE), str(REFERENCE / "frozen/vendor")]
    files = {p.name: p for p in HERE.glob("*.py")}
    files.update({name: PROTO / name for name in ("exact_vector.py", "test_exact_vector.py")})
    before = {name: sha(path) for name, path in files.items()}
    expected_ids = set()
    for filename in ("test_exact_vector.py", "test_integration.py"):
        for node in ast.parse(files[filename].read_text()).body:
            if isinstance(node, ast.ClassDef):
                expected_ids.update(
                    filename[:-3] + "." + node.name + "." + method.name
                    for method in node.body
                    if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
                )
    started = time.monotonic()
    suite = unittest.TestSuite(
        unittest.defaultTestLoader.loadTestsFromName(name)
        for name in ("test_exact_vector", "test_integration")
    )
    cases = ids(suite)
    denied = []

    def blocked(*a, **k):
        denied.append("connection/process")
        raise RuntimeError("A3 correctness forbids real connections and processes")

    with ExitStack() as stack:
        for name in (
            "psycopg.connect",
            "psycopg.Connection.connect",
            "psycopg.AsyncConnection.connect",
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "subprocess.Popen",
        ):
            stack.enter_context(patch(name, blocked))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    from sa_driver import provenance

    actual = provenance()
    target = "IMAGE-REFERENCE.json" if args.target_image_config else "DRIVER-REFERENCE.json"
    reference = json.loads((REFERENCE / target).read_text())
    runtime_ok = actual == reference
    if args.target_image_config:
        runtime_ok = (
            runtime_ok
            and platform.python_version() == "3.12.15"
            and args.target_image_config
            == "ea7083a544d105d589ac1a3915b7ab8425fe1e867f2afc3ceaf99f0a9a48967f"
        )
    after = {name: sha(path) for name, path in files.items()}
    module_origins = {
        name: str(Path(sys.modules[name].__file__).resolve())
        for name in ("test_exact_vector", "test_integration", "integration", "exact_vector")
    }
    origins_ok = all(Path(path).parent in (HERE, PROTO) for path in module_origins.values())
    good = (
        result.wasSuccessful()
        and not result.skipped
        and not denied
        and before == after
        and set(cases) == expected_ids
        and len(cases) == len(expected_ids)
        and origins_ok
        and runtime_ok
    )
    receipt = {
        "status": "pass" if good else "fail",
        "phase": args.phase,
        "tests_run": result.testsRun,
        "expected_tests": len(expected_ids),
        "test_ids": cases,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "denied_actions": len(denied),
        "source_files_sha256": after,
        "source_stable": before == after,
        "loaded_modules": module_origins,
        "module_origins_verified": origins_ok,
        "actual_provenance": actual,
        "runtime_reference_pass": runtime_ok,
        "target_image_config_sha256": args.target_image_config,
        "python": platform.python_version(),
        "elapsed_seconds": time.monotonic() - started,
        "ANN_searches": 0,
        "exact_searches": 0,
        "SQL": 0,
        "database_connections": 0,
        "Torch_submissions": 0,
        "fixture_rows_max": 64,
        "dimensions": 768,
        "native_resource_release": False,
    }
    with args.receipt.open("x") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in ("status", "phase", "tests_run", "errors", "runtime_reference_pass")
            },
            indent=2,
        )
    )
    raise SystemExit(not good)


if __name__ == "__main__":
    main()
