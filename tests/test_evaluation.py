from fannagent.contracts import ExactTruth, ProbeResult
from fannagent.evaluation import score, summarize


def test_ties_short_results_empty_and_predicate_violations():
    truth = ExactTruth(4, 2, frozenset({1}), frozenset({2, 3}), frozenset({1, 2, 3, 4}))
    assert score(truth, ProbeResult([1, 3], [], 1))["recall"] == 1
    assert score(truth, ProbeResult([3], [], 1))["recall"] == 0.5
    assert not score(truth, ProbeResult([1, 1], [], 1))["valid"]
    assert not score(truth, ProbeResult([1, 5], [], 1))["valid"]
    empty = ExactTruth(0, 0, frozenset(), frozenset(), frozenset())
    assert score(empty, ProbeResult([], [], 1)) == {
        "recall": None,
        "valid": True,
        "duplicate_count": 0,
        "predicate_violation_count": 0,
        "returned_count": 0,
    }


def test_repetitions_do_not_manufacture_independent_groups():
    rows = [
        {
            "group": str(i % 2),
            "valid": True,
            "hardness": "easy",
            "recall_delta": 0,
            "native_ms": 2,
            "policy_ms": 1,
        }
        for i in range(300)
    ]
    result = summarize(rows, seed=42, samples=100, minimum=30, tolerance=0.005)
    assert result["groups"]["easy"]["independent_groups"] == 2
    assert result["status"] == "no_recommendation"


def test_failed_measurements_are_retained_and_cluster_weights_preserve_mean():
    rows = [
        {
            "id": str(i),
            "group": "large",
            "valid": True,
            "hardness": "easy",
            "recall_delta": 0.1,
            "native_ms": 2,
            "policy_ms": 1,
        }
        for i in range(9)
    ]
    rows.append(
        {
            "id": "small",
            "group": "small",
            "valid": True,
            "hardness": "easy",
            "recall_delta": -0.1,
            "native_ms": 2,
            "policy_ms": 1,
        }
    )
    rows.append(
        {
            "id": "failed",
            "group": "failed",
            "valid": False,
            "recall_delta": None,
            "native_ms": 2,
            "policy_ms": None,
        }
    )
    report = summarize(rows, seed=42, samples=10000, minimum=30, tolerance=0.005)
    assert abs(report["groups"]["overall"]["mean_recall_delta"] - 0.08) < 1e-12
    assert report["failed_pairs"] == 1
    assert not report["valid"]
