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
