"""Offline agent research in a container exposing only development evidence."""

import os
import subprocess
import uuid
from pathlib import Path

from limits import read, sha, write


class ResearchWorkspace:
    def __init__(self, root, image, *, invoke=subprocess.run):
        self.root, self.image, self.invoke = Path(root).resolve(), image, invoke
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ("policies", "scratch"):
            (self.root / name).mkdir(exist_ok=True)

    def execute(self, code):
        if type(code) is not str or not 1 <= len(code.encode()) <= 65536:
            raise ValueError("Python source must contain 1..65536 bytes")
        name = uuid.uuid4().hex
        record = self.root.parent / "research-executions" / name
        record.mkdir(parents=True)
        (record / "source.py").write_text(code)
        command = [
            "docker",
            "run",
            "--interactive",
            "--rm",
            "--platform",
            "linux/amd64",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "128",
            "--memory",
            "2g",
            "--cpus",
            "1",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--tmpfs",
            "/tmp:rw,nosuid,size=256m",
            "--workdir",
            "/workspace",
            "--mount",
            f"type=bind,src={self.root},dst=/workspace",
            "--mount",
            f"type=bind,src={self.root / 'evidence'},dst=/workspace/evidence,readonly",
            "--mount",
            f"type=bind,src={self.root / 'api'},dst=/workspace/api,readonly",
            "--env",
            "PYTHONPATH=/workspace/api:/opt/torch-reviews/vendor",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "OPENBLAS_NUM_THREADS=1",
            "--env",
            "OMP_NUM_THREADS=1",
            "--entrypoint",
            "python",
            self.image,
            "-B",
            "-",
        ]
        # A CID lets the host terminate a timed-out container, not just its Docker client.
        cid = record / "container-id"
        command[2:2] = ["--cidfile", str(cid)]
        status = None
        try:
            with (record / "output.txt").open("w") as output:
                result = self.invoke(
                    command,
                    input=code,
                    text=True,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    timeout=240,
                    check=False,
                )
                status = result.returncode
        except subprocess.TimeoutExpired:
            status = "timeout"
        finally:
            if status == "timeout" and cid.exists():
                self.invoke(
                    ["docker", "rm", "-f", cid.read_text().strip()],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
        output = (record / "output.txt").read_text(errors="replace")
        answer = {
            "execution_id": name,
            "exit_code": status,
            "output": output[-16000:],
            "output_truncated": len(output) > 16000,
            "source_sha256": sha(record / "source.py"),
            "policy_files": sorted(
                str(p.relative_to(self.root)) for p in (self.root / "policies").glob("*.json")
            ),
        }
        write(record / "receipt.json", answer)
        return answer

    def policies(self, arguments):
        if type(arguments) is not dict or not set(arguments) <= {"policies", "policy_paths"}:
            raise ValueError("submit inline policies or workspace policy_paths")
        values, paths = arguments.get("policies", []), arguments.get("policy_paths", [])
        if (
            type(values) is not list
            or type(paths) is not list
            or not 1 <= len(values) + len(paths) <= 3
        ):
            raise ValueError("one to three v3 policies per native batch")
        values = list(values)
        for name in paths:
            if type(name) is not str:
                raise ValueError("policy path must be text")
            path = (self.root / name).resolve(strict=True)
            if (
                not path.is_relative_to(self.root / "policies")
                or not path.is_file()
                or path.stat().st_size > 8 * 1024**2
            ):
                raise ValueError("policy path must be a bounded file under policies/")
            values.append(read(path))
        return values
