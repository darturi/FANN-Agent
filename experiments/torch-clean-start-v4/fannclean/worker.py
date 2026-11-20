"""One serial, finite-clock worker. No scheduler or model-provider client."""

import argparse
import fcntl
import json
import sys
import time
from pathlib import Path

from .core import Limits, digest, read, verify_initial, write
from .deploy import ContainerExecutor, verify_package, verify_running_code
from .engine import Engine
from .transport import require_authorization


def status(root):
    root = Path(root)
    p = root / "private/worker.json"
    if not p.exists():
        return {"status": "not_started"}
    s = read(p)
    limits = Limits(**read(root / "config.json")["limits"])
    elapsed = max(0, time.time() - s["started_epoch"])
    ledger = (
        read(root / "private/query-ledger.json")
        if (root / "private/query-ledger.json").exists()
        else {"charged": 0}
    )
    development = read(root / "agent/task.json")["queries"]
    cached = {p.name for p in (root / "private/cache").glob("*.json")}
    missing = sum(digest(c["handle"]) + ".json" not in cached for c in development)
    minimum_confirmation = 2 * missing + 2 * len(development) + 18 * min(len(development), 672) + 70
    return {
        **s,
        "discovery_seconds_remaining": max(0, limits.discovery_seconds - elapsed),
        "wall_seconds_remaining": max(0, limits.wall_seconds - elapsed),
        "discovery_queries_remaining": max(
            0, limits.query_cap - limits.final_reserve - ledger["charged"]
        ),
        "minimum_action_queries": 50,
        "minimum_confirmation_queries": minimum_confirmation,
        "queries_charged": ledger["charged"],
        "final_reserved": limits.final_reserve,
    }


def dispatch(root, operation, identity=None, payload=None):
    root = Path(root)
    if operation == "status":
        return status(root)
    s = status(root)
    if operation == "freeze":
        from fannagent.api.broad_policy import validate

        freeze, closed = payload["freeze"], payload["model_closed"]
        if (
            s["status"] != "running"
            or s["wall_seconds_remaining"] <= 60
            or freeze["run_id"] != s["run_id"]
            or freeze.get("test_feedback_seen") is not False
        ):
            raise ValueError("invalid/late policy freeze")
        if (
            closed.get("run_id") != s["run_id"]
            or closed.get("model_closed") is not True
            or closed.get("freeze_sha256") != digest(freeze)
        ):
            raise ValueError("close the matching model conversation before attaching any oracle")
        if (root / "private/final-freeze.json").exists() or (
            root / "private/comparison.json"
        ).exists():
            raise ValueError("comparison/freeze already attached; no replacement")
        if any((root / "private/queue").glob("*/ready")):
            raise ValueError("discovery requests still queued")
        ledger = root / "private/query-ledger.json"
        if ledger.exists() and any(
            r["status"] == "open" for r in read(ledger)["requests"].values()
        ):
            raise ValueError("discovery request uncertain; cannot finalize")
        validate(freeze["policy"])
        for key in ("oracle_full", "oracle_test"):
            validate(payload[key])
        write(
            root / "private/comparison.json",
            {
                "agent_freeze_sha256": digest(freeze),
                "oracle_full": payload["oracle_full"],
                "oracle_test": payload["oracle_test"],
            },
        )
        write(root / "private/final-freeze.json", freeze)
        return {"status": "frozen", "run_id": s["run_id"], "freeze_sha256": digest(freeze)}
    if operation == "report":
        from .report import analyze

        if s["status"] != "completed_frozen_comparison":
            raise ValueError("no complete frozen comparison available")
        return analyze(root)
    if operation == "heartbeat":
        if s["status"] != "running":
            raise ValueError("heartbeat cannot revive a closed worker")
        write(root / "private/heartbeat.json", {"epoch": time.time(), "run_id": s["run_id"]})
        return {"status": "active"}
    if (
        not isinstance(identity, str)
        or len(identity) != 32
        or any(c not in "0123456789abcdef" for c in identity)
    ):
        raise ValueError("request identity required")
    directory = root / "private/queue" / identity
    if operation == "result":
        if (directory / "response.json").exists():
            return read(directory / "response.json")
        return {
            "status": "pending" if s["status"] == "running" else "worker_stopped",
            "request_id": identity,
            "payload_sha256": read(directory / "request.json")["payload_sha256"],
        }
    if operation != "submit" or s["status"] != "running" or s["wall_seconds_remaining"] <= 60:
        raise ValueError("worker is not admitting actions")
    if directory.exists():
        if read(directory / "request.json")["payload_sha256"] != digest(payload):
            raise ValueError("identity already belongs to a different action")
        return {"status": "already_registered"}
    if payload["kind"] != "final" and s["discovery_seconds_remaining"] <= 60:
        raise ValueError("discovery deadline; time reserved for final comparison")
    engine = Engine(root, None)
    _, worst = engine.validate_request(payload)
    engine.ledger.check_available(worst, payload["kind"] == "final")
    if payload["kind"] == "final" and (
        not (root / "private/final-freeze.json").exists()
        or read(root / "private/final-freeze.json")["policy"] != payload["policies"][0]
    ):
        raise ValueError("final request must match the frozen policy")
    if payload["kind"] == "final" and (
        (root / "private/final-started.json").exists()
        or any(
            read(p).get("payload", {}).get("kind") == "final"
            for p in (root / "private/queue").glob("*/request.json")
        )
    ):
        raise ValueError("one final attempt only")
    if (root / "private/final-freeze.json").exists() and payload["kind"] != "final":
        raise ValueError("final artifact frozen; no more discovery")
    write(
        directory / "request.json",
        {
            "run_id": s["run_id"],
            "request_id": identity,
            "payload": payload,
            "payload_sha256": digest(payload),
        },
    )
    (directory / "ready").touch()
    return {"status": "registered", "request_id": identity}


def serve(root, *, executor=None, clock=time.time, sleep=time.sleep):
    root = Path(root)
    require_authorization(root)
    verify_package(root)
    verify_initial(root)
    # Never adopt an earlier worker/cache, including a cache with edited run-id fields.
    for name in ("worker.json", "query-ledger.json", "cache", "requests", "builds"):
        if (root / "private" / name).exists():
            raise ValueError("fresh worker required; existing empirical state cannot be imported")
    lock = (root / "private/worker.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    config = read(root / "config.json")
    limits = Limits(**config["limits"])
    state = {"status": "running", "run_id": config["run_id"], "started_epoch": clock()}
    write(root / "private/worker.json", state)
    executor = executor or ContainerExecutor(root)
    last = clock()
    try:
        while clock() - state["started_epoch"] < limits.wall_seconds - 60:
            waiting = sorted((root / "private/queue").glob("*/ready"))
            if not waiting:
                heartbeat = root / "private/heartbeat.json"
                active = (
                    heartbeat.exists()
                    and read(heartbeat).get("run_id") == state["run_id"]
                    and clock() - read(heartbeat)["epoch"] < 900
                )
                if clock() - last > 900 and not active:
                    state["status"] = "stopped_idle"
                    break
                sleep(2)
                continue
            directory = waiting[0].parent
            waiting[0].rename(directory / "claimed")
            request = read(directory / "request.json")
            payload, identity = request["payload"], request["request_id"]
            try:
                if request["run_id"] != state["run_id"] or request["payload_sha256"] != digest(
                    payload
                ):
                    raise ValueError("request binding changed")
                remaining = limits.wall_seconds - (clock() - state["started_epoch"]) - 60
                if payload["kind"] != "final":
                    remaining = min(
                        remaining, limits.discovery_seconds - (clock() - state["started_epoch"])
                    )
                if remaining <= 60:
                    raise ValueError("request no longer fits its time envelope")
                result = executor(identity, payload, remaining)
                if not result.get("private_cleanup_verified"):
                    raise ValueError("native cleanup did not verify")
                write(directory / "response.json", result)
                if payload["kind"] == "final":
                    state["status"] = "completed_frozen_comparison"
                    break
            except BaseException as error:
                write(
                    directory / "response.json",
                    {
                        "status": "failed",
                        "run_id": state["run_id"],
                        "request_id": identity,
                        "payload_sha256": digest(payload),
                        "error": str(error),
                        "automatic_retry": False,
                    },
                )
                state["status"] = "stopped_action_failure"
                break
            last = clock()
    finally:
        if state["status"] == "running":
            state["status"] = "stopped_deadline"
        write(root / "private/worker.json", state)
        lock.close()
    return state


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "operation",
        choices=("serve", "status", "heartbeat", "submit", "result", "freeze", "report"),
    )
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--identity")
    a = p.parse_args()
    payload = None
    if a.operation in ("submit", "freeze"):
        raw = sys.stdin.buffer.read(40 * 1024**2 + 1)
        if len(raw) > 40 * 1024**2:
            raise ValueError("request exceeds wire bound")
        payload = json.loads(raw)
    try:
        if a.operation == "serve":
            verify_running_code(a.root)
        answer = (
            serve(a.root)
            if a.operation == "serve"
            else dispatch(a.root, a.operation, a.identity, payload)
        )
    except (ValueError, KeyError, TypeError) as error:
        if a.operation != "submit":
            raise
        directory = a.root / "private/queue" / str(a.identity)
        if (directory / "ready").exists() or (directory / "claimed").exists():
            raise
        answer = {
            "status": "rejected",
            "error": str(error),
            "request_id": a.identity,
            "run_id": read(a.root / "config.json")["run_id"],
            "payload_sha256": digest(payload),
        }
    print(json.dumps(answer))


if __name__ == "__main__":
    main()
