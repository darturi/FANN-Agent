"""Reproduce lifecycle edge cases without a provider or Docker connection."""
import json
import tempfile
import threading
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fannagent.backends.fake import extension
from fannagent.broker import FileBroker
from fannagent.cli import clean
from fannagent.client import open_session
from fannagent.config import RunConfig
from fannagent.controller import explore, open_run
from fannagent.errors import AgentError
from psycopg.conninfo import conninfo_to_dict, make_conninfo

OUTPUT = Path(__file__).resolve().parent
results = {}


class Environment:
    created = False
    closed = False

    def __init__(self, *args):
        Environment.created = True

    def close(self):
        Environment.closed = True


with tempfile.TemporaryDirectory(prefix="fannagent-audit-") as folder:
    config = RunConfig(
        backend={"name": "fake"},
        model={"model": "audit/test", "ceiling_usd": "1", "input_usd_per_million": "1",
               "output_usd_per_million": "1", "input_token_bound": 100000,
               "pricing_revision": "audit", "bound_verified": True},
        workload={"count": 100, "warmups": 0, "passes": 1},
    )
    config, store, backend = open_run(Path(folder)/"run", config)
    store.set("prepared", backend.prepare_copy().serialize())
    trajectory = store.put("trajectory", {"audit": "corrupted saved trajectory"})
    store.set("trajectory", trajectory)
    with patch("fannagent.controller.ContainerEnvironment", Environment), \
         patch("fannagent.model.BudgetedModel"):
        try:
            explore(config, store, backend, resume=True)
        except KeyError:
            pass
        else:
            raise AssertionError("expected invalid saved trajectory to fail")
    results["resume_initialization"] = {"sandbox_created": Environment.created,
                                        "sandbox_closed": Environment.closed}

    manifest = extension.manifest()

    class ChangedDescriptor:
        def manifest(self):
            return replace(manifest, runtime_profile=manifest.runtime_profile.model_copy(
                update={"checkpoint_interval": 9}))

    with patch("fannagent.controller.extension", return_value=ChangedDescriptor()):
        try:
            clean(store.root)
        except AgentError as exc:
            results["cleanup_after_profile_upgrade"] = str(exc)
        else:
            raise AssertionError("expected profile change to block cleanup")


class FailingSessionBackend:
    closed = False

    def describe_capabilities(self):
        return backend.describe_capabilities()

    def compatibility(self):
        raise RuntimeError("connection lost during compatibility check")

    def close(self):
        self.closed = True


class SessionStore:
    def get(self, key, default=None):
        return {"prepared": {"qualified": True}, "deployment": {"compatibility": {}}}.get(key, default)


session_backend = FailingSessionBackend()
with patch("fannagent.client.open_run", return_value=(None, SessionStore(), session_backend)):
    try:
        open_session("unused")
    except RuntimeError:
        results["session_failure_closed_backend"] = session_backend.closed

original = conninfo_to_dict("host=source.example hostaddr=192.0.2.20 user=example dbname=example require_auth=scram-sha-256")
copied = {**original, "host": "127.0.0.1", "port": "54321", "sslmode": "disable",
          "dbname": "example", "user": "example"}
results["copy_dsn_retains_source_parameters"] = conninfo_to_dict(make_conninfo(**copied))

started, finish = threading.Event(), threading.Event()


class SlowTools:
    def call(self, operation, args):
        started.set()
        finish.wait(2)
        return {"finished": True}


with tempfile.TemporaryDirectory(prefix="fannagent-broker-audit-") as folder:
    broker = FileBroker(SlowTools(), Path(folder)/"broker")
    broker.__enter__()
    (broker.folder/("0"*32+".request")).write_text(json.dumps({
        "token": broker.token, "operation": "slow", "args": {}}))
    assert started.wait(1)
    closing = threading.Thread(target=broker.__exit__, args=(None, None, None))
    closing.start()
    closing.join(0.05)
    results["broker_shutdown_during_tool"] = {
        "stop_requested": broker.stop.is_set(),
        "tool_thread_running": broker.thread.is_alive(),
        "shutdown_waiting_for_tool": closing.is_alive(),
    }
    finish.set()
    closing.join(2)
    assert not closing.is_alive()

(OUTPUT/"core-audit-observations.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
