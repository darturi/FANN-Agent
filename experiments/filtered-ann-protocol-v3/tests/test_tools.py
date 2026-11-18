import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fannproto3.tools import BroadPolicyTools  # noqa: E402
from test_broad_policy import policy  # noqa: E402


def test_scripted_artifact_submission(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    p = policy(["gt", ["feature", "checkpoint"], 2])
    (workspace / "fitted.json").write_text(json.dumps(p))
    host = BroadPolicyTools(workspace, tmp_path / "registry", lambda p, c: {"accepted": True})
    result = host.evaluate_broad_candidates({"policy_paths": ["fitted.json"]})
    assert result["candidates"][0]["metrics"] == {"accepted": True}
    assert json.loads(Path(result["candidates"][0]["artifact"]).read_text()) == p
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(p))
    (workspace / "escape").symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        host.evaluate_broad_candidates({"policy_paths": ["escape"]})
    with pytest.raises(ValueError, match="invalid candidate"):
        host.evaluate_broad_candidates({"commands": ["arbitrary code"]})
