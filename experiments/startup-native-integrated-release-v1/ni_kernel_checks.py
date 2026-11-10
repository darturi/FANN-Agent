import argparse
import ast
import os
import platform
import sys
import time
import unittest
from pathlib import Path

from nh_common import HERE, inventory, save


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", required=True, type=Path)
    p.add_argument("--phase", choices=("source", "snapshot"), required=True)
    a = p.parse_args()
    if platform.system() != "Linux" or os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Offline Linux integration only")
    before = inventory(HERE)
    denied = []
    calls = []

    def audit(event, args):
        if event in ("socket.connect", "socket.bind", "os.kill", "os.killpg"):
            denied.append(event)
            raise RuntimeError("Offline kernel integration prohibits external actions")
        if event == "subprocess.Popen":
            argv = list(map(str, args[1]))
            calls.append(argv)
            if (
                len(argv) < 3
                or argv[1] != "-B"
                or Path(argv[2]).resolve() != HERE / "ni_guardian.py"
            ):
                denied.append(event)
                raise RuntimeError("Only exact integrated guardian may spawn")

    sys.addaudithook(audit)
    import test_kernel_integration as m

    suite = unittest.defaultTestLoader.loadTestsFromModule(m)
    actual = [t.id() for group in suite for t in group]
    expected = {
        "test_kernel_integration." + c.name + "." + f.name
        for c in ast.parse((HERE / "test_kernel_integration.py").read_text()).body
        if isinstance(c, ast.ClassDef)
        for f in c.body
        if isinstance(f, ast.FunctionDef) and f.name.startswith("test_")
    }

    class DetailedResult(unittest.TextTestResult):
        def addError(self, test, error):
            groups = getattr(test, "groups", None)
            if groups is not None:
                self.stream.write("GUARDIAN DIAGNOSTICS: " + repr(groups.failures) + "\n")
            for filename in ("host-fixture.log", "guest-fixture.log"):
                path = getattr(test, "raw", Path("/missing")) / filename
                if path.exists():
                    self.stream.write(filename + ": " + path.read_text()[-8000:] + "\n")
            super().addError(test, error)

    began = time.monotonic()
    r = unittest.TextTestRunner(verbosity=2, resultclass=DetailedResult).run(suite)
    good = (
        r.wasSuccessful()
        and not r.skipped
        and not denied
        and set(actual) == expected
        and len(actual) == len(expected)
        and before == inventory(HERE)
        and time.monotonic() - began < 180
    )
    save(
        a.receipt,
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
            "observations": m.OBSERVATIONS,
            "elapsed_seconds": time.monotonic() - began,
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "native_qualification": False,
            "Torch_jobs": 0,
            "ANN_searches": 0,
            "exact_searches": 0,
        },
    )
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
