# Extension API v1

Publish a Python distribution depending on `fannagent>=0.2,<0.3`. Import SDK contracts and algorithms only through `fannagent.api` and `fannagent.api.primitives`. Register a descriptor instance, rather than a backend factory:

```toml
[project.entry-points."fannagent.backends"]
mydb = "mydb_extension:extension"
```

```python
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from fannagent.api import ExtensionManifest

class Options(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoint_env: str

class Extension:
    def manifest(self):
        return ExtensionManifest(
            "mydb", "mydb-extension", "0.1.0", (1,),
            Options.model_json_schema(), DATA_PROFILE, RUNTIME_PROFILE,
            ("Describe actual qualification limits",),
        )

    def normalize_options(self, options: dict, origin: Path):
        # Resolve extension-owned relative paths against origin here.
        return Options.model_validate(options)

    def create(self, options, context):
        return Backend(options, context)

extension = Extension()
```

Descriptors must be safe to load without database connections or model-provider initialization. Duplicate names, unsupported API versions and malformed manifests fail explicitly. Distribution versions are provenance; profile and native fingerprints express compatibility.

## Interfaces and profiles

Every backend implements inspection, capability description, compatibility, portable `execute_probe(ProbeRequest)`, and `close()`. Declare optional snapshot/exact truth, observation, stopping, preparation and serving capabilities only when their corresponding interfaces are implemented. An inspection-only extension can work without supporting a stopping-policy study. The core requires snapshot, exact truth, observation and stopping before it starts that study.

For a fresh conversation, the core collects inspection after preparation and study compatibility checks and supplies compact backend context before the first model call. The initial user task includes backend identity, capabilities, the snapshot description (including source-to-logical field mappings), budget totals, and development artifact hashes for full inspection and the feature registry. The runtime profile continues to supply feature definitions in the system prompt. Saved conversations resume with their original messages; initialization inspection is not repeated.

`inspect_target()` may include an optional `startup_summary` dictionary containing concise, JSON-serializable, model-visible target details such as database versions, selected index, preserved search settings, and guidance. Extensions own its contents; no new method or API version is required. When omitted, the core uses any existing inspection `settings` and `guidance` alongside the portable baseline. Keep credentials, unrelated inventories, storage paths, and backup prerequisites out of the summary. Build it from the prepared run's inspected identity when available and avoid mutating saved manifests. The complete inspection response remains accessible through `inspect` and the referenced development artifact. Invalid summaries, serialization failures, and artifact-storage failures stop initialization before model spending; the configured input bound still applies.

The backend's `data_profile` and `runtime_profile` match its manifest. Data profiles declare normalized cosine float32, predicate semantics, identifier type, dimensions, k bounds, and the supported in-memory analysis profile. Additional metrics/streaming are future work. Public `Snapshot` maps typed source identifiers to dense internal analysis IDs; integer `1` and string `"1"` remain distinct. Query study results use analysis IDs; application sessions return original source IDs.

Runtime features declare type, stage, group, units, population, scope, availability, provenance, collection cost and source. Only declared runtime features can enter the bounded tree. The language preserves continue/stop actions, strict int64/float64 arithmetic, 255-node/depth-8 bounds and the bounded shape-model payload. `validate_policy` produces the versioned canonical `PolicyArtifact`; `evaluate_policy` provides reference semantics. Extensions own native serialization. Core profile fingerprints exclude release versions, descriptive guidance, feature descriptions and the separately recorded native registry/protocol identity. Both semantic and native identities must remain compatible for execution and deployment.

`ExecutionEvidence` carries execution/query/profile identities, ordered `EvidenceCheckpoint`s, scope, terminal outcome and truncation. Checkpoints pair opaque `CheckpointRef`s with explicitly unit-bearing `WorkMeasure`s. Tokens must identify the same checkpoint across comparable reruns; do not encode per-request nonces or policy decisions in observation prefixes. The core requests real stops using `StopAtCheckpoint`; the extension translates this into native intervention while preserving collection groups. Truncated or mismatched prefixes cannot prove a stop label. Work units are compared within one study, never assumed equivalent across extensions.

## Host services and lifecycle

`ExtensionContext` provides namespaced state and secrets, artifact services, a durable resource journal, private directory, run identity, common resource/evidence/query limits and configuration origin. Store database manifests, restore progress and native bindings in extension state. Obtain credentials from references or private secrets; never place credentials in public configuration, inspection guidance or model-visible artifacts.

Record resource ownership in `context.journal` **before** external creation. Preserve the journal when preparation fails or is interrupted. `prepare_copy()` returns a typed `PreparedEnvironment`; the core records it and owns the resulting study qualification state. `close()` releases connections. `cleanup()` removes only explicitly owned resources, verifies their labels, is idempotent and works without source credentials or a database connection. Retain artifacts and supplied backups. Never modify core spending, split, freeze, evaluator entitlement or deployment state from callbacks. Installed extensions are trusted integration code; these boundaries do not provide process isolation.

The core verifies acceptance, frozen policy and deployment compatibility before opening the extension's `PolicySession`. Sessions implement `query(..., fallback=True)` and `close()`. Mark fallback outcomes and surface execution failures when fallback is disabled.

## Conformance

Use `fannagent.api.conformance.check_descriptor` and `check_observation`. Test unsupported capabilities, changed semantic/native profiles, changed data/index/settings identity, partial preparation recovery, foreign-resource refusal, repeated cleanup, source ID preservation and fallback behavior. Run the independent example's complete study workflow against a built core wheel from an unrelated working directory. Do not use private controller/store modules from an extension; the test driver may use core application entry points.

Core controllers retain calibration aggregation, protected queries/artifacts, freezing, one-shot final-test entitlement and monetary reservations. Database-specific telemetry availability inference stays in the extension. The shared membership-audit primitive accepts an event-bearing trace view; its output is development-only and never a runtime policy feature.

The [complete independent example](../tests/extensions/independent/src/independent_extension/__init__.py) and its own pyproject.toml can be built as a separate test wheel. It imports only public SDK modules.
