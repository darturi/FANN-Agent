"""Guarded differential helper checks; no network, process or native execution."""

import argparse
import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--phase", choices=("source", "snapshot"), required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in here.glob("*.py")}
    denied = []

    def audit(event, values):
        if event in ("socket.connect", "socket.bind", "subprocess.Popen"):
            denied.append(event)
            raise RuntimeError("Offline helper tests forbid external execution")

    sys.addaudithook(audit)
    import test_fast_paths

    expected = {
        "test_fast_paths." + cls.name + "." + method.name
        for cls in ast.parse((here / "test_fast_paths.py").read_text()).body
        if isinstance(cls, ast.ClassDef)
        for method in cls.body
        if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
    }
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_fast_paths)

    def ids(value):
        return (
            [name for child in value for name in ids(child)]
            if isinstance(value, unittest.TestSuite)
            else [value.id()]
        )

    actual = ids(suite)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in here.glob("*.py")}
    good = (
        result.wasSuccessful()
        and not result.skipped
        and not denied
        and before == after
        and set(actual) == expected
        and len(actual) == len(expected) == 26
        and Path(test_fast_paths.__file__).resolve() == here / "test_fast_paths.py"
    )
    receipt = {
        "status": "pass" if good else "failed",
        "phase": args.phase,
        "tests_run": result.testsRun,
        "test_ids": actual,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "external_attempts": len(denied),
        "code_sha256": after,
        "Torch_jobs": 0,
        "ANN_searches": 0,
        "exact_searches": 0,
        "native_qualification": False,
    }
    with args.receipt.open("x") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write("\n")
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
