"""Bounded local Docker correctness suites, exact existing image, no network/DB."""

import argparse
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
SOURCE = ROOT / "agent/experiments/startup-attribution-v1-image-reference"
OUTPUT = ROOT / "trials/torch-reviews-startup-attribution-v1-image-reference"
IMAGE = "sha256:ea7083a544d105d589ac1a3915b7ab8425fe1e867f2afc3ceaf99f0a9a48967f"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["source", "sealed"])
    a = p.parse_args()
    image = json.loads(subprocess.check_output(["docker", "image", "inspect", IMAGE], text=True))[0]
    if image["Id"] != IMAGE or image["Os"] != "linux" or image["Architecture"] != "amd64":
        raise RuntimeError("Existing exact image identity differs; never pull or rebuild")
    path = (
        SOURCE if a.phase == "source" else OUTPUT / "torch-startup-attribution-v1-image-reference"
    )
    receipt = "target-checks-" + a.phase + ".json"
    log = OUTPUT / ("target-checks-" + a.phase + ".log")
    record = OUTPUT / ("target-container-" + a.phase + ".json")
    if any(q.exists() for q in (OUTPUT / receipt, log, record)):
        raise FileExistsError("Preserve existing target check evidence")
    name = "fann-a2-check-" + a.phase + "-" + uuid.uuid4().hex[:12]
    cmd = [
        "docker",
        "create",
        "--name",
        name,
        "--label",
        "fannagent.scope=a2-offline-correctness",
        "--platform=linux/amd64",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--cpus=2",
        "--memory=3g",
        "--memory-swap=3g",
        "--pids-limit=128",
        "--user",
        str(os.getuid()) + ":" + str(os.getgid()),
        "--tmpfs",
        "/work:rw,exec,nosuid,nodev,size=1792m,mode=1777",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=64m,mode=1777",
        "--mount",
        "type=bind,src=" + str(ROOT) + ",dst=" + str(ROOT) + ",readonly",
        "--mount",
        "type=bind,src=" + str(OUTPUT) + ",dst=/receipts",
        "--env",
        "TMPDIR=/work",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "OPENBLAS_NUM_THREADS=1",
        "--env",
        "OMP_NUM_THREADS=1",
        "--env",
        "PYTHONPATH=" + str(path) + ":/opt/torch-reviews/vendor",
        IMAGE,
        "python",
        str(path / "run_checks.py"),
        "--phase",
        a.phase,
        "--receipt",
        "/receipts/" + receipt,
        "--target-image-config",
        IMAGE.removeprefix("sha256:"),
    ]
    cid = None
    started = time.monotonic()
    evidence = dict(
        scope="offline synthetic correctness only",
        phase=a.phase,
        image=IMAGE,
        command=cmd,
        ANN_searches=0,
        exact_searches=0,
        native_database_queries=0,
        network="none",
        new_Torch_jobs=0,
    )
    try:
        cid = subprocess.check_output(cmd, text=True).strip()
        evidence["container_id"] = cid
        with log.open("x") as handle:
            result = subprocess.run(
                ["docker", "start", "-a", cid], stdout=handle, stderr=subprocess.STDOUT, timeout=900
            )
        evidence["command_exit_code"] = result.returncode
    except BaseException as error:
        evidence["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if cid:
            subprocess.run(
                ["docker", "stop", "--time=10", cid], capture_output=True, text=True, timeout=30
            )
            actual = json.loads(subprocess.check_output(["docker", "inspect", cid], text=True))[0]
            evidence["container_state"] = actual["State"]
            evidence["actual_host_config"] = {
                k: actual["HostConfig"][k]
                for k in (
                    "NetworkMode",
                    "ReadonlyRootfs",
                    "Memory",
                    "MemorySwap",
                    "NanoCpus",
                    "PidsLimit",
                    "CapDrop",
                    "Tmpfs",
                    "SecurityOpt",
                )
            }
            subprocess.run(
                ["docker", "rm", cid], check=True, capture_output=True, text=True, timeout=30
            )
            evidence["owned_container_removed"] = True
        evidence["elapsed_seconds"] = time.monotonic() - started
        with record.open("x") as handle:
            json.dump(evidence, handle, indent=2, sort_keys=True)
            handle.write("\n")
    report = json.loads((OUTPUT / receipt).read_text())
    if evidence["command_exit_code"] or report["status"] != "pass":
        raise RuntimeError("Target correctness checks failed; preserved log and receipt")
    print(
        json.dumps(
            dict(
                status="pass",
                phase=a.phase,
                tests=report["tests_run"],
                python=report["python"],
                network="none",
                native_database_queries=0,
                owned_container_removed=True,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
