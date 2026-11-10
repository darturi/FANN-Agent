"""Run every declared local test, retaining identities and bounded fixture raw."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    a = p.parse_args()
    a.output.mkdir(mode=0o700)
    os.umask(0o077)
    os.environ["A3_COMPAT_TEST_OUT"] = str(a.output.resolve())
    here = Path(__file__).resolve().parent
    def inventory():
        return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in here.iterdir() if f.is_file()}
    before = inventory()
    actions = []
    def audit(event, args):
        if event in ("socket.connect", "socket.bind"):
            actions.append(event)
            raise RuntimeError("Network prohibited in offline harness checks")
        if event == "subprocess.Popen":
            argv = args[1]
            if not isinstance(argv, (list, tuple)) or len(argv) < 3 or argv[0] != sys.executable or argv[1] != "-B" or not str(argv[2]).startswith(str(a.output.resolve()) + "/"):
                actions.append(str(argv))
                raise RuntimeError("Only owned local Python fixture children are allowed")
    sys.addaudithook(audit)
    import test_compatibility as m
    suite = unittest.defaultTestLoader.loadTestsFromModule(m)
    actual = [t.id() for group in suite for t in group]
    expected = {m.__name__ + "." + c.name + "." + f.name
                for c in ast.parse(Path(m.__file__).read_text()).body if isinstance(c, ast.ClassDef)
                for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test_")}
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    good = (result.wasSuccessful() and not result.skipped and not actions and
            len(actual) == len(expected) and set(actual) == expected and inventory() == before)
    receipt = {"status": "pass" if good else "failed", "tests_run": result.testsRun,
               "test_ids": actual, "failures": len(result.failures), "errors": len(result.errors),
               "skipped": len(result.skipped), "prohibited_actions": actions, "code_sha256": before,
               "source_unchanged": inventory() == before, "new_allocations": 0,
               "ANN_searches": 0, "exact_searches": 0, "native_Slurm_executed": False}
    (a.output / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return not good


if __name__ == "__main__":
    raise SystemExit(main())
