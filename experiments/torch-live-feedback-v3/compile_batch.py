"""Compile broad JSON through the trusted v3 compiler; no generated native code."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from limits import digest, read, sha, write


def compile_batch(stage, batch):
    sys.path[:0] = [str(stage / "src"), str(stage / "protocol")]
    from fannproto3.compiler import compile_programs

    from fannagent.api.broad_policy import validate

    request = read(batch / "request.json")
    payload = request["payload"]
    if digest(payload) != request["payload_sha256"]:
        raise ValueError("payload changed after registration")
    arms, bindings = {"native640": None}, []

    def add(name, arm, policy, force=False):
        validate(policy)
        arms[name] = arm
        bindings.append({"arm": arm, "policy": policy, "force_continue": force})

    if payload["mode"] == "final":
        validate(payload["policies"][0])
        if payload["policies"][0]["programs"]:
            add("agent", 60, payload["policies"][0])
        else:
            # Abstention deploys the ordinary native path, without policy dispatch.
            arms["agent"] = None
        add("oracle_full", 61, read(stage / "oracle-full.json"))
        add("oracle_test", 62, read(stage / "oracle-test.json"))
        arms["native_clone"] = None
    else:
        for i, policy in enumerate(payload["policies"], 1):
            add(f"candidate{i}", 59 + i, policy)
            add(f"matched{i}", 69 + i, policy, True)
    empty = {
        "schema": "fannagent.broad-stop.v3",
        "name": "empty-v3",
        "rationale": "Native dispatch control.",
        "fuel": 2000000,
        "state_slots": 0,
        "programs": {},
    }
    add("empty", 85, empty)
    # A sealed synthetic fixture may add an observation-only capture probe.
    # Production preparation never includes this file; requests cannot supply it.
    fixture_capture = stage / "fixture-capture.json"
    if fixture_capture.exists():
        bindings.append(read(fixture_capture))
    code, manifest = compile_programs(bindings)
    engine = batch / "engine"
    shutil.copytree(stage / "engine", engine)
    (engine / "src/compiled_v3.inc").write_text(code)
    result = subprocess.run(
        ["make", "-j1", "OPTFLAGS=", "PG_CONFIG=/opt/postgresql/bin/pg_config"],
        cwd=engine,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (batch / "build.log").write_bytes(result.stdout)
    if result.returncode:
        raise RuntimeError("candidate build failed; preserve build.log")
    shutil.copyfile(engine / "vector.so", batch / "timing-module.so")
    write(batch / "compiled-programs.json", manifest)
    write(
        batch / "batch-binding.json",
        {
            "request_id": request["request_id"],
            "payload_sha256": request["payload_sha256"],
            "mode": payload["mode"],
            "arms": arms,
            "module_sha256": sha(batch / "timing-module.so"),
            "programs_sha256": sha(batch / "compiled-programs.json"),
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--batch", type=Path, required=True)
    a = p.parse_args()
    compile_batch(a.stage, a.batch)
