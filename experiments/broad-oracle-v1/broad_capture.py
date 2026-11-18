"""Acquire causal v3 observations on the unchanged original graph."""

import json
import shutil
from pathlib import Path

from broad_contract import FEATURES, compile_graph
from broad_support import replay_graph, verify_audit
from common import capture, matches, sha, threshold, write
from oracle_design import FILTERS, prefix_chain, prefix_signature, require, validate_output
from oracle_experiment import emit, perform
from sessions import bind, session
from support import check_plan
from timing_followup import WindowLedger

HERE = Path(__file__).resolve().parent


def rows(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def reserve(counter, operation, args):
    args.window_ledger.reserve(counter, operation)


def offline(Backend, args, queries, eligible, counter):
    del Backend, counter
    expected = {
        int(t): set(ids)
        for t, ids in json.loads((HERE / "source-eligibility.json").read_text()).items()
    }
    require(expected == eligible, "fresh source eligibility differs")
    args.native_refs = {r["id"]: r for r in rows(HERE / "source-quality.jsonl")}
    args.trajectories = {r["id"]: r for r in rows(HERE / "source-trajectories.jsonl")}
    truths = {r["id"]: r["output"] for r in rows(HERE / "source-exact-reference.jsonl")}
    require(
        set(args.native_refs)
        == set(args.trajectories)
        == set(truths)
        == {q["id"] for q in queries},
        "source coverage differs",
    )
    args.capture_graph = compile_graph(
        json.loads((HERE / "capture-bindings.json").read_text())[0]["policy"]
    )
    shutil.copyfile(HERE / "source-exact-reference.jsonl", args.output / "exact-reference.jsonl")
    args.window_ledger = WindowLedger(args.output, 0)
    return truths


def acquire(Backend, args, queries, eligible, truths, counter):
    completed = 0
    frame_count = 0
    with (args.output / "cases.jsonl").open("x") as output:
        for t in FILTERS:
            with session(Backend, args) as c:
                for index, q in enumerate(q for q in queries if threshold(q) == t):
                    qid = q["id"]
                    with bind(c, args, t, len(eligible[t]), None):
                        if index == 0:
                            write(args.output / f"ann-plan-{t}.json", check_plan(c, q))
                        native = perform(c, q, counter, "native_bridge", args)["output"]
                    require(
                        matches(native, args.native_refs[qid]["native"]), "native bridge differs"
                    )
                    score = validate_output(native, eligible[t], truths[qid])
                    with bind(c, args, t, len(eligible[t]), 0):
                        reserve(counter, "canonical_capture", args)
                        canonical = capture(
                            c, q, f"broad-{t}-{index}", budget=(1 << 63) - 1, fixture=False
                        )
                    require(matches(canonical["output"], native), "canonical output differs")
                    chain = prefix_chain(prefix_signature(canonical["states"]))
                    require(
                        chain == args.trajectories[qid]["prefix_sha256"],
                        "original traversal differs",
                    )
                    with bind(c, args, t, len(eligible[t]), 80):
                        c.execute("SELECT fannagent.v3_audit_enable(true)")
                        result = perform(c, q, counter, "broad_capture", args)["output"]
                        audit = json.loads(
                            c.execute("SELECT fannagent.v3_audit_read()").fetchone()[0]
                        )
                    require(
                        matches(result, native) and not audit["exhausted"] and not audit["fault"],
                        "capture changed result or exceeded budget",
                    )
                    require(
                        [f["checkpoint"] for f in audit["frames"]]
                        == list(range(1, len(chain) + 1)),
                        "capture frame coverage differs",
                    )
                    for frame in audit["frames"]:
                        require(
                            frame["values"][1]
                            == canonical["states"][frame["checkpoint"]]["actual_layer0_distances"],
                            "causal work differs",
                        )
                    observed = {
                        f["checkpoint"]: dict(zip(FEATURES, f["values"], strict=True))
                        for f in audit["frames"]
                    }
                    for old in canonical["checkpoints"]:
                        for name in ("qualifying_count", "tenth_distance", "frontier_gap"):
                            a, b = old[name], observed[old["checkpoint"]][name]
                            require(
                                a == b or a is not None and b is not None and abs(a - b) < 1e-12,
                                "canonical feature differs",
                            )
                    row = {
                        "id": qid,
                        "filter": t,
                        "role": args.roles[qid],
                        "native": native,
                        "native_recall": score,
                        "native_layer0_work": canonical["telemetry"]["work_counters"][
                            "layer0_distance_evaluations"
                        ],
                        "frames": audit["frames"],
                        "canonical_checkpoint_count": len(chain),
                    }
                    cp, reference = replay_graph(
                        args.capture_graph, row, force_continue=True, trace=True
                    )
                    require(cp == 0, "forced capture stopped")
                    verify_audit(reference, audit)
                    with bind(c, args, t, len(eligible[t]), None):
                        after = perform(c, q, counter, "native_bridge", args)["output"]
                    require(matches(after, native), "native after bridge differs")
                    emit(output, row)
                    completed += 1
                    frame_count += len(audit["frames"])
                    if index % 25 == 0:
                        output.flush()
                        print(
                            json.dumps(
                                {
                                    "phase": "broad_capture",
                                    "cases": completed,
                                    "frames": frame_count,
                                    "attempts": counter["total"],
                                }
                            ),
                            flush=True,
                        )
    args.window_ledger.finish(counter)
    write(
        args.output / "capture-freeze.json",
        {
            "cases": completed,
            "frames": frame_count,
            "cases_sha256": sha(args.output / "cases.jsonl"),
            "full_causal_capture": True,
            "fresh_exact_queries": 0,
            "source_prefix_chains_verified": True,
            "reference_vm_verified": True,
        },
    )
    return {}


def timing(*args):
    pass
