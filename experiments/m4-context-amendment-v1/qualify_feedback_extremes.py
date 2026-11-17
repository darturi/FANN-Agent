"""Stress every filter's bounded counterexamples and repeated nine-program comparisons."""

import json
from copy import deepcopy
from unittest.mock import patch

from common import CONTEXT, DEST, canonical, seed_campaign, tool_block, verify_origin, write
from fannproto.policy import FILTERS


def qualify():
    output = DEST / "feedback-extremes-v1"
    output.mkdir(exist_ok=False)
    policy = {
        "schema": "fannagent.filtered-ann.v2",
        "name": "all-filter unsafe prefix capacity fixture",
        "rationale": "Diagnostic only: maximize bounded counterexample feedback; never a nominee.",
        "rules": {f: [{"cp": 16, "conditions": []}] for f in FILTERS},
    }
    sizes = []
    with patch("socket.create_connection", side_effect=AssertionError("no network")):
        campaign = seed_campaign(
            output / "campaign", {"status": "simulation_only"}, simulation=True
        )
        for n in range(3):
            answer = campaign.dispatch(
                f"batch-{n}",
                "evaluate_candidates",
                {"policies": [deepcopy(policy) for _ in range(3)]},
            )
            sizes.append(len(canonical(tool_block(f"batch-{n}", answer))))
            for value in answer["evaluations"]:
                assert set(value["evaluation"]["counterexamples"]) == set(FILTERS)
                assert sum(map(len, value["evaluation"]["counterexamples"].values())) == 21
                assert not value["evaluation"]["quality_preserves_raw_native640"]
        for n in range(5):
            answer = campaign.dispatch(
                f"compare-{n}",
                "compare_candidates",
                {"candidate_ids": [f"candidate-{i}" for i in range(1, 10)]},
            )
            sizes.append(len(canonical(tool_block(f"compare-{n}", answer))))
        assert campaign.store.get("v2_state")["tool_calls"] == 12
        assert campaign.store.get("v2_state")["candidate_submissions"] == 9
        assert not campaign.shortlist()
    assert max(sizes) < CONTEXT["tool_result_block_bytes"]
    verify_origin()
    receipt = {
        "status": "passed_all_filter_counterexample_and_nine_program_compare_capacity",
        "counterexamples_per_candidate": 21,
        "programs": 9,
        "evaluation_batches": 3,
        "repeated_full_comparisons": 5,
        "tool_result_block_bytes": sizes,
        "maximum_tool_result_bytes": max(sizes),
        "declared_tool_result_bytes": CONTEXT["tool_result_block_bytes"],
        "unsafe_fixture_not_new_discovery": True,
        "SQL_searches": 0,
        "new_paid_requests": 0,
        "development_count_requests": 0,
        "validation_test_outcomes_opened": False,
    }
    write(output / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    qualify()
