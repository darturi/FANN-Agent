"""Guarded source/snapshot storage and budget policy checks."""

import argparse
import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", choices=("source", "snapshot"), required=True)
    a = p.parse_args()
    here = Path(__file__).resolve().parent
    before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in here.glob("*.py")}
    denied = []

    def audit(event, values):
        if event in ("socket.connect", "socket.bind", "subprocess.Popen"):
            denied.append(event)
            raise RuntimeError("Offline unit checks forbid external execution")

    sys.addaudithook(audit)
    import test_storage

    expected = {
        "test_storage." + c.name + "." + m.name
        for c in ast.parse((here / "test_storage.py").read_text()).body
        if isinstance(c, ast.ClassDef)
        for m in c.body
        if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")
    }
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_storage)

    def ids(value):
        if isinstance(value, unittest.TestSuite):
            return [name for child in value for name in ids(child)]
        return [value.id()]

    actual = ids(suite)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in here.glob("*.py")}
    good = (
        result.wasSuccessful()
        and not result.skipped
        and not denied
        and before == after
        and len(actual) == len(expected)
        and set(actual) == expected
        and Path(test_storage.__file__).resolve() == here / "test_storage.py"
    )
    value = {
        "status": "pass" if good else "failed",
        "phase": a.phase,
        "tests_run": result.testsRun,
        "test_ids": actual,
        "errors": len(result.errors),
        "failures": len(result.failures),
        "skipped": len(result.skipped),
        "external_attempts": len(denied),
        "code_sha256": after,
        "Torch_jobs": 0,
        "ANN_searches": 0,
        "exact_searches": 0,
        "native_release": False,
    }
    with a.receipt.open("x") as out:
        json.dump(value, out, indent=2, sort_keys=True)
        out.write("\n")
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
