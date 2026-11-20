"""Typed local/SSH mailbox. Requests are registered once and never retried blindly."""

import json
import re
import shlex
import subprocess
import time
import uuid
from pathlib import Path

from .core import canonical, digest, read, write


class Client:
    def __init__(
        self,
        root,
        output,
        *,
        host=None,
        known_hosts=None,
        control_path=None,
        host_key_alias=None,
        invoke=subprocess.run,
    ):
        self.root, self.output, self.host, self.invoke = str(root), Path(output), host, invoke
        self.options = []
        if host:
            if not re.fullmatch(r"[A-Za-z0-9_.@-]+", host) or not known_hosts:
                raise ValueError("explicit host and pinned known_hosts required")
            self.options = [
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                "UserKnownHostsFile=" + str(known_hosts),
            ]
            if control_path:
                self.options += ["-S", str(control_path)]
            if host_key_alias:
                self.options += ["-o", "HostKeyAlias=" + host_key_alias]
        self.output.mkdir(parents=True, exist_ok=True)

    def call(self, operation, identity=None, payload=None):
        args = ["python3", "-B", "-m", "fannclean.worker", operation, "--root", self.root]
        if identity:
            args += ["--identity", identity]
        # The worker's immutable code path is fixed by the stage, not supplied by the agent.
        command = [
            "env",
            "PYTHONPATH="
            + self.root
            + "/code/experiments/torch-clean-start-v4:"
            + self.root
            + "/code/src:"
            + self.root
            + "/code/experiments/filtered-ann-protocol-v3",
            *args,
        ]
        if self.host:
            command = ["ssh", *self.options, self.host, shlex.join(command)]
        result = self.invoke(
            command,
            input=canonical(payload).decode() if payload else "",
            text=True,
            capture_output=True,
            timeout=45,
        )
        if result.returncode:
            raise ConnectionError(
                "mailbox delivery uncertain; retrieve existing identity, never redispatch"
            )
        return json.loads(result.stdout)

    def status(self):
        return self.call("status")

    def action(self, payload):
        identity = uuid.uuid4().hex
        write(
            self.output / (identity + ".json"),
            {"identity": identity, "payload": payload, "status": "delivery_not_confirmed"},
        )
        admission = self.call("submit", identity, payload)
        if admission.get("status") == "rejected":
            if admission.get("request_id") != identity or admission.get("payload_sha256") != digest(
                payload
            ):
                raise ValueError("admission response binding failed")
            write(self.output / (identity + ".result.json"), admission)
            return admission
        started = time.monotonic()
        while True:
            result = self.call("result", identity)
            if result["status"] != "pending":
                if result.get("request_id") != identity or result.get("payload_sha256") != digest(
                    payload
                ):
                    raise ValueError("response identity/payload mismatch")
                write(self.output / (identity + ".result.json"), result)
                return result
            if time.monotonic() - started > 21660:
                raise TimeoutError(
                    "mailbox wait exceeded the entire allocation; recover existing identity only"
                )
            time.sleep(5)


def require_authorization(root):
    root = Path(root)
    grant = read(root / "authorization.json")
    expected = {
        "run_id": read(root / "config.json")["run_id"],
        "package_sha256": __import__("hashlib")
        .sha256((root / "package-seal.json").read_bytes())
        .hexdigest(),
        "purpose": "clean_start_discovery",
    }
    if (
        grant.get("status") != "authorized"
        or not grant.get("user_instruction")
        or any(grant.get(k) != v for k, v in expected.items())
    ):
        raise ValueError("no matching authorization for this fresh run and its exact caps/assets")
    return grant
