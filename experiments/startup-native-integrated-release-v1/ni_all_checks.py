"""Every inherited and added model case, exact IDs/origins, no external action."""

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
    a = p.parse_args()
    before = inventory(HERE)
    denied = []

    def audit(event, args):
        if event in ("subprocess.Popen", "socket.connect", "socket.bind", "os.kill", "os.killpg"):
            denied.append(event)
            raise RuntimeError("Offline models prohibit external calls")

    sys.addaudithook(audit)
    modules = [
        importlib.import_module(name)
        for name in (
            "test_integration",
            "test_release",
            "au_test_authority",
            "au_test_models",
            "test_native_integration",
        )
    ]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)

    def ids(s):
        return (
            [n for child in s for n in ids(child)]
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
    r = unittest.TextTestRunner(verbosity=2).run(suite)
    good = (
        r.wasSuccessful()
        and not r.skipped
        and not denied
        and len(actual) == len(expected)
        and set(actual) == expected
        and before == inventory(HERE)
        and all(Path(m.__file__).resolve() == HERE / (m.__name__ + ".py") for m in modules)
    )
    save(
        a.receipt,
        {
            "status": "pass" if good else "failed",
            "tests_run": r.testsRun,
            "test_ids": actual,
            "failures": len(r.failures),
            "errors": len(r.errors),
            "skipped": len(r.skipped),
            "external_attempts": denied,
            "code_sha256": before,
            "phase": a.phase,
            "Torch_jobs": 0,
            "ANN_searches": 0,
            "exact_searches": 0,
            "native_release": False,
        },
    )
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
