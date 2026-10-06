from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .primitives.hashing import stable_hash


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DataProfile(ContractModel):
    name: str = "normalized_cosine_f32/v1"
    metric: Literal["cosine"] = "cosine"
    representation: Literal["float32"] = "float32"
    normalized: Literal[True] = True
    predicate_semantics: str = "portable_scalar_v2"
    identifier_representation: Literal["int64", "string", "mixed"] = "mixed"
    min_dimension: int = Field(default=1, gt=0)
    max_dimension: int = Field(default=2000, gt=0)
    max_k: int = Field(default=100, gt=0)
    analysis_profile: Literal["cosine_in_memory_v1"] = "cosine_in_memory_v1"

    @model_validator(mode="after")
    def dimensions(self):
        if self.max_dimension < self.min_dimension:
            raise ValueError("data profile dimension bounds are reversed")
        return self


class FeatureDefinition(ContractModel):
    name: str = Field(min_length=1)
    kind: Literal["int", "float", "bool"]
    stage: Literal["runtime", "development", "evaluator"] = "runtime"
    group: str = "basic"
    units: str = "count"
    population: str = "query"
    scope: str = "query"
    availability: str = "when_observed"
    provenance: str = "server_observed"
    collection_cost: str = "declared_by_extension"
    source: str = "extension"
    description: str = ""


class RuntimeProfile(ContractModel):
    name: str = Field(min_length=1)
    features: dict[str, FeatureDefinition]
    actions: tuple[Literal["continue", "stop"], ...] = ("continue", "stop")
    numeric_semantics: Literal["int64_float64_strict"] = "int64_float64_strict"
    checkpoint_interval: int = Field(gt=0)
    checkpoint_semantics: str
    stopping_scope: str
    work_unit: str
    policy_encoding: str = "bounded_tree_v1"
    collection_groups: tuple[str, ...] = ()
    native_protocol: str = ""
    native_registry_hash: str | None = None
    guidance: str = ""
    scripted_policy: dict | None = None

    @model_validator(mode="after")
    def feature_names(self):
        if any(key != feature.name for key, feature in self.features.items()):
            raise ValueError("feature definition names differ from their registry keys")
        if set(self.actions) != {"continue", "stop"}:
            raise ValueError("bounded_tree_v1 requires continue and stop actions")
        if len(set(self.collection_groups)) != len(self.collection_groups):
            raise ValueError("duplicate profile collection groups")
        if self.collection_groups and {f.group for f in self.features.values()}.difference(
            self.collection_groups
        ):
            raise ValueError("features refer to undeclared collection groups")
        return self

    @property
    def available_collection_groups(self):
        return (
            set(self.collection_groups)
            if self.collection_groups
            else {f.group for f in self.features.values()}
        )

    @property
    def fingerprint(self) -> str:
        value = self.model_dump(
            mode="json",
            exclude={"guidance", "scripted_policy", "native_protocol", "native_registry_hash"},
        )
        for feature in value["features"].values():
            feature.pop("description", None)
            feature.pop("source", None)
        return stable_hash(value)

    @property
    def runtime_features(self) -> dict[str, FeatureDefinition]:
        return {
            name: feature for name, feature in self.features.items() if feature.stage == "runtime"
        }

    def describe(self) -> dict:
        return {**self.model_dump(mode="json"), "fingerprint": self.fingerprint}
