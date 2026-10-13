"""Configuration creation and read-only installation diagnostics."""

import os
import shutil
import sys
from importlib.resources import files
from pathlib import Path

import yaml

from .backends import extension
from .config import RunConfig, load_config
from .errors import AgentError


def initialize(backend: str, output: Path):
    selected = extension(backend)
    template = getattr(selected, "configuration_template", None)
    if template:
        content = template()
    elif backend == "fake":
        content = files("fannagent").joinpath("assets/fake.yaml").read_text()
    else:
        raise AgentError("this extension does not supply a configuration template")
    value = yaml.safe_load(content)
    if "research" not in value:
        value["research"] = {"mode": "guided"}
        content = yaml.safe_dump(value, sort_keys=False)
    RunConfig.model_validate(value)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise AgentError(f"configuration already exists: {output}") from None
    with os.fdopen(fd, "w") as handle:
        handle.write(content)
    return {"configuration": str(output.resolve()), "backend": backend}


def diagnose(path: Path, *, check_source=False):
    config = load_config(path)
    selected = extension(config.backend.name)
    options = selected.normalize_options(config.backend.options, config.configuration_origin)
    checks = [
        {
            "name": "python",
            "status": "ok" if (3, 12) <= sys.version_info[:2] < (3, 14) else "fail",
            "detail": "Python 3.12 or 3.13 required",
        },
        {"name": "backend", "status": "ok", "detail": selected.manifest().distribution},
    ]
    if config.workload.queries:
        checks.append(
            {
                "name": "queries",
                "status": "ok" if config.workload.queries.is_file() else "fail",
                "detail": "supplied query JSONL must be readable",
            }
        )
    free = shutil.disk_usage(path.resolve().parent).free
    checks.append(
        {
            "name": "evidence_storage",
            "status": "ok" if free >= config.evidence.max_bytes else "fail",
            "detail": f"{free} bytes available; backups need additional space",
        }
    )
    hook = getattr(selected, "installation_checks", None)
    if hook:
        checks.extend(hook(options, config, check_source=check_source))
    if config.model.model != "scripted":
        import json
        import subprocess

        try:
            image = os.environ.get("FANNAGENT_WORKSPACE_IMAGE", "fannagent/workspace:0.2.0")
            result = subprocess.run(
                ["docker", "image", "inspect", image],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            labels = json.loads(result.stdout)[0]["Config"].get("Labels") or {}
            from .build_workspace import client_hash

            ready = labels.get("io.fannagent.tool_client") == client_hash()
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            ready = False
        checks.append(
            {
                "name": "sandbox",
                "status": "ok" if ready else "fail",
                "detail": "build the matching sandbox with fannagent-workspace-build",
            }
        )
        checks.append(
            {
                "name": "provider_contract",
                "status": "ok",
                "detail": "verified pricing/token contract configured; provider credentials "
                "and API connectivity must be checked with the chosen provider",
            }
        )
    return {
        "ready": all(c["status"] != "fail" for c in checks),
        "checks": checks,
        "source_checked": check_source,
    }
