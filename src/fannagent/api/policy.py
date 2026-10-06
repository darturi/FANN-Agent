from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import AgentError
from .primitives.hashing import stable_hash
from .primitives.interpreter import PolicyDecision
from .primitives.interpreter import evaluate_policy as _evaluate
from .primitives.policy_tree import INT64_MAX, INT64_MIN, MAX_SHAPE_MODEL_BYTES, validate_node
from .profiles import RuntimeProfile


class FeatureValue(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    available: bool
    value: int | float | bool | None = None

    @model_validator(mode="after")
    def availability(self):
        import math

        if self.available != (self.value is not None):
            raise ValueError("available feature requires a value")
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("feature values must be finite")
        if isinstance(self.value, int) and not INT64_MIN <= self.value <= INT64_MAX:
            raise ValueError("integer feature values must fit in int64")
        return self


class PolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    features: dict[str, FeatureValue]


class PolicyArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    format: Literal["fannagent.bounded_tree.v1"] = "fannagent.bounded_tree.v1"
    name: str = Field(min_length=1)
    root: dict[str, Any] | str
    runtime_profile_hash: str
    numeric_semantics: Literal["int64_float64_strict"] = "int64_float64_strict"
    feature_groups: list[str] = Field(default_factory=list)
    shape_model: dict[str, Any] = Field(default_factory=dict)
    training_provenance: dict[str, Any] = Field(default_factory=dict)

    @property
    def policy_hash(self) -> str:
        return stable_hash(self.model_dump(mode="json"))

    def serialize(self) -> dict:
        return self.model_dump(mode="json")


def validate_policy(raw: dict | PolicyArtifact, profile: RuntimeProfile) -> PolicyArtifact:
    raw = raw.model_dump(mode="python") if isinstance(raw, PolicyArtifact) else dict(raw)
    if raw.get("runtime_profile_hash", profile.fingerprint) != profile.fingerprint:
        raise AgentError("policy runtime profile is incompatible")
    features = profile.runtime_features

    def referenced(node):
        if isinstance(node, dict):
            if "feature" in node:
                yield node["feature"]
            for child in node.values():
                yield from referenced(child)
        elif isinstance(node, list):
            for child in node:
                yield from referenced(child)

    names = set(referenced(raw.get("root")))
    if names.difference(features):
        raise AgentError(
            f"policy references unsupported runtime inputs: {sorted(names.difference(features))}"
        )
    groups = raw.get("feature_groups", sorted({features[name].group for name in names}))
    if len(groups) != len(set(groups)) or set(groups).difference(
        profile.available_collection_groups
    ):
        raise AgentError("policy collection groups are incompatible")
    declared: dict[str, str] = {
        name: feature.kind for name, feature in features.items() if feature.group in groups
    }
    try:
        json.dumps(raw, allow_nan=False, sort_keys=True, separators=(",", ":"))
        root = raw.get("root")
        if not isinstance(root, (dict, str)):
            raise ValueError("policy root is required")
        validate_node(root, feature_kinds=declared)
        raw.update(runtime_profile_hash=profile.fingerprint, feature_groups=groups)
        artifact = PolicyArtifact.model_validate(raw)
        json.dumps(artifact.serialize(), allow_nan=False, sort_keys=True, separators=(",", ":"))
        if len(json.dumps(artifact.shape_model).encode()) > MAX_SHAPE_MODEL_BYTES:
            raise ValueError("shape model exceeds bounded payload")
    except (TypeError, ValueError) as exc:
        raise AgentError(f"invalid policy: {exc}") from None
    return artifact


def evaluate_policy(
    artifact: PolicyArtifact, values: PolicyInput, profile: RuntimeProfile
) -> PolicyDecision:
    validate_policy(artifact, profile)
    definitions = profile.runtime_features
    if set(values.features).difference(definitions):
        raise AgentError("policy inputs contain undeclared features")
    for name, value in values.features.items():
        if not value.available:
            continue
        kind = definitions[name].kind
        if kind == "int" and (type(value.value) is not int or value.value < 0):
            raise AgentError(f"counter {name} must be a nonnegative int64")
        if kind == "float" and (type(value.value) not in (int, float)):
            raise AgentError(f"feature {name} must be numeric")
        if kind == "bool" and type(value.value) is not bool:
            raise AgentError(f"feature {name} must be Boolean")
    return _evaluate(
        artifact,
        values,
        float_features=frozenset(n for n, f in definitions.items() if f.kind == "float"),
    )
