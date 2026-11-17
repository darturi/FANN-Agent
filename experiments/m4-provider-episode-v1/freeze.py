"""Seal the prepared M4 proposal once, without authorizing or sending it."""

import importlib.metadata
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from decimal import Decimal

from episode import BOUND, DEST, HERE, ROOT, STUDY, Evidence, canonical, sha, write
from transport import ApprovalRequired, load_approval, verify_sources


def freeze():
    package = DEST / "package-freeze.json"
    assert not package.exists(), "preserve the completed package; version any amendment"
    assert not (DEST / "authorization.json").exists()
    assert not (DEST / "live-episode").exists()
    prepared = DEST / "prepared"
    contract = json.loads((prepared / "episode-contract.json").read_text())
    assert contract["provider_authorized"] is False and contract["paid_requests"] == 0
    assert contract["scope"] == {
        "development_groups": 450,
        "scalar_filters": 6,
        "unfiltered": True,
        "exact_scoring_only": True,
        "validation_test_outcomes_opened": False,
    }
    for name, digest_ in contract["files_sha256"].items():
        assert sha(prepared / name) == digest_, name
    request_bytes = (prepared / "first-request.json").read_bytes()
    assert canonical(json.loads(request_bytes)) == request_bytes
    assert len(request_bytes) == contract["first_request_bytes"] == 14472
    assert sha(prepared / "first-request.json") == contract["first_request_sha256"]
    assert json.loads(request_bytes) == json.loads(
        (prepared / "first-request.preview.json").read_text()
    )
    evidence = Evidence(json.loads((BOUND / "bound-evidence.json").read_text()))
    assert evidence.identity == contract["evidence_identity"]
    assert sha(BOUND / "bound-evidence.json") == contract["evidence_file_sha256"]
    assert len(evidence.rows) == 3150
    assert set(evidence.summary()["per_filter"]) == {
        "unfiltered", "votes743", "votes527", "votes310", "votes192", "votes108", "votes32"
    }
    limits = contract["limits"]
    assert Decimal(limits["maximum_reserved_usd_per_request"]) * 6 == Decimal("12.36")
    assert Decimal(limits["six_maximal_requests_usd"]) <= Decimal(limits["ceiling_usd"]) == 15
    assert limits["allowance_usd"] == "0" and not limits["automatic_retries"]
    provider = json.loads((DEST / "provider/preflight.json").read_text())
    assert sha(DEST / "provider/preflight.json") == contract["provider_preflight_sha256"]
    assert provider["paid_Messages_requests"] == provider["development_payloads_sent"] == 0
    assert provider["authenticated_model_GETs"] == 1
    model = json.loads((DEST / "provider/model-api-response.json").read_text())
    assert sha(DEST / "provider/model-api-response.json") == provider["model_response_sha256"]
    assert model["id"] == contract["model"] and model["lifecycle"] == "active"
    assert model["max_input_tokens"] == limits["billing_input_token_bound"] == 1000000
    for name, record in provider["official_documents"].items():
        assert sha(DEST / "provider" / (name + ".md")) == record["sha256"]
    rehearsal = json.loads((DEST / "no-network-rehearsal/receipt.json").read_text())
    assert rehearsal["status"].startswith("passed_no_network_real_evidence")
    assert rehearsal["first_real_request_sha256"] == contract["first_request_sha256"]
    assert rehearsal["evidence_identity"] == evidence.identity
    assert rehearsal["pending_real_approval_blocks_transport_and_reservation"]
    assert rehearsal["real_runner_blocks_before_credentials_or_live_state"]
    assert rehearsal["progress_blocks_preserved_unchanged"]
    assert rehearsal["provider_generation_requests"] == 0
    suite = ET.parse(DEST / "local-tests.xml").getroot().find("testsuite")
    assert suite is not None and int(suite.attrib["tests"]) == 85
    assert all(int(suite.attrib[k]) == 0 for k in ("errors", "failures", "skipped"))

    predecessor = DEST / "predecessor-source"
    predecessor.mkdir(exist_ok=True)
    assert not (predecessor / "controller.py").exists()
    assert not (predecessor / "receipt.json").exists()
    relative = "experiments/filtered-ann-protocol-v2/fannproto/controller.py"
    original = subprocess.check_output(
        ["git", "show", "9e8518a:" + relative], cwd=ROOT / "agent"
    )
    snapshot = predecessor / "fannproto/controller.py"
    if snapshot.exists():
        assert snapshot.read_bytes() == original
    (predecessor / "controller.py").write_bytes(original)
    base = subprocess.check_output(
        ["git", "rev-parse", "9e8518a"], cwd=ROOT / "agent", text=True
    ).strip()
    write(
        predecessor / "receipt.json",
        {
            "base_commit": base,
            "source_path": "agent/" + relative,
            "original_sha256": sha(predecessor / "controller.py"),
            "active_sha256": sha(ROOT / "agent" / relative),
            "change": "Separate operational byte guard from full-context financial reservation; "
            "preserve signed thinking/progress blocks unchanged in Messages history.",
            "research_contract_changed": False,
        },
    )
    write(
        DEST / "dependency-versions.json",
        {
            name: importlib.metadata.version(name)
            for name in ("fannagent", "mini-swe-agent", "pydantic", "certifi", "pytest", "ruff")
        },
    )
    sources = set(HERE.glob("*.py")) | set(HERE.glob("*.md")) | set(HERE.glob("tests/*.py"))
    sources.update((HERE.parent / "filtered-ann-protocol-v2/fannproto").glob("*.py"))
    sources.update((HERE.parent / "filtered-ann-protocol-v2/tests").glob("*.py"))
    sources.update(ROOT / "agent/src/fannagent" / f for f in ("budget.py", "config.py", "store.py"))
    sources.add(ROOT / "agent/pyproject.toml")
    artifacts = set(prepared.iterdir())
    for folder in (
        "provider", "no-network-rehearsal", "predecessor-source", "freeze-preflight-rejected"
    ):
        artifacts.update(p for p in (DEST / folder).rglob("*") if p.is_file())
    artifacts.update(
        DEST / f
        for f in (
            "local-tests.xml",
            "local-tests.log",
            "rehearsal.log",
            "preparation-compact.log",
            "dependency-versions.json",
        )
    )
    artifacts.update(
        (
            BOUND / "bound-evidence.json",
            BOUND / "binding-receipt-v2.json",
            BOUND / "M3-bound-v2/receipt.json",
            BOUND / "primer.md",
            STUDY / "freeze/uncertainty-shortlist-v1.json",
            STUDY / "reports/protocol-v2-gates-after-uncertainty-shortlist-v1.json",
        )
    )
    write(
        package,
        {
            "schema": "filtered-ann.M4-package-freeze.v1",
            "date": "2026-11-16",
            "status": "frozen_proposal_pending_explicit_user_approval",
            "base_commit": base,
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)},
            "artifact_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sorted(artifacts)},
            "paid_requests": 0,
            "authorization_created": False,
            "validation_test_outcomes_opened": False,
        },
    )
    verify_sources(package)
    try:
        load_approval(DEST / "authorization.json", prepared, package)
    except ApprovalRequired:
        pass
    else:
        raise AssertionError("missing approval must block")
    receipt = {
        "schema": "filtered-ann.M4-preparation-outcome.v1",
        "date": "2026-11-16",
        "status": "frozen_qualified_proposal_awaiting_explicit_user_approval",
        "package_workspace_path": str(package.relative_to(ROOT)),
        "package_sha256": sha(package),
        "episode_contract_sha256": sha(prepared / "episode-contract.json"),
        "first_request_bytes": len(request_bytes),
        "first_request_sha256": contract["first_request_sha256"],
        "evidence_identity": evidence.identity,
        "local_tests_passed": 85,
        "bound_no_network_rehearsal": rehearsal["status"],
        "maximum_requests": 6,
        "hard_ceiling_usd": "15",
        "maximum_six_reservations_usd": "12.36",
        "provider_model": contract["model"],
        "input_output_usd_per_million": ["2", "10"],
        "authenticated_model_GETs": 1,
        "paid_generation_requests": 0,
        "actual_generation_spend_usd": "0",
        "development_payloads_sent": 0,
        "provider_authorized": False,
        "authorization_file_exists": False,
        "scope": contract["scope"],
        "next_step": "Explicit user approval of the exact frozen packet before Messages dispatch",
    }
    outcome = STUDY / "freeze/m4-episode-v1-proposal.json"
    assert not outcome.exists()
    write(outcome, receipt)
    write(DEST / "preparation-receipt.json", receipt)
    copies = HERE / "receipts"
    copies.mkdir(exist_ok=False)
    for path in (
        package,
        outcome,
        DEST / "preparation-receipt.json",
        prepared / "episode-contract.json",
        prepared / "execution-contract.json",
        prepared / "approval-specification.json",
        DEST / "provider/preflight.json",
        DEST / "provider/model-api-response.json",
        DEST / "no-network-rehearsal/receipt.json",
        DEST / "local-tests.xml",
        DEST / "dependency-versions.json",
    ):
        name = (
            "no-network-rehearsal.json"
            if path.parent.name == "no-network-rehearsal"
            else path.name
        )
        shutil.copyfile(path, copies / name)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    freeze()
