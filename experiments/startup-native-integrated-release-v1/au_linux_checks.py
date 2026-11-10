"""Bounded real-kernel suite in a network-disabled local Linux container."""

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
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--phase", choices=("source", "snapshot"), required=True)
    a = p.parse_args()
    if (
        platform.system() != "Linux"
        or os.environ.get("SLURM_JOB_ID")
        or os.environ.get("SLURM_ARRAY_JOB_ID")
    ):
        raise RuntimeError("Isolated local Linux only")
    before = inventory(HERE)
    denied = []
    popen = []

    def audit(event, args):
        if event in ("socket.connect", "socket.bind", "os.kill", "os.killpg"):
            denied.append(event)
            raise RuntimeError("Network/numeric signalling prohibited")
        if event == "subprocess.Popen":
            argv = list(map(str, args[1]))
            popen.append(argv)
            if (
                len(argv) < 4
                or argv[1] != "-B"
                or Path(argv[2]).resolve() not in {HERE / "au_guardian.py", HERE / "au_fixture.py"}
            ):
                denied.append(event)
                raise RuntimeError("Only fixed owned Linux fixtures permitted")

    sys.addaudithook(audit)
    import au_test_linux

    suite = unittest.defaultTestLoader.loadTestsFromModule(au_test_linux)
    actual = [t.id() for group in suite for t in group]
    expected = {
        "au_test_linux." + c.name + "." + m.name
        for c in ast.parse((HERE / "au_test_linux.py").read_text()).body
        if isinstance(c, ast.ClassDef)
        for m in c.body
        if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")
    }
    began = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    good = (
        result.wasSuccessful()
        and not result.skipped
        and not denied
        and len(actual) == len(expected)
        and set(actual) == expected
        and before == inventory(HERE)
        and time.monotonic() - began < 180
    )
    save(
        a.receipt,
        {
            "status": "pass" if good else "failed",
            "scope": "isolated local Linux ownership; no Torch/x86 science qualification",
            "phase": a.phase,
            "tests_run": result.testsRun,
            "test_ids": actual,
            "errors": len(result.errors),
            "failures": len(result.failures),
            "skipped": len(result.skipped),
            "external_attempts": denied,
            "kernel_observations": au_test_linux.OBSERVATIONS,
            "owned_subprocesses": len(popen),
            "elapsed_seconds": time.monotonic() - began,
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "code_sha256": before,
            "native_release": False,
            "production_roots": 0,
            "Torch_jobs": 0,
            "ANN_searches": 0,
            "exact_searches": 0,
            "provider_calls": 0,
            "real_SQL": 0,
        },
    )
    raise SystemExit(0 if good else 1)


if __name__ == "__main__":
    main()
