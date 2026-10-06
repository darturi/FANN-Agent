from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BackendConfig(Strict):
    name: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_-]*$")
    options: dict = Field(default_factory=dict)


class ResourcesConfig(Strict):
    cpus: float = Field(default=4, gt=0)
    memory_gib: int = Field(default=8, gt=0)


class EvidenceConfig(Strict):
    max_bytes: int = Field(default=2 * 1024**3, gt=0)
    trace_max_bytes: int = Field(default=64 * 1024**2, gt=0, le=64 * 1024**2)


class ModelConfig(Strict):
    model: str = "scripted"
    ceiling_usd: Decimal
    allowance_usd: Decimal = Decimal("1")
    input_usd_per_million: Decimal | None = None
    output_usd_per_million: Decimal | None = None
    input_token_bound: int | None = Field(default=None, gt=0)
    output_token_limit: int = Field(default=16384, gt=0)
    output_limit_parameter: str = "max_tokens"
    pricing_revision: str | None = None
    bound_verified: bool = False
    max_attempts: int = Field(default=1, ge=1, le=3)

    @model_validator(mode="after")
    def validate_money(self):
        values = [self.ceiling_usd, self.allowance_usd]
        values += [
            v for v in (self.input_usd_per_million, self.output_usd_per_million) if v is not None
        ]
        if any(not v.is_finite() or v < 0 for v in values):
            raise ValueError("monetary values must be finite and nonnegative")
        if self.ceiling_usd <= 0 or self.allowance_usd >= 10:
            raise ValueError("positive ceiling and allowance strictly below US$10 required")
        if self.output_limit_parameter not in {"max_tokens", "max_completion_tokens"}:
            raise ValueError("unsupported output limit parameter")
        if self.model != "scripted" and not (
            self.bound_verified
            and self.pricing_revision
            and self.input_token_bound
            and self.input_usd_per_million is not None
            and self.output_usd_per_million is not None
        ):
            raise ValueError("paid models require a verified bound and versioned rate card")
        return self


class WorkloadConfig(Strict):
    queries: Path | None = None
    count: int = Field(default=1000, ge=15)
    k: int = Field(default=10, ge=1)
    seed: int = 42
    warmups: int = Field(default=5, ge=0)
    passes: int = Field(default=30, gt=0)
    bootstrap_samples: int = Field(default=10000, ge=10000)
    minimum_groups: int = Field(default=30, ge=30)
    recall_tolerance: float = Field(default=0.005, ge=0, le=0.005)


class RunConfig(Strict):
    schema_version: Literal[2] = 2
    backend: BackendConfig
    model: ModelConfig
    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)
    evidence: EvidenceConfig = Field(default_factory=EvidenceConfig)
    workload: WorkloadConfig = Field(default_factory=WorkloadConfig)
    query_timeout_seconds: float = Field(default=30, gt=0)
    _origin: Path = PrivateAttr(default_factory=Path.cwd)

    def public(self) -> dict:
        return self.model_dump(mode="json")

    @property
    def configuration_origin(self):
        return self._origin


def load_config(path: Path) -> RunConfig:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict) or raw.get("schema_version") != 2:
        from .errors import AgentError

        raise AgentError(
            "configuration requires schema_version: 2; "
            "convert old target/copy fields to backend.options"
        )
    config = RunConfig.model_validate(raw)
    config._origin = path.resolve().parent
    value = config.workload.queries
    if value and not value.is_absolute():
        config.workload.queries = (config._origin / value).resolve()
    return config
