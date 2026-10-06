"""Exact, cached development descriptors for filtered ANN queries.

These labels are computed outside timed database execution and must not be
inserted into a runtime policy input by the evaluation interface.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from .data import LoadedDataset, Query
from .filters import evaluate_filter
from .hashing import sha256_file, stable_hash

DESCRIPTOR_VERSION = "filtered_ann_descriptors_v1"


def descriptor_version(dataset: LoadedDataset) -> str:
    return (
        "filtered_ann_descriptors_v2"
        if dataset.manifest.schema_version == 2
        else DESCRIPTOR_VERSION
    )


LID_NEIGHBORS = 20
LID_SAMPLES = 1024
MAHALANOBIS_SAMPLES = 5000


def predicate_structure(expr: dict[str, Any] | None) -> dict[str, Any]:
    counts = {
        key: 0
        for key in (
            "eq",
            "in",
            "lt",
            "lte",
            "gt",
            "gte",
            "is_null",
            "is_not_null",
            "and",
            "or",
            "not",
        )
    }
    fields: set[str] = set()

    def visit(node: dict[str, Any] | None) -> None:
        if node is None:
            return
        for op in ("and", "or"):
            if op in node:
                counts[op] += 1
                for child in node[op]:
                    visit(child)
                return
        if "not" in node:
            counts["not"] += 1
            visit(node["not"])
            return
        counts[node["op"]] += 1
        fields.add(node["field"])

    visit(expr)
    if not counts["is_null"] and not counts["is_not_null"]:
        del counts["is_null"], counts["is_not_null"]
    return {"operator_counts": counts, "field_count": len(fields), "fields": sorted(fields)}


def exact_query_descriptors(
    dataset: LoadedDataset,
    query: Query,
    *,
    seed: int = 0,
    dataset_lid: dict[str, Any] | None = None,
    checkpoint: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Compute deterministic exact descriptors without changing the database."""
    started = time.perf_counter_ns()
    n = len(dataset.ids)
    mask = (
        np.asarray(evaluate_filter(query.filter, dataset.metadata), dtype=bool)
        if query.filter is not None
        else np.ones(n, dtype=bool)
    )
    if mask.shape != (n,):
        raise ValueError("filter mask length differs from dataset row count")
    eligible_count = int(np.count_nonzero(mask))
    global_fraction = eligible_count / n
    query_vector = np.asarray(query.vector, dtype=np.float32).astype(np.float64)
    distances = np.empty(n, dtype=np.float64)
    for start in range(0, n, 32768):
        if checkpoint:
            checkpoint()
        end = min(n, start + 32768)
        distances[start:end] = 1.0 - dataset.vectors[start:end].astype(np.float64) @ query_vector
    order = np.lexsort((dataset.ids, distances))
    ordered_matches = mask[order]
    neighborhood_sizes = sorted({query.k, 64, 256})
    neighborhoods: dict[str, Any] = {}
    for requested in neighborhood_sizes:
        actual = min(requested, n)
        local_fraction = (
            float(np.count_nonzero(ordered_matches[:actual]) / actual) if actual else None
        )
        denominator = local_fraction + global_fraction if local_fraction is not None else 0.0
        neighborhoods[str(requested)] = {
            "requested": requested,
            "actual": actual,
            "local_match_fraction": local_fraction,
            "gls": (
                (local_fraction - global_fraction) / denominator
                if denominator > 0 and local_fraction is not None
                else None
            ),
            "unavailable_reason": "zero_denominator" if denominator == 0 else None,
        }

    alpha_k = None
    filtered_k_distance = None
    unfiltered_k_distance = None
    alpha_hat = None
    alpha_hat_reason = None
    if eligible_count >= query.k and n >= query.k:
        matching_ranks = np.flatnonzero(ordered_matches)
        alpha_k = int(matching_ranks[query.k - 1] + 1)
        filtered_k_distance = float(distances[order[alpha_k - 1]])
        unfiltered_k_distance = float(distances[order[query.k - 1]])
        if unfiltered_k_distance > 0 and filtered_k_distance >= 0:
            alpha_hat = (
                (n / eligible_count) * (filtered_k_distance / unfiltered_k_distance) * query.k
            )
        else:
            alpha_hat_reason = "zero_or_negative_distance_denominator"
    else:
        alpha_hat_reason = "insufficient_results"

    mahalanobis = filtered_mahalanobis(dataset, query, mask, seed=seed)
    value = {
        "descriptor_version": descriptor_version(dataset),
        "dataset_hash": dataset.dataset_hash,
        "query_id": query.id,
        "query_hash": stable_hash(query.model_dump(mode="json")),
        "metric": "cosine",
        "seed": seed,
        "row_count": n,
        "eligible_count": eligible_count,
        "global_match_fraction": global_fraction,
        "global_rejection_fraction": 1.0 - global_fraction,
        "predicate_structure": predicate_structure(query.filter),
        "neighborhoods": neighborhoods,
        "alpha_k": alpha_k,
        "alpha_k_unavailable_reason": ("insufficient_results" if alpha_k is None else None),
        "filtered_k_distance": filtered_k_distance,
        "unfiltered_k_distance": unfiltered_k_distance,
        "alpha_hat": alpha_hat,
        "alpha_hat_unavailable_reason": alpha_hat_reason,
        "mahalanobis": mahalanobis,
        "dataset_lid": dataset_lid,
        "computation_seconds": (time.perf_counter_ns() - started) / 1e9,
    }
    return value


def filtered_mahalanobis(
    dataset: LoadedDataset,
    query: Query,
    eligible_mask: np.ndarray,
    *,
    seed: int = 0,
) -> dict[str, Any]:
    eligible_positions = np.flatnonzero(eligible_mask)
    sample_size = min(MAHALANOBIS_SAMPLES, len(eligible_positions))
    if sample_size < 2:
        return {
            "distance": None,
            "sample_size": sample_size,
            "rank": 0,
            "unavailable_reason": "insufficient_results",
        }
    predicate_seed = int(stable_hash({"predicate": query.filter, "seed": seed})[:16], 16)
    selected = np.random.default_rng(predicate_seed).choice(
        eligible_positions, sample_size, replace=False
    )
    vectors = dataset.vectors[selected].astype(np.float64)
    mean = np.mean(vectors, axis=0)
    centered = vectors - mean
    covariance = centered.T @ centered / (sample_size - 1)
    rank = int(np.linalg.matrix_rank(covariance))
    inverse = np.linalg.pinv(covariance, hermitian=True)
    delta = np.asarray(query.vector, dtype=np.float32).astype(np.float64) - mean
    squared = float(delta @ inverse @ delta)
    return {
        "distance": math.sqrt(max(0.0, squared)),
        "sample_size": sample_size,
        "rank": rank,
        "unavailable_reason": None,
    }


def sampled_dataset_lid(
    dataset: LoadedDataset,
    *,
    seed: int = 0,
    checkpoint: Callable[[], None] | None = None,
    progress: Callable[[str, int, int], None] | None = None,
) -> dict[str, Any]:
    """Exact 20-neighbor LID on a deterministic sample of dataset points."""
    n = len(dataset.ids)
    sample_size = min(LID_SAMPLES, n)
    result: dict[str, Any] = {
        "mean": None,
        "sample_size": sample_size,
        "valid_samples": 0,
        "degenerate_samples": sample_size,
        "neighbor_count": LID_NEIGHBORS,
        "distance_kind": "euclidean_chord_from_normalized_cosine",
    }
    if n <= LID_NEIGHBORS:
        result["unavailable_reason"] = "insufficient_results"
        return result
    try:
        import faiss
    except ImportError as exc:
        raise RuntimeError("exact sampled LID requires the locked faiss-cpu dependency") from exc
    index = faiss.IndexFlatIP(dataset.manifest.dimension)
    vectors = np.ascontiguousarray(dataset.vectors, dtype=np.float32)
    index.add(vectors)
    samples = np.random.default_rng(seed).choice(n, sample_size, replace=False)
    score_blocks, position_blocks = [], []
    for start in range(0, sample_size, 32):
        if checkpoint:
            checkpoint()
        scores, positions = index.search(vectors[samples[start : start + 32]], LID_NEIGHBORS + 1)
        score_blocks.append(scores)
        position_blocks.append(positions)
        if progress:
            progress("dataset_lid", min(start + 32, sample_size), sample_size)
    valid: list[float] = []
    for source, row_scores, row_positions in zip(
        samples, np.concatenate(score_blocks), np.concatenate(position_blocks), strict=True
    ):
        neighbors = [
            math.sqrt(max(0.0, 2.0 * (1.0 - float(score))))
            for score, position in zip(row_scores, row_positions, strict=True)
            if int(position) != int(source)
        ][:LID_NEIGHBORS]
        if len(neighbors) < LID_NEIGHBORS or neighbors[0] <= 0 or neighbors[-1] <= 0:
            continue
        radius = neighbors[-1]
        mean_log_ratio = sum(math.log(value / radius) for value in neighbors) / len(neighbors)
        if mean_log_ratio < 0:
            valid.append(-1.0 / mean_log_ratio)
    if valid:
        result["mean"] = float(np.mean(valid))
        result["valid_samples"] = len(valid)
        result["degenerate_samples"] = sample_size - len(valid)
        result["unavailable_reason"] = None
    else:
        result["unavailable_reason"] = "zero_or_duplicate_neighbor_distances"
    return result


def _cached_value(
    path: Path, dataset: LoadedDataset, query: Query | None = None
) -> dict[str, Any] | None:
    try:
        if not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
            return None
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            return None
        if query is None:
            return (
                value
                if {"mean", "sample_size", "valid_samples", "neighbor_count"} <= value.keys()
                else None
            )
        if (
            value.get("dataset_hash") != dataset.dataset_hash
            or value.get("query_hash") != stable_hash(query.model_dump(mode="json"))
            or value.get("descriptor_version") != descriptor_version(dataset)
        ):
            return None
        return value
    except (OSError, ValueError):
        return None


def descriptor_cache_snapshot(directory: Path) -> dict[str, str]:
    """Detect cache changes between review and execution without creating cache files."""
    return {p.name: sha256_file(p) for p in sorted(directory.glob("*.json")) if p.is_file()}


def cached_descriptors(
    dataset: LoadedDataset,
    queries: list[Query],
    cache_dir: Path,
    *,
    seed: int = 0,
    checkpoint: Callable[[], None] | None = None,
    progress: Callable[[str, int, int], None] | None = None,
) -> dict[str, dict[str, Any]]:
    """Cache exact descriptors by immutable inputs and record cache exposure."""
    directory = cache_dir.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    lid_key = stable_hash(
        {
            "version": descriptor_version(dataset),
            "dataset": dataset.dataset_hash,
            "seed": seed,
            "kind": "lid",
        }
    )
    lid_path = directory / f"{lid_key}.json"
    dataset_lid = _cached_value(lid_path, dataset)
    if dataset_lid is None:
        dataset_lid = sampled_dataset_lid(
            dataset, seed=seed, checkpoint=checkpoint, progress=progress
        )
        _write_json_atomic(lid_path, dataset_lid)
    output: dict[str, dict[str, Any]] = {}
    for number, query in enumerate(queries, start=1):
        if checkpoint:
            checkpoint()
        key = stable_hash(
            {
                "version": descriptor_version(dataset),
                "dataset": dataset.dataset_hash,
                "query": query.model_dump(mode="json"),
                "metric": dataset.manifest.metric,
                "seed": seed,
            }
        )
        path = directory / f"{key}.json"
        value = _cached_value(path, dataset, query)
        hit = value is not None
        if not hit:
            value = exact_query_descriptors(
                dataset, query, seed=seed, dataset_lid=dataset_lid, checkpoint=checkpoint
            )
            _write_json_atomic(path, value)
        assert value is not None
        output[query.id] = {
            **value,
            "cache_hit": hit,
            "cache_key": key,
            "storage_bytes": path.stat().st_size,
        }
        if progress:
            progress("descriptors", number, len(queries))
    return output


def estimated_descriptor_distance_work(
    dataset: LoadedDataset, queries: list[Query], cache_dir: Path, *, seed: int = 0
) -> int:
    """Reserve exact vector comparisons before launching a descriptor job."""
    directory = cache_dir.expanduser().resolve()
    count = len(dataset.ids)
    lid_key = stable_hash(
        {
            "version": descriptor_version(dataset),
            "dataset": dataset.dataset_hash,
            "seed": seed,
            "kind": "lid",
        }
    )
    work = (
        count * min(LID_SAMPLES, count)
        if count > LID_NEIGHBORS and _cached_value(directory / f"{lid_key}.json", dataset) is None
        else 0
    )
    for query in queries:
        key = stable_hash(
            {
                "version": descriptor_version(dataset),
                "dataset": dataset.dataset_hash,
                "query": query.model_dump(mode="json"),
                "metric": dataset.manifest.metric,
                "seed": seed,
            }
        )
        if _cached_value(directory / f"{key}.json", dataset, query) is None:
            work += count
    return work


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    temporary.replace(path)
