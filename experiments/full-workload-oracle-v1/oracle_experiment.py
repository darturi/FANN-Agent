"""Exhaustive measured prefix acquisition, frozen choices, then independent timing."""

import json
import os
from contextlib import ExitStack
from time import perf_counter_ns

from common import capture, matches, sha, threshold, write
from oracle_design import (
    FAMILIES,
    FILTERS,
    MAX_ATTEMPTS,
    MAX_CHECKPOINTS,
    ordered,
    prefix_chain,
    prefix_signature,
    qualifies,
    reader_order,
    require,
    validate_output,
)
from serving import request
from sessions import bind, pin, session
from support import check_plan


def emit(handle, row):
    handle.write(json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n")


def reserve(counter, operation, args):
    require(counter["total"] < MAX_ATTEMPTS, "oracle attempt cap reached; preserve partial result")
    counter["total"] += 1
    counter[operation] += 1
    # Reserve every attempt durably, including one interrupted before its result.
    ledger = args.output / "attempts.json"
    temporary = ledger.with_suffix(".pending")
    with temporary.open("w") as handle:
        json.dump(dict(counter), handle)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(ledger)


def perform(c, q, counter, operation, args):
    return request(c, q, lambda _: reserve(counter, operation, args), fixture=args.fixture)


def set_target(c, checkpoint):
    require(
        c.execute("SELECT fannagent.oracle_set(%s)", (checkpoint,)).fetchone() == (checkpoint,),
        "oracle target acknowledgement differs",
    )


def offline(Backend, args, queries, eligible, counter):
    from common import search

    truths = {}
    with (args.output / "exact-reference.jsonl").open("x") as out:
        for t in FILTERS:
            cases = [q for q in queries if threshold(q) == t]
            with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), None):
                for setting in ("enable_indexscan", "enable_indexonlyscan", "enable_bitmapscan"):
                    c.execute("SET LOCAL " + setting + "=off")
                c.execute("SET LOCAL enable_seqscan=on")
                if not args.fixture:
                    write(args.output / f"exact-plan-{t}.json", check_plan(c, cases[0], exact=True))
                for q in cases:
                    reserve(counter, "offline_exact", args)
                    truth, elapsed = search(c, q, exact=True, fixture=args.fixture)
                    validate_output(truth[:10], eligible[t], truth)
                    truths[q["id"]] = truth
                    emit(out, {"id": q["id"], "filter": t, "output": truth, "query_ns": elapsed})
            out.flush()
            print(
                json.dumps({"phase": "offline_exact", "filter": t, "attempts": counter["total"]}),
                flush=True,
            )
    return truths


def acquire(Backend, args, queries, eligible, truths, counter):
    choices = {}
    with (
        (args.output / "prefixes.jsonl").open("x") as prefixes,
        (args.output / "quality.jsonl").open("x") as out,
        (args.output / "trajectories.jsonl").open("x") as trajectories,
    ):
        for t in FILTERS:
            cases = [q for q in queries if threshold(q) == t]
            passing = len(eligible[t])
            with session(Backend, args) as c:
                for j, q in enumerate(cases):
                    qid = q["id"]
                    with bind(c, args, t, passing, None):
                        if j == 0 and not args.fixture:
                            write(args.output / f"ann-plan-{t}.json", check_plan(c, q))
                        native = perform(c, q, counter, "native_quality", args)["output"]
                        prior = getattr(args, "prior_native", {}).get(qid)
                        if prior is not None:
                            require(
                                matches(native, prior),
                                "qualified original-module native bridge changed",
                            )
                    native_recall = validate_output(native, eligible[t], truths[qid])
                    chosen, chosen_output, chosen_score = 0, native, native_recall
                    with bind(c, args, t, passing, 0):
                        reserve(counter, "canonical_capture", args)
                        cap = capture(
                            c, q, f"oracle-{t}-{j}", budget=(1 << 63) - 1, fixture=args.fixture
                        )
                        require(
                            matches(native, cap["output"]),
                            "canonical capture changed native output",
                        )
                        states = cap["states"]
                        count = cap["telemetry"]["checkpoint_count"]
                        require(
                            set(states) == set(range(1, count + 1)) and count <= MAX_CHECKPOINTS,
                            "incomplete or oversized checkpoint trajectory",
                        )
                        signature = prefix_signature(states)
                        chain = prefix_chain(signature)
                        targets = [s["target"] for s in signature]
                        require(targets == sorted(set(targets)), "nonincreasing checkpoint targets")
                        emit(
                            trajectories,
                            {
                                "id": qid,
                                "count": count,
                                "targets": targets,
                                "prefix_sha256": chain,
                                "output": cap["output"],
                            },
                        )
                        attempts = []
                        # Every reached ordinal is tested in order. No binary search,
                        # interpolation, or assumption of monotone recall is made.
                        for cp in range(1, count + 1):
                            reserve(counter, "forced_prefix", args)
                            forced = capture(
                                c,
                                q,
                                f"force-{t}-{j}-{cp}",
                                budget=targets[cp - 1],
                                fixture=args.fixture,
                            )
                            require(
                                forced["telemetry"]["stop_reason"] == "fixed_budget_stop"
                                and forced["telemetry"]["checkpoint_count"] == cp
                                and prefix_signature(forced["states"]) == signature[:cp],
                                "forced execution prefix changed",
                            )
                            output = forced["output"]
                            score = validate_output(output, eligible[t], truths[qid])
                            safe = qualifies(output, score, native, native_recall)
                            row = {
                                "id": qid,
                                "filter": t,
                                "checkpoint": cp,
                                "target": targets[cp - 1],
                                "output": output,
                                "recall": score,
                                "qualifies": safe,
                                "prefix_verified": True,
                                "prefix_sha256": prefix_chain(prefix_signature(forced["states"]))[
                                    -1
                                ],
                            }
                            emit(prefixes, row)
                            attempts.append(cp)
                            if safe:
                                chosen, chosen_output, chosen_score = cp, output, score
                                break
                    require(
                        attempts == list(range(1, (chosen or count) + 1)),
                        "earliest stop not proven",
                    )
                    with bind(c, args, t, passing, 10):
                        set_target(c, chosen)
                        replay = perform(c, q, counter, "oracle_quality", args)["output"]
                        stopped = c.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                        require(
                            stopped == chosen and matches(replay, chosen_output),
                            "oracle replay differs",
                        )
                    with bind(c, args, t, passing, 11):
                        set_target(c, chosen)
                        matched = perform(c, q, counter, "matched_quality", args)["output"]
                        require(
                            c.execute("SELECT fannagent.confirm_last()").fetchone()[0] == 0
                            and matches(matched, native),
                            "matched continue changed native",
                        )
                    with bind(c, args, t, passing, None):
                        after = perform(c, q, counter, "native_quality", args)["output"]
                        require(matches(after, native), "native before/after bridge changed")
                    record = {
                        "id": qid,
                        "filter": t,
                        "role": args.roles[qid],
                        "native": native,
                        "native_recall": native_recall,
                        "checkpoint": chosen,
                        "output": chosen_output,
                        "recall": chosen_score,
                        "native_checkpoint_count": count,
                        "tested_count": len(attempts),
                    }
                    choices[qid] = record
                    emit(out, record)
                    if j % 25 == 0:
                        out.flush()
                        prefixes.flush()
                        trajectories.flush()
                        print(
                            json.dumps(
                                {
                                    "phase": "acquisition",
                                    "filter": t,
                                    "cases_done": j + 1,
                                    "cases_total": len(cases),
                                    "attempts": counter["total"],
                                }
                            ),
                            flush=True,
                        )
    # Seal before ANY oracle timing; timings never influence checkpoint choices.
    write(
        args.output / "oracle-freeze.json",
        {
            "quality_sha256": sha(args.output / "quality.jsonl"),
            "prefixes_sha256": sha(args.output / "prefixes.jsonl"),
            "trajectories_sha256": sha(args.output / "trajectories.jsonl"),
            "cases": len(choices),
            "timing_started": False,
            "criterion": (
                "earliest reached64-distance checkpoint preserving native recall and result count"
            ),
        },
    )
    return choices


def timing(Backend, args, queries, eligible, choices, counter):
    allowed = sorted(os.sched_getaffinity(0))[:4]
    require(len(allowed) == 4, "four allocated cores required")
    write(args.output / "allowed-cpus.json", allowed)
    with (
        (args.output / "timing.jsonl").open("x") as out,
        (args.output / "reader-setup.jsonl").open("x") as setup,
    ):
        for ti, t in enumerate(FILTERS):
            cases = [q for q in queries if threshold(q) == t]
            passing = len(eligible[t])
            with ExitStack() as stack:
                readers = [stack.enter_context(session(Backend, args)) for _ in range(4)]
                pids = [c.execute("SELECT pg_backend_pid()").fetchone()[0] for c in readers]
                for r, pid in enumerate(pids):
                    emit(
                        setup,
                        {"filter": t, "reader": r, **pin(pid, allowed[(r + ti) % 4], allowed)},
                    )
                for cycle in (0, 1):
                    for rotation in range(4) if not cycle else reversed(range(4)):
                        order = ordered(cases, rotation, cycle)
                        with ExitStack() as transactions:
                            families = [FAMILIES[(r + rotation) % 4] for r in range(4)]
                            for r, c in enumerate(readers):
                                arm = {"native": None, "oracle": 10, "matched": 11, "empty": 43}[
                                    families[r]
                                ]
                                begin = perf_counter_ns()
                                transactions.enter_context(bind(c, args, t, passing, arm))
                                emit(
                                    setup,
                                    {
                                        "filter": t,
                                        "reader": r,
                                        "cycle": cycle,
                                        "rotation": rotation,
                                        "family": families[r],
                                        "bind_ns": perf_counter_ns() - begin,
                                    },
                                )
                                for q in order[: min(10, len(order))]:
                                    if families[r] in ("oracle", "matched"):
                                        set_target(c, choices[q["id"]]["checkpoint"])
                                    result = perform(c, q, counter, "warmup_ann", args)
                                    want = choices[q["id"]][
                                        "output" if families[r] == "oracle" else "native"
                                    ]
                                    require(
                                        matches(result["output"], want), "warmup result differs"
                                    )
                            for position, q in enumerate(order):
                                for r in reader_order(position, rotation, cycle, ti):
                                    family, c = families[r], readers[r]
                                    routing_start = perf_counter_ns()
                                    if family in ("oracle", "matched"):
                                        set_target(c, choices[q["id"]]["checkpoint"])
                                    routing_ns = perf_counter_ns() - routing_start
                                    result = perform(c, q, counter, "timed_ann", args)
                                    want = choices[q["id"]][
                                        "output" if family == "oracle" else "native"
                                    ]
                                    require(matches(result["output"], want), "timed output changed")
                                    emit(
                                        out,
                                        {
                                            "id": q["id"],
                                            "filter": t,
                                            "family": family,
                                            "reader": r,
                                            "pid": pids[r],
                                            "cpu": allowed[(r + ti) % 4],
                                            "cycle": cycle,
                                            "rotation": rotation,
                                            "position": position,
                                            "oracle_routing_ns_outside_primary": routing_ns,
                                            **result,
                                        },
                                    )
                        out.flush()
                        print(
                            json.dumps(
                                {
                                    "phase": "timing",
                                    "filter": t,
                                    "cycle": cycle,
                                    "rotation": rotation,
                                    "attempts": counter["total"],
                                }
                            ),
                            flush=True,
                        )
