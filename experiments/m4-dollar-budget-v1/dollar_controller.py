"""Dollar-ceiling host controller; frozen policy/evidence/selection logic is inherited."""

from decimal import Decimal

from fannproto.controller import Campaign as LegacyCampaign
from fannproto.controller import ProtocolError, generation_ready, parse_final
from fannproto.policy import PROFILE

from fannagent.budget import Budget
from fannagent.store import canonical, digest

LIMITS = {
    "paid_requests": None,
    "tool_calls": 12,
    "candidate_submissions": 9,
    "batch_size": 3,
    "finalists": 3,
}


class DollarCampaign(LegacyCampaign):
    def __init__(self, store, model_config, evidence, gates):
        self.store, self.model_config, self.evidence, self.gates = (
            store,
            model_config,
            evidence,
            gates,
        )
        if (
            model_config.allowance_usd != 0
            or model_config.ceiling_usd != 15
            or model_config.output_token_limit != 6000
            or model_config.max_attempts != 1
        ):
            raise ProtocolError("cumulative$15/zero-overrun/output/no-retry contract required")
        self.budget = Budget(store, model_config)
        contract = {
            "schema": "filtered-ann-campaign.v3-dollar",
            "evidence": evidence.identity,
            "runtime_profile": PROFILE.fingerprint,
            "limits": LIMITS,
            "gates": digest(gates),
            "fixture": evidence.fixture,
        }
        old = store.get("v2_contract")
        if old is not None and old != contract:
            raise ProtocolError("resume cannot change dollar-budget contract")
        store.set("v2_contract", contract)
        if store.get("v2_state") is None:
            store.set(
                "v2_state",
                {
                    "tool_calls": 0,
                    "candidate_submissions": 0,
                    "registry": {},
                    "receipts": {},
                    "terminal": None,
                },
            )

    def _dispatch(self, identity, operation, arguments):
        state = self.store.get("v2_state")
        if operation != "submit_or_abstain":
            if self.store.get("dollar_phase") == "closing":
                raise ProtocolError("closing phase permits only submission or abstention")
            if state["tool_calls"] >= 11 or state["candidate_submissions"] >= 9:
                raise ProtocolError("research quota reached; closing tool slot is reserved")
        answer = super()._dispatch(identity, operation, arguments)
        block = {
            "type": "tool_result",
            "tool_use_id": identity,
            "content": canonical(answer).decode(),
            "is_error": "error" in answer,
        }
        if len(canonical(block)) > 512 * 1024:
            raise ProtocolError("host feedback exceeds qualified wire envelope")
        return answer

    def round(self, request, transport):
        """Transport is injected. This module has no credential loader or network client."""
        with self.store.lease("run"):
            generation_ready(self.evidence, self.gates)
            state = self.store.get("v2_state")
            if state["terminal"]:
                raise ProtocolError("campaign is terminal")
            if self.store.get("v2_round_pending"):
                raise ProtocolError("interrupted model round requires audit, not automatic retry")
            if self.evidence.fixture and self.model_config.model != "scripted":
                raise ProtocolError("fixture cannot authorize a paid model")
            if self.model_config.model != "scripted":
                authorization = self.gates.get("provider_authorization")
                if (
                    type(authorization) is not dict
                    or authorization.get("status") != "authorized"
                    or authorization.get("model") != self.model_config.model
                    or authorization.get("evidence_hash") != self.evidence.identity
                    or authorization.get("max_requests") is not None
                    or authorization.get("spending_policy") != "dollar_ceiling"
                    or authorization.get("max_output_tokens")
                    != self.model_config.output_token_limit
                    or authorization.get("ceiling_usd") != str(self.model_config.ceiling_usd)
                ):
                    raise ProtocolError("new concrete provider authorization required")
            frozen = {
                k: request.get(k)
                for k in (
                    "model",
                    "system",
                    "tools",
                    "inference_geo",
                    "service_tier",
                    "thinking",
                    "output_config",
                )
            }
            phase = self.store.get("dollar_phase", "research")
            if digest(frozen) != self.gates["phase_prompt_hashes"].get(phase):
                raise ProtocolError(
                    "request differs from frozen research/closing phase prompt contract"
                )
            if type(request.get("messages")) is not list or not request["messages"]:
                raise ProtocolError("messages required")
            history = self.store.get("v2_messages")
            if history is not None and request["messages"] != history:
                raise ProtocolError("resume must preserve exact transcript/tool feedback")
            summary = self.budget.summary()
            if summary["uncertain_calls"]:
                raise ProtocolError("uncertain call requires audit, not automatic retry")
            if getattr(transport, "automatic_retries", None) is not False:
                raise ProtocolError("transport must disable retries")
            if (
                request.get("model") != self.model_config.model
                or request.get("max_tokens") != self.model_config.output_token_limit
            ):
                raise ProtocolError("request model/output cap differs from frozen contract")
            byte_bound = self.gates.get("execution_contract", {}).get(
                "request_byte_bound", self.model_config.input_token_bound
            )
            if type(byte_bound) is not int or byte_bound <= 8192:
                raise ProtocolError("invalid operational request byte bound")
            if len(canonical(request)) + 8192 > byte_bound:
                raise ProtocolError("request bytes exceed conservative input bound")
            self.store.set("v2_prompt_contract", digest(frozen))
            maximum = self.budget.maximum_call()
            reservation = self.budget.reserve(
                maximum, {"request_hash": digest(request), "ordinal": len(summary["calls"]) + 1}
            )
            request_artifact = self.store.put("v2_model_request", request, scope="private")
            self.store.set(
                "v2_round_pending",
                {"reservation": reservation, "request_artifact": request_artifact},
            )
            try:
                response = transport(request)
                if (
                    len(canonical({"role": "assistant", "content": response.get("content")}))
                    > 512 * 1024
                ):
                    raise ProtocolError("assistant response exceeds wire envelope")
                artifact = self.store.put("v2_model_response", response, scope="private")
                usage = response["usage"]
                a = usage["input_tokens"]
                b = usage["output_tokens"]
                if (
                    type(a) is not int
                    or type(b) is not int
                    or not 0 <= a <= self.model_config.input_token_bound
                    or not 0 <= b <= self.model_config.output_token_limit
                    or response["model"] != self.model_config.model
                    or usage.get("cache_creation_input_tokens", 0)
                    or usage.get("cache_read_input_tokens", 0)
                ):
                    raise ProtocolError("unqualified model/token/cache usage contract")
                charge = (
                    Decimal(a) * self.model_config.input_usd_per_million
                    + Decimal(b) * self.model_config.output_usd_per_million
                ) / 1000000
                self.budget.settle(
                    reservation, charge, {"response_artifact": artifact, "usage": usage}
                )
            except BaseException as error:
                self.budget.uncertain(reservation, type(error).__name__)
                state["terminal"] = "provider_failure_or_uncertain_response"
                self.store.set("v2_state", state)
                raise
            # Settle before parsing: malformed output still consumes its paid request.
            content = response.get("content")
            if not isinstance(content, list) or any(not isinstance(x, dict) for x in content):
                return self._invalid_response("invalid_provider_content")
            uses = [x for x in content if x.get("type") == "tool_use"]
            ids = [x.get("id") for x in uses]
            if any(type(i) is not str for i in ids) or len(ids) != len(set(ids)):
                return self._invalid_response("invalid_tool_envelope")

            def valid_block(block):
                kind = block.get("type")
                if kind == "text":
                    return type(block.get("text")) is str
                if kind == "tool_use":
                    return True  # Typed tool envelope/arguments are checked by the dispatcher.
                if request.get("thinking", {}).get("type") not in ("between_tools", "adaptive"):
                    return False
                if kind == "thinking":
                    return (
                        type(block.get("thinking")) is str
                        and type(block.get("signature")) is str
                        and bool(block["signature"])
                    )
                if kind == "redacted_thinking":
                    return type(block.get("data")) is str and bool(block["data"])
                return False

            if not all(valid_block(block) for block in content):
                return self._invalid_response("invalid_content_envelope")
            if uses:
                results = []
                for x in uses:
                    try:
                        value = self._dispatch(x["id"], x.get("name"), x.get("input"))
                    except ProtocolError as error:
                        value = {"error": str(error)}
                    results.append({"tool_use_id": x["id"], "result": value})
                outcome = {"tool_results": results}
                feedback = [
                    {
                        "type": "tool_result",
                        "tool_use_id": r["tool_use_id"],
                        "content": canonical(r["result"]).decode(),
                        "is_error": "error" in r["result"],
                    }
                    for r in results
                ]
            else:
                try:
                    final = parse_final(
                        "".join(x.get("text", "") for x in content if x.get("type") == "text")
                    )
                    outcome = self._dispatch("final-" + reservation, "submit_or_abstain", final)
                except ProtocolError as error:
                    outcome = {"error": str(error), "paid_request_consumed": True}
                feedback = [{"type": "text", "text": canonical(outcome).decode()}]
            history = request["messages"] + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": feedback},
            ]
            outcome_artifact = self.store.put(
                "v2_round_outcome",
                {"reservation": reservation, "outcome": outcome},
                scope="private",
            )
            self.store.set_many(
                {
                    "v2_messages": history,
                    "v2_last_round": {
                        "reservation": reservation,
                        "outcome_artifact": outcome_artifact,
                    },
                },
                delete=("v2_round_pending",),
            )
            return outcome
