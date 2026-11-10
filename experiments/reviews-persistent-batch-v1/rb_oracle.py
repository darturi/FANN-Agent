"""Replay frozen hindsight stops as a development-only fixed-budget control."""

import json
import math
from functools import partial
from statistics import fmean
from types import SimpleNamespace
from uuid import uuid4

import rb_calibration
import rb_persistent
from rb_evidence import Evidence
from rb_measure import check_timed, collect_session, outputs
from rb_plan import CHECKPOINTS, SESSION_LENGTH, digest, require
from rb_stats import aa_equivalent, quality
from rb_verify import check_identity, check_requests

NAME = "oracle"
FAMILIES = ("native", "seed", NAME)
ARMS = tuple(f"{family}-{label}" for family in FAMILIES for label in "AB")
INTERVAL = 64
CONTINUE = (1 << 63) - 1
SCHEMA = "reviews-persistent-batch.oracle-replay.v1"
VERDICTS = (
    "measurement_inconclusive",
    "closed_negative_quality",
    "material_oracle_headroom",
    "material_oracle_headroom_not_established",
)
HEADROOM_RATIO = 0.90
make_backend = rb_calibration.make_backend


class Meter(rb_persistent.Meter):
    install_limits = {"timing": rb_persistent.WORKLOADS * rb_persistent.EPOCHS * 2}


def checkpoint_budget(states, stop):
    """Reproduce the engine checkpoint target recurrence, including overshoot."""
    require(
        stop is None or (stop in CHECKPOINTS and stop <= len(states)),
        "Oracle stop is off-grid or unreachable",
    )
    next_target = INTERVAL
    first_reached = None
    budget = CONTINUE if stop is None else states[stop - 1]["features"]["checkpoint_target"]
    for cp, state in enumerate(states, 1):
        feature = state["features"]
        actual = feature["layer0_distance_evaluations"]
        require(
            state["checkpoint_index"] == cp
            and feature["checkpoint_target"] == next_target
            and type(actual) is int
            and next_target <= actual < CONTINUE - INTERVAL
            and feature["checkpoint_overshoot"] == actual - next_target,
            "Saved HNSW checkpoint recurrence differs",
        )
        if first_reached is None and actual >= budget:
            first_reached = cp
        next_target = (actual // INTERVAL + 1) * INTERVAL
    require(first_reached == stop, "Distance budget selects a different checkpoint")
    count = stop or len(states)
    state = states[count - 1]["features"]
    actual = state["layer0_distance_evaluations"]
    return {
        "budget": budget,
        "checkpoint_count": count,
        "last_checkpoint_distances": actual,
        "max_final_distances": actual if stop else (actual // INTERVAL + 1) * INTERVAL - 1,
    }


def attach(stage, payload):
    """Bind the sealed oracle table to the unchanged retained seed and native evidence."""
    plan, base = stage.plan, stage.evidence
    rows = payload["outcomes"]
    require(
        payload["schema"] == SCHEMA
        and payload["identity"] == digest(rows)
        and rows.keys() == plan.cases.keys(),
        "Oracle evidence binding changed",
    )
    for qid, row in rows.items():
        ref = base.references[qid]
        count = row["checkpoint_count"]
        stop = row["stop"]
        actual = row["last_checkpoint_distances"]
        require(
            set(row)
            == {
                "output",
                "bypass",
                "stop",
                "prefix",
                "budget",
                "checkpoint_count",
                "last_checkpoint_distances",
                "max_final_distances",
            }
            and type(stop) is bool
            and row["bypass"] is False
            and type(count) is int
            and count > 0
            and type(actual) is int
            and actual > 0
            and type(row["budget"]) is int
            and row["budget"] > 0,
            "Malformed oracle replay row",
        )
        if stop:
            require(
                count in CHECKPOINTS
                and count <= ref["continues"]["light19"]["length"]
                and 0 <= actual - row["budget"] < INTERVAL * 8
                and row["budget"] % INTERVAL == 0
                and row["max_final_distances"] == actual,
                "Malformed saved oracle stop",
            )
        else:
            require(
                count == ref["continues"]["light19"]["length"]
                and row["budget"] == CONTINUE
                and row["prefix"] == ref["continues"]["light19"]["digest"]
                and digest(row["output"]) == digest(ref["native"])
                and row["max_final_distances"] == (actual // INTERVAL + 1) * INTERVAL - 1,
                "Malformed oracle continue",
            )
    evidence = Evidence(
        base.references,
        base.eligible,
        {"seed": base.policies["seed"]},
        {"seed": base.identities["seed"], NAME: payload["identity"]},
        {"seed": base.outcomes["seed"], NAME: rows},
    )
    verified = quality(plan, stage.frozen, evidence, NAME)
    require(
        verified == payload["recall"] and verified["passes"] and verified["stops"] == 584,
        "Sealed oracle recall changed",
    )
    stage.evidence = evidence


def fixed_budget_query(backend, query, budget, registry_hash):
    """Use the frozen engine and driver transport without installing a policy."""
    from fannagent_pgvector.native.sequential import (
        begin_execution_batch,
        begin_query_batch,
        complete_execution_batch,
    )
    from fannagent_pgvector.native.transport import feature_set_hash

    with backend._operation_lock:
        conn = backend._connect()
        snapshot = backend.snapshot()
        query = snapshot.query(query)
        statement, params = backend._statement(query)
        nonce = uuid4().hex
        groups = sorted(("basic", "work", "queue", "distances"))
        begin_sql = "SELECT fannagent.begin_execution(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        begin_params = (
            "fixed_budget",
            None,
            budget,
            nonce,
            query["k"],
            int(query.get("filter") is not None),
            "off",
            backend.config.copy.trace_max_bytes,
            registry_hash,
            feature_set_hash(groups),
            ",".join(groups),
            False,
        )
        if backend._batch_ready(conn):
            if backend._combined_query_batch:
                rows = begin_query_batch(conn, begin_sql, begin_params, statement, params, nonce)
            else:
                require(
                    begin_execution_batch(conn, begin_sql, begin_params) == nonce,
                    "Oracle request nonce was not acknowledged",
                )
                rows = conn.execute(statement, params).fetchall()
            raw = complete_execution_batch(conn, nonce, len(rows))
        else:
            with conn.transaction():
                require(
                    conn.execute(begin_sql, begin_params).fetchone() == (nonce,),
                    "Oracle request nonce was not acknowledged",
                )
                rows = conn.execute(statement, params).fetchall()
                raw = conn.execute(
                    "SELECT fannagent.complete(%s,%s)", (nonce, len(rows))
                ).fetchone()[0]
        telemetry = json.loads(raw)
        require(
            telemetry["request_nonce"] == nonce
            and telemetry["target_index_oid"] == backend.state["source_manifest"]["index"]["oid"],
            "Oracle execution binding changed",
        )
        return SimpleNamespace(
            ids=[snapshot.source_to_id[str(row[0])] for row in rows],
            distances=[float(row[1]) for row in rows],
            metadata=telemetry,
        )


def check_oracle_request(evidence, record):
    qid = record["query_id"]
    want = evidence.outcomes[NAME][qid]
    receipt = record["oracle"]
    actual = receipt["layer0_distances"]
    require(
        record["installations"] == 0
        and record["composite"] == evidence.identities[NAME]
        and record["ordinary_default"] is False
        and record["policy_applied"] is False
        and receipt["budget"] == want["budget"]
        and receipt["protocol"] == "same_execution_v4"
        and receipt["effective_mode"] == "fixed_budget"
        and receipt["executed_path"] == "postgresql_pgvector_hnsw"
        and receipt["stop_scope"] == "hnsw_scan"
        and receipt["stop_reason"] == ("fixed_budget_stop" if want["stop"] else "native_limit")
        and receipt["returned_count"] == 10
        and receipt["returned_count_source"] == "client_reported"
        and receipt["policy_hash"] is None
        and receipt["policy_fallback"] is False
        and receipt["policy_runtime_error"] is None
        and receipt["trace_descriptor"] is None
        and receipt["policy_evaluations"] == 0
        and type(actual) is int
        and want["last_checkpoint_distances"] <= actual <= want["max_final_distances"],
        "Oracle stop, budget, or execution acknowledgement differs",
    )
    check_timed(evidence, evidence.outcomes, NAME, record)


class Oracle:
    def __init__(self, frozen, evidence):
        self.registry = frozen.profile.native_registry_hash
        self.evidence = evidence

    def query(self, case, backend, meter):
        want = self.evidence.outcomes[NAME][case.id]
        meter.reserve("policy")
        if getattr(backend, "synthetic_only", False) is True:
            return backend.oracle_fixture(case.query, want)
        require(
            backend.state["source_manifest"]["settings"]["hnsw.iterative_scan"] == "off",
            "Oracle requires the retained non-iterative HNSW path",
        )
        return fixed_budget_query(backend, case.query, want["budget"], self.registry)

    def record(self, qid, result, installs, request_ns):
        meta = result.metadata
        keys = (
            "protocol",
            "effective_mode",
            "executed_path",
            "stop_scope",
            "stop_reason",
            "returned_count",
            "returned_count_source",
            "policy_hash",
            "policy_fallback",
            "policy_runtime_error",
            "trace_descriptor",
        )
        record = {
            "query_id": qid,
            "output": outputs(result),
            "bypass": False,
            "checkpoint_count": meta["checkpoint_count"],
            "stop": meta["stop_reason"] == "fixed_budget_stop",
            "installations": installs,
            "composite": self.evidence.identities[NAME],
            "ordinary_default": meta.get("ordinary_default") is True,
            "policy_applied": meta["policy_applied"],
            "request_ns": request_ns,
            "oracle": {
                **{key: meta[key] for key in keys},
                "budget": self.evidence.outcomes[NAME][qid]["budget"],
                "layer0_distances": meta["work_counters"]["layer0_distance_evaluations"],
                "policy_evaluations": meta["work_counters"]["policy_evaluation_count"],
            },
        }
        check_oracle_request(self.evidence, record)
        return record


def capture(plan, frozen, evidence, backend, meter, output, *, synthetic_only, after_snapshot):
    oracle = Oracle(frozen, evidence)

    def collect(plan, frozen, evidence, backend, meter, session, arm, epoch, *, batch_size):
        return collect_session(
            plan,
            frozen,
            evidence,
            backend,
            meter,
            session,
            arm,
            epoch,
            batch_size=batch_size,
            diagnostic=oracle if arm.startswith("oracle-") else None,
        )

    rb_calibration.capture(
        plan,
        frozen,
        evidence,
        backend,
        meter,
        output,
        synthetic_only=synthetic_only,
        after_snapshot=after_snapshot,
        schedule=rb_persistent.schedule(plan, evidence, arms=ARMS),
        batch_size=SESSION_LENGTH,
        collector=collect,
    )


def reconstruct(directory, plan, frozen, evidence, *, synthetic_only):
    rows, accounting = rb_calibration.completed_timing(directory, evidence, synthetic_only)
    cells, seen, installations, previous_close = {}, set(), 0, 0
    for row, (epoch, session, arm) in zip(
        rows, rb_persistent.schedule(plan, evidence, arms=ARMS), strict=True
    ):
        require(
            (row["epoch"], row["session_id"], row["arm"]) == (epoch, session.id, arm),
            "Oracle schedule differs",
        )
        cells[epoch, session.block, arm] = rb_persistent.measurements(row, previous_close)
        previous_close = row["boundary_ns"][-1]
        check_identity(row, seen)
        family = arm.split("-")[0]
        if family == NAME:
            for case, record in zip(session.cases, row["requests"], strict=True):
                require(record["query_id"] == case.id, "Oracle request order changed")
                check_oracle_request(evidence, record)
        else:
            installations += check_requests(session, family, evidence, row)
            for record in row["requests"]:
                check_timed(evidence, evidence.outcomes, family, record)
    rb_calibration.check_accounting(accounting, Meter, installations)
    paired = partial(rb_persistent.paired, cells)

    def labels(family):
        return f"{family}-A", f"{family}-B"

    aa = {family: paired((f"{family}-B",), (f"{family}-A",)) for family in FAMILIES}
    for cell in aa.values():
        cell["passes"] = aa_equivalent(cell)
    aa_pass = all(cell["passes"] for cell in aa.values())
    recall = {family: quality(plan, frozen, evidence, family) for family in ("seed", NAME)}
    contrasts = {}
    verdict = "measurement_inconclusive"
    if aa_pass:
        verdict = "closed_negative_quality"
        if all(cell["passes"] for cell in recall.values()):
            for left, right in ((NAME, "native"), (NAME, "seed"), ("seed", "native")):
                contrasts[f"{left}_vs_{right}"] = paired(labels(left), labels(right))
            material = all(
                cell["log_ratio_ci95"][1] < math.log(HEADROOM_RATIO)
                and all(gap < 0 for gap in cell["epoch_gap_ms"])
                for key, cell in contrasts.items()
                if key.startswith("oracle_")
            )
            verdict = (
                "material_oracle_headroom"
                if material
                else "material_oracle_headroom_not_established"
            )

    means = {
        family: {
            key: fmean(
                cell[key] for (_, _, arm), cell in cells.items() if arm.startswith(f"{family}-")
            )
            for key in next(iter(cells.values()))
        }
        for family in FAMILIES
    }
    return {
        "provisional_verdict": verdict,
        "development_qualifier": False,
        "oracle_diagnostic": True,
        "synthetic_only": synthetic_only,
        "accounting": accounting,
        "quality": recall,
        "aa_pass": aa_pass,
        "aa_per_steady_request": aa,
        "steady_contrasts_per_request": contrasts,
        "mean_lifetime_components_ms": means,
        "material_upper_ratio": HEADROOM_RATIO,
    }
