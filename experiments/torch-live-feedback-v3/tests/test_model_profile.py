import copy
import json
from decimal import Decimal

import pytest
import run_agent
from limits import read, sha, write
from model_profile import PROFILE, load_profile, verify_current_provider

from fannagent.budget import Budget
from fannagent.config import ModelConfig
from fannagent.errors import AgentError
from fannagent.store import Store


def metadata():
    return {
        "id": "claude-opus-5-5",
        "max_input_tokens": 1000000,
        "lifecycle": "active",
        "capabilities": {
            "thinking": {
                "types": {"adaptive": {"supported": True}, "between_tools": {"supported": False}}
            },
            "effort": {"high": {"supported": True}},
        },
    }


def fetcher(info, overview=None):
    calls = []

    def fetch(host, path, **kwargs):
        calls.append((host, path, kwargs))
        if host == "api.anthropic.com":
            assert path == "/v1/models/claude-opus-5-5"
            assert kwargs["authenticated"]
            return json.dumps(info).encode()
        if "overview" in path:
            return (
                overview or b"claude-opus-5-5 Input pricing: $4 / MTok Output pricing: $20 / MTok"
            )
        return b"A 900k-token request is billed at the same per-token rate as a 9k-token request"

    return fetch, calls


def test_opus_preflight_checks_selected_model_and_actual_rates(tmp_path):
    profile = load_profile()
    fetch, calls = fetcher(metadata())
    result = verify_current_provider(
        tmp_path / "preflight",
        profile["model_config"],
        profile["api_version"],
        profile["inference"],
        fetch=fetch,
    )
    assert result["model"] == "claude-opus-5-5" and result["thinking"] == "adaptive"
    assert result["paid_requests"] == result["development_payloads_sent"] == 0
    assert len(calls) == 3
    budget = Budget(
        Store(tmp_path / "campaign", create=True),
        ModelConfig.model_validate(profile["model_config"]),
    )
    assert budget.maximum_call() == Decimal("4.12")


@pytest.mark.parametrize(
    "change", ["wrong_model", "inactive", "bound", "thinking", "effort", "price"]
)
def test_changed_opus_terms_or_unsupported_thinking_fail_before_dispatch(tmp_path, change):
    profile = load_profile()
    info = metadata()
    overview = None
    if change == "wrong_model":
        info["id"] = "claude-sonnet-5-5"
    elif change == "inactive":
        info["lifecycle"] = "retired"
    elif change == "bound":
        info["max_input_tokens"] = 200000
    elif change == "thinking":
        profile["inference"]["thinking"]["type"] = "between_tools"
    elif change == "effort":
        info["capabilities"]["effort"]["high"]["supported"] = False
    else:
        overview = b"claude-opus-5-5 Input pricing: $5 / MTok Output pricing: $25 / MTok"
    fetch, _ = fetcher(info, overview)
    with pytest.raises(ValueError, match="differ"):
        verify_current_provider(
            tmp_path / "preflight",
            profile["model_config"],
            profile["api_version"],
            profile["inference"],
            fetch=fetch,
        )
    assert not (tmp_path / "preflight/receipt.json").exists()


def fixture_kit(tmp_path, monkeypatch):
    study = tmp_path / "study"
    known = study / "oracle-variants-v1/connection/known_hosts-b0-v1"
    known.parent.mkdir(parents=True)
    known.write_text("synthetic host key\n")
    monkeypatch.setattr(run_agent, "STUDY", study)
    kit = tmp_path / "input/kit"
    kit.mkdir(parents=True)
    (kit / "SHA256SUMS").write_text("fixture\n")
    evidence = kit.parent / "workspace/evidence/summary.json"
    evidence.parent.mkdir(parents=True)
    write(evidence, {"development_cases": 3150})
    write(kit.parent / "workspace-binding.json", {"image": "fixture-image", "files": {}})
    return kit, evidence


def test_fresh_preparation_uses_opus_and_binds_profile_without_dispatch(tmp_path, monkeypatch):
    kit, _ = fixture_kit(tmp_path, monkeypatch)
    output = tmp_path / "prepared"
    review = run_agent.prepare(output, "fixture-host", "/fixture-stage", kit)
    request = read(output / "first-request.json")
    assert request["model"] == "claude-opus-5-5" and request["max_tokens"] == 6000
    assert request["thinking"] == {"type": "adaptive"}
    assert request["output_config"] == {"effort": "high"}
    assert review["api_version"] == "2026-10-21"
    assert review["source_sha256"][str(PROFILE)] == sha(PROFILE)
    assert read(output / "approval-specification.json")["status"] == "pending"
    assert not (output / "live").exists()


def test_legacy_resume_preserves_sonnet_contract_and_inference(tmp_path, monkeypatch):
    kit, evidence = fixture_kit(tmp_path, monkeypatch)
    model = load_profile()["model_config"]
    model.update(
        model="claude-sonnet-5-5",
        input_usd_per_million="2",
        output_usd_per_million="10",
        pricing_revision="legacy-fixture",
    )
    prior = tmp_path / "prior"
    prior.mkdir()
    write(
        prior / "review.json",
        {
            "model_config": model,
            "workspace": str(evidence.parent.parent),
            "evidence_path": str(evidence),
            "workspace_binding": read(kit.parent / "workspace-binding.json"),
        },
    )
    write(
        prior / "first-request.json",
        {
            "thinking": {"type": "between_tools"},
            "output_config": {"effort": "high"},
            "inference_geo": "global",
            "service_tier": "standard_only",
        },
    )
    store = Store(prior / "live/campaign", create=True)
    Budget(store, ModelConfig.model_validate(model))
    store.set("live_messages", [{"role": "user", "content": []}])
    write(
        prior / "live/tools.json",
        {"terminal": "worker_stopped_or_admission_closed", "receipts": {}},
    )
    output = tmp_path / "resumed"
    review = run_agent.prepare(output, "fixture", "/fixture", kit, resume_from=prior)
    assert review["model_config"] == model
    assert review["api_version"] == "2023-06-01"
    assert read(output / "first-request.json")["thinking"] == {"type": "between_tools"}
    with pytest.raises(AgentError, match="spending contract"):
        Budget(store, ModelConfig.model_validate(load_profile()["model_config"]))


def test_opus_tool_loop_returns_thinking_blocks_unmodified(tmp_path):
    class Tools:
        state = {"terminal": None}
        path = tmp_path / "tools.json"

        def __init__(self):
            self.client = self

        def call(self, *args):
            if args[0] in ("status", "heartbeat"):
                return {"status": "running", "accepting_development": True}
            if args[1] == "finish":
                self.state["terminal"] = "abstained"
            return {}

    first_content = [
        {"type": "thinking", "thinking": "synthetic fixture", "signature": "fixture"},
        {"type": "tool_use", "id": "first", "name": "inspect", "input": {}},
    ]
    requests = []

    class Provider:
        def count(self, request):
            pass

        def __call__(self, request):
            requests.append(copy.deepcopy(request))
            return {
                "model": "claude-opus-5-5",
                "usage": {"input_tokens": 10, "output_tokens": 20},
                "content": first_content
                if len(requests) == 1
                else [{"type": "tool_use", "id": "last", "name": "finish", "input": {}}],
            }

    store = Store(tmp_path / "campaign", create=True)
    budget = Budget(store, ModelConfig.model_validate(load_profile()["model_config"]))
    result = run_agent.drive(
        Tools(), store, budget, {"messages": [{"role": "user", "content": "fixture"}]}, Provider()
    )
    assert requests[1]["messages"][1]["content"] == first_content
    assert result["status"] == "abstained"
    assert result["budget"]["committed_usd"] == "0.00088"
