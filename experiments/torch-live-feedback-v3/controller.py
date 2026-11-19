"""V3 model controller: isolated offline discovery and measured development feedback."""

import sys
import uuid
from pathlib import Path

from limits import digest, write
from workspace import ResearchWorkspace

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1] / "src"), str(HERE.parent / "filtered-ann-protocol-v3")]
from fannproto3.compiler import compile_programs  # noqa: E402

from fannagent.api.broad_policy import FEATURES, policy_hash, validate  # noqa: E402

SYSTEM = """Discover a deployable causal filtered-ANN stopping policy in broad-stop.v3.
You control the discovery method. Inspect the development evidence; use research_python to
write fitting/search scripts and generate JSON files, then evaluate_broad_candidates to
obtain actual Torch recall and complete-request latency. You may use NumPy and Python's
standard library; sklearn is not installed. No internet or package installer is available.
The offline workspace contains only 450 development vector groups, all seven conditions,
causal checkpoint frames, and actually executed prefix recall labels. Unknown prefix labels
are unknown, never safe by assumption. No vectors, source IDs, oracle programs or held-out
outcomes are exposed. This data is available at evidence/development.jsonl. Read api/README.md
and api/broad_contract.py for the exact schema. api/broad_support.py provides replay(policy,row)
for captured frame rows; evidence labels are offline fitting targets, never runtime inputs.

Submit one fixed policy shared by queries, with optional per-filter programs. Programs may
use all 13 declared causal features, arithmetic/Boolean expressions, scheduled checkpoints
1..4096 and up to32 query-local registers. Source<=8MiB, nodes<=131072, depth<=64,
compiled tables<=4MiB and query fuel<=16000000. Only true stops. Fault or fuel exhaustion
continues native. No IDs, truth labels, role tables, future features, external calls or index
mutation are permitted in runtime programs. Do not embed a query-ID lookup. Offline search
and fitting are unrestricted within the workspace and resource budget. Policy files go under
policies/. Both inline policies and policy_paths are accepted. No researcher policy is seeded.

Preserve every development case's actual raw native640 Recall@10, including short outputs.
Exact references are offline evaluator inputs, never serving inputs or completion repairs.
Live tools check all3150 development cases; only zero-loss batches receive timing, on a fixed
32-vector development screen. At most3 policies/batch. All feature/VM costs are included.
The native attempt budget reserves the final frozen comparison first; when no further batch
fits, choose among measured candidates or abstain. Use offline replay before native requests.
Native is always admissible. Choose one final candidate using development evidence only.
submit_or_abstain freezes it permanently. A measured zero-loss candidate may be frozen for
descriptive evaluation even if timing controls fail; report that failure, never call it a
qualified win. Formal qualification requires the unchanged strict timing controls and
improvement against native and matched continuation. No test outcomes are available to you.
The host evaluates the frozen artifact once against the hindsight oracle afterward.
The episode has a $15 ceiling, no fixed model/candidate quota, one six-hour allocation,
300000 durably reserved ANN requests, and no automatic retries/requeue. Compilation,
waiting and offline research during the allocation consume its time. No tool extends it.
Development admission ends after three allocated hours to reserve final comparison time.
"""


def tool(name, description, properties, required):
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TOOLS = [
    tool("inspect_workload", "Development scope, language and native budget.", {}, []),
    tool(
        "research_python",
        "Run an offline Python fitting/replay script in the isolated development workspace "
        "(240s, 2GiB, no network).",
        {"code": {"type": "string"}},
        ["code"],
    ),
    tool(
        "evaluate_broad_candidates",
        "Compile and measure up to3 v3 policies on development; "
        "accepts inline JSON or workspace policy paths.",
        {
            "policies": {"type": "array", "maxItems": 3, "items": {"type": "object"}},
            "policy_paths": {"type": "array", "maxItems": 3, "items": {"type": "string"}},
        },
        [],
    ),
    tool(
        "submit_or_abstain",
        "Permanently freeze one measured, zero-development-loss candidate "
        "for final evaluation, or abstain.",
        {
            "candidate_ids": {"type": "array", "maxItems": 1, "items": {"type": "string"}},
            "abstain": {"type": "boolean"},
        },
        ["candidate_ids", "abstain"],
    ),
]


class LiveTools:
    def __init__(self, evidence, client, path, workspace=None, image=None):
        self.evidence, self.client, self.path = evidence, client, Path(path)
        if self.path.exists():
            raise ValueError("episode already exists; audit before resume")
        self.workspace = ResearchWorkspace(workspace, image) if workspace else None
        self.state = {
            "schema": "fannagent.live-controller.v3",
            "registry": {},
            "receipts": {},
            "terminal": None,
            "performance_claim": False,
        }
        write(self.path, self.state)

    def call(self, identity, operation, arguments):
        signature = digest({"operation": operation, "arguments": arguments})
        if identity in self.state["receipts"]:
            prior = self.state["receipts"][identity]
            if prior["signature"] != signature or prior["status"] != "complete":
                raise ValueError("uncertain or conflicting tool identity; never repeat")
            return prior["answer"]
        if self.state["terminal"]:
            raise ValueError("episode is closed")
        self.state["receipts"][identity] = {"signature": signature, "status": "reserved"}
        write(self.path, self.state)
        try:
            answer = self._call(operation, arguments)
        except (ValueError, KeyError, TypeError, FileNotFoundError) as error:
            answer = {"error": str(error)[:600]}
        self.state["receipts"][identity].update(status="complete", answer=answer)
        write(self.path, self.state)
        return answer

    def _call(self, operation, arguments):
        if operation == "inspect_workload" and not arguments:
            return {
                "development": self.evidence,
                "features": FEATURES,
                "worker": self.client.call("status"),
                "workspace": "evidence/development.jsonl, api/, policies/, scratch/",
            }
        if operation == "research_python" and set(arguments) == {"code"}:
            return self.workspace.execute(arguments["code"])
        if operation == "evaluate_broad_candidates":
            policies = self.workspace.policies(arguments)
            for policy in policies:
                validate(policy)
                compile_programs([{"arm": 60, "policy": policy, "force_continue": False}])
            remote = uuid.uuid4().hex
            ids = []
            for policy in policies:
                cid = "candidate-" + str(len(self.state["registry"]) + 1)
                self.state["registry"][cid] = {
                    "policy": policy,
                    "policy_hash": policy_hash(policy),
                    "remote_request_id": remote,
                    "status": "pending",
                }
                ids.append(cid)
            write(self.path, self.state)
            result = self.client.evaluate(policies, identity=remote)
            for i, cid in enumerate(ids, 1):
                self.state["registry"][cid].update(
                    remote_family=f"candidate{i}", result=result, status=result["status"]
                )
            if result["status"] not in ("measured", "quality_rejected", "budget_rejected"):
                self.state["terminal"] = "remote_failure_no_retry"
            return {"candidate_ids": ids, "live_result": result}
        if operation == "submit_or_abstain" and set(arguments) == {"candidate_ids", "abstain"}:
            ids = arguments["candidate_ids"]
            if type(ids) is not list or len(ids) > 1 or type(arguments["abstain"]) is not bool:
                raise ValueError("freeze one registered candidate or explicitly abstain")
            if arguments["abstain"]:
                if ids:
                    raise ValueError("abstention needs an empty nominee list")
                self.state["terminal"] = "abstained"
            else:
                if not ids or not self.quality_eligible(ids[0]):
                    raise ValueError("freeze requires measured zero-development-loss candidate")
                self.state["terminal"] = "development_candidate_frozen"
                self.state["nominees"] = ids
                self.state["strict_development_qualification"] = self.eligible(ids[0])
            return {
                "status": self.state["terminal"],
                "performance_claim": False,
                "strict_development_qualification": self.state.get(
                    "strict_development_qualification", False
                ),
            }
        raise ValueError("unknown tool or invalid arguments")

    def quality_eligible(self, cid):
        r = self.state["registry"].get(cid, {})
        return (
            r.get("status") == "measured"
            and r["result"]["feedback"]["quality_loss_cases"][r["remote_family"]] == 0
        )

    def eligible(self, cid):
        if not self.quality_eligible(cid):
            return False
        r = self.state["registry"][cid]
        lat = r["result"]["feedback"]["latency"]
        value = lat[r["remote_family"]]
        return (
            value["conditional95_interval"][1] < 1
            and value["matched_conditional95_interval"][1] < 1
            and r["result"]["feedback"]["all_condition_controls_pass"]
        )
