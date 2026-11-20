import uuid

import pytest
from fannclean.comparison import bootstrap, panels
from fannclean.controller import REPORT_KEYS, Controller
from fannclean.core import Limits, prepare, read, verify_initial, write
from fannclean.deploy import package, verify_package, verify_runtime_assets
from fannclean.engine import Engine
from test_comparison import LocalFixtureClient, finalize, inputs, plan
from test_core_engine import SyntheticBackend, policy
from test_model_worker import active, authorize
from test_search_deploy import minimal_engine


def call(controller, name, **args):
    return controller.call(uuid.uuid4().hex, name, args)


def test_revision_uses_failed_stop_as_evidence_and_rechecks_other_groups(tmp_path):
    root = tmp_path / "revision"
    limits = Limits(query_cap=20_000, final_reserve=2000, bootstrap_draws=60)
    prepare(
        root,
        inputs(),
        limits,
        comparison={**plan("agent", 7), "mode": "agent_revision", "followup_groups": 0},
    )
    authorize(root)
    active(root)
    design = read(root / "config.json")["comparison"]
    _, _, screening = panels(root, design)
    bad_group = screening[0].rsplit("-", 1)[0]

    class PartialFailure(SyntheticBackend):
        def execute(self, case, family, **kwargs):
            result = super().execute(case, family, **kwargs)
            if result["checkpoint"] == 2 and case["group"] != bad_group:
                result["output"] = self.native
            return result

    class Client(LocalFixtureClient):
        def action(self, payload):
            return Engine(self.root, PartialFailure).process(uuid.uuid4().hex, payload)

    client = Client(root)
    controller = Controller(root, client)
    start = bootstrap(controller, design)
    write(root / "agent/policies/early.json", policy("early", cp=2))
    write(
        root / "agent/policies/alternative.json",
        policy("alternative", ["gt", ["feature", "qualifying_count"], 1], cp=4),
    )
    write(root / "agent/policies/later.json", policy("later", cp=4))
    first = call(controller, "evaluate", policy_paths=["policies/early.json"])
    assert first["quality_failure_cases"] == 7
    call(controller, "evaluate", policy_paths=["policies/alternative.json"])
    report = {
        field: "Explanation grounded in measured development evidence." for field in REPORT_KEYS
    }
    assert (
        "investigate_stop" in call(controller, "finish", candidate_id=None, report=report)["error"]
    )
    revision_args = {
        "parent_candidate_id": "c1",
        "policy_path": "policies/later.json",
        "hypothesis": "Wait to checkpoint 4 because later prefixes restored recall.",
    }
    assert "investigate" in call(controller, "evaluate_revision", **revision_args)["error"]
    private_handle = next(
        c["handle"] for c in read(root / "private/cases.json") if c["role"] == "test"
    )
    arguments = {"candidate_id": "c1", "later_checkpoints": [4], "features": ["qualifying_count"]}
    assert (
        "measured failed stop"
        in call(controller, "investigate_stop", handle=private_handle, **arguments)["error"]
    )
    failed_handle = first["counterexamples"][0]["handle"]
    evidence = call(controller, "investigate_stop", handle=failed_handle, **arguments)
    assert evidence["later_prefixes_measured"] == 1
    assert [r["recall"] for r in evidence["prefix_scores"] if r["handle"] == failed_handle] == [
        0,
        1,
    ]
    assert len(read(root / "agent" / evidence["artifact"])["successful_peers"]) == 1

    unchanged = {**revision_args, "policy_path": "policies/early.json"}
    assert "change the executable" in call(controller, "evaluate_revision", **unchanged)["error"]
    revised = call(controller, "evaluate_revision", **revision_args)["revision"]
    assert revised["previously_unmeasured_groups"] == 2
    assert revised["investigation_request_ids"] == [evidence["request_id"]]
    revised_id = revised["revised_candidate_id"]
    assert call(controller, "confirm", candidate_id=revised_id)["full_quality"]
    outcome = call(controller, "finish", candidate_id=revised_id, report=report)
    assert outcome["status"] == "policy_frozen"
    assert outcome["targeted_investigations"] == outcome["evaluated_revisions"] == 1
    from fannclean.core import digest

    held_out = finalize(
        root,
        client,
        {
            **start,
            "run_id": controller.run_id,
            "model_closed": True,
            "model_charged_usd": "0",
            "freeze_sha256": digest(read(root / "host/freeze.json")),
        },
    )
    assert held_out["cohorts"]["held_out"]["qualified_agent_win"]
    assert set(held_out["cohorts"]) == {"held_out"}


def test_archive_preparation_imports_only_static_pins(tmp_path):
    source = minimal_engine(tmp_path)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "PG_VERSION").write_text("17")
    image = tmp_path / "image.sif"
    image.write_bytes(b"synthetic image")
    previous = tmp_path / "previous"
    package(previous, inputs(), source, snapshot, image, "sha256:" + "a" * 64)
    (previous / "agent/evidence/observations.jsonl").write_text("old observation")
    write(previous / "host/history.json", {"prior": "old conversation"})
    write(previous / "agent/policies/old.json", policy())
    fresh = tmp_path / "fresh"
    package(fresh, inputs(), None, None, None, None, asset_stage=previous)
    verify_package(fresh)
    verify_initial(fresh)
    verify_runtime_assets(fresh)
    assert read(fresh / "config.json")["run_id"] != read(previous / "config.json")["run_id"]
    assert not any((fresh / "agent/policies").iterdir())
    assert not (fresh / "host").exists()
    assert not (fresh / "agent/evidence/observations.jsonl").read_bytes()
    (snapshot / "extra").write_text("unexpected database file")
    with pytest.raises(ValueError, match="static snapshot changed"):
        verify_runtime_assets(fresh)
    write(previous / "deployment.json", {"invalid": True})
    with pytest.raises(ValueError, match="recorded static asset differs"):
        package(tmp_path / "rejected", inputs(), None, None, None, None, asset_stage=previous)
