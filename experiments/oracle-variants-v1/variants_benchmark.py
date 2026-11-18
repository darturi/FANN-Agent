"""Measure free hindsight actions and actual compiler-emitted feasible policies."""

import hashlib
import json
import os
import shutil
from contextlib import ExitStack
from pathlib import Path
from time import perf_counter_ns

from common import matches, sha, threshold, write
from m5_design import choose
from m5_experiment import expected_program
from oracle_design import FILTERS, require, validate_output
from oracle_experiment import emit, perform, set_target
from sessions import bind, pin, session
from support import check_plan
from timing_followup import WindowLedger

HERE = Path(__file__).resolve().parent
FAMILIES = (
    "native640",
    "oracle_ideal",
    "oracle_constrained",
    "oracle_feasible_full",
    "oracle_feasible_test",
    "matched_full",
    "matched_test",
    "empty",
)
ARMS = dict(zip(FAMILIES, (None, 10, 10, 20, 21, 30, 31, 43), strict=True))
SEED = "oracle-variants-paired-20261118-v1"
POINTS = (16, 32, 64)


def reserve(counter, operation, args):
    args.window_ledger.reserve(counter, operation)


def read_rows(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def expected(row, family, entries):
    if family == "oracle_ideal":
        return row["ideal"]["checkpoint"], row["ideal"]["output"]
    if family == "oracle_constrained":
        cp = next(
            (
                cp
                for cp in POINTS
                if str(cp) in row["actions"]
                and row["actions"][str(cp)]["recall"] + 1e-12 >= row["native_recall"]
            ),
            0,
        )
        return cp, row["actions"][str(cp)]["output"] if cp else row["native"]
    if family in ("native640", "empty", "matched_full", "matched_test"):
        return 0, row["native"]
    observations = [row["observations"][str(cp)] for cp in POINTS if str(cp) in row["observations"]]
    name = "unfiltered" if row["filter"] < 0 else "votes" + str(row["filter"])
    cp = choose(entries[ARMS[family]], name, observations)
    return cp, row["actions"][str(cp)]["output"] if cp else row["native"]


def quality_required(row, family):
    return family != "oracle_feasible_test" or row["role"] == "test"


def offline(Backend, args, queries, eligible, counter):
    del Backend
    cases = list(read_rows(HERE / "source-cases.jsonl"))
    freeze = json.loads((HERE / "source-capture-freeze.json").read_text())
    require(
        sha(HERE / "source-cases.jsonl") == freeze["cases_sha256"]
        and freeze["cases"] == len(cases) == len(queries),
        "capture freeze differs",
    )
    args.cases = {r["id"]: r for r in cases}
    require(set(args.cases) == {q["id"] for q in queries}, "source case coverage differs")
    old_eligible = {
        int(t): set(ids)
        for t, ids in json.loads((HERE / "source-eligibility.json").read_text()).items()
    }
    require(eligible == old_eligible, "fresh eligibility differs")
    args.entries = {
        r["arm"]: r for r in json.loads((HERE / "compiled-programs.json").read_text())["bindings"]
    }
    require(set(args.entries) == {20, 21, 30, 31, 43}, "compiled program pool differs")
    source_receipt = json.loads((HERE / "source-capture-receipt.json").read_text())
    budget = json.loads((HERE / "source-capture-budget.json").read_text())
    counter.update(source_receipt["searches"])
    counter["previous_unused_reserved"] = budget["charged_total"] - counter["total"]
    counter["total"] = budget["charged_total"]
    args.window_ledger = WindowLedger(args.output, counter["total"])
    for name in ("cases", "capture-freeze", "capture-receipt", "capture-budget"):
        shutil.copyfile(
            HERE / ("source-" + name + (".jsonl" if name == "cases" else ".json")),
            args.output / ("source-" + name + (".jsonl" if name == "cases" else ".json")),
        )
    shutil.copyfile(HERE / "source-exact-reference.jsonl", args.output / "exact-reference.jsonl")
    return {r["id"]: r["output"] for r in read_rows(HERE / "source-exact-reference.jsonl")}


def acquire(Backend, args, queries, eligible, truths, counter):
    """Qualify actual masks/decisions/answers on the fresh graph before timing."""
    with (args.output / "quality.jsonl").open("x") as output:
        for t in FILTERS:
            cases = [q for q in queries if threshold(q) == t]
            for family in FAMILIES:
                arm = ARMS[family]
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), arm):
                    if family == "native640" and not args.fixture:
                        write(args.output / f"ann-plan-{t}.json", check_plan(c, cases[0]))
                    if arm is not None and arm >= 20:
                        c.execute("SELECT fannagent.v2_audit_enable(true)")
                    for q in cases:
                        row = args.cases[q["id"]]
                        checkpoint, wanted = expected(row, family, args.entries)
                        if family in ("oracle_ideal", "oracle_constrained"):
                            set_target(c, checkpoint)
                        result = perform(c, q, counter, "quality_ann", args)
                        require(matches(result["output"], wanted), "compiled/frozen output differs")
                        actual_cp = (
                            c.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                            if arm is not None
                            else 0
                        )
                        require(actual_cp == checkpoint, "compiled/frozen checkpoint differs")
                        score = validate_output(result["output"], eligible[t], truths[q["id"]])
                        if quality_required(row, family):
                            require(
                                score + 1e-12 >= row["native_recall"],
                                "intended-cohort quality regression: " + family,
                            )
                        audit = None
                        if arm is not None and arm >= 20:
                            audit = json.loads(
                                c.execute("SELECT fannagent.v2_audit_read()").fetchone()[0]
                            )
                            observations = [
                                row["observations"][str(cp)]
                                for cp in POINTS
                                if str(cp) in row["observations"]
                            ]
                            expected_program(
                                args.entries[arm], t, observations, result["output"], audit
                            )
                        emit(
                            output,
                            {
                                "id": q["id"],
                                "filter": t,
                                "role": row["role"],
                                "family": family,
                                "checkpoint": actual_cp,
                                "recall": score,
                                "quality_required": quality_required(row, family),
                                "audit": audit,
                                **result,
                            },
                        )
            output.flush()
            print(
                json.dumps({"phase": "variant_quality", "filter": t, "attempts": counter["total"]}),
                flush=True,
            )
    write(
        args.output / "policy-freeze.json",
        {
            "compiled_programs_sha256": sha(HERE / "compiled-programs.json"),
            "source_cases_sha256": sha(HERE / "source-cases.jsonl"),
            "quality_sha256": sha(args.output / "quality.jsonl"),
            "cases": len(queries),
            "timing_started": False,
            "families": FAMILIES,
            "feasible_test_gate": "test cohort; transfer failures retained",
        },
    )
    return args.cases


def ordered(queries, rotation):
    order = sorted(
        queries,
        key=lambda q: hashlib.sha256(
            f"{SEED}:{rotation % 4}:{q['id'].rsplit('-', 1)[0]}".encode()
        ).digest(),
    )
    return order[::-1] if rotation >= 4 else order


def reader_order(position, rotation, ti):
    offset = (position + rotation + ti) % 8
    order = [(r + offset) % 8 for r in (0, 1, 3, 2, 4, 5, 7, 6)]
    return order[::-1] if rotation >= 4 else order


def schedule(queries, ti):
    for rotation in range(8):
        for position, q in enumerate(ordered(queries, rotation)):
            for reader in reader_order(position, rotation, ti):
                yield rotation, position, reader, FAMILIES[(reader + rotation) % 8], q


def timing(Backend, args, queries, eligible, choices, counter):
    del choices
    allowed = sorted(os.sched_getaffinity(0))[:4]
    require(len(allowed) == 4, "four physical CPUs required")
    write(args.output / "allowed-cpus.json", allowed)
    with (
        (args.output / "timing.jsonl").open("x") as output,
        (args.output / "reader-setup.jsonl").open("x") as setup,
    ):
        for ti, t in enumerate(FILTERS):
            cases = [q for q in queries if threshold(q) == t]
            with ExitStack() as stack:
                readers = [stack.enter_context(session(Backend, args)) for _ in range(8)]
                pids = [c.execute("SELECT pg_backend_pid()").fetchone()[0] for c in readers]
                for r, (pid, c) in enumerate(zip(pids, readers, strict=True)):
                    emit(
                        setup,
                        {"filter": t, "reader": r, **pin(pid, allowed[(r + ti) % 4], allowed)},
                    )
                    c.execute("SELECT fannagent.v2_audit_enable(false)")
                for rotation in range(8):
                    order = ordered(cases, rotation)
                    families = [FAMILIES[(r + rotation) % 8] for r in range(8)]
                    with ExitStack() as transactions:
                        for r, c in enumerate(readers):
                            transactions.enter_context(
                                bind(c, args, t, len(eligible[t]), ARMS[families[r]])
                            )
                            for q in order[: min(10, len(order))]:
                                row = args.cases[q["id"]]
                                checkpoint, want = expected(row, families[r], args.entries)
                                if families[r] in ("oracle_ideal", "oracle_constrained"):
                                    set_target(c, checkpoint)
                                result = perform(c, q, counter, "warmup_ann", args)
                                require(matches(result["output"], want), "warmup output differs")
                        for position, q in enumerate(order):
                            for r in reader_order(position, rotation, ti):
                                family, c = families[r], readers[r]
                                row = args.cases[q["id"]]
                                checkpoint, want = expected(row, family, args.entries)
                                started = perf_counter_ns()
                                if family in ("oracle_ideal", "oracle_constrained"):
                                    set_target(c, checkpoint)
                                routing = perf_counter_ns() - started
                                result = perform(c, q, counter, "timed_ann", args)
                                require(matches(result["output"], want), "timed answer differs")
                                emit(
                                    output,
                                    {
                                        "id": q["id"],
                                        "filter": t,
                                        "role": row["role"],
                                        "rotation": rotation,
                                        "position": position,
                                        "reader": r,
                                        "pid": pids[r],
                                        "cpu": allowed[(r + ti) % 4],
                                        "family": family,
                                        "checkpoint": checkpoint,
                                        "oracle_routing_ns_outside_primary": routing,
                                        **result,
                                    },
                                )
                    output.flush()
                    print(
                        json.dumps(
                            {
                                "phase": "variant_timing",
                                "filter": t,
                                "rotation": rotation,
                                "attempts": counter["total"],
                            }
                        ),
                        flush=True,
                    )
    args.window_ledger.finish(counter)
