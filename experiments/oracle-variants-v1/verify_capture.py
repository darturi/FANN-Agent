"""Independently score complete legal-action evidence before hindsight fitting."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def lines(path):
    with path.open() as handle:
        yield from map(json.loads, handle)


def verify(results, kit, *, fixture=False):
    sys.path.insert(0, str(kit))
    from common import matches
    from oracle_design import validate_output

    receipt = read(results / "receipt.json") if not fixture else None
    if not fixture:
        assert receipt["status"] == "oracle_variants_capture_complete"
        assert read(results / "host-exit.json") == {"exit_code": 0, "job_id": receipt["job_id"]}
        assert receipt["binding_sha256"] == sha(kit / "binding.json")
        binding = read(kit / "binding.json")
        for name, expected in binding["files"].items():
            assert sha(kit / name) == expected, name
        assert receipt["graph"] == binding["graph"] and receipt["data_index_before_after"] is True
        for name, expected in receipt["raw_sha256"].items():
            assert sha(results / name) == expected, name
    freeze = read(results / "capture-freeze.json")
    assert freeze["cases_sha256"] == sha(results / "cases.jsonl")
    roles = read(kit / "query-roles.json")
    truth = {r["id"]: r["output"] for r in lines(results / "exact-reference.jsonl")}
    eligible = {int(t): set(ids) for t, ids in read(results / "eligibility.json").items()}
    prior = {r["id"]: r for r in lines(kit / "source-quality.jsonl")}
    trajectories = {r["id"]: r for r in lines(kit / "source-trajectories.jsonl")}
    cases = {r["id"]: r for r in lines(results / "cases.jsonl")}
    assert len(cases) == freeze["cases"] == len(roles) and set(cases) == set(roles) == set(truth)
    count = 0
    for qid, row in cases.items():
        assert row["role"] == roles[qid] and matches(row["native"], prior[qid]["native"])
        native = validate_output(row["native"], eligible[row["filter"]], truth[qid])
        assert abs(native - row["native_recall"]) < 1e-12
        old = trajectories[qid]
        assert row["canonical_checkpoint_count"] == old["count"]
        points = {str(cp) for cp in (16, 32, 64) if cp <= old["count"]}
        assert set(row["actions"]) == set(row["observations"]) == points
        for point, action in row["actions"].items():
            cp = int(point)
            score = validate_output(action["output"], eligible[row["filter"]], truth[qid])
            assert abs(score - action["recall"]) < 1e-12
            assert action["safe"] == (score + 1e-12 >= native)
            assert action["prefix_sha256"] == old["prefix_sha256"][cp - 1]
            assert action["target"] == old["targets"][cp - 1]
            assert 0 <= action["layer0_work"] <= row["native_layer0_work"]
            observation = row["observations"][point]
            assert (
                observation["budget"] == action["target"] and observation["extra_heap_fetches"] == 0
            )
            for name in (
                "qualifying_count",
                "tenth_distance",
                "frontier_gap",
                "top10_new_since_previous",
            ):
                value = observation[name]
                assert value is None or math.isfinite(value)
            count += 1
        ideal = row["ideal"]
        assert (
            validate_output(ideal["output"], eligible[row["filter"]], truth[qid]) + 1e-12 >= native
        )
        if ideal["checkpoint"]:
            assert ideal["prefix_sha256"] == old["prefix_sha256"][ideal["checkpoint"] - 1]
        else:
            assert matches(ideal["output"], row["native"])
    attempts = read(results / "attempts.json")
    expected = {
        "native_bridge": len(cases) * 2,
        "canonical_capture": len(cases),
        "forced_prefix": count,
        "ideal_replay": len(cases),
    }
    expected["total"] = sum(expected.values())
    assert attempts == expected
    budget = read(results / "reservation-final.json")
    assert budget["actual_total"] == attempts["total"] and budget["source_charged"] == 0
    assert budget["charged_total"] >= attempts["total"]
    assert budget["unused_charged"] == budget["charged_total"] - attempts["total"]
    assert budget["charged_total"] <= budget["cap"] == 2000000
    result = {
        "status": "legal_action_capture_verified",
        "fixture": fixture,
        "cases": len(cases),
        "heldout_cases": sum(r["role"] == "test" for r in cases.values()),
        "legal_action_labels": count,
        "actual_fresh_ann_queries": attempts["total"],
        "charged_attempts": budget["charged_total"],
        "unused_charged": budget["unused_charged"],
        "fresh_exact_queries": 0,
        "raw_case_sha256": sha(results / "cases.jsonl"),
    }
    (results / "capture-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.results, args.kit, fixture=args.fixture)))
