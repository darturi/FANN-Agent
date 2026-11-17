"""Seal the qualified context amendment, preserving the terminal episode and debt."""

import json
import shutil
import xml.etree.ElementTree as ET

from common import (
    CONTEXT,
    DEST,
    HERE,
    ORIGINAL,
    ROOT,
    STUDY,
    ApprovalRequired,
    ReadOnlyStore,
    canonical,
    check_request,
    digest,
    load_approval,
    request_for,
    sha,
    verify_origin,
    verify_package,
    write,
)


def freeze():
    package = DEST / "package-freeze.json"
    assert not package.exists(), "preserve a completed freeze; version amendments"
    assert not (DEST / "authorization.json").exists()
    assert not (DEST / "live-continuation").exists()
    assessment = verify_origin()
    prepared = DEST / "prepared"
    contract = json.loads((prepared / "continuation-contract.json").read_text())
    assert contract["context"] == CONTEXT
    assert contract["new_paid_requests"] == contract["new_count_requests"] == 0
    assert contract["provider_authorized"] is False
    request = request_for()
    check_request(request)
    assert canonical(request) == (prepared / "first-request.json").read_bytes()
    assert request == json.loads((prepared / "first-request.preview.json").read_text())
    assert sha(prepared / "first-request.json") == contract["first_request_sha256"]
    assert len(canonical(request)) == contract["first_request_bytes"] == 42382
    origin = ReadOnlyStore(prepared / "origin-campaign")
    assert origin.get("v2_messages") == request["messages"]
    assert digest(request["messages"]) == contract["prior_history_sha256"]
    assert origin.get("v2_state")["terminal"] == contract["original_terminal"]
    initial = json.loads((ORIGINAL / "prepared/first-request.json").read_text())
    assert {k: v for k, v in initial.items() if k != "messages"} == {
        k: v for k, v in request.items() if k != "messages"
    }
    assert assessment["request_count"] == 2 and assessment["actual_spend_usd"] == "0.038798"
    qualifier = json.loads((DEST / "qualification-v1/receipt.json").read_text())
    extremes = json.loads((DEST / "feedback-extremes-v1/receipt.json").read_text())
    assert qualifier["status"].startswith("passed_actual_bound")
    assert extremes["status"].startswith("passed_all_filter")
    assert qualifier["resumed_exact_first_request_sha256"] == contract["first_request_sha256"]
    assert qualifier["all_category_filter_combinations"] == 49
    assert qualifier["structural_wire_bound_including_headroom_bytes"] == 5818766
    assert qualifier["new_paid_requests"] == qualifier["new_count_requests"] == 0
    assert extremes["counterexamples_per_candidate"] == 21
    assert extremes["maximum_tool_result_bytes"] == 84561 < CONTEXT["tool_result_block_bytes"]
    suite = ET.parse(DEST / "local-tests.xml").getroot().find("testsuite")
    assert suite is not None and int(suite.attrib["tests"]) == 106
    assert all(int(suite.attrib[k]) == 0 for k in ("failures", "errors", "skipped"))
    synthetic = json.loads((DEST / "synthetic-count-endpoint-check/receipt.json").read_text())
    assert synthetic["status"].startswith("verified_free_count_endpoint")
    assert synthetic["study_data_sent"] is False and synthetic["Messages_requests"] == 0
    assert synthetic["source_sha256"] == sha(HERE / "check_count_endpoint.py")
    for filename, key in (("request.json", "request_sha256"), ("response.json", "response_sha256")):
        assert sha(DEST / "synthetic-count-endpoint-check" / filename) == synthetic[key]
    docs = json.loads((DEST / "official-docs/receipt.json").read_text())
    for name, record in docs["documents"].items():
        assert sha(DEST / "official-docs" / (name + ".md")) == record["sha256"]
    try:
        load_approval(DEST / "authorization.json")
    except ApprovalRequired:
        pass
    else:
        raise AssertionError("missing approval must block")
    sources = set(HERE.glob("*.py")) | set(HERE.glob("*.md")) | set(HERE.glob("tests/*.py"))
    artifacts = set()
    for folder in (
        "prepared",
        "official-docs",
        "synthetic-count-endpoint-check",
        "qualification-v1",
        "feedback-extremes-v1",
    ):
        for path in (DEST / folder).rglob("*"):
            if not path.is_file() or path.name.endswith("-shm"):
                continue
            if path.name.endswith("-wal"):
                assert path.stat().st_size == 0, "checkpoint data before freezing"
                continue
            artifacts.add(path)
    artifacts.update(p for p in DEST.glob("*.log") if p.name != "freeze.log")
    artifacts.add(DEST / "local-tests.xml")
    artifacts.update(
        (
            ORIGINAL / "package-freeze.json",
            ORIGINAL / "authorization.json",
            ORIGINAL / "assessment-v1/receipt.json",
            ORIGINAL / "prepared/model-config.json",
            ORIGINAL / "prepared/episode-contract.json",
            ORIGINAL / "prepared/first-request.json",
        )
    )
    write(
        package,
        {
            "schema": "filtered-ann.M4-context-package.v1",
            "date": "2026-11-16",
            "status": "qualified_frozen_amendment_pending_explicit_approval",
            "original_execution_commit": "ee1ad72",
            "original_outcome_commit": "b09dba0",
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)},
            "artifact_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sorted(artifacts)},
            "sqlite_ephemeral_exclusions": "SHM synchronization files and asserted-empty WALs; "
            "all database and content bytes are pinned",
            "new_paid_requests": 0,
            "development_count_requests": 0,
            "synthetic_free_count_requests": 1,
            "validation_test_outcomes_opened": False,
        },
    )
    verify_package(package)
    receipt = {
        "schema": "filtered-ann.M4-context-amendment-outcome.v1",
        "date": "2026-11-16",
        "status": "qualified_frozen_continuation_awaiting_explicit_amendment_approval",
        "package_workspace_path": str(package.relative_to(ROOT)),
        "package_sha256": sha(package),
        "contract_sha256": sha(prepared / "continuation-contract.json"),
        "first_request_sha256": contract["first_request_sha256"],
        "first_request_bytes": 42382,
        "evidence_identity": contract["evidence_identity"],
        "scope": contract["scope"],
        "original_episode_unchanged": True,
        "prior_requests": 2,
        "prior_spend_usd": "0.038798",
        "remaining_Messages_requests": 4,
        "maximum_development_count_requests": 4,
        "cumulative_request_cap": 6,
        "ceiling_usd": "15",
        "context": CONTEXT,
        "local_tests_passed": 106,
        "full_four_round_request_bytes": qualifier["full_four_round_request_bytes"],
        "structural_wire_bound_with_headroom_bytes": 5818766,
        "maximum_actual_tool_result_stress_bytes": 84561,
        "synthetic_free_count_endpoint_verified": True,
        "synthetic_free_count_requests": 1,
        "new_paid_requests": 0,
        "development_count_requests": 0,
        "new_paid_spend_usd": "0",
        "provider_authorized": False,
        "authorization_file_exists": False,
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
        "next_step": "Explicit approval of exact amended context contract and four free "
        "data-count checks before four remaining paid requests",
    }
    write(DEST / "preparation-receipt.json", receipt)
    freeze_path = STUDY / "freeze/m4-context-amendment-v1.json"
    assert not freeze_path.exists()
    write(freeze_path, receipt)
    copies = HERE / "receipts"
    copies.mkdir(exist_ok=False)
    shutil.copytree(prepared, copies / "prepared", ignore=shutil.ignore_patterns("origin-campaign"))
    for path, name in (
        (package, "package-freeze.json"),
        (DEST / "preparation-receipt.json", "preparation-receipt.json"),
        (DEST / "qualification-v1/receipt.json", "qualification.json"),
        (DEST / "feedback-extremes-v1/receipt.json", "feedback-extremes.json"),
        (DEST / "synthetic-count-endpoint-check/receipt.json", "synthetic-count-endpoint.json"),
        (DEST / "synthetic-count-endpoint-check/request.json", "synthetic-count-request.json"),
        (DEST / "official-docs/receipt.json", "official-documents.json"),
        (DEST / "local-tests.xml", "local-tests.xml"),
    ):
        shutil.copyfile(path, copies / name)
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "package_sha256",
                    "first_request_sha256",
                    "local_tests_passed",
                    "remaining_Messages_requests",
                    "cumulative_request_cap",
                    "new_paid_requests",
                    "development_count_requests",
                    "next_step",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    freeze()
