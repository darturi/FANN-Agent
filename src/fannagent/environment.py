from __future__ import annotations

import json
import os
import shlex
import subprocess
import uuid
from pathlib import Path

from .errors import AgentError


def docker(*args):
    process = subprocess.run(["docker", *map(str, args)], capture_output=True, text=True)
    if process.returncode:
        raise AgentError("Docker operation failed: " + process.stderr[-2000:])
    return process.stdout.strip()


class ScriptedEnvironment:
    def __init__(self, tools):
        self.tools = tools

    def execute(self, action):
        # Test doubles never execute arbitrary host shell commands.
        args = shlex.split(action["command"])
        try:
            if args[0] != "fannagent-tool" or len(args) != 3:
                raise AgentError("scripted environment only accepts broker operations")
            output = self.tools.call(args[1], json.loads(args[2]))
            return {"returncode": 0, "output": json.dumps(output)}
        except Exception as exc:
            return {
                "returncode": 1,
                "output": str(exc) if isinstance(exc, AgentError) else type(exc).__name__,
            }

    def get_template_vars(self):
        return {}

    def serialize(self):
        return {"environment": "scripted"}


class ContainerEnvironment:
    def __init__(self, workspace, broker, image="fannagent/workspace:0.1.0"):
        self.name = "fannagent-agent-" + uuid.uuid4().hex[:12]
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        import fannagent.tool_client

        client = Path(fannagent.tool_client.__file__)
        docker(
            "run",
            "-d",
            "--name",
            self.name,
            "--label",
            "io.fannagent.sandbox=true",
            "--read-only",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=128",
            "--memory=2g",
            "--cpus=2",
            "--tmpfs",
            "/tmp:rw,size=256m",
            "--network=none",
            "-v",
            f"{self.workspace}:/workspace",
            "-v",
            f"{client}:/tools/client.py:ro",
            "-e",
            "FANNAGENT_QUEUE=/workspace/.broker",
            "-e",
            "FANNAGENT_TOKEN=" + broker.token,
            "-w",
            "/workspace",
            image,
            "sleep",
            "infinity",
        )

    def execute(self, action):
        if action["command"].strip() == "exit 0":
            from minisweagent.exceptions import InterruptAgentFlow

            raise InterruptAgentFlow(
                {
                    "role": "exit",
                    "content": "No candidate submitted",
                    "extra": {"exit_status": "no_recommendation"},
                }
            )
        try:
            result = subprocess.run(
                ["docker", "exec", self.name, "bash", "-lc", action["command"]],
                text=True,
                capture_output=True,
                timeout=180,
            )
            return {
                "returncode": result.returncode,
                "output": (result.stdout + result.stderr)[-64000:],
            }
        except subprocess.TimeoutExpired:
            # Kill the entire container to prevent a timed-out process continuing hidden work.
            self.close()
            raise AgentError("development command timed out; sandbox stopped") from None

    def get_template_vars(self):
        return {"workspace": "/workspace", "tool": "fannagent-tool"}

    def serialize(self):
        return {"environment": "isolated_container"}

    def close(self):
        if self.name:
            docker("rm", "-f", self.name)
            self.name = None
