"""Development-only reconstruction of graph membership from bounded trace events."""

from __future__ import annotations

from collections import Counter
from typing import Any, Protocol

from .data import LoadedDataset, Query
from .errors import ValidationError
from .filters import evaluate_filter


class AuditFeature(Protocol):
    available: bool
    value: int | float | None


class AuditCheckpoint(Protocol):
    sequence: int
    component_id: str
    index: int
    features: dict[str, Any]


class ExecutionTrace(Protocol):
    """Event-bearing trace view accepted by the neutral membership audit."""

    query_id: str
    dataset_hash: str
    events: tuple[dict[str, Any], ...]
    checkpoints: tuple[AuditCheckpoint, ...]
    truncated: bool
    protocol: str
    feature_registry_hash: str
    nonce: str
    index_hash: str
    engine_build_hash: str


def reconstruct_membership(
    dataset: LoadedDataset, query: Query, trace: ExecutionTrace
) -> dict[str, Any]:
    """Evaluate the portable predicate after execution; never populate policy inputs."""
    if trace.query_id != query.id or trace.dataset_hash != dataset.dataset_hash:
        raise ValidationError("audit trace has a different query or dataset")
    row_by_id = {int(identifier): index for index, identifier in enumerate(dataset.ids)}
    mask = (
        [True] * len(dataset.ids)
        if query.filter is None
        else list(evaluate_filter(query.filter, dataset.metadata))
    )
    identities: dict[tuple[str, str], tuple[int, ...]] = {}
    identity_conflicts: set[tuple[str, str]] = set()
    for event in trace.events:
        if event["type"] != "audit_identity":
            continue
        key = _key(event)
        logical = event.get("logical_ids")
        if not isinstance(logical, list) or any(
            isinstance(value, bool) or not isinstance(value, int) for value in logical
        ):
            identity_conflicts.add(key)
            continue
        values = tuple(int(value) for value in logical)
        if key in identities and identities[key] != values:
            identity_conflicts.add(key)
        identities[key] = values

    visited: dict[str, set[str]] = {}
    frontier: dict[str, Counter[str]] = {}
    observed: dict[tuple[str, str], bool] = {}
    tuple_observed: dict[tuple[str, str], dict[str, tuple[int | None, bool]]] = {}
    observation_conflicts: set[tuple[str, str]] = set()
    events = sorted(trace.events, key=lambda event: event["sequence"])
    audit_present = any(event["type"] == "audit_discovery" for event in events)
    next_event = 0
    rows: list[dict[str, Any]] = []
    for checkpoint in trace.checkpoints:
        while next_event < len(events) and events[next_event]["sequence"] < checkpoint.sequence:
            event = events[next_event]
            next_event += 1
            kind = event["type"]
            component = event["component_id"]
            if kind == "audit_discovery":
                visited.setdefault(component, set()).add(_physical(event))
            elif kind == "audit_frontier_reset":
                frontier[component] = Counter()
            elif kind == "audit_frontier_add":
                frontier.setdefault(component, Counter())[_physical(event)] += 1
            elif kind == "audit_frontier_remove":
                identity = _physical(event)
                if frontier.setdefault(component, Counter())[identity] <= 0:
                    observation_conflicts.add((component, identity))
                else:
                    frontier[component][identity] -= 1
            elif kind == "audit_membership":
                key = _key(event)
                value = event.get("matched")
                if not isinstance(value, bool) or (key in observed and observed[key] != value):
                    observation_conflicts.add(key)
                elif isinstance(value, bool):
                    observed[key] = value
            elif kind == "audit_tuple_membership":
                key = _key(event)
                heap_tid = event.get("heap_tid")
                logical_id = event.get("logical_id")
                matched = event.get("matched")
                if (
                    not isinstance(heap_tid, str)
                    or not isinstance(matched, bool)
                    or (
                        logical_id is not None
                        and (isinstance(logical_id, bool) or not isinstance(logical_id, int))
                    )
                ):
                    observation_conflicts.add(key)
                else:
                    prior = tuple_observed.setdefault(key, {}).get(heap_tid)
                    value = (logical_id, matched)
                    if prior is not None and prior != value:
                        observation_conflicts.add(key)
                    tuple_observed[key][heap_tid] = value

        component = checkpoint.component_id
        visited_ids = visited.get(component, set())
        queued_ids = list(frontier.get(component, Counter()).elements())
        tuple_count = 0
        tuple_pass = 0
        tuple_fail = 0
        tuple_mismatches: list[str] = []
        for identity in visited_ids:
            key = (component, identity)
            tuples = tuple_observed.get(key, {})
            tuple_count += len(tuples)
            tuple_pass += sum(matched for _, matched in tuples.values())
            tuple_fail += sum(not matched for _, matched in tuples.values())
            logical = identities.get(key, ())
            if key not in observed and tuples:
                if any(matched for _, matched in tuples.values()):
                    observed[key] = True
                elif logical and Counter(
                    value for value, _ in tuples.values() if value is not None
                ) >= Counter(logical):
                    observed[key] = False
            for heap_tid, (logical_id, matched) in tuples.items():
                row = row_by_id.get(logical_id) if logical_id is not None else None
                if row is not None and mask[row] != matched:
                    tuple_mismatches.append(f"{identity}:{heap_tid}")
        checked = [identity for identity in visited_ids if (component, identity) in observed]
        checked_matches = sum(observed[(component, identity)] for identity in checked)
        missing: set[str] = set()
        mismatches: list[str] = []

        def eligible(identity: str) -> bool | None:
            key = (component, identity)
            logical = identities.get(key)
            if key in identity_conflicts or logical is None or not logical:
                missing.add(identity)
                return None
            indexes = [row_by_id.get(value) for value in logical]
            if any(index is None for index in indexes):
                missing.add(identity)
                return None
            answer = any(mask[index] for index in indexes if index is not None)
            if key in observed and observed[key] != answer:
                mismatches.append(identity)
            return answer

        visited_values = [eligible(identity) for identity in sorted(visited_ids)]
        queued_values = [eligible(identity) for identity in queued_ids]
        expected_visited = checkpoint.features.get(
            "component_unique_discoveries", checkpoint.features.get("unique_discoveries")
        )
        expected_queued = checkpoint.features.get("frontier_count")
        count_mismatch = (
            not audit_present
            or (
                expected_visited is not None
                and expected_visited.available
                and expected_visited.value != len(visited_ids)
            )
            or (
                expected_queued is not None
                and expected_queued.available
                and expected_queued.value != len(queued_ids)
            )
        )
        complete = (
            not trace.truncated and not missing and not observation_conflicts and not count_mismatch
        )
        rows.append(
            {
                "checkpoint_index": checkpoint.index,
                "component_id": component,
                "visited_count": len(visited_ids),
                "queued_count": len(queued_ids),
                "checked_count": len(checked),
                "tuple_observation_count": tuple_count,
                "tuple_pass_count": tuple_pass,
                "tuple_fail_count": tuple_fail,
                "checked_match_fraction": checked_matches / len(checked) if checked else None,
                "checked_coverage": len(checked) / len(visited_ids) if visited_ids else None,
                "visited_match_fraction": (
                    sum(value is True for value in visited_values) / len(visited_values)
                    if complete and visited_values
                    else None
                ),
                "queued_match_fraction": (
                    sum(value is True for value in queued_values) / len(queued_values)
                    if complete and queued_values
                    else None
                ),
                "complete": complete,
                "missing_identities": sorted(missing),
                "observed_predicate_mismatches": sorted(set(mismatches + tuple_mismatches)),
                "observation_conflicts": sorted(identity for _, identity in observation_conflicts),
                "count_mismatch": count_mismatch,
                "unavailability_reason": (
                    "truncated_capture"
                    if trace.truncated
                    else "missing_identity"
                    if missing
                    else "incomplete_coverage"
                    if observation_conflicts or count_mismatch
                    else None
                ),
            }
        )
    return {
        "protocol": trace.protocol,
        "feature_registry_hash": trace.feature_registry_hash,
        "query_id": query.id,
        "trace_nonce": trace.nonce,
        "dataset_hash": trace.dataset_hash,
        "index_hash": trace.index_hash,
        "engine_build_hash": trace.engine_build_hash,
        "trace_truncated": trace.truncated,
        "capture_complete": bool(rows)
        and not trace.truncated
        and all(row["complete"] for row in rows),
        "capture_unavailability_reason": (
            "truncated_capture"
            if trace.truncated
            else "no_graph_checkpoints"
            if not rows
            else "incomplete_coverage"
            if any(not row["complete"] for row in rows)
            else None
        ),
        "audit_predicate_evaluations": len(dataset.ids),
        "checkpoints": rows,
    }


def _physical(event: dict[str, Any]) -> str:
    identity = event.get("physical_id")
    if not isinstance(identity, (str, int)) or isinstance(identity, bool):
        raise ValidationError("audit event needs a physical identity")
    return str(identity)


def _key(event: dict[str, Any]) -> tuple[str, str]:
    return str(event["component_id"]), _physical(event)
