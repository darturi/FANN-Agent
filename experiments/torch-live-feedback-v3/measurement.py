"""Actual compiled v3 quality and balanced request timing on frozen graph inputs."""

import hashlib
import json
import os
from contextlib import ExitStack

import oracle_experiment
from broad_contract import compile_graph
from broad_support import replay_graph, verify_audit
from common import matches, threshold, write
from oracle_design import FILTERS, require, validate_output
from oracle_experiment import emit, perform, set_target
from sessions import bind, pin, session
from support import check_plan


class Ledger:
    """Reserve durable 32-query windows; unused slots remain charged."""

    def __init__(self, batch, prior, limit):
        self.batch, self.prior, self.limit = batch, prior, limit
        self.reserved = 0

    def reserve(self, counter, operation):
        if counter["total"] >= self.reserved:
            next_end = min(self.reserved + 32, self.limit - self.prior)
            require(counter["total"] < next_end, "episode native attempt limit reached")
            self.reserved = next_end
            write(
                self.batch / "attempts.json",
                {
                    "total": self.reserved,
                    "actual": counter["total"],
                    "prior": self.prior,
                    "limit": self.limit,
                    "window": 32,
                },
            )
        counter["total"] += 1
        counter[operation] += 1

    def finish(self, counter):
        write(
            self.batch / "attempts.json",
            {
                "total": self.reserved,
                "actual": counter["total"],
                "prior": self.prior,
                "limit": self.limit,
                "operations": dict(counter),
                "window": 32,
            },
        )


def reserve(counter, operation, args):
    args.ledger.reserve(counter, operation)


oracle_experiment.reserve = reserve


def quality(Backend, args, queries, eligible, truths, cases, entries, known):
    graphs = {arm: compile_graph(e["policy"]) for arm, e in entries.items()}
    expected, records, losses = {}, [], {name: 0 for name in args.arms}
    forced = {}
    with (args.output / "quality.jsonl").open("x") as output:
        for t in FILTERS:
            subset = [q for q in queries if threshold(q) == t]
            if not subset:
                continue
            for family, arm in args.arms.items():
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), arm):
                    if family == "native640":
                        write(args.output / f"ann-plan-{t}.json", check_plan(c, subset[0]))
                    if arm is not None:
                        c.execute("SELECT fannagent.v3_audit_enable(true)")
                    for q in subset:
                        row = cases[q["id"]]
                        if arm is None:
                            cp, trace = 0, []
                        else:
                            cp, trace = replay_graph(
                                graphs[arm],
                                row,
                                force_continue=entries[arm]["force_continue"],
                                trace=True,
                            )
                        result = perform(c, q, args.counter, "quality_ann", args)
                        actual_cp = (
                            c.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                            if arm is not None
                            else 0
                        )
                        require(actual_cp == cp, "native/reference decision differs")
                        if arm is not None:
                            audit = json.loads(
                                c.execute("SELECT fannagent.v3_audit_read()").fetchone()[0]
                            )
                            verify_audit(trace, audit)
                        else:
                            audit = None
                        if cp == 0:
                            wanted = row["native"]
                        elif (q["id"], cp) in known:
                            wanted = known[q["id"], cp]
                        elif (q["id"], cp) in forced:
                            wanted = forced[q["id"], cp]
                        else:
                            with (
                                session(Backend, args) as ref,
                                bind(ref, args, t, len(eligible[t]), 10),
                            ):
                                set_target(ref, cp)
                                wanted = perform(ref, q, args.counter, "forced_prefix", args)[
                                    "output"
                                ]
                            forced[q["id"], cp] = wanted
                        require(
                            matches(result["output"], wanted), "canonical prefix output differs"
                        )
                        score = validate_output(result["output"], eligible[t], truths[q["id"]])
                        loss = score + 1e-12 < row["native_recall"]
                        losses[family] += loss
                        # Final transfer failures are retained and timed for diagnosis.
                        if (
                            family == "oracle_full"
                            or family == "oracle_test"
                            and row["role"] == "test"
                        ):
                            require(not loss, "saved oracle failed intended-cohort quality")
                        expected[q["id"], family] = wanted
                        record = {
                            "id": q["id"],
                            "filter": t,
                            "role": row["role"],
                            "family": family,
                            "checkpoint": cp,
                            "recall": score,
                            "native_recall": row["native_recall"],
                            "native_count": len(row["native"]),
                            "audit": audit,
                            **result,
                        }
                        emit(output, record)
                        records.append(record)
                output.flush()
                print(
                    json.dumps(
                        {
                            "phase": "quality",
                            "filter": t,
                            "family": family,
                            "actual_queries": args.counter["total"],
                            "losses": losses[family],
                        }
                    ),
                    flush=True,
                )
    return expected, records, losses


def family_for(families, rotation, reader, ti):
    return families[(rotation + reader + ti) % len(families)]


def timing(Backend, args, queries, eligible, expected):
    families = tuple(args.arms)
    allowed = sorted(os.sched_getaffinity(0))[:4]
    require(len(allowed) == 4, "four pinned CPUs required")
    write(args.output / "allowed-cpus.json", allowed)
    rotations = len(families)
    with (
        (args.output / "timing.jsonl").open("x") as output,
        (args.output / "reader-setup.jsonl").open("x") as setup,
    ):
        for ti, t in enumerate(FILTERS):
            subset = [q for q in queries if threshold(q) == t]
            if not subset:
                continue
            with ExitStack() as stack:
                readers = [stack.enter_context(session(Backend, args)) for _ in range(4)]
                pids = [c.execute("SELECT pg_backend_pid()").fetchone()[0] for c in readers]
                for ri, c in enumerate(readers):
                    emit(
                        setup,
                        {
                            "filter": t,
                            "reader": ri,
                            **pin(pids[ri], allowed[(ri + ti) % 4], allowed),
                        },
                    )
                    c.execute("SELECT fannagent.v3_audit_enable(false)")
                for rotation in range(rotations):
                    mirror = rotation >= rotations // 2
                    seed = rotation % max(1, rotations // 2)
                    order = sorted(
                        subset,
                        key=lambda q: hashlib.sha256(
                            f"live-v3:{seed}:{q['id'].rsplit('-', 1)[0]}".encode()
                        ).digest(),
                        reverse=mirror,
                    )
                    chosen = [family_for(families, rotation, ri, ti) for ri in range(4)]
                    with ExitStack() as transactions:
                        for ri, c in enumerate(readers):
                            family = chosen[ri]
                            transactions.enter_context(
                                bind(c, args, t, len(eligible[t]), args.arms[family])
                            )
                            for q in order[:2]:
                                result = perform(c, q, args.counter, "warmup_ann", args)
                                require(
                                    matches(result["output"], expected[q["id"], family]),
                                    "warmup output differs",
                                )
                        for position, q in enumerate(order):
                            offset = (position + rotation + ti) % 4
                            rorder = [(r + offset) % 4 for r in (0, 1, 3, 2)]
                            if mirror:
                                rorder.reverse()
                            for ri in rorder:
                                family = chosen[ri]
                                result = perform(readers[ri], q, args.counter, "timed_ann", args)
                                require(
                                    matches(result["output"], expected[q["id"], family]),
                                    "timed output differs",
                                )
                                emit(
                                    output,
                                    {
                                        "id": q["id"],
                                        "filter": t,
                                        "family": family,
                                        "rotation": rotation,
                                        "reader": ri,
                                        "position": position,
                                        "pid": pids[ri],
                                        "cpu": allowed[(ri + ti) % 4],
                                        **result,
                                    },
                                )
                    output.flush()
                    print(
                        json.dumps(
                            {
                                "phase": "timing",
                                "filter": t,
                                "rotation": rotation,
                                "actual_queries": args.counter["total"],
                            }
                        ),
                        flush=True,
                    )
