"""Source/snapshot meaningful integration checks, with process/network denial."""

import argparse
import ast
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
        if event in ("socket.connect", "socket.bind", "subprocess.Popen"):
            denied.append(event)
            raise RuntimeError("Offline integration units prohibit external calls")

    sys.addaudithook(audit)
    import test_integration

    suite = unittest.defaultTestLoader.loadTestsFromModule(test_integration)

    def ids(s):
        return (
            [n for child in s for n in ids(child)]
            if isinstance(s, unittest.TestSuite)
            else [s.id()]
        )

    actual = ids(suite)
    expected = {
        "test_integration." + c.name + "." + m.name
        for c in ast.parse((HERE / "test_integration.py").read_text()).body
        if isinstance(c, ast.ClassDef)
        for m in c.body
        if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")
    }
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    good = (
        result.wasSuccessful()
        and not result.skipped
        and not denied
        and len(actual) == len(expected)
        and set(actual) == expected
        and Path(test_integration.__file__).resolve() == HERE / "test_integration.py"
        and before == inventory(HERE)
    )
    save(
        a.receipt,
        {
            "status": "pass" if good else "failed",
            "phase": a.phase,
            "tests_run": result.testsRun,
            "test_ids": actual,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "external_attempts": len(denied),
            "code_sha256": inventory(HERE),
            "Torch_jobs": 0,
            "ANN_searches": 0,
            "exact_searches": 0,
            "native_release": False,
        },
    )
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
