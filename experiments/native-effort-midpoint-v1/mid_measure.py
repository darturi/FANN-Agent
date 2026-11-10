"""Quality-first conformance and two temporal warm blocks; no search on import."""

import json
import math
import random
import time
from contextlib import ExitStack

from mid_common import CELLS, COUNTS, FILTERS, SEED, context, digest, read, save
from mid_interface import audit, freeze
from mid_quality import quality_report


def write(handle, row):
    handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    handle.flush()


def schedule(qid, block):
    cells = CELLS.copy()
    random.Random(int(digest([SEED, "cells", qid]), 16)).shuffle(cells)
    if block:
        cells.reverse()
    for position, cell in enumerate(cells):
        flip = bool(int(digest([SEED, "labels", qid, cell]), 16) % 2) ^ bool(block)
        first = ["b", "a"] if flip else ["a", "b"]
        for round_ in range(2):
            for within, label in enumerate(first if round_ == 0 else first[::-1]):
                yield {
                    "cell": cell,
                    "cell_position": position,
                    "round": round_,
                    "label": label,
                    "within_round": within,
                }


def ordered(items):
    result = list(items)
    random.Random(SEED).shuffle(result)
    return result


def order_manifest(items):
    ids = [i["query"]["id"] for i in ordered(items)]
    return {
        "seed": SEED,
        "quality_order": ids,
        "timing_order": {"0": ids, "1": ids[::-1]},
        "slots": {str(b): {qid: list(schedule(qid, b)) for qid in ids} for b in (0, 1)},
    }


def truth_record(truth):
    return {
        "truth_strict": sorted(truth.strictly_better),
        "truth_ties": sorted(truth.boundary_ties),
        "truth_k": truth.effective_k,
    }


def result_record(result, truth, scorer):
    metadata = getattr(result, "metadata", None) or {}
    if any(
        metadata.get(k) for k in ("policy_applied", "policy_fallback", "policy_runtime_error")
    ) or getattr(result, "evidence", None):
        raise RuntimeError("Unexpected policy/trace result in native-only experiment")
    value = scorer(truth, result)
    record = {
        "ids": list(result.ids),
        "distances": list(result.distances),
        "recall": value["recall"],
        "valid": bool(value["valid"] and len(result.ids) == 10),
        "returned_count": len(result.ids),
        "duplicate_count": value["duplicate_count"],
        "predicate_violation_count": value["predicate_violation_count"],
    }
    if (
        not record["valid"]
        or len(result.distances) != 10
        or any(type(i) is not int for i in result.ids)
        or any(not math.isfinite(d) or not -1e-6 <= d <= 2.000001 for d in result.distances)
        or list(result.distances) != sorted(result.distances)
    ):
        raise RuntimeError("Invalid/incomplete native result; not a complete quality experiment")
    return record


def plan(reader, q):
    from psycopg import sql

    reader.check()
    statement, params = reader.backend._statement(q)
    value = reader.connection.execute(
        sql.SQL("EXPLAIN (FORMAT JSON) ") + statement, params
    ).fetchone()[0]
    if isinstance(value, str):
        value = json.loads(value)
    if not hnsw_plan(value):
        raise RuntimeError("Preserved HNSW plan not selected")
    reader.check()
    return value


def hnsw_plan(value):
    if isinstance(value, dict):
        return (
            value.get("Index Name") == "reviews_hnsw" and value.get("Node Type") == "Index Scan"
        ) or any(hnsw_plan(v) for v in value.values())
    if isinstance(value, list):
        return any(hnsw_plan(v) for v in value)
    return False


def rollback(reader):
    conn = reader.connection
    try:
        with conn.transaction():
            conn.execute("SELECT 1/0")
    except Exception as error:
        if getattr(error, "sqlstate", None) != "22012":
            raise
    else:
        raise RuntimeError("Expected native SQL error missing")
    if conn.execute("SELECT 1").fetchone()[0] != 1:
        raise RuntimeError("Rollback failed")
    reader.close()


def exact(reader, q, budget, operation):
    start = time.perf_counter_ns()
    truth = reader.exact(q, budget, operation)
    end = time.perf_counter_ns()
    return truth, {
        "start_ns": start,
        "end_ns": end,
        "outer_ms": (end - start) / 1e6,
        "inherited_non_search_execute_calls": 20,
    }


def qualify(factory, reference, items, pins, budget, scorer):
    rows, candidate = [], None
    for filter_ in FILTERS:
        q = next(i["query"] for i in items if context(i["query"]) == filter_)
        first, exact_before = exact(reference, q, budget, "qualification_exact")
        outputs = []

        def search(reader):
            start = time.perf_counter_ns()
            r = reader.native(q, budget, "qualification_native" + str(reader.level))
            end = time.perf_counter_ns()
            value = result_record(r, first, scorer)
            outputs.append(
                {
                    "step": len(outputs) + 1,
                    "reader": reader.identity,
                    "level": reader.level,
                    "result": value,
                    "start_ns": start,
                    "end_ns": end,
                    "outer_ms": (end - start) / 1e6,
                }
            )
            return value

        original = search(reference)
        pin = pins[q["id"]]
        if (
            truth_record(first) != {k: pin[k] for k in truth_record(first)}
            or original != pin["original640"]
        ):
            raise RuntimeError("Pinned original640/exact truth differs")
        old = factory.create(480, "qualification-" + filter_ + "-480-old")
        lower = search(old)
        search(reference)
        search(old)
        audits = {"before": {"reference": audit(reference), "candidate": audit(old)}}
        plans = {"native640": plan(reference, q), "native480": plan(old, q)}
        rollback(old)
        before = budget.calls
        try:
            old.native(q, budget, "qualification_native480")
        except RuntimeError:
            pass
        else:
            raise RuntimeError("Closed handle was accepted")
        if budget.calls != before:
            raise RuntimeError("Rejected closed reader consumed search")
        candidate = factory.create(480, "qualification-" + filter_ + "-480-new")
        search(candidate)
        after, exact_after = exact(reference, q, budget, "qualification_exact")
        if truth_record(first) != truth_record(after):
            raise RuntimeError("Exact truth/transaction isolation changed")
        search(reference)
        temporary = factory.create(640, "qualification-" + filter_ + "-640-new")
        try:
            search(temporary)
        finally:
            temporary.close()
        search(candidate)
        audits["after"] = {"reference": audit(reference), "candidate": audit(candidate)}
        if any(o["result"] != (original if o["level"] == 640 else lower) for o in outputs):
            raise RuntimeError("Alternation/new-session setting or result isolation failed")
        rows.append(
            {
                "query_id": q["id"],
                "filter": filter_,
                "searches": 10,
                "status": "passed",
                "truth": truth_record(first),
                "outputs": outputs,
                "settings": audits,
                "plans": plans,
                "exact_before": exact_before,
                "exact_after": exact_after,
                "sql_abort_rolled_back": True,
                "closed_session_rejected_without_search": True,
                "explicit_new_session_recovered": True,
            }
        )
        if filter_ != FILTERS[-1]:
            candidate.close()
    return {
        "status": "passed",
        "backend_searches": 30,
        "cases": rows,
        "non_search_sql": {
            "plan_explains": 6,
            "setting_queries": 12,
            "injected_failed_statements": 3,
            "rollback_recovery_selects": 3,
            "exact_internal_non_search_execute_calls": 120,
        },
    }, candidate


def measure(factory, reference, scorer, budget, package, out, items, notify):
    pins = read(package / "baseline-results.json")
    phase_start = time.perf_counter_ns()
    qualification, candidate = qualify(factory, reference, items, pins, budget, scorer)
    qualification["outer_ms"] = (time.perf_counter_ns() - phase_start) / 1e6
    save(out / "qualification.json", qualification)
    refs = {}
    with (out / "references.jsonl").open("x") as journal:
        for index, item in enumerate(ordered(items)):
            q, group = item["query"], item["group"]
            truth, charge = exact(reference, q, budget, "reference_exact")
            outcomes = {}
            for reader, cell in ((reference, "native640"), (candidate, "native480")):
                start = time.perf_counter_ns()
                result = reader.native(q, budget, "reference_" + cell)
                end = time.perf_counter_ns()
                outcomes[cell] = result_record(result, truth, scorer)
                charge[cell] = {"start_ns": start, "end_ns": end, "outer_ms": (end - start) / 1e6}
            pin = pins[q["id"]]
            if (
                truth_record(truth) != {k: pin[k] for k in truth_record(truth)}
                or outcomes["native640"] != pin["original640"]
            ):
                raise RuntimeError("Original640/truth changed in quality screen")
            row = {
                "query_id": q["id"],
                "group": group,
                **truth_record(truth),
                "outcomes": outcomes,
                "charge": charge,
            }
            write(journal, row)
            refs[q["id"]] = row
            notify("quality_references", cases=index + 1, backend_searches=budget.calls)
    phase_start = time.perf_counter_ns()
    quality = quality_report(list(refs.values()))
    quality["analysis_outer_ms"] = (time.perf_counter_ns() - phase_start) / 1e6
    save(out / "quality.json", quality)
    save(
        out / "quality-settings.json",
        {"reference": audit(reference), "candidate": audit(candidate)},
    )
    candidate.close()
    budget.check()
    if not quality["pass"]:
        return {
            "quality_pass": False,
            "retained_executions": 0,
            "discarded_warmups": 0,
            "conditioning_searches": 0,
            "slots": 0,
        }
    arms = {
        (cell, label): factory.create(int(cell[6:]), cell + "-" + label)
        for cell in CELLS
        for label in ("a", "b")
    }
    save(out / "warm-boundaries-before.json", {r.identity: audit(r) for r in arms.values()})
    counts = {
        "quality_pass": True,
        "retained_executions": 0,
        "discarded_warmups": 0,
        "conditioning_searches": 0,
        "slots": 0,
    }
    by_id = {i["query"]["id"]: i for i in items}
    order = read(package / "order.json")
    with ExitStack() as stack:
        journals = {
            n: stack.enter_context((out / (n + ".jsonl")).open("x"))
            for n in ("executions", "slots", "conditioning")
        }
        for block in range(2):
            boundary_start = time.perf_counter_ns()
            before = {r.identity: audit(r) for r in [reference, *arms.values()]}
            boundary_end = time.perf_counter_ns()
            for index, qid in enumerate(order["timing_order"][str(block)]):
                item, ref = by_id[qid], refs[qid]
                q = item["query"]
                for slot_index, meta in enumerate(schedule(qid, block)):
                    common = {
                        "query_id": qid,
                        "group": item["group"],
                        "block": block,
                        "slot_index": slot_index,
                        **meta,
                    }
                    c_start = time.perf_counter_ns()
                    for rep in range(2):
                        start = time.perf_counter_ns()
                        result = reference.native(q, budget, "conditioning")
                        end = time.perf_counter_ns()
                        # Replay validates compact truth with sealed eligibility.
                        value = unscored_record(result, ref["outcomes"]["native640"])
                        write(
                            journals["conditioning"],
                            {
                                **common,
                                "repetition": rep,
                                "start_ns": start,
                                "end_ns": end,
                                "outer_ms": (end - start) / 1e6,
                                "sql_ms": result.latency_ms,
                                "result": value,
                                "reader": reference.identity,
                            },
                        )
                        counts["conditioning_searches"] += 1
                    c_end = time.perf_counter_ns()
                    reader = arms[(meta["cell"], meta["label"])]
                    for rep in range(4):
                        operation = "warmup" if rep == 0 else "measurement"
                        start = time.perf_counter_ns()
                        result = reader.native(q, budget, operation)
                        end = time.perf_counter_ns()
                        value = unscored_record(result, ref["outcomes"][meta["cell"]])
                        write(
                            journals["executions"],
                            {
                                **common,
                                "repetition": rep,
                                "regime": "reuse",
                                "retained": rep != 0,
                                "start_ns": start,
                                "end_ns": end,
                                "outer_ms": (end - start) / 1e6,
                                "sql_ms": result.latency_ms,
                                "result": value,
                                "reader": reader.identity,
                            },
                        )
                        counts["retained_executions"] += int(rep != 0)
                        counts["discarded_warmups"] += int(rep == 0)
                    slot_end = time.perf_counter_ns()
                    write(
                        journals["slots"],
                        {
                            **common,
                            "conditioning_start_ns": c_start,
                            "conditioning_end_ns": c_end,
                            "end_ns": slot_end,
                            "reader": reader.identity,
                        },
                    )
                    counts["slots"] += 1
                notify(
                    "warm_measurement",
                    temporal_block=block,
                    cases=index + 1,
                    backend_searches=budget.calls,
                    retained=counts["retained_executions"],
                )
            end_start = time.perf_counter_ns()
            after = {r.identity: audit(r) for r in [reference, *arms.values()]}
            end_end = time.perf_counter_ns()
            save(
                out / f"warm-boundary-{block}.json",
                {
                    "block": block,
                    "before": before,
                    "after": after,
                    "start_ns": boundary_start,
                    "before_end_ns": boundary_end,
                    "after_start_ns": end_start,
                    "end_ns": end_end,
                },
            )
    if (
        counts
        != {
            "quality_pass": True,
            "retained_executions": 28800,
            "discarded_warmups": 9600,
            "conditioning_searches": 19200,
            "slots": 9600,
        }
        or budget.calls != COUNTS["searches_total"]
    ):
        raise RuntimeError("Incomplete search/slot accounting")
    return counts


def unscored_record(result, expected):
    if (
        list(result.ids) != expected["ids"]
        or list(result.distances) != expected["distances"]
        or getattr(result, "evidence", None)
        or any(
            (getattr(result, "metadata", None) or {}).get(k)
            for k in ("policy_applied", "policy_fallback", "policy_runtime_error")
        )
    ):
        raise RuntimeError("Native timed result differs from actual same-effort reference")
    return expected


def admit(snapshot, raw_items):
    result = []
    for item in raw_items:
        query = snapshot.query(item["query"])
        if context(query) != context(item["query"]) or query["id"] != item["query"]["id"]:
            raise RuntimeError("Validated query semantics differ")
        result.append({"group": item["group"], "query": freeze(query)})
    return result
