"""Independent source/snapshot authority tests with external actions denied."""

import argparse
import ast
import importlib
import sys
import unittest
from pathlib import Path

from nh_common import HERE, inventory, offline, save


def main():
    offline()
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", choices=("source", "snapshot"), required=True)
    args = p.parse_args()
    before = inventory(HERE)
    denied = []

    def audit(event, values):
        if event in ("socket.connect", "socket.bind", "subprocess.Popen", "os.kill", "os.killpg"):
            denied.append(event)
            raise RuntimeError("Offline model checks prohibit external actions")

    sys.addaudithook(audit)
    modules = [importlib.import_module(n) for n in ("au_test_authority", "au_test_models")]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)

    def ids(s):
        return (
            [name for child in s for name in ids(child)]
            if isinstance(s, unittest.TestSuite)
            else [s.id()]
        )

    actual = ids(suite)
    expected = {
        m.__name__ + "." + c.name + "." + f.name
        for m in modules
        for c in ast.parse(Path(m.__file__).read_text()).body
        if isinstance(c, ast.ClassDef)
        for f in c.body
        if isinstance(f, ast.FunctionDef) and f.name.startswith("test_")
    }
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    good = (
        result.wasSuccessful()
        and not result.skipped
        and not denied
        and len(actual) == len(expected)
        and set(actual) == expected
        and before == inventory(HERE)
        and all(Path(m.__file__).resolve() == HERE / (m.__name__ + ".py") for m in modules)
    )
    save(
        args.receipt,
        {
            "status": "pass" if good else "failed",
            "phase": args.phase,
            "tests_run": result.testsRun,
            "test_ids": actual,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "external_attempts": denied,
            "code_sha256": before,
            "native_release": False,
            "Torch_jobs": 0,
            "ANN_searches": 0,
            "exact_searches": 0,
        },
    )
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
