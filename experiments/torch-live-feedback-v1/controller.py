"""Opt-in live tool service. Historical replay campaigns and seals remain unchanged."""

import sys
import uuid
from pathlib import Path

from limits import digest, write

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "filtered-ann-protocol-v2"))
from fannproto.policy import PROFILE, rule_hash, validate  # noqa: E402

SYSTEM = """Develop bounded causal filtered-ANN stopping policies using actual Torch feedback.
Use inspect_workload and explain_cases, propose your own hypotheses and thresholds, then use
evaluate_candidates to compile and measure at most three policies per batch. All six scalar
filters plus unfiltered remain in scope. Keep each development query's actual raw native640
recall. Short outputs count as misses. Exact references are evaluator-only, never serving inputs.
The v2 DSL permits checkpoints16/32/64; qualifying_count, tenth_distance, frontier_gap and
top10_new_since_previous; <= or >=; at most three ordered clauses/filter and four comparisons
per clause. Missing comparisons are false. The compiler infers feature dependencies. Empty
branches continue native without observation. Query/fold IDs, labels, costs, and future states
are forbidden runtime inputs. Policy format:
{"schema":"fannagent.filtered-ann.v2","name":"your_name","rules":{},"rationale":"..."}.
The tool checks actual outputs on all450 development vector groups and times the same fixed64
groups across all seven conditions. Costs are actual full-request times on Torch, never proxy
predictions. Candidate/native and candidate/matched-control comparisons include conditional
group bootstrap intervals. These omit adaptive selection and allocation variability. Treat
small or inconsistent differences as inconclusive. Do not fabricate wins or use work as time.
Feedback includes failed trials. Revise within the remaining dollar/time budget. No fixed
request/candidate count overrides those budgets; batch size is at most three. At six hours the
single allocation ends; no tool can extend or replace it. Fifteen idle minutes also ends it.
Submit eligible measured candidates or explicitly abstain. Native is always admissible.
Validation/test remain inaccessible. This is development, not a final performance claim.
"""


def schema(properties, required):
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


TOOLS = [
    {
        "name": "inspect_workload",
        "description": "Development scope and runtime semantics.",
        "input_schema": schema({}, []),
    },
    {
        "name": "explain_cases",
        "description": "At most twelve anonymous development examples.",
        "input_schema": schema(
            {
                "category": {"type": "string"},
                "filter": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 12},
            },
            ["category", "filter", "limit"],
        ),
    },
    {
        "name": "evaluate_candidates",
        "description": "Compile and run up to three DSL policies "
        "on Torch; return actual quality and paired serving-time measurements.",
        "input_schema": schema(
            {
                "policies": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 3,
                    "items": {"type": "object"},
                }
            },
            ["policies"],
        ),
    },
    {
        "name": "submit_or_abstain",
        "description": "Freeze measured development nominees or abstain.",
        "input_schema": schema(
            {
                "candidate_ids": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
                "abstain": {"type": "boolean"},
            },
            ["candidate_ids", "abstain"],
        ),
    },
]


class LiveTools:
    def __init__(self, evidence, client, path):
        self.evidence, self.client, self.path = evidence, client, Path(path)
        if self.path.exists():
            raise ValueError(
                "live episode already exists; audit interrupted delivery before resume"
            )
        self.state = {
            "schema": "fannagent.live-controller.v1",
            "registry": {},
            "receipts": {},
            "terminal": None,
            "performance_claim": False,
        }
        write(self.path, self.state)

    def call(self, identity, operation, arguments):
        signature = digest({"operation": operation, "arguments": arguments})
        if identity in self.state["receipts"]:
            receipt = self.state["receipts"][identity]
            if receipt["signature"] != signature or receipt["status"] != "complete":
                raise ValueError("uncertain or conflicting tool identity; never repeat it")
            return receipt["answer"]
        if self.state["terminal"]:
            raise ValueError("episode is closed")
        self.state["receipts"][identity] = {"signature": signature, "status": "reserved"}
        write(self.path, self.state)
        try:
            answer = self._call(operation, arguments)
        except (ValueError, KeyError, TypeError) as error:
            answer = {"error": str(error)[:400]}
        self.state["receipts"][identity].update(status="complete", answer=answer)
        write(self.path, self.state)
        return answer

    def _call(self, operation, arguments):
        if operation == "inspect_workload" and not arguments:
            return {
                "per_filter": self.evidence.summary()["per_filter"],
                "runtime": PROFILE.describe(),
                "feedback": "actual Torch measurements only",
                "historical_control_measurements": self.client.call("status").get(
                    "qualification_feedback"
                ),
            }
        if operation == "explain_cases" and set(arguments) == {"category", "filter", "limit"}:
            return {
                "cases": self.evidence.examples(
                    arguments["category"], arguments["filter"], arguments["limit"]
                )
            }
        if operation == "evaluate_candidates" and set(arguments) == {"policies"}:
            policies = arguments["policies"]
            if not isinstance(policies, list) or not 1 <= len(policies) <= 3:
                raise ValueError("one to three DSL policies per live batch")
            # Validate the entire batch before remote submission; rejected attempts remain recorded.
            for policy in policies:
                validate(policy)
            remote_id = uuid.uuid4().hex
            ids = []
            for policy in policies:
                cid = "candidate-" + str(len(self.state["registry"]) + 1)
                self.state["registry"][cid] = {
                    "policy": policy,
                    "rule_hash": rule_hash(policy),
                    "remote_request_id": remote_id,
                    "status": "pending",
                }
                ids.append(cid)
            write(self.path, self.state)
            result = self.client.evaluate(policies, identity=remote_id)
            for index, cid in enumerate(ids, 1):
                self.state["registry"][cid].update(
                    remote_family=f"candidate{index}", result=result, status=result["status"]
                )
            if result["status"] not in ("measured", "quality_rejected"):
                self.state["terminal"] = "remote_failure_no_retry"
            return {"candidate_ids": ids, "live_result": result}
        if operation == "submit_or_abstain" and set(arguments) == {"candidate_ids", "abstain"}:
            ids = arguments["candidate_ids"]
            if not isinstance(ids, list) or len(set(ids)) != len(ids) or len(ids) > 3:
                raise ValueError("at most three distinct registered candidates")
            if type(arguments["abstain"]) is not bool:
                raise ValueError("abstain must be Boolean")
            if arguments["abstain"]:
                if ids:
                    raise ValueError("abstention must have an empty nominee list")
                self.state["terminal"] = "abstained"
            else:
                if not ids or any(not self.eligible(cid) for cid in ids):
                    raise ValueError("no qualifying measured signal; retain native or abstain")
                self.state["terminal"] = "development_nominees_frozen"
                self.state["nominees"] = ids
            return {"status": self.state["terminal"], "performance_claim": False}
        raise ValueError("unknown tool or invalid arguments; no SQL/shell/holdout/scheduler tool")

    def eligible(self, cid):
        record = self.state["registry"].get(cid, {})
        if record.get("status") != "measured":
            return False
        feedback = record["result"]["feedback"]
        family = record["remote_family"]
        latency = feedback["latency"]
        candidate = latency[family]
        empty = latency["empty"]["conditional90_interval"]
        return (
            not feedback["quality_loss_cases"][family]
            and candidate["scalar_ratio_to_native"] < 1
            and candidate["conditional95_interval"][1] < 1
            and candidate["matched_conditional95_interval"][1] < 1
            and empty[0] >= 0.98
            and empty[1] <= 1.02
        )
