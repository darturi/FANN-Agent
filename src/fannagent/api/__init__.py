"""Stable extension API v1; no database or model-provider initialization."""

from .contracts import (
    API_VERSION,
    ArtifactService,
    Backend,
    BackendExtension,
    Capabilities,
    CheckpointRef,
    EvidenceCheckpoint,
    ExactTruth,
    ExecutionEvidence,
    ExecutionLimits,
    ExtensionContext,
    ExtensionManifest,
    PolicySession,
    PreparedEnvironment,
    ProbeRequest,
    ProbeResult,
    SourceIdentifier,
    StopAtCheckpoint,
    WorkMeasure,
    require_capabilities,
    validate_capabilities,
)
from .errors import (
    AgentError,
    BudgetExceeded,
    IncompatibleExtension,
    LegacyRun,
    ProtectedEvidence,
    UnsupportedCapability,
    UnsupportedTarget,
)
from .policy import FeatureValue, PolicyArtifact, PolicyInput, evaluate_policy, validate_policy
from .primitives.hashing import stable_hash as digest
from .profiles import DataProfile, FeatureDefinition, RuntimeProfile


def __getattr__(name):
    if name == "Snapshot":
        from ..snapshot import Snapshot

        return Snapshot
    raise AttributeError(name)


__all__ = [
    "API_VERSION",
    "AgentError",
    "ArtifactService",
    "Backend",
    "BackendExtension",
    "BudgetExceeded",
    "Capabilities",
    "CheckpointRef",
    "DataProfile",
    "EvidenceCheckpoint",
    "ExactTruth",
    "ExecutionEvidence",
    "ExecutionLimits",
    "ExtensionContext",
    "ExtensionManifest",
    "FeatureDefinition",
    "FeatureValue",
    "IncompatibleExtension",
    "LegacyRun",
    "PolicyArtifact",
    "PolicyInput",
    "PolicySession",
    "PreparedEnvironment",
    "ProbeRequest",
    "ProbeResult",
    "ProtectedEvidence",
    "RuntimeProfile",
    "Snapshot",
    "SourceIdentifier",
    "StopAtCheckpoint",
    "UnsupportedCapability",
    "UnsupportedTarget",
    "WorkMeasure",
    "digest",
    "evaluate_policy",
    "require_capabilities",
    "validate_capabilities",
    "validate_policy",
]
