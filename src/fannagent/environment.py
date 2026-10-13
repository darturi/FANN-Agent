from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import uuid
from pathlib import Path

from .errors import AgentError
from .submission import InvalidSubmission, error_response, validate_action

# Broker transports wait three hours for a single operation. Allow that entire
# interval plus 180 seconds for syntax checking and 60 seconds for response overhead.
DEVELOPMENT_COMMAND_TIMEOUT_SECONDS = 11040


def rejected_action(exc, tracker, turn_id):
    response = error_response(exc)
    tracker.record(turn_id, error=response.get("error_info"), success=False)
    return {
        "returncode": 1,
        "output": json.dumps(response),
        "extra": {"error_info": response["error_info"]} if "error_info" in response else {},
    }


def exit_action():
    from minisweagent.exceptions import InterruptAgentFlow

    raise InterruptAgentFlow(
        {
            "role": "exit",
            "content": "No candidate submitted",
            "extra": {"exit_status": "no_recommendation"},
        }
    )


def docker(*args):
    process = subprocess.run(["docker", *map(str, args)], capture_output=True, text=True)
    if process.returncode:
        raise AgentError("Docker operation failed: " + process.stderr[-2000:])
    return process.stdout.strip()


def clean_sandboxes(store):
    """Recover sandbox containers after a controller is killed, using durable ownership."""
    for resource in store.get("sandbox_resources", []):
        try:
            item = json.loads(docker("container", "inspect", resource["name"]))[0]
        except AgentError as exc:
            if ("no such container: " + resource["name"].lower()) in str(exc).lower():
                continue
            raise
        labels = item.get("Config", {}).get("Labels", {})
        key, value = resource["label"].split("=", 1)
        if labels.get(key) != value or labels.get("io.fannagent.sandbox") != "true":
            raise AgentError("sandbox ownership changed; cleanup refused")
        docker("rm", "-f", resource["name"])


class ScriptedEnvironment:
    def __init__(self, tools):
        self.tools = tools
        self.turn_id = None

    def execute(self, action):
        # Test doubles never execute arbitrary host shell commands.
        try:
            command = validate_action(action)
        except InvalidSubmission as exc:
            return rejected_action(exc, self.tools.submissions, self.turn_id)
        if command.strip() == "exit 0":
            exit_action()
        try:
            args = shlex.split(command)
        except ValueError:
            return rejected_action(
                InvalidSubmission(
                    "invalid_shell_syntax",
                    "command has unmatched shell quotes",
                    path="command",
                    hint="Close shell quotes and pass JSON as one quoted argument.",
                ),
                self.tools.submissions,
                self.turn_id,
            )
        try:
            if args[0] != "fannagent-tool":
                raise AgentError("scripted environment only accepts broker operations")
            from .broker import dispatch_request

            response = dispatch_request(self.tools, {"argv": args[1:], "turn_id": self.turn_id})
            return {
                "returncode": 0 if response["ok"] else 1,
                "output": json.dumps(response["result"] if response["ok"] else response),
                "extra": {"error_info": response["error_info"]} if "error_info" in response else {},
            }
        except Exception as exc:
            return rejected_action(exc, self.tools.submissions, self.turn_id)

    def get_template_vars(self):
        return {}

    def serialize(self):
        return {"environment": "scripted"}


class ContainerEnvironment:
    def __init__(self, workspace, broker, image=None):
        self.submissions = broker.tools.submissions
        self.turn_id = None
        self.name = "fannagent-agent-" + uuid.uuid4().hex[:12]
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        from .build_workspace import client_hash

        image = image or os.environ.get("FANNAGENT_WORKSPACE_IMAGE", "fannagent/workspace:0.2.0")
        labels = json.loads(docker("image", "inspect", image))[0]["Config"].get("Labels") or {}
        if labels.get("io.fannagent.tool_client") != client_hash():
            raise AgentError("sandbox tool client differs; run fannagent-workspace-build")
        from .store import digest

        store = broker.tools.study.store
        label = "io.fannagent.run=" + digest(str(store.root))[:16]
        resources = store.get("sandbox_resources", [])
        resources.append({"name": self.name, "label": label})
        store.set("sandbox_resources", resources)
        docker(
            "run",
            "-d",
            "--name",
            self.name,
            "--label",
            "io.fannagent.sandbox=true",
            "--label",
            label,
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
        try:
            command = validate_action(action)
        except InvalidSubmission as exc:
            return rejected_action(exc, self.submissions, self.turn_id)
        if command.strip() == "exit 0":
            exit_action()
        started = time.monotonic()
        try:
            syntax = subprocess.run(
                ["docker", "exec", self.name, "bash", "-n", "-c", command],
                text=True,
                capture_output=True,
                timeout=180,
            )
            if syntax.returncode:
                # Bash returns 2 for grammar errors. Docker/shell startup errors retain
                # their ordinary failure behavior and do not consume invalid-turn retries.
                if syntax.returncode == 2:
                    return rejected_action(
                        InvalidSubmission(
                            "invalid_shell_syntax",
                            "command has invalid shell syntax",
                            path="command",
                            hint="Check shell quotes, parentheses, and here-document delimiters.",
                        ),
                        self.submissions,
                        self.turn_id,
                    )
                self.submissions.record(self.turn_id, success=False)
                return {
                    "returncode": syntax.returncode,
                    "output": (syntax.stdout + syntax.stderr)[-64000:],
                }
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "-e",
                    "FANNAGENT_TURN_ID=" + (self.turn_id or ""),
                    self.name,
                    "bash",
                    "-lc",
                    command,
                ],
                text=True,
                capture_output=True,
                timeout=max(
                    0.001, DEVELOPMENT_COMMAND_TIMEOUT_SECONDS - (time.monotonic() - started)
                ),
            )
            self.submissions.record(self.turn_id, success=result.returncode == 0)
            output = (result.stdout + result.stderr)[-64000:]
            info = self.submissions.error_for(self.turn_id)
            if info is not None:
                # Preserve feedback even if the shell redirected or suppressed tool output.
                output += "\n" + json.dumps(
                    {"ok": False, "error": info["message"], "error_info": info}
                )
            return {
                "returncode": result.returncode,
                "output": output,
                "extra": {"error_info": info} if info is not None else {},
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
