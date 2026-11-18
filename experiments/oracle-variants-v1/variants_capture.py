"""Capture actual legal actions and causal features for hindsight DSL fitting."""

import json
import shutil
from pathlib import Path

from common import capture, matches, sha, threshold, write
from oracle_design import FILTERS, prefix_chain, prefix_signature, require, validate_output
from oracle_experiment import emit, perform, set_target
from sessions import bind, session
from support import check_plan
from timing_followup import WindowLedger

HERE = Path(__file__).resolve().parent
POINTS = (16, 32, 64)


def reserve(counter, operation, args):
    args.window_ledger.reserve(counter, operation)


def rows(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def offline(Backend, args, queries, eligible, counter):
    del Backend, counter
    expected = {
        int(t): set(ids)
        for t, ids in json.loads((HERE / "source-eligibility.json").read_text()).items()
    }
    require(expected == eligible, "fresh source eligibility changed")
    args.native_refs = {r["id"]: r for r in rows(HERE / "source-quality.jsonl")}
    args.trajectories = {r["id"]: r for r in rows(HERE / "source-trajectories.jsonl")}
    args.ideals = {r["id"]: r for r in rows(HERE / "ideal-recall-choices.jsonl")}
    truths = {r["id"]: r["output"] for r in rows(HERE / "source-exact-reference.jsonl")}
    want = {q["id"] for q in queries}
    require(
        set(args.native_refs) == set(args.trajectories) == set(args.ideals) == set(truths) == want,
        "source query coverage differs",
    )
    shutil.copyfile(HERE / "source-exact-reference.jsonl", args.output / "exact-reference.jsonl")
    args.window_ledger = WindowLedger(args.output, 0)
    return truths


def acquire(Backend, args, queries, eligible, truths, counter):
    choices = {}
    with (args.output / "cases.jsonl").open("x") as output:
        for t in FILTERS:
            cases = [q for q in queries if threshold(q) == t]
            with session(Backend, args) as c:
                for index, q in enumerate(cases):
                    qid = q["id"]
                    with bind(c, args, t, len(eligible[t]), None):
                        if index == 0 and not args.fixture:
                            write(args.output / f"ann-plan-{t}.json", check_plan(c, q))
                        native = perform(c, q, counter, "native_bridge", args)["output"]
                    require(
                        matches(native, args.native_refs[qid]["native"]), "native bridge differs"
                    )
                    native_recall = validate_output(native, eligible[t], truths[qid])
                    with bind(c, args, t, len(eligible[t]), 0):
                        reserve(counter, "canonical_capture", args)
                        canonical = capture(
                            c,
                            q,
                            f"variants-{t}-{index}",
                            budget=(1 << 63) - 1,
                            fixture=args.fixture,
                        )
                        require(matches(canonical["output"], native), "canonical output differs")
                        signature = prefix_signature(canonical["states"])
                        chain = prefix_chain(signature)
                        if not args.fixture:
                            old = args.trajectories[qid]
                            require(chain == old["prefix_sha256"], "canonical traversal changed")
                        observations = {str(o["checkpoint"]): o for o in canonical["checkpoints"]}
                        require(
                            set(map(int, observations))
                            == {cp for cp in POINTS if cp <= len(chain)},
                            "legal observation coverage differs",
                        )
                        native_work = canonical["telemetry"]["work_counters"][
                            "layer0_distance_evaluations"
                        ]
                        actions = {}
                        for cp in POINTS:
                            if cp > len(chain):
                                continue
                            target = canonical["states"][cp]["target"]
                            reserve(counter, "forced_prefix", args)
                            forced = capture(
                                c,
                                q,
                                f"variants-{t}-{index}-stop-{cp}",
                                budget=target,
                                fixture=args.fixture,
                            )
                            require(
                                forced["telemetry"]["stop_reason"] == "fixed_budget_stop"
                                and forced["telemetry"]["checkpoint_count"] == cp
                                and prefix_signature(forced["states"]) == signature[:cp],
                                "legal action prefix differs",
                            )
                            score = validate_output(forced["output"], eligible[t], truths[qid])
                            actions[str(cp)] = {
                                "output": forced["output"],
                                "recall": score,
                                "safe": score + 1e-12 >= native_recall,
                                "native_count_preserved": len(forced["output"]) >= len(native),
                                "layer0_work": forced["telemetry"]["work_counters"][
                                    "layer0_distance_evaluations"
                                ],
                                "target": target,
                                "prefix_sha256": chain[cp - 1],
                            }
                    ideal = args.ideals[qid]
                    with bind(c, args, t, len(eligible[t]), 10):
                        set_target(c, ideal["checkpoint"])
                        actual = perform(c, q, counter, "ideal_replay", args)["output"]
                        require(
                            matches(actual, ideal["output"]), "recall-only ideal replay differs"
                        )
                        require(
                            c.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                            == ideal["checkpoint"],
                            "ideal checkpoint differs",
                        )
                    with bind(c, args, t, len(eligible[t]), None):
                        after = perform(c, q, counter, "native_bridge", args)["output"]
                        require(matches(after, native), "native after bridge differs")
                    row = {
                        "id": qid,
                        "filter": t,
                        "role": args.roles[qid],
                        "native": native,
                        "native_recall": native_recall,
                        "native_layer0_work": native_work,
                        "observations": observations,
                        "actions": actions,
                        "ideal": ideal,
                        "canonical_checkpoint_count": len(chain),
                    }
                    choices[qid] = row
                    emit(output, row)
                    if index % 25 == 0:
                        output.flush()
                        print(
                            json.dumps(
                                {
                                    "phase": "legal_action_capture",
                                    "filter": t,
                                    "cases_done": index + 1,
                                    "cases_total": len(cases),
                                    "attempts": counter["total"],
                                }
                            ),
                            flush=True,
                        )
    args.window_ledger.finish(counter)
    write(
        args.output / "capture-freeze.json",
        {
            "cases": len(choices),
            "cases_sha256": sha(args.output / "cases.jsonl"),
            "points": POINTS,
            "quality": "per-case native recall preservation",
            "exact_serving_calls": 0,
            "fresh_exact_queries": 0,
        },
    )
    return choices


def timing(*args):
    del args
    # Acquisition is a separate allocation; no serving timings select policies.
