"""Read the pinned Torch training package without importing or executing its scripts."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath

from ..api import AgentError, RuntimeProfile, validate_policy
from ..store import digest
from .files import decode, read_bytes
from .models import (
    Checkpoint,
    FeedbackCorpus,
    LearningObjective,
    StopOutcome,
    TrainingEntitlement,
    TrainingQuery,
)


def _import_torch_training(package: Path, profile: RuntimeProfile) -> FeedbackCorpus:
    """Import only the learning inventory already sealed in the feedback package.

    Native prefix verification is source attestation, retained with its original hash.
    This adapter verifies artifact identity and membership, not a new native execution.
    """
    package = package.resolve()

    def load_file(name):
        parts = PurePosixPath(name)
        if parts.is_absolute() or ".." in parts.parts or str(parts) != name:
            raise AgentError("unsafe training manifest path")
        target = package
        for part in parts.parts:
            target = target / part
            if target.is_symlink():
                raise AgentError("training package cannot contain symbolic links")
        if not target.resolve().is_relative_to(package):
            raise AgentError("training input escapes the package")
        return read_bytes(target)

    manifest_bytes = load_file("manifest.json")
    manifest = decode(manifest_bytes)
    hashes = {"manifest.json": hashlib.sha256(manifest_bytes).hexdigest()}
    content = {}
    entries = manifest.get("files", {})
    if not isinstance(entries, dict) or not 1 <= len(entries) <= 256:
        raise AgentError("invalid or oversized training package manifest")
    total = 0
    for name, expected in entries.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise AgentError("invalid training source digest")
        value = load_file(name)
        total += len(value)
        if total > 256 * 2**20:
            raise AgentError("training package exceeds import size bound")
        if hashlib.sha256(value).hexdigest() != expected:
            raise AgentError("training package hash differs: " + name)
        hashes[name] = expected
        content[name] = value

    def read(name):
        if name not in content:
            raise AgentError("required training input is not pinned: " + name)
        return decode(content[name])

    config = read("experiment.json")
    receipt = read("inputs/original-learning-receipt.json")
    provenance = read("inputs/split-provenance.json")
    candidates = read("inputs/candidates.json")
    if (
        config.get("name") != "torch-reviews-policy-feedback"
        or config.get("ef_search_levels") != [640]
        or config.get("tiers") != ["light"]
        or config.get("confirmation_queries_allowed") != 0
        or config.get("maximum_model_calls_on_Torch") != 0
        or receipt.get("status") != "complete"
        or receipt.get("confirmation_outcomes_exported") is not False
        or receipt.get("canonical_test_consumed") is not False
        or provenance.get("training_confirmation_disjoint") is not True
        or provenance.get("confirmation_vectors_in_package") is not False
        or provenance.get("confirmation_outcomes_in_package") is not False
        or provenance.get("base_manifest_sha256") != receipt.get("package_manifest_sha256")
    ):
        raise AgentError("package does not describe the supported training-only study")
    names = receipt["qualified_features"]["640/light"]
    if candidates["feature_pool"] != names or (
        candidates["training_view_sha256"] != hashes["inputs/training-640-light.jsonl"]
    ):
        raise AgentError("qualified features or candidate training identity differ")
    policies = candidates.get("candidates", [])
    if not 1 <= len(policies) <= 6:
        raise AgentError("invalid source candidate inventory")
    collection_groups = policies[0]["policy"]["feature_groups"]
    for item in policies:
        policy = validate_policy(item["policy"], profile)
        if policy.policy_hash != item["policy_hash"] or (
            policy.feature_groups != collection_groups
        ):
            raise AgentError("source candidate does not bind the supplied runtime profile")
    inventory = []
    k_by_query = {}
    for line in content["inputs/queries.jsonl"].splitlines():
        raw = decode(line)
        query = raw["query"]
        if raw.get("split") != "learning":
            raise AgentError("confirmation or non-learning query in training inventory")
        stratum = query["id"].rsplit("-", 1)[-1]
        if stratum not in config["filters"]:
            raise AgentError("unexpected training filter stratum")
        inventory.append(
            TrainingEntitlement(query_id=query["id"], group=raw["group"], stratum=stratum)
        )
        k_by_query[query["id"]] = query["k"]
    if (
        digest(sorted(q.query_id for q in inventory)) != provenance["training_query_ids_sha256"]
        or len({q.group for q in inventory}) != config["learning_groups"]
        or len(inventory) != config["learning_groups"] * len(config["filters"])
    ):
        raise AgentError("training entitlement coverage differs")
    by_query = {q.query_id: q for q in inventory}
    for group in {q.group for q in inventory}:
        if sorted(q.stratum for q in inventory if q.group == group) != sorted(config["filters"]):
            raise AgentError("training group is missing or duplicates a filter variant")
    rows = []
    allowed = {
        "checkpoint_count",
        "ef_search",
        "group",
        "labels",
        "native_recall",
        "native_work",
        "oracle_checkpoint",
        "oracle_definition",
        "query_id",
        "states",
    }
    for line in content["inputs/training-640-light.jsonl"].splitlines():
        raw = decode(line)
        entitlement = by_query.get(raw.get("query_id"))
        if (
            set(raw).difference(allowed)
            or entitlement is None
            or raw["group"] != entitlement.group
            or raw["ef_search"] != 640
            or raw["checkpoint_count"] != len(raw["states"])
        ):
            raise AgentError("training record is outside the pinned entitlement or trajectory")
        outcomes = []
        for label in raw["labels"]:
            preserves = bool(
                label["valid"]
                and label["returned_count"] == k_by_query[raw["query_id"]]
                and label["recall"] >= raw["native_recall"]
            )
            if label["preserves_default"] != preserves:
                raise AgentError("source proposal label disagrees with measured outcome")
            outcomes.append(
                StopOutcome(
                    checkpoint_index=label["checkpoint_index"],
                    recall=label["recall"],
                    returned_count=label["returned_count"],
                    valid=label["valid"],
                    actual_work=label["actual_work"],
                    prefix_matches=label["prefix_matches"],
                    source_prefix_sha256=label["reference_prefix_sha256"],
                    source_ref=f"inputs/training-640-light.jsonl:{raw['query_id']}",
                )
            )
        rows.append(
            TrainingQuery(
                **entitlement.model_dump(),
                effective_k=k_by_query[entitlement.query_id],
                native_recall=raw["native_recall"],
                native_work=raw["native_work"],
                checkpoints=[Checkpoint.model_validate(s) for s in raw["states"]],
                outcomes=outcomes,
            )
        )
    return FeedbackCorpus(
        profile=profile,
        qualified_features=names,
        collection_groups=collection_groups,
        work_feature="layer0_distance_evaluations",
        source_hashes=hashes,
        inventory=inventory,
        queries=rows,
        objective=LearningObjective(
            recall_tolerance=config["recall_tolerance"],
            minimum_native_recall=config["minimum_native_recall"],
            bootstrap_samples=config["bootstrap_samples"],
            seed=config["seed"],
        ),
    )


def import_torch_training(package: Path, profile: RuntimeProfile) -> FeedbackCorpus:
    try:
        return _import_torch_training(package, profile)
    except (KeyError, TypeError, AttributeError, IndexError, ValueError) as exc:
        raise AgentError(f"invalid Torch training package: {exc}") from None
