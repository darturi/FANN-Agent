"""A bounded development tool interface. No provider, DB or serving operations."""

import re

from ..api import AgentError
from .archive import CandidateArchive
from .describe import describe_corpus
from .evaluate import OfflineEvaluator
from .returned_models import ReturnedFeedback


class LearningTools:
    def __init__(self, evaluator: OfflineEvaluator, archive: CandidateArchive | None = None):
        self.evaluator, self.archive = evaluator, archive

    def call(self, request: dict | str, args: dict | None = None):
        # FileBroker passes (operation, args); the CLI accepts the same request
        # as one JSON object. Both routes share this validation and scorer.
        if isinstance(request, str):
            if not isinstance(args, dict) or "operation" in args:
                raise AgentError("broker arguments must be an object without operation")
            request = {"operation": request, **args}
        elif args is not None:
            raise AgentError("supply either a request object or operation and arguments")
        if not isinstance(request, dict) or set(request) - {"operation", "policy", "receipt"}:
            raise AgentError("learning request permits operation, policy and receipt only")
        operation = request.get("operation")
        if operation == "inspect":
            if set(request) != {"operation"}:
                raise AgentError("inspect takes no policy or receipt")
            result = describe_corpus(self.evaluator.corpus)
            result["evidence_hash"] = self.evaluator.evidence_hash
            result["study_version"] = "measured-feedback-v2"
            result["criterion"] = (
                "Aggregate recall noninferiority overall and per filter; complete valid results; "
                "actual measured latency including activation. Per-query loss is diagnostic."
            )
            if isinstance(self.evaluator.evidence, ReturnedFeedback):
                result["original_campaign_budget"] = self.evaluator.evidence.import_receipt[
                    "budget_receipt"
                ]
            result["canonical_acceptance_established"] = False
            return result
        if operation in ("validate", "screen", "archive"):
            if set(request) != {"operation", "policy"}:
                raise AgentError("candidate operation requires exactly operation and policy")
            policy = self.evaluator.validate(request["policy"])
            if operation == "validate":
                return {"policy_hash": policy.policy_hash}
            if operation == "archive":
                if self.archive is None:
                    raise AgentError("archive operation requires a separate learning archive")
                return self.archive.record(
                    self.evaluator,
                    policy.serialize(),
                    fitting={"interface": "measured-feedback-v2"},
                )
            report = self.evaluator.evaluate(policy)
            return {
                "evidence_hash": report["evidence_hash"],
                "policy_hash": report["policy_hash"],
                "overall": report["overall"],
                "per_filter": report["per_filter"],
                "qualification": report["learning_qualification"],
                "timings": report["timings"],
                "feedback": report["feedback"],
                "measurement_request_count": len(report["measurement_requests"]),
                "canonical_acceptance_established": False,
            }
        if operation == "freeze":
            if (
                set(request) != {"operation", "receipt"}
                or self.archive is None
                or not isinstance(request["receipt"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", request["receipt"])
            ):
                raise AgentError("freeze requires a saved receipt and a learning archive")
            return self.archive.freeze_for_confirmation(request["receipt"])
        raise AgentError("operations: inspect, validate, screen, archive, freeze")
