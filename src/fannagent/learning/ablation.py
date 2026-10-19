"""Prepare a separate, unqualified predicate-context study. No native feature claims."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..api import AgentError, FeatureDefinition, RuntimeProfile
from ..store import digest
from .files import decode, write_new
from .returned import read_under, require
from .returned_models import ReturnedFeedback

FEATURE = "query_predicate_threshold"


def predicate_context(query: dict) -> int:
    """Read the actual portable predicate, never infer context from an ID or stratum."""
    predicate = query.get("filter")
    if predicate is None:
        return 0  # Existing predicate_leaf_count=0 distinguishes the unfiltered case.
    if (
        not isinstance(predicate, dict)
        or set(predicate) != {"field", "op", "value"}
        or predicate["field"] != "m_000000"
        or predicate["op"] != "gte"
        or type(predicate["value"]) is not int
        or not 0 <= predicate["value"] < 2**63
    ):
        raise AgentError("context-v1 supports only a nonnegative integer m_000000 >= threshold")
    return predicate["value"]


def prepare_ablation(evidence: ReturnedFeedback, package: Path, output: Path):
    if not isinstance(evidence, ReturnedFeedback):
        raise AgentError("ablation preparation requires verified returned training evidence")
    require(not output.exists(), "preserve existing ablation study")
    corpus = evidence.corpus
    content = read_under(package.resolve(), "inputs/queries.jsonl")
    require(
        hashlib.sha256(content).hexdigest() == corpus.source_hashes["inputs/queries.jsonl"],
        "ablation queries differ from the original training entitlement",
    )
    source = [decode(line) for line in content.splitlines()]
    queries = {q.query_id: q for q in corpus.queries}
    require(
        len(source) == len(queries)
        and {r["query"]["id"] for r in source} == set(queries)
        and all(r["split"] == "learning" for r in source),
        "ablation may contain only the same learning queries",
    )
    context = []
    for row in source:
        query = row["query"]
        threshold = predicate_context(query)
        expected_leaves = 0 if query["filter"] is None else 1
        require(
            all(
                c.features["predicate_leaf_count"] == expected_leaves
                for c in queries[query["id"]].checkpoints
            ),
            "predicate context disagrees with native predicate structure",
        )
        context.append({"query_id": query["id"], "features": {FEATURE: threshold}})
    raw_profile = corpus.profile.model_dump(mode="python")
    raw_profile["name"] += "/predicate-context-v1"
    raw_profile["native_registry_hash"] = None
    raw_profile["native_protocol"] = "pending_native_qualification"
    raw_profile["collection_groups"] = (*raw_profile["collection_groups"], "query_context")
    raw_profile["features"][FEATURE] = FeatureDefinition(
        name=FEATURE,
        kind="int",
        group="query_context",
        units="predicate_scalar",
        availability="pre_execution_query_constant",
        provenance="validated_query_predicate",
        collection_cost="must_be_measured_in_separate_ablation",
        source="query_context_v1",
        description="Actual m_000000 >= integer threshold; unfiltered uses 0 and leaf_count=0",
    ).model_dump()
    planned_profile = RuntimeProfile.model_validate(raw_profile)
    group_ids = sorted({q.group for q in corpus.queries}, key=lambda g: digest([20261019, g]))
    folds = {g: i % 5 for i, g in enumerate(group_ids)}
    manifest = {
        "schema_version": 1,
        "format": "fannagent.learning.predicate-ablation.v1",
        "study_version": "predicate-context-v1",
        "scope": "learning",
        "status": "prepared_awaiting_native_qualification",
        "evidence_hash": evidence.evidence_hash,
        "base_runtime_profile_hash": corpus.profile.fingerprint,
        "planned_context_profile_hash": planned_profile.fingerprint,
        "arms": {
            "baseline": {
                "qualified_features": corpus.qualified_features,
                "runtime_profile_hash": corpus.profile.fingerprint,
            },
            "predicate_context": {
                "proposed_features": [*corpus.qualified_features, FEATURE],
                "native_qualified": False,
                "runtime_profile_hash": planned_profile.fingerprint,
            },
        },
        "shared_objective": corpus.objective.model_dump(mode="json"),
        "shared_group_folds": folds,
        "context_hash": digest(context),
        "source_query_sha256": corpus.source_hashes["inputs/queries.jsonl"],
        "shared_fitting_grid": {
            "depth": [2, 3],
            "risk_weight": [20.0, 80.0],
            "minimum_leaf_groups": 8,
            "folds": 5,
            "seed": 20261019,
        },
        "shared_baselines": ["native", "fixed_work", "measured_cart", "direct_agent_synthesis"],
        "budget_receipt": evidence.import_receipt["budget_receipt"],
        "budget_reset": False,
        "provider_calls_in_preparation": 0,
        "maximum_new_training_candidates": 4,
        "maximum_provider_calls_before_explicit_round": 0,
        "measurement_contract": {
            "timing_boundary": evidence.benchmark.timing_boundary,
            "blocks": len(evidence.benchmark.schedule.blocks),
            "cold_passes": evidence.benchmark.schedule.cold_passes,
            "warmups": evidence.benchmark.warmups,
            "warm_passes": evidence.benchmark.schedule.warm_passes,
            "native_and_matched_continue_required": True,
            "context_feature_cost_must_be_measured": True,
            "confirmation_queries": 0,
            "canonical_acceptance_established": False,
        },
        "qualification_required": [
            "Implement and qualify the native getter against the actual query predicate",
            "Verify true/false numeric branches and unfiltered sentinel behavior",
            "Verify context invariance and original causal prefixes for both study arms",
            "Measure native equivalence and collection overhead under both profiles",
            "Refit all competing learners with identical group folds and evidence",
            "Acquire actual outcomes at new first stops; never interpolate recall",
            "Freeze evidence, profile, scorer, candidate and schedule before confirmation",
        ],
        "context_is_qualified_runtime_evidence": False,
        "existing_timings_apply_to_context_arm": False,
        "canonical_acceptance_established": False,
    }
    output.mkdir(mode=0o700, parents=False)
    write_new(output / "query-context.json", context)
    write_new(output / "planned-runtime-profile.json", planned_profile.model_dump(mode="json"))
    write_new(output / "study.json", manifest)  # Publish the manifest after its inputs.
    return {
        "output": str(output),
        "study_hash": digest(manifest),
        "status": manifest["status"],
        "native_qualified": False,
    }
