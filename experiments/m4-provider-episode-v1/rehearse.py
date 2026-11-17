"""No-network M4 preparation rehearsal on real bound evidence; no live approval created."""

import json
from unittest.mock import patch

from episode import DEST, ROOT, STUDY, Evidence, ModelConfig, canonical, make_request, sha, write
from fannproto.controller import Campaign, ProtocolError
from fannproto.rehearsal import ScriptedTransport
from run_episode import run as real_run
from transport import ApprovalRequired

from fannagent.store import Store


def run():
    output = DEST / "no-network-rehearsal"
    output.mkdir(exist_ok=False)
    prepared = DEST / "prepared"
    contract = json.loads((prepared / "episode-contract.json").read_text())
    evidence = Evidence(json.loads((ROOT / contract["evidence_workspace_path"]).read_text()))
    gates = json.loads((prepared / "bound-gates.json").read_text())
    config = ModelConfig.model_validate({**contract["model_config"], "model": "scripted"})
    programs = json.loads(
        (STUDY / "kits/m1-runtime-qualification-v2/compiled-programs.json").read_text()
    )["bindings"]
    policies = {p["arm"]: p["policy"] for p in programs}
    campaign = Campaign(Store(output / "scripted-campaign", create=True), config, evidence, gates)
    progress = {
        "type": "thinking",
        "thinking": "Synthetic rehearsal progress.",
        "signature": "synthetic-not-valid-for-real-provider",
    }
    contents = [
        [
            progress,
            {
                "type": "tool_use",
                "id": "evaluate",
                "name": "evaluate_candidates",
                "input": {"policies": [policies[20], policies[21], policies[22]]},
            },
        ],
        [
            progress,
            {
                "type": "text",
                "text": "Freeze the scripted qualification nominees.\n```json\n{}\n```",
            },
        ],
    ]
    transport = ScriptedTransport(contents)
    sizes, outcomes = [], []
    with patch(
        "socket.create_connection", side_effect=AssertionError("network forbidden in rehearsal")
    ):
        for _ in range(2):
            request = make_request(campaign, prepared)
            request["model"] = "scripted"
            sizes.append(len(canonical(request)))
            outcomes.append(campaign.round(request, transport))
        assert set(outcomes[-1]["candidate_ids"]) == {"candidate-1", "candidate-2", "candidate-3"}
        assert outcomes[-1]["selection_decision"]["conditional_regret_bound"] == 0
        assert transport.requests[1]["messages"][1]["content"][0] == progress
        assert max(sizes) + 8192 <= 50000
        paid = Campaign(
            Store(output / "pending-approval-campaign", create=True),
            ModelConfig.model_validate(contract["model_config"]),
            evidence,
            gates,
        )
        never = ScriptedTransport([])
        try:
            paid.round(make_request(paid, prepared), never)
        except ProtocolError as error:
            assert "provider authorization" in str(error)
        else:
            raise AssertionError("pending user approval did not block generation")
        assert not never.requests and not paid.budget.summary()["calls"]
        try:
            real_run(DEST / "authorization.json")
        except ApprovalRequired:
            pass
        else:
            raise AssertionError("real driver did not require the frozen approval")
        assert not (DEST / "live-episode").exists()
    budget = campaign.budget.summary()
    assert budget["calls"] and all(c["status"] == "settled" for c in budget["calls"])
    assert (
        campaign.budget.maximum_call().as_tuple() == config.ceiling_usd.__class__("2.06").as_tuple()
    )
    result = {
        "schema": "filtered-ann.M4-preparation-rehearsal.v1",
        "date": "2026-11-16",
        "status": "passed_no_network_real_evidence_pending_approval_and_progress_checks",
        "evidence_identity": evidence.identity,
        "first_real_request_sha256": contract["first_request_sha256"],
        "simulation_difference": "Only wire/config model ID becomes scripted; prompt/tools/"
        "inference/evidence/byte bound/billing ceilings are the prepared real contract.",
        "scripted_requests": 2,
        "request_bytes": sizes,
        "synthetic_accounting_usd": budget["committed_usd"],
        "maximum_financial_reservation_usd": "2.06",
        "six_maximal_reservations_usd": "12.36",
        "pending_real_approval_blocks_transport_and_reservation": True,
        "real_runner_blocks_before_credentials_or_live_state": True,
        "progress_blocks_preserved_unchanged": True,
        "conditional_shortlist": outcomes[-1]["selection_decision"],
        "known_policy_nominees_are_scripted_fixtures_not_new_discovery": True,
        "provider_generation_requests": 0,
        "actual_API_spend_usd": "0",
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
    }
    result["artifacts_sha256"] = {
        str(p.relative_to(output)): sha(p) for p in sorted(output.rglob("*")) if p.is_file()
    }
    write(output / "receipt.json", result)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("artifacts_sha256", "conditional_shortlist")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
