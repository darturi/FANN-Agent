"""Fresh Opus conversation, context-sized reservations, no automatic paid retries."""

import http.client
import json
import math
import os
import ssl
import time
import uuid
from decimal import Decimal
from pathlib import Path

import certifi

from .controller import SYSTEM, Controller, empty_policy
from .core import Limits, canonical, digest, read, write
from .provider import verify_current_provider
from .transport import require_authorization

API_VERSION = "2026-10-21"
MODEL = "claude-opus-5-5"
INFERENCE = {
    "inference_geo": "global",
    "service_tier": "standard_only",
    "thinking": {"type": "adaptive"},
    "output_config": {"effort": "high"},
}
RATES = {
    "model": MODEL,
    "input_token_bound": 1000000,
    "input_usd_per_million": "4",
    "output_usd_per_million": "20",
}


class Money:
    """Microdollars. Uncertain requests retain their entire reservation forever.

    Counting is an estimate, so an input margin is not a provider invoice guarantee.
    Any bound/rate/usage anomaly ends dispatch before its tools are executed.
    """

    def __init__(self, path, run_id, cap):
        self.path = Path(path)
        if self.path.exists():
            raise ValueError("fresh model ledger required; no conversation/ledger resume")
        self.state = {
            "run_id": run_id,
            "cap": int(Decimal(cap) * 1000000),
            "charged": 0,
            "calls": {},
            "closed": False,
        }
        self.save()

    def save(self):
        write(self.path, self.state)

    def status(self):
        remaining = self.state["cap"] - self.state["charged"]
        return {
            "model_remaining_usd": str(Decimal(remaining) / 1000000),
            "model_charged_usd": str(Decimal(self.state["charged"]) / 1000000),
            "model_exhausted": self.state["closed"] or remaining < 40960,
        }

    def reserve(self, identity, counted, output_limit):
        if self.state["closed"] or any(c["status"] == "open" for c in self.state["calls"].values()):
            raise ValueError("uncertain or closed model ledger")
        if type(counted) is not int or not 0 < counted <= 1000000:
            raise ValueError("invalid provider token estimate")
        envelope = counted + max(1024, math.ceil(counted * 0.10))
        if envelope > 1000000:
            raise ValueError("context envelope exceeds the reviewed model limit")
        remaining = self.state["cap"] - self.state["charged"]
        output = min(output_limit, (remaining - 4 * envelope) // 20)
        if output < 2048:
            raise ValueError("insufficient model budget for input plus reasoning/tool output")
        reserved = 4 * envelope + 20 * output
        self.state["calls"][identity] = {
            "status": "open",
            "count_estimate": counted,
            "input_envelope": envelope,
            "output_limit": output,
            "reserved": reserved,
        }
        self.state["charged"] += reserved
        self.save()
        return output

    def settle(self, identity, usage):
        c = self.state["calls"][identity]
        inputs, outputs = usage.get("input_tokens"), usage.get("output_tokens")
        if type(inputs) is not int or type(outputs) is not int or min(inputs, outputs) < 0:
            self.state["closed"] = True
            self.save()
            raise ValueError("missing provider usage; retain reservation, stop without retry")
        creation, hits = (
            usage.get("cache_creation_input_tokens", 0),
            usage.get("cache_read_input_tokens", 0),
        )
        if type(creation) is not int or type(hits) is not int or min(creation, hits) < 0:
            raise ValueError("unrecognized cache billing; retain reservation")
        actual = 4 * inputs + 20 * outputs + 8 * creation + 4 * hits
        supported = (
            not creation
            and not hits
            and inputs <= c["input_envelope"]
            and outputs <= c["output_limit"]
            and actual <= c["reserved"]
            and usage.get("service_tier", "standard") == "standard"
            and usage.get("inference_geo", "global") == "global"
            and usage.get("speed", "standard") == "standard"
        )
        c.update(
            status="settled" if supported else "billing_bound_violation", usage=usage, actual=actual
        )
        self.state["charged"] += (
            actual - c["reserved"] if supported else max(0, actual - c["reserved"])
        )
        self.state["closed"] = not supported
        self.save()
        if not supported:
            raise ValueError("provider billing envelope changed; stop before executing tools")


class Provider:
    def __init__(self):
        import minisweagent  # noqa: F401 -- existing local credential loader

        if any(os.environ.get(k) for k in ("ANTHROPIC_API_BASE", "ANTHROPIC_BASE_URL")):
            raise ValueError("provider endpoint overrides are outside this protocol")
        self.key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.key:
            raise ValueError(
                "Anthropic credential unavailable; keep credentials outside the workspace"
            )

    def post(self, endpoint, payload, timeout):
        if endpoint not in ("/v1/messages", "/v1/messages/count_tokens"):
            raise ValueError("unsupported provider endpoint")
        connection = http.client.HTTPSConnection(
            "api.anthropic.com",
            timeout=timeout,
            context=ssl.create_default_context(cafile=certifi.where()),
        )
        try:
            connection.request(
                "POST",
                endpoint,
                canonical(payload),
                {
                    "x-api-key": self.key,
                    "anthropic-version": API_VERSION,
                    "content-type": "application/json",
                },
            )
            response = connection.getresponse()
            raw = response.read(8 * 1024**2 + 1)
            if response.status != 200 or len(raw) > 8 * 1024**2:
                raise ConnectionError(f"Provider HTTP {response.status}; no automatic retry")
            return json.loads(raw)
        finally:
            connection.close()


def run(root, client, *, provider=None, qualify=verify_current_provider, clock=time.monotonic):
    root = Path(root)
    require_authorization(root)
    config = read(root / "config.json")
    limits = Limits(**config["limits"])
    comparison = config.get("comparison")
    if comparison and comparison["arm"] != "agent":
        raise ValueError("model can run only in the sealed agent arm")
    host = root / "host"
    if host.exists():
        raise ValueError(
            "fresh host state required; prior conversation or scratch cannot be resumed"
        )
    host.mkdir()
    money = Money(host / "model-ledger.json", config["run_id"], limits.model_usd)
    controller = Controller(root, client, money.status)
    system = SYSTEM
    if comparison:
        system += (
            "\nThe controller starts by collecting a common fresh development panel. "
            "Use fit_batch for cheap grouped first-stop feedback. Prioritize follow-up "
            "measurements where candidates disagree, where early stops could save work, "
            "and where apparent convergence hid a recall loss. Propose alternate policies "
            "when the same-run evidence supports them. Call evaluate with policy_paths only "
            "to use the reserved development screening panel. Read same-run artifacts "
            "for detail. The controller periodically restarts model context at a "
            "completed tool boundary using a compact state. Record hypotheses and "
            "next steps using plan_search so they survive that transition."
        )
    if controller.revision:
        system += (
            "\nThis is a single agent-directed experiment. Explore high-upside policies "
            "and preserve useful early stops while refining the risky regions. "
            "Exploratory recall and count losses are expected signals for the next experiment. "
            "Use investigate_stop to measure the failing case and comparable successful "
            "stops at the original checkpoint and later checkpoints. Check recovery using "
            "measured prefixes because recall can vary nonmonotonically. Use evaluate_revision "
            "to test a targeted policy change alongside its parent on other development "
            "groups. Try alternate runtime features or guarded later stops where evidence "
            "supports them. Before voluntary abstention with resources left, investigate "
            "a measured failed stop if any and test a linked revision. Preserve resources "
            "for full confirmation. The strict recall and count requirements apply to the "
            "policy you freeze and its final evaluation."
        )
    messages = [
        {
            "role": "user",
            "content": (
                "Start this fresh discovery run. Inspect the static task, "
                "plan your research, and acquire your own evidence."
            ),
        }
    ]
    write(
        host / "initial-conversation.json",
        {
            "system": system,
            "messages": messages,
            "run_id": config["run_id"],
            "inherited_messages": 0,
        },
    )
    reason = "incomplete"
    started = clock()
    history = []
    bootstrap_receipt = {}
    calls_in_phase = 0
    try:
        worker = client.status()
        if worker.get("status") != "running" or worker.get("run_id") != config["run_id"]:
            raise ValueError("model cannot run without its matching fresh worker")
        qualify(host / "provider-check", RATES, API_VERSION, INFERENCE)
        provider = provider or Provider()
        if comparison:
            from .comparison import bootstrap

            bootstrap_receipt = bootstrap(controller, comparison)
            write(host / "comparison-bootstrap.json", bootstrap_receipt)
            messages.append(
                {"role": "user", "content": canonical(controller.compact_state()).decode()}
            )
        while not controller.state["terminal"]:
            resources = client.status()
            if resources.get("status") != "running":
                reason = "worker_closed"
                break
            remaining = min(
                resources["discovery_seconds_remaining"],
                limits.discovery_seconds - (clock() - started),
            )
            if remaining <= 60:
                reason = "discovery_time_exhausted"
                break
            client.call("heartbeat")
            identity = uuid.uuid4().hex
            payload = {
                "model": MODEL,
                "system": system,
                "tools": controller.tools,
                "messages": messages,
                **INFERENCE,
            }
            count_payload = {
                k: payload[k] for k in ("model", "system", "tools", "messages", "thinking")
            }
            counted = provider.post("/v1/messages/count_tokens", count_payload, min(60, remaining))
            write(
                host / "calls" / identity / "count.json",
                {"request_sha256": digest(count_payload), **counted},
            )
            try:
                payload["max_tokens"] = money.reserve(
                    identity, counted["input_tokens"], limits.output_tokens
                )
            except ValueError:
                reason = "model_budget_or_context_exhausted"
                break
            write(host / "calls" / identity / "request.json", payload)
            answer = provider.post("/v1/messages", payload, min(600, remaining - 30))
            write(host / "calls" / identity / "response.json", answer)
            money.settle(identity, answer["usage"])
            calls_in_phase += 1
            if answer.get("model") != MODEL:
                raise ValueError("provider returned a different model")
            # Preserve thinking/signature blocks byte-for-byte as JSON values.
            content = answer["content"]
            messages.append({"role": "assistant", "content": content})
            if answer.get("stop_reason") != "tool_use":
                reason = (
                    "truncated_output"
                    if answer.get("stop_reason") == "max_tokens"
                    else "model_ended_without_finish"
                )
                break
            results = []
            for block in content:
                if block["type"] != "tool_use":
                    continue
                if controller.state["terminal"]:
                    break
                resource = client.status()
                if resource["discovery_seconds_remaining"] <= 60:
                    reason = "discovery_time_exhausted_before_tool"
                    break
                client.call("heartbeat")
                result = controller.call(block["id"], block["name"], block["input"])
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block["id"],
                        "content": canonical(result).decode(),
                    }
                )
                if not controller.state["terminal"]:
                    client.call("heartbeat")
            if not results:
                break
            messages.append({"role": "user", "content": results})
            write(host / "conversation.json", history + messages)
            if not controller.state["terminal"]:
                client.call("heartbeat")
                if (
                    comparison
                    and calls_in_phase >= 6
                    and len(results) == sum(item["type"] == "tool_use" for item in content)
                ):
                    history.extend(messages)
                    messages = [
                        {
                            "role": "user",
                            "content": "Continue this same research run from the current state.\n"
                            + canonical(controller.compact_state()).decode(),
                        }
                    ]
                    calls_in_phase = 0
        if controller.state["terminal"]:
            reason = controller.state["terminal"]["status"]
    except Exception as error:
        reason = "incomplete_error"
        write(
            host / "error.json",
            {"type": type(error).__name__, "detail": str(error), "automatic_retry": False},
        )
    finally:
        money.state["closed"] = True
        money.save()
        write(host / "conversation.json", history + messages)
        if not (host / "freeze.json").exists():
            write(
                host / "freeze.json",
                {
                    "run_id": config["run_id"],
                    "policy": empty_policy(),
                    "test_feedback_seen": False,
                    "disposition": {
                        "status": "incomplete",
                        "reason": reason,
                        "candidate_id": None,
                        "performance_claim": False,
                    },
                },
            )
        result = {
            "run_id": config["run_id"],
            "status": reason,
            "model_closed": True,
            "freeze_sha256": digest(read(host / "freeze.json")),
            **money.status(),
            **(
                {
                    "model_calls": len(money.state["calls"]),
                    "initial_handles_sha256": bootstrap_receipt.get("initial_handles_sha256"),
                }
                if comparison
                else {}
            ),
        }
        write(host / "model-closed.json", result)
    return result
