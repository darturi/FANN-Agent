from __future__ import annotations

import json
import uuid
from decimal import ROUND_CEILING, Decimal

from .config import ModelConfig
from .errors import AgentError, BudgetExceeded
from .store import Store

SCALE = Decimal(1_000_000_000)


def units(value: Decimal) -> int:
    if not value.is_finite() or value < 0:
        raise AgentError("invalid charge")
    return int((value * SCALE).to_integral_value(rounding=ROUND_CEILING))


class Budget:
    def __init__(self, store: Store, config: ModelConfig, *, readonly: bool = False):
        self.store, self.config = store, config
        contract = config.model_dump(mode="json")
        existing = store.get("budget_contract")
        if existing is not None and existing != contract:
            raise AgentError("resume cannot change the spending contract")
        if not readonly:
            store.set("budget_contract", contract)

    def reserve(self, maximum: Decimal, metadata: dict | None = None) -> str:
        if self.store.get("provider_bound_failed"):
            raise AgentError("provider token-bound contract failed")
        amount = units(maximum)
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM charges WHERE status='bound_violation'").fetchone():
                raise AgentError("provider charge bound was violated")
            if db.execute("SELECT 1 FROM charges WHERE status='reserved'").fetchone():
                raise AgentError("one model request may be in flight")
            spent = db.execute(
                "SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM charges"
            ).fetchone()[0]
            if spent >= int(self.config.ceiling_usd * SCALE) or (
                spent + amount > int((self.config.ceiling_usd + self.config.allowance_usd) * SCALE)
            ):
                raise BudgetExceeded("monetary ceiling reached")
            identity = uuid.uuid4().hex
            db.execute(
                "INSERT INTO charges VALUES (?,?,NULL,'reserved',?)",
                (identity, amount, json.dumps(metadata or {})),
            )
        return identity

    def settle(self, identity: str, actual: Decimal, metadata: dict):
        amount = units(actual)
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM charges WHERE id=?", (identity,)).fetchone()
            if not row or row["status"] != "reserved":
                raise AgentError("charge is not an outstanding reservation")
            status = "settled" if amount <= row["reserved"] else "bound_violation"
            db.execute(
                "UPDATE charges SET actual=?,status=?,metadata=? WHERE id=?",
                (amount, status, json.dumps(metadata), identity),
            )
        if status != "settled":
            raise AgentError("provider exceeded its verified charge bound; further calls disabled")

    def uncertain(self, identity: str, reason: str):
        with self.store.connect() as db:
            db.execute(
                "UPDATE charges SET status='uncertain',metadata=? WHERE id=? AND status='reserved'",
                (json.dumps({"reason": reason}), identity),
            )

    def recover(self):
        with self.store.connect() as db:
            db.execute("UPDATE charges SET status='uncertain' WHERE status='reserved'")

    def summary(self) -> dict:
        with self.store.connect() as db:
            rows = [dict(row) for row in db.execute("SELECT * FROM charges")]
        return {
            "ceiling_usd": str(self.config.ceiling_usd),
            "allowance_usd": str(self.config.allowance_usd),
            "committed_usd": str(
                Decimal(
                    sum(r["actual"] if r["actual"] is not None else r["reserved"] for r in rows)
                )
                / SCALE
            ),
            "uncertain_calls": sum(r["status"] in {"uncertain", "reserved"} for r in rows),
            "calls": rows,
            "scope": "model API charges; database hosting excluded",
        }

    def maximum_call(self) -> Decimal:
        c = self.config
        if not c.bound_verified:
            raise AgentError("unverified provider bound")
        return (
            Decimal(c.input_token_bound) * c.input_usd_per_million
            + Decimal(c.output_token_limit) * c.output_usd_per_million
        ) / Decimal(1_000_000)
