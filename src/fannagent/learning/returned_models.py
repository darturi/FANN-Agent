"""A new evidence envelope; the Stage 1 corpus and its hashes stay unchanged."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from ..api import validate_policy
from ..store import digest
from .models import FeedbackCorpus, Hash, Name, Record, TimingPair, TimingSchedule


class BenchmarkPair(TimingPair):
    arm: Name
    native_outer_ms: float = Field(gt=0, le=1e9)
    policy_outer_ms: float = Field(gt=0, le=1e9)
    policy_already_activated: bool
    stopped_checkpoint: int | None = Field(default=None, gt=0)
    work: dict[str, Annotated[int, Field(ge=0)]]


class BenchmarkArm(Record):
    arm: Name
    kind: Literal["candidate", "matched-continue", "continue", "fixed", "oracle"]
    policy: dict | None = None
    matched_candidate: Name | None = None
    per_query_policy_hashes: dict[Name, Hash] = Field(default_factory=dict)


class BenchmarkEvidence(Record):
    schedule: TimingSchedule
    warmups: int = Field(ge=0, le=1000)
    timing_boundary: Name
    allocation_ids: dict[Name, Name]
    arms: list[BenchmarkArm] = Field(min_length=1, max_length=64)
    pairs: list[BenchmarkPair] = Field(min_length=1)


class ReturnedFeedback(Record):
    schema_version: Literal[1] = 1
    format: Literal["fannagent.learning.returned-feedback.v1"] = (
        "fannagent.learning.returned-feedback.v1"
    )
    scope: Literal["learning"] = "learning"
    corpus: FeedbackCorpus
    benchmark: BenchmarkEvidence
    import_receipt: dict

    @property
    def evidence_hash(self):
        return digest(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def verify(self):
        if self.corpus.timings or self.corpus.timing_schedule is not None:
            raise ValueError("returned timings belong only in the benchmark envelope")
        benchmark = self.benchmark
        arms = {a.arm: a for a in benchmark.arms}
        if len(arms) != len(benchmark.arms):
            raise ValueError("duplicate benchmark arm")
        schedule = benchmark.schedule
        if set(benchmark.allocation_ids) != {str(b) for b in schedule.blocks}:
            raise ValueError("allocation inventory differs from the schedule")
        queries = {q.query_id: q for q in self.corpus.queries}
        hashes = {}
        for arm in arms.values():
            if arm.kind == "oracle":
                if arm.policy is not None or set(arm.per_query_policy_hashes) != set(queries):
                    raise ValueError("oracle requires per-query identities and no global policy")
            else:
                if arm.policy is None or arm.per_query_policy_hashes:
                    raise ValueError("ordinary arm requires one policy")
                hashes[arm.arm] = validate_policy(arm.policy, self.corpus.profile).policy_hash
            if arm.kind == "matched-continue":
                if arm.matched_candidate is None:
                    raise ValueError("matched continue has no candidate")
                parent = arms.get(arm.matched_candidate)
                if parent is None or parent.kind != "candidate":
                    raise ValueError("matched continue has no candidate")
            elif arm.matched_candidate is not None:
                raise ValueError("only matched continue arms may name a candidate")
        seen = set()
        for pair in benchmark.pairs:
            measured_arm, query = arms.get(pair.arm), queries.get(pair.query_id)
            if measured_arm is None or query is None:
                raise ValueError("benchmark arm or query outside learning inventory")
            expected_hash = (
                measured_arm.per_query_policy_hashes[pair.query_id]
                if measured_arm.kind == "oracle"
                else hashes[measured_arm.arm]
            )
            passes = (
                schedule.cold_passes if pair.regime == "activation-cold" else schedule.warm_passes
            )
            key = (pair.arm, pair.query_id, pair.block, pair.regime, pair.repetition)
            if (
                key in seen
                or pair.block not in schedule.blocks
                or pair.repetition >= passes
                or pair.policy_hash != expected_hash
                or pair.policy_already_activated != (pair.regime == "reused-warm")
                or pair.native_recall != query.native_recall
                or pair.returned_count > query.effective_k
                or pair.valid != (pair.returned_count == query.effective_k)
                or "layer0_distance_evaluations" not in pair.work
                or (
                    pair.stopped_checkpoint is not None
                    and pair.stopped_checkpoint > len(query.checkpoints)
                )
            ):
                raise ValueError("benchmark identity, activation, coverage or outcome differs")
            seen.add(key)
        expected = (
            len(arms)
            * len(queries)
            * len(schedule.blocks)
            * (schedule.cold_passes + schedule.warm_passes)
        )
        if len(seen) != expected:
            raise ValueError("incomplete returned benchmark coverage")
        return self


LearningEvidence = FeedbackCorpus | ReturnedFeedback


def parse_evidence(value) -> LearningEvidence:
    if (
        isinstance(value, dict)
        and value.get("format") == ReturnedFeedback.model_fields["format"].default
    ):
        return ReturnedFeedback.model_validate(value)
    return FeedbackCorpus.model_validate(value)
