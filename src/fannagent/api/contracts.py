from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from .errors import IncompatibleExtension, UnsupportedCapability
from .policy import PolicyArtifact
from .primitives.hashing import stable_hash
from .profiles import DataProfile, RuntimeProfile

API_VERSION = 1
SourceIdentifier = int | str


@dataclass(frozen=True)
class Capabilities:
    backend: str
    observation: bool = False
    stopping: bool = False
    copy_methods: tuple[str, ...] = ()
    runtime_features: tuple[str, ...] = ()
    routes: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    exact: bool = False
    snapshot: bool = False
    serving: bool = False


@dataclass(frozen=True)
class WorkMeasure:
    value: int | float
    unit: str

    def __post_init__(self):
        import math

        if (
            type(self.value) not in (int, float)
            or not math.isfinite(self.value)
            or self.value < 0
            or not self.unit
        ):
            raise ValueError("invalid work measurement")


@dataclass(frozen=True)
class CheckpointRef:
    component_id: str
    scope: str
    ordinal: int
    token: str

    def __post_init__(self):
        if not self.component_id or not self.scope or not self.token or self.ordinal <= 0:
            raise ValueError("invalid checkpoint reference")


@dataclass(frozen=True)
class StopAtCheckpoint:
    checkpoint: CheckpointRef
    collection_groups: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProbeRequest:
    query: dict
    mode: Literal["native", "observation", "policy"] = "native"
    policy: PolicyArtifact | None = None
    trace: bool = False
    audit: bool = False
    intervention: StopAtCheckpoint | None = None

    def __post_init__(self):
        if self.mode == "policy" and self.policy is None and self.intervention is None:
            raise ValueError("policy execution requires a policy or checkpoint intervention")
        if self.mode != "policy" and (self.policy is not None or self.intervention is not None):
            raise ValueError("interventions require policy execution")
        if self.policy is not None and self.intervention is not None:
            raise ValueError("choose one policy intervention")


@dataclass(frozen=True)
class EvidenceCheckpoint:
    reference: CheckpointRef
    work: WorkMeasure
    features: dict[str, Any]
    availability: dict[str, str] = field(default_factory=dict)
    provenance: str = "server_observed"

    @property
    def observation_hash(self):
        return stable_hash(asdict(self))


@dataclass(frozen=True)
class ExecutionEvidence:
    execution_id: str
    query_hash: str
    runtime_profile_hash: str
    scope: str
    checkpoints: tuple[EvidenceCheckpoint, ...]
    terminal: dict
    truncated: bool = False
    collection_groups: tuple[str, ...] = ()
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if (
            not self.execution_id
            or not self.query_hash
            or not self.runtime_profile_hash
            or not self.scope
        ):
            raise ValueError("evidence is missing execution identity")
        previous: dict[str, int] = {}
        for checkpoint in self.checkpoints:
            reference = checkpoint.reference
            if reference.scope != self.scope or reference.ordinal <= previous.get(
                reference.component_id, 0
            ):
                raise ValueError("evidence checkpoints have invalid scope or order")
            previous[reference.component_id] = reference.ordinal


@dataclass
class ProbeResult:
    ids: list[SourceIdentifier]
    distances: list[float]
    latency_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] | None = None
    execution_id: str = ""


@dataclass(frozen=True)
class ExactTruth:
    eligible_count: int
    effective_k: int
    strictly_better: frozenset[int]
    boundary_ties: frozenset[int]
    eligible_ids: frozenset[int]


@dataclass(frozen=True)
class PreparedEnvironment:
    backend: str
    qualified: bool
    compatibility: dict
    connection_references: tuple[str, ...] = ()
    resources: tuple[dict, ...] = ()
    details: dict = field(default_factory=dict)

    def serialize(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ExtensionManifest:
    name: str
    distribution: str
    version: str
    api_versions: tuple[int, ...]
    configuration_schema: dict
    data_profile: DataProfile
    runtime_profile: RuntimeProfile | None
    limitations: tuple[str, ...] = ()

    def validate(self):
        if not isinstance(self.data_profile, DataProfile) or (
            self.runtime_profile is not None
            and not isinstance(self.runtime_profile, RuntimeProfile)
        ):
            raise IncompatibleExtension("malformed extension profiles")
        if not isinstance(self.api_versions, tuple) or any(
            type(v) is not int for v in self.api_versions
        ):
            raise IncompatibleExtension("malformed API version declaration")
        if API_VERSION not in self.api_versions:
            raise IncompatibleExtension(
                f"extension {self.name!r} does not support API {API_VERSION}"
            )
        if (
            not self.name
            or not self.distribution
            or not self.version
            or not isinstance(self.configuration_schema, dict)
        ):
            raise IncompatibleExtension("malformed extension manifest")

    def serialize(self):
        self.validate()
        return {
            "name": self.name,
            "distribution": self.distribution,
            "version": self.version,
            "api_versions": list(self.api_versions),
            "configuration_schema": self.configuration_schema,
            "data_profile": self.data_profile.model_dump(mode="json"),
            "runtime_profile": self.runtime_profile.describe() if self.runtime_profile else None,
            "limitations": list(self.limitations),
        }


class NamespaceState(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...


class SecretService(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...


class ArtifactService(Protocol):
    def put(
        self, kind: str, value: Any, *, scope: str = "private", limit: int | None = None
    ) -> str: ...
    def read(self, identity: str) -> Any: ...


class ResourceJournal(Protocol):
    def record(self, resource: dict) -> None: ...
    def resources(self) -> tuple[dict, ...]: ...


@dataclass(frozen=True)
class ExecutionLimits:
    cpus: float = 4
    memory_gib: int = 8
    max_evidence_bytes: int = 2 * 1024**3
    trace_max_bytes: int = 64 * 1024**2
    query_timeout_seconds: float = 30


@dataclass(frozen=True)
class ExtensionContext:
    name: str
    run_id: str
    private_directory: Path
    configuration_origin: Path
    limits: ExecutionLimits
    state: NamespaceState
    secrets: SecretService
    artifacts: ArtifactService
    journal: ResourceJournal


@runtime_checkable
class Backend(Protocol):
    def inspect_target(self) -> dict: ...
    def describe_capabilities(self) -> Capabilities: ...
    def compatibility(self) -> dict: ...
    def execute_probe(self, request: ProbeRequest) -> ProbeResult: ...
    def close(self) -> None: ...


@runtime_checkable
class ProvisioningBackend(Protocol):
    def prepare_copy(self) -> PreparedEnvironment: ...
    def cleanup(self) -> dict: ...


@runtime_checkable
class ObservationBackend(Protocol):
    def collect_evidence(self, result: ProbeResult) -> ExecutionEvidence: ...


@runtime_checkable
class StoppingBackend(Protocol):
    def validate_policy(self, raw: dict) -> PolicyArtifact: ...
    def install_policy(self, policy: PolicyArtifact) -> dict: ...


class PolicySession(Protocol):
    def query(self, query: dict, *, fallback: bool = True) -> ProbeResult: ...
    def close(self) -> None: ...


@runtime_checkable
class ServingBackend(Protocol):
    def open_policy_session(self, policy: PolicyArtifact) -> PolicySession: ...


@runtime_checkable
class BackendExtension(Protocol):
    def manifest(self) -> ExtensionManifest: ...
    def normalize_options(self, options: dict, origin: Path) -> BaseModel: ...
    def create(self, options: BaseModel, context: ExtensionContext) -> Backend: ...


def validate_capabilities(backend: Backend, manifest: ExtensionManifest) -> Capabilities:
    capabilities = backend.describe_capabilities()
    if capabilities.backend != manifest.name:
        raise IncompatibleExtension("backend capability identity differs from its extension")
    for enabled, protocol, label in (
        (bool(capabilities.copy_methods), ProvisioningBackend, "provisioning"),
        (capabilities.observation, ObservationBackend, "observation"),
        (capabilities.stopping, StoppingBackend, "stopping"),
        (capabilities.serving, ServingBackend, "serving"),
    ):
        if enabled and not isinstance(backend, protocol):
            raise IncompatibleExtension(f"declared {label} capability has no implementation")
    for enabled, method in (
        (capabilities.snapshot, "snapshot"),
        (capabilities.exact, "exact_reference"),
    ):
        if enabled and not callable(getattr(backend, method, None)):
            raise IncompatibleExtension(f"declared {method} capability has no implementation")
    if capabilities.stopping or capabilities.observation:
        if manifest.runtime_profile is None:
            raise IncompatibleExtension("observation/stopping requires a runtime profile")
        if set(capabilities.runtime_features).difference(manifest.runtime_profile.runtime_features):
            raise IncompatibleExtension("capabilities advertise undeclared runtime features")
    return capabilities


def require_capabilities(
    backend: Backend, *, study: bool = False, preparation: bool = False, serving: bool = False
):
    c = backend.describe_capabilities()
    if study and not (c.snapshot and c.exact and c.observation and c.stopping):
        raise UnsupportedCapability(
            "stopping-policy study requires snapshot, exact truth, observation, and stopping"
        )
    if preparation and not c.copy_methods:
        raise UnsupportedCapability("extension does not support preparation")
    if serving and not c.serving:
        raise UnsupportedCapability("extension does not support application policy sessions")
