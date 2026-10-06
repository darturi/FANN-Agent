import os

import pytest
from test_workflow import configuration

from fannagent.broker import FileBroker, Tools
from fannagent.budget import Budget
from fannagent.controller import open_run
from fannagent.environment import ContainerEnvironment
from fannagent.study import Study

pytestmark = pytest.mark.integration


def test_container_broker_has_only_development_access(tmp_path):
    if not os.environ.get("FANNAGENT_TEST_CONTAINER"):
        pytest.skip("set FANNAGENT_TEST_CONTAINER=1 with workspace image installed")
    config, store, backend = open_run(tmp_path / "run", configuration())
    store.set("prepared", backend.prepare_copy().serialize())
    study = Study(config, store, backend)
    with FileBroker(
        Tools(study, Budget(store, config.model)), store.root / "workspace" / ".broker"
    ) as broker:
        env = ContainerEnvironment(store.root / "workspace", broker)
        try:
            result = env.execute({"command": "fannagent-tool queries '{\"limit\":1}'"})
            assert result["returncode"] == 0, result
            assert "generated-" in result["output"]
            denied = env.execute({"command": "ls /workspace/../private /var/run/docker.sock"})
            assert denied["returncode"] != 0
        finally:
            env.close()
