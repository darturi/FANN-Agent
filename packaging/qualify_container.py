"""Run native disposable qualification through an installed controller image."""

import argparse
import os
import subprocess
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="directory containing agent-pgvector/tests and disposable fixture image",
    )
    args = parser.parse_args()
    root, bundle = args.workspace.resolve(), args.bundle.resolve()
    endpoint = (
        os.environ.get("DOCKER_HOST")
        or subprocess.check_output(
            ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"], text=True
        ).strip()
    )
    if not endpoint.startswith("unix://"):
        raise ValueError("native qualification requires a local Docker socket")
    socket = Path(endpoint.removeprefix("unix://"))
    name = "fannagent-native-qualification-" + uuid.uuid4().hex[:12]
    image = (bundle / "controller-pgvector.image").read_text().strip()
    socket_gid = subprocess.check_output(
        [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--mount",
            f"type=bind,source={socket},target=/var/run/docker.sock,readonly",
            "--entrypoint",
            "stat",
            image,
            "-c",
            "%g",
            "/var/run/docker.sock",
        ],
        text=True,
    ).strip()
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--init",
            "--name",
            name,
            "--label",
            "io.fannagent.controller=1",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--group-add",
            socket_gid,
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:rw,size=256m",
            "--mount",
            f"type=bind,source={root},target={root}",
            "--mount",
            f"type=bind,source={bundle},target=/bundle,readonly",
            "--mount",
            f"type=bind,source={socket},target=/var/run/docker.sock",
            "--add-host",
            "host.docker.internal:host-gateway",
            "-e",
            f"FANNAGENT_CONTROLLER={name}",
            "-e",
            "HOME=/tmp",
            "-e",
            "FANNAGENT_PGVECTOR_IMAGE=" + (bundle / "database.image").read_text().strip(),
            "-e",
            "FANNAGENT_QUALIFICATION_SCRIPT=" + str(root / "agent-pgvector/tests/qualify.py"),
            "--entrypoint",
            "sh",
            image,
            "-ec",
            "pip install --no-cache-dir --require-hashes --target /tmp/test-deps "
            "-r /bundle/qualification-requirements.txt >/dev/null && "
            'PYTHONPATH=/tmp/test-deps exec python "$FANNAGENT_QUALIFICATION_SCRIPT"',
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
