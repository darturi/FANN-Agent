"""M5 semantics, full-request timing and separately instrumented work. No model imports."""

import json
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path
from time import perf_counter_ns

from common import capture, matches, require, search, threshold, write
from m5_design import (
    ARMS,
    CONTINUE_FAMILIES,
    COUNT,
    COUNTERS,
    DECIDE,
    DISTANCE,
    FEATURES,
    FILTERS,
    GRAPH_COUNTERS,
    GROUPS,
    TURNOVER,
    blocks,
    choose,
    cpu_for,
    decision,
    masks,
    ordered,
    reader_order,
    role,
)
from serving import request
from sessions import pin
from support import check_plan, valid

HERE = Path(__file__).resolve().parent
KEYS = ("output", "returned_count", "request_ns", "construction_ns", "sql_fetch_decode_ns")
LEGACY = {}


def load_programs(folder=HERE):
    manifest = json.loads((folder / "compiled-programs.json").read_text())
    entries = {r["arm"]: r for r in manifest["bindings"]}
    require(
        set(entries) == {a for a in ARMS.values() if a is not None and a >= 20},
        "compiled binding pool changed",
    )
    for entry in entries.values():
        for f, plan in entry["observation_plan"].items():
            require(
                plan == masks(entry["policy"], f),
                "compiler mask differs from independently derived dependencies",
            )
    nominees = json.loads((folder / "nominees.json").read_text())["nominees"]
    require(
        [n["candidate_id"] for n in nominees] == ["candidate-7", "candidate-8"],
        "submitted nominee inventory changed",
    )
    for nominee, arm, matched in zip(nominees, (20, 21), (30, 31)):
        require(
            entries[arm]["policy"] == entries[matched]["policy"] == nominee["policy"]
            and entries[arm]["rule_hash"] == entries[matched]["rule_hash"] == nominee["rule_hash"]
            and not entries[arm]["force_continue"]
            and entries[matched]["force_continue"],
            "candidate or matched-control contract changed",
        )
    require(
        not entries[43]["policy"]["rules"] and not entries[43]["force_continue"],
        "empty control changed",
    )
    return entries


@contextmanager
def session(Backend, args):
    b = Backend(args.bundle, args.work)
    b.state["source_manifest"]["settings"]["hnsw.ef_search"] = str(args.ef)
    try:
        c = b._connect()
        require(c.autocommit, "autocommit reader required")
        yield c
    finally:
        b.close()


@contextmanager
def bind(c, args, t, passing, arm):
    from psycopg import sql

    with c.transaction():
        c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        c.execute(sql.SQL("SET TRANSACTION SNAPSHOT {}").format(sql.Literal(args.snapshot)))
        c.execute("SET LOCAL max_parallel_workers_per_gather=0")
        c.execute("SET LOCAL idle_in_transaction_session_timeout=0")
        c.execute("SET LOCAL hnsw.ef_search=" + str(args.ef))
        c.execute("SET LOCAL hnsw.iterative_scan=off")
        if arm is not None:
            c.execute(
                "SELECT fannagent.study_attach('reviews','reviews_hnsw',%s,%s,%s)",
                (t, arm, passing),
            )
        yield c


def reserve(counter, op, args):
    cap = 200000 if args.phase == "timing" else 25000
    require(
        counter["total"] < cap and args.previous_attempts + counter["total"] < 225000,
        "fixed M5 attempt ceiling",
    )
    counter["total"] += 1
    counter[op] = counter.get(op, 0) + 1


def perform(c, q, counter, op, args):
    return request(c, q, lambda operation: reserve(counter, op, args), fixture=args.fixture)


def validate(result, q, eligible, truth):
    require(set(result) == set(KEYS), "serving metadata changed")
    require(
        result["returned_count"] == len(result["output"])
        and result["request_ns"] == result["construction_ns"] + result["sql_fetch_decode_ns"],
        "timer/count accounting differs",
    )
    require(
        result["request_ns"] > 0
        and result["construction_ns"] >= 0
        and result["sql_fetch_decode_ns"] > 0,
        "invalid timer",
    )
    return valid(result["output"], q, eligible, truth)


def offline(Backend, args, queries, eligible, prior, counter):
    truths = {}
    total_ns = 0
    with (args.output / "exact-reference.jsonl").open("x") as out:
        for t in FILTERS:
            cases = [q for q in queries if threshold(q) == t]
            with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), None):
                c.execute("SET LOCAL enable_seqscan=on")
                c.execute("SET LOCAL enable_indexscan=off")
                c.execute("SET LOCAL enable_indexonlyscan=off")
                c.execute("SET LOCAL enable_bitmapscan=off")
                if not args.fixture:
                    write(args.output / f"exact-plan-{t}.json", check_plan(c, cases[0], exact=True))
                for q in cases:
                    reserve(counter, "reference_exact", args)
                    truth, ns = search(c, q, exact=True, fixture=args.fixture)
                    if prior is not None:
                        require(
                            matches(truth, prior[q["id"]]["exact"]),
                            "fresh exact reference differs from frozen development truth",
                        )
                    truths[q["id"]] = truth
                    total_ns += ns
                    emit(
                        out, {"id": q["id"], "filter": t, "output": truth, "reference_query_ns": ns}
                    )
            out.flush()
            print(
                json.dumps(
                    {
                        "phase": args.phase + "_offline_exact",
                        "filter": t,
                        "attempts": counter["total"],
                    }
                ),
                flush=True,
            )
    write(
        args.output / "offline-reference-cost.json",
        {
            "queries": len(queries),
            "query_ns": total_ns,
            "included_in_serving": False,
            "exact_readers_closed_before_approximate": True,
        },
    )
    return truths


def emit(handle, value):
    handle.write(json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n")


def filter_name(t):
    return "unfiltered" if t < 0 else "votes" + str(t)


def expected_program(entry, t, observations, output, audit):
    name = filter_name(t)
    wanted = choose(entry, name, observations)
    plan = masks(entry["policy"], name)
    frames = [
        o
        for o in observations
        if plan[str(o["checkpoint"])] and (not wanted or o["checkpoint"] <= wanted)
    ]
    require(
        audit["arm"] == entry["arm"] and len(audit["frames"]) == len(frames),
        "incorrect mask frame coverage",
    )
    for frame, canonical in zip(audit["frames"], frames, strict=True):
        cp = canonical["checkpoint"]
        mask = plan[str(cp)]
        require(
            frame["checkpoint"] == cp and frame["mask"] == mask, "wrong checkpoint/dependency mask"
        )
        require(
            frame["decision"]
            == (bool(mask & DECIDE) and decision(entry["policy"], name, cp, canonical)),
            "nullable/partial decision differs",
        )
        for feature in FEATURES:
            needed = mask & (
                COUNT
                if feature == "qualifying_count"
                else TURNOVER
                if feature == "top10_new_since_previous"
                else DISTANCE
            )
            value = frame[feature]
            target = canonical[feature] if needed else None
            require(
                value is None
                if target is None
                else value is not None and abs(value - target) <= 1e-12,
                "masked feature or availability differs",
            )
    return wanted


def quality(Backend, args, queries, eligible, truths, expected, counter, entries):
    cache = {}
    summary = {}
    prefixes = 0
    partial = 0
    names = tuple(n for n in ARMS if n != "native640")
    with (args.output / "quality.jsonl").open("x") as out:
        for t in FILTERS:
            cases = [q for q in queries if threshold(q) == t]
            passing = len(eligible[t])
            with session(Backend, args) as c:
                with bind(c, args, t, passing, None):
                    if not args.fixture:
                        write(args.output / f"ann-plan-{t}.json", check_plan(c, cases[0]))
                for j, q in enumerate(cases):
                    qid = q["id"]
                    with bind(c, args, t, passing, None):
                        c.execute("SELECT fannagent.v2_audit_enable(false)")
                        native = perform(c, q, counter, "native_bridge", args)
                    native_score = validate(native, q, eligible[t], truths[qid])
                    if expected is not None:
                        require(
                            matches(
                                native["output"], expected[qid]["results"]["native640"]["output"]
                            ),
                            "new-module native bridge differs",
                        )
                    with bind(c, args, t, passing, 0):
                        reserve(counter, "capture", args)
                        cap = capture(c, q, f"M5-{t}-{j}", fixture=args.fixture)
                        require(matches(cap["output"], native["output"]), "capture/native mismatch")
                        if expected is not None:

                            def strip(obs):
                                return [
                                    {k: v for k, v in o.items() if k != "collection_ns"}
                                    for o in obs
                                ]

                            require(
                                strip(cap["checkpoints"]) == strip(expected[qid]["checkpoints"]),
                                "canonical prefix differs from M0",
                            )
                        proofs = {}
                        for o in cap["checkpoints"]:
                            reserve(counter, "forced_prefix", args)
                            forced = capture(
                                c,
                                q,
                                f"M5-force-{t}-{j}-{o['checkpoint']}",
                                budget=o["budget"],
                                fixture=args.fixture,
                            )
                            output = forced["output"]
                            score = valid(output, q, eligible[t], truths[qid])
                            proofs[str(o["checkpoint"])] = {
                                "output": output,
                                "recall": score,
                                "returned_count": len(output),
                            }
                            if expected is not None:
                                old = expected[qid]["prefixes"][str(o["checkpoint"])]
                                require(
                                    matches(output, old["output"])
                                    and abs(score - old["recall"]) < 1e-12,
                                    "actual prefix differs from verified M1 label",
                                )
                            prefixes += 1
                            partial += o["qualifying_count"] < 10
                    results = {
                        "native640": {
                            **native,
                            "checkpoint": 0,
                            "recall": native_score,
                            "audit": None,
                        }
                    }
                    rotation = j % len(names)
                    sequence = names[rotation:] + names[:rotation]
                    for name in sequence:
                        arm = ARMS[name]
                        with bind(c, args, t, passing, arm):
                            c.execute("SELECT fannagent.v2_audit_enable(%s)", (arm >= 20,))
                            result = perform(c, q, counter, "quality_ann", args)
                            cp = c.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                            audit = (
                                json.loads(
                                    c.execute("SELECT fannagent.v2_audit_read()").fetchone()[0]
                                )
                                if arm >= 20
                                else None
                            )
                            c.execute("SELECT fannagent.v2_audit_enable(false)")
                        if arm >= 20:
                            wanted = expected_program(
                                entries[arm], t, cap["checkpoints"], result["output"], audit
                            )
                        elif arm == 6:
                            wanted = 0
                        else:
                            wanted = choose(entries[arm + 13], filter_name(t), cap["checkpoints"])
                        require(
                            cp == wanted
                            and matches(
                                result["output"],
                                proofs[str(wanted)]["output"] if wanted else native["output"],
                            ),
                            "first-stop/actual prefix output differs",
                        )
                        score = validate(result, q, eligible[t], truths[qid])
                        results[name] = {
                            **result,
                            "checkpoint": cp,
                            "recall": score,
                            "audit": audit,
                        }
                    with bind(c, args, t, passing, None):
                        after = perform(c, q, counter, "native_bridge", args)
                    require(
                        matches(after["output"], native["output"]),
                        "native contaminated after role changes",
                    )
                    row = {
                        "id": qid,
                        "filter": t,
                        "checkpoints": cap["checkpoints"],
                        "prefixes": proofs,
                        "results": results,
                        "native_after": after,
                        "native_predecessor": sequence[-1],
                    }
                    emit(out, row)
                    for name, r in results.items():
                        cache[qid, name] = r
            out.flush()
            summary[str(t)] = {"queries": len(cases), "families": len(ARMS)}
            print(
                json.dumps({"phase": "M5_quality", "filter": t, "attempts": counter["total"]}),
                flush=True,
            )
    summary["prefixes"] = {
        "reached": prefixes,
        "partial": partial,
        "all_actual_outputs_scored": True,
    }
    write(args.output / "quality-summary.json", summary)
    if not args.fixture:
        from m5_design import EXPECTED_STOPS

        loss = {
            name: sum(
                cache[q["id"], name]["recall"] < cache[q["id"], "native640"]["recall"] - 1e-12
                for q in queries
            )
            for name in ARMS
        }
        stops = {
            name: {
                str(t): sum(
                    bool(cache[q["id"], name]["checkpoint"]) for q in queries if threshold(q) == t
                )
                for t in FILTERS
            }
            for name in EXPECTED_STOPS
        }
        write(args.output / "nominee-quality-gate.json", {"loss_cases": loss, "stop_counts": stops})
        require(
            not any(loss.values()), "M5 quality regression: preserve result, do not time/promote"
        )
        require(
            all(
                stops[n][str(t)] == EXPECTED_STOPS[n].get(t, 0)
                for n in EXPECTED_STOPS
                for t in FILTERS
            ),
            "nominee stops differ from bound M4 evidence",
        )
    return cache, summary


def timing(Backend, args, queries, eligible, cache, counter):
    cpus = sorted(os.sched_getaffinity(0))
    require(len(cpus) == 4, "four allocated CPUs required")
    write(args.output / "allowed-cpus.json", cpus)
    setup = []
    with (
        (args.output / "timing.jsonl").open("x") as timed,
        (args.output / "warmup.jsonl").open("x") as warm,
        (args.output / "assignments.jsonl").open("x") as assignments,
    ):
        for ti, t in enumerate(FILTERS):
            cases = [q for q in queries if threshold(q) == t]
            for group, families in enumerate(GROUPS):
                started = perf_counter_ns()
                with ExitStack() as stack:
                    pool = {r: stack.enter_context(session(Backend, args)) for r in range(4)}
                    pids = {
                        r: c.execute("SELECT pg_backend_pid()").fetchone()[0]
                        for r, c in pool.items()
                    }
                    require(len(set(pids.values())) == 4, "distinct persistent readers required")
                    placement = {
                        r: pin(pid, cpu_for(r, ti, group, cpus), cpus) for r, pid in pids.items()
                    }
                    opened = perf_counter_ns() - started
                    for block, (cycle, rotation) in enumerate(blocks(group)):
                        cases_order = ordered(cases, group, rotation, cycle)
                        start = perf_counter_ns()
                        with ExitStack() as tx:
                            for r, c in pool.items():
                                name = role(group, r, rotation)
                                require(
                                    os.sched_getaffinity(pids[r]) == {placement[r]["cpu"]},
                                    "reader affinity changed",
                                )
                                tx.enter_context(bind(c, args, t, len(eligible[t]), ARMS[name]))
                                c.execute("SELECT fannagent.v2_audit_enable(false)")
                                require(
                                    c.execute(
                                        "SELECT pg_backend_pid(),"
                                        "current_setting('hnsw.ef_search'),"
                                        "current_setting('hnsw.iterative_scan')"
                                    ).fetchone()
                                    == (pids[r], str(args.ef), "off"),
                                    "reader settings/PID changed",
                                )
                                emit(
                                    assignments,
                                    {
                                        "filter": t,
                                        "group": group,
                                        "block": block,
                                        "cycle": cycle,
                                        "rotation": rotation,
                                        "reader": r,
                                        "family": name,
                                        **placement[r],
                                    },
                                )
                            attached = perf_counter_ns()
                            for r in range(4) if cycle == 0 else reversed(range(4)):
                                name = role(group, r, rotation)
                                for q in cases_order[:10]:
                                    result = perform(pool[r], q, counter, "warmup_ann", args)
                                    require(
                                        matches(result["output"], cache[q["id"], name]["output"]),
                                        "warmup output differs",
                                    )
                                    emit(
                                        warm,
                                        {
                                            "id": q["id"],
                                            "filter": t,
                                            "group": group,
                                            "block": block,
                                            "cycle": cycle,
                                            "rotation": rotation,
                                            "reader": r,
                                            "family": name,
                                            "pid": pids[r],
                                            "cpu": placement[r]["cpu"],
                                            **result,
                                        },
                                    )
                            warmed = perf_counter_ns()
                            for j, q in enumerate(cases_order):
                                forward = j if cycle == 0 else len(cases_order) - 1 - j
                                order = reader_order(forward, cycle, rotation, ti, group)
                                for position, r in enumerate(order):
                                    name = role(group, r, rotation)
                                    result = perform(pool[r], q, counter, "timed_ann", args)
                                    require(
                                        matches(result["output"], cache[q["id"], name]["output"]),
                                        "timed output differs",
                                    )
                                    emit(
                                        timed,
                                        {
                                            "id": q["id"],
                                            "filter": t,
                                            "group": group,
                                            "block": block,
                                            "cycle": cycle,
                                            "rotation": rotation,
                                            "reader": r,
                                            "family": name,
                                            "pid": pids[r],
                                            "cpu": placement[r]["cpu"],
                                            "order": order,
                                            "position": position,
                                            "predecessor": order[position - 1]
                                            if position
                                            else None,
                                            **result,
                                        },
                                    )
                            closing = perf_counter_ns()
                        closed = perf_counter_ns() - closing
                        for r in pool:
                            require(
                                os.sched_getaffinity(pids[r]) == {placement[r]["cpu"]},
                                "reader affinity changed during block",
                            )
                        setup.append(
                            {
                                "filter": t,
                                "group": group,
                                "block": block,
                                "open_ns": opened if block == 0 else 0,
                                "bind_ns": attached - start,
                                "warmup_ns": warmed - attached,
                                "close_ns": closed,
                                "warmups": 4 * min(10, len(cases_order)),
                            }
                        )
                        for handle in (timed, warm, assignments):
                            handle.flush()
                        print(
                            json.dumps(
                                {
                                    "phase": "M5_serving_timing",
                                    "filter": t,
                                    "group": group,
                                    "block": block,
                                    "attempts": counter["total"],
                                }
                            ),
                            flush=True,
                        )
    write(args.output / "setup.json", setup)


def work(Backend, args, queries, eligible, truths, cache, counter):
    cpus = sorted(os.sched_getaffinity(0))
    require(len(cpus) == 4, "four allocated CPUs required")
    write(args.output / "allowed-cpus.json", cpus)
    summary = {}
    with (args.output / "work.jsonl").open("x") as out:
        for ti, t in enumerate(FILTERS):
            cases = [q for q in queries if threshold(q) == t]
            counts_cache = {}
            with session(Backend, args) as c:
                pid = c.execute("SELECT pg_backend_pid()").fetchone()[0]
                cpu = cpus[ti % 4]
                pin(pid, cpu, cpus)
                for name, arm in ARMS.items():
                    with bind(c, args, t, len(eligible[t]), arm):
                        c.execute("SELECT fannagent.v2_audit_enable(false)")
                        for q in cases:
                            c.execute("SELECT fannagent.diagnostic_reset()")
                            result = perform(c, q, counter, "work_ann", args)
                            counts = json.loads(
                                c.execute("SELECT fannagent.diagnostic_read()").fetchone()[0]
                            )
                            cp = (
                                0
                                if arm is None
                                else c.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                            )
                            target = cache[q["id"], name]
                            score = validate(result, q, eligible[t], truths[q["id"]])
                            require(
                                cp == target["checkpoint"]
                                and matches(result["output"], target["output"])
                                and abs(score - target["recall"]) < 1e-12,
                                "observer/output parity differs",
                            )
                            require(
                                counts["pid"] == pid
                                and counts["start_cpu"] == counts["end_cpu"] == cpu
                                and os.sched_getaffinity(pid) == {cpu},
                                "work CPU/PID differs",
                            )
                            require(
                                set(counts) == set(COUNTERS) | {"pid", "start_cpu", "end_cpu"}
                                and all(
                                    type(counts[k]) is int and counts[k] >= 0 for k in COUNTERS
                                ),
                                "work counter schema differs",
                            )
                            require(
                                counts["vector_calls"] > 0
                                and counts["layer0_queue_pops"] > 0
                                and counts["feature_passes"] <= 3,
                                "work counter bounds differ",
                            )
                            if arm is not None and arm >= 20:
                                expected_passes = sum(
                                    bool(f["mask"] & COUNT) for f in target["audit"]["frames"]
                                )
                                require(
                                    counts["feature_passes"] == expected_passes,
                                    "unneeded or missing heap feature passes",
                                )
                                if expected_passes == 0:
                                    require(
                                        counts["membership_probes"] == 0,
                                        "unrequested membership feature work",
                                    )
                            if name in ("native640", "empty", "decision_continue"):
                                require(
                                    counts["feature_passes"] == counts["membership_probes"] == 0,
                                    "no-observation path performed heap work",
                                )
                            counts_cache[q["id"], name] = counts
                            if (
                                name == "native640"
                                and getattr(args, "native_work", None) is not None
                            ):
                                require(
                                    all(
                                        counts[k] == args.native_work[q["id"]][k]
                                        for k in GRAPH_COUNTERS
                                    ),
                                    "new-module native graph work differs from verified M0",
                                )
                            if name in CONTINUE_FAMILIES:
                                require(
                                    all(
                                        counts[k] == counts_cache[q["id"], "native640"][k]
                                        for k in GRAPH_COUNTERS
                                    ),
                                    "continue-only/native graph work differs",
                                )
                            emit(
                                out,
                                {
                                    "id": q["id"],
                                    "filter": t,
                                    "family": name,
                                    "checkpoint": cp,
                                    "recall": score,
                                    "counts": counts,
                                    **result,
                                },
                            )
            out.flush()
            summary[str(t)] = {
                "queries": len(cases),
                "families": len(ARMS),
                "all_continue_graph_work_matches_native": True,
            }
            print(
                json.dumps(
                    {"phase": "M5_separate_work", "filter": t, "attempts": counter["total"]}
                ),
                flush=True,
            )
    write(args.output / "work-summary.json", summary)
    return summary
