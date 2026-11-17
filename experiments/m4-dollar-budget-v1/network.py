"""One context check per paid attempt, with no request-count ceiling."""

from pathlib import Path

from support import (
    CONFIG,
    accept_count,
    canonical,
    count_payload,
    has_cache_directive,
    load_authorization,
    post,
    prompt_hash,
    sha,
    template,
    verify_package,
    write,
)


class DollarTransport:
    automatic_retries = False

    def __init__(self, authorization, output, start_ordinal):
        self.authorization = Path(authorization)
        load_authorization(authorization)
        self.authorization_hash = sha(self.authorization)
        self.output = Path(output)
        self.output.mkdir(exist_ok=False)
        self.next_ordinal = start_ordinal
        self.counted_ordinals = set()
        self.pending_count = None
        self.count_attempts = self.message_attempts = 0

    def check(self, request, phase):
        if sha(self.authorization) != self.authorization_hash:
            raise ValueError("dollar authorization changed")
        verify_package()
        if prompt_hash(request) != prompt_hash(template(phase)):
            raise ValueError("request differs from frozen dollar phase contract")
        if set(request) != set(template(phase)) or request["max_tokens"] != 6000:
            raise ValueError("unapproved request field or output limit")
        if has_cache_directive(request):
            raise ValueError("cache directives are outside the charge contract")
        if len(canonical(request)) + 8192 > CONFIG["request_byte_bound"]:
            raise ValueError("actual wire capacity exceeded")
        return sha_request(request)

    def count(self, request, ordinal, phase):
        key = self.check(request, phase)
        if ordinal != self.next_ordinal or ordinal in self.counted_ordinals or self.pending_count:
            raise ValueError("count ordinal reused or out of sequence; no retry")
        self.counted_ordinals.add(ordinal)
        self.count_attempts += 1
        folder = self.output / f"count-{ordinal}"
        count = accept_count(post("/v1/messages/count_tokens", count_payload(request), folder))
        self.pending_count = {
            "ordinal": ordinal,
            "request_hash": key,
            "phase": phase,
            "input_tokens": count,
        }
        write(folder / "context-receipt.json", self.pending_count)
        return count

    def __call__(self, request):
        if not self.pending_count:
            raise ValueError("exact successful count preflight required")
        pending = self.pending_count
        if self.check(request, pending["phase"]) != pending["request_hash"]:
            raise ValueError("request changed after count preflight")
        ordinal = self.next_ordinal
        self.next_ordinal += 1
        self.pending_count = None
        self.message_attempts += 1
        response = post("/v1/messages", request, self.output / f"message-{ordinal}")
        if response.get("type") != "message" or response.get("role") != "assistant":
            raise ValueError("unexpected provider envelope")
        usage = response["usage"]
        if (
            usage.get("service_tier", "standard") != "standard"
            or usage.get("inference_geo", "global") != "global"
            or usage.get("speed", "standard") != "standard"
        ):
            raise ValueError("provider service/geography/speed changed; audit without retry")
        return response


def sha_request(request):
    from fannagent.store import digest

    return digest(request)
