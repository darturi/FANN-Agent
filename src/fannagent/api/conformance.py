"""Reusable SDK conformance checks for extension authors."""

from dataclasses import asdict

from .contracts import Backend, ExtensionManifest, ProbeRequest, validate_capabilities
from .errors import IncompatibleExtension
from .primitives.hashing import stable_hash


def check_descriptor(manifest: ExtensionManifest, backend: Backend) -> dict:
    manifest.validate()
    capabilities = validate_capabilities(backend, manifest)
    if getattr(backend, "runtime_profile", None) != manifest.runtime_profile:
        raise IncompatibleExtension("backend runtime profile differs from descriptor")
    if getattr(backend, "data_profile", None) != manifest.data_profile:
        raise IncompatibleExtension("backend data profile differs from descriptor")
    return asdict(capabilities)


def check_observation(backend, query: dict) -> dict:
    result = backend.execute_probe(ProbeRequest(query, mode="observation", trace=True))
    evidence = backend.collect_evidence(result)
    if evidence.execution_id != result.execution_id or evidence.query_hash != stable_hash(query):
        raise IncompatibleExtension("execution/query acknowledgement mismatch")
    if evidence.runtime_profile_hash != backend.runtime_profile.fingerprint:
        raise IncompatibleExtension("execution profile acknowledgement mismatch")
    if evidence.scope != backend.runtime_profile.stopping_scope or any(
        c.work.unit != backend.runtime_profile.work_unit for c in evidence.checkpoints
    ):
        raise IncompatibleExtension("observation scope/work units differ from profile")
    return asdict(evidence)
