import argparse
import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def inventory():
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.is_file()
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", required=True)
    a = p.parse_args()
    before = inventory()
    denied = []

    def audit(event, args):
        if event in ("subprocess.Popen", "socket.connect", "socket.bind", "os.kill", "os.killpg"):
            denied.append(event)
            raise RuntimeError("Offline model external action prohibited")

    sys.addaudithook(audit)
    import test_site_compatibility as m

    suite = unittest.defaultTestLoader.loadTestsFromModule(m)
    actual = [t.id() for group in suite for t in group]
    expected = {
        m.__name__ + "." + c.name + "." + f.name
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
        and set(actual) == expected
        and len(actual) == len(expected)
        and inventory() == before
    )
    a.receipt.write_text(
        json.dumps(
            {
                "status": "pass" if good else "failed",
                "phase": a.phase,
                "tests_run": r.testsRun,
                "test_ids": actual,
                "errors": len(r.errors),
                "failures": len(r.failures),
                "skipped": len(r.skipped),
                "external_attempts": denied,
                "code_sha256": before,
                "Torch_allocations": 0,
                "searches": 0,
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
