import sys

import prepare
import prepare_continuation
import pytest
import remote
import run_agent


@pytest.mark.parametrize(
    "entrypoint", ["kit", "continuation", "packet", "model", "launch", "final", "qualify"]
)
def test_seeded_workflow_stops_before_files_provider_or_remote_work(
    tmp_path, monkeypatch, entrypoint
):
    def forbidden(*args, **kwargs):
        pytest.fail("retired workflow attempted external work")

    monkeypatch.setattr(run_agent, "verify_current_provider", forbidden)
    monkeypatch.setattr(remote, "ssh", forbidden)
    monkeypatch.setattr(remote, "client", forbidden)
    target = tmp_path / "must-not-exist"
    calls = {
        "kit": lambda: prepare.prepare(target),
        "continuation": lambda: prepare_continuation.prepare(tmp_path / "prior", target),
        "packet": lambda: run_agent.prepare(target, "fixture", "/fixture", tmp_path / "kit"),
        "model": lambda: run_agent.run(target, tmp_path / "approval"),
        "launch": remote.launch,
        "final": remote.finalize,
        "qualify": remote.main,
    }
    monkeypatch.setattr(sys, "argv", ["remote.py", "qualify", "--run", str(target)])
    with pytest.raises(ValueError, match="required clean start"):
        calls[entrypoint]()
    assert not target.exists()
