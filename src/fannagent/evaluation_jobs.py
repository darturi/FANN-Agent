"""Durable evaluation receipts and results; retrieval never reruns a measurement."""

from __future__ import annotations

import re
import time
import uuid

from .errors import AgentError
from .store import digest

BROKER_WAIT_SECONDS = 10800


class EvaluationJobs:
    def __init__(self, store):
        self.store = store
        self.active = None
        self.last_update = 0.0

    def status(self, identity):
        if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{32}", identity):
            raise AgentError("evaluation job_id must be 32 lowercase hexadecimal characters")
        record = self.store.get("evaluation_job:" + identity)
        if record is None:
            raise AgentError("unknown evaluation job_id")
        return {k: v for k, v in record.items() if k != "request_hash"}

    def begin(self, operation, args, identity=None):
        identity = identity or uuid.uuid4().hex
        if not re.fullmatch(r"[0-9a-f]{32}", identity):
            raise AgentError("invalid evaluation request identity")
        key = "evaluation_job:" + identity
        request_hash = digest({"operation": operation, "args": args})
        previous = self.store.get(key)
        if previous:
            if previous["request_hash"] != request_hash:
                raise AgentError("evaluation identity belongs to a different request")
            if previous["state"] == "completed":
                return identity, self.store.read(previous["response_artifact"])
            raise AgentError(
                f"evaluation {identity} already started; retrieve evaluation_status; do not replay"
            )
        self.store.set(
            key,
            {
                "job_id": identity,
                "operation": operation,
                "request_hash": request_hash,
                "state": "running",
                "phase": "starting",
                "started_at": time.time(),
                "do_not_replay": True,
            },
        )
        self.active = identity
        self.last_update = 0.0
        return identity, None

    def progress(self, phase, completed=0, total=None):
        if not self.active:
            return
        now = time.monotonic()
        if completed != total and now - self.last_update < 5:
            return
        key = "evaluation_job:" + self.active
        record = self.store.get(key)
        self.store.set(
            key,
            {
                **record,
                "phase": phase,
                "completed": completed,
                "total": total,
                "updated_at": time.time(),
            },
        )
        self.last_update = now

    def complete(self, identity, result):
        # calibrate already returns only its approved aggregate view. Never publish
        # the private calibration report or its measurement/diagnostic pointers.
        if self.store.get("evaluation_job:" + identity)["operation"] == "calibrate":
            result = {
                k: v
                for k, v in result.items()
                if k
                in {
                    "status",
                    "valid",
                    "groups",
                    "latencies",
                    "checkpoint_policy_hash",
                    "reviews_acceptance",
                    "experiment_event_id",
                }
            }
        full = self.store.put("evaluation_report", result, scope="development")
        response = {
            k: v
            for k, v in result.items()
            if k not in {"per_query_regressions", "compatibility", "extension_manifest"}
        }
        response.update(evaluation_job_id=identity, evaluation_report_artifact=full)
        response_artifact = self.store.put("evaluation_response", response, scope="development")
        key = "evaluation_job:" + identity
        self.store.set(
            key,
            {
                **self.store.get(key),
                "state": "completed",
                "phase": "finished",
                "finished_at": time.time(),
                "response_artifact": response_artifact,
                "result": response,
            },
        )
        self.active = None
        return response

    def fail(self, identity, response):
        key = "evaluation_job:" + identity
        self.store.set(
            key,
            {
                **self.store.get(key),
                "state": "failed",
                "finished_at": time.time(),
                "error": response,
            },
        )
        self.active = None
