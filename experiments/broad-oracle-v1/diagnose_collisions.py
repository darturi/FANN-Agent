"""Check first-checkpoint observational collisions without additional ANN calls."""

import argparse
import json
from pathlib import Path

from prepare_capture import STUDY, sha


def rows(path):
    with path.open() as handle:
        yield from map(json.loads, handle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--fit", type=Path, required=True)
    args = parser.parse_args()
    first = {}
    for row in rows(args.capture / "cases.jsonl"):
        frame = row["frames"][0]
        # Include the collection fuel charge, an implicit possible side channel.
        key = (row["filter"], *frame["values"], frame["count_units"])
        first[row["id"]] = {"key": key, "role": row["role"], "native_recall": row["native_recall"]}
    unsafe = {}
    prefixes = STUDY / "full-workload-oracle-v1/return-23567950/results/prefixes.jsonl"
    for row in rows(prefixes):
        if row["checkpoint"] == 1 and row["recall"] + 1e-12 < first[row["id"]]["native_recall"]:
            unsafe.setdefault(first[row["id"]]["key"], []).append(
                {"id": row["id"], "prefix_recall": row["recall"], **first[row["id"]]}
            )
    legacy = {
        r["id"]: r for r in rows(STUDY / "oracle-variants-v1/return-23604734/results/cases.jsonl")
    }
    output = {
        "schema": "fannagent.first-checkpoint-collisions.v1",
        "cases_sha256": sha(args.capture / "cases.jsonl"),
        "prefixes_sha256": sha(prefixes),
        "source_sha256": sha(Path(__file__)),
        "cohorts": {},
        "scope": (
            "Only the first scheduled checkpoint. Identical declared inputs, initial zero "
            "state and collection fuel charges imply identical decisions for any "
            "deterministic v3 policy. No claim about later checkpoints or latency optimality."
        ),
    }
    for cohort in ("full_workload", "heldout_test"):
        evidence = []
        for row in rows(args.fit / (cohort + "-choices.jsonl")):
            ideal = legacy[row["id"]]["ideal"]["checkpoint"]
            if ideal == row["checkpoint"]:
                continue
            twins = [
                t
                for t in unsafe.get(first[row["id"]]["key"], [])
                if cohort == "full_workload" or t["role"] == "test"
            ]
            evidence.append(
                {
                    "id": row["id"],
                    "ideal_checkpoint": ideal,
                    "broader_checkpoint": row["checkpoint"],
                    "inputs_and_count_units": first[row["id"]]["key"],
                    "native_recall": first[row["id"]]["native_recall"],
                    "unsafe_twins": [{k: v for k, v in t.items() if k != "key"} for t in twins],
                }
            )
        output["cohorts"][cohort] = {
            "mismatches": evidence,
            "all_have_unsafe_first_checkpoint_twin": all(
                r["unsafe_twins"] and r["ideal_checkpoint"] == 1 for r in evidence
            ),
        }
    (args.fit / "first-checkpoint-collisions.json").write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                c: {
                    "mismatches": len(r["mismatches"]),
                    "all_have_unsafe_twin": r["all_have_unsafe_first_checkpoint_twin"],
                }
                for c, r in output["cohorts"].items()
            }
        )
    )


if __name__ == "__main__":
    main()
