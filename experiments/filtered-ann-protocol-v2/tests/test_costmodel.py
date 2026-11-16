import pytest
from fannproto.costmodel import features, operations, predict_ratio
from fannproto.rehearsal import fixture_policy


def row():
    return {
        "filter": "votes32",
        "observations": {
            str(cp): {
                "qualifying_count": 7 if cp == 16 else 10,
                "tenth_distance": None if cp == 16 else 0.4,
                "frontier_gap": None if cp == 16 else 0.1,
                "top10_new_since_previous": 0 if cp == 64 else None,
            }
            for cp in (16, 32, 64)
        },
    }


def costs():
    return {
        "prefix_ratio": {"full": 1, "16": 0.2, "32": 0.4, "64": 0.6},
        "search_work": {
            key: {"vector_calls": n, "layer0_queue_pops": n}
            for key, n in (("full", 100), ("16", 20), ("32", 40), ("64", 60))
        },
    }


def test_partial_stop_and_force_continue_have_distinct_causal_work():
    p = fixture_policy()
    r = row()
    stop, ops = operations(p, r)
    assert stop == 16 and ops["count"] == [1, 0, 0]
    assert ops["comparison"] == [1, 0, 0]
    stop, ops = operations(p, r, force_continue=True)
    assert stop is None and ops["count"] == ops["comparison"] == [1, 0, 0]
    assert features(p, r, costs())[0] == 0.2
    assert features(p, r, costs(), force_continue=True)[0] == 1


def test_turnover_dependency_collects_previous_checkpoint_without_deciding():
    p = fixture_policy()
    p["rules"] = {"votes32": [{"cp": 64, "conditions": [["top10_new_since_previous", "<=", 0]]}]}
    stop, ops = operations(p, row())
    assert stop == 64
    assert ops["count"] == ops["ranked"] == [0, 1, 1]
    assert ops["turnover"] == ops["decision"] == ops["comparison"] == [0, 0, 1]


def test_null_and_failed_conditions_stop_numeric_comparison_count():
    p = fixture_policy()
    p["rules"] = {
        "votes32": [
            {
                "cp": 16,
                "conditions": [["tenth_distance", ">=", 0], ["qualifying_count", ">=", 0]],
            }
        ]
    }
    stop, ops = operations(p, row())
    assert stop is None and ops["comparison"] == [0, 0, 0]
    assert ops["decision"] == [1, 0, 0] and ops["ranked"] == [1, 0, 0]
    p["rules"]["votes32"][0]["conditions"] = [
        ["qualifying_count", ">=", 8],
        ["tenth_distance", ">=", 0],
    ]
    assert operations(p, row())[1]["comparison"] == [1, 0, 0]


def test_signed_proxy_does_not_clip_negative_component_estimates():
    p = fixture_policy()
    model = {"kind": "signed_additive", "coefficients": {"votes32": [-0.01, 0, 0, 0, 0]}}
    assert predict_ratio(model, p, row(), costs()) == pytest.approx(0.19)
    p["rules"] = {}
    assert predict_ratio(model, p, row(), costs()) == 1
