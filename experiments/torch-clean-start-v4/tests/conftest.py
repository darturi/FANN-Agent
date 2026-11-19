import http.client
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fannclean.core import FILTERS, Limits, prepare, read, seal_initial  # noqa: E402


@pytest.fixture(autouse=True)
def prohibit_real_provider_or_processes(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unit verification must not start a provider, database, Docker or SSH")

    monkeypatch.setattr(http.client.HTTPSConnection, "request", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)


def static_cases():
    return [
        {
            "handle": f"old-{g}-{t}",
            "group": f"source-{g}",
            "role": role,
            "filter": t,
            "vector": [float(g), 1.0],
        }
        for g, role in enumerate(["development"] * 2 + ["test"] * 2)
        for t in FILTERS
    ]


@pytest.fixture
def input_cases():
    return static_cases()


@pytest.fixture
def stage(tmp_path):
    root = tmp_path / "fresh"
    prepare(root, static_cases(), Limits(bootstrap_draws=128))
    seal_initial(root)
    return root


@pytest.fixture
def cases(stage):
    return read(stage / "private/cases.json")
