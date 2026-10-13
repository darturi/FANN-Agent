import json
import os
import subprocess
import sys
from pathlib import Path

from fannagent import tool_client
from fannagent.broker import FileBroker


class EchoTools:
    def __init__(self):
        self.calls = []

    def call(self, operation, args):
        self.calls.append((operation, args))
        return {"payload": "x" * 100_000}


def test_missing_response_read_waits_without_replaying_request(tmp_path, monkeypatch, capsys):
    tools = EchoTools()
    queue = tmp_path / "queue"
    real_read = Path.read_text
    delayed_reads = 0

    def read_text(path, *args, **kwargs):
        nonlocal delayed_reads
        if path.name.endswith(".response.ready") and path.exists() and delayed_reads < 2:
            delayed_reads += 1
            raise FileNotFoundError(path)
        return real_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(sys, "argv", ["fannagent-tool", "queries", "{}"])
    with FileBroker(tools, queue) as broker:
        monkeypatch.setenv("FANNAGENT_QUEUE", str(queue))
        monkeypatch.setenv("FANNAGENT_TOKEN", broker.token)
        tool_client.main()
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] and len(result["result"]["payload"]) == 100_000
    assert delayed_reads == 2
    assert tools.calls == [("queries", {})]
    assert not list(queue.iterdir())


def test_closed_output_pipe_does_not_fail_or_replay_tool(tmp_path):
    tools = EchoTools()
    queue = tmp_path / "queue"
    with FileBroker(tools, queue) as broker:
        client = subprocess.Popen(
            [sys.executable, tool_client.__file__, "queries", "{}"],
            env={**os.environ, "FANNAGENT_QUEUE": str(queue), "FANNAGENT_TOKEN": broker.token},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            client.stdout.close()
            assert client.wait(timeout=5) == 0
            assert client.stderr.read() == b""
        finally:
            if client.poll() is None:
                client.kill()
                client.wait(timeout=5)
            client.stderr.close()
    assert tools.calls == [("queries", {})]
    assert not list(queue.iterdir())


def test_queue_waits_past_one_hour_without_another_request(tmp_path, monkeypatch, capsys):
    tools = EchoTools()
    queue = tmp_path / "queue"
    real_read = Path.read_text
    attempts = 0
    clock = iter([0, 3700, 4620])

    def read_text(path, *args, **kwargs):
        nonlocal attempts
        if path.name.endswith(".response.ready") and attempts < 2:
            attempts += 1
            raise FileNotFoundError(path)
        return real_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(tool_client.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(sys, "argv", ["fannagent-tool", "queries", "{}"])
    with FileBroker(tools, queue) as broker:
        monkeypatch.setenv("FANNAGENT_QUEUE", str(queue))
        monkeypatch.setenv("FANNAGENT_TOKEN", broker.token)
        tool_client.main()
    assert json.loads(capsys.readouterr().out)["ok"]
    assert tools.calls == [("queries", {})]
