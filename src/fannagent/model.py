from __future__ import annotations

import json
import time
from decimal import Decimal

from minisweagent.exceptions import FormatError
from minisweagent.models.litellm_model import LitellmModel
from minisweagent.models.utils.actions_toolcall import BASH_TOOL

from .errors import AgentError
from .store import canonical


class BudgetedModel(LitellmModel):
    """Wrap mini's formatting interfaces; each provider attempt is reserved separately."""

    def __init__(self, config, budget, dispatch=None):
        super().__init__(
            model_name=config.model,
            litellm_model_registry=None,
            model_kwargs={},
            set_cache_control=None,
        )
        self.contract, self.budget = config, budget
        if dispatch is None:
            import litellm

            dispatch = litellm.completion
        self.dispatch = dispatch

    def format_observation_messages(self, message, outputs, template_vars=None):
        # Mini's template expects exception_info; our shell environments return exit/output only.
        return super().format_observation_messages(
            message, [{"exception_info": None, **output} for output in outputs], template_vars
        )

    def query(self, messages, **kwargs):
        if kwargs:
            raise AgentError("unaccounted model parameter overrides are forbidden")
        prepared = self._prepare_messages_for_api(messages)
        # Covered providers must certify the byte/overhead bound and inclusive output limit.
        bound = (
            len(canonical({"messages": prepared, "tools": [BASH_TOOL]}))
            + 2048
            + 512 * len(messages)
        )
        if bound > self.contract.input_token_bound:
            raise AgentError("request exceeds the configured conservative input bound")
        maximum = self.budget.maximum_call()
        for attempt in range(self.contract.max_attempts):
            reservation = self.budget.reserve(
                maximum,
                {"attempt": attempt + 1, "pricing_revision": self.contract.pricing_revision},
            )
            try:
                response = self.dispatch(
                    model=self.contract.model,
                    messages=prepared,
                    tools=[BASH_TOOL],
                    num_retries=0,
                    max_retries=0,
                    timeout=120,
                    **{self.contract.output_limit_parameter: self.contract.output_token_limit},
                )
            except BaseException as exc:
                self.budget.uncertain(reservation, type(exc).__name__)
                if attempt + 1 == self.contract.max_attempts or not isinstance(exc, Exception):
                    raise AgentError("provider request failed; possible charge retained") from None
                continue
            raw = response.model_dump(mode="json")
            artifact = self.budget.store.put("model_response", raw)
            usage = raw.get("usage") or {}
            input_count, output_count = usage.get("prompt_tokens"), usage.get("completion_tokens")
            if (
                not isinstance(input_count, int)
                or not isinstance(output_count, int)
                or min(input_count, output_count) < 0
            ):
                self.budget.uncertain(reservation, "missing authoritative usage")
                raise AgentError("response usage unavailable; maximum charge retained")
            charge = (
                Decimal(input_count) * self.contract.input_usd_per_million
                + Decimal(output_count) * self.contract.output_usd_per_million
            ) / 1_000_000
            self.budget.settle(reservation, charge, {"response": artifact, "usage": usage})
            if (
                input_count > self.contract.input_token_bound
                or output_count > self.contract.output_token_limit
            ):
                self.budget.store.set("provider_bound_failed", True)
                raise AgentError("provider violated the verified token limit")
            # Response and billing are durable before parsing shell actions.
            try:
                actions = self._parse_actions(response)
            except FormatError as exc:
                exc.messages[0]["extra"].update(
                    {"cost": float(charge), "response_artifact": artifact}
                )
                raise
            message = response.choices[0].message.model_dump(mode="json")
            message["extra"] = {
                "actions": actions,
                "cost": float(charge),
                "response_artifact": artifact,
                "timestamp": time.time(),
            }
            return message


class ScriptedModel:
    """Uses mini's tool-message shape without any provider calls."""

    def __init__(self, actions):
        self.actions, self.index = actions, 0

    def query(self, messages):
        command = self.actions[self.index] if self.index < len(self.actions) else "true"
        self.index += 1
        identity = f"script-{self.index}"
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": identity,
                    "type": "function",
                    "function": {"name": "bash", "arguments": json.dumps({"command": command})},
                }
            ],
            "extra": {"actions": [{"command": command, "tool_call_id": identity}], "cost": 0.0},
        }

    def format_message(self, **kwargs):
        return kwargs

    def format_observation_messages(self, message, outputs, template_vars=None):
        return [
            {"role": "tool", "tool_call_id": a["tool_call_id"], "content": json.dumps(o)}
            for a, o in zip(message["extra"]["actions"], outputs)
        ]

    def get_template_vars(self):
        return {}

    def serialize(self):
        return {"scripted_index": self.index}
