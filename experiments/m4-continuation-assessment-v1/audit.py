"""Reconcile the closed continuation and independently score every proposed rule."""

import json
import shutil
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "m4-context-amendment-v1"))

from common import (  # noqa: E402
    CONTEXT,
    DEST,
    ORIGINAL,
    ROOT,
    STUDY,
    Evidence,
    ReadOnlyStore,
    canonical,
    count_payload,
    digest,
    load_approval,
    sha,
    tool_block,
    verify_origin,
    verify_package,
    write,
)
from fannproto.compiler import compile_programs  # noqa: E402
from fannproto.controller import candidate_feedback  # noqa: E402
from fannproto.policy import (  # noqa: E402
    FILTERS,
    POINTS,
    observation_plan,
    replay,
    rule_hash,
    validate,
)
from fannproto.uncertainty import select_shortlist  # noqa: E402


def independent_scores(policy, rows, evaluation):
    """First-satisfied causal rule over existing labels; no evaluator/choose helper."""
    losses = {f: 0 for f in FILTERS}
    stops = {f: 0 for f in FILTERS}
    sums = {f: 0.0 for f in FILTERS}
    unknown = {f: 0 for f in FILTERS}
    folds = {str(n): {"queries": 0, "losses": 0, "stops": 0, "unknown_stops": 0} for n in range(5)}
    failures = []
    for row in rows:
        chosen = None
        for clause in policy["rules"].get(row["filter"], []):
            observation = row["observations"].get(str(clause["cp"]))
            if observation is None:
                continue
            passed = True
            for name, op, threshold in clause["conditions"]:
                value = observation.get(name)
                if (
                    value is None
                    or (op == ">=" and value < threshold)
                    or (op == "<=" and value > threshold)
                ):
                    passed = False
                    break
            if passed:
                chosen = clause["cp"]
                break
        f = row["filter"]
        fold = folds[str(row["fold"])]
        fold["queries"] += 1
        score = row["native_recall"]
        if chosen is not None:
            stops[f] += 1
            fold["stops"] += 1
            proof = row["proofs"].get(str(chosen))
            if proof is None:
                unknown[f] += 1
                fold["unknown_stops"] += 1
                continue
            score = proof["recall"]
        sums[f] += score
        if score < row["native_recall"] - 1e-12:
            losses[f] += 1
            fold["losses"] += 1
            failures.append({"anonymous_group": row["group"], "filter": f, "checkpoint": chosen})
    for f in FILTERS:
        saved = evaluation["per_filter"][f]
        assert saved["queries"] == 450
        assert (saved["stops"], saved["losses"], saved["unknown_stops"]) == (
            stops[f],
            losses[f],
            unknown[f],
        )
        assert saved["mean_recall"] == (None if unknown[f] else sums[f] / 450)
    assert evaluation["per_exposed_development_fold"] == folds
    assert evaluation["recall_losses"] == sum(losses.values())
    assert evaluation["quality_preserves_raw_native640"] == (
        not any(losses.values()) and not any(unknown.values())
    )
    return losses, stops, failures


def audit():
    output = DEST / "assessment-v1"
    assert not output.exists(), "preserve completed assessments; version amendments"
    package = DEST / "package-freeze.json"
    frozen = verify_package(package)
    origin = verify_origin()
    assert origin["request_count"] == 2
    approval = load_approval(DEST / "authorization.json")
    contract = json.loads((DEST / "prepared/continuation-contract.json").read_text())
    evidence = Evidence(json.loads((ROOT / contract["evidence_workspace_path"]).read_text()))
    assert evidence.identity == contract["evidence_identity"] == approval["evidence_hash"]
    assert len(evidence.rows) == 3150 and set(evidence.summary()["per_filter"]) == set(FILTERS)
    live = DEST / "live-continuation"
    store = ReadOnlyStore(live / "campaign")
    state = store.get("v2_state")
    disposition = json.loads((live / "continuation-disposition.json").read_text())
    assert (
        state["terminal"]
        == disposition["status"]
        == "bounded_M4_abstention_cumulative_request_limit_without_submission"
    )
    assert store.get("v2_round_pending") is None and not (live / "local-stop.json").exists()
    assert state["candidate_submissions"] == disposition["cumulative_candidate_submissions"] == 6
    assert (
        state["tool_calls"]
        == store.get("m4_context_result_slots")
        == disposition["cumulative_tool_calls"]
        == 8
    )
    assert disposition["new_Messages_attempts"] == disposition["new_count_tokens_attempts"] == 4
    assert not disposition["candidate_ids"] and not disposition["nominees"]
    assert disposition["live_policy_timing_measured"] is False
    with store.connect() as db:
        charges = [dict(x) for x in db.execute("SELECT * FROM charges ORDER BY rowid")]
        artifacts = [dict(x) for x in db.execute("SELECT * FROM artifacts ORDER BY rowid")]
        assert db.execute("SELECT COUNT(*) FROM leases").fetchone()[0] == 0
    assert charges == disposition["budget"]["calls"]
    original_disposition = json.loads(
        (ORIGINAL / "live-episode/episode-disposition.json").read_text()
    )
    assert charges[:2] == original_disposition["budget"]["calls"]
    assert len(charges) == 6 and all(x["status"] == "settled" for x in charges)
    assert disposition["budget"]["uncertain_calls"] == 0
    assert (
        disposition["budget"]["ceiling_usd"] == "15"
        and disposition["budget"]["allowance_usd"] == "0"
    )
    for artifact in artifacts:
        store.read(artifact["hash"])
        assert artifact["scope"] in ("private", "development")
    preflight = json.loads((live / "dispatch-preflight/receipt.json").read_text())
    assert preflight["status"] == "current_model_and_rates_match_approved_contract"
    for filename, key in (
        ("model.json", "model_sha256"),
        ("model-overview.md", "pricing_sha256"),
        ("pricing.md", "full_context_pricing_sha256"),
    ):
        assert sha(live / "dispatch-preflight" / filename) == preflight[key]

    records = {cid: store.read(artifact, agent=True) for cid, artifact in state["registry"].items()}
    assert list(sorted(records)) == [f"candidate-{n}" for n in range(1, 7)]
    candidates = []
    for cid, record in sorted(records.items()):
        policy = validate(record["policy"])
        assert record["rule_hash"] == rule_hash(policy)
        assert record["observation_plan"] == observation_plan(policy)
        assert record["evaluation"] == replay(policy, evidence.rows)
        losses, stops, failures = independent_scores(policy, evidence.rows, record["evaluation"])
        assert record["cost_estimate"] == evidence.estimate(policy)
        assert record["work_estimate"] == evidence.work_estimate(policy)
        source, manifest = compile_programs(
            [{"arm": 20, "policy": policy, "force_continue": False}]
        )
        assert store.read(record["compiled_artifact"], agent=True) == {
            "source": source,
            "manifest": manifest,
        }
        unsupported = []
        for f in FILTERS:
            for cp in POINTS:
                mask = record["observation_plan"][f][str(cp)]
                allowed = evidence.bundle["shortlist_contract"]["supported_masks"][f][str(cp)]
                if mask not in allowed:
                    unsupported.append(
                        {
                            "filter": f,
                            "checkpoint": cp,
                            "needed_mask": mask,
                            "supported_masks": allowed,
                        }
                    )
        candidates.append(
            {
                "candidate_id": cid,
                "name": policy["name"],
                "rule_hash": record["rule_hash"],
                "policy_rules_sha256": digest(policy["rules"]),
                "record_artifact": state["registry"][cid],
                "compiled_artifact": record["compiled_artifact"],
                "quality_preserves_raw_native640": record["evaluation"][
                    "quality_preserves_raw_native640"
                ],
                "recall_losses": sum(losses.values()),
                "per_filter_losses": losses,
                "per_filter_stops": stops,
                "per_filter_quality": record["evaluation"]["per_filter"],
                "per_fold_quality": record["evaluation"]["per_exposed_development_fold"],
                "independent_failure_cases": failures,
                "scalar_stops": sum(stops[f] for f in FILTERS if f != "unfiltered"),
                "unfiltered_stops": stops["unfiltered"],
                "cost_status": record["cost_estimate"]["status"],
                "cost_support_failures": unsupported,
                "equal_scalar_vector_calls_proxy": record["work_estimate"]["equal_scalar_means"][
                    "vector_calls"
                ],
                "latency_measured": False,
            }
        )
    assert [r["recall_losses"] for r in candidates] == [8, 4, 1, 1, 1, 0]
    assert [r["candidate_id"] for r in candidates if r["quality_preserves_raw_native640"]] == [
        "candidate-6"
    ]
    assert candidates[-1]["scalar_stops"] == 41 and candidates[-1]["unfiltered_stops"] == 135
    assert candidates[-1]["cost_support_failures"] == [
        {
            "filter": "unfiltered",
            "checkpoint": 32,
            "needed_mask": 3,
            "supported_masks": [0, 8, 9, 11, 15],
        }
    ]
    decision = select_shortlist([{"candidate_id": cid, **r} for cid, r in records.items()])
    assert decision["candidate_ids"] == [] and decision["admissible_intervals"] == {}
    assert decision["exclusions"]["candidate-6"] == "uncertainty_estimate_unsupported"

    first = json.loads((DEST / "prepared/first-request.json").read_text())
    history = deepcopy(first["messages"])
    assert digest(history) == contract["prior_history_sha256"]
    request_rows, tool_rows = [], []
    new_spend = Decimal("0")
    candidate_offset = 0
    provider = live / "provider"
    assert sorted(p.name for p in provider.iterdir()) == [
        *(f"count-{n}" for n in range(3, 7)),
        *(f"message-{n}" for n in range(3, 7)),
    ]
    for ordinal in range(3, 7):
        count_dir, message_dir = provider / f"count-{ordinal}", provider / f"message-{ordinal}"
        request = json.loads((message_dir / "request.json").read_text())
        assert request == {**first, "messages": history}
        assert (message_dir / "request.json").read_bytes() == canonical(request)
        assert len(canonical(request)) + 8192 < CONTEXT["request_byte_bound"]
        assert store.read(digest(request)) == request
        count = json.loads((count_dir / "response.json").read_text())["input_tokens"]
        assert json.loads((count_dir / "request.json").read_text()) == count_payload(request)
        context_receipt = json.loads((count_dir / "context-receipt.json").read_text())
        assert context_receipt["ordinal"] == ordinal and context_receipt["request_hash"] == digest(
            request
        )
        assert context_receipt["input_tokens"] == count <= 900000
        assert context_receipt["estimated_context_total"] == count + 6000 < 1000000
        for folder, endpoint in (
            (count_dir, "/v1/messages/count_tokens"),
            (message_dir, "/v1/messages"),
        ):
            attempt = json.loads((folder / "attempt.json").read_text())
            http = json.loads((folder / "http.json").read_text())
            assert attempt["endpoint"] == "https://api.anthropic.com" + endpoint
            assert attempt["method"] == "POST" and attempt["automatic_retries"] is False
            assert attempt["request_sha256"] == sha(folder / "request.json")
            assert http["status"] == 200 and http["response_sha256"] == sha(
                folder / "response.json"
            )
        response = json.loads((message_dir / "response.json").read_text())
        usage = response["usage"]
        assert response["model"] == "claude-sonnet-5-5" and response["stop_reason"] == "tool_use"
        assert response["type"] == "message" and response["role"] == "assistant"
        assert usage["input_tokens"] == count and 0 <= usage["output_tokens"] <= 6000
        assert usage["service_tier"] == usage["speed"] == "standard"
        assert usage["inference_geo"] == "global"
        assert usage["cache_creation_input_tokens"] == usage["cache_read_input_tokens"] == 0
        charge = charges[ordinal - 1]
        metadata = json.loads(charge["metadata"])
        assert metadata["usage"] == usage and store.read(metadata["response_artifact"]) == response
        actual = (
            Decimal(usage["input_tokens"]) * 2 + Decimal(usage["output_tokens"]) * 10
        ) / 1000000
        assert actual == Decimal(charge["actual"]) / 1000000000
        assert Decimal(charge["reserved"]) / 1000000000 == Decimal("2.06")
        new_spend += actual
        feedback = []
        uses = [b for b in response["content"] if b["type"] == "tool_use"]
        outcome = disposition["outcomes"][ordinal - 3]
        assert len(uses) == len(outcome["tool_results"]) == 1
        for use, saved in zip(uses, outcome["tool_results"], strict=True):
            args = use["input"]
            if use["name"] == "evaluate_candidates":
                ids = []
                for policy in args["policies"]:
                    candidate_offset += 1
                    cid = f"candidate-{candidate_offset}"
                    assert records[cid]["policy"] == policy
                    ids.append(cid)
                value = {
                    "evaluations": [
                        {"candidate_id": cid, **candidate_feedback(records[cid])} for cid in ids
                    ],
                    "candidate_submissions_remaining": 9 - candidate_offset,
                }
            else:
                assert use["name"] == "explain_cases"
                try:
                    value = {
                        "cases": evidence.examples(args["category"], args["filter"], args["limit"])
                    }
                except ValueError as error:
                    value = {"error": str(error)[:400]}
            assert saved == {"tool_use_id": use["id"], "result": value}
            receipt = state["receipts"][use["id"]]
            assert (
                receipt["status"] == "complete"
                and store.read(receipt["artifact"], agent=True) == value
            )
            assert receipt["signature"] == digest({"operation": use["name"], "arguments": args})
            block = tool_block(use["id"], value)
            assert len(canonical(block)) < CONTEXT["tool_result_block_bytes"]
            feedback.append(block)
            tool_rows.append(
                {
                    "ordinal": ordinal,
                    "name": use["name"],
                    "arguments_sha256": digest(args),
                    "argument_summary": args
                    if use["name"] == "explain_cases"
                    else {"policies": len(args["policies"])},
                    "error": value.get("error"),
                    "result_bytes": len(canonical(block)),
                }
            )
        assistant = {"role": "assistant", "content": response["content"]}
        assert len(canonical(assistant)) < CONTEXT["assistant_message_bytes"]
        history.extend([assistant, {"role": "user", "content": feedback}])
        request_rows.append(
            {
                "ordinal": ordinal,
                "input_tokens": usage["input_tokens"],
                "counted_input_tokens": count,
                "output_tokens": usage["output_tokens"],
                "thinking_output_tokens": usage["output_tokens_details"]["thinking_tokens"],
                "actual_usd": str(actual),
                "request_bytes": len(canonical(request)),
                "request_sha256": sha(message_dir / "request.json"),
                "response_sha256": sha(message_dir / "response.json"),
            }
        )
    assert history == store.get("v2_messages") and candidate_offset == 6
    assert sha(provider / "message-3/request.json") == contract["first_request_sha256"]
    assert new_spend == Decimal("0.205510")
    total = sum(Decimal(row["actual"]) / 1000000000 for row in charges)
    assert total == Decimal(disposition["budget"]["committed_usd"]) == Decimal("0.244308") < 15
    assert tool_rows[1]["error"] == "bounded category/filter/limit required"
    assert sum(r["error"] is not None for r in tool_rows) == 1
    verify_package(package)
    verify_origin()
    live_hashes = {}
    for p in sorted(live.rglob("*")):
        if not p.is_file() or p.name.endswith("-shm"):
            continue
        if p.name.endswith("-wal") and p.stat().st_size == 0:
            continue
        live_hashes[str(p.relative_to(ROOT))] = sha(p)
    receipt = {
        "schema": "filtered-ann.M4-continuation-assessment.v1",
        "date": "2026-11-16",
        "status": "verified_six_request_episode_closed_one_zero_loss_policy_"
        "cost_unsupported_no_nominees",
        "execution_commit": "23ba475",
        "package_sha256": sha(package),
        "authorization_sha256": sha(DEST / "authorization.json"),
        "evidence_identity": evidence.identity,
        "scope": contract["scope"],
        "original_episode_unchanged": True,
        "amended_source_files_verified": len(frozen["source_sha256"]),
        "amended_preparation_artifacts_verified": len(frozen["artifact_sha256"]),
        "durable_artifacts_rehashed": len(artifacts),
        "new_Messages_requests": 4,
        "development_count_requests": 4,
        "total_Messages_requests": 6,
        "remaining_authorized_Messages_requests": 0,
        "new_spend_usd": str(new_spend),
        "total_spend_usd": str(total),
        "ceiling_usd": "15",
        "new_input_tokens": sum(r["input_tokens"] for r in request_rows),
        "new_output_tokens": sum(r["output_tokens"] for r in request_rows),
        "total_input_tokens": 17434 + sum(r["input_tokens"] for r in request_rows),
        "total_output_tokens": 393 + sum(r["output_tokens"] for r in request_rows),
        "all_count_estimates_equal_actual_input_usage": True,
        "thinking_blocks_preserved_unchanged": True,
        "retries": 0,
        "uncertain_calls": 0,
        "requests": request_rows,
        "new_tools": tool_rows,
        "cumulative_domain_tools": 8,
        "feedback_slots": 8,
        "candidate_submissions": 6,
        "independently_replayed_query_filter_cases": 18900,
        "zero_loss_candidates": ["candidate-6"],
        "candidates": candidates,
        "diagnostic_selection_only_not_model_submission": decision,
        "final_submission_received": False,
        "formal_M5_nominees": [],
        "last_batch_feedback_not_sent_to_model_due_to_request_limit": [
            "candidate-4",
            "candidate-5",
            "candidate-6",
        ],
        "SQL_searches": 0,
        "exact_search_calls": 0,
        "exact_truth_use": "Existing frozen offline recall labels only; no serving repair",
        "validation_test_outcomes_opened": False,
        "live_policy_timing_measured": False,
        "interpretation": "Context/transport qualification succeeded. The bounded discovery "
        "yielded one zero-loss development policy but no cost-supported eligible nominee or "
        "final submission. No speedup or protected/general robustness claim follows.",
        "next_step": "Retain this closed outcome; expose filter enums, cost-support and "
        "remaining quotas before any future episode. Qualifying candidate-6's missing "
        "observation-only path would need a prospective development-only protocol amendment.",
        "audit_source_sha256": sha(Path(__file__)),
        "live_artifacts_sha256": live_hashes,
    }
    output.mkdir()
    write(output / "receipt.json", receipt)
    freeze_path = STUDY / "freeze/m4-continuation-outcome-v1.json"
    assert not freeze_path.exists()
    write(
        freeze_path,
        {
            "schema": "filtered-ann.M4-continuation-outcome.v1",
            "date": "2026-11-16",
            "status": receipt["status"],
            "receipt_workspace_path": str((output / "receipt.json").relative_to(ROOT)),
            "receipt_sha256": sha(output / "receipt.json"),
            "package_sha256": sha(package),
            "total_Messages_requests": 6,
            "total_spend_usd": str(total),
            "zero_loss_candidates": ["candidate-6"],
            "formal_M5_nominees": [],
            "validation_test_outcomes_opened": False,
        },
    )
    copies = HERE / "receipts"
    copies.mkdir(exist_ok=False)
    for path in (output / "receipt.json", freeze_path, DEST / "authorization.json"):
        shutil.copyfile(path, copies / path.name)
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "new_Messages_requests",
                    "development_count_requests",
                    "total_Messages_requests",
                    "new_spend_usd",
                    "total_spend_usd",
                    "candidate_submissions",
                    "zero_loss_candidates",
                    "formal_M5_nominees",
                    "validation_test_outcomes_opened",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    audit()
