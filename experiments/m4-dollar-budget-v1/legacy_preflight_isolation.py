"""Run the historical pending-approval test without assuming no live run has ever existed."""

import pytest


@pytest.fixture(autouse=True)
def isolate_completed_history_from_pending_test(request, monkeypatch, tmp_path):
    target = "test_missing_amendment_approval_blocks_before_credentials_or_network"
    if request.node.name != target or "m4-context-amendment-v1" not in request.node.nodeid:
        return
    import common
    import run_continuation

    pending = tmp_path / "isolated-pending-amendment"
    monkeypatch.setattr(common, "DEST", pending)
    monkeypatch.setattr(run_continuation, "DEST", pending)
    monkeypatch.setattr(request.module, "DEST", pending)
