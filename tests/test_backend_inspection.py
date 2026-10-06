import pytest
from test_workflow import configuration

from fannagent.backends import create
from fannagent.errors import UnsupportedTarget
from fannagent.store import Store


@pytest.mark.parametrize("name", ["weaviate", "elasticsearch"])
def test_deferred_extensions_are_not_registered(tmp_path, name):
    with pytest.raises(UnsupportedTarget, match="not installed"):
        create(configuration(name), Store(tmp_path / "run", create=True))
