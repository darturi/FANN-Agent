"""Fresh paired comparison of old oracles and ordinary v3 feasible policies."""

import hashlib
import json
import os
import shutil
from contextlib import ExitStack
from pathlib import Path
from time import perf_counter_ns

from broad_contract import compile_graph
from broad_support import replay_graph, verify_audit
from common import capture, matches, sha, threshold, write
from m5_experiment import expected_program
from oracle_design import FILTERS, prefix_chain, prefix_signature, require, validate_output
from oracle_experiment import emit, perform, set_target
from sessions import bind, pin, session
from support import check_plan
from timing_followup import WindowLedger
from variants_benchmark import expected as legacy_expected

HERE = Path(__file__).resolve().parent
FAMILIES = (
    "native640",
    "oracle_ideal",
    "oracle_constrained",
    "oracle_feasible_full",
    "oracle_feasible_test",
    "broad_full",
    "broad_test",
    "matched_broad_full",
    "matched_broad_test",
    "empty_v2",
    "empty_v3",
    "native_clone",
)
ARMS = dict(zip(FAMILIES, (None, 10, 10, 20, 21, 60, 61, 70, 71, 43, 85, None), strict=True))
SEED = "broad-oracle-paired-20261118-v1"
ROTATIONS = 12
READERS = 4


def rows(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def reserve(counter, operation, args):
    args.window_ledger.reserve(counter, operation)


def quality_required(row, family):
    return family not in ("oracle_feasible_test", "broad_test") or row["role"] == "test"


def family_for(rotation, reader, ti):
    return FAMILIES[(5 * rotation + 3 * reader + ti) % len(FAMILIES)]


def ordered(queries, rotation):
    order = sorted(
        queries,
        key=lambda q: hashlib.sha256(
            f"{SEED}:{rotation % 6}:{q['id'].rsplit('-', 1)[0]}".encode()
        ).digest(),
    )
    return order[::-1] if rotation >= 6 else order


def reader_order(position, rotation, ti):
    offset = (position + rotation + ti) % READERS
    order = [(r + offset) % READERS for r in (0, 1, 3, 2)]
    return order[::-1] if rotation >= 6 else order


def schedule(queries, ti):
    for rotation in range(ROTATIONS):
        for position, q in enumerate(ordered(queries, rotation)):
            for reader in reader_order(position, rotation, ti):
                yield rotation, position, reader, family_for(rotation, reader, ti), q


def offline(Backend, args, queries, eligible, counter):
    del Backend
    args.cases = {r["id"]: r for r in rows(HERE / "source-cases.jsonl")}
    args.legacy = {r["id"]: r for r in rows(HERE / "legacy-cases.jsonl")}
    args.chains = {r["id"]: r["prefix_sha256"] for r in rows(HERE / "source-trajectories.jsonl")}
    freeze = json.loads((HERE / "source-capture-freeze.json").read_text())
    require(freeze["cases_sha256"] == sha(HERE / "source-cases.jsonl"), "capture freeze differs")
    require(
        set(args.cases) == set(args.legacy) == {q["id"] for q in queries}, "case coverage differs"
    )
    require(
        eligible
        == {
            int(t): set(ids)
            for t, ids in json.loads((HERE / "source-eligibility.json").read_text()).items()
        },
        "eligibility differs",
    )
    args.entries = {
        r["arm"]: r for r in json.loads((HERE / "compiled-programs.json").read_text())["bindings"]
    }
    args.broad_entries = {
        r["arm"]: r for r in json.loads((HERE / "compiled-v3.json").read_text())["bindings"]
    }
    args.graphs = {arm: compile_graph(b["policy"]) for arm, b in args.broad_entries.items()}
    known = {r["id"]: r for r in rows(HERE / "full_workload-choices.jsonl")}
    test_known = {r["id"]: r for r in rows(HERE / "heldout_test-choices.jsonl")}
    args.expected = {}
    for qid, row in args.cases.items():
        old = args.legacy[qid]
        require(matches(row["native"], old["native"]), "legacy native differs")
        for family in FAMILIES:
            if family in ("broad_full", "broad_test"):
                cp, _ = replay_graph(args.graphs[ARMS[family]], row)
                source = known if family == "broad_full" else test_known
                if qid in source:
                    require(cp == source[qid]["checkpoint"], "compiled reference differs from fit")
                    wanted = source[qid]["output"]
                else:
                    wanted = row["native"] if cp == 0 else None
            elif family in (
                "native_clone",
                "empty_v2",
                "empty_v3",
                "matched_broad_full",
                "matched_broad_test",
            ):
                cp, wanted = 0, row["native"]
            else:
                cp, wanted = legacy_expected(old, family, args.entries)
            args.expected[qid, family] = (cp, wanted)
    source = json.loads((HERE / "source-capture-receipt.json").read_text())
    budget = json.loads((HERE / "source-capture-budget.json").read_text())
    counter.update(source["searches"])
    counter["previous_unused_reserved"] = budget["charged_total"] - counter["total"]
    counter["total"] = budget["charged_total"]
    args.window_ledger = WindowLedger(args.output, counter["total"])
    shutil.copyfile(HERE / "source-exact-reference.jsonl", args.output / "exact-reference.jsonl")
    return {r["id"]: r["output"] for r in rows(HERE / "source-exact-reference.jsonl")}


def acquire(Backend, args, queries, eligible, truths, counter):
    # Independently qualify the cheap frontier input at every checkpoint.
    checked = 0
    for t in FILTERS:
        with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), 0):
            for index, q in enumerate(q for q in queries if threshold(q) == t):
                reserve(counter, "frontier_qualification", args)
                canonical = capture(
                    c, q, f"frontier-{t}-{index}", budget=(1 << 63) - 1, fixture=False
                )
                row = args.cases[q["id"]]
                require(matches(canonical["output"], row["native"]), "qualification native differs")
                require(
                    prefix_chain(prefix_signature(canonical["states"])) == args.chains[q["id"]],
                    "qualification traversal differs",
                )
                require(
                    len(row["frames"]) == len(canonical["states"]), "qualification coverage differs"
                )
                for frame in row["frames"]:
                    old = canonical["states"][frame["checkpoint"]]
                    a, b = frame["values"][8], old["features"].get("frontier_distance_min")
                    require(
                        a == b or a is not None and b is not None and abs(a - b) < 1e-12,
                        "canonical frontier differs",
                    )
                    require(
                        frame["values"][1] == old["actual_layer0_distances"],
                        "qualification work differs",
                    )
                    checked += 1
        print(
            json.dumps(
                {
                    "phase": "frontier_qualification",
                    "filter": t,
                    "frames": checked,
                    "attempts": counter["total"],
                }
            ),
            flush=True,
        )
    write(
        args.output / "frontier-qualification.json",
        {
            "cases": len(queries),
            "frames": checked,
            "all_prefix_chains_match": True,
            "all_frontier_values_match": True,
            "all_work_values_match": True,
            "separate_canonical_execution": True,
        },
    )
    with (args.output / "quality.jsonl").open("x") as output:
        for t in FILTERS:
            cases = [q for q in queries if threshold(q) == t]
            for family in FAMILIES:
                arm = ARMS[family]
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), arm):
                    if family == "native640":
                        write(args.output / f"ann-plan-{t}.json", check_plan(c, cases[0]))
                    audit_version = (
                        3
                        if arm is not None and arm >= 60
                        else 2
                        if arm is not None and arm >= 20
                        else 0
                    )
                    if audit_version:
                        c.execute(f"SELECT fannagent.v{audit_version}_audit_enable(true)")
                    for q in cases:
                        row = args.cases[q["id"]]
                        cp, wanted = args.expected[q["id"], family]
                        if arm == 10:
                            set_target(c, cp)
                        result = perform(c, q, counter, "quality_ann", args)
                        actual_cp = (
                            c.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                            if arm is not None
                            else 0
                        )
                        require(actual_cp == cp, "native compiled checkpoint differs")
                        audit = (
                            json.loads(
                                c.execute(
                                    f"SELECT fannagent.v{audit_version}_audit_read()"
                                ).fetchone()[0]
                            )
                            if audit_version
                            else None
                        )
                        if wanted is None:
                            # Verify an unlabeled transfer prefix independently.
                            with (
                                session(Backend, args) as reference,
                                bind(reference, args, t, len(eligible[t]), 10),
                            ):
                                set_target(reference, cp)
                                wanted = perform(reference, q, counter, "transfer_prefix", args)[
                                    "output"
                                ]
                            args.expected[q["id"], family] = (cp, wanted)
                        require(matches(result["output"], wanted), "frozen/forced output differs")
                        if audit_version == 3:
                            predicted, expected = replay_graph(
                                args.graphs[arm],
                                row,
                                force_continue=args.broad_entries[arm]["force_continue"],
                                trace=True,
                            )
                            require(predicted == cp, "reference checkpoint differs")
                            verify_audit(expected, audit)
                        elif audit_version == 2:
                            old = args.legacy[q["id"]]
                            observations = [
                                old["observations"][str(p)]
                                for p in (16, 32, 64)
                                if str(p) in old["observations"]
                            ]
                            expected_program(
                                args.entries[arm], t, observations, result["output"], audit
                            )
                        score = validate_output(result["output"], eligible[t], truths[q["id"]])
                        required = quality_required(row, family)
                        require(
                            not required or score + 1e-12 >= row["native_recall"],
                            "intended cohort recall loss: " + family,
                        )
                        emit(
                            output,
                            {
                                "id": q["id"],
                                "filter": t,
                                "role": row["role"],
                                "family": family,
                                "checkpoint": cp,
                                "recall": score,
                                "quality_required": required,
                                "audit": audit,
                                **result,
                            },
                        )
                output.flush()
                print(
                    json.dumps(
                        {
                            "phase": "broad_quality",
                            "filter": t,
                            "family": family,
                            "attempts": counter["total"],
                        }
                    ),
                    flush=True,
                )
    write(
        args.output / "policy-freeze.json",
        {
            "cases": len(queries),
            "families": FAMILIES,
            "quality_sha256": sha(args.output / "quality.jsonl"),
            "compiled_v3_sha256": sha(HERE / "compiled-v3.json"),
            "compiled_v2_sha256": sha(HERE / "compiled-programs.json"),
            "source_cases_sha256": sha(HERE / "source-cases.jsonl"),
            "timing_started": False,
        },
    )
    return args.cases


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
                readers = [stack.enter_context(session(Backend, args)) for _ in range(READERS)]
                pids = [c.execute("SELECT pg_backend_pid()").fetchone()[0] for c in readers]
                for r, (pid, c) in enumerate(zip(pids, readers, strict=True)):
                    emit(
                        setup,
                        {"filter": t, "reader": r, **pin(pid, allowed[(r + ti) % 4], allowed)},
                    )
                    c.execute("SELECT fannagent.v2_audit_enable(false)")
                    c.execute("SELECT fannagent.v3_audit_enable(false)")
                for rotation in range(ROTATIONS):
                    order = ordered(cases, rotation)
                    families = [family_for(rotation, r, ti) for r in range(READERS)]
                    with ExitStack() as transactions:
                        for r, c in enumerate(readers):
                            family = families[r]
                            transactions.enter_context(
                                bind(c, args, t, len(eligible[t]), ARMS[family])
                            )
                            for q in order[:10]:
                                cp, wanted = args.expected[q["id"], family]
                                if ARMS[family] == 10:
                                    set_target(c, cp)
                                require(
                                    matches(
                                        perform(c, q, counter, "warmup_ann", args)["output"], wanted
                                    ),
                                    "warmup output differs",
                                )
                        for position, q in enumerate(order):
                            for r in reader_order(position, rotation, ti):
                                family, c = families[r], readers[r]
                                cp, wanted = args.expected[q["id"], family]
                                started = perf_counter_ns()
                                if ARMS[family] == 10:
                                    set_target(c, cp)
                                routing = perf_counter_ns() - started
                                result = perform(c, q, counter, "timed_ann", args)
                                require(matches(result["output"], wanted), "timed output differs")
                                emit(
                                    output,
                                    {
                                        "id": q["id"],
                                        "filter": t,
                                        "role": args.cases[q["id"]]["role"],
                                        "rotation": rotation,
                                        "position": position,
                                        "reader": r,
                                        "pid": pids[r],
                                        "cpu": allowed[(r + ti) % 4],
                                        "family": family,
                                        "checkpoint": cp,
                                        "oracle_routing_ns_outside_primary": routing,
                                        **result,
                                    },
                                )
                    output.flush()
                    print(
                        json.dumps(
                            {
                                "phase": "broad_timing",
                                "filter": t,
                                "rotation": rotation,
                                "attempts": counter["total"],
                            }
                        ),
                        flush=True,
                    )
    args.window_ledger.finish(counter)
