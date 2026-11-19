"""Unpaid, model-specific provider qualification for a future authorized run.

Generic verifier only; no saved provider receipts or empirical artifacts are reused.
"""

import datetime
import http.client
import json
import os
import re
import ssl

import certifi

from .core import sha, write

MODELS = {"claude-opus-5-5": "/docs/en/models/opus-5-5/overview.md"}
PRICING = "/docs/en/about-claude/pricing.md"


def official_get(host, path, *, api_version, authenticated=False):
    headers = {"User-Agent": "FANNAgent-v3-model-preflight/1"}
    if authenticated:
        if host != "api.anthropic.com" or path not in {"/v1/models/" + m for m in MODELS}:
            raise ValueError("credentials are restricted to the selected model metadata GET")
        import minisweagent  # noqa: F401  Existing local dotenv loader; never loaded on Torch.

        if any(os.environ.get(k) for k in ("ANTHROPIC_API_BASE", "ANTHROPIC_BASE_URL")):
            raise ValueError("provider endpoint overrides are outside the contract")
        credential = os.environ.get("ANTHROPIC_API_KEY")
        if not credential:
            raise ValueError("existing Anthropic credential unavailable")
        headers.update({"x-api-key": credential, "anthropic-version": api_version})
    elif host != "platform.claude.com" or path not in {*MODELS.values(), PRICING}:
        raise ValueError("only pinned official documents may be fetched")
    connection = http.client.HTTPSConnection(
        host, timeout=30, context=ssl.create_default_context(cafile=certifi.where())
    )
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        body = response.read(4 * 1024**2 + 1)
        if response.status != 200 or len(body) > 4 * 1024**2:
            raise ValueError(f"unpaid provider preflight failed: HTTP {response.status}")
        return body
    finally:
        connection.close()


def verify_current_provider(target, model_config, api_version, inference, *, fetch=official_get):
    """Check the exact reviewed model, rates and inference settings; generate nothing."""
    model_id = model_config["model"]
    if model_id not in MODELS:
        raise ValueError("unsupported provider model")
    if inference["inference_geo"] != "global" or inference["service_tier"] != "standard_only":
        raise ValueError("only global standard pricing is supported")
    target.mkdir(exist_ok=False)
    body = fetch(
        "api.anthropic.com",
        "/v1/models/" + model_id,
        api_version=api_version,
        authenticated=True,
    )
    (target / "model.json").write_bytes(body)
    model = json.loads(body)
    thinking = inference["thinking"]["type"]
    effort = inference["output_config"]["effort"]
    if (
        model.get("id") != model_id
        or model.get("max_input_tokens") != model_config["input_token_bound"]
        or model.get("lifecycle") != "active"
        or not model["capabilities"]["thinking"]["types"][thinking]["supported"]
        or not model["capabilities"]["effort"][effort]["supported"]
    ):
        raise ValueError("selected model metadata/capabilities differ from the reviewed profile")
    text = fetch("platform.claude.com", MODELS[model_id], api_version=api_version)
    pricing = fetch("platform.claude.com", PRICING, api_version=api_version)
    (target / "model-overview.md").write_bytes(text)
    (target / "pricing.md").write_bytes(pricing)
    normalized = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text.decode()))
    if model_id not in normalized:
        raise ValueError("official overview does not identify the selected model")
    for label, key in (("Input", "input_usd_per_million"), ("Output", "output_usd_per_million")):
        rate = re.escape(str(model_config[key]))
        if not re.search(
            label + r"(?:\s+pricing)?\s*[:|]?\s*\$" + rate + r"(?:\.0+)?\s*/\s*(?:MTok|million)",
            normalized,
            re.I,
        ):
            raise ValueError("current price differs from the reviewed profile")
    if (
        "900k-token request is billed at the same per-token rate as a 9k-token request"
        not in pricing.decode()
    ):
        raise ValueError("full-context standard pricing could not be verified")
    receipt = {
        "status": "current_model_and_rates_match_reviewed_profile",
        "checked_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "model": model_id,
        "api_version": api_version,
        "model_sha256": sha(target / "model.json"),
        "pricing_sha256": sha(target / "model-overview.md"),
        "full_context_pricing_sha256": sha(target / "pricing.md"),
        "input_usd_per_million": str(model_config["input_usd_per_million"]),
        "output_usd_per_million": str(model_config["output_usd_per_million"]),
        "thinking": thinking,
        "effort": effort,
        "paid_requests": 0,
        "development_payloads_sent": 0,
    }
    write(target / "receipt.json", receipt)
    return receipt
