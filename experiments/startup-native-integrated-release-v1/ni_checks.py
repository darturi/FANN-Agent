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
        if event in ("subprocess.Popen", "socket.connect", "socket.bind", "os.kill", "os.killpg"):
            denied.append(event)
            raise RuntimeError("Offline integration units prohibit external actions")

    sys.addaudithook(audit)
    import test_native_integration as m

    suite = unittest.defaultTestLoader.loadTestsFromModule(m)
    actual = [t.id() for group in suite for t in group]
    expected = {
        "test_native_integration." + c.name + "." + f.name
        for c in ast.parse((HERE / "test_native_integration.py").read_text()).body
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
        and Path(m.__file__).resolve() == HERE / "test_native_integration.py"
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
        },
    )
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
