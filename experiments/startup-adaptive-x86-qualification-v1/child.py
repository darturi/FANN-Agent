# ruff: noqa: E402
"""Fresh target/local interpreter with durable per-case outcomes and external-call guards."""

import sys

sys.dont_write_bytecode = True

import argparse
import contextlib
from pathlib import Path
from unittest.mock import patch

from common import read, save, sha
from paths import configure


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--kind", choices=("main", "a3", "cpu", "build"), required=True)
    p.add_argument("--phase", choices=("source", "sealed"), required=True)
    p.add_argument("--profile", choices=("local", "target"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--candidate", type=Path)
    a = p.parse_args()
    network_attempts = []

    def audit(event, args):
        if event in ("socket.connect", "socket.bind"):
            network_attempts.append(event)
            raise RuntimeError("Qualification child network forbidden")

    sys.addaudithook(audit)
    a.out.mkdir(parents=True, exist_ok=False)
    e = configure(a.workspace, a.source, "main" if a.kind in ("main", "build") else "a3")
    hardware = None
    if a.profile == "target":
        from hardware import capture

        hardware = capture()
        save(a.out / "hardware.json", hardware)
    import check_child

    result = None
    code = 0
    error = None
    try:
        if a.kind == "build":
            candidate = e.build(a.candidate, testing=True)
            save(
                a.out / "receipt.json",
                dict(
                    status="pass",
                    candidate=str(candidate),
                    manifest_sha256=sha(candidate / "manifest.json"),
                    profile=a.profile,
                    Torch_jobs=0,
                ),
            )
            return
        if a.kind == "main":
            argv = [
                str(Path(check_child.__file__)),
                "--runner",
                str(a.source / "run_checks.py"),
                "--guard-receipt",
                str(a.out / "guard.json"),
                "--",
                "--phase",
                a.phase,
                "--receipt",
                str(a.out / "tests.json"),
            ]
            if a.profile == "target":
                argv += [
                    "--target-image-config",
                    "ea7083a544d105d589ac1a3915b7ab8425fe1e867f2afc3ceaf99f0a9a48967f",
                ]
            with patch.object(sys, "argv", argv):
                try:
                    check_child.main()
                except SystemExit as exc:
                    code = int(exc.code or 0)
            result = read(a.out / "tests.json")
            guard = read(a.out / "guard.json")
            if (
                code
                or result["status"] != "pass"
                or result["tests_run"] != 128
                or result["failures"]
                or result["errors"]
                or guard["denied_connections"]
                or guard["denied_subprocesses"]
                or not guard["connection_bindings_restored"]
            ):
                raise RuntimeError("Preserved main suite/guard failed")
            save(
                a.out / "receipt.json",
                dict(
                    status="pass",
                    tests_run=128,
                    profile=a.profile,
                    phase=a.phase,
                    tests_sha256=sha(a.out / "tests.json"),
                    guard_sha256=sha(a.out / "guard.json"),
                    Torch_jobs=0,
                    ANN_searches=0,
                    exact_searches=0,
                ),
            )
            return
        import test_fixtures  # noqa:F401
        from sa_driver import provenance

        review_dir = a.workspace / "trials/torch-reviews-startup-exact-vector-exact-image-review-v1"
        sys.path.insert(0, str(review_dir))
        import review

        if Path(review.__file__).resolve() != review_dir / "review.py":
            raise RuntimeError("Wrong exact-review origin")
        review.STATE.update(
            freeze=read(review_dir / "REVIEW-FREEZE.json"),
            source=a.source.resolve(),
            profile=a.profile,
            adapter_records=[],
        )
        actual = provenance()
        review.require_reference(actual, a.profile)
        denied = []

        def block(*args, **kwargs):
            denied.append("external")
            raise RuntimeError("No real DB/network/process allowed")

        with contextlib.ExitStack() as stack:
            for name in (
                "psycopg.connect",
                "psycopg.Connection.connect",
                "psycopg.AsyncConnection.connect",
                "socket.socket.connect",
                "socket.socket.connect_ex",
                "subprocess.Popen",
                "subprocess.run",
            ):
                stack.enter_context(patch(name, block))
            with check_child.immediate_results(a.out / "events.jsonl"):
                result = (
                    review.correctness(a.source.resolve(), a.profile, False)
                    if a.kind == "a3"
                    else review.cpu_probe()
                )
        if result["status"] != "pass" or denied or provenance() != actual:
            raise RuntimeError("Complete A3/CPU qualification failed")
        if a.kind == "a3" and result["tests_run"] != 276:
            raise RuntimeError("All 272+4 cases required")
        save(a.out / "tests.json" if a.kind == "a3" else a.out / "cpu.json", result)
        save(
            a.out / "receipt.json",
            dict(
                status="pass",
                profile=a.profile,
                phase=a.phase,
                kind=a.kind,
                tests_run=result.get("tests_run", 0),
                actual_provenance=actual,
                code_sha256={
                    n: sha(a.source / n)
                    for n in read(review_dir / "REVIEW-FREEZE.json")["source_inventory"]
                },
                hardware=hardware,
                external_attempts=len(denied),
                bounded_CPU_measurement_qualified=a.kind == "cpu" and a.profile == "target",
                native_CPU_budget_qualified=False,
                native_memory_qualified=False,
                native_release=False,
                Torch_jobs=0,
                ANN_searches=0,
                exact_searches=0,
                real_SQL=0,
            ),
        )
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:2048])
        save(a.out / "failure.json", error)
        raise


if __name__ == "__main__":
    main()
