"""Two bounded offline suites in the unchanged native SIF; no real database."""

import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

from common import MAIN, ROOT, read, save, sha


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
    deadline = min(start + 720, float(os.environ["CC_DEADLINE"]))

    def interrupt(n, f):
        raise TimeoutError("Compatibility signal/deadline " + str(n))

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGALRM):
        signal.signal(sig, interrupt)
    signal.alarm(max(1, int(deadline - start)))
    try:
        if (
            platform.python_version() != "3.12.15"
            or platform.system() != "Linux"
            or platform.machine() != "x86_64"
        ):
            raise RuntimeError("Exact native interpreter required")
        c = read("/compat/COMPATIBILITY-CONTRACT.json")
        expected = c["main_recipe_files_sha256"]
        if {n: sha(MAIN / n) for n in expected} != expected:
            raise RuntimeError("Source recipe differs")
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
            remaining = min(300, deadline - time.monotonic() - 30)
            if remaining <= 0:
                raise TimeoutError("No suite/cleanup reserve")
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
                    end = time.monotonic() + remaining
                    while child.poll() is None:
                        if time.monotonic() > end:
                            raise TimeoutError("Suite deadline: " + phase)
                        if (
                            sum(p.stat().st_size for p in out.iterdir() if p.is_file())
                            > 4 * 1024**2
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
            ):
                raise RuntimeError("Suite/guard/readiness failed: " + phase)
            return dict(tests=128, receipt_sha256=sha(receipt), guard_sha256=sha(guard))

        result["source"] = suite(MAIN, "source")
        # The same builder creates a sealed synthetic candidate; native submit stays blocked.
        import experiment

        if Path(experiment.__file__).resolve().parent != MAIN:
            raise RuntimeError("Wrong builder origin")
        remaining = min(90, deadline - time.monotonic() - 330)
        if remaining <= 0:
            raise TimeoutError("No seal/suite/cleanup reserve")
        signal.alarm(max(1, int(remaining)))
        candidate = experiment.build(work / "candidate", testing=True)
        signal.alarm(max(1, int(deadline - time.monotonic())))
        if not read(candidate / "experiment.json")["synthetic_fixture"]:
            raise RuntimeError("Candidate may not submit")
        save(out / "candidate-manifest.json", read(candidate / "manifest.json"))
        result["sealed"] = suite(candidate, "sealed")
        result["candidate_manifest_sha256"] = sha(candidate / "manifest.json")
        code = 0
    except BaseException as e:
        code = 1
        error = dict(type=type(e).__name__, message=str(e)[:2048])
        save(out / "failure.json", error)
    finally:
        signal.alarm(0)
        stop(child)
        if sum(p.stat().st_size for p in out.iterdir() if p.is_file()) > 4 * 1024**2:
            code = 1
        save(
            out / "status.json",
            dict(
                status="complete" if code == 0 else "failed",
                exit_code=code,
                result=result,
                error=error,
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
    raise SystemExit(code)


if __name__ == "__main__":
    main()
