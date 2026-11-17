"""Open-ended development search with inherited dollar, quality and holdout checks."""

from copy import deepcopy

import exploration_support as exploration_support

# isort: split

from dollar_controller import DollarCampaign
from fannproto.compiler import compile_programs
from fannproto.controller import ProtocolError, candidate_feedback, generation_ready
from fannproto.policy import PROFILE, observation_plan, replay, rule_hash, validate
from fannproto.uncertainty import COST_STATUS
from selection import select_shortlist

from fannagent.budget import Budget
from fannagent.store import canonical, digest

LIMITS = {
    "paid_requests": None,
    "tool_calls": None,
    "candidate_submissions": None,
    "batch_size": 3,
    "finalists": 3,
}


class ExplorationCampaign(DollarCampaign):
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
            "schema": "filtered-ann-campaign.v4-open-exploration",
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
        if self.store.get("dollar_phase") == "closing" and operation != "submit_or_abstain":
            raise ProtocolError("closing phase permits only submission or abstention")
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
                if not 1 <= n <= 3:
                    raise ProtocolError("one..three candidates per batch required")
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
                    evaluations.append({"candidate_id": cid, **candidate_feedback(record)})
                answer = {
                    "evaluations": evaluations,
                    "candidate_submissions_remaining": None,
                    "cumulative_candidate_submissions": state["candidate_submissions"],
                }
            elif operation == "compare_candidates":
                if (
                    set(arguments) != {"candidate_ids"}
                    or type(arguments["candidate_ids"]) is not list
                    or not arguments["candidate_ids"]
                ):
                    raise ProtocolError("nonempty registered candidate IDs required")
                answer = {
                    "candidates": {
                        cid: candidate_feedback(self.store.read(state["registry"][cid], agent=True))
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
                    decision = self.shortlist_decision(state)
                    ranked = decision["candidate_ids"] if decision else self.shortlist(state)
                    if decision and not ranked:
                        if ids:
                            raise ProtocolError("uncertainty contract requires abstention")
                        state["terminal"] = "uncertainty_shortlist_abstention"
                        answer = {
                            "status": "abstained",
                            "selection_decision": decision,
                            "no_performance_promotion": True,
                        }
                        return self._complete_tool(state, identity, signature, answer)
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
                    if decision:
                        answer["selection_decision"] = decision
            else:
                raise ProtocolError(
                    "unknown operation; no shell/SQL/file/network/holdout tool exists"
                )
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            answer = {"error": str(error)[:400]}
        return self._complete_tool(state, identity, signature, answer)

    def shortlist_decision(self, state=None):
        if self.evidence.bundle.get("cost_status") != COST_STATUS:
            return None
        state = state or self.store.get("v2_state")
        records = [
            {"candidate_id": cid, **self.store.read(artifact, agent=True)}
            for cid, artifact in state["registry"].items()
        ]
        return select_shortlist(records)

    def _complete_tool(self, state, identity, signature, answer):
        block = {
            "type": "tool_result",
            "tool_use_id": identity,
            "content": canonical(answer).decode(),
            "is_error": "error" in answer,
        }
        if len(canonical(block)) > 512 * 1024:
            artifact = self.store.put("open_exploration_full_feedback", answer, scope="development")
            if "candidates" in answer:
                answer = {
                    "error": "Comparison exceeds the response envelope; compare fewer IDs.",
                    "full_feedback_artifact": artifact,
                }
            else:
                answer = {k: v for k, v in answer.items() if k != "selection_decision"}
                answer["full_feedback_artifact"] = artifact
        return super()._complete_tool(state, identity, signature, answer)
