import itertools
import random

import pytest
from fannproto.policy import FILTERS
from fannproto.uncertainty import ESTIMATE_STATUS, regret_bound, select_shortlist


def record(index, interval, *, comparisons=1):
    return {
        "candidate_id": f"candidate-{index}",
        "rule_hash": f"{index:064x}",
        "policy": {
            "rules": {
                "votes32": [{"cp": 16, "conditions": [["qualifying_count", ">=", 0]] * comparisons}]
            }
        },
        "evaluation": {
            "quality_preserves_raw_native640": True,
            "per_filter": {f: {"stops": int(f == "votes32")} for f in FILTERS},
        },
        "cost_estimate": {
            "status": ESTIMATE_STATUS,
            "primary_ratio_interval": interval,
            "primary_ratio_proxy": sum(interval) / 2,
        },
    }


def test_strict_dominance_selects_one_and_never_uses_point_estimate_ties():
    records = [record(1, [0.80, 0.82]), record(2, [0.90, 0.92]), record(3, [0.95, 1.02])]
    result = select_shortlist(records)
    assert result["candidate_ids"] == ["candidate-1"]
    assert result["conditional_regret_bound"] == 0
    tied = [record(i, [0.90, 0.96]) for i in range(1, 4)]
    before = select_shortlist(tied)
    for r in tied:
        r["cost_estimate"]["primary_ratio_proxy"] = r["cost_estimate"]["primary_ratio_interval"][0]
    assert select_shortlist(list(reversed(tied))) == before
    assert len(before["candidate_ids"]) == 3


def test_four_way_ambiguity_abstains_instead_of_arbitrarily_dropping_a_candidate():
    result = select_shortlist([record(i, [0.90, 0.96]) for i in range(1, 5)])
    assert result["status"] == "abstain_uncertainty_exceeds_cap"
    assert result["candidate_ids"] == [] and result["conditional_regret_bound"] is None
    assert result["best_attainable_bound"] == pytest.approx(0.06)


def test_native_abstention_quality_support_no_stop_and_deduplication():
    assert select_shortlist([record(1, [0.995, 1.04])])["status"] == "certified_native_abstention"
    original, duplicate = record(1, [0.90, 0.96]), record(2, [0.90, 0.96])
    duplicate["rule_hash"] = original["rule_hash"]
    bad = record(3, [0.1, 0.2])
    bad["evaluation"]["quality_preserves_raw_native640"] = False
    unknown = record(4, [0.1, 0.2])
    unknown["cost_estimate"]["status"] = "unsupported_uncertainty_estimate"
    noop = record(5, [0.1, 0.2])
    for value in noop["evaluation"]["per_filter"].values():
        value["stops"] = 0
    result = select_shortlist([duplicate, noop, bad, unknown, original])
    assert result["candidate_ids"] == ["candidate-1"]
    assert len(result["exclusions"]) == 4


def test_certificate_matches_every_interval_corner_for_all_bounded_subsets():
    rng = random.Random(20261116)
    checked = 0
    for trial in range(35):
        count = 1 + trial % 6
        intervals = {}
        for i in range(count):
            low = rng.uniform(0.6, 1.1)
            intervals[str(i)] = [low, low + rng.uniform(0, 0.15)]
        ids = list(intervals)
        for n in range(min(3, count) + 1):
            for selected in itertools.combinations(ids, n):
                maximum = 0
                for vertex in itertools.product(*(intervals[cid] for cid in ids)):
                    costs = dict(zip(ids, vertex, strict=True))
                    regret = min([1, *(costs[cid] for cid in selected)]) - min([1, *vertex])
                    maximum = max(maximum, regret)
                assert regret_bound(intervals, selected) == pytest.approx(maximum, abs=1e-12)
                checked += 1
    assert checked > 500


def test_complexity_breaks_certified_subset_ties_and_cap_is_fixed():
    # Either candidate is within one point under these narrow intervals.
    result = select_shortlist([record(1, [0.90, 0.905], comparisons=2), record(2, [0.90, 0.905])])
    assert result["candidate_ids"] == ["candidate-2"]
    with pytest.raises(ValueError, match="nine"):
        select_shortlist([record(i, [0.9, 0.95]) for i in range(10)])
    bad = record(1, [float("nan"), 0.95])
    with pytest.raises(ValueError, match="interval"):
        select_shortlist([bad])
