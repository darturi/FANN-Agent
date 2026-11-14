"""Stage the frozen confirmation cohort and an exposed-output parity check."""

import argparse
import json
import struct
from pathlib import Path

from prepare_live import FREEZE_SHA
from rb_plan import ROOT, digest, file_sha, load_plan, pinned, pinned_lines, require

HERE = Path(__file__).resolve().parent
SOURCE = (
    ROOT
    / "trials/torch-reviews-results/feature-data-ablation-v1"
    / "torch-feature-data-ablation-v1/inputs/evaluation.jsonl"
)
SHADOW = (
    ROOT
    / "trials/reviews-persistent-batch-native-v1/qualified-shadow-extended"
    / "job-22556100/shadow.jsonl"
)
PREDICATE = {"field": "m_000000", "op": "gte", "value": 108}


def vector_key(query):
    return struct.pack("<768f", *query["vector"])


def select_stop(checkpoints, rule):
    for clause in rule:
        obs = checkpoints.get(clause["cp"])
        if obs is None:
            continue
        tenth, frontier = obs["tenth_distance"], obs["frontier_distance_min"]
        if tenth is None or frontier is None:
            continue
        values = {"tenth_distance": tenth, "frontier_gap": frontier - tenth}
        if all(
            values[name] >= limit if op == ">=" else values[name] <= limit
            for name, op, limit in clause["conditions"]
        ):
            return clause["cp"]
    return 0


def write(path, rows):
    with path.open("x") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def stage(output):
    freeze = json.loads(pinned(HERE / "freeze.json", FREEZE_SHA))
    plan = load_plan()
    source = list(pinned_lines(SOURCE, freeze["fresh_confirmation_source_sha256"]))
    fresh = [row for row in source if row["query"]["filter"] == PREDICATE]
    groups = {row["group"] for row in fresh}
    ids = {row["query"]["id"] for row in fresh}
    vectors = {vector_key(row["query"]) for row in fresh}
    require(
        len(source) == 180
        and len({row["group"] for row in source}) == 60
        and len(fresh) == len(groups) == len(ids) == len(vectors) == 60
        and not groups.intersection(case.group for case in plan.cases.values())
        and not ids.intersection(plan.cases)
        and not vectors.intersection(vector_key(case.query) for case in plan.cases.values())
        and all(row["query"]["k"] == 10 for row in fresh),
        "Confirmation cohort changed or overlaps development",
    )
    # A stable predeclared order, independent of vectors and outcomes.
    fresh.sort(key=lambda row: digest(["votes108-confirm-v1", row["group"]]))
    write(output / "fresh.jsonl", [row["query"] for row in fresh])
    qualification = []
    for row in pinned_lines(SHADOW, freeze["development_capture_sha256"]):
        obs = {s["checkpoint"]: s for s in row["checkpoints"]}
        stops = {s["checkpoint"]: s for s in row["forced_stops"]}
        qid = row["query_id"]
        require(
            row["output"] and plan.cases[qid].stratum == "votes108", "Unexpected development row"
        )
        expected = {"native": [0, row["output"]]}
        for arm in ("baseline", "candidate"):
            cp = select_stop(obs, freeze[arm])
            require(not cp or stops[cp]["saved_stop_output_matches"], "Unverified forced stop")
            expected[arm] = [cp, stops[cp]["output"] if cp else row["output"]]
        qualification.append({"id": qid, "expected": expected})
    require(len({row["id"] for row in qualification}) == 200, "Development coverage differs")
    require(
        sum(bool(row["expected"]["baseline"][0]) for row in qualification) == 21
        and sum(bool(row["expected"]["candidate"][0]) for row in qualification) == 56,
        "Frozen development replay changed",
    )
    write(output / "qualification.jsonl", qualification)
    print("Fresh cohort digest", file_sha(output / "fresh.jsonl"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    stage(parser.parse_args().output)
