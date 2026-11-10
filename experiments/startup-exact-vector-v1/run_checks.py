"""Run A3's offline prototype under explicit connection/process denials."""

import hashlib
import json
import platform
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = ROOT / "trials/torch-reviews-startup-exact-vector-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ids(node):
    if isinstance(node, unittest.TestSuite):
        return [name for child in node for name in test_ids(child)]
    return [node.id()]


def main():
    files = {p.name: sha(p) for p in HERE.glob("*.py")}
    before = json.loads((OUTPUT / "preservation-before.json").read_text())
    for name, expected in before.items():
        if sha(ROOT / name) != expected:
            raise RuntimeError("Preexisting evidence changed before checks: " + name)
    denied = []

    def deny(*args, **kwargs):
        denied.append("connection/process")
        raise AssertionError("A3 offline scope prohibits connections and subprocesses")

    started = time.monotonic()
    # The tests import the exact frozen source tree; no returned Python is loaded.
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
    cases = test_ids(suite)
    with ExitStack() as stack:
        for name in (
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "subprocess.Popen",
            "psycopg.connect",
            "psycopg.Connection.connect",
        ):
            stack.enter_context(patch(name, deny))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    changed = [name for name, expected in before.items() if sha(ROOT / name) != expected]
    stable = files == {p.name: sha(p) for p in HERE.glob("*.py")}
    import numpy
    import pyarrow
    import pydantic

    receipt = {
        "status": "pass"
        if result.wasSuccessful() and not denied and not changed and stable
        else "fail",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "test_ids": cases,
        "elapsed_seconds": time.monotonic() - started,
        "phase": "A3 bounded offline prototype; native producer not implemented",
        "python": platform.python_version(),
        "dependencies": {
            "numpy": numpy.__version__,
            "pyarrow": pyarrow.__version__,
            "pydantic": pydantic.__version__,
        },
        "candidate_files_sha256": files,
        "candidate_source_stable": stable,
        "freeze_sha256": sha(OUTPUT / "A3-FREEZE.json"),
        "preexisting_files_preserved": len(before),
        "changed_preexisting_files": changed,
        "blocked_connection_process_attempts": len(denied),
        "fixture_rows_max": 64,
        "dimensions": 768,
        "ANN_searches": 0,
        "exact_searches": 0,
        "SQL": 0,
        "native_database_connections": 0,
        "Torch_submissions": 0,
        "SSH": 0,
        "native_target_correctness_qualified": False,
        "native_memory_or_savings_qualified": False,
        "full_B2f_released": False,
    }
    with (OUTPUT / "local-checks.json").open("x") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(receipt["status"] != "pass")


if __name__ == "__main__":
    main()
