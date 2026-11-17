"""Prepare/seal the requested allowance change, without dispatching inference."""

import argparse
import datetime
import json
import shutil
import xml.etree.ElementTree as ET
from types import SimpleNamespace

from exploration_support import (
    CONFIG,
    DEST,
    HERE,
    PRIOR,
    PRIOR_SPEND,
    ROOT,
    STUDY,
    Evidence,
    ModelConfig,
    canonical,
    digest,
    load_authorization,
    notice,
    prompt_hash,
    sha,
    template,
    verify_origin,
    verify_package,
    write,
)

from fannagent.budget import Budget
from fannagent.store import ReadOnlyStore


def prepare():
    original = verify_origin()
    prepared = DEST / "prepared"
    prepared.mkdir(parents=True, exist_ok=False)
    shutil.copytree(PRIOR / "live-dollar-continuation/campaign", prepared / "origin-campaign")
    origin = ReadOnlyStore(prepared / "origin-campaign")
    request = json.loads((PRIOR / "prepared/research-template.json").read_text())
    old = "Research limits remain12 domain tools and9 candidate submissions TOTAL, "
    assert request["system"].count(old) == 1
    request["system"] = (
        request["system"]
        .replace(old, "There is NO cumulative candidate-submission or domain-tool-call ceiling, ")
        .replace(
            "Invalid/duplicate/repair programs consume\nslots.",
            "Invalid, duplicate and revised programs remain recorded.",
        )
        .replace(
            "Stop before quota/context exhaustion; exhaustion without final submission is recorded "
            "as abstention with no extra rescue request.",
            "Stop when further exploration is unlikely to help. Spending the full budget is not a "
            "goal. Context failure without submission remains an abstention.",
        )
    )
    request["system"] += (
        "\nOpen-exploration-v1 supersedes every historical request/candidate/tool quota in the "
        "retained transcript. All charges, candidates and feedback carry forward. Explore "
        "additional evidence-backed hypotheses when useful; submit or abstain voluntarily "
        "when further investigation is unlikely to help. Spending $15 is not a goal. "
        "Three candidates per batch, three live finalists, quality and cost-support checks, "
        "the uncertainty selection rule and protected holdouts remain.\n"
    )
    for tool in request["tools"]:
        if tool["name"] == "compare_candidates":
            tool["input_schema"]["properties"]["candidate_ids"].pop("maxItems", None)
    request["messages"] = []
    write(prepared / "research-template.json", request)
    config = ModelConfig.model_validate(
        json.loads((PRIOR / "prepared/model-config.json").read_text())
    )
    write(prepared / "model-config.json", config.model_dump(mode="json"))
    old_contract = json.loads((PRIOR / "prepared/contract.json").read_text())
    evidence = Evidence(json.loads((ROOT / old_contract["evidence_workspace_path"]).read_text()))
    first = {
        **request,
        "messages": origin.get("v2_messages")
        + [
            notice(
                SimpleNamespace(
                    store=origin, budget=Budget(origin, config, readonly=True), evidence=evidence
                ),
                "research",
                initial=True,
            )
        ],
    }
    (prepared / "first-request.json").write_bytes(canonical(first))
    gates = json.loads((PRIOR / "prepared/gates.json").read_text())
    gates["execution_contract"] = CONFIG
    gates["phase_prompt_hashes"] = {p: prompt_hash(template(p)) for p in ("research", "closing")}
    gates["provider_authorization"] = "user_requested_configuration_pending_local_seal"
    write(prepared / "gates.json", gates)
    write(
        prepared / "contract.json",
        {
            "schema": "filtered-ann.M4-open-exploration.v1",
            "date": "2026-11-17",
            "config": CONFIG,
            "evidence_identity": evidence.identity,
            "evidence_workspace_path": old_contract["evidence_workspace_path"],
            "scope": old_contract["scope"],
            "prior_outcome_sha256": sha(PRIOR / "assessment-v1/receipt.json"),
            "prior_history_sha256": digest(origin.get("v2_messages")),
            "prior_Messages_requests": 8,
            "prior_spend_usd": str(PRIOR_SPEND),
            "prior_candidate_submissions": original["candidate_submissions"],
            "prior_domain_tools": original["domain_tools"],
            "remaining_USD": CONFIG["remaining_USD"],
            "first_request_sha256": sha(prepared / "first-request.json"),
            "phase_prompt_hashes": gates["phase_prompt_hashes"],
            "new_paid_requests": 0,
            "new_count_requests": 0,
        },
    )
    verify_origin()


def seal():
    package = DEST / "package-freeze.json"
    assert not package.exists() and not (DEST / "live-open-exploration").exists()
    verify_origin()
    qualification = json.loads((DEST / "qualification-v1/receipt.json").read_text())
    assert qualification["status"] == "passed_open_exploration_actual_bound_rehearsal"
    assert qualification["new_paid_requests"] == qualification["new_count_requests"] == 0
    suites = ET.parse(DEST / "local-tests.xml").getroot().findall("testsuite")
    assert suites and sum(int(s.attrib["tests"]) for s in suites) > 0
    assert all(int(s.attrib[k]) == 0 for s in suites for k in ("failures", "errors", "skipped"))
    regression_suites = [
        suite
        for name in ("protocol", "provider", "context", "dollar")
        for suite in ET.parse(DEST / f"regression-{name}.xml").getroot().findall("testsuite")
    ]
    assert regression_suites
    assert all(
        int(s.attrib[k]) == 0 for s in regression_suites for k in ("failures", "errors", "skipped")
    )
    sources = set(HERE.glob("*.py")) | set(HERE.glob("*.md")) | set(HERE.glob("tests/*.py"))
    artifacts = {DEST / "local-tests.xml", DEST / "qualification-v1/receipt.json"}
    artifacts.update(DEST.glob("regression-*.xml"))
    for path in (DEST / "prepared").rglob("*"):
        if not path.is_file() or path.name.endswith("-shm"):
            continue
        if path.name.endswith("-wal"):
            assert path.stat().st_size == 0
            continue
        artifacts.add(path)
    write(
        package,
        {
            "schema": "filtered-ann.M4-open-exploration-package.v1",
            "date": "2026-11-17",
            "status": "configured_qualified_no_new_inference",
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)},
            "artifact_sha256": {str(p.relative_to(ROOT)): sha(p) for p in sorted(artifacts)},
            "origin_package_sha256": sha(PRIOR / "package-freeze.json"),
            "validation_test_outcomes_opened": False,
        },
    )
    verify_package()
    contract = json.loads((DEST / "prepared/contract.json").read_text())
    authorization = {
        "status": "authorized",
        "model": "claude-sonnet-5-5",
        "spending_policy": "dollar_ceiling",
        "max_requests": None,
        "max_count_requests": None,
        "candidate_submissions": None,
        "domain_tools": None,
        "max_output_tokens": 6000,
        "ceiling_usd": "15",
        "prior_spend_usd": str(PRIOR_SPEND),
        "evidence_hash": contract["evidence_identity"],
        "contract_sha256": sha(DEST / "prepared/contract.json"),
        "package_sha256": sha(package),
        "recorded_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "user_approval_record": "Remove the candidate and tool-call caps so the agent can explore "
        "more thoroughly within the $15 ceiling. Keep the quality and holdout safeguards; "
        "spending the full budget shouldn't be a goal. First commit the current work",
        "prior_provider_authorization_sha256": sha(PRIOR / "execution-authorization.json"),
        "configuration_only_no_inference_invoked": True,
    }
    write(DEST / "authorization.json", authorization)
    load_authorization(DEST / "authorization.json")
    receipt = {
        "schema": "filtered-ann.active-provider-configuration.v2",
        "date": "2026-11-17",
        "configuration": "open_exploration_v1",
        "status": "configured_qualified_no_new_inference",
        "max_requests": None,
        "max_count_requests": None,
        "candidate_submissions": None,
        "domain_tools": None,
        "ceiling_usd": "15",
        "actual_spend_usd": str(PRIOR_SPEND),
        "remaining_USD": CONFIG["remaining_USD"],
        "total_Messages_requests": 8,
        "prior_candidates_retained": 8,
        "prior_tools_retained": 10,
        "new_paid_requests": 0,
        "new_count_requests": 0,
        "local_tests_passed": sum(int(s.attrib["tests"]) for s in suites),
        "regression_tests_passed": sum(int(s.attrib["tests"]) for s in regression_suites),
        "runner_workspace_path": str((HERE / "exploration_run.py").relative_to(ROOT)),
        "package_workspace_path": str(package.relative_to(ROOT)),
        "package_sha256": sha(package),
        "authorization_workspace_path": str((DEST / "authorization.json").relative_to(ROOT)),
        "validation_test_outcomes_opened": False,
        "live_policy_timing_measured": False,
        "prior_M5_nominees_unchanged": True,
    }
    write(DEST / "configuration-receipt.json", receipt)
    write(STUDY / "reports/active-provider-configuration.json", receipt)
    copies = HERE / "receipts"
    copies.mkdir(exist_ok=False)
    for path in (
        package,
        DEST / "authorization.json",
        DEST / "configuration-receipt.json",
        DEST / "qualification-v1/receipt.json",
        DEST / "local-tests.xml",
    ):
        shutil.copyfile(path, copies / path.name)
    shutil.copytree(
        DEST / "prepared",
        copies / "prepared",
        ignore=shutil.ignore_patterns("origin-campaign", "first-request.json"),
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "seal"))
    args = parser.parse_args()
    {"prepare": prepare, "seal": seal}[args.action]()
