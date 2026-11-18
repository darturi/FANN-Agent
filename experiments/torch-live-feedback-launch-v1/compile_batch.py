"""Compile only validated v2 DSL; supplied C, SQL, paths and commands are not accepted."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from limits import digest, read, sha, write


def compile_batch(stage, batch):
    sys.path.insert(0, str(stage / "protocol"))
    sys.path.insert(0, str(stage / "src"))
    from fannproto.compiler import compile_programs
    from fannproto.policy import validate

    request = read(batch / "request.json")
    payload = request["payload"]
    if digest(payload) != request["payload_sha256"]:
        raise ValueError("payload changed after registration")
    policies = payload["policies"]
    programs = []
    arms = {"native640": None}
    for i, policy in enumerate(policies):
        validate(policy)
        for name, arm, force in (
            (f"candidate{i + 1}", 20 + i, False),
            (f"matched{i + 1}", 30 + i, True),
        ):
            arms[name] = arm
            programs.append({"arm": arm, "policy": policy, "force_continue": force})
    empty = {
        "schema": "fannagent.filtered-ann.v2",
        "name": "live_empty",
        "rules": {},
        "rationale": "Researcher dispatch control.",
    }
    arms["empty"] = 43
    programs.append({"arm": 43, "policy": empty, "force_continue": False})
    code, manifest = compile_programs(programs)
    # Engine sources were extracted and hash-verified when the local kit was prepared.
    engine = batch / "engine"
    shutil.copytree(stage / "engine", engine)
    (engine / "src/compiled_v2.inc").write_text(code)
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
            "module_sha256": sha(batch / "timing-module.so"),
            "arms": arms,
            "programs_sha256": sha(batch / "compiled-programs.json"),
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--batch", type=Path, required=True)
    args = p.parse_args()
    compile_batch(args.stage, args.batch)
