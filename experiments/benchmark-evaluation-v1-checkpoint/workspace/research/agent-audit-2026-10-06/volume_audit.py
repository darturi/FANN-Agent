"""Demonstrate Docker's existing-volume behavior using a fresh audit volume."""
import json
import uuid
from pathlib import Path

from fannagent_pgvector.docker import docker

name = "fannagent-audit-volume-" + uuid.uuid4().hex[:12]
label = "io.fannagent.audit=2026-10-06"
docker("volume", "create", "--label", label, "--label", "io.fannagent.run=foreign", name)
try:
    docker("volume", "create", "--label", "io.fannagent.run=claimed", name)
    item = json.loads(docker("volume", "inspect", name))[0]
    assert item["Labels"]["io.fannagent.audit"] == "2026-10-06"
    docker("run", "--rm", "--entrypoint", "sh", "-v", name+":/copy",
           "fannagent/pgvector:0.8.6-core-v2", "-c",
           'test -z "$(ls -A /copy)" && printf audit-marker > /copy/restored-marker')
    marker = docker("run", "--rm", "--entrypoint", "cat", "-v", name+":/copy:ro",
                    "fannagent/pgvector:0.8.6-core-v2", "/copy/restored-marker")
    result = {"label_after_recreate": item["Labels"]["io.fannagent.run"],
              "write_to_existing_empty_volume": marker}
    Path(__file__).with_name("volume-audit-observations.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
finally:
    item = json.loads(docker("volume", "inspect", name))[0]
    assert item["Labels"]["io.fannagent.audit"] == "2026-10-06"
    docker("volume", "rm", name)
