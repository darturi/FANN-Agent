"""Local model loop with live Torch tools, cumulative money accounting and no retries.

Preparation and tests do not contact a provider. Execution needs a separately bound
approval record; no existing experiment's authorization or charges are reset.
"""

import argparse
import http.client
import json
import os
import ssl
import sys
from decimal import Decimal
from pathlib import Path

import certifi
from client import TorchClient
from controller import SYSTEM, TOOLS, LiveTools
from limits import canonical, digest, read, sha, write
from model_profile import PROFILE, load_profile, verify_current_provider
from workflow_status import require_live_workflow

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "agent/src"))
from fannagent.budget import Budget  # noqa: E402
from fannagent.config import ModelConfig  # noqa: E402
from fannagent.store import Store  # noqa: E402

STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"


def prepare(output, host, stage, kit, control_path=None, resume_from=None):
    require_live_workflow()
    output.mkdir(parents=True, exist_ok=False)
    profile = load_profile()
    model = profile["model_config"]
    inference = profile["inference"]
    api_version = profile["api_version"]
    workspace = kit.parent / "workspace"
    evidence = workspace / "evidence/summary.json"
    workspace_binding = read(kit.parent / "workspace-binding.json")
    carried = None
    carried_messages = None
    if resume_from:
        prior = read(resume_from / "review.json")
        model = prior["model_config"]
        previous_request = read(resume_from / "first-request.json")
        inference = {k: previous_request[k] for k in profile["inference"]}
        api_version = prior.get("api_version", "2023-06-01")
        workspace = Path(prior["workspace"])
        evidence = Path(prior["evidence_path"])
        workspace_binding = prior["workspace_binding"]
        campaign = resume_from / "live/campaign"
        store = Store(campaign)
        summary = Budget(store, ModelConfig.model_validate(model), readonly=True).summary()
        if summary["uncertain_calls"] or any(c["status"] != "settled" for c in summary["calls"]):
            raise ValueError("unknown prior charges cannot be resumed")
        previous_tools = resume_from / "live/tools.json"
        state = read(previous_tools)
        if state["terminal"] != "worker_stopped_or_admission_closed":
            raise ValueError("only an audited administrative stop can resume")
        if any(r["status"] != "complete" for r in state["receipts"].values()):
            raise ValueError("uncertain prior tool calls cannot be replayed")
        carried_messages = store.get("live_messages")
        if not carried_messages:
            raise ValueError("missing prior conversation")
        write(output / "carried-messages.json", carried_messages)
        carried = {
            "campaign": str(campaign.resolve()),
            "previous_tools": str(previous_tools.resolve()),
            "previous_tools_sha256": sha(previous_tools),
            "budget_sha256": digest(summary),
            "committed_usd": summary["committed_usd"],
            "calls": len(summary["calls"]),
            "messages_sha256": digest(carried_messages),
            "prior_packet": str(resume_from.resolve()),
        }
    request = {
        "model": model["model"],
        "max_tokens": model["output_token_limit"],
        "system": SYSTEM,
        "tools": TOOLS,
        **inference,
        "messages": [
            {
                "role": "user",
                "content": "Explore the full v3 language using offline fitting scripts. "
                "Submit normal artifacts and use development-only live feedback, then "
                "freeze one measured zero-loss candidate for comparison or explicitly abstain. "
                "Report failed timing controls separately. "
                "Preserve all six filters plus unfiltered.",
            }
        ],
    }
    if carried:
        notice = (
            "Operational continuation: the prior worker ended on its idle clock while you were "
            "fitting offline, before any learned policy was submitted. All prior model spend, "
            "conversation and research files carry forward. The same development evidence, v3 "
            "language, quality gate and final comparison remain. The repaired controller sends "
            "activity heartbeats; the aggregate compute and monetary caps are not reset. "
            "Continue your existing search, evaluate promising artifacts, then freeze one "
            "measured zero-loss candidate or abstain. No protected result has been opened."
        )
        messages = json.loads(json.dumps(carried_messages))
        if messages[-1]["role"] != "user" or not isinstance(messages[-1]["content"], list):
            raise ValueError("unexpected carried conversation boundary")
        messages[-1]["content"].append({"type": "text", "text": notice})
        request["messages"] = messages
    write(output / "first-request.json", request)
    source_files = [p for p in HERE.iterdir() if p.suffix in (".py", ".sh", ".md")]
    # Bind the controller's transitive policy/store/budget and provider preflight sources too.
    source_files += list((ROOT / "agent/src/fannagent").rglob("*.py"))
    source_files += list((HERE.parent / "filtered-ann-protocol-v3/fannproto3").glob("*.py"))
    source_files.append(PROFILE)
    review = {
        "schema": "fannagent.live-feedback-review.v3",
        "status": "prepared_not_authorized",
        "host": host,
        "stage": stage,
        "ssh_control_path": control_path,
        "known_hosts": str(STUDY / "oracle-variants-v1/connection/known_hosts-b0-v1"),
        "known_hosts_sha256": sha(STUDY / "oracle-variants-v1/connection/known_hosts-b0-v1"),
        "kit_sha256": sha(kit / "SHA256SUMS"),
        "model_config": model,
        "api_version": api_version,
        "inference": inference,
        "default_model_profile_sha256": sha(PROFILE),
        "evidence_path": str(evidence),
        "evidence_sha256": sha(evidence),
        "evidence_identity": digest(workspace_binding),
        "workspace": str(workspace),
        "workspace_binding": workspace_binding,
        "research_image": workspace_binding["image"],
        "protocol_sha256": sha(HERE / "PROTOCOL.md"),
        "first_request_sha256": sha(output / "first-request.json"),
        "source_sha256": {str(p): sha(p) for p in source_files},
        "provider": "https://api.anthropic.com/v1/messages",
        "disclosure": "Anonymized development causal observations and executed-prefix labels, "
        "model-authored research scripts/policies, and live development measurements. "
        "No vectors, neighbor/source IDs, oracle artifacts, "
        "validation/test outcomes or credentials.",
        "torch_wall_seconds": 21600,
        "new_allowance_authorized": False,
        "paid_requests": None,
        "automatic_retry": False,
        "proposed_new_episode_cap_usd": model["ceiling_usd"],
        "resume": carried,
    }
    write(output / "review.json", review)
    write(
        output / "approval-specification.json",
        {
            "status": "pending",
            "review_sha256": sha(output / "review.json"),
            "user_approval_record": "Explicit approval of the reviewed live episode required",
        },
    )
    return review


class Provider:
    automatic_retries = False

    def __init__(self, output, api_version="2026-10-21"):
        self.output = output
        self.api_version = api_version
        self.ordinal = 0

    def post(self, endpoint, payload, label):
        import minisweagent  # noqa: F401  Existing local credential loader; never loaded on Torch.

        if any(os.environ.get(k) for k in ("ANTHROPIC_API_BASE", "ANTHROPIC_BASE_URL")):
            raise ValueError("provider overrides are outside the frozen contract")
        credential = os.environ.get("ANTHROPIC_API_KEY")
        if not credential:
            raise ValueError("existing Anthropic credential unavailable")
        write(self.output / (label + "-request.json"), payload)
        connection = http.client.HTTPSConnection(
            "api.anthropic.com",
            timeout=180,
            context=ssl.create_default_context(cafile=certifi.where()),
        )
        try:
            connection.request(
                "POST",
                endpoint,
                body=canonical(payload),
                headers={
                    "content-type": "application/json",
                    "x-api-key": credential,
                    "anthropic-version": self.api_version,
                },
            )
            response = connection.getresponse()
            raw = response.read(8 * 1024**2 + 1)
            if len(raw) > 8 * 1024**2:
                raise ValueError("provider response exceeds wire limit")
            value = json.loads(raw)
            write(self.output / (label + "-response.json"), value)
            if response.status != 200:
                raise ValueError("provider HTTP failure; no automatic retry")
            return value
        finally:
            connection.close()

    def count(self, request):
        self.ordinal += 1
        payload = {k: request[k] for k in ("model", "system", "tools", "messages", "thinking")}
        result = self.post("/v1/messages/count_tokens", payload, f"count-{self.ordinal}")
        count = result.get("input_tokens")
        if type(count) is not int or not 0 <= count <= 900000:
            raise ValueError("context does not fit the frozen live episode")

    def __call__(self, request):
        return self.post("/v1/messages", request, f"message-{self.ordinal}")


def drive(tools, store, budget, template, provider):
    messages = template["messages"]
    while not tools.state["terminal"]:
        worker = tools.client.call("status")
        if worker["status"] != "running" or not worker["accepting_development"]:
            tools.state["terminal"] = "worker_stopped_or_admission_closed"
            break
        tools.client.call("heartbeat")
        if budget.summary()["uncertain_calls"]:
            raise ValueError("uncertain model charge requires audit")
        request = {**template, "messages": messages}
        if len(canonical(request)) + 8192 > 8 * 1024**2:
            tools.state["terminal"] = "context_limit"
            break
        maximum = budget.maximum_call()
        available = Decimal(budget.config.ceiling_usd) - Decimal(budget.summary()["committed_usd"])
        if maximum > available:
            tools.state["terminal"] = "dollar_limit"
            break
        provider.count(request)  # One exact context check per attempt, before monetary reservation.
        reservation = budget.reserve(maximum, {"request_sha256": digest(request)})
        try:
            response = provider(request)
            artifact = store.put("live_model_response", response, scope="private")
            usage = response["usage"]
            a, b = usage["input_tokens"], usage["output_tokens"]
            if (
                response["model"] != budget.config.model
                or type(a) is not int
                or type(b) is not int
                or not 0 <= a <= budget.config.input_token_bound
                or not 0 <= b <= budget.config.output_token_limit
                or usage.get("cache_creation_input_tokens", 0)
                or usage.get("cache_read_input_tokens", 0)
                or usage.get("service_tier", "standard") != "standard"
                or usage.get("inference_geo", "global") != "global"
                or usage.get("speed", "standard") != "standard"
            ):
                raise ValueError("provider identity, service or charge contract differs")
            charge = (
                a * budget.config.input_usd_per_million + b * budget.config.output_usd_per_million
            ) / 1000000
            budget.settle(reservation, charge, {"response_artifact": artifact, "usage": usage})
        except BaseException as error:
            budget.uncertain(reservation, type(error).__name__)
            raise
        content = response["content"]
        if not isinstance(content, list) or any(not isinstance(b, dict) for b in content):
            raise ValueError("malformed paid response retained; no automatic retry")
        uses = [block for block in content if block.get("type") == "tool_use"]
        feedback = []
        ids = [block.get("id") for block in uses]
        if any(type(i) is not str for i in ids) or len(set(ids)) != len(ids):
            raise ValueError("ambiguous tool envelope retained; no automatic retry")
        for block in uses:
            answer = tools.call(block["id"], block["name"], block["input"])
            if not tools.state["terminal"]:
                tools.client.call("heartbeat")
            feedback.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": canonical(answer).decode(),
                    "is_error": "error" in answer,
                }
            )
        if not uses:
            # No silent request to rescue a missing final/tool action.
            tools.state["terminal"] = "model_finished_without_submission"
            break
        messages += [
            {"role": "assistant", "content": content},
            {"role": "user", "content": feedback},
        ]
        store.set("live_messages", messages)
    write(tools.path, tools.state)
    return {
        "status": tools.state["terminal"],
        "budget": budget.summary(),
        "nominees": tools.state.get("nominees", []),
        "performance_claim": False,
    }


def run(prepared, approval_path):
    require_live_workflow()
    review = read(prepared / "review.json")
    approval = read(approval_path)
    if (
        approval.get("status") != "authorized"
        or approval.get("review_sha256") != sha(prepared / "review.json")
        or not approval.get("user_approval_record")
    ):
        raise ValueError("new live-episode approval does not match the review packet")
    for path, expected in review["source_sha256"].items():
        if sha(path) != expected:
            raise ValueError("reviewed source changed: " + path)
    if sha(review["evidence_path"]) != review["evidence_sha256"]:
        raise ValueError("development evidence changed")
    if sha(prepared / "first-request.json") != review["first_request_sha256"]:
        raise ValueError("reviewed prompt changed")
    output = prepared / "live"
    output.mkdir(mode=0o700, exist_ok=False)
    request = read(prepared / "first-request.json")
    inference = {
        k: request[k] for k in ("thinking", "output_config", "inference_geo", "service_tier")
    }
    api_version = review.get("api_version", "2023-06-01")
    verify_current_provider(
        output / "provider-preflight", review["model_config"], api_version, inference
    )
    resume = review.get("resume")
    store = Store(Path(resume["campaign"])) if resume else Store(output / "campaign", create=True)
    budget = Budget(store, ModelConfig.model_validate(review["model_config"]))
    if resume:
        if digest(budget.summary()) != resume["budget_sha256"]:
            raise ValueError("carried budget changed after review")
        if sha(resume["previous_tools"]) != resume["previous_tools_sha256"]:
            raise ValueError("carried tool state changed after review")
        if digest(store.get("live_messages")) != resume["messages_sha256"]:
            raise ValueError("carried conversation changed after review")
    client = TorchClient(
        review["host"],
        review["stage"],
        output / "torch",
        control_path=review.get("ssh_control_path"),
        known_hosts=review["known_hosts"],
    )
    if sha(review["known_hosts"]) != review["known_hosts_sha256"]:
        raise ValueError("reviewed SSH host trust changed")
    worker = client.call("status")
    if worker.get("kit_sha256") != review["kit_sha256"]:
        raise ValueError("Torch worker does not match the reviewed kit")
    if not worker.get("qualified"):
        raise ValueError("run the model-free diagnostic batch in this same allocation first")
    for name, expected in review["workspace_binding"]["files"].items():
        if sha(Path(review["workspace"]) / name) != expected:
            raise ValueError("reviewed development workspace changed: " + name)
    tool_args = (
        read(review["evidence_path"]),
        client,
        output / "tools.json",
    )
    if resume:
        tools = LiveTools.resume(
            *tool_args, resume["previous_tools"], review["workspace"], review["research_image"]
        )
    else:
        tools = LiveTools(*tool_args, review["workspace"], review["research_image"])
    provider = Provider(output, api_version)
    if resume:
        provider.ordinal = resume["calls"]
    try:
        result = drive(tools, store, budget, read(prepared / "first-request.json"), provider)
    except BaseException:
        tools.state["terminal"] = "interrupted_requires_audit_no_retry"
        write(tools.path, tools.state)
        write(
            output / "disposition.json",
            {"status": tools.state["terminal"], "budget": budget.summary()},
        )
        raise
    write(output / "disposition.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=("prepare", "run"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--host")
    p.add_argument("--stage")
    p.add_argument("--kit", type=Path)
    p.add_argument("--ssh-control-path")
    p.add_argument("--approval", type=Path)
    p.add_argument("--resume-from", type=Path)
    args = p.parse_args()
    print(
        canonical(
            prepare(
                args.output,
                args.host,
                args.stage,
                args.kit,
                args.ssh_control_path,
                args.resume_from,
            )
            if args.operation == "prepare"
            else run(args.output, args.approval)
        ).decode()
    )
