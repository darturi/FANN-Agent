from decimal import Decimal

import pytest

from fannagent.backends.fake import PROFILE
from fannagent.budget import Budget
from fannagent.config import RunConfig
from fannagent.controller import explore, open_run
from fannagent.errors import AgentError, BudgetExceeded, ProtectedEvidence
from fannagent.policy import validate_candidate
from fannagent.store import Store
from fannagent.study import Study


def configuration(backend="fake"):
    return RunConfig(
        backend={"name": backend},
        model={"ceiling_usd": "1", "allowance_usd": ".5"},
        workload={
            "count": 1000,
            "warmups": 0,
            "passes": 1,
            "bootstrap_samples": 10000,
            "minimum_groups": 30,
        },
    )


def test_complete_resume_and_fourth_backend(tmp_path):
    config, store, backend = open_run(tmp_path / "run", configuration())
    store.set("prepared", backend.prepare_copy().serialize())
    assert explore(config, store, backend, step_limit=2)["status"] == "interrupted"
    assert explore(config, store, backend, resume=True, step_limit=10)["status"] == "frozen"
    study = Study(config, store, backend)
    with pytest.raises(ProtectedEvidence):
        study.validate({"name": "changed", "root": "continue"})
    report = study.final()
    assert report["status"] in {"accepted", "no_recommendation"}
    assert report["valid"]
    assert report["simulated"]
    assert study.final() == report
    assert store.get("test_entitlement") == "consumed"
    store.set("prepared", {"tampered": True})
    with pytest.raises(AgentError, match="compatibility"):
        study.frozen_policy()


def test_protected_query_and_artifact(tmp_path):
    config, store, backend = open_run(tmp_path / "run", configuration())
    store.set("prepared", backend.prepare_copy().serialize())
    study = Study(config, store, backend)
    query = next(i["query"] for i in study.manifest["items"] if i["split"] == "test")
    with pytest.raises(ProtectedEvidence):
        study.probe(query)
    private = store.put("private", {"private": 1})
    with pytest.raises(AgentError):
        store.read(private, agent=True)
    with pytest.raises(AgentError, match="scopes"):
        store.put("private", {"private": 1}, scope="development")


def test_spending_reservations_survive_crash(tmp_path):
    config = configuration().model
    store = Store(tmp_path / "run", create=True)
    budget = Budget(store, config)
    first = budget.reserve(Decimal(".75"))
    with pytest.raises(AgentError, match="in flight"):
        budget.reserve(Decimal(".01"))
    budget.recover()
    assert budget.summary()["uncertain_calls"] == 1
    second = budget.reserve(Decimal(".75"))
    budget.settle(second, Decimal(".5"), {})
    assert budget.summary()["committed_usd"] == "1.25"
    with pytest.raises(BudgetExceeded):
        budget.reserve(Decimal(".01"))
    changed = config.model_copy(update={"ceiling_usd": Decimal("2")})
    with pytest.raises(AgentError, match="contract"):
        Budget(store, changed)
    assert first != second


def test_bound_violation_disables_calls(tmp_path):
    budget = Budget(Store(tmp_path / "run", create=True), configuration().model)
    reservation = budget.reserve(Decimal(".01"))
    with pytest.raises(AgentError, match="exceeded"):
        budget.settle(reservation, Decimal(".02"), {})
    with pytest.raises(AgentError, match="violated"):
        budget.reserve(Decimal(".01"))


def test_policy_uses_shared_interpreter_and_rejects_offline_features():
    policy = validate_candidate({"name": "safe", "root": "continue"}, PROFILE)
    assert policy.runtime_profile_hash == PROFILE.fingerprint
    with pytest.raises(AgentError):
        validate_candidate(
            {
                "name": "invalid",
                "root": {
                    "if": {"feature": "visited_match_fraction"},
                    "then": "stop",
                    "else": "continue",
                },
            },
            PROFILE,
        )


def test_frozen_backend_settings_cannot_change(tmp_path):
    config, store, backend = open_run(tmp_path / "run", configuration())
    store.set("prepared", backend.prepare_copy().serialize())
    assert explore(config, store, backend)["status"] == "frozen"
    original = backend.compatibility
    backend.compatibility = lambda: {**original(), "settings": {"effort": 999}}
    with pytest.raises(AgentError, match="compatibility"):
        Study(config, store, backend).frozen_policy()


def test_artifact_symlink_and_nonregular_files_are_refused(tmp_path):
    store = Store(tmp_path / "run", create=True)
    artifact = store.put("development", {"value": 1}, scope="development")
    folder = store.root / "workspace" / "artifacts"
    file = folder / f"{artifact}.json"
    file.unlink()
    private = tmp_path / "outside"
    private.write_text("secret")
    file.symlink_to(private)
    with pytest.raises(AgentError, match="unsafe"):
        store.read(artifact, agent=True)
    file.unlink()
    import os

    os.mkfifo(file)
    with pytest.raises(AgentError, match="type"):
        store.read(artifact, agent=True)
    file.unlink()
    folder.rmdir()
    folder.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(AgentError, match="unsafe"):
        store.put("write", {"outside": True}, scope="development")
    assert not list(tmp_path.glob("*.json"))


def test_protected_synthetic_anchor_provenance_cannot_be_probed(tmp_path):
    config, store, backend = open_run(tmp_path / "run", configuration())
    store.set("prepared", backend.prepare_copy().serialize())
    study = Study(config, store, backend)
    item = next(i for i in study.manifest["items"] if i["split"] == "test")
    anchor = backend.snapshot().rows[backend.snapshot().analysis_id(item["anchor"])]
    with pytest.raises(ProtectedEvidence, match="anchor"):
        study.probe({"id": "new-anchor-query", "vector": anchor["vector"], "k": 10})
    assert study.permitted(study.development[0]["query"])
