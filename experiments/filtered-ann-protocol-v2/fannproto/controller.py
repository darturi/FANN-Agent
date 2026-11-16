"""Typed bounded controller using the existing durable Store and Budget services."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from decimal import Decimal

from fannagent.budget import Budget
from fannagent.store import Store, canonical, digest

from .compiler import compile_programs
from .policy import PROFILE, observation_plan, replay, rule_hash, validate

LIMITS = {
    "paid_requests": 6,
    "tool_calls": 12,
    "candidate_submissions": 9,
    "batch_size": 3,
    "finalists": 3,
}


class ProtocolError(ValueError):
    pass


def parse_final(text):
    if type(text) is not str or len(text.encode()) > 100000:
        raise ProtocolError("bounded text envelope required")
    stripped = text.strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        blocks = re.findall(r"```json\s*\n(.*?)\n```", text, re.S)
        if len(blocks) != 1:
            raise ProtocolError(
                "one JSON object or one uniquely fenced JSON object required"
            ) from None
        try:
            value = json.loads(blocks[0])
        except json.JSONDecodeError:
            raise ProtocolError("invalid JSON block") from None
    if not isinstance(value, dict) or set(value) - {"candidate_ids", "abstain", "notes"}:
        raise ProtocolError("invalid final submission envelope")
    return value


def generation_ready(evidence, gates):
    if gates.get("M0", {}).get("status") != "verified_attribution_resolved":
        raise ProtocolError("M0 attribution return is not verified/resolved")
    if (
        gates.get("M1", {}).get("status") != "verified_original_graph"
        or gates["M1"].get("runtime_profile") != PROFILE.fingerprint
    ):
        raise ProtocolError("M1 original-graph v2 runtime qualification is pending")
    if evidence.bundle.get("cost_status") == "unqualified_M2_models_failed":
        raise ProtocolError("M2 cost models failed qualification; ranking and generation blocked")
    if (
        evidence.bundle.get("cost_status") != "qualified"
        or gates.get("M2", {}).get("evidence_hash") != evidence.identity
    ):
        raise ProtocolError("M2 qualified cost/prefix evidence is pending")
    if any(cp not in r["proofs"] for r in evidence.rows for cp in r["observations"]):
        raise ProtocolError("missing partial-prefix proof blocks generation")
    for key in ("M0", "M1"):
        if not re.fullmatch("[a-f0-9]{64}", gates[key].get("receipt_sha256", "")):
            raise ProtocolError("qualification receipt identity required")


class Campaign:
    def __init__(self, store: Store, model_config, evidence, gates):
        self.store = store
        self.evidence = evidence
        self.gates = gates
        self.model_config = model_config
        if (
            model_config.allowance_usd != 0
            or model_config.ceiling_usd > 15
            or model_config.output_token_limit > 6000
            or model_config.max_attempts != 1
        ):
            raise ProtocolError("v2 charge/output/no-retry limits required")
        self.budget = Budget(store, model_config)
        contract = {
            "schema": "filtered-ann-campaign.v2",
            "evidence": evidence.identity,
            "runtime_profile": PROFILE.fingerprint,
            "limits": LIMITS,
            "gates": digest(gates),
            "fixture": evidence.fixture,
        }
        existing = store.get("v2_contract")
        if existing is not None and existing != contract:
            raise ProtocolError("resume cannot change campaign contract")
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
        signature = digest({"operation": operation, "arguments": arguments})
        old = state["receipts"].get(identity)
        if old:
            if old["signature"] != signature:
                raise ProtocolError("tool identity reused with different arguments")
            if old["status"] != "complete":
                raise ProtocolError("interrupted tool is not automatically repeated")
            return self.store.read(old["artifact"], agent=True)
        if state["terminal"]:
            raise ProtocolError("campaign is terminal")
        if state["tool_calls"] >= LIMITS["tool_calls"]:
            raise ProtocolError("domain tool limit reached")
        if type(identity) is not str or not 1 <= len(identity) <= 100:
            raise ProtocolError("bounded tool identity required")
        state["tool_calls"] += 1
        state["receipts"][identity] = {"signature": signature, "status": "reserved"}
        self.store.set("v2_state", state)
        try:
            if type(arguments) is not dict or len(canonical(arguments)) > 100000:
                raise ProtocolError("bounded typed arguments required")
            if operation == "inspect_workload":
                if arguments:
                    raise ProtocolError("inspect takes no arguments")
                answer = self.evidence.summary()
                if "development_prefix_summary" in self.evidence.bundle:
                    answer["prefix_opportunity"] = deepcopy(
                        self.evidence.bundle["development_prefix_summary"]
                    )
            elif operation == "explain_cases":
                if set(arguments) != {"category", "filter", "limit"}:
                    raise ProtocolError("category/filter/limit required")
                answer = {
                    "cases": self.evidence.examples(
                        arguments["category"], arguments["filter"], arguments["limit"]
                    )
                }
            elif operation == "evaluate_candidates":
                if set(arguments) != {"policies"} or type(arguments["policies"]) is not list:
                    raise ProtocolError("policies list required")
                values = arguments["policies"]
                n = len(values)
                if not 1 <= n <= 3 or state["candidate_submissions"] + n > 9:
                    state["terminal"] = "candidate_submission_limit_or_batch_violation"
                    self.store.set("v2_state", state)
                    raise ProtocolError("at most3/batch and9 total candidate submissions")
                start = state["candidate_submissions"]
                state["candidate_submissions"] += n
                self.store.set("v2_state", state)
                evaluations = []
                for offset, p in enumerate(values):
                    cid = f"candidate-{start + offset + 1}"
                    try:
                        validate(p)
                        evaluation = replay(p, self.evidence.rows)
                        source, manifest = compile_programs(
                            [{"arm": 20, "policy": p, "force_continue": False}]
                        )
                        compiled = self.store.put(
                            "v2_compiled_candidate",
                            {"source": source, "manifest": manifest},
                            scope="development",
                        )
                        record = {
                            "policy": p,
                            "rule_hash": rule_hash(p),
                            "observation_plan": observation_plan(p),
                            "evaluation": evaluation,
                            "cost_estimate": self.evidence.estimate(p),
                            "work_estimate": self.evidence.work_estimate(p),
                            "compiled_artifact": compiled,
                        }
                    except (ValueError, TypeError, KeyError, OverflowError) as error:
                        record = {"rejected": str(error)[:300]}
                    artifact = self.store.put("v2_candidate", record, scope="development")
                    state["registry"][cid] = artifact
                    evaluations.append(
                        {"candidate_id": cid, **{k: v for k, v in record.items() if k != "policy"}}
                    )
                answer = {
                    "evaluations": evaluations,
                    "candidate_submissions_remaining": 9 - state["candidate_submissions"],
                }
            elif operation == "compare_candidates":
                if (
                    set(arguments) != {"candidate_ids"}
                    or type(arguments["candidate_ids"]) is not list
                    or not 1 <= len(arguments["candidate_ids"]) <= 9
                ):
                    raise ProtocolError("one..nine registered candidate IDs required")
                answer = {
                    "candidates": {
                        cid: self.store.read(state["registry"][cid], agent=True)
                        for cid in arguments["candidate_ids"]
                    }
                }
            elif operation == "submit_or_abstain":
                if set(arguments) - {"candidate_ids", "abstain", "notes"}:
                    raise ProtocolError("unknown submission field")
                ids = arguments.get("candidate_ids", [])
                abstain = arguments.get("abstain", False)
                if (
                    type(abstain) is not bool
                    or type(ids) is not list
                    or len(ids) != len(set(ids))
                    or len(ids) > 3
                ):
                    raise ProtocolError("invalid bounded submission")
                if abstain:
                    if ids:
                        raise ProtocolError("abstention cannot include candidates")
                    state["terminal"] = "explicit_abstention"
                    answer = {
                        "status": "abstained",
                        "notes": str(arguments.get("notes", ""))[:4000],
                    }
                else:
                    generation_ready(self.evidence, self.gates)
                    ranked = self.shortlist(state)
                    if not ranked:
                        raise ProtocolError("no fully qualified cost-ranked candidate; abstain")
                    if ids and set(ids) != set(ranked):
                        raise ProtocolError(
                            "submission must match deterministic qualified shortlist"
                        )
                    ids = ranked
                    for cid in ids:
                        record = self.store.read(state["registry"][cid], agent=True)
                        if (
                            not record.get("evaluation", {}).get("quality_preserves_raw_native640")
                            or record.get("cost_estimate") is None
                        ):
                            raise ProtocolError("finalist lacks full quality/cost evidence")
                    state["terminal"] = "finalists_frozen_pending_live_measurement"
                    answer = {
                        "status": state["terminal"],
                        "candidate_ids": ids,
                        "no_performance_promotion": True,
                    }
            else:
                raise ProtocolError(
                    "unknown operation; no shell/SQL/file/network/holdout tool exists"
                )
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            answer = {"error": str(error)[:400]}
        artifact = self.store.put("v2_tool_result", answer, scope="development")
        state["receipts"][identity] = {
            "signature": signature,
            "status": "complete",
            "artifact": artifact,
        }
        self.store.set("v2_state", state)
        return answer

    def shortlist(self, state=None):
        state = state or self.store.get("v2_state")
        remaining = []
        seen = set()
        for cid, artifact in state["registry"].items():
            r = self.store.read(artifact, agent=True)
            if (
                r.get("evaluation", {}).get("quality_preserves_raw_native640")
                and r.get("cost_estimate") is not None
                and r["rule_hash"] not in seen
            ):
                seen.add(r["rule_hash"])
                clauses = [c for values in r["policy"]["rules"].values() for c in values]
                remaining.append(
                    (
                        r["cost_estimate"]["equal_scalar_mean_ms"],
                        sum(len(c["conditions"]) for c in clauses),
                        len(clauses),
                        r["rule_hash"],
                        cid,
                    )
                )
        chosen = []
        while remaining and len(chosen) < 3:
            minimum = min(r[0] for r in remaining)
            r = min((r for r in remaining if r[0] <= minimum * 1.01), key=lambda r: r[1:4])
            chosen.append(r[-1])
            remaining.remove(r)
        return chosen

    def dispatch(self, identity, operation, arguments):
        with self.store.lease("run"):
            return self._dispatch(identity, operation, arguments)

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
            old_prompt = self.store.get("v2_prompt_contract")
            if old_prompt is not None and old_prompt != digest(frozen):
                raise ProtocolError("resume cannot change prompt/tools/inference contract")
            if type(request.get("messages")) is not list or not request["messages"]:
                raise ProtocolError("messages required")
            history = self.store.get("v2_messages")
            if history is not None and request["messages"] != history:
                raise ProtocolError("resume must preserve exact transcript/tool feedback")
            summary = self.budget.summary()
            if summary["uncertain_calls"]:
                raise ProtocolError("uncertain call requires audit, not automatic retry")
            if len(summary["calls"]) >= 6:
                raise ProtocolError("six paid request limit reached")
            if getattr(transport, "automatic_retries", None) is not False:
                raise ProtocolError("transport must disable retries")
            if (
                request.get("model") != self.model_config.model
                or request.get("max_tokens") != self.model_config.output_token_limit
            ):
                raise ProtocolError("request model/output cap differs from frozen contract")
            if len(canonical(request)) + 8192 > self.model_config.input_token_bound:
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
            if any(
                x.get("type") not in ("text", "tool_use")
                or x.get("type") == "text"
                and type(x.get("text")) is not str
                for x in content
            ):
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

    def _invalid_response(self, reason):
        state = self.store.get("v2_state")
        state["terminal"] = reason
        outcome = {"error": reason, "paid_request_consumed": True}
        artifact = self.store.put(
            "v2_round_outcome",
            {"pending_round": self.store.get("v2_round_pending"), "outcome": outcome},
            scope="private",
        )
        self.store.set_many(
            {"v2_state": state, "v2_last_round": {"outcome_artifact": artifact}},
            delete=("v2_round_pending",),
        )
        return outcome
