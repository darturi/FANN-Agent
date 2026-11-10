"""Two bounded offline suites in the unchanged native SIF; no real database."""

import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

from budget import LIMITS, admit, validate
from budget import phase as phase_budget
from common import MAIN, ROOT, read, replace, save, sha


def stop(child):
    if child and child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)


def main():
    out = Path("/results")
    work = Path("/work")
    child = None
    error = None
    code = 1
    result = {}
    start = time.monotonic()
    limits = LIMITS
    deadline = min(start + limits["guest_seconds"], float(os.environ["CC_DEADLINE"]))
    ledger = []
    cleanup = dict(status="pending")

    def interrupt(n, f):
        raise TimeoutError("Compatibility signal/deadline " + str(n))

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGALRM):
        signal.signal(sig, interrupt)
    try:
        # A late container start must fail before tests, never shrink a suite.
        admit(start, limits["guest_seconds"], deadline)
        with phase_budget(
            "preflight",
            limits["guest_preflight_seconds"],
            deadline,
            ledger,
            tail=limits["guest_seconds"] - limits["guest_preflight_seconds"],
            began=start,
        ):
            if (
                platform.python_version() != "3.12.15"
                or platform.system() != "Linux"
                or platform.machine() != "x86_64"
            ):
                raise RuntimeError("Exact native interpreter required")
            c = read("/compat/COMPATIBILITY-CONTRACT.json")
            validate(c["limits"])
            expected = c["main_recipe_files_sha256"]
            if {n: sha(MAIN / n) for n in expected} != expected:
                raise RuntimeError("Source recipe differs")
            first = ROOT / "trials/torch-reviews-first"
            for n, expected_hash in c["fixture_dependency_files_sha256"].items():
                if sha(first / n) != expected_hash:
                    raise RuntimeError("Offline dependency differs: " + n)
            save(out / "fixture-dependencies.json", c["fixture_dependency_files_sha256"])
            sys.path[:0] = [
                str(MAIN),
                str(
                    ROOT
                    / "trials/torch-reviews-startup-attribution-v1"
                    / "torch-startup-attribution-v1/frozen/vendor"
                ),
            ]
            from sa_driver import provenance

            if provenance() != read(MAIN / "IMAGE-REFERENCE.json"):
                raise RuntimeError("Exact image provenance differs")
            save(out / "native-provenance.json", provenance())

        def suite(path, phase):
            nonlocal child
            cap = limits[phase + "_suite_seconds"]
            tail = limits["guest_cleanup_seconds"]
            if phase == "source":
                tail += limits["candidate_build_seconds"] + limits["sealed_suite_seconds"]
            with phase_budget(phase, cap, deadline, ledger, tail=tail) as end:
                receipt = out / ("target-checks-" + phase + ".json")
                guard = out / ("guard-" + phase + ".json")
                cmd = [
                    sys.executable,
                    "/compat/check_child.py",
                    "--runner",
                    str(path / "run_checks.py"),
                    "--guard-receipt",
                    str(guard),
                    "--",
                    "--phase",
                    phase,
                    "--receipt",
                    str(receipt),
                    "--target-image-config",
                    "ea7083a544d105d589ac1a3915b7ab8425fe1e867f2afc3ceaf99f0a9a48967f",
                ]
                with (out / ("checks-" + phase + ".log")).open("x") as log:
                    child = subprocess.Popen(
                        cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
                    )
                    try:
                        while child.poll() is None:
                            if time.monotonic() >= end:
                                raise TimeoutError("Suite deadline: " + phase)
                            if (
                                sum(p.stat().st_size for p in out.iterdir() if p.is_file())
                                > limits["raw_bytes"]
                            ):
                                raise RuntimeError("Raw evidence cap")
                            time.sleep(0.25)
                        rc = child.returncode
                    finally:
                        stop(child)
                child = None
                data = read(receipt)
                g = read(guard)
                if (
                    rc
                    or data["status"] != "pass"
                    or data["tests_run"] != 128
                    or data["python"] != "3.12.15"
                    or data["recipe_files_sha256"] != expected
                    or g["denied_connections"]
                    or g["denied_subprocesses"]
                    or not g["connection_bindings_restored"]
                    or g["exit_code"]
                    or g["error"] is not None
                    or g["fixture_io"]["clones"] < 1
                    or g["fixture_io"]["clones"] != g["fixture_io"]["seeds_verified"]
                    or g["fixture_io"]["reseals"] != 10
                    or g["fixture_builds"]
                    != dict(
                        requests=5, actual_builds=1, reused=4, seed_verifications=6, restored=True
                    )
                ):
                    raise RuntimeError("Suite/guard/readiness failed: " + phase)
                return dict(tests=128, receipt_sha256=sha(receipt), guard_sha256=sha(guard))

        result["source"] = suite(MAIN, "source")
        # Original unpatched builder; candidate checks are included in its cap.
        with phase_budget(
            "candidate",
            limits["candidate_build_seconds"],
            deadline,
            ledger,
            tail=limits["sealed_suite_seconds"] + limits["guest_cleanup_seconds"],
        ):
            import experiment

            if Path(experiment.__file__).resolve().parent != MAIN:
                raise RuntimeError("Wrong builder origin")
            candidate = experiment.build(work / "candidate", testing=True)
            if not read(candidate / "experiment.json")["synthetic_fixture"]:
                raise RuntimeError("Candidate may not submit")
            save(out / "candidate-manifest.json", read(candidate / "manifest.json"))
            result["candidate_manifest_sha256"] = sha(candidate / "manifest.json")
        result["sealed"] = suite(candidate, "sealed")
        code = 0
    except BaseException as e:
        code = 1
        error = dict(type=type(e).__name__, message=str(e)[:2048])
        save(out / "failure.json", error)
    finally:
        signal.alarm(0)
        try:
            with phase_budget("guest_cleanup", limits["guest_cleanup_seconds"], deadline, ledger):
                stop(child)
                if (
                    sum(p.stat().st_size for p in out.iterdir() if p.is_file())
                    > limits["raw_bytes"]
                ):
                    raise RuntimeError("Raw evidence cap")
                cleanup = dict(
                    status="pass", child_stopped=child is None or child.poll() is not None
                )
                if not cleanup["child_stopped"]:
                    raise RuntimeError("Owned child not stopped")
                save(out / "cleanup.json", cleanup)
        except BaseException as e:
            code = 1
            cleanup = dict(status="failed", error_type=type(e).__name__, message=str(e)[:2048])
            if error is None:
                error = dict(type=type(e).__name__, message=str(e)[:2048])
            if not (out / "failure.json").exists():
                save(out / "failure.json", error)
            replace(out / "cleanup.json", cleanup)
        finally:
            signal.alarm(0)
        # Publication remains inside the same30s finalization interval. Failure
        # publication may be partial; the host then locks it incomplete.
        publish_end = next(
            (r["deadline_monotonic"] for r in reversed(ledger) if r["phase"] == "guest_cleanup"),
            deadline,
        )
        try:
            import math

            left = publish_end - time.monotonic()
            if left <= 0:
                raise TimeoutError("Guest publication reserve exhausted")
            signal.alarm(max(1, math.ceil(left)))
            save(
                out / "phase-timing.json",
                dict(
                    limits=limits, phases=ledger, cleanup=cleanup, guest_deadline_monotonic=deadline
                ),
            )
            save(
                out / "status.json",
                dict(
                    status="complete" if code == 0 else "failed",
                    exit_code=code,
                    result=result,
                    error=error,
                    cleanup=cleanup,
                    elapsed_seconds=time.monotonic() - start,
                    ANN_searches=0,
                    exact_searches=0,
                    SQL=0,
                    database_connections=0,
                    postgres_servers=0,
                    main_A2_launched=False,
                    provider_calls=0,
                ),
            )
            if time.monotonic() >= publish_end:
                raise TimeoutError("Guest terminal publication deadline")
        except BaseException as e:
            code = 1
            signal.alarm(0)
            if not (out / "failure.json").exists():
                save(out / "failure.json", dict(type=type(e).__name__, message=str(e)[:2048]))
            replace(
                out / "status.json",
                dict(
                    status="failed",
                    exit_code=1,
                    result=result,
                    error=error or dict(type=type(e).__name__, message=str(e)[:2048]),
                    cleanup=dict(status="failed"),
                    main_A2_launched=False,
                    ANN_searches=0,
                    exact_searches=0,
                    SQL=0,
                    database_connections=0,
                    postgres_servers=0,
                    provider_calls=0,
                    elapsed_seconds=time.monotonic() - start,
                ),
            )
        finally:
            signal.alarm(0)

    raise SystemExit(code)


if __name__ == "__main__":
    main()
