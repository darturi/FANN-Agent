"""Capture exactly 200 votes108 observations on an already verified private restore."""

import json
from pathlib import Path
from statistics import fmean
from tempfile import TemporaryDirectory
from time import monotonic_ns
from uuid import uuid4

from rb_evidence import PILOT_REFS, Evidence, stop_proofs
from rb_native import GRAPH
from rb_plan import PILOT_BLOCK, ROOT, digest, file_sha, pinned, pinned_lines, require
from rb_stats import exact_truth, quality, result_score

CHECKPOINTS = (16, 32, 64)
BASELINE_GAP = 0.05

GROUPS = ("basic", "distances", "query_context", "queue", "work")
BEGIN = "SELECT fannagent.begin_execution(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::bigint)"


def capture_request(conn, backend, snapshot, case, names, context, expected_index, folder):
    from fannagent_pgvector.native.features import FEATURE_REGISTRY_HASH
    from fannagent_pgvector.native.transport import feature_set_hash, normalize_engine_trace

    from fannagent.api.primitives.data import Query

    mode = context.mode.value
    query = snapshot.query(case.query)
    require(
        query["k"] == 10 and query["filter"] == {"field": "m_000000", "op": "gte", "value": 108},
        "Unexpected shadow query predicate",
    )
    statement, params = backend._statement(query)
    nonce = uuid4().hex
    begin_args = (
        mode,
        None,
        context.fixed_budget,
        nonce,
        10,
        1,
        "checkpoints",
        context.trace_max_bytes,
        FEATURE_REGISTRY_HASH,
        feature_set_hash(GROUPS),
        ",".join(GROUPS),
        False,
        108,
    )
    require(conn.execute(BEGIN, begin_args).fetchone() == (nonce,), "Missing begin acknowledgement")
    output = conn.execute(statement, params).fetchall()
    raw = conn.execute("SELECT fannagent.complete(%s,%s)", (nonce, len(output))).fetchone()[0]
    telemetry = json.loads(raw)
    require(
        telemetry["request_nonce"] == nonce
        and telemetry["target_index_oid"] == expected_index
        and telemetry["effective_mode"] == mode
        and telemetry["stop_reason"]
        == ("fixed_budget_stop" if context.fixed_budget else "native_limit")
        and telemetry["returned_count"] == len(output) <= 10,
        "Shadow completion identity changed",
    )
    observations = json.loads(
        conn.execute("SELECT fannagent.shadow_read(%s)", (nonce,)).fetchone()[0]
    )
    raw_trace = conn.execute("SELECT fannagent.take_trace(%s)", (nonce,)).fetchone()[0]
    trace_file = folder / f"{nonce}.jsonl"
    trace_file.write_text(raw_trace)
    prepared = backend.store.get("prepared")
    trace = normalize_engine_trace(
        trace_file,
        descriptor=telemetry["trace_descriptor"],
        backend="pgvector",
        query=Query.model_validate(query),
        context=context,
        nonce=nonce,
        dataset_hash=snapshot.identity,
        index_hash=prepared["index_identity"],
        engine_build_hash=prepared["image_id"],
        completion=telemetry,
    )
    trace_file.unlink()
    require(not trace.truncated, "Incomplete shadow traversal trace")
    states = []
    for cp in trace.checkpoints:
        features = {name: field.value for name, field in cp.features.items() if field.available}
        states.append(
            {
                "checkpoint_index": cp.index,
                "features": {name: features.get(name) for name in names},
            }
        )
    return {
        "query_id": case.id,
        "output": [
            [snapshot.source_to_id[str(row[0])] for row in output],
            [float(row[1]) for row in output],
        ],
        "light19_trace_sha256": digest(states),
        "checkpoints": observations,
        "layer0_work": telemetry["work_counters"]["layer0_distance_evaluations"],
    }, states


def reference_rows(plan):
    """Extract compact capture pins locally for staging with the guest."""
    proofs = stop_proofs(ROOT, "static23")
    return {
        row["query_id"]: [
            [row["native_ids"], row["native_distances"]],
            digest(row["states"]["light19"]),
            {
                str(cp): proofs["static23", row["query_id"], cp][1]
                for cp in CHECKPOINTS
                if cp <= len(row["states"]["light19"])
            },
        ]
        for row in pinned_lines(ROOT / PILOT_BLOCK / "references.jsonl", PILOT_REFS)
        if plan.cases[row["query_id"]].stratum == "votes108"
    }


def capture(
    plan, frozen, evidence, backend, destination, reference_path, reference_sha, module_sha
):
    """The caller must verify the physical restore before and after this capture."""
    from fannagent_pgvector.native.context import ExecutionContext

    require(not destination.exists(), "Capture destination already exists")
    require(
        file_sha(Path("/opt/postgresql/lib/vector.so")) == module_sha,
        "Loaded shadow module differs from qualification",
    )
    prepared = backend.store.get("prepared")
    require(prepared["index_identity"] == GRAPH, "Prepared graph identity changed")
    source = backend.store.get("source_manifest")
    expected_index = source["index"]["oid"]
    cases = {qid: case for qid, case in plan.cases.items() if case.stratum == "votes108"}
    require(len(cases) == 200, "Unexpected shadow request limit")
    expected = json.loads(pinned(reference_path, reference_sha))
    require(expected.keys() == cases.keys(), "Saved output and trace coverage differs")
    names = frozen.policy.names(plan.config, "light19")
    context = ExecutionContext(
        mode="policy_noop",
        trace_level="checkpoints",
        policy_feature_profile="fann_features_v2",
        trace_max_bytes=backend.config.copy.trace_max_bytes,
        feature_groups=list(GROUPS),
        audit_membership=False,
    )
    start = monotonic_ns()
    conn = backend._connect()
    snapshot = backend.snapshot()
    setup_ns = monotonic_ns() - start
    rows = []
    with conn.transaction(), TemporaryDirectory() as temp:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '60s'")
        start = monotonic_ns()
        ack = conn.execute(
            "SELECT fannagent.shadow_bind(%s::regclass)", (backend.relation.as_string(conn),)
        ).fetchone()
        map_ns = monotonic_ns() - start
        require(ack == (247286,), "Membership map acknowledgement differs")
        for qid, case in cases.items():
            row, states = capture_request(
                conn, backend, snapshot, case, names, context, expected_index, Path(temp)
            )
            require(
                [row["output"], row["light19_trace_sha256"]] == expected[qid][:2],
                f"Shadow changed pinned output or traversal: {qid}",
            )
            reached = [cp for cp in CHECKPOINTS if cp <= len(states)]
            require(
                [cp["checkpoint"] for cp in row["checkpoints"]] == reached,
                f"Incomplete native observations: {qid}",
            )
            truth = exact_truth(frozen, evidence.references[qid], evidence.eligible["votes108"])
            row["native_recall"], native_valid = result_score(frozen, truth, row["output"])
            require(native_valid, f"Invalid pinned native output: {qid}")
            row["forced_stops"] = []
            for obs in row["checkpoints"]:
                cp = obs["checkpoint"]
                features = states[cp - 1]["features"]
                obs["frontier_distance_min"] = features["frontier_distance_min"]
                budget = features["checkpoint_target"]
                stop_context = ExecutionContext(
                    **{**context.model_dump(), "mode": "fixed_budget", "fixed_budget": budget}
                )
                stopped, prefix = capture_request(
                    conn, backend, snapshot, case, names, stop_context, expected_index, Path(temp)
                )
                require(prefix == states[:cp], f"Forced stop changed traversal: {qid} cp{cp}")
                require(
                    [sample["checkpoint"] for sample in stopped["checkpoints"]]
                    == [point for point in reached if point <= cp],
                    f"Incomplete forced observations: {qid} cp{cp}",
                )
                for measured, shadow in zip(stopped["checkpoints"], row["checkpoints"]):
                    require(
                        all(
                            measured[key] == shadow[key]
                            for key in (
                                "qualifying_count",
                                "tenth_distance",
                                "top10_new_since_previous",
                            )
                        ),
                        f"Forced and continue observations differ: {qid} cp{cp}",
                    )
                recall, valid = result_score(frozen, truth, stopped["output"])
                row["forced_stops"].append(
                    {
                        "checkpoint": cp,
                        "budget": budget,
                        "prefix_sha256": digest(prefix),
                        "output": stopped["output"],
                        "recall": recall,
                        "valid_top10": valid,
                        "saved_stop_output_matches": stopped["output"] == expected[qid][2][str(cp)],
                        "layer0_work": stopped["layer0_work"],
                        "layer0_saved_vs_continue": row["layer0_work"] - stopped["layer0_work"],
                        "collection_ns_by_checkpoint": {
                            sample["checkpoint"]: sample["collection_ns"]
                            for sample in stopped["checkpoints"]
                        },
                    }
                )
            row["unreached_checkpoints"] = sorted(set(CHECKPOINTS) - set(reached))
            row["baseline_stop_checkpoint"] = next(
                (
                    32
                    for obs in row["checkpoints"]
                    if obs["checkpoint"] == 32
                    and obs["tenth_distance"] is not None
                    and obs["frontier_distance_min"] is not None
                    and obs["frontier_distance_min"] - obs["tenth_distance"] >= BASELINE_GAP
                ),
                None,
            )
            rows.append(row)
    by_id = {row["query_id"]: row for row in rows}
    outcomes = dict(evidence.outcomes["seed"])
    for qid, row in by_id.items():
        if row["baseline_stop_checkpoint"] is not None:
            stopped = next(stop for stop in row["forced_stops"] if stop["checkpoint"] == 32)
            outcomes[qid] = {"stop": True, "output": stopped["output"]}
    baseline = quality(
        plan,
        frozen,
        Evidence(evidence.references, evidence.eligible, {}, {}, {"baseline": outcomes}),
        "baseline",
    )
    forced_count = sum(len(row["forced_stops"]) for row in rows)
    selected = [row for row in rows if row["baseline_stop_checkpoint"] == 32]
    continued = [row for row in rows if row["baseline_stop_checkpoint"] is None]
    baseline_costs = {}
    for label, cohort in (("would_stop", selected), ("would_continue", continued)):
        costs = [
            obs["collection_ns"]
            for row in cohort
            for obs in row["checkpoints"]
            if obs["checkpoint"] == 32
        ]
        baseline_costs[label] = {
            "requests_with_checkpoint_32": len(costs),
            "mean_extended_observer_ns": fmean(costs) if costs else None,
        }
    with destination.open("x") as stream:
        for row in rows:
            print(json.dumps(row, sort_keys=True, allow_nan=False), file=stream)
    return {
        "graph": GRAPH,
        "module_sha256": module_sha,
        "capture_reference_sha256": reference_sha,
        "shadow_return_sha256": file_sha(destination),
        "searches": len(rows) + forced_count,
        "shadow_continues": len(rows),
        "verified_forced_stops": forced_count,
        "saved_stop_output_mismatches": sum(
            not stop["saved_stop_output_matches"] for row in rows for stop in row["forced_stops"]
        ),
        "baseline": {
            "checkpoint": 32,
            "minimum_frontier_gap": BASELINE_GAP,
            "votes108_stops": len(selected),
            "checkpoint_32_shadow_cost": baseline_costs,
            "quality": baseline,
        },
        "reader_setup_ns": setup_ns,
        "membership_map_build_ns": map_ns,
    }
