import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fannagent.cli import app
from fannagent.config import load_config
from fannagent.errors import AgentError
from fannagent.store import Store, lock_owner_alive


def test_init_is_private_and_never_replaces_existing_configuration(tmp_path):
    path = tmp_path / "with spaces" / "fake.yaml"
    result = CliRunner().invoke(app, ["init", "--output", str(path)])
    assert result.exit_code == 0, result.output
    assert path.stat().st_mode & 0o777 == 0o600
    assert load_config(path).backend.name == "fake"
    original = path.read_bytes()
    result = CliRunner().invoke(app, ["init", "--output", str(path)])
    assert result.exit_code != 0
    assert path.read_bytes() == original


def test_doctor_creates_no_run_and_spends_no_money(tmp_path):
    path = tmp_path / "fake.yaml"
    runner = CliRunner()
    assert runner.invoke(app, ["init", "--output", str(path)]).exit_code == 0
    result = runner.invoke(app, ["doctor", str(path)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["ready"]
    assert list(tmp_path.iterdir()) == [path]


def test_process_lock_excludes_same_pid_owners_and_recovers_after_kill(tmp_path):
    root = tmp_path / "run"
    store = Store(root, create=True)
    # These independent handles have the same PID, as do many container entrypoints.
    with store.lease("run"):
        with pytest.raises(AgentError, match="already owns"):
            with Store(root).lease("run"):
                pass
    code = """
import sys,time
from pathlib import Path
from fannagent.store import Store
with Store(Path(sys.argv[1])).lease('run'):
    print('locked',flush=True)
    time.sleep(60)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(root)],
        stdout=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    try:
        assert process.stdout.readline().strip() == "locked"
        with pytest.raises(AgentError, match="already owns"):
            with store.lease("run"):
                pass
    finally:
        process.kill()
        process.wait(timeout=5)
    with store.lease("run"):
        assert store.get("config") is None


def test_live_legacy_owner_is_not_silently_replaced(tmp_path):
    store = Store(tmp_path / "run", create=True)
    with store.connect() as db:
        db.execute("INSERT INTO leases VALUES ('run','legacy',?,0)", (os.getpid(),))
    with pytest.raises(AgentError, match="legacy"):
        with store.lease("run"):
            pass


def test_busy_run_is_refused_before_sqlite_initialization(tmp_path, monkeypatch):
    store = Store(tmp_path / "run", create=True)
    with store.lease("run"):
        def forbidden(*args):
            raise AssertionError("busy run must not initialize writable SQLite")

        monkeypatch.setattr(Store, "connect", forbidden)
        with pytest.raises(AgentError, match="already owns"):
            Store(store.root)
        monkeypatch.undo()


def test_unreachable_docker_socket_does_not_reclaim_a_live_controller(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=1, stderr="dial unix /var/run/docker.sock: no such file or directory"))
    with pytest.raises(AgentError, match="cannot verify"):
        lock_owner_alive({"controller": "still-running"})


def test_bundle_verification_rejects_tampered_artifact(tmp_path):
    import hashlib
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "packaging/verify_bundle.py"
    spec = importlib.util.spec_from_file_location("verify_bundle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    artifact = tmp_path / "test.whl"
    artifact.write_bytes(b"original")
    manifest = {
        "schema_version": 1,
        "artifacts": {"test.whl": hashlib.sha256(artifact.read_bytes()).hexdigest()},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    identity = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:20]
    (tmp_path / "release-id").write_text(identity)
    assert module.verify(tmp_path) == identity
    artifact.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        module.verify(tmp_path)
