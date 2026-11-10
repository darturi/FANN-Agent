"""Frozen backend execution body; only policy preparation resolves an owned handle.

The correctness suite compares this AST with the pinned original, allowing only
this function name and one policy-preparation expression to differ.
"""

import json
import tempfile
import time
import uuid
from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path

from fannagent_pgvector.backend import (
    FEATURE_REGISTRY_HASH,
    ExecutionContext,
    ProbeResult,
    Query,
    begin_execution_batch,
    begin_query_batch,
    complete_execution_batch,
    feature_set_hash,
    normalize_engine_trace,
    predicate_leaf_count,
    reconstruct_membership,
)

from fannagent.api import AgentError


def execute_owned(backend, query, handle, *, trace=False):
    with backend._operation_lock:
        try:
            return _execute_owned(backend, query, mode="policy", policy=handle, trace=trace)
        except BaseException:
            backend.close()
            raise


def _execute_owned(self, query, *, mode="native", policy=None, trace=False, audit=False):
    conn = self._connect()
    started = time.perf_counter_ns()
    policy = policy.resolve(self) if policy is not None else None
    if mode == "policy":
        query = self.snapshot().query(query)
    statement, params = self._statement(query)
    nonce = uuid.uuid4().hex
    groups = (
        list(policy.groups)
        if policy
        else [
            "basic",
            "work",
            "filters",
            "progress",
            "queue",
            "queue_quantiles",
            "pgvector_executor",
        ]
    )
    context = ExecutionContext(
        mode="policy_agent" if mode == "policy" else "policy_noop",
        policy_hash=policy.policy_hash if policy else None,
        trace_level="checkpoints" if trace else "off",
        policy_role="treatment" if policy else None,
        policy_feature_profile="fann_features_v2",
        trace_max_bytes=self.config.copy.trace_max_bytes,
        feature_groups=groups,
        audit_membership=audit,
    )
    # Native timing is an ordinary autocommit SQL request. Policy timing includes
    # validation, initialization, transaction boundaries, transport and decoding.
    begin_params = (
        context.mode.value,
        context.policy_hash,
        None,
        nonce,
        query["k"],
        predicate_leaf_count(query.get("filter")),
        context.trace_level.value,
        context.trace_max_bytes,
        FEATURE_REGISTRY_HASH,
        policy.group_hash if policy else feature_set_hash(groups),
        policy.group_csv if policy else ",".join(sorted(groups)),
        audit,
    )
    begin_sql = "SELECT fannagent.begin_execution(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    if "local_filter" in groups:
        predicate = query.get("filter")
        if predicate is None:
            threshold = 0
        elif (
            isinstance(predicate, dict)
            and set(predicate) == {"field", "op", "value"}
            and predicate["field"] == "m_000000"
            and predicate["op"] == "gte"
            and type(predicate["value"]) is int
            and 0 <= predicate["value"] < 2**63
        ):
            threshold = predicate["value"]
        else:
            raise AgentError("local-filter-v1 requires the declared votes predicate")
        begin_sql = begin_sql[:-1] + ",%s::bigint)"
        begin_params = (*begin_params, threshold)
    # Select transport before sending execution commands. Installation is acknowledged
    # separately and remains inside this call's original policy timing boundary.
    batched = mode != "native" and self._batch_ready(conn)
    if batched:
        if policy and self._installed != policy.policy_hash:
            self._install_policy(policy)
        if self._combined_query_batch:
            rows = begin_query_batch(conn, begin_sql, begin_params, statement, params, nonce)
        else:
            ack = begin_execution_batch(conn, begin_sql, begin_params)
            if ack != nonce:
                raise AgentError("query nonce acknowledgement mismatch")
            rows = conn.execute(statement, params).fetchall()
        # The final batch drains completion AND commit before accepting results.
        telemetry = json.loads(complete_execution_batch(conn, nonce, len(rows)))
        decoded = [(self.snapshot().source_to_id[str(r[0])], float(r[1])) for r in rows]
        if mode == "policy":
            telemetry["application_source_ids"] = [int(r[0]) for r in rows]
    else:
        with nullcontext() if mode == "native" else conn.transaction():
            if mode == "native":
                started = time.perf_counter_ns()
            if mode != "native":
                if policy and self._installed != policy.policy_hash:
                    self._install_policy(policy)
                ack = conn.execute(
                    begin_sql,
                    begin_params,
                ).fetchone()[0]
                if ack != nonce:
                    raise AgentError("query nonce acknowledgement mismatch")
            rows = conn.execute(statement, params).fetchall()
            telemetry = (
                json.loads(
                    conn.execute("SELECT fannagent.complete(%s,%s)", (nonce, len(rows))).fetchone()[
                        0
                    ]
                )
                if mode != "native"
                else {"ordinary_default": True}
            )
            decoded = [(self.snapshot().source_to_id[str(r[0])], float(r[1])) for r in rows]
            if mode == "policy":
                telemetry["application_source_ids"] = [int(r[0]) for r in rows]
    if mode != "native":
        if (
            telemetry.get("request_nonce") != nonce
            or telemetry.get("protocol") != "same_execution_v4"
        ):
            raise AgentError("execution telemetry identity mismatch")
        if policy and telemetry.get("policy_hash") != policy.policy_hash:
            raise AgentError("executed policy hash mismatch")
        if (
            telemetry.get("returned_count") != len(rows)
            or telemetry.get("returned_count_source") != "client_reported"
        ):
            raise AgentError("execution result-count acknowledgement mismatch")
        if telemetry.get("effective_mode") != context.mode.value:
            raise AgentError("execution mode acknowledgement mismatch")
        if policy and telemetry.get("policy_opportunity") and not telemetry.get("policy_applied"):
            raise AgentError("engine had a checkpoint but did not evaluate the policy")
        if (
            telemetry.get("target_index_oid")
            != (self._binding or self.store.get("source_manifest"))["index"]["oid"]
        ):
            raise AgentError("query bound index identity mismatch")
    elapsed = (time.perf_counter_ns() - started) / 1e6
    raw_trace = (
        conn.execute("SELECT fannagent.take_trace(%s)", (nonce,)).fetchone()[0]
        if trace and mode != "native"
        else None
    )
    evidence = None
    if raw_trace is not None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / f"{nonce}.jsonl"
            path.write_text(raw_trace)
            prepared = self.store.get("prepared")
            normalized = normalize_engine_trace(
                path,
                descriptor=telemetry["trace_descriptor"],
                backend="pgvector",
                query=Query.model_validate(query),
                context=context,
                nonce=nonce,
                dataset_hash=self.snapshot().identity,
                index_hash=prepared["index_identity"],
                engine_build_hash=prepared["image_id"],
                completion=telemetry,
            )
        for event in normalized.events:
            if "logical_ids" in event:
                event["logical_ids"] = [
                    self.snapshot().source_to_id[str(v)] for v in event["logical_ids"]
                ]
            for key in ("identity", "logical_id"):
                if event.get(key) is not None:
                    event[key] = self.snapshot().source_to_id[str(event[key])]
        evidence = {
            "checkpoints": [
                {
                    "index": c.index,
                    "actual_layer0_distances": c.actual_layer0_distances,
                    "component_id": c.component_id,
                    "features": {n: f.value for n, f in c.features.items() if f.available},
                }
                for c in normalized.checkpoints
            ],
            "terminal": normalized.terminal,
            "truncated": normalized.truncated,
            "collection_groups": groups,
            "normalized": asdict(normalized),
        }
        if audit:
            evidence["membership"] = reconstruct_membership(
                self.snapshot().data, Query.model_validate(query), normalized
            )
            evidence["membership_provenance"] = "offline_identity_predicate_reconstruction"
    return ProbeResult(
        [r[0] for r in decoded], [r[1] for r in decoded], elapsed, telemetry, evidence
    )
