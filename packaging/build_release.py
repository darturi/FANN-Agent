"""Build a self-contained local installation bundle from both distributions."""

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-controller", action="store_true")
    parser.add_argument("--build-runtime-images", action="store_true")
    parser.add_argument("--save-images", action="store_true")
    parser.add_argument(
        "--python-image",
        default="python@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f",
    )
    parser.add_argument(
        "--docker-image",
        default="docker@sha256:b1805116a6a86cc591b5d5f60a910a0715cdcc9d18d866ad68b1457ead25c35c",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "wheels").mkdir(exist_ok=True)
    for project, requirement in (
        ("agent", "core-requirements.txt"),
        ("agent-pgvector", "pgvector-requirements.txt"),
    ):
        run(sys.executable, "-m", "hatchling", "build", "-t", "wheel", cwd=ROOT / project)
        # Select the wheel built by this version, rather than historic dist files.
        info = tomllib.loads((ROOT / project / "pyproject.toml").read_text())["project"]
        wheel = f"{info['name'].replace('-', '_')}-{info['version']}-py3-none-any.whl"
        shutil.copy2(ROOT / project / "dist" / wheel, output / "wheels" / wheel)
        run(
            "uv",
            "export",
            "--no-cache",
            "--project",
            ROOT / project,
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--no-emit-package",
            "fannagent",
            "--output-file",
            output / requirement,
            stdout=subprocess.DEVNULL,
        )
    names = (
        "install.sh",
        "fannagent-launcher.sh",
        "verify_bundle.py",
        "controller.Dockerfile",
        "compose.yaml",
        ".dockerignore",
        "README.md",
        "verify_installation.py",
        "qualify_container.py",
    )
    for name in names:
        shutil.copy2(HERE / name, output / name)
    (output / "python-version").write_text(platform.python_version() + "\n")
    packages = tomllib.loads((ROOT / "agent/uv.lock").read_text())["package"]
    requirements = []
    for package in packages:
        if package["name"] in {"pytest", "packaging", "pluggy", "iniconfig", "pygments"}:
            hashes = sorted({item["hash"] for item in [package["sdist"], *package["wheels"]]})
            requirements.append(
                package["name"]
                + "=="
                + package["version"]
                + " \\\n"
                + " \\\n".join("    --hash=" + value for value in hashes)
            )
    (output / "qualification-requirements.txt").write_text("\n".join(requirements) + "\n")
    if args.build_runtime_images:
        run(sys.executable, "-m", "fannagent.build_workspace")
        run(sys.executable, "-m", "fannagent_pgvector.build")
    runtime_images = {}
    bases = {}
    if args.build_controller:
        # Resolve and record base images before identifying the release.
        for name, image in (
            ("PYTHON_IMAGE", args.python_image),
            ("DOCKER_IMAGE", args.docker_image),
        ):
            run("docker", "pull", image)
            item = json.loads(
                run("docker", "image", "inspect", image, capture_output=True, text=True).stdout
            )[0]
            bases[name] = item["RepoDigests"][0]
        for name, image in (
            ("sandbox", "fannagent/workspace:0.2.0"),
            ("database", "fannagent/pgvector:0.8.6-secure-v1"),
        ):
            item = json.loads(
                run("docker", "image", "inspect", image, capture_output=True, text=True).stdout
            )[0]
            runtime_images[name] = item["Id"]
            (output / f"{name}.image").write_text(item["Id"] + "\n")
    paths = [
        output / name
        for name in (
            *names,
            "python-version",
            "core-requirements.txt",
            "pgvector-requirements.txt",
            "qualification-requirements.txt",
        )
    ]
    paths.extend((output / "wheels").glob("*.whl"))
    artifacts = {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
    }
    manifest = {
        "schema_version": 1,
        "artifacts": artifacts,
        "supported_installation": ["macos", "linux"],
        # An image's earlier database qualification does not qualify a newly
        # assembled controller bundle. Record actual results separately.
        "native_qualified_architectures": [],
        "native_qualification_driver": "qualify_container.py",
        "images": {
            "database": runtime_images.get("database", "fannagent/pgvector:0.8.6-secure-v1"),
            "sandbox": runtime_images.get("sandbox", "fannagent/workspace:0.2.0"),
        },
        "controller_bases": bases,
    }
    identity = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:20]
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "release-id").write_text(identity + "\n")
    if args.build_controller:
        for backend, requirements in (
            ("fake", "core-requirements.txt"),
            ("pgvector", "pgvector-requirements.txt"),
        ):
            tag = f"fannagent/controller:{identity}-{backend}"
            run(
                "docker",
                "build",
                "-f",
                output / "controller.Dockerfile",
                "-t",
                tag,
                "--build-arg",
                f"BACKEND={backend}",
                "--build-arg",
                f"RELEASE_ID={identity}",
                "--build-arg",
                f"REQUIREMENTS={requirements}",
                "--build-arg",
                "PYTHON_IMAGE=" + bases["PYTHON_IMAGE"],
                "--build-arg",
                "DOCKER_IMAGE=" + bases["DOCKER_IMAGE"],
                output,
            )
            image_id = run(
                "docker",
                "image",
                "inspect",
                tag,
                "--format",
                "{{.Id}}",
                capture_output=True,
                text=True,
            ).stdout.strip()
            (output / f"controller-{backend}.image").write_text(image_id + "\n")
        (output / "image-build.json").write_text(json.dumps(bases, indent=2) + "\n")
        if args.save_images:
            archive = output / "images.tar"
            images = [
                *(runtime_images.values()),
                *(
                    (output / f"controller-{backend}.image").read_text().strip()
                    for backend in ("fake", "pgvector")
                ),
            ]
            run("docker", "save", "--output", archive, *images)
            checksum = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
            (output / "images.tar.sha256").write_text(checksum + "\n")
    for name in ("install.sh", "fannagent-launcher.sh"):
        (output / name).chmod(0o755)
    print(output)


if __name__ == "__main__":
    main()
