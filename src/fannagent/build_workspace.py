"""Build the core-owned development sandbox from an installed distribution."""

import hashlib
import shutil
import subprocess
import tempfile
from importlib.resources import as_file, files
from pathlib import Path


def client_hash():
    return hashlib.sha256(files("fannagent").joinpath("tool_client.py").read_bytes()).hexdigest()


def main():
    with (
        tempfile.TemporaryDirectory(prefix="fannagent-workspace-") as temporary,
        as_file(files("fannagent").joinpath("assets/workspace.Dockerfile")) as path,
    ):
        root = Path(temporary)
        shutil.copy(path, root / "Dockerfile")
        (root / "workspace-requirements.txt").write_bytes(
            files("fannagent").joinpath("assets/workspace-requirements.txt").read_bytes()
        )
        (root / "client.py").write_bytes(files("fannagent").joinpath("tool_client.py").read_bytes())
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(root / "Dockerfile"),
                "--build-arg",
                "TOOL_CLIENT_SHA256=" + client_hash(),
                "-t",
                "fannagent/workspace:0.2.0",
                str(root),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
