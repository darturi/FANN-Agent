"""Local live-tool client. SSH authentication uses the user's existing trusted route."""

import argparse
import json
import re
import shlex
import subprocess
import time
import uuid
from pathlib import Path

from limits import SCHEMA, canonical, digest, read, write


class TorchClient:
    def __init__(
        self,
        host,
        stage,
        output,
        *,
        invoke=subprocess.run,
        clock=time.monotonic,
        sleep=time.sleep,
        control_path=None,
        known_hosts=None,
    ):
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@-]*", host):
            raise ValueError("trusted SSH host or alias required")
        if not stage.startswith("/") or "\n" in stage:
            raise ValueError("absolute remote stage required")
        self.host, self.stage, self.output = host, stage, Path(output)
        self.invoke, self.clock, self.sleep = invoke, clock, sleep
        self.control_path = control_path
        self.known_hosts = known_hosts
        self.output.mkdir(parents=True, exist_ok=True)

    def call(self, operation, identity=None, payload=None):
        remote = ["python3", self.stage + "/mailbox.py", "--stage", self.stage, operation]
        if identity:
            remote += ["--identity", identity]
        command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
        command += ["-o", "StrictHostKeyChecking=yes"]
        if self.known_hosts:
            command += [
                "-o",
                "HostKeyAlias=login.torch.hpc.nyu.edu",
                "-o",
                "UserKnownHostsFile=" + str(self.known_hosts),
            ]
        if self.control_path:
            command += ["-S", self.control_path]
        command += [self.host, shlex.join(remote)]
        result = self.invoke(
            command,
            input=canonical(payload).decode() if payload is not None else "",
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode:
            raise ConnectionError("SSH failed; retrieve this request's status, never resubmit it")
        return json.loads(result.stdout)

    def evaluate(self, policies, *, identity=None, wait_seconds=20700, mode="development"):
        identity = identity or uuid.uuid4().hex
        if not re.fullmatch(r"[0-9a-f]{32}", identity):
            raise ValueError("32-character request identity required")
        pending = self.output / (identity + ".json")
        if pending.exists():
            raise ValueError("request already exists locally; recover its result instead")
        payload = {"schema": SCHEMA, "policies": policies, "mode": mode}
        write(
            pending,
            {
                "request_id": identity,
                "host": self.host,
                "stage": self.stage,
                "payload": payload,
                "status": "delivery_not_confirmed",
            },
        )
        self.call("submit", identity, payload)
        write(pending, {"request_id": identity, "status": "registered", "payload": payload})
        end = self.clock() + wait_seconds
        while self.clock() < end:
            result = self.call("result", identity)
            if result["status"] not in ("pending",):
                if result.get("request_id") != identity:
                    raise ValueError("remote response belongs to another request; audit it")
                if result["status"] in (
                    "measured",
                    "quality_rejected",
                    "final_complete",
                ) and result.get("payload_sha256") != digest(payload):
                    raise ValueError("remote result's candidate hash differs; audit it")
                write(self.output / (identity + ".result.json"), result)
                return result
            self.sleep(5)
        raise TimeoutError("local wait expired; Torch retains its independent six-hour limit")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("operation", choices=("evaluate", "status", "result"))
    p.add_argument("--policies", type=Path)
    p.add_argument("--identity")
    p.add_argument("--ssh-control-path")
    a = p.parse_args()
    client = TorchClient(a.host, a.stage, a.output, control_path=a.ssh_control_path)
    result = (
        client.evaluate(read(a.policies), identity=a.identity)
        if a.operation == "evaluate"
        else client.call(a.operation, a.identity)
    )
    print(canonical(result).decode())


if __name__ == "__main__":
    main()
