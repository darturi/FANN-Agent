from __future__ import annotations

from pathlib import Path

from ..api import AgentError
from ..store import ReadOnlyStore, Store, canonical
from .evaluate import OfflineEvaluator

CONTRACT = {"schema_version": 1, "format": "fannagent.learning.archive.v1"}
MARKER = "learning_archive_contract"
MAX_ARCHIVE_BYTES = 512 * 2**20


class CandidateArchive:
    """Content-addressed training records in a separate existing Store namespace."""

    def __init__(self, root: Path, *, create: bool = False, readonly: bool = False):
        root = root.resolve()
        if create and root.exists():
            raise AgentError("preserve the existing directory; open its learning archive instead")
        if readonly and create:
            raise AgentError("cannot create a read-only archive")
        if not create:
            view = ReadOnlyStore(root)
            if view.get(MARKER) != CONTRACT:
                raise AgentError("directory is not a learning archive; study runs are separate")
        self.store = ReadOnlyStore(root) if readonly else Store(root, create=create)
        self.readonly = readonly
        if create:
            self.store.set(MARKER, CONTRACT)

    def record(self, evaluator: OfflineEvaluator, raw: dict, *, fitting: dict | None = None):
        if self.readonly:
            raise AgentError("archive is read-only")
        fitting = {} if fitting is None else fitting
        if not isinstance(fitting, dict):
            raise AgentError("fitting provenance must be an object")
        if len(canonical(fitting)) > 8192:
            raise AgentError("fitting provenance exceeds 8 KiB")
        policy = evaluator.validate(raw)
        assessment = evaluator.evaluate(policy)
        candidate = {
            "schema_version": 1,
            "format": "fannagent.learning.candidate.v1",
            "policy": policy.serialize(),
            "policy_hash": policy.policy_hash,
            "evidence_hash": evaluator.evidence_hash,
            "fitting": fitting,
        }
        with self.store.lease("run"):
            corpus_ref = self.store.put(
                "learning_corpus",
                evaluator.evidence.model_dump(mode="json"),
                scope="development",
                limit=MAX_ARCHIVE_BYTES,
            )
            candidate_ref = self.store.put(
                "learning_candidate", candidate, scope="development", limit=MAX_ARCHIVE_BYTES
            )
            assessment_ref = self.store.put(
                "learning_assessment", assessment, scope="development", limit=MAX_ARCHIVE_BYTES
            )
            receipt = {
                "schema_version": 1,
                "format": "fannagent.learning.receipt.v1",
                "scope": "learning",
                "candidate": candidate_ref,
                "assessment": assessment_ref,
                "corpus": corpus_ref,
                "policy_hash": policy.policy_hash,
                "evidence_hash": evaluator.evidence_hash,
                "canonical_acceptance_established": False,
            }
            receipt_ref = self.store.put(
                "learning_receipt", receipt, scope="development", limit=MAX_ARCHIVE_BYTES
            )
            self.store.set("learning_receipt:" + receipt_ref, receipt_ref)
        return {"receipt": receipt_ref, **receipt}

    def read(self, receipt_ref: str):
        if self.store.get("learning_receipt:" + receipt_ref) != receipt_ref:
            raise AgentError("unknown learning receipt")
        receipt = self.store.read(receipt_ref, agent=True)
        self.store.read(receipt["corpus"], agent=True)
        candidate = self.store.read(receipt["candidate"], agent=True)
        assessment = self.store.read(receipt["assessment"], agent=True)
        if (
            receipt["corpus"] != receipt["evidence_hash"]
            or (
                candidate["evidence_hash"] != receipt["evidence_hash"]
                or candidate["policy_hash"] != receipt["policy_hash"]
            )
            or (
                assessment["policy_hash"] != receipt["policy_hash"]
                or assessment["evidence_hash"] != receipt["evidence_hash"]
            )
        ):
            raise AgentError("archive receipt bindings differ")
        return {"receipt": receipt, "candidate": candidate, "assessment": assessment}

    def list(self, *, offset: int = 0, limit: int = 20):
        if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 100:
            raise AgentError("archive pagination requires offset >= 0 and limit from 1 to 100")
        with self.store.connect() as db:
            rows = db.execute(
                "SELECT value FROM state WHERE key LIKE 'learning_receipt:%' "
                "ORDER BY key LIMIT ? OFFSET ?",
                (limit + 1, offset),
            ).fetchall()
        import json

        return {
            "receipts": [
                {"receipt": json.loads(r[0]), **self.store.read(json.loads(r[0]), agent=True)}
                for r in rows[:limit]
            ],
            "next_offset": offset + limit if len(rows) > limit else None,
        }

    def freeze_for_confirmation(self, receipt_ref: str):
        """Freeze one measured training candidate; this never runs confirmation."""
        if self.readonly:
            raise AgentError("archive is read-only")
        saved = self.read(receipt_ref)
        assessment = saved["assessment"]
        qualification = assessment.get("learning_qualification", {})
        required = ("activation-cold", "reused-warm")
        if not qualification.get("aggregate_quality_passed") or not all(
            qualification.get("regimes", {}).get(r, {}).get("training_feasible") is True
            for r in required
        ):
            raise AgentError("candidate needs complete aggregate quality and measured timing gains")
        selection = {
            "schema_version": 1,
            "scope": "learning",
            "status": "frozen_for_confirmation",
            "receipt": receipt_ref,
            "policy_hash": assessment["policy_hash"],
            "evidence_hash": assessment["evidence_hash"],
            "required_regimes": list(required),
            "confirmation_consumed": False,
            "canonical_acceptance_established": False,
        }
        with self.store.lease("run"):
            previous = self.store.get("learning_frozen_candidate")
            if previous is not None and previous != selection:
                raise AgentError("this study already froze a different candidate")
            self.store.set("learning_frozen_candidate", selection)
        return selection
