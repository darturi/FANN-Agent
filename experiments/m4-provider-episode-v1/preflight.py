"""Unpaid official-document/model GETs only. Never send evidence or persist credentials."""

import datetime
import hashlib
import http.client
import json
import os
import re
import ssl
from pathlib import Path

import certifi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEST = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small/m4-episode-v1"
MODEL = "claude-sonnet-5-5"
API_VERSION = "2023-06-01"
DOCUMENTS = {
    "model": "/docs/en/models/sonnet-5-5/overview.md",
    "pricing": "/docs/en/about-claude/pricing.md",
    "thinking": "/docs/en/build-with-claude/thinking.md",
    "versioning": "/docs/en/about-claude/models/model-ids-and-versions.md",
    "messages": "/docs/en/api/messages/create.md",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def credentials():
    import minisweagent  # noqa: F401  Existing local dotenv loader, same as previous episodes.

    if any(os.environ.get(k) for k in ("ANTHROPIC_API_BASE", "ANTHROPIC_BASE_URL")):
        raise ValueError("provider endpoint overrides are not permitted")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("configured Anthropic credential unavailable; no generation attempted")
    return key


def get(host, path, *, key=None):
    connection = http.client.HTTPSConnection(
        host, timeout=30, context=ssl.create_default_context(cafile=certifi.where())
    )
    headers = {"User-Agent": "FANNAgent-M4-read-only-preflight/1"}
    if key is not None:
        if host != "api.anthropic.com" or path != "/v1/models/" + MODEL:
            raise ValueError("credential may only accompany the pinned model GET")
        headers.update({"x-api-key": key, "anthropic-version": API_VERSION})
    try:
        connection.request("GET", path, headers=headers)
        reply = connection.getresponse()
        body = reply.read(4 * 1024**2 + 1)
        if reply.status != 200 or len(body) > 4 * 1024**2:
            raise ValueError(f"preflight GET failed: {host}{path}, HTTP{reply.status}")
        return body
    finally:
        connection.close()


def run():
    target = DEST / "provider"
    assert not (target / "preflight.json").exists(), "preserve completed preflight"
    records = {}
    for label, path in DOCUMENTS.items():
        body = get("platform.claude.com", path)
        (target / (label + ".md")).write_bytes(body)
        records[label] = {"url": "https://platform.claude.com" + path, "sha256": sha(body)}
    model_text = (target / "model.md").read_text()
    normalized = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", model_text))
    assert MODEL in normalized
    for label, rate in (("Input", "2"), ("Output", "10")):
        assert re.search(
            label + r"(?:\s+pricing)?\s*[:|]?\s*\$" + rate + r"(?:\.0+)?\s*/\s*(?:MTok|million)",
            normalized,
            re.I,
        ), label + " price not verified"
    assert re.search(r"1M\s*(?:token|tokens)", normalized), "1M context not verified"
    info_bytes = get("api.anthropic.com", "/v1/models/" + MODEL, key=credentials())
    info = json.loads(info_bytes)
    assert info["id"] == MODEL, "model ID changed; no silent substitution"
    if "lifecycle" in info:
        assert info["lifecycle"] == "active", "model is not active"
    maximum = info.get("max_input_tokens") or 1000000
    assert type(maximum) is int and 0 < maximum <= 1000000
    capabilities = info.get("capabilities", {})
    if "thinking" in capabilities:
        assert capabilities["thinking"]["types"]["between_tools"]["supported"]
    if "effort" in capabilities:
        assert capabilities["effort"]["high"]["supported"]
    (target / "model-api-response.json").write_bytes(info_bytes)
    receipt = {
        "schema": "filtered-ann.M4-provider-preflight.v1",
        "date": "2026-11-16",
        "checked_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "status": "official_prices_and_account_model_GET_verified",
        "model": MODEL,
        "api_version": API_VERSION,
        "model_response_sha256": sha(info_bytes),
        "official_documents": records,
        "input_usd_per_million": "2",
        "output_usd_per_million": "10",
        "documented_context_bound": 1000000,
        "billing_input_token_bound": maximum,
        "input_bound_source": "Models API max_input_tokens or official1M context ceiling",
        "inference_geo": "global",
        "service_tier": "standard_only",
        "thinking": {"type": "between_tools"},
        "effort": "high",
        "cache_control": "none",
        "server_tools": [],
        "credential": "existing local minisweagent dotenv reference; never persisted",
        "authenticated_model_GETs": 1,
        "paid_Messages_requests": 0,
        "development_payloads_sent": 0,
        "provider_calls_for_generation": 0,
        "validation_test_outcomes_opened": False,
    }
    (target / "preflight.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "model",
                    "input_usd_per_million",
                    "output_usd_per_million",
                    "billing_input_token_bound",
                    "paid_Messages_requests",
                    "development_payloads_sent",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
