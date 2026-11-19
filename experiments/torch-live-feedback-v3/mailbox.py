"""Typed file mailbox. This command never submits jobs or executes supplied code."""

import argparse
import re
import sys
import time
from pathlib import Path

from limits import DEVELOPMENT_SECONDS, SCHEMA, canonical, digest, read, write


def dispatch(stage, operation, identity=None, payload=None):
    stage = Path(stage)
    job = (stage / "job-id").read_text().strip()
    if not re.fullmatch(r"[1-9][0-9]*", job):
        raise ValueError("missing numeric submission binding")
    run = stage / ("run-" + job)
    if not (run / "state.json").exists():
        if operation != "status":
            raise ValueError("worker has not started; do not send a candidate yet")
        return {"status": "not_started", "job_id": job}
    state = read(run / "state.json")
    elapsed = max(0, time.time() - state["started_epoch"])
    state["work_remaining_seconds"] = max(0, state["work_seconds"] - elapsed)
    state["accepting_requests"] = (
        state["status"] == "running" and elapsed < state["admission_seconds"]
    )
    state["accepting_development"] = state["accepting_requests"] and elapsed < state.get(
        "development_seconds", DEVELOPMENT_SECONDS
    )
    if state["job_id"] != job:
        raise ValueError("worker/submission identity differs")
    if operation == "status":
        return state
    if operation == "heartbeat":
        if not state["accepting_requests"] or state.get("final_started"):
            raise ValueError("worker is closed; heartbeat cannot reopen it")
        write(run / "controller-heartbeat.json", {"job_id": job, "epoch": time.time()})
        return {
            "status": "controller_active",
            "job_id": job,
            "work_remaining_seconds": state["work_remaining_seconds"],
        }
    if not identity or not re.fullmatch(r"[0-9a-f]{32}", identity):
        raise ValueError("32-character request identity required")
    folder = run / "requests" / identity
    if operation == "result":
        return (
            read(folder / "response.json")
            if (folder / "response.json").is_file()
            else {
                "status": "pending" if state["status"] == "running" else "worker_stopped",
                "request_id": identity,
                "worker": state,
            }
        )
    if operation != "submit":
        raise ValueError("only status, submit and result are exposed")
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema", "policies", "mode"}
        or payload["schema"] != SCHEMA
        or not isinstance(payload["policies"], list)
        or not 1 <= len(payload["policies"]) <= 3
        or payload["mode"] not in ("qualification", "development", "final")
        or payload["mode"] == "final"
        and len(payload["policies"]) != 1
        or len(canonical(payload)) > 25 * 1024**2
    ):
        raise ValueError("one to three bounded DSL policies required")
    if folder.exists():
        prior = read(folder / "request.json")
        if prior["payload_sha256"] != digest(payload):
            raise ValueError("request identity already belongs to another payload")
        return {"status": "already_registered", "request_id": identity}
    if not state["accepting_requests"]:
        raise ValueError("worker is not accepting work")
    if payload["mode"] == "development" and not state["accepting_development"]:
        raise ValueError("development admission closed; wall time reserved for frozen comparison")
    if state.get("final_started"):
        raise ValueError("final policy is frozen; no further development or final requests")
    folder.mkdir(mode=0o700)
    write(
        folder / "request.json",
        {
            "request_id": identity,
            "job_id": job,
            "payload_sha256": digest(payload),
            "payload": payload,
        },
    )
    # The worker watches only this marker, which is published after the fsynced JSON.
    (folder / "ready").touch(mode=0o600)
    return {"status": "registered", "request_id": identity}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("operation", choices=("status", "submit", "result", "heartbeat"))
    parser.add_argument("--identity")
    args = parser.parse_args()
    payload = None
    if args.operation == "submit":
        data = sys.stdin.buffer.read(25 * 1024**2 + 1)
        if len(data) > 25 * 1024**2:
            raise ValueError("payload too large")
        import json

        payload = json.loads(data)
    print(canonical(dispatch(args.stage, args.operation, args.identity, payload)).decode())


if __name__ == "__main__":
    main()
