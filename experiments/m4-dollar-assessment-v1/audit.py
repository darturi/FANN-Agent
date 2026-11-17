"""Audit the dollar-governed episode and freeze its actual agent-submitted nominees."""

import importlib.util
import json
import shutil
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "m4-dollar-budget-v1"))
import support  # noqa: E402,F401
from common import count_payload, tool_block  # noqa: E402
from fannproto.compiler import compile_programs  # noqa: E402
from fannproto.controller import candidate_feedback  # noqa: E402
from fannproto.policy import (  # noqa: E402
    FILTERS,
    choose,
    observation_plan,
    replay,
    rule_hash,
    validate,
)
from fannproto.uncertainty import select_shortlist  # noqa: E402
from support import (  # noqa: E402
    CONFIG,
    DEST,
    PRIOR,
    ROOT,
    STUDY,
    Evidence,
    ReadOnlyStore,
    canonical,
    digest,
    load_authorization,
    notice,
    prompt_hash,
    sha,
    verify_origin,
    verify_package,
    write,
)


def independent_scorer():
    source = HERE.parent / "m4-continuation-assessment-v1/audit.py"
    receipt = json.loads((PRIOR / "assessment-v1/receipt.json").read_text())
    assert sha(source) == receipt["audit_source_sha256"]
    spec = importlib.util.spec_from_file_location("verified_prior_manual_scorer", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.independent_scores, sha(source)


def expected_notice(evidence, charges, submissions, tools, *, initial=False):
    snapshot = SimpleNamespace(
        store=SimpleNamespace(
            get=lambda _: {"candidate_submissions": submissions, "tool_calls": tools}
        ),
        budget=SimpleNamespace(
            summary=lambda: {
                "calls": charges,
                "committed_usd": str(Decimal(sum(c["actual"] for c in charges)) / 1000000000),
            }
        ),
        evidence=evidence,
    )
    return notice(snapshot, "research", initial=initial)


def audit():
    output = DEST / "assessment-v1"
    assert not output.exists(), "preserve completed audit; version amendments"
    frozen = verify_package()
    prior = verify_origin()
    approval = load_authorization(DEST / "execution-authorization.json")
    contract = json.loads((DEST / "prepared/contract.json").read_text())
    evidence = Evidence(json.loads((ROOT / contract["evidence_workspace_path"]).read_text()))
    assert evidence.identity == contract["evidence_identity"] == approval["evidence_hash"]
    assert len(evidence.rows) == 3150 and set(evidence.summary()["per_filter"]) == set(FILTERS)
    live = DEST / "live-dollar-continuation"
    disposition = json.loads((live / "disposition.json").read_text())
    store = ReadOnlyStore(live / "campaign")
    state = store.get("v2_state")
    assert state["terminal"] == disposition["status"] == "finalists_frozen_pending_live_measurement"
    assert state["candidate_submissions"] == disposition["cumulative_candidates"] == 8
    assert state["tool_calls"] == disposition["cumulative_tools"] == 10
    assert disposition["candidate_ids"] == ["candidate-7", "candidate-8"]
    assert disposition["new_Messages_attempts"] == disposition["new_count_attempts"] == 2
    assert disposition["request_ceiling"] is None
    assert store.get("v2_contract")["limits"]["paid_requests"] is None
    assert store.get("v2_round_pending") is None and not (live / "local-stop.json").exists()
    with store.connect() as db:
        charges = [dict(x) for x in db.execute("SELECT * FROM charges ORDER BY rowid")]
        artifacts = [dict(x) for x in db.execute("SELECT * FROM artifacts ORDER BY rowid")]
        assert db.execute("SELECT COUNT(*) FROM leases").fetchone()[0] == 0
    assert charges == disposition["budget"]["calls"] and len(charges) == 8
    assert all(c["status"] == "settled" for c in charges)
    prior_disposition = json.loads(
        (PRIOR / "live-continuation/continuation-disposition.json").read_text()
    )
    assert charges[:6] == prior_disposition["budget"]["calls"]
    assert disposition["budget"]["uncertain_calls"] == 0
    assert (
        disposition["budget"]["ceiling_usd"] == "15"
        and disposition["budget"]["allowance_usd"] == "0"
    )
    for item in artifacts:
        store.read(item["hash"])
        assert item["scope"] in ("private", "development")
    assert len(artifacts) == 50
    bridge = store.get("dollar_bridge")
    assert bridge["simulation_only"] is False
    assert bridge["prior_history_sha256"] == contract["prior_history_sha256"]
    assert bridge["prior_charge_ids"] == [c["id"] for c in charges[:6]]
    assert bridge["prior_spend_usd"] == "0.244308"
    preflight = json.loads((live / "dispatch-preflight/receipt.json").read_text())
    assert preflight["status"] == "current_model_and_rates_match_approved_contract"
    for file, key in (
        ("model.json", "model_sha256"),
        ("model-overview.md", "pricing_sha256"),
        ("pricing.md", "full_context_pricing_sha256"),
    ):
        assert sha(live / "dispatch-preflight" / file) == preflight[key]

    manual_score, scorer_sha = independent_scorer()
    records = {cid: store.read(a, agent=True) for cid, a in state["registry"].items()}
    assert sorted(records) == [f"candidate-{n}" for n in range(1, 9)]
    for inherited in prior["candidates"]:
        assert state["registry"][inherited["candidate_id"]] == inherited["record_artifact"]
    summaries = []
    for cid, record in sorted(records.items()):
        policy = validate(record["policy"])
        assert record["rule_hash"] == rule_hash(policy)
        assert record["evaluation"] == replay(policy, evidence.rows)
        losses, stops, _ = manual_score(policy, evidence.rows, record["evaluation"])
        assert record["observation_plan"] == observation_plan(policy)
        assert record["cost_estimate"] == evidence.estimate(policy)
        assert record["work_estimate"] == evidence.work_estimate(policy)
        source, manifest = compile_programs(
            [{"arm": 20, "policy": policy, "force_continue": False}]
        )
        assert store.read(record["compiled_artifact"], agent=True) == {
            "source": source,
            "manifest": manifest,
        }
        if cid in disposition["candidate_ids"]:
            assert not any(losses.values())
            assert record["cost_estimate"]["status"] == "supported_uncertainty_shortlist_proxy"
            assert record["observation_plan"] == {
                f: {"16": 0, "32": 0, "64": 11 if f in ("unfiltered", "votes32") else 0}
                for f in FILTERS
            }
        summaries.append(
            {
                "candidate_id": cid,
                "name": policy["name"],
                "rule_hash": record["rule_hash"],
                "record_artifact": state["registry"][cid],
                "compiled_artifact": record["compiled_artifact"],
                "recall_losses": sum(losses.values()),
                "per_filter_losses": losses,
                "per_filter_stops": stops,
                "quality_preserves_raw_native640": record["evaluation"][
                    "quality_preserves_raw_native640"
                ],
                "cost_status": record["cost_estimate"]["status"],
                "primary_ratio_proxy": record["cost_estimate"].get("primary_ratio_proxy"),
                "primary_ratio_interval": record["cost_estimate"].get("primary_ratio_interval"),
                "per_filter_quality": record["evaluation"]["per_filter"],
            }
        )
    assert [s["recall_losses"] for s in summaries] == [8, 4, 1, 1, 1, 0, 0, 0]
    decision = select_shortlist([{"candidate_id": cid, **r} for cid, r in records.items()])
    assert decision["candidate_ids"] == disposition["candidate_ids"]
    assert decision["conditional_regret_bound"] == 0
    assert disposition["nominees"] == {cid: records[cid] for cid in decision["candidate_ids"]}

    initial = json.loads((DEST / "prepared/first-request.json").read_text())
    assert initial["messages"][-1] == expected_notice(evidence, charges[:6], 6, 8, initial=True)
    assert digest(initial["messages"][:-1]) == contract["prior_history_sha256"]
    history = deepcopy(initial["messages"])
    gates = json.loads((DEST / "prepared/gates.json").read_text())
    provider = live / "provider"
    assert sorted(p.name for p in provider.iterdir()) == [
        "count-7",
        "count-8",
        "message-7",
        "message-8",
    ]
    rows = []
    additional = Decimal("0")
    for ordinal in (7, 8):
        count_dir, message_dir = provider / f"count-{ordinal}", provider / f"message-{ordinal}"
        request = json.loads((message_dir / "request.json").read_text())
        assert request == {**initial, "messages": history}
        assert prompt_hash(request) == gates["phase_prompt_hashes"]["research"]
        assert canonical(request) == (message_dir / "request.json").read_bytes()
        assert store.read(digest(request)) == request
        assert len(canonical(request)) + 8192 < CONFIG["request_byte_bound"]
        counted = json.loads((count_dir / "response.json").read_text())["input_tokens"]
        assert json.loads((count_dir / "request.json").read_text()) == count_payload(request)
        count_receipt = json.loads((count_dir / "context-receipt.json").read_text())
        assert count_receipt == {
            "ordinal": ordinal,
            "request_hash": digest(request),
            "phase": "research",
            "input_tokens": counted,
        }
        assert counted <= 900000 and counted + 6000 < 1000000
        for folder, path in (
            (count_dir, "/v1/messages/count_tokens"),
            (message_dir, "/v1/messages"),
        ):
            attempt = json.loads((folder / "attempt.json").read_text())
            http = json.loads((folder / "http.json").read_text())
            assert attempt["method"] == "POST" and attempt["automatic_retries"] is False
            assert attempt["endpoint"] == "https://api.anthropic.com" + path
            assert attempt["request_sha256"] == sha(folder / "request.json")
            assert http["status"] == 200 and http["response_sha256"] == sha(
                folder / "response.json"
            )
        response = json.loads((message_dir / "response.json").read_text())
        usage = response["usage"]
        assert response["type"] == "message" and response["role"] == "assistant"
        assert response["model"] == "claude-sonnet-5-5" and response["stop_reason"] == "tool_use"
        assert usage["input_tokens"] == counted and 0 <= usage["output_tokens"] <= 6000
        assert usage["cache_creation_input_tokens"] == usage["cache_read_input_tokens"] == 0
        assert (
            usage["service_tier"] == usage["speed"] == "standard"
            and usage["inference_geo"] == "global"
        )
        charge = charges[ordinal - 1]
        metadata = json.loads(charge["metadata"])
        assert metadata["usage"] == usage and store.read(metadata["response_artifact"]) == response
        actual = (
            Decimal(usage["input_tokens"]) * 2 + Decimal(usage["output_tokens"]) * 10
        ) / 1000000
        assert actual == Decimal(charge["actual"]) / 1000000000
        assert Decimal(charge["reserved"]) / 1000000000 == Decimal("2.06")
        additional += actual
        uses = [x for x in response["content"] if x["type"] == "tool_use"]
        assert len(uses) == 1
        use = uses[0]
        args = use["input"]
        if ordinal == 7:
            assert use["name"] == "evaluate_candidates" and len(args["policies"]) == 2
            assert args["policies"] == [
                records[cid]["policy"] for cid in ("candidate-7", "candidate-8")
            ]
            value = {
                "evaluations": [
                    {"candidate_id": cid, **candidate_feedback(records[cid])}
                    for cid in ("candidate-7", "candidate-8")
                ],
                "candidate_submissions_remaining": 1,
            }
        else:
            assert use["name"] == "submit_or_abstain" and args["abstain"] is False
            assert args["candidate_ids"] == decision["candidate_ids"]
            value = {
                "status": "finalists_frozen_pending_live_measurement",
                "candidate_ids": decision["candidate_ids"],
                "selection_decision": decision,
                "no_performance_promotion": True,
            }
        assert disposition["outcomes"][ordinal - 7] == {
            "tool_results": [{"tool_use_id": use["id"], "result": value}]
        }
        tool_receipt = state["receipts"][use["id"]]
        assert (
            tool_receipt["status"] == "complete"
            and store.read(tool_receipt["artifact"], agent=True) == value
        )
        assert tool_receipt["signature"] == digest({"operation": use["name"], "arguments": args})
        feedback = tool_block(use["id"], value)
        assert len(canonical(feedback)) < CONFIG["tool_result_block_bytes"]
        history.extend(
            [
                {"role": "assistant", "content": response["content"]},
                {"role": "user", "content": [feedback]},
            ]
        )
        if ordinal == 7:
            history.append(expected_notice(evidence, charges[:7], 8, 9))
        rows.append(
            {
                "ordinal": ordinal,
                "input_tokens": counted,
                "output_tokens": usage["output_tokens"],
                "thinking_output_tokens": usage["output_tokens_details"]["thinking_tokens"],
                "actual_usd": str(actual),
                "request_bytes": len(canonical(request)),
                "request_sha256": sha(message_dir / "request.json"),
                "response_sha256": sha(message_dir / "response.json"),
            }
        )
    assert history == store.get("v2_messages")
    assert sha(provider / "message-7/request.json") == contract["first_request_sha256"]
    assert additional == Decimal("0.158806")
    total = sum(Decimal(c["actual"]) / 1000000000 for c in charges)
    assert total == Decimal(disposition["budget"]["committed_usd"]) == Decimal("0.403114") < 15
    same_stops = all(
        choose(records["candidate-6"]["policy"], row)
        == choose(records["candidate-7"]["policy"], row)
        for row in evidence.rows
    )
    verify_package()
    verify_origin()
    live_hashes = {}
    for path in sorted(live.rglob("*")):
        if not path.is_file() or path.name.endswith("-shm"):
            continue
        if path.name.endswith("-wal") and path.stat().st_size == 0:
            continue
        live_hashes[str(path.relative_to(ROOT))] = sha(path)
    output.mkdir()
    nominees = {
        "schema": "filtered-ann.formally-submitted-development-nominees.v1",
        "source_package_sha256": sha(DEST / "package-freeze.json"),
        "evidence_identity": evidence.identity,
        "scope": contract["scope"],
        "agent_submitted": True,
        "selection_decision": decision,
        "nominees": [
            {
                "candidate_id": cid,
                "policy": records[cid]["policy"],
                "rule_hash": records[cid]["rule_hash"],
                "source_record_artifact": state["registry"][cid],
                "source_compiled_artifact": records[cid]["compiled_artifact"],
            }
            for cid in decision["candidate_ids"]
        ],
        "development_only": True,
        "live_latency_measured": False,
        "validation_test_outcomes_opened": False,
    }
    write(output / "nominees.json", nominees)
    receipt = {
        "schema": "filtered-ann.M4-dollar-assessment.v1",
        "date": "2026-11-16",
        "status": "verified_two_agent_submitted_zero_loss_cost_supported_M5_nominees",
        "execution_commit": "f85f9d6",
        "package_sha256": sha(DEST / "package-freeze.json"),
        "execution_authorization_sha256": sha(DEST / "execution-authorization.json"),
        "evidence_identity": evidence.identity,
        "scope": contract["scope"],
        "old_outcomes_unchanged": True,
        "configured_sources_verified": len(frozen["source_sha256"]),
        "configured_artifacts_verified": len(frozen["artifact_sha256"]),
        "durable_artifacts_rehashed": len(artifacts),
        "new_Messages_requests": 2,
        "new_count_requests": 2,
        "total_Messages_requests": 8,
        "request_ceiling": None,
        "new_spend_usd": str(additional),
        "total_spend_usd": str(total),
        "ceiling_usd": "15",
        "remaining_USD": str(Decimal("15") - total),
        "uncertain_calls": 0,
        "retries": 0,
        "all_count_estimates_match_actual_usage": True,
        "signed_history_preserved_unchanged": True,
        "requests": rows,
        "total_input_tokens": 110859 + sum(r["input_tokens"] for r in rows),
        "total_output_tokens": 2259 + sum(r["output_tokens"] for r in rows),
        "candidate_submissions": 8,
        "domain_tools": 10,
        "independently_scored_policy_query_filter_cases": 25200,
        "candidates": summaries,
        "final_submission_received": True,
        "formal_M5_nominees": decision["candidate_ids"],
        "selection_decision": decision,
        "ending_reason": "Agent explicitly submitted; no monetary or research quota was reached",
        "same_candidate6_and_candidate7_stop_decisions_on_development": same_stops,
        "nominees_workspace_path": str((output / "nominees.json").relative_to(ROOT)),
        "nominees_sha256": sha(output / "nominees.json"),
        "SQL_searches": 0,
        "exact_search_calls": 0,
        "exact_truth_use": "Frozen offline recall labels; no serving repair",
        "live_policy_latency_measured": False,
        "validation_test_outcomes_opened": False,
        "next_step": "M5 development-only qualification and timing of both exact frozen "
        "nominees, native and matched continue-only controls across six filters and unfiltered",
        "audit_source_sha256": sha(Path(__file__)),
        "independent_scorer_source_sha256": scorer_sha,
        "live_artifacts_sha256": live_hashes,
    }
    write(output / "receipt.json", receipt)
    freeze_path = STUDY / "freeze/m4-dollar-outcome-v1.json"
    assert not freeze_path.exists()
    write(
        freeze_path,
        {
            "schema": "filtered-ann.M4-dollar-outcome.v1",
            "date": "2026-11-16",
            "status": receipt["status"],
            "receipt_workspace_path": str((output / "receipt.json").relative_to(ROOT)),
            "receipt_sha256": sha(output / "receipt.json"),
            "nominees_sha256": receipt["nominees_sha256"],
            "formal_M5_nominees": decision["candidate_ids"],
            "total_spend_usd": str(total),
            "total_Messages_requests": 8,
            "validation_test_outcomes_opened": False,
        },
    )
    copies = HERE / "receipts"
    copies.mkdir(exist_ok=False)
    for path in (
        output / "receipt.json",
        output / "nominees.json",
        freeze_path,
        DEST / "execution-authorization.json",
    ):
        shutil.copyfile(path, copies / path.name)
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "new_Messages_requests",
                    "total_Messages_requests",
                    "new_spend_usd",
                    "total_spend_usd",
                    "formal_M5_nominees",
                    "ending_reason",
                    "validation_test_outcomes_opened",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    audit()
