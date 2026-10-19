from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..api import FeatureValue, PolicyInput, RuntimeProfile
from ..store import digest

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Name = Annotated[str, Field(min_length=1, max_length=256)]
Recall = Annotated[float, Field(ge=0, le=1)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class TrainingEntitlement(Record):
    query_id: Name
    group: Name
    stratum: Name
    split: Literal["learning"] = "learning"


class Checkpoint(Record):
    checkpoint_index: int = Field(gt=0)
    features: dict[str, int | float | bool | None]


class StopOutcome(Record):
    checkpoint_index: int = Field(gt=0)
    recall: Recall
    returned_count: int = Field(ge=0)
    valid: bool
    actual_work: int = Field(ge=0)
    prefix_matches: bool
    # The source's native verification can cover more fields than a sanitized export.
    # Preserve its proof; never claim a rehash of sanitized fields reverified execution.
    source_prefix_sha256: Hash
    source_ref: Name

    @model_validator(mode="after")
    def verified_prefix(self):
        if self.prefix_matches is not True:
            raise ValueError("prefix_matches must record successful native verification")
        return self


class TrainingQuery(TrainingEntitlement):
    effective_k: int = Field(gt=0)
    native_recall: Recall
    native_work: int = Field(ge=0)
    trajectory_complete: bool = True
    checkpoints: list[Checkpoint]
    outcomes: list[StopOutcome]


class TimingPair(Record):
    query_id: Name
    policy_hash: Hash
    regime: Literal["activation-cold", "reused-warm"]
    block: int = Field(ge=0)
    repetition: int = Field(ge=0)
    native_ms: float = Field(gt=0, le=1e9)
    policy_ms: float = Field(gt=0, le=1e9)
    native_recall: Recall
    policy_recall: Recall
    valid: bool
    returned_count: int = Field(ge=0)
    source_ref: Name


class TimingSchedule(Record):
    blocks: list[int] = Field(min_length=1, max_length=64)
    cold_passes: int = Field(default=1, gt=0, le=1000)
    warm_passes: int = Field(default=3, gt=0, le=1000)

    @model_validator(mode="after")
    def unique_blocks(self):
        if len(set(self.blocks)) != len(self.blocks) or any(b < 0 for b in self.blocks):
            raise ValueError("timing blocks must be unique nonnegative integers")
        return self


class LearningObjective(Record):
    recall_tolerance: float = Field(default=0.005, ge=0, lt=1)
    minimum_native_recall: Recall = 0.95
    minimum_groups: int = Field(default=30, ge=2)
    bootstrap_samples: int = Field(default=10000, ge=100, le=100000)
    seed: int = Field(default=20261019, ge=0)
    maximum_decision_depth: int = Field(default=4, ge=1, le=8)


class FeedbackCorpus(Record):
    schema_version: Literal[1] = 1
    format: Literal["fannagent.learning.feedback.v1"] = "fannagent.learning.feedback.v1"
    scope: Literal["learning"] = "learning"
    profile: RuntimeProfile
    qualified_features: list[Name] = Field(min_length=1)
    collection_groups: list[Name] = Field(min_length=1)
    work_feature: Name
    source_hashes: dict[Name, Hash] = Field(min_length=1)
    inventory: list[TrainingEntitlement] = Field(min_length=1)
    queries: list[TrainingQuery] = Field(min_length=1)
    objective: LearningObjective = Field(default_factory=LearningObjective)
    timing_schedule: TimingSchedule | None = None
    timings: list[TimingPair] = Field(default_factory=list)

    @property
    def evidence_hash(self) -> str:
        return digest(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def verify(self):
        names = set(self.qualified_features)
        definitions = self.profile.runtime_features
        if len(names) != len(self.qualified_features) or names.difference(definitions):
            raise ValueError("qualified features must be unique declared runtime features")
        groups = set(self.collection_groups)
        if len(groups) != len(self.collection_groups) or groups.difference(
            self.profile.available_collection_groups
        ):
            raise ValueError("invalid collection groups")
        if any(definitions[n].group not in groups for n in names):
            raise ValueError("qualified feature is outside the collection groups")
        if self.work_feature not in names or definitions[self.work_feature].kind != "int":
            raise ValueError("work feature must be a qualified integer counter")
        inventory = {r.query_id: (r.group, r.stratum) for r in self.inventory}
        if len(inventory) != len(self.inventory):
            raise ValueError("duplicate query in training entitlement")
        query_ids = [q.query_id for q in self.queries]
        if len(set(query_ids)) != len(query_ids) or set(query_ids) != set(inventory):
            raise ValueError("query coverage differs from the training entitlement")
        for query in self.queries:
            if query.trajectory_complete is not True:
                raise ValueError("trajectory must be complete before replay")
            if (query.group, query.stratum) != inventory[query.query_id]:
                raise ValueError("query group or stratum differs from training entitlement")
            checkpoints = query.checkpoints
            if [c.checkpoint_index for c in checkpoints] != list(range(1, len(checkpoints) + 1)):
                raise ValueError("complete trajectory requires consecutive checkpoint ordinals")
            last_work = 0
            for checkpoint in checkpoints:
                if set(checkpoint.features) != names:
                    raise ValueError("checkpoint contains missing or unqualified feature columns")
                for name, value in checkpoint.features.items():
                    kind = definitions[name].kind
                    if value is None:
                        continue
                    FeatureValue(available=True, value=value)
                    if kind == "int" and (type(value) is not int or value < 0):
                        raise ValueError("integer counters must be nonnegative integers")
                    if kind == "bool" and type(value) is not bool:
                        raise ValueError("Boolean feature has the wrong kind")
                    if kind == "float" and (
                        type(value) not in (int, float) or not math.isfinite(value)
                    ):
                        raise ValueError("floating feature must be finite and numeric")
                work = checkpoint.features[self.work_feature]
                if type(work) is not int or not last_work <= work <= query.native_work:
                    raise ValueError("checkpoint work is missing, decreasing or beyond native work")
                last_work = work
            ordinals = [label.checkpoint_index for label in query.outcomes]
            if len(set(ordinals)) != len(ordinals):
                raise ValueError("duplicate measured stopping outcome")
            for label in query.outcomes:
                if label.checkpoint_index > len(checkpoints):
                    raise ValueError("stopping outcome is outside the verified trajectory")
                if (
                    label.actual_work
                    != checkpoints[label.checkpoint_index - 1].features[self.work_feature]
                ):
                    raise ValueError("stopped work differs from its checkpoint")
                if label.returned_count > query.effective_k:
                    raise ValueError("stopping outcome exceeds effective k")
        if self.timings and self.timing_schedule is None:
            raise ValueError("measured timings require a predeclared schedule")
        seen = set()
        by_query = {q.query_id: q for q in self.queries}
        for pair in self.timings:
            timed_query = by_query.get(pair.query_id)
            if timed_query is None or pair.native_recall != timed_query.native_recall:
                raise ValueError("timing query or native recall differs from training evidence")
            schedule = self.timing_schedule
            assert schedule is not None
            repetitions = (
                schedule.cold_passes if pair.regime == "activation-cold" else (schedule.warm_passes)
            )
            key = (pair.policy_hash, pair.query_id, pair.regime, pair.block, pair.repetition)
            if key in seen or pair.block not in schedule.blocks or pair.repetition >= repetitions:
                raise ValueError("duplicate timing or timing outside declared schedule")
            if pair.returned_count > timed_query.effective_k:
                raise ValueError("timing result exceeds effective k")
            seen.add(key)
        return self


def policy_input(checkpoint: Checkpoint) -> PolicyInput:
    return PolicyInput(
        features={
            name: FeatureValue(available=value is not None, value=value)
            for name, value in checkpoint.features.items()
        }
    )
