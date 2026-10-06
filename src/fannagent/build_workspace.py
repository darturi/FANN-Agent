"""Build the core-owned development sandbox from an installed distribution."""

import subprocess
from importlib.resources import as_file, files


def main():
    with as_file(files("fannagent").joinpath("assets/workspace.Dockerfile")) as path:
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(path),
                "-t",
                "fannagent/workspace:0.1.0",
                str(path.parent),
            ],
            check=True,
        )
