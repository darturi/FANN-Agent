import pytest
from test_workflow import configuration

from fannagent.cli import clean, deploy
from fannagent.client import open_session
from fannagent.controller import explore, open_run
from fannagent.errors import AgentError
from fannagent.study import Study


def test_explicit_deployment_and_sdk_use_the_evaluated_policy(tmp_path):
    # Seed 1 has enough independent strata for this deterministic simulated fixture.
    config = configuration()
    config.workload.seed = 1
    config, store, backend = open_run(tmp_path / "source", config)
    store.set("prepared", backend.prepare_copy().serialize())
    assert explore(config, store, backend)["status"] == "frozen"
    assert Study(config, store, backend).final()["status"] == "accepted"
    target_config, target_store, target_backend = open_run(tmp_path / "target", config)
    target_store.set("prepared", target_backend.prepare_copy().serialize())
    deploy(store.root, target_store.root)
    query = {
        "id": "application-query",
        "vector": backend.snapshot().rows[0]["vector"],
        "k": 10,
    }
    session = open_session(target_store.root)
    try:
        result = session.query(query)
        assert -250 in result.ids
        assert result.metadata["identifier_space"] == "source"
        assert (
            target_store.get("deployment")["policy_hash"]
            == store.read(store.get("frozen"))["policy_hash"]
        )
    finally:
        session.close()
    clean(target_store.root)
    clean(target_store.root)  # Cleanup is safe to repeat after an interrupted caller.
    with pytest.raises(AgentError, match="live qualified"):
        open_session(target_store.root)
