"""Seal the local reconfiguration and bind the user's explicit budget amendment."""

import datetime
import json
import shutil
import xml.etree.ElementTree as ET

from support import (
    CONFIG,
    DEST,
    HERE,
    PRIOR,
    ROOT,
    STUDY,
    load_authorization,
    sha,
    verify_origin,
    verify_package,
    write,
)


def freeze():
    package = DEST / "package-freeze.json"
    assert not package.exists() and not (DEST / "live-dollar-continuation").exists()
    original = verify_origin()
    contract = json.loads((DEST / "prepared/contract.json").read_text())
    assert contract["config"] == CONFIG
    assert CONFIG["max_requests"] is CONFIG["max_count_requests"] is None
    assert contract["prior_spend_usd"] == original["total_spend_usd"] == "0.244308"
    assert contract["remaining_USD"] == "14.755692"
    qualifier = json.loads((DEST / "qualification-v1/receipt.json").read_text())
    assert qualifier["status"].startswith("passed_actual_bound_dollar")
    assert qualifier["scripted_total_requests"] == 8 and qualifier["closing_tool_only"]
    assert qualifier["new_paid_requests"] == qualifier["new_count_requests"] == 0
    suite = ET.parse(DEST / "local-tests.xml").getroot().find("testsuite")
    assert suite is not None and int(suite.attrib["tests"]) == 115
    assert all(int(suite.attrib[k]) == 0 for k in ("failures", "errors", "skipped"))
    sources = set(HERE.glob("*.py")) | set(HERE.glob("*.md")) | set(HERE.glob("tests/*.py"))
    artifacts = set()
    for folder in ("prepared", "qualification-v1"):
        for path in (DEST / folder).rglob("*"):
            if not path.is_file() or path.name.endswith("-shm"):
                continue
            if path.name.endswith("-wal"):
                assert path.stat().st_size == 0
                continue
            artifacts.add(path)
    artifacts.update(p for p in DEST.glob("*.log") if p.name != "freeze.log")
    artifacts.add(DEST / "local-tests.xml")
    artifacts.update((PRIOR / "package-freeze.json", PRIOR / "assessment-v1/receipt.json"))
    write(
        package,
        {
            "schema": "filtered-ann.M4-dollar-package.v1",
            "date": "2026-11-16",
            "status": "configured_qualified_dollar_ceiling_no_new_inference",
            "prior_outcome_commit": "b298712",
            "max_requests": None,
            "ceiling_usd": "15",
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)},
            "artifact_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sorted(artifacts)},
            "new_paid_requests": 0,
            "new_count_requests": 0,
            "validation_test_outcomes_opened": False,
        },
    )
    verify_package()
    authorization = {
        "status": "authorized",
        "model": "claude-sonnet-5-5",
        "spending_policy": "dollar_ceiling",
        "max_requests": None,
        "max_count_requests": None,
        "max_output_tokens": 6000,
        "ceiling_usd": "15",
        "prior_spend_usd": "0.244308",
        "evidence_hash": contract["evidence_identity"],
        "contract_sha256": sha(DEST / "prepared/contract.json"),
        "package_sha256": sha(package),
        "recorded_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "user_approval_record": "Reconfigure to $15 cap, clearly the request cap "
        "is far too conservative",
        "inherited_provider_permission": "Existing explicit Anthropic claude-sonnet-5-5 "
        "Messages/token-count authorization and development-only data scope; latest instruction "
        "removes the request-count allowances while retaining the cumulative dollar cap.",
        "prior_provider_authorization_sha256": sha(PRIOR / "authorization.json"),
        "configuration_only_no_inference_invoked": True,
    }
    path = DEST / "authorization.json"
    assert not path.exists()
    write(path, authorization)
    load_authorization(path)
    receipt = {
        "schema": "filtered-ann.M4-dollar-configuration.v1",
        "date": "2026-11-16",
        "status": "configured_qualified_dollar_cap_no_request_ceiling_no_new_inference",
        "package_workspace_path": str(package.relative_to(ROOT)),
        "package_sha256": sha(package),
        "authorization_sha256": sha(path),
        "config": CONFIG,
        "evidence_identity": contract["evidence_identity"],
        "scope": contract["scope"],
        "prior_requests_retained": 6,
        "prior_candidates_retained": 6,
        "prior_spend_usd": "0.244308",
        "remaining_USD": "14.755692",
        "max_requests": None,
        "ceiling_usd": "15",
        "local_tests_passed": 115,
        "actual_bound_seventh_and_eighth_call_rehearsal_passed": True,
        "sixteen_round_controller_and_transport_checks_passed": True,
        "closing_reservation_and_final_tool_passed": True,
        "original_outcome_unchanged": True,
        "new_paid_requests": 0,
        "new_count_requests": 0,
        "SQL_searches": 0,
        "validation_test_outcomes_opened": False,
    }
    write(DEST / "configuration-receipt.json", receipt)
    target = STUDY / "freeze/m4-dollar-budget-v1.json"
    assert not target.exists()
    write(target, receipt)
    copies = HERE / "receipts"
    copies.mkdir(exist_ok=False)
    shutil.copytree(
        DEST / "prepared", copies / "prepared", ignore=shutil.ignore_patterns("origin-campaign")
    )
    for source, name in (
        (package, "package-freeze.json"),
        (path, "authorization.json"),
        (DEST / "configuration-receipt.json", "configuration-receipt.json"),
        (DEST / "qualification-v1/receipt.json", "qualification.json"),
        (DEST / "local-tests.xml", "local-tests.xml"),
    ):
        shutil.copyfile(source, copies / name)
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "package_sha256",
                    "prior_spend_usd",
                    "remaining_USD",
                    "max_requests",
                    "ceiling_usd",
                    "local_tests_passed",
                    "new_paid_requests",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    freeze()
