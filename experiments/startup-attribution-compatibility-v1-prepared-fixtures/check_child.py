"""Real target interpreter tests; block real database/network/scheduler actions."""

import argparse
import contextlib
import faulthandler
import json
import os
import runpy
import sys
import time
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

from fixture_io import fixture_copies, prepared_seed


@contextlib.contextmanager
def immediate_results(path):
    """Persist each outcome immediately, including class setup errors."""
    original = unittest.TextTestRunner
    with Path(path).open("x", buffering=1) as events:

        def emit(kind, test, **extra):
            events.write(
                json.dumps(
                    dict(kind=kind, test=str(test), monotonic_ns=time.monotonic_ns(), **extra)
                )
                + "\n"
            )

        class Result(unittest.TextTestResult):
            def startTest(self, test):
                emit("start", test)
                super().startTest(test)

            def addSuccess(self, test):
                emit("pass", test)
                super().addSuccess(test)

            def addError(self, test, err):
                emit("error", test, exception=err[0].__name__)
                super().addError(test, err)
                traceback.print_exception(*err, file=self.stream)
                self.stream.flush()

            def addFailure(self, test, err):
                emit("failure", test, exception=err[0].__name__)
                super().addFailure(test, err)
                traceback.print_exception(*err, file=self.stream)
                self.stream.flush()

            def addSubTest(self, test, subtest, err):
                if err is not None:
                    emit("subtest_error", subtest, exception=err[0].__name__)
                    traceback.print_exception(*err, file=self.stream)
                    self.stream.flush()
                super().addSubTest(test, subtest, err)

        def runner(*args, **kwargs):
            kwargs.update(resultclass=Result, failfast=True)
            return original(*args, **kwargs)

        emit("suite_start", "offline main suite")
        try:
            with patch.object(unittest, "TextTestRunner", runner):
                yield emit
        finally:
            emit("suite_end", "offline main suite")


@contextlib.contextmanager
def guard():
    import psycopg

    stats = dict(active=True, denied_connections=0, denied_subprocesses=0, allowed_fixture_shells=0)

    def blocked(*a, **k):
        stats["denied_connections"] += 1
        raise RuntimeError("Native compatibility forbids database connections")

    targets = [
        (psycopg, "connect"),
        (psycopg.Connection, "connect"),
        (psycopg.AsyncConnection, "connect"),
    ]
    original = [(o, n, o.__dict__[n]) for o, n in targets]

    def audit(event, args):
        if event in ("socket.connect", "socket.bind"):
            stats["denied_connections"] += 1
            raise RuntimeError("Native compatibility forbids network access")
        if event == "subprocess.Popen":
            program, argv = args[:2]
            if (
                os.fsdecode(program) not in ("/bin/bash", "/usr/bin/bash")
                or not isinstance(argv, (tuple, list))
                or len(argv) < 2
                or not (str(argv[1]).endswith("/LAUNCHER.sh") or argv[1] == "-n")
            ):
                stats["denied_subprocesses"] += 1
                raise RuntimeError("Only existing fake launcher shell fixtures may spawn")
            stats["allowed_fixture_shells"] += 1

    sys.addaudithook(audit)  # Child lifetime only; child exits before publication.
    try:
        for o, n in targets:
            setattr(o, n, blocked)
        yield stats
    finally:
        for o, n, v in reversed(original):
            setattr(o, n, v)
        stats["connection_bindings_restored"] = all(o.__dict__[n] is v for o, n, v in original)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runner", type=Path, required=True)
    p.add_argument("--guard-receipt", type=Path, required=True)
    p.add_argument("args", nargs=argparse.REMAINDER)
    a = p.parse_args()
    sys.path.insert(0, str(a.runner.parent))
    code = 1
    stats = dict(active=False)
    error = None
    clones = {}
    builds = {}
    faulthandler.enable()
    try:
        with (
            guard() as stats,
            immediate_results(a.guard_receipt.with_suffix(".events.jsonl")) as emit,
        ):
            import sa_fixtures

            sys.argv = [str(a.runner), *a.args]
            if sys.argv[1:2] == ["--"]:
                sys.argv.pop(1)
            with (
                prepared_seed(sa_fixtures.E, emit) as builds,
                fixture_copies(sa_fixtures, emit) as clones,
            ):
                runpy.run_path(str(a.runner), run_name="__main__")
            code = 0
    except SystemExit as e:
        code = int(e.code or 0)
    except BaseException as e:
        error = dict(type=type(e).__name__, message=str(e)[:2048])
        traceback.print_exc()
    stats.update(exit_code=code, audit_hook_scope="child process lifetime only")
    stats.update(fixture_io=clones, fixture_builds=builds, error=error)
    with a.guard_receipt.open("x") as f:
        json.dump(stats, f, indent=2, sort_keys=True)
        f.write("\n")
    raise SystemExit(
        code
        or int(
            not stats["connection_bindings_restored"]
            or stats["denied_connections"]
            or stats["denied_subprocesses"]
        )
    )


if __name__ == "__main__":
    main()
