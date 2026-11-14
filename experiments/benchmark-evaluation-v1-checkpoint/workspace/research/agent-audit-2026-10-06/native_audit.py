"""Run the existing disposable qualification driver with audit failure injection.

No user database or existing Docker resource is used. The driver's labelled
fixtures and copies are removed by its normal finally blocks.
"""
import json
import runpy
from pathlib import Path
from unittest.mock import patch

from fannagent.api import Snapshot
from fannagent_pgvector.docker import docker
from fannagent_pgvector.integration import PgvectorBackend

OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1]
observations = {}
original_prepare = PgvectorBackend.prepare_copy


def audited_prepare(backend):
    if not observations:
        with patch.object(Snapshot, "save", side_effect=RuntimeError("audit sidecar interruption")):
            try:
                original_prepare(backend)
            except RuntimeError as exc:
                assert str(exc) == "audit sidecar interruption"
                observations["interrupted_preparation"] = True
        prepared = original_prepare(backend)
        observations["retry_qualified"] = prepared.qualified
        observations["retry_has_sidecar_manifest"] = bool(backend.context.state.get("sidecar"))
        details = prepared.details
        item = json.loads(docker("inspect", details["container"]))[0]
        observations["copy_network_mode"] = item["HostConfig"]["NetworkMode"]
        ip = item["NetworkSettings"]["Networks"]["bridge"]["IPAddress"]
        observations["unauthenticated_peer_sql"] = docker(
            "run", "--rm", "--label", "io.fannagent.audit=2026-10-06",
            "--entrypoint", "psql", "fannagent/pgvector:0.8.6-core-v2",
            "-h", ip, "-U", "postgres", "-d", "postgres", "-Atc",
            "SELECT current_user,rolsuper FROM pg_roles WHERE rolname=current_user",
        )
        (OUTPUT / "native-audit-observations.json").write_text(json.dumps(observations, indent=2))
        print("audit_observations", json.dumps(observations), flush=True)
        return prepared
    return original_prepare(backend)


PgvectorBackend.prepare_copy = audited_prepare
runpy.run_path(str(ROOT / "agent-pgvector/tests/qualify.py"), run_name="__main__")
