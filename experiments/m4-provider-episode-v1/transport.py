"""Pinned Messages transport: no retry, redirects or credentials in artifacts."""

import http.client
import json
import ssl
from pathlib import Path

import certifi
from episode import DEST, MODEL, PARAMETERS, canonical, digest, sha, write
from preflight import API_VERSION, credentials, get


class ApprovalRequired(ValueError):
    pass


def has_cache_directive(value):
    if isinstance(value, dict):
        return "cache_control" in value or any(has_cache_directive(v) for v in value.values())
    if isinstance(value, list):
        return any(has_cache_directive(v) for v in value)
    return False


def load_approval(path, prepared, package):
    path = Path(path)
    if not path.is_file():
        raise ApprovalRequired("explicit user approval is pending; no Messages dispatch")
    approval = json.loads(path.read_text())
    contract = json.loads((prepared / "episode-contract.json").read_text())
    spec = json.loads((prepared / "approval-specification.json").read_text())
    required = {
        "status": "authorized",
        "model": MODEL,
        "endpoint": "https://api.anthropic.com/v1/messages",
        "evidence_hash": contract["evidence_identity"],
        "max_requests": 6,
        "max_output_tokens": 6000,
        "ceiling_usd": "15",
        "episode_contract_sha256": sha(prepared / "episode-contract.json"),
        "first_request_sha256": contract["first_request_sha256"],
        "prompt_tools_inference_hash": contract["prompt_tools_inference_hash"],
        "package_sha256": sha(package),
    }
    if (
        any(approval.get(k) != v for k, v in required.items())
        or not isinstance(approval.get("user_approval_record"), str)
        or not approval["user_approval_record"].strip()
        or approval.get("simulation_only", False)
    ):
        raise ApprovalRequired("approval does not match the frozen M4 packet and scope")
    assert spec["status"] == "pending_user_approval_not_dispatchable"
    return approval


def verify_sources(package):
    frozen = json.loads(Path(package).read_text())
    root = DEST.parents[3]
    for path, digest_ in frozen["source_sha256"].items():
        if sha(root / path) != digest_:
            raise ValueError("frozen M4 source changed: " + path)
    for path, digest_ in frozen["artifact_sha256"].items():
        if sha(root / path) != digest_:
            raise ValueError("frozen M4 artifact changed: " + path)
    return frozen


def verify_current_provider(target):
    """After approval, recheck without sending evidence. Changed terms stop dispatch."""
    target.mkdir(exist_ok=False)
    body = get("api.anthropic.com", "/v1/models/" + MODEL, key=credentials())
    model = json.loads(body)
    if (
        model.get("id") != MODEL
        or model.get("max_input_tokens") != 1000000
        or model.get("lifecycle") != "active"
    ):
        raise ValueError("model metadata changed; reapproval required")
    if (
        not model["capabilities"]["thinking"]["types"]["between_tools"]["supported"]
        or not model["capabilities"]["effort"]["high"]["supported"]
    ):
        raise ValueError("model capabilities changed; reapproval required")
    text = get("platform.claude.com", "/docs/en/models/sonnet-5-5/overview.md")
    pricing = get("platform.claude.com", "/docs/en/about-claude/pricing.md")
    # Use the same exact rate patterns as preparation, preserving a fresh receipt.
    import re

    normalized = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text.decode()))
    for label, rate in (("Input", "2"), ("Output", "10")):
        if not re.search(
            label + r"(?:\s+pricing)?\s*[:|]?\s*\$" + rate + r"(?:\.0+)?\s*/\s*(?:MTok|million)",
            normalized,
            re.I,
        ):
            raise ValueError("current price could not be matched; reapproval required")
    if (
        "900k-token request is billed at the same per-token rate as a 9k-token request"
        not in pricing.decode()
    ):
        raise ValueError("full-context standard pricing changed; reapproval required")
    (target / "model.json").write_bytes(body)
    (target / "model-overview.md").write_bytes(text)
    (target / "pricing.md").write_bytes(pricing)
    write(
        target / "receipt.json",
        {
            "status": "current_model_and_rates_match_approved_contract",
            "model_sha256": sha(target / "model.json"),
            "pricing_sha256": sha(target / "model-overview.md"),
            "full_context_pricing_sha256": sha(target / "pricing.md"),
            "paid_requests": 0,
        },
    )


class MessagesTransport:
    automatic_retries = False

    def __init__(self, authorization_path, prepared, package, output, *, resume_attempts=None):
        self.prepared, self.package = Path(prepared), Path(package)
        self.authorization_path = Path(authorization_path)
        self.authorization = load_approval(authorization_path, self.prepared, self.package)
        self.authorization_hash = sha(self.authorization_path)
        self.contract = json.loads((self.prepared / "episode-contract.json").read_text())
        verify_sources(self.package)
        self.output = Path(output)
        self.output.mkdir(exist_ok=resume_attempts is not None)
        self.ordinal = 0 if resume_attempts is None else resume_attempts
        if len(list(self.output.glob("request-*"))) != self.ordinal:
            raise ValueError("provider attempt inventory differs; audit before resume")

    def __call__(self, request):
        verify_sources(self.package)
        if has_cache_directive(request):
            raise ValueError("prompt-cache directives are outside the approved charge contract")
        if sha(self.authorization_path) != self.authorization_hash:
            raise ApprovalRequired("authorization changed during the episode")
        if self.ordinal >= 6:
            raise ValueError("six Messages requests exhausted")
        for key, value in PARAMETERS.items():
            if request.get(key) != value:
                raise ValueError("provider parameters differ from approved contract")
        frozen = {
            k: request[k]
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
        if digest(frozen) != self.contract["prompt_tools_inference_hash"]:
            raise ValueError("prompt/tools/inference contract changed")
        payload = canonical(request)
        if len(payload) + 8192 > 50000:
            raise ValueError("operational byte limit reached before provider request")
        if set(request) != {
            "model",
            "max_tokens",
            "system",
            "tools",
            "messages",
            "inference_geo",
            "service_tier",
            "thinking",
            "output_config",
        }:
            raise ValueError("unapproved request field or server capability")
        self.ordinal += 1
        folder = self.output / f"request-{self.ordinal}"
        folder.mkdir(mode=0o700)
        (folder / "request.json").write_bytes(payload)
        write(
            folder / "attempt.json",
            {
                "method": "POST",
                "endpoint": "https://api.anthropic.com/v1/messages",
                "automatic_retries": False,
                "request_sha256": sha(folder / "request.json"),
            },
        )
        connection = http.client.HTTPSConnection(
            "api.anthropic.com",
            timeout=180,
            context=ssl.create_default_context(cafile=certifi.where()),
        )
        try:
            connection.request(
                "POST",
                "/v1/messages",
                body=payload,
                headers={
                    "x-api-key": credentials(),
                    "anthropic-version": API_VERSION,
                    "content-type": "application/json",
                },
            )
            reply = connection.getresponse()
            raw = reply.read(2 * 1024**2 + 1)
            (folder / "response.json").write_bytes(raw)
            write(
                folder / "http.json",
                {
                    "status": reply.status,
                    "request_id": reply.getheader("request-id"),
                    "response_sha256": sha(folder / "response.json"),
                },
            )
            if reply.status != 200 or len(raw) > 2 * 1024**2:
                raise ValueError("provider response failed; no automatic retry")
            response = json.loads(raw)
            usage = response["usage"]
            if (
                usage.get("service_tier", "standard") != "standard"
                or usage.get("inference_geo", "global") != "global"
            ):
                raise ValueError("unexpected service tier or geography; stop for audit")
            if response.get("type") != "message" or response.get("role") != "assistant":
                raise ValueError("unexpected Messages response envelope")
            return response
        finally:
            connection.close()
