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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "agent/src"))
from fannagent.budget import Budget  # noqa: E402
from fannagent.config import ModelConfig  # noqa: E402
from fannagent.store import Store  # noqa: E402

STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
OLD_CONTRACT = STUDY / "m4-episode-v1/prepared/episode-contract.json"


def prepare(output, host, stage, kit, control_path=None):
    output.mkdir(parents=True, exist_ok=False)
    model = read(OLD_CONTRACT)["model_config"]
    workspace = kit.parent / "workspace"
    evidence = workspace / "evidence/summary.json"
    workspace_binding = read(kit.parent / "workspace-binding.json")
    request = {
        "model": model["model"],
        "max_tokens": model["output_token_limit"],
        "system": SYSTEM,
        "tools": TOOLS,
        "inference_geo": "global",
        "service_tier": "standard_only",
        "thinking": {"type": "between_tools"},
        "output_config": {"effort": "high"},
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
    write(output / "first-request.json", request)
    source_files = [p for p in HERE.iterdir() if p.suffix in (".py", ".sh", ".md")]
    # Bind the controller's transitive policy/store/budget and provider preflight sources too.
    source_files += list((ROOT / "agent/src/fannagent").rglob("*.py"))
    source_files += list((HERE.parent / "filtered-ann-protocol-v3/fannproto3").glob("*.py"))
    source_files += [
        HERE.parent / "m4-provider-episode-v1" / n
        for n in ("preflight.py", "transport.py", "episode.py")
    ]
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

    def __init__(self, output):
        self.output = output
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
                    "anthropic-version": "2023-06-01",
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
    # Official prices/model/account capability are rechecked with the established read-only code.
    sys.path.insert(0, str(HERE.parent / "m4-provider-episode-v1"))
    from transport import verify_current_provider

    verify_current_provider(output / "provider-preflight")
    store = Store(output / "campaign", create=True)
    budget = Budget(store, ModelConfig.model_validate(review["model_config"]))
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
    tools = LiveTools(
        read(review["evidence_path"]),
        client,
        output / "tools.json",
        review["workspace"],
        review["research_image"],
    )
    provider = Provider(output)
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
    args = p.parse_args()
    print(
        canonical(
            prepare(args.output, args.host, args.stage, args.kit, args.ssh_control_path)
            if args.operation == "prepare"
            else run(args.output, args.approval)
        ).decode()
    )
