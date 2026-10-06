"""Existing-target inspectors for the next backend milestones.

They deliberately fail the copy/qualification gate. Stock APIs and native backup endpoints
alone do not establish preservation of the physical index or functioning stopping hooks.
"""

import os
from urllib.parse import quote

import httpx

from ..contracts import Capabilities
from ..errors import AgentError, UnsupportedTarget


class UnqualifiedHTTPBackend:
    backend = ""
    version = ""
    copy_method = ""

    def __init__(self, config, store):
        self.config, self.store = config, store
        endpoint = os.environ.get(config.target.connection_env)
        if not endpoint:
            raise AgentError(f"set endpoint credential reference {config.target.connection_env}")
        headers = {}
        if config.target.token_env:
            token = os.environ.get(config.target.token_env)
            if not token:
                raise AgentError("configured HTTP authentication reference is unavailable")
            headers["Authorization"] = "Bearer " + token
        self.client = httpx.Client(
            base_url=endpoint, headers=headers, timeout=config.query_timeout_seconds
        )

    def read(self, path):
        response = self.client.get(path)
        if response.is_error:
            raise AgentError(f"{self.backend} inspection failed with HTTP {response.status_code}")
        return response.json()

    def describe_capabilities(self):
        return Capabilities(
            self.backend,
            limitations=(
                "existing-database restore and stopping integration is not release-qualified",
                f"planned native copy mechanism: {self.copy_method}",
            ),
        )

    def unavailable(self, *args, **kwargs):
        raise UnsupportedTarget(
            f"{self.backend} existing-database integration is not qualified; "
            "inspect is available, but no index is rebuilt or policy applied"
        )

    prepare_copy = unavailable
    snapshot = unavailable
    execute_probe = unavailable
    exact_reference = unavailable
    collect_evidence = unavailable
    install_policy = unavailable
    open_policy_session = unavailable
    validate_policy = unavailable

    def close(self):
        self.client.close()


class WeaviateBackend(UnqualifiedHTTPBackend):
    backend, version, copy_method = "weaviate", "1.39.2", "native collection backup"

    def inspect_target(self):
        metadata = self.read("/v1/meta")
        schema = self.read("/v1/schema/" + quote(self.config.target.resource, safe=""))
        issues = ["existing-index restore qualification and custom identity binding pending"]
        if metadata.get("version") != self.version:
            issues.append(f"planned profile requires Weaviate {self.version}")
        return {
            "backend": self.backend,
            "compatible": False,
            "inspection_available": True,
            "versions": {"weaviate": metadata.get("version")},
            "schema": schema,
            "issues": issues,
            "planned_routes": ["sweeping", "ACORN", "flat"],
            "settings": schema.get("vectorIndexConfig", schema.get("vectorConfig", {})),
        }


class ElasticsearchBackend(UnqualifiedHTTPBackend):
    backend, version, copy_method = "elasticsearch", "9.5.4", "native snapshot segments"

    def inspect_target(self):
        metadata = self.read("/")
        resource = quote(self.config.target.resource, safe="")
        mappings = self.read(f"/{resource}/_mapping")
        settings = self.read(f"/{resource}/_settings?include_defaults=true&flat_settings=true")
        segments = self.read(f"/{resource}/_segments")
        issues = [
            "snapshot segment preservation, multi-segment stopping and merge qualification pending"
        ]
        if metadata.get("version", {}).get("number") != self.version:
            issues.append(f"planned profile requires Elasticsearch {self.version}")
        return {
            "backend": self.backend,
            "compatible": False,
            "inspection_available": True,
            "versions": metadata.get("version"),
            "mappings": mappings,
            "settings": settings,
            "segments": segments,
            "issues": issues,
            "planned_routes": ["Lucene HNSW", "exact fallback", "merged segment search"],
        }
