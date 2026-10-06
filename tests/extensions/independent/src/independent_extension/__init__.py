from __future__ import annotations

import math
import uuid
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from fannagent.api import (
    Capabilities,
    CheckpointRef,
    DataProfile,
    EvidenceCheckpoint,
    ExactTruth,
    ExecutionEvidence,
    ExtensionManifest,
    FeatureDefinition,
    FeatureValue,
    PolicyInput,
    PreparedEnvironment,
    ProbeRequest,
    ProbeResult,
    RuntimeProfile,
    Snapshot,
    WorkMeasure,
    digest,
    evaluate_policy,
    validate_policy,
)
from fannagent.api.primitives.filters import evaluate_filter


class Options(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = 7
    rows: int = Field(default=500, ge=100, le=10000)


PROFILE = RuntimeProfile(
    name="independent_blocks/v1",
    features={
        name: FeatureDefinition(
            name=name, kind=kind, group="simulation", provenance="simulated", units=unit
        )
        for name, kind, unit in (
            ("other.requested", "int", "neighbors"),
            ("other.ready", "bool", "boolean"),
            ("other.batch", "int", "batches"),
        )
    },
    checkpoint_interval=5,
    checkpoint_semantics="completed simulated batches",
    stopping_scope="query",
    work_unit="vector_blocks",
    guidance="Synthetic latency and five-block checkpoints. Stop when other.ready is true.",
    scripted_policy={
        "name": "ready",
        "root": {"if": {"feature": "other.ready"}, "then": "stop", "else": "continue"},
    },
)
DATA_PROFILE = DataProfile(
    name="independent_string_cosine/v1", max_dimension=8, identifier_representation="string"
)


class FakeBackend:
    """Deterministic simulation with its own feature and checkpoint semantics."""

    runtime_profile = PROFILE
    data_profile = DATA_PROFILE
    name = "independent"

    def __init__(self, options, context):
        self.options, self.context = options, context
        rng = np.random.default_rng(options.seed)
        vectors = rng.normal(size=(options.rows, 8))
        vectors /= np.linalg.norm(vectors, axis=1)[:, None]
        self._snapshot = Snapshot(
            [
                {
                    "source_id": "item:" + str(i - options.rows // 2),
                    "vector": v.tolist(),
                    "metadata": {"category": str(i % 5), "rating": i},
                }
                for i, v in enumerate(vectors)
            ],
            [{"name": "category", "type": "string"}, {"name": "rating", "type": "integer"}],
            self.data_profile,
        )

    def validate_policy(self, raw):
        return validate_policy(raw, self.runtime_profile)

    def inspect_target(self):
        return {
            "backend": self.name,
            "compatible": True,
            "simulated": True,
            "settings": {},
            **self._snapshot.description(),
        }

    def describe_capabilities(self):
        return Capabilities(
            self.name,
            True,
            True,
            ("simulated",),
            tuple(self.runtime_profile.runtime_features),
            ("simulation",),
            ("latency is simulated",),
            exact=True,
            snapshot=True,
            serving=True,
        )

    def prepare_copy(self):
        self.context.state.set("prepared", True)
        return PreparedEnvironment(
            self.name, True, self.compatibility(), details={"simulated": True}
        )

    def cleanup(self):
        self.context.state.set("cleaned", True)
        return {"removed": [], "artifacts_retained": str(self.context.private_directory)}

    def snapshot(self):
        return self._snapshot

    def compatibility(self):
        return {
            "backend": self.name,
            "index_identity": "independent-1",
            "dataset_hash": self._snapshot.identity,
            "profile_hash": self.runtime_profile.fingerprint,
            "data_profile": digest(self.data_profile.model_dump(mode="json")),
            "settings": {},
        }

    def _ordered(self, query):
        data = self._snapshot.data
        mask = (
            evaluate_filter(query.get("filter"), data.metadata)
            if query.get("filter")
            else np.ones(len(data.ids), bool)
        )
        distances = 1 - data.vectors.astype(np.float64) @ np.asarray(query["vector"])
        eligible = data.ids[mask]
        order = np.lexsort((eligible, distances[mask]))
        return eligible[order].tolist(), distances[mask][order].tolist()

    def exact_reference(self, query):
        ids, distances = self._ordered(query)
        k = min(query["k"], len(ids))
        boundary = distances[k - 1] if k else None
        strict = frozenset(
            i for i, d in zip(ids, distances) if boundary is not None and d < boundary - 1e-9
        )
        ties = frozenset(
            i for i, d in zip(ids, distances) if boundary is not None and abs(d - boundary) <= 1e-9
        )
        return ExactTruth(len(ids), k, strict, ties, frozenset(ids))

    def features(self, query, ordinal, ready):
        return {"other.requested": query["k"], "other.batch": ordinal, "other.ready": ready}

    def execute_probe(self, request: ProbeRequest):
        query = self.snapshot().query(request.query)
        ids, distances = self._ordered(query)
        interval = self.runtime_profile.checkpoint_interval
        difficulty = interval * (1 + int(abs(query["vector"][0]) * 12))
        native_work = difficulty + interval * 4
        checkpoints, stop = [], None
        groups = (
            tuple(request.policy.feature_groups)
            if request.policy
            else tuple(sorted({f.group for f in self.runtime_profile.runtime_features.values()}))
        )
        for ordinal in range(1, math.ceil(native_work / interval)):
            reference = CheckpointRef(
                "simulation", self.runtime_profile.stopping_scope, ordinal, str(ordinal)
            )
            values = self.features(query, ordinal, ordinal * interval >= difficulty)
            checkpoints.append(
                EvidenceCheckpoint(
                    reference,
                    WorkMeasure(ordinal * interval, self.runtime_profile.work_unit),
                    values,
                    provenance="simulated",
                )
            )
            if request.intervention and reference == request.intervention.checkpoint:
                stop = ordinal * interval
                break
            if request.policy:
                inputs = PolicyInput(
                    features={n: FeatureValue(available=True, value=v) for n, v in values.items()}
                )
                if evaluate_policy(request.policy, inputs, self.runtime_profile).value == "stop":
                    stop = ordinal * interval
                    break
        work = stop or native_work
        count = min(query["k"], len(ids)) if work >= difficulty else 0
        metadata = {
            "route": "simulation",
            "policy_opportunity": True,
            "stop_reason": "policy_stop" if stop else "native_convergence",
            "work": work,
            "work_unit": self.runtime_profile.work_unit,
            "simulated": True,
        }
        nonce = uuid.uuid4().hex
        evidence = ExecutionEvidence(
            nonce,
            digest(query),
            self.runtime_profile.fingerprint,
            self.runtime_profile.stopping_scope,
            tuple(checkpoints),
            metadata,
            collection_groups=groups,
        )
        return ProbeResult(
            ids[:count],
            distances[:count],
            work * 0.08 + (0.1 if request.mode == "policy" else 0),
            metadata,
            asdict(evidence),
            nonce,
        )

    def collect_evidence(self, result):
        raw = result.evidence
        checkpoints = tuple(
            EvidenceCheckpoint(
                CheckpointRef(**c["reference"]),
                WorkMeasure(**c["work"]),
                c["features"],
                c["availability"],
                c["provenance"],
            )
            for c in raw["checkpoints"]
        )
        return ExecutionEvidence(**{**raw, "checkpoints": checkpoints})

    def install_policy(self, policy):
        self.validate_policy(policy)
        return {"policy_hash": policy.policy_hash, "simulated": True}

    def open_policy_session(self, policy):
        backend = self
        self.install_policy(policy)

        class Session:
            def query(self, query, *, fallback=True):
                result = backend.execute_probe(ProbeRequest(query, mode="policy", policy=policy))
                result.ids = [backend.snapshot().source_ids[i] for i in result.ids]
                result.metadata["identifier_space"] = "source"
                return result

            def close(self):
                backend.close()

        return Session()

    def close(self):
        pass


class FakeExtension:
    def manifest(self):
        return ExtensionManifest(
            "independent",
            "fannagent-test-extension",
            version("fannagent-test-extension"),
            (1,),
            Options.model_json_schema(),
            DATA_PROFILE,
            PROFILE,
            ("simulation only",),
        )

    def normalize_options(self, options: dict, origin: Path):
        return Options.model_validate(options)

    def create(self, options, context):
        return FakeBackend(options, context)


extension = FakeExtension()
