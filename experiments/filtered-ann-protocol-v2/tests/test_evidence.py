import pytest
from fannproto.evidence import Evidence
from fannproto.rehearsal import fixture_bundle, fixture_policy


def test_fixture_does_not_satisfy_real_development_inventory():
    with pytest.raises(ValueError, match="450-group"):
        Evidence(fixture_bundle())


def test_component_costs_are_required_and_not_live_latency():
    b = fixture_bundle()
    e = Evidence(b, fixture=True)
    p = fixture_policy()
    estimate = e.estimate(p)
    assert estimate["equal_scalar_mean_ms"] == pytest.approx(1.012)
    assert "not live policy cost" in estimate["status"]
    # Freezing evidence takes a defensive copy of input data.
    b["rows"][0]["native_recall"] = 0
    assert e.rows[0]["native_recall"] == 0.7
    b = fixture_bundle()
    b["cost_status"] = "pending_M0"
    assert Evidence(b, fixture=True).estimate(p) is None


@pytest.mark.parametrize(
    "mutator",
    [
        lambda b: b["rows"][0].update(source_id=123),
        lambda b: b["rows"][0].update(native_recall=0.8),
        lambda b: b["rows"][0].update(native_recall=True),
        lambda b: b["rows"][0]["observations"]["16"].update(tenth_distance=0.2),
        lambda b: b["rows"][0]["observations"]["16"].update(qualifying_count=7.5),
        lambda b: b["rows"][0]["observations"]["16"].update(top10_new_since_previous=0),
        lambda b: b["rows"][0]["costs"].update(comparison_ms=float("nan")),
        lambda b: b["rows"][0]["costs"].update(count_only_ms=-1),
        lambda b: b["rows"][0]["costs"]["search_ms"].pop("16"),
        lambda b: b.update(cost_qualification_receipt_sha256="missing"),
        lambda b: b["rows"][1].update(fold=4),
    ],
)
def test_reject_leaks_inconsistent_labels_features_and_costs(mutator):
    b = fixture_bundle()
    mutator(b)
    with pytest.raises(ValueError):
        Evidence(b, fixture=True)


def work_bundle():
    from fannproto.evidence import GRAPH

    b = fixture_bundle()
    b["cost_status"] = "unqualified_M2_models_failed"
    for r in b["rows"]:
        r["work"] = {
            "graph": {
                "full": {key: 100 for key in GRAPH},
                "16": {key: 20 for key in GRAPH},
            },
            "membership_per_checkpoint": {"16": 640},
        }
    return b


def test_complete_partial_examples_and_work_remain_usable_without_cost_ranking():
    evidence = Evidence(work_bundle(), fixture=True)
    assert len(evidence.examples("preserving_partial_prefix", "votes743", 3)) == 3
    assert not evidence.examples("missing_partial_prefix", "votes743", 3)
    estimate = evidence.work_estimate(fixture_policy())
    assert estimate["equal_scalar_means"]["vector_calls"] == 20
    assert estimate["equal_scalar_means"]["membership_probes"] == 640
    assert evidence.estimate(fixture_policy()) is None
    assert evidence.summary()["cost_ranking_enabled"] is False
    assert "not live" in estimate["status"]


@pytest.mark.parametrize(
    "mutator",
    [
        lambda w: w["graph"]["16"].update(source_id=5),
        lambda w: w["graph"]["full"].update(vector_calls=-1),
        lambda w: w["graph"]["full"].update(vector_calls=True),
        lambda w: w["graph"].pop("16"),
        lambda w: w["membership_per_checkpoint"].update({"16": -1}),
    ],
)
def test_work_inputs_reject_identifiers_invalid_counts_and_missing_prefixes(mutator):
    b = work_bundle()
    mutator(b["rows"][0]["work"])
    with pytest.raises(ValueError):
        Evidence(b, fixture=True)
