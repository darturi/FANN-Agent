"""Bounded native conformance and fully charged application timing."""

import json
import random
import time
from contextlib import ExitStack

from ef_common import CELLS, COUNTS, FILTERS, SEED, digest, lines, read, save
from ef_interface import Pool, audit_session, envelope, execute, session, settings


def write(handle, row):
    handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    handle.flush()


def schedule(qid, block):
    cells = CELLS.copy()
    random.Random(int(digest(["effort-cells-v1", qid]), 16)).shuffle(cells)
    if block:
        cells.reverse()
    for position, cell in enumerate(cells):
        flip = bool(int(digest(["effort-label-v1", qid, cell]), 16) % 2) ^ bool(block)
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


def truth_record(truth):
    return {
        "truth_strict": sorted(truth.strictly_better),
        "truth_ties": sorted(truth.boundary_ties),
        "truth_k": truth.effective_k,
    }


def result_record(result, truth, scorer):
    score = scorer(truth, result)
    return {
        "ids": list(result.ids),
        "distances": list(result.distances),
        "recall": score["recall"],
        "valid": bool(score["valid"] and len(result.ids) == 10),
        "returned_count": len(result.ids),
        "duplicate_count": score["duplicate_count"],
        "predicate_violation_count": score["predicate_violation_count"],
    }


def native(reader, q, budget, operation):
    budget.reserve(operation)
    return reader.execute_probe(q, mode="native")


def exact(reader, q, budget, operation):
    budget.reserve(operation)
    return reader.exact_reference(q)


def plan(reader, q):
    from psycopg import sql

    statement, params = reader._statement(q)
    value = (
        reader._connect()
        .execute(sql.SQL("EXPLAIN (FORMAT JSON) ") + statement, params)
        .fetchone()[0]
    )
    if isinstance(value, str):
        value = json.loads(value)

    def nodes(v):
        if isinstance(v, dict):
            yield v
            for child in v.values():
                yield from nodes(child)
        elif isinstance(v, list):
            for child in v:
                yield from nodes(child)

    if not any(
        n.get("Index Name") == "reviews_hnsw" and n.get("Node Type") == "Index Scan"
        for n in nodes(value)
    ):
        raise RuntimeError("Native effort query did not select the preserved HNSW index")
    return value


def qualify(create, reference, source, items, pins, budget, scorer):
    rows = []
    for filter_ in FILTERS:
        q = next(i["query"] for i in items if i["query"]["id"].endswith("-" + filter_))
        truth = exact(reference, q, budget, "qualification_exact")
        original = result_record(
            native(reference, q, budget, "qualification_original640"), truth, scorer
        )
        pin = pins[q["id"]]
        if (
            truth_record(truth) != {k: pin[k] for k in truth_record(truth)}
            or original != pin["original640"]
        ):
            raise RuntimeError("Pinned original640/exact reference changed")
        pool = Pool(create)
        fresh = None
        try:
            outputs, audits, plans = [], {}, {}
            for level in (640, 320, 640):
                r, route = pool.query(envelope(q, level), budget, "qualification_wrapped")
                outputs.append(
                    {"level": level, "result": result_record(r, truth, scorer), "route": route}
                )
            s_before = result_record(
                native(source, q, budget, "qualification_source"), truth, scorer
            )
            for level in (320, 640):
                r, route = pool.query(envelope(q, level), budget, "qualification_wrapped")
                outputs.append(
                    {"level": level, "result": result_record(r, truth, scorer), "route": route}
                )
            audits["before"] = {
                "original640": settings(reference),
                "source": settings(source),
                "pool": pool.audit(),
            }
            for name, reader in {
                "original640": reference,
                "source": source,
                **{str(n): r for n, r in pool._readers.items()},
            }.items():
                plans[name] = plan(reader, q)
            # A real aborted transaction is rolled back. Closing the poisoned session
            # cannot trigger a transparent retry; only explicit new admission recovers.
            conn = pool._connections[320]
            failed_sql = False
            try:
                with conn.transaction():
                    conn.execute("SELECT 1/0")
            except Exception as error:
                if getattr(error, "sqlstate", None) != "22012":
                    raise
                failed_sql = True
            if not failed_sql or conn.execute("SELECT 1").fetchone()[0] != 1:
                raise RuntimeError("SQL rollback qualification failed")
            pool.close()
            calls_before = budget.calls
            try:
                pool.query(envelope(q, 640), budget, "qualification_wrapped")
            except RuntimeError:
                pass
            else:
                raise RuntimeError("Closed session accepted a query")
            if budget.calls != calls_before:
                raise RuntimeError("Rejected closed session consumed a search")
            fresh = Pool(create)
            r, route = fresh.query(envelope(q, 640), budget, "qualification_wrapped")
            outputs.append(
                {"level": 640, "result": result_record(r, truth, scorer), "route": route}
            )
            after = exact(reference, q, budget, "qualification_exact")
            o_after = result_record(
                native(reference, q, budget, "qualification_original640"), after, scorer
            )
            s_after = result_record(
                native(source, q, budget, "qualification_source"), after, scorer
            )
            if (
                truth_record(after) != truth_record(truth)
                or o_after != original
                or s_after != s_before
            ):
                raise RuntimeError("Exact reference leaked settings or changed outputs")
            if any(o["result"] != original for o in outputs if o["level"] == 640):
                raise RuntimeError("Effort640 differs from unchanged ordinary-native reference")
            lower = [o["result"] for o in outputs if o["level"] == 320]
            if lower[0] != lower[1] or (
                int(source._binding["settings"]["hnsw.ef_search"]) == 320 and s_before != lower[0]
            ):
                raise RuntimeError("Effort/source setting isolation failed")
            audits["after"] = {
                "original640": settings(reference),
                "source": settings(source),
                "pool": fresh.audit(),
            }
            rows.append(
                {
                    "query_id": q["id"],
                    "filter": filter_,
                    "status": "passed",
                    "searches": 12,
                    "truth": truth_record(truth),
                    "original640": original,
                    "source": s_before,
                    "outputs": outputs,
                    "settings": audits,
                    "plans": plans,
                    "sql_abort_rolled_back": True,
                    "closed_session_rejected_without_search": True,
                    "explicit_new_session_recovered": True,
                }
            )
        finally:
            pool.close()
            if fresh is not None:
                fresh.close()
    return {
        "status": "passed",
        "backend_searches": 36,
        "cases": rows,
        "diagnostic_sql": (
            "12 EXPLAINs,24 setting queries,3 failed transaction statements,3 recovery SELECTs; "
            "transaction boundaries/binding SQL separate from search counts"
        ),
    }


def measure(create, reference, source, scorer, budget, package, out, block, notify):
    items = lines(package / "frozen/inputs/queries.jsonl")
    pins = read(package / "baseline-results.json")
    started = time.perf_counter_ns()
    qualification = qualify(create, reference, source, items, pins, budget, scorer)
    qualification["outer_ms"] = (time.perf_counter_ns() - started) / 1e6
    save(out / "qualification.json", qualification)
    ordered = items.copy()
    random.Random(SEED + block).shuffle(ordered)
    retained, warms, slots, conditions = 0, 0, 0, 0
    reference_pool = Pool(create)
    try:
        with ExitStack() as stack:
            journals = {
                n: stack.enter_context((out / (n + ".jsonl")).open("x"))
                for n in ("references", "executions", "slots", "conditioning")
            }
            for index, item in enumerate(ordered):
                q, group = item["query"], item["group"]
                ref_started = time.perf_counter_ns()
                truth = exact(reference, q, budget, "reference_exact")
                native_ = native(reference, q, budget, "reference_original640")
                original = result_record(native_, truth, scorer)
                lower, _ = reference_pool.query(envelope(q, 320), budget, "reference_wrapped320")
                source_ = native(source, q, budget, "reference_source")
                outcomes = {
                    "original640": original,
                    "wrapped640": original,
                    "wrapped320": result_record(lower, truth, scorer),
                    "source": result_record(source_, truth, scorer),
                }
                pin = pins[q["id"]]
                if original != pin["original640"] or truth_record(truth) != {
                    k: pin[k] for k in truth_record(truth)
                }:
                    raise RuntimeError("Original640/exact pinned identity changed: " + q["id"])
                if not original["valid"]:
                    raise RuntimeError("Incomplete/invalid original640 reference")
                ref = {
                    "query_id": q["id"],
                    "group": group,
                    **truth_record(truth),
                    "outcomes": outcomes,
                    "outer_ms": (time.perf_counter_ns() - ref_started) / 1e6,
                }
                write(journals["references"], ref)
                for slot_index, meta in enumerate(schedule(q["id"], block)):
                    wrapped = meta["cell"].startswith("wrapped")
                    common = {
                        "query_id": q["id"],
                        "group": group,
                        "block": block,
                        "slot_index": slot_index,
                        **meta,
                    }
                    c_start = time.perf_counter_ns()
                    for repetition in range(2):
                        begin = time.perf_counter_ns()
                        r = native(reference, q, budget, "conditioning")
                        end = time.perf_counter_ns()
                        value = result_record(r, truth, scorer)
                        if value != original:
                            raise RuntimeError("Conditioning changed original640 output")
                        write(
                            journals["conditioning"],
                            {
                                **common,
                                "repetition": repetition,
                                "start_ns": begin,
                                "end_ns": end,
                                "outer_ms": (end - begin) / 1e6,
                                "sql_ms": r.latency_ms,
                                "result": value,
                            },
                        )
                        conditions += 1
                    c_end = time.perf_counter_ns()
                    prep_start = time.perf_counter_ns()
                    s = None
                    try:
                        s = session(create, meta["cell"])
                        prep_end = time.perf_counter_ns()
                        prep_ms = (prep_end - prep_start) / 1e6
                        for repetition in range(5):
                            if wrapped:
                                begin = time.perf_counter_ns()
                                r, route = execute(s, meta["cell"], q, budget)
                                end = time.perf_counter_ns()
                            else:
                                begin = time.perf_counter_ns()
                                budget.reserve("measurement")
                                r = s.execute_probe(q, mode="native")
                                end = time.perf_counter_ns()
                                # Diagnostic reporting stays outside the unchanged
                                # ordinary-native query endpoint.
                                route = {
                                    "requested_effort": None,
                                    "effective_effort": int(
                                        s._binding["settings"]["hnsw.ef_search"]
                                    ),
                                    "context": None,
                                    "fallback_to640": False,
                                }
                            value = result_record(r, truth, scorer)
                            if value != outcomes[meta["cell"]]:
                                raise RuntimeError("Timed result differs from actual effort proof")
                            cold = repetition == 0
                            row = {
                                **common,
                                "repetition": repetition,
                                "regime": "activation" if cold else "reuse",
                                "retained": repetition != 1,
                                "start_ns": begin,
                                "end_ns": end,
                                "query_outer_ms": (end - begin) / 1e6,
                                "preparation_ms": prep_ms if cold else 0.0,
                                "outer_ms": (end - begin) / 1e6 + (prep_ms if cold else 0.0),
                                "sql_ms": r.latency_ms,
                                "route": route,
                                "result": value,
                            }
                            write(journals["executions"], row)
                            retained += int(repetition != 1)
                            warms += int(repetition == 1)
                        audit_start = time.perf_counter_ns()
                        audit = audit_session(s, meta["cell"])
                        audit_end = time.perf_counter_ns()
                    finally:
                        close_start = time.perf_counter_ns()
                        if s is not None:
                            s.close()
                        close_end = time.perf_counter_ns()
                    write(
                        journals["slots"],
                        {
                            **common,
                            "conditioning_start_ns": c_start,
                            "conditioning_end_ns": c_end,
                            "preparation_start_ns": prep_start,
                            "preparation_end_ns": prep_end,
                            "preparation_ms": prep_ms,
                            "audit_start_ns": audit_start,
                            "audit_end_ns": audit_end,
                            "audit": audit,
                            "cleanup_start_ns": close_start,
                            "cleanup_end_ns": close_end,
                        },
                    )
                    slots += 1
                notify(
                    "measurement",
                    query=index + 1,
                    total=len(items),
                    backend_searches=budget.calls,
                    retained=retained,
                )
    finally:
        reference_pool.close()
    counts = {
        "retained_executions": retained,
        "discarded_warmups": warms,
        "slots": slots,
        "conditioning_searches": conditions,
    }
    expected = {
        "retained_executions": COUNTS["retained_executions_per_block"],
        "discarded_warmups": COUNTS["discarded_warmups_per_block"],
        "slots": COUNTS["slots_per_block"],
        "conditioning_searches": COUNTS["conditioning_searches_per_block"],
    }
    if counts != expected or budget.calls != COUNTS["searches_per_block"]:
        raise RuntimeError("Incomplete call accounting")
    return counts
