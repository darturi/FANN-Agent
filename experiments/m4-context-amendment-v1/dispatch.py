"""Approved four-request continuation, with free context preflights and no retries."""

import http.client
import json
import ssl
from pathlib import Path

import certifi
from common import (
    CONTEXT,
    DEST,
    accept_count,
    canonical,
    check_request,
    count_payload,
    load_approval,
    sha,
    verify_package,
    write,
)
from preflight import API_VERSION, credentials


def post(path, payload, folder):
    """One exact first-party POST; no headers or key are persisted."""
    folder.mkdir()
    wire = canonical(payload)
    (folder / "request.json").write_bytes(wire)
    write(
        folder / "attempt.json",
        {
            "method": "POST",
            "endpoint": "https://api.anthropic.com" + path,
            "request_sha256": sha(folder / "request.json"),
            "automatic_retries": False,
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
            path,
            body=wire,
            headers={
                "x-api-key": credentials(),
                "anthropic-version": API_VERSION,
                "content-type": "application/json",
            },
        )
        response = connection.getresponse()
        raw = response.read(2 * 1024**2 + 1)
        (folder / "response.json").write_bytes(raw)
        write(
            folder / "http.json",
            {
                "status": response.status,
                "request_id": response.getheader("request-id"),
                "response_sha256": sha(folder / "response.json"),
            },
        )
        if response.status != 200 or len(raw) > 2 * 1024**2:
            raise ValueError("provider POST failed; no retry")
        return json.loads(raw)
    finally:
        connection.close()


class ContinuationTransport:
    automatic_retries = False

    def __init__(self, authorization, output):
        self.authorization = Path(authorization)
        load_approval(self.authorization)
        self.authorization_hash = sha(self.authorization)
        self.output = Path(output)
        self.output.mkdir(exist_ok=False)
        self.next_ordinal = 3
        self.pending_count = None
        self.count_attempts = 0
        self.message_attempts = 0
        self.counted_ordinals = set()

    def check(self, request):
        if sha(self.authorization) != self.authorization_hash:
            raise ValueError("amended authorization changed during dispatch")
        verify_package(DEST / "package-freeze.json")
        return check_request(request)

    def count(self, request, ordinal):
        request_hash = self.check(request)
        if (
            ordinal != self.next_ordinal
            or not 3 <= ordinal <= 6
            or self.count_attempts >= 4
            or self.pending_count is not None
            or ordinal in self.counted_ordinals
        ):
            raise ValueError("count preflight ordinal exhausted or reused; no retry")
        self.count_attempts += 1
        self.counted_ordinals.add(ordinal)
        folder = self.output / f"count-{ordinal}"
        response = post("/v1/messages/count_tokens", count_payload(request), folder)
        count = accept_count(response)
        self.pending_count = {
            "ordinal": ordinal,
            "request_hash": request_hash,
            "input_tokens": count,
        }
        write(
            folder / "context-receipt.json",
            {
                **self.pending_count,
                "status": "estimated_input_within_context_margin",
                "output_reserve_tokens": 6000,
                "estimated_context_total": count + 6000,
                "model_context_tokens": 1000000,
                "paid_Messages_requests": 0,
            },
        )
        return count

    def __call__(self, request):
        request_hash = self.check(request)
        if (
            self.pending_count is None
            or self.pending_count["request_hash"] != request_hash
            or self.pending_count["ordinal"] != self.next_ordinal
            or self.message_attempts >= 4
            or self.next_ordinal > 6
        ):
            raise ValueError("exact successful context preflight required before Messages")
        ordinal = self.next_ordinal
        self.pending_count = None
        self.next_ordinal += 1
        self.message_attempts += 1
        response = post("/v1/messages", request, self.output / f"message-{ordinal}")
        usage = response["usage"]
        if response.get("type") != "message" or response.get("role") != "assistant":
            raise ValueError("unexpected Messages envelope")
        if (
            usage.get("service_tier", "standard") != "standard"
            or usage.get("inference_geo", "global") != "global"
            or usage.get("speed", "standard") != "standard"
        ):
            raise ValueError("unqualified service, speed or geography; halt for audit")
        assistant = {"role": "assistant", "content": response["content"]}
        if len(canonical(assistant)) > CONTEXT["assistant_message_bytes"]:
            raise ValueError(
                "provider assistant envelope exceeds qualified capacity; halt for audit"
            )
        # Core Campaign settles usage and preserves every signed block unchanged.
        return response
