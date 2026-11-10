"""Guarded qualification-controller checks, source and sealed code origins."""

import argparse
import ast
import contextlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from common import HERE, code_map, save


def flatten(suite):
    if isinstance(suite, unittest.TestSuite):
        return [n for s in suite for n in flatten(s)]
    return [suite.id()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", choices=("source", "sealed"), required=True)
    a = p.parse_args()
    before = code_map(HERE)
    attempts = []

    def block(*args, **kwargs):
        attempts.append("external")
        raise RuntimeError("Local qualification verification forbids external calls")

    with contextlib.ExitStack() as stack:
        for n in (
            "subprocess.Popen",
            "subprocess.run",
            "subprocess.check_output",
            "socket.socket.connect",
            "socket.socket.connect_ex",
        ):
            stack.enter_context(patch(n, block))
        suite = unittest.defaultTestLoader.loadTestsFromName("test_qualification")
        cases = flatten(suite)
        r = unittest.TextTestRunner(verbosity=2).run(suite)
    expected = {
        "test_qualification." + n.name + "." + m.name
        for n in ast.parse((HERE / "test_qualification.py").read_text()).body
        if isinstance(n, ast.ClassDef)
        for m in n.body
        if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")
    }
    good = (
        r.wasSuccessful()
        and not r.skipped
        and not attempts
        and before == code_map(HERE)
        and set(cases) == expected
        and len(cases) == len(expected)
        and Path(sys.modules["test_qualification"].__file__).resolve()
        == HERE / "test_qualification.py"
    )
    save(
        a.receipt,
        dict(
            status="pass" if good else "fail",
            phase=a.phase,
            tests_run=r.testsRun,
            test_ids=cases,
            failures=len(r.failures),
            errors=len(r.errors),
            skipped=len(r.skipped),
            external_attempts=len(attempts),
            code_sha256=code_map(HERE),
            Torch_jobs=0,
            ANN_searches=0,
            exact_searches=0,
            native_resource_release=False,
        ),
    )
    raise SystemExit(not good)


if __name__ == "__main__":
    main()
