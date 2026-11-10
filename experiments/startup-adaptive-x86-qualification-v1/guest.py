"""Exact non-emulated x86 correctness and CPU measurements; no resource acquisition."""

import math
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from budget import admit, phase
from common import ROOT, inventory, read, save, sha, verify
from paths import A3, MAIN


def stop(child):
    if child and child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
    if child and child.poll() is None:
        raise RuntimeError("Owned child remains live")


def main():
    package = Path("/qual")
    out = Path("/results")
    work = Path("/work")
    child = None
    error = None
    code = 1
    ledger = []
    cleanup = {"status": "pending"}
    result = None
    began = time.monotonic()
    deadline = min(began + 3000, float(os.environ["QX_DEADLINE"]))
    c = read(package / "QUALIFICATION-CONTRACT.json")
    phases = c["phase_seconds"]
    remaining = list(phases)

    def interrupted(n, frame):
        raise TimeoutError("Qualification signal/deadline " + str(n))

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGALRM):
        signal.signal(sig, interrupted)

    def stage(name):
        remaining.remove(name)
        return phase(name, phases[name], deadline, ledger, tail=sum(phases[k] for k in remaining))

    def run(kind, source, label, phase_name):
        nonlocal child
        args = [
            sys.executable,
            "-B",
            "/qual/child.py",
            "--workspace",
            str(ROOT),
            "--source",
            str(source),
            "--kind",
            kind,
            "--profile",
            "target",
            "--phase",
            phase_name,
            "--out",
            str(out / label),
        ]
        if kind == "build":
            args += ["--candidate", str(work / "candidate-main")]
        with (out / (label + ".log")).open("x") as log:
            child = subprocess.Popen(
                args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
            )
            try:
                while child.poll() is None:
                    if time.monotonic() >= min(deadline, ledger[-1]["deadline"]):
                        raise TimeoutError("Qualification child deadline")
                    if (
                        sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
                        > c["limits"]["raw_bytes"]
                    ):
                        raise RuntimeError("Raw evidence cap")
                    time.sleep(0.25)
                if child.returncode:
                    raise RuntimeError("Qualification child failed: " + label)
            finally:
                stop(child)
        child = None
        if read(out / label / "receipt.json")["status"] != "pass":
            raise RuntimeError("Missing complete child proof")

    try:
        admit(began, 3000, deadline)
        with stage("preflight"):
            verify(package)
            from hardware import capture

            hw = capture()
            save(out / "guest-hardware.json", hw)
            sys.path[:0] = [
                str(ROOT / MAIN),
                str(
                    ROOT / "trials/torch-reviews-startup-attribution-v1/"
                    "torch-startup-attribution-v1/frozen/vendor"
                ),
            ]
            from sa_driver import provenance

            if provenance() != c["target_reference"]:
                raise RuntimeError("Exact complete target reference required")
            save(out / "native-provenance.json", provenance())
        with stage("main_source"):
            run("main", ROOT / MAIN, "main-source", "source")
        with stage("candidate_build"):
            run("build", ROOT / MAIN, "candidate-build", "source")
            candidate = Path(read(out / "candidate-build/receipt.json")["candidate"])
            a3 = work / "candidate-a3"
            shutil.copytree(ROOT / A3, a3)
            if inventory(a3) != c["source_inventory"]:
                raise RuntimeError("A3 sealed code differs")
        with stage("main_sealed"):
            run("main", candidate, "main-sealed", "sealed")
        with stage("a3_source"):
            run("a3", ROOT / A3, "a3-source", "source")
        with stage("a3_sealed"):
            run("a3", a3, "a3-sealed", "sealed")
        with stage("cpu"):
            run("cpu", ROOT / A3, "cpu", "source")
        from proofs import validate

        result = validate(out, ROOT, c)
        code = 0
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:2048])
        save(out / "failure.json", error)
    finally:
        signal.alarm(0)
        # Cleanup work and terminal publication share one original 600s endpoint.
        try:
            with phase("guest_cleanup", 600, deadline, ledger):
                stop(child)
                verify(package)
                if inventory(ROOT / A3) != c["source_inventory"]:
                    raise RuntimeError("Protected source changed")
                cleanup = {
                    "status": "pass",
                    "children_stopped": True,
                    "capsule_verified": True,
                    "source_unchanged": True,
                }
                save(out / "guest-integrity.json", cleanup)
            publication_end = ledger[-1]["deadline"]
            left = publication_end - time.monotonic()
            if left <= 0:
                raise TimeoutError("Cleanup publication reserve exhausted")
            signal.alarm(max(1, math.ceil(left)))
            save(
                out / "guest-timing.json",
                dict(
                    started=began,
                    deadline=deadline,
                    finished=time.monotonic(),
                    cleanup_publication_deadline=publication_end,
                    phases=ledger,
                    limits=c["limits"],
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
                    ANN_searches=0,
                    exact_searches=0,
                    SQL=0,
                    provider_calls=0,
                ),
            )
            files = {
                str(p.relative_to(out)): sha(p)
                for p in out.rglob("*")
                if p.is_file()
                and not p.name.startswith("host-")
                and p.name not in ("GUEST-LOCK.json", "HOST-LOCK.json", "guest-terminal.json")
            }
            save(out / "GUEST-LOCK.json", dict(complete=code == 0, files=files))
            save(
                out / "guest-terminal.json",
                dict(
                    finished=time.monotonic(), publication_deadline=publication_end, exit_code=code
                ),
            )
            if time.monotonic() >= publication_end:
                raise TimeoutError("Guest terminal publication deadline")
        except BaseException as exc:
            code = 1
            if not (out / "cleanup-failure.json").exists():
                save(
                    out / "cleanup-failure.json",
                    dict(type=type(exc).__name__, message=str(exc)[:2048]),
                )
        finally:
            signal.alarm(0)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
