import json

import pytest
import transport
from episode import PARAMETERS, canonical, digest, sha, write


def packet(root):
    prepared = root / "prepared"
    prepared.mkdir()
    request = {
        **PARAMETERS,
        "system": "synthetic unit-test scope",
        "tools": [],
        "messages": [{"role": "user", "content": "synthetic"}],
    }
    (prepared / "first-request.json").write_bytes(canonical(request))
    fields = (
        "model",
        "system",
        "tools",
        "inference_geo",
        "service_tier",
        "thinking",
        "output_config",
    )
    contract = {
        "evidence_identity": "e" * 64,
        "first_request_sha256": sha(prepared / "first-request.json"),
        "prompt_tools_inference_hash": digest({k: request[k] for k in fields}),
    }
    write(prepared / "episode-contract.json", contract)
    write(
        prepared / "approval-specification.json",
        {"status": "pending_user_approval_not_dispatchable"},
    )
    package = root / "package.json"
    write(package, {"source_sha256": {}, "artifact_sha256": {}})
    approval = {
        "status": "authorized",
        "model": PARAMETERS["model"],
        "endpoint": "https://api.anthropic.com/v1/messages",
        "evidence_hash": "e" * 64,
        "max_requests": 6,
        "max_output_tokens": 6000,
        "ceiling_usd": "15",
        "episode_contract_sha256": sha(prepared / "episode-contract.json"),
        "first_request_sha256": contract["first_request_sha256"],
        "prompt_tools_inference_hash": contract["prompt_tools_inference_hash"],
        "package_sha256": sha(package),
        "user_approval_record": "Synthetic HTTP-stub unit test only; not a live M4 approval.",
    }
    path = root / "unit-only-approval.json"
    write(path, approval)
    return prepared, package, path, request


def test_pending_or_mismatched_approval_blocks_before_credentials_or_network(tmp_path, monkeypatch):
    prepared, package, approval, _ = packet(tmp_path)
    monkeypatch.setattr(transport, "credentials", lambda: pytest.fail("credential accessed"))
    with pytest.raises(transport.ApprovalRequired):
        transport.MessagesTransport(tmp_path / "missing.json", prepared, package, tmp_path / "run")
    value = json.loads(approval.read_text())
    value["status"] = "pending_user_approval_not_dispatchable"
    write(approval, value)
    with pytest.raises(transport.ApprovalRequired):
        transport.MessagesTransport(approval, prepared, package, tmp_path / "run")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(inference_geo="us"),
        lambda r: r.update(model="unapproved-model"),
        lambda r: r.update(cache_control={"type": "ephemeral"}),
        lambda r: r["messages"].append(
            {
                "role": "user",
                "content": [{"type": "text", "text": "x", "cache_control": {"type": "ephemeral"}}],
            }
        ),
        lambda r: r.update(system="changed prompt"),
    ],
)
def test_parameter_prompt_or_cache_drift_never_reaches_network(tmp_path, monkeypatch, mutation):
    prepared, package, approval, request = packet(tmp_path)
    t = transport.MessagesTransport(approval, prepared, package, tmp_path / "provider")
    monkeypatch.setattr(transport, "credentials", lambda: pytest.fail("credential accessed"))
    mutation(request)
    with pytest.raises(ValueError):
        t(request)
    assert t.ordinal == 0


@pytest.mark.parametrize("status", [200, 503])
def test_http_attempt_is_single_and_headers_are_never_persisted(tmp_path, monkeypatch, status):
    prepared, package, approval, request = packet(tmp_path)
    calls = []

    class Reply:
        def __init__(self):
            self.status = status

        def read(self, _):
            return json.dumps(
                {
                    "type": "message",
                    "role": "assistant",
                    "model": PARAMETERS["model"],
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "service_tier": "standard",
                        "inference_geo": "global",
                    },
                    "content": [
                        {
                            "type": "thinking",
                            "thinking": "Synthetic progress.",
                            "signature": "test-signature",
                        },
                        {"type": "text", "text": '{"abstain":true}'},
                    ],
                }
            ).encode()

        def getheader(self, _):
            return "synthetic-request-id"

    class Connection:
        def __init__(self, host, **_):
            assert host == "api.anthropic.com"

        def request(self, method, path, **kwargs):
            assert method == "POST" and path == "/v1/messages"
            assert kwargs["headers"]["x-api-key"] == "synthetic-not-real-secret"
            calls.append((method, path))

        def getresponse(self):
            return Reply()

        def close(self):
            pass

    monkeypatch.setattr(transport.http.client, "HTTPSConnection", Connection)
    monkeypatch.setattr(transport, "credentials", lambda: "synthetic-not-real-secret")
    t = transport.MessagesTransport(approval, prepared, package, tmp_path / "provider")
    if status == 200:
        assert t(request)["content"][0]["signature"] == "test-signature"
    else:
        with pytest.raises(ValueError, match="no automatic retry"):
            t(request)
    assert calls == [("POST", "/v1/messages")]
    assert all(
        "synthetic-not-real-secret" not in p.read_text()
        for p in (tmp_path / "provider").rglob("*")
        if p.is_file()
    )


def test_cache_detection_does_not_interpret_user_text_as_a_directive():
    assert not transport.has_cache_directive(
        {"content": 'The literal word "cache_control" is text.'}
    )


@pytest.mark.parametrize("drift", [None, "model", "price", "full-context"])
def test_fresh_preflight_uses_only_get_and_stops_when_approved_terms_change(
    tmp_path, monkeypatch, drift
):
    model = {
        "id": PARAMETERS["model"],
        "max_input_tokens": 1000000,
        "lifecycle": "active",
        "capabilities": {
            "thinking": {"types": {"between_tools": {"supported": True}}},
            "effort": {"high": {"supported": True}},
        },
    }
    if drift == "model":
        model["lifecycle"] = "retired"
    overview = "Input $2 / MTok. Output $10 / MTok."
    if drift == "price":
        overview = overview.replace("$2", "$3")
    pricing = "900k-token request is billed at the same per-token rate as a 9k-token request"
    if drift == "full-context":
        pricing = "Changed full-context terms."
    routes = {
        ("api.anthropic.com", "/v1/models/" + PARAMETERS["model"]): json.dumps(model).encode(),
        ("platform.claude.com", "/docs/en/models/sonnet-5-5/overview.md"): overview.encode(),
        ("platform.claude.com", "/docs/en/about-claude/pricing.md"): pricing.encode(),
    }
    calls = []

    def get(host, path, **_):
        calls.append((host, path))
        return routes[(host, path)]

    monkeypatch.setattr(transport, "get", get)
    monkeypatch.setattr(transport, "credentials", lambda: "synthetic-only")
    target = tmp_path / "fresh"
    if drift:
        with pytest.raises(ValueError, match="reapproval required"):
            transport.verify_current_provider(target)
        assert not (target / "receipt.json").exists()
    else:
        transport.verify_current_provider(target)
        receipt = json.loads((target / "receipt.json").read_text())
        assert receipt["paid_requests"] == 0
    assert calls and all(path != "/v1/messages" for _, path in calls)
