"""Offline dynamic build and actual PostgreSQL flow; no Torch or provider requests."""

import argparse
import shutil
import subprocess
import tarfile
from pathlib import Path

from limits import SCHEMA, digest, read, sha, write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
IMAGE = "fannagent/torch-reviews-first:20261013"


def main(target):
    target.mkdir(parents=True)
    stage = target / "stage"
    stage.mkdir()
    batch = target / "batch"
    batch.mkdir()
    fixture = target / "fixture"
    shutil.copytree(
        STUDY / "broad-oracle-v1/fixture-v2",
        fixture,
        ignore=shutil.ignore_patterns("checks", "__pycache__", "*.pyc", "*.so"),
    )
    (fixture / "checks").mkdir(mode=0o777)
    for p in HERE.glob("*.py"):
        shutil.copyfile(p, stage / p.name)
    shutil.copytree(
        ROOT / "agent/src/fannagent",
        stage / "src/fannagent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        HERE.parent / "filtered-ann-protocol-v3/fannproto3",
        stage / "protocol/fannproto3",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    with tarfile.open(STUDY / "broad-oracle-v1/benchmark-kit-v3/engine-sources.tar.gz") as f:
        f.extractall(stage, filter="data")
    capture = read(STUDY / "broad-oracle-v1/capture-bindings.json")[0]
    for program in capture["policy"]["programs"].values():
        program["checkpoints"] = list(range(1, 17))
    write(stage / "fixture-capture.json", capture)
    policies = []
    for i, (root, updates, slots) in enumerate(
        [
            (["ge", ["feature", "qualifying_count"], 1], {}, 0),
            (["ge", ["state", 0], 1], {"0": ["add", ["state", 0], 1]}, 1),
            (["gt", ["div", 1, 0], 0], {}, 0),
        ]
    ):
        policies.append(
            {
                "schema": "fannagent.broad-stop.v3",
                "name": f"synthetic-probe-{i}",
                "rationale": "Fixture-only early/state/fault probe, not an agent seed.",
                "fuel": 2000000,
                "state_slots": slots,
                "programs": {
                    f: {"checkpoints": [1, 3, 9, 16], "root": root, "updates": updates}
                    for f in capture["policy"]["programs"]
                },
            }
        )
    payload = {"schema": SCHEMA, "mode": "development", "policies": policies}
    write(
        batch / "request.json",
        {"request_id": "0" * 32, "payload": payload, "payload_sha256": digest(payload)},
    )
    command = [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "--network",
        "none",
        "--mount",
        f"type=bind,src={stage.resolve()},dst=/code,readonly",
        "--mount",
        f"type=bind,src={batch.resolve()},dst=/batch",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--entrypoint",
        "python",
        IMAGE,
        "-B",
        "/code/compile_batch.py",
        "--stage",
        "/code",
        "--batch",
        "/batch",
    ]
    with (target / "build-host.log").open("w") as out:
        subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, timeout=900, check=True)
    (batch / "compiled-programs.json").chmod(0o644)
    (batch / "batch-binding.json").chmod(0o644)
    # Container test files are synthetic, with no host/provider credentials mounted.
    command = [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "--network",
        "none",
        "--mount",
        f"type=bind,src={stage.resolve()},dst=/code,readonly",
        "--mount",
        f"type=bind,src={batch.resolve()},dst=/batch,readonly",
        "--mount",
        f"type=bind,src={fixture.resolve()},dst=/qual",
        "--entrypoint",
        "bash",
        IMAGE,
        "-c",
        "cp /batch/timing-module.so /opt/postgresql/lib/vector.so && "
        "runuser -u nobody -- env PYTHONDONTWRITEBYTECODE=1 "
        "PYTHONPATH=/code:/qual:/opt/torch-reviews/vendor "
        "OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B /code/smoke_flow.py",
    ]
    with (target / "native-host.log").open("w") as out:
        subprocess.run(command, stdout=out, stderr=subprocess.STDOUT, timeout=900, check=True)
    receipt = read(fixture / "checks/live-v3-flow/receipt.json")
    receipt["build_log_sha256"] = sha(target / "build-host.log")
    receipt["native_log_sha256"] = sha(target / "native-host.log")
    write(target / "receipt.json", receipt)
    print(receipt)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    main(p.parse_args().output)
