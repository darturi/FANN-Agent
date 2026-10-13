"""Bounded hypothesis records and trusted operation outcomes in the existing store."""

from __future__ import annotations

import json
import time
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from .errors import AgentError
from .guidance import principle_ids, read_guidance
from .store import canonical, digest
from .submission import InvalidSubmission

Text = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=512)
]
Key = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-zA-Z0-9_-]{1,80}$")]
Reference = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128)]
EMPIRICAL = {
    "count",
    "descriptors",
    "probe",
    "screen",
    "audit",
    "labels",
    "development_evaluate",
    "calibrate",
}
PREFIX = "research_experiment:"
EVENT_PREFIX = "research_event:"
MAX_EXPERIMENTS = 1024
MAX_EVENTS = 10000
MAX_VIEW_BYTES = 48 * 1024


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Basis(Strict):
    kind: Literal["literature", "measurement", "exploratory"]
    principle_ids: list[Key] = Field(default_factory=list, max_length=16)
    evidence_refs: list[Reference] = Field(default_factory=list, max_length=16)


class Plan(Strict):
    client_key: Key
    purpose: Literal["investigation", "candidate_evaluation", "calibration"]
    hypothesis: Text
    why_now: Text
    basis: Basis
    comparison: Text
    measurements: Text
    expected_observation: Text
    challenging_observation: Text
    decision_if_supported: Text
    decision_if_challenged: Text


class Conclusion(Strict):
    assessment: Literal["supported", "challenged", "inconclusive"]
    observations: Text
    evidence_refs: list[Reference] = Field(max_length=32)
    decision: Text


def validated(cls, value, limit):
    try:
        if len(canonical(value)) > limit:
            raise InvalidSubmission("invalid_experiment", "experiment payload exceeds byte limit")
        return cls.model_validate(value).model_dump(mode="json")
    except (ValidationError, ValueError, TypeError, RecursionError) as exc:
        details = (
            [
                {"path": ".".join(map(str, e["loc"])), "message": e["msg"]}
                for e in exc.errors(include_input=False)[:5]
            ]
            if isinstance(exc, ValidationError)
            else []
        )
        raise InvalidSubmission(
            "invalid_experiment",
            "invalid experiment fields",
            details=details,
            hint="Use the experiment schema from the pinned protocol.",
        ) from None


def records(store, prefix):
    with store.connect() as db:
        rows = db.execute(
            "SELECT value FROM state WHERE key LIKE ? ORDER BY key", (prefix + "%",)
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def compact_observation(store, operation, result):
    # Calibration has an explicit allowlist: no private report pointers or rows.
    if operation == "calibrate":
        result = {
            key: result[key]
            for key in ("status", "valid", "groups", "latencies", "checkpoint_policy_hash")
            if key in result
        }
    references = []

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"artifact", "rows", "diagnostics"} and isinstance(child, str):
                    try:
                        store.read(child, agent=True)
                    except AgentError:
                        continue
                    references.append(child)
                elif isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(result)
    if len(canonical(result)) > 12288:
        result = {
            "truncated": True,
            "artifact_refs": sorted(set(references))[:32],
            **{key: result[key] for key in ("status", "valid") if key in result},
        }
    return result, sorted(set(references))[:32]


class ExperimentJournal:
    def __init__(self, store):
        self.store = store
        self.mode = read_guidance(store)["mode"]
        self.required = self.mode != "baseline"

    def _get(self, identity):
        record = self.store.get(PREFIX + str(identity))
        if not record:
            raise InvalidSubmission("invalid_experiment", "unknown experiment")
        return record

    def _resolve(self, args):
        if args.get("experiment_id"):
            return self._get(args["experiment_id"])
        key = args.get("client_key")
        for record in records(self.store, PREFIX):
            if record["plan"]["client_key"] == key:
                return record
        raise InvalidSubmission("invalid_experiment", "supply experiment_id or a known client_key")

    def _save(self, record, *, updates=None):
        # SQLite retains the bounded record even when artifact capacity is exhausted.
        try:
            artifact = self.store.put(
                "experiment_record",
                {
                    "view": "development_experiment_record",
                    **record,
                },
                scope="development",
            )
            record = {**record, "artifact": artifact}
        except AgentError as exc:
            record = {**record, "storage_failure": str(exc)[:256]}
        self.store.set_many({PREFIX + record["experiment_id"]: record, **(updates or {})})
        return record

    def events(self, identity=None):
        prefix = EVENT_PREFIX + (identity + ":" if identity else "")
        return sorted(records(self.store, prefix), key=lambda e: e["sequence"])

    def start(self, raw):
        plan = validated(Plan, raw, 6144)
        known = records(self.store, PREFIX)
        for record in known:
            if record["plan"]["client_key"] == plan["client_key"]:
                if record["plan"] != plan:
                    raise InvalidSubmission(
                        "invalid_experiment", "client_key already has another plan"
                    )
                return record
        if len(known) >= MAX_EXPERIMENTS:
            raise AgentError("experiment journal reached its record limit")
        if self.store.get("research_active_experiment"):
            raise InvalidSubmission("invalid_experiment", "finish the open experiment first")
        basis = plan["basis"]
        if set(basis["principle_ids"]) - principle_ids(self.store):
            raise InvalidSubmission("invalid_experiment", "unknown or unavailable principle ID")
        if basis["kind"] == "literature" and not (
            set(basis["principle_ids"]) & principle_ids(self.store, "literature_finding")
        ):
            raise InvalidSubmission(
                "invalid_experiment", "literature basis needs a cited literature principle"
            )
        if basis["kind"] == "measurement" and not basis["evidence_refs"]:
            raise InvalidSubmission(
                "invalid_experiment", "measurement basis needs development evidence"
            )
        for reference in basis["evidence_refs"]:
            try:
                self.store.read(reference, agent=True)
            except AgentError:
                raise InvalidSubmission(
                    "invalid_experiment", "basis evidence is unavailable in development scope"
                ) from None
        identity = uuid.uuid4().hex
        return self._save(
            {
                "experiment_id": identity,
                "plan": plan,
                "state": "open",
                "created_at": time.time(),
            },
            updates={"research_active_experiment": identity},
        )

    def before(self, study, operation, args):
        identity = self.store.get("research_active_experiment")
        if self.required and operation in EMPIRICAL and not identity:
            raise InvalidSubmission(
                "experiment_required",
                "register a hypothesis before measurements",
                hint="Call experiment with action=start and a bounded plan.",
            )
        if operation not in EMPIRICAL and not (operation == "validate" and identity):
            return None
        if identity and self._get(identity)["state"] != "open":
            raise AgentError("active experiment is not open")
        query_hash = digest(study.permitted(args["query"])) if "query" in args else None
        policy_hash = (
            study.backend.validate_policy(args["policy"]).policy_hash
            if args.get("policy")
            else None
        )
        sequence = self.store.get("research_event_sequence", 0) + 1
        if sequence > MAX_EVENTS:
            if self.required:
                raise AgentError("experiment journal reached its operation limit")
            return None  # Observational recording must not impose a new baseline limit.
        event = {
            "event_id": "evt_" + uuid.uuid4().hex,
            "experiment_id": identity,
            "sequence": sequence,
            "operation": operation,
            "state": "pending",
            "query_hash": query_hash,
            "policy_hash": policy_hash,
            "started_at": time.time(),
            "artifact_refs": [],
        }
        key = EVENT_PREFIX + (identity or "unplanned") + ":" + event["event_id"]
        self.store.set_many({key: event, "research_event_sequence": sequence})
        return key, event

    def after(self, pending, *, result=None, error=None):
        if pending is None:
            return None
        key, event = pending
        event = {**event, "state": "failed" if error else "success", "finished_at": time.time()}
        if error:
            info = getattr(error, "info", {"code": type(error).__name__})
            if len(canonical(info)) > 12288:
                info = {
                    "code": str(info.get("code", type(error).__name__))[:128],
                    "truncated": True,
                }
            event["error"] = info
        else:
            observation, refs = compact_observation(self.store, event["operation"], result)
            event.update(observation=observation, artifact_refs=refs)
        if self.required:
            try:
                event["observation_artifact"] = self.store.put(
                    "experiment_observation",
                    {
                        "view": "development_experiment_observation",
                        **event,
                    },
                    scope="development",
                )
            except AgentError as exc:
                event["storage_failure"] = str(exc)[:256]
        self.store.set(key, event)
        return event["event_id"]

    def finish(self, args):
        record = self._resolve(args)
        conclusion = validated(Conclusion, args.get("conclusion"), 4096)
        events = self.events(record["experiment_id"])
        if "$latest" in conclusion["evidence_refs"]:
            if not events:
                raise InvalidSubmission(
                    "invalid_experiment", "experiment has no recorded observation"
                )
            conclusion["evidence_refs"] = [
                events[-1]["event_id"] if ref == "$latest" else ref
                for ref in conclusion["evidence_refs"]
            ]
        if record["state"] == "completed":
            if conclusion == record["conclusion"]:
                return record
            raise InvalidSubmission("invalid_experiment", "conclusion is immutable")
        if record["state"] != "open":
            raise InvalidSubmission("invalid_experiment", "experiment is interrupted")
        allowed = set(record["plan"]["basis"]["evidence_refs"])
        for event in events:
            allowed.add(event["event_id"])
            allowed.update(event["artifact_refs"])
            if event.get("observation_artifact"):
                allowed.add(event["observation_artifact"])
        if set(conclusion["evidence_refs"]) - allowed:
            raise InvalidSubmission(
                "invalid_experiment", "conclusion references unrecorded evidence"
            )
        if events and not conclusion["evidence_refs"]:
            raise InvalidSubmission("invalid_experiment", "cite a recorded observation")
        if any(event["state"] == "pending" for event in events):
            raise InvalidSubmission("invalid_experiment", "an operation is still pending")
        updates = {"research_active_experiment": None}
        for event in events:
            observation = event.get("observation", {})
            if (
                event["operation"] == "calibrate"
                and event["state"] == "success"
                and observation.get("status") == "accepted"
                and observation.get("valid") is True
            ):
                updates["research_candidate_origin:" + event["policy_hash"]] = {
                    "experiment_id": record["experiment_id"],
                    "event_id": event["event_id"],
                    "policy_hash": event["policy_hash"],
                }
        return self._save(
            {**record, "state": "completed", "conclusion": conclusion, "finished_at": time.time()},
            updates=updates,
        )

    def call(self, args):
        action = args.get("action")
        if not isinstance(action, str):
            raise InvalidSubmission("invalid_experiment", "action must be a string")
        allowed = {
            "start": {"action", "plan"},
            "finish": {"action", "experiment_id", "client_key", "conclusion"},
            "get": {"action", "experiment_id", "client_key", "offset", "limit"},
            "list": {"action", "offset", "limit"},
        }.get(action)
        if allowed is None:
            raise InvalidSubmission(
                "invalid_experiment", "action must be start, finish, get, or list"
            )
        if set(args) - allowed:
            raise InvalidSubmission("invalid_experiment", "unknown experiment arguments")
        if action == "start":
            return self.start(args.get("plan"))
        if action == "finish":
            return self.finish(args)
        try:
            offset = max(0, int(args.get("offset", 0)))
            limit = min(100, max(1, int(args.get("limit", 20))))
        except (ValueError, TypeError, OverflowError):
            raise InvalidSubmission("invalid_experiment", "invalid offset or limit") from None
        if action == "get":
            record = self._resolve(args)
            events = self.events(record["experiment_id"])
            page = []
            for event in events[offset : offset + limit]:
                if len(canonical({**record, "events": [*page, event]})) > MAX_VIEW_BYTES - 512:
                    break
                page.append(event)
            end = offset + len(page)
            return {
                **record,
                "events": page,
                "total_events": len(events),
                "next_offset": end if end < len(events) else None,
            }
        entries = records(self.store, PREFIX)
        page = []
        for entry in entries[offset : offset + limit]:
            item = {
                "experiment_id": entry["experiment_id"],
                "state": entry["state"],
                "client_key": entry["plan"]["client_key"],
                "hypothesis": entry["plan"]["hypothesis"],
            }
            if len(canonical([*page, item])) > MAX_VIEW_BYTES - 512:
                break
            page.append(item)
        end = offset + len(page)
        return {
            "experiments": page,
            "total_experiments": len(entries),
            "next_offset": end if end < len(entries) else None,
        }

    def require_candidate(self, policy_hash):
        if not self.required:
            return
        if self.store.get("research_active_experiment"):
            raise InvalidSubmission("invalid_experiment", "finish the experiment before submit")
        origin = self.store.get("research_candidate_origin:" + policy_hash)
        if not origin or self._get(origin["experiment_id"])["state"] != "completed":
            raise InvalidSubmission(
                "invalid_experiment", "candidate needs a completed calibrated experiment"
            )

    def recover(self):
        for event in self.events():
            if event["state"] == "pending":
                key = (
                    EVENT_PREFIX + (event["experiment_id"] or "unplanned") + ":" + event["event_id"]
                )
                self.store.set(
                    key,
                    {
                        **event,
                        "state": "unknown",
                        "reason": "controller interrupted; measurement not replayed",
                    },
                )

    def interrupt(self, reason, *, terminal):
        identity = self.store.get("research_active_experiment")
        if not identity:
            return
        record = self._get(identity)
        updates = {"research_active_experiment": None} if terminal else {}
        self._save(
            {
                **record,
                "state": "interrupted" if terminal else "open",
                "interruption_reason": reason,
            },
            updates=updates,
        )

    def summary(self):
        state = read_guidance(self.store)
        entries = records(self.store, PREFIX)
        events = self.events()
        origins = records(self.store, "research_candidate_origin:")
        return {
            "mode": state["mode"],
            "research_protocol_version": state["research_protocol_version"],
            "guidance_recorded": self.store.get("research_guidance") is not None,
            "primer_hash": state.get("primer_hash"),
            "system_prompt_hash": state.get("system_prompt_hash"),
            "experiments": {
                status: sum(e["state"] == status for e in entries)
                for status in ("open", "completed", "interrupted")
            },
            "operations": {
                status: sum(e["state"] == status for e in events)
                for status in ("pending", "success", "failed", "unknown")
            },
            "active_experiment": self.store.get("research_active_experiment"),
            "candidate_origins": origins,
        }


def scripted_plan(key, purpose="investigation"):
    return {
        "client_key": key,
        "purpose": purpose,
        "hypothesis": "The profile candidate preserves default recall while stopping earlier.",
        "why_now": "Check the provided candidate with actual permitted evidence.",
        "basis": {"kind": "exploratory", "principle_ids": [], "evidence_refs": []},
        "comparison": "Compare ordinary default execution and the selected profile candidate.",
        "measurements": "Inspect checkpoint evidence, recall and complete latency.",
        "expected_observation": "Calibration accepts the profile candidate.",
        "challenging_observation": "Recall loss, invalid results or no latency improvement.",
        "decision_if_supported": "Select the passing candidate after calibration.",
        "decision_if_challenged": "Reject the candidate or abstain.",
    }


def scripted_conclusion():
    return {
        "assessment": "inconclusive",
        "observations": "Recorded deterministic demonstration "
        "evidence; study calibration remains authoritative.",
        "evidence_refs": ["$latest"],
        "decision": "Use the actual calibration result to decide candidate eligibility.",
    }
