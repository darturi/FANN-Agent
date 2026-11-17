"""Read-only independent audit of the completed frozen M4 episode."""

import json
import shutil
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "m4-provider-episode-v1"))

from episode import DEST, ROOT, STUDY, Evidence, canonical, digest, sha, write  # noqa: E402
from transport import load_approval, verify_sources  # noqa: E402

from fannagent.store import ReadOnlyStore  # noqa: E402


def audit():
    output = DEST / "assessment-v1"
    assert not output.exists(), "preserve completed audit; version amendments"
    live = DEST / "live-episode"
    prepared = DEST / "prepared"
    package = DEST / "package-freeze.json"
    frozen = verify_sources(package)
    approval = load_approval(DEST / "authorization.json", prepared, package)
    contract = json.loads((prepared / "episode-contract.json").read_text())
    disposition = json.loads((live / "episode-disposition.json").read_text())
    store = ReadOnlyStore(live / "campaign")
    state = store.get("v2_state")
    assert (
        state["terminal"] == disposition["status"] == "bounded_M4_abstention_local_contract_limit"
    )
    assert state["tool_calls"] == disposition["tool_calls"] == 4
    assert state["candidate_submissions"] == disposition["candidate_submissions"] == 0
    assert (
        not state["registry"] and not disposition["candidate_ids"] and not disposition["nominees"]
    )
    assert store.get("v2_round_pending") is None
    with store.connect() as db:
        charges = [dict(row) for row in db.execute("SELECT * FROM charges ORDER BY rowid")]
        artifacts = [dict(row) for row in db.execute("SELECT * FROM artifacts ORDER BY rowid")]
        assert db.execute("SELECT COUNT(*) FROM leases").fetchone()[0] == 0
    assert charges == disposition["budget"]["calls"]
    assert len(charges) == 2 and all(c["status"] == "settled" for c in charges)
    assert disposition["budget"]["uncertain_calls"] == 0
    assert disposition["budget"]["ceiling_usd"] == "15"
    assert disposition["budget"]["allowance_usd"] == "0"
    assert len(artifacts) == 10
    for artifact in artifacts:
        # ReadOnlyStore revalidates each content hash, size, type and scope.
        store.read(artifact["hash"])
        assert artifact["scope"] in {"private", "development"}
    preflight = json.loads((live / "dispatch-preflight/receipt.json").read_text())
    assert preflight["status"] == "current_model_and_rates_match_approved_contract"
    assert preflight["paid_requests"] == 0
    for file, key in (
        ("model.json", "model_sha256"),
        ("model-overview.md", "pricing_sha256"),
        ("pricing.md", "full_context_pricing_sha256"),
    ):
        assert sha(live / "dispatch-preflight" / file) == preflight[key]
    evidence = Evidence(json.loads((ROOT / contract["evidence_workspace_path"]).read_text()))
    assert evidence.identity == contract["evidence_identity"] == approval["evidence_hash"]
    assert len(evidence.rows) == 3150
    expected_filters = {
        "unfiltered",
        "votes743",
        "votes527",
        "votes310",
        "votes192",
        "votes108",
        "votes32",
    }
    assert set(evidence.summary()["per_filter"]) == expected_filters
    initial = json.loads((prepared / "first-request.json").read_text())
    assert (
        set(json.loads(initial["messages"][0]["content"])["development_summary"]["per_filter"])
        == expected_filters
    )
    history = deepcopy(initial["messages"])
    paths = sorted((live / "provider").glob("request-*"))
    assert [p.name for p in paths] == ["request-1", "request-2"]
    rows, tools, feedback_sizes = [], [], []
    spent = Decimal("0")
    for number, (folder, charge) in enumerate(zip(paths, charges, strict=True), 1):
        request = json.loads((folder / "request.json").read_text())
        assert request == {**initial, "messages": history}
        assert (folder / "request.json").read_bytes() == canonical(request)
        assert len(canonical(request)) + 8192 <= 50000
        assert store.read(digest(request)) == request
        attempt = json.loads((folder / "attempt.json").read_text())
        assert attempt["request_sha256"] == sha(folder / "request.json")
        assert attempt["endpoint"] == approval["endpoint"] and attempt["method"] == "POST"
        assert attempt["automatic_retries"] is False
        http = json.loads((folder / "http.json").read_text())
        assert http["status"] == 200 and http["response_sha256"] == sha(folder / "response.json")
        response = json.loads((folder / "response.json").read_text())
        assert response["type"] == "message" and response["role"] == "assistant"
        assert response["model"] == contract["model"] and response["stop_reason"] == "tool_use"
        usage = response["usage"]
        assert usage["service_tier"] == usage["speed"] == "standard"
        assert usage["inference_geo"] == "global"
        assert usage["cache_creation_input_tokens"] == usage["cache_read_input_tokens"] == 0
        assert 0 <= usage["input_tokens"] <= 1000000 and 0 <= usage["output_tokens"] <= 6000
        metadata = json.loads(charge["metadata"])
        assert metadata["usage"] == usage
        assert store.read(metadata["response_artifact"]) == response
        assert metadata["response_artifact"] == digest(response)
        actual = (
            Decimal(usage["input_tokens"]) * 2 + Decimal(usage["output_tokens"]) * 10
        ) / 1000000
        assert actual == Decimal(charge["actual"]) / 1000000000
        assert Decimal(charge["reserved"]) / 1000000000 == Decimal("2.06")
        spent += actual
        uses = [b for b in response["content"] if b["type"] == "tool_use"]
        outcome = disposition["outcomes"][number - 1]
        assert len(uses) == len(outcome["tool_results"])
        feedback = []
        for use, result in zip(uses, outcome["tool_results"], strict=True):
            assert use["id"] == result["tool_use_id"]
            args = use["input"]
            if use["name"] == "inspect_workload":
                assert args == {}
                expected = evidence.summary()
                expected["prefix_opportunity"] = deepcopy(
                    evidence.bundle["development_prefix_summary"]
                )
            else:
                assert use["name"] == "explain_cases" and 1 <= args["limit"] <= 12
                assert args["filter"] in expected_filters
                expected = {
                    "cases": evidence.examples(args["category"], args["filter"], args["limit"])
                }
            assert result["result"] == expected
            receipt = state["receipts"][use["id"]]
            assert receipt["status"] == "complete"
            assert receipt["signature"] == digest({"operation": use["name"], "arguments": args})
            assert store.read(receipt["artifact"], agent=True) == expected
            block = {
                "type": "tool_result",
                "tool_use_id": use["id"],
                "content": canonical(expected).decode(),
                "is_error": False,
            }
            feedback.append(block)
            tools.append(
                {"name": use["name"], "arguments": args, "cases": len(expected.get("cases", []))}
            )
            feedback_sizes.append(
                {
                    "after_request": number,
                    "name": use["name"],
                    "tool_result_block_bytes": len(canonical(block)),
                }
            )
        history.extend(
            [
                {"role": "assistant", "content": response["content"]},
                {"role": "user", "content": feedback},
            ]
        )
        rows.append(
            {
                "ordinal": number,
                "request_bytes": len(canonical(request)),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "thinking_output_tokens": usage["output_tokens_details"]["thinking_tokens"],
                "actual_usd": str(actual),
                "http_status": 200,
                "request_sha256": sha(folder / "request.json"),
                "response_sha256": sha(folder / "response.json"),
            }
        )
    assert history == store.get("v2_messages")
    assert spent == Decimal(disposition["budget"]["committed_usd"]) == Decimal("0.038798")
    assert sha(paths[0] / "request.json") == contract["first_request_sha256"]
    blocked_bytes = len(canonical({**initial, "messages": history}))
    assert blocked_bytes == 42382 and blocked_bytes + 8192 - 50000 == 574
    stop = json.loads((live / "local-stop.json").read_text())
    assert stop == {
        "no_automatic_retry": True,
        "reason": "request bytes exceed conservative input bound",
    }
    assert len(state["receipts"]) == len(tools) == 4
    live_inventory = {
        str(p.relative_to(ROOT)): sha(p) for p in sorted(live.rglob("*")) if p.is_file()
    }
    receipt = {
        "schema": "filtered-ann.M4-episode-assessment.v1",
        "date": "2026-11-16",
        "status": "verified_terminal_host_payload_limit_abstention_no_policy_candidates",
        "execution_commit": "ee1ad72",
        "package_sha256": sha(package),
        "authorization_sha256": sha(DEST / "authorization.json"),
        "evidence_identity": evidence.identity,
        "frozen_source_files_verified": len(frozen["source_sha256"]),
        "frozen_artifact_files_verified": len(frozen["artifact_sha256"]),
        "actual_bound_feedback_recomputed": True,
        "requests": rows,
        "request_count": len(rows),
        "maximum_requests": 6,
        "input_tokens_total": sum(r["input_tokens"] for r in rows),
        "output_tokens_total": sum(r["output_tokens"] for r in rows),
        "actual_spend_usd": str(spent),
        "ceiling_usd": "15",
        "uncertain_calls": 0,
        "retries": 0,
        "new_generation_provider_metadata_GETs": 1,
        "tools": tools,
        "tool_result_sizes": feedback_sizes,
        "domain_tool_count": 4,
        "candidate_submissions": 0,
        "M5_nominees": 0,
        "next_unsent_request_bytes": blocked_bytes,
        "reserved_headroom_bytes": 8192,
        "operational_limit_bytes": 50000,
        "excess_bytes": 574,
        "next_request_reserved_or_sent": False,
        "locally_prepared_case_feedback_not_sent": 18,
        "data_sent": "Frozen compact initial payload and aggregate inspect_workload feedback; "
        "the 18 locally prepared case examples never reached a third request.",
        "scope": contract["scope"],
        "SQL_searches": 0,
        "exact_search_calls": 0,
        "exact_truth_use": "Existing offline development recall labels only; no serving repair",
        "validation_test_outcomes_opened": False,
        "live_policy_timing_measured": False,
        "interpretation": "Host operational payload capacity failed on a valid permitted tool "
        "sequence. This episode provides no evidence of agent policy quality or robustness.",
        "runner_generic_M5_next_step_is_eligible": False,
        "next_step": "Amend and locally qualify context/feedback capacity before a separately "
        "approved continuation; retain these two requests and spend in any cumulative cap.",
        "audit_source_sha256": sha(Path(__file__)),
        "live_artifacts_sha256": live_inventory,
    }
    output.mkdir()
    write(output / "receipt.json", receipt)
    freeze_path = STUDY / "freeze/m4-episode-v1-outcome.json"
    assert not freeze_path.exists()
    write(
        freeze_path,
        {
            "schema": "filtered-ann.M4-outcome-freeze.v1",
            "date": "2026-11-16",
            "status": receipt["status"],
            "receipt_workspace_path": str((output / "receipt.json").relative_to(ROOT)),
            "receipt_sha256": sha(output / "receipt.json"),
            "package_sha256": sha(package),
            "terminal": state["terminal"],
            "actual_spend_usd": str(spent),
            "requests": 2,
            "nominees": 0,
            "validation_test_outcomes_opened": False,
        },
    )
    copies = HERE / "receipts"
    copies.mkdir(exist_ok=False)
    for path in (
        output / "receipt.json",
        freeze_path,
        DEST / "authorization.json",
        live / "local-stop.json",
    ):
        shutil.copyfile(path, copies / path.name)
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "request_count",
                    "actual_spend_usd",
                    "candidate_submissions",
                    "M5_nominees",
                    "next_unsent_request_bytes",
                    "excess_bytes",
                    "validation_test_outcomes_opened",
                    "next_step",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    audit()
