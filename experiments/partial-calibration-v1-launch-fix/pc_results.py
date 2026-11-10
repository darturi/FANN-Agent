"""Inherited result semantics and timers; no policy/graph changes."""

import math
import time

from pc_common import CELLS, CRITERIA, context, inventory
from pc_interface import freeze
from pc_stats import score_result


def truth_record(t):
    return dict(
        truth_strict=sorted(t.strictly_better),
        truth_ties=sorted(t.boundary_ties),
        truth_k=t.effective_k,
    )


def record_result(result, truth, q, eligibility):
    if getattr(result, "evidence", None) or any(
        (getattr(result, "metadata", None) or {}).get(k)
        for k in ("policy_applied", "policy_fallback", "policy_runtime_error")
    ):
        raise RuntimeError("Unexpected policy/trace result")
    ids = list(result.ids)
    distances = list(result.distances)
    strict = set(truth["truth_strict"])
    ties = set(truth["truth_ties"])
    k = truth["truth_k"]
    votes = eligibility["votes"]
    if len(ids) != 10 or any(type(i) is not int or not 0 <= i < len(votes) for i in ids):
        raise RuntimeError("Invalid result IDs/length")
    violations = sum(votes[i] is None or votes[i] < 108 for i in set(ids))
    duplicates = len(ids) - len(set(ids))
    recall = (len(set(ids) & strict) + min(k - len(strict), len(set(ids) & ties))) / k
    r = dict(
        ids=ids,
        distances=distances,
        recall=recall,
        valid=not violations and not duplicates,
        returned_count=len(ids),
        duplicate_count=duplicates,
        predicate_violation_count=violations,
    )
    score_result(r, truth, q, eligibility)
    if not r["valid"]:
        raise RuntimeError("Invalid native output is an acquisition failure")
    return r


def equivalent(value, expected):
    if (
        not value["valid"]
        or not expected["valid"]
        or value["recall"] != expected["recall"]
        or dict(zip(value["ids"], value["distances"]))
        != dict(zip(expected["ids"], expected["distances"]))
    ):
        raise RuntimeError("Repeated native ID-distance mapping changed")


def admit(snapshot, items):
    inventory(items)
    out = []
    mapping = snapshot.field_map
    if mapping.get("m_000000") != "total_votes":
        raise RuntimeError("Logical metadata mapping differs")
    for i in items:
        q = snapshot.query(i["query"])
        context(q)
        if q != i["query"]:
            raise RuntimeError("Validated query semantics differ")
        out.append(dict(group=i["group"], query=freeze(q)))
    return out


def call(reader, q, truth, budget, operation, eligibility, emit, **meta):
    start = time.perf_counter_ns()
    value = None
    reserved = budget.calls
    try:
        r = reader.native(q, budget, operation)
        end = time.perf_counter_ns()
        value = record_result(r, truth, q, eligibility)
        if not math.isfinite(r.latency_ms) or r.latency_ms < 0:
            raise RuntimeError("Invalid SQL timer")
        row = dict(
            operation=operation,
            query_id=q["id"],
            group=q["id"].rsplit("-", 1)[0],
            reader=reader.identity,
            cell=reader.mode,
            stage=budget.stage,
            start_ns=start,
            end_ns=end,
            outer_ms=(end - start) / 1e6,
            sql_ms=r.latency_ms,
            result=value,
            **meta,
        )
        emit("searches", row)
        return row
    except BaseException as e:
        if budget.calls > reserved:
            emit(
                "searches",
                dict(
                    operation=operation,
                    query_id=q["id"],
                    reader=reader.identity,
                    cell=reader.mode,
                    stage=budget.stage,
                    start_ns=start,
                    end_ns=time.perf_counter_ns(),
                    error=dict(type=type(e).__name__, message=str(e)),
                    **meta,
                ),
            )
        raise


def exact(reader, q, budget, operation, emit):
    start = time.perf_counter_ns()
    reserved = budget.calls
    try:
        t = reader.exact(q, budget, operation)
        end = time.perf_counter_ns()
        value = truth_record(t)
        emit(
            "searches",
            dict(
                operation=operation,
                query_id=q["id"],
                reader=reader.identity,
                cell=reader.mode,
                stage=budget.stage,
                start_ns=start,
                end_ns=end,
                outer_ms=(end - start) / 1e6,
                truth=value,
            ),
        )
        return value
    except BaseException as e:
        if budget.calls > reserved:
            emit(
                "searches",
                dict(
                    operation=operation,
                    query_id=q["id"],
                    reader=reader.identity,
                    stage=budget.stage,
                    start_ns=start,
                    end_ns=time.perf_counter_ns(),
                    error=dict(type=type(e).__name__, message=str(e)),
                ),
            )
        raise


def quality_report(refs):
    import numpy as np

    if len(refs) != 200 or len({r["group"] for r in refs}) != 200:
        raise ValueError("Incomplete quality inventory")
    for r in refs:
        if set(r["outcomes"]) != set(CELLS) or not all(
            v["valid"] and v["returned_count"] == 10 for v in r["outcomes"].values()
        ):
            raise ValueError("Invalid reference output")
    values = np.asarray(
        [
            r["outcomes"]["partial640"]["recall"] - r["outcomes"]["native640"]["recall"]
            for r in sorted(refs, key=lambda r: r["group"])
        ]
    )
    rng = np.random.default_rng(CRITERIA["bootstrap_seed"])
    boot = np.empty(CRITERIA["bootstrap_samples"])
    for i in range(0, len(boot), 128):
        count = min(128, len(boot) - i)
        boot[i : i + count] = values[rng.integers(0, 200, size=(count, 200))].mean(axis=1)
    ci = np.quantile(boot, [0.025, 0.975]).tolist()
    means = {c: float(np.mean([r["outcomes"][c]["recall"] for r in refs])) for c in CELLS}
    checks = dict(
        both_native_floors=all(v >= 0.95 for v in means.values()),
        development_reserve=ci[0] >= -0.0025,
    )
    return dict(
        context="votes108",
        cases=200,
        independent_vectors=200,
        mean_recall=means,
        recall_delta=float(values.mean()),
        recall_delta_ci95=ci,
        checks=checks,
        **{"pass": all(checks.values())},
        final_margin_diagnostic_only=ci[0] >= -0.005,
        independent_confirmation=False,
    )
