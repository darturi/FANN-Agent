import copy
import json

import pytest
from learning_cases import make_corpus, stop_at
from pydantic import ValidationError
from returned_cases import jsonl, returned_fixture, seal
from typer.testing import CliRunner

from fannagent.api import AgentError
from fannagent.broker import dispatch_request
from fannagent.learning.ablation import FEATURE, predicate_context, prepare_ablation
from fannagent.learning.archive import CandidateArchive
from fannagent.learning.benchmark import benchmark_report
from fannagent.learning.cli import app
from fannagent.learning.evaluate import OfflineEvaluator
from fannagent.learning.files import write_new
from fannagent.learning.models import FeedbackCorpus
from fannagent.learning.returned import import_returned_feedback, scorer_parity
from fannagent.learning.returned_models import ReturnedFeedback, parse_evidence
from fannagent.learning.tools import LearningTools


@pytest.fixture
def returned(tmp_path):
    inputs = returned_fixture(tmp_path)
    return inputs, import_returned_feedback(*inputs)


def test_import_reproduces_independent_saved_statistics_and_preserves_sources(returned):
    (package, campaign, _, _), evidence = returned
    assert len(evidence.corpus.queries) == 60
    assert sum(len(q.outcomes) for q in evidence.corpus.queries) == 180
    assert len(evidence.benchmark.pairs) == 2160
    assert evidence.import_receipt["scorer_parity"]["status"] == "passed"
    assert evidence.import_receipt["new_actual_labels"] == 60
    assert evidence.benchmark.warmups == 1
    assert len(evidence.benchmark.allocation_ids) == 2
    assert evidence.import_receipt["budget_receipt"]["provider_attempts"] == 42
    # Context and results vectors are not optimizer-visible feature columns.
    text = evidence.model_dump_json()
    assert '"native_ids"' not in text and '"vector"' not in text
    source = json.loads((campaign / "analysis/performance.json").read_text())
    assert scorer_parity(evidence, source)["status"] == "passed"
    raw = json.loads((package / "inputs/training-640-light.jsonl").read_text().splitlines()[0])
    query = next(q for q in evidence.corpus.queries if q.query_id == raw["query_id"])
    assert query.outcomes[0].source_prefix_sha256 == raw["labels"][0]["reference_prefix_sha256"]


def test_runtime_scorer_archive_and_freeze_use_returned_evidence_identity(returned, tmp_path):
    _, evidence = returned
    evaluator = OfflineEvaluator(parse_evidence(evidence.model_dump(mode="json")))
    candidate = next(a for a in evidence.benchmark.arms if a.kind == "candidate")
    report = evaluator.evaluate(candidate.policy)
    assert report["evidence_hash"] == evidence.evidence_hash
    assert report["learning_qualification"]["aggregate_quality_passed"] is True
    assert all(v["training_feasible"] for v in report["learning_qualification"]["regimes"].values())
    archive = CandidateArchive(tmp_path / "archive", create=True)
    tools = LearningTools(evaluator, archive)
    receipt = tools.call({"operation": "archive", "policy": candidate.policy})["receipt"]
    selected = tools.call({"operation": "freeze", "receipt": receipt})
    assert selected == tools.call({"operation": "freeze", "receipt": receipt})
    assert selected["confirmation_consumed"] is False
    assert selected["canonical_acceptance_established"] is False
    assert archive.read(receipt)["receipt"]["corpus"] == evidence.evidence_hash
    assert (
        tools.call({"operation": "inspect"})["original_campaign_budget"]["original_ceiling_usd"]
        == "15"
    )
    other = archive.record(evaluator, {**candidate.policy, "name": "different-policy"})
    with pytest.raises(AgentError, match="measured timing"):
        archive.freeze_for_confirmation(other["receipt"])
    summary = benchmark_report(evidence)
    assert summary["arms"]["oracle-original"]["activation-cold"]["deployable_arm"] is False
    assert (
        summary["matched_continue_contrasts"]["source"]["activation-cold"][
            "mean_candidate_minus_control_ms"
        ]
        < 0
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_pair",
        "activation",
        "policy_hash",
        "raw_recall",
        "control_results",
        "old_label",
        "prefix",
        "confirmation",
        "statistic",
    ],
)
def test_import_rejects_semantic_corruption_even_after_archive_resealing(tmp_path, mutation):
    package, campaign, verification, profile = returned_fixture(tmp_path)
    if mutation in ("duplicate_pair", "activation", "policy_hash", "raw_recall", "control_results"):
        path = campaign / "blocks/block-0/pairs.jsonl"
        rows = [json.loads(s) for s in path.read_text().splitlines()]
        if mutation == "duplicate_pair":
            rows[-1] = copy.deepcopy(rows[0])
        if mutation == "activation":
            rows[0]["policy_already_activated"] = True
        if mutation == "policy_hash":
            rows[0]["policy_hash"] = "0" * 64
        if mutation == "raw_recall":
            rows[0]["policy_recall"] = 0.9
        if mutation == "control_results":
            row = next(r for r in rows if r["kind"] == "matched-continue")
            row["policy_distances"][0] = 0.01
        jsonl(path, rows)
    elif mutation in ("old_label", "prefix"):
        path = campaign / "analysis/training-feedback.jsonl"
        rows = [json.loads(s) for s in path.read_text().splitlines()]
        if mutation == "old_label":
            rows[0]["labels"][0]["recall"] = 0.4
        else:
            rows[0]["labels"][1]["reference_prefix_sha256"] = "0" * 64
        jsonl(path, rows)
    else:
        path = campaign / (
            "analysis/feedback-receipt.json"
            if mutation == "confirmation"
            else "blocks/block-0/summary.json"
        )
        value = json.loads(path.read_text())
        if mutation == "confirmation":
            value["confirmation_outcomes_exported"] = True
        else:
            value["source"]["activation-cold"]["overall"]["gap_ms"] += 0.1
        path.write_text(json.dumps(value))
    seal(campaign, verification)
    with pytest.raises(AgentError):
        import_returned_feedback(package, campaign, verification, profile)


def test_import_rejects_wrong_archive_checksum(returned):
    (package, campaign, verification, profile), _ = returned
    record = json.loads(verification.read_text())
    record["source_archive_sha256"][campaign.name + ".tar.gz"] = "0" * 64
    verification.write_text(json.dumps(record))
    with pytest.raises(AgentError, match="archive checksum"):
        import_returned_feedback(package, campaign, verification, profile)


def test_normalized_benchmark_rejects_missing_coverage_and_oracle_as_global_policy(returned):
    _, evidence = returned
    raw = evidence.model_dump(mode="python")
    raw["benchmark"]["pairs"].pop()
    with pytest.raises(ValidationError, match="coverage"):
        ReturnedFeedback.model_validate(raw)
    raw = evidence.model_dump(mode="python")
    oracle = next(a for a in raw["benchmark"]["arms"] if a["kind"] == "oracle")
    oracle["policy"] = {"name": "fake-oracle", "root": "continue"}
    with pytest.raises(ValidationError, match="oracle"):
        ReturnedFeedback.model_validate(raw)


def test_normalized_timings_cannot_mark_an_incomplete_result_valid(returned):
    _, evidence = returned
    raw = evidence.model_dump(mode="python")
    raw["benchmark"]["pairs"][0]["returned_count"] = 9
    with pytest.raises(ValidationError, match="outcome"):
        ReturnedFeedback.model_validate(raw)


def quality_case(groups, invalid=False):
    raw = make_corpus(groups).model_dump(mode="python")
    for query in raw["queries"]:
        if query["group"] == "0":
            query["outcomes"][-1]["recall"] = 0.9
            if invalid:
                query["outcomes"][-1]["returned_count"] = 9
    return FeedbackCorpus.model_validate(raw)


def test_learning_interface_uses_aggregate_quality_and_keeps_invalid_unknown_hard_gates():
    tools = LearningTools(OfflineEvaluator(quality_case(100)))
    report = tools.call({"operation": "screen", "policy": stop_at(30)})
    assert report["qualification"]["per_query_loss_count"] == 2
    assert report["qualification"]["aggregate_quality_passed"] is True
    assert report["qualification"]["status"] == "ready_for_timing"
    assert all(not r["training_feasible"] for r in report["qualification"]["regimes"].values())
    failing = LearningTools(OfflineEvaluator(quality_case(6)))
    assert not failing.call({"operation": "screen", "policy": stop_at(30)})["qualification"][
        "aggregate_quality_passed"
    ]
    invalid = LearningTools(OfflineEvaluator(quality_case(100, invalid=True)))
    assert (
        invalid.call({"operation": "screen", "policy": stop_at(30)})["qualification"]["status"]
        == "invalid"
    )
    unknown = tools.call({"operation": "screen", "policy": stop_at(20)})
    assert unknown["qualification"]["status"] == "needs_actual_outcomes"
    assert len(unknown["feedback"]["unknown_stops"]) == 20
    with pytest.raises(AgentError):
        tools.call({"operation": "deploy", "policy": stop_at(30)})
    with pytest.raises(AgentError):
        tools.call({"operation": "inspect", "query_id": "hidden"})
    response = dispatch_request(tools, {"operation": "screen", "args": {"policy": stop_at(30)}})
    assert response["ok"] is True
    assert response["result"]["qualification"]["aggregate_quality_passed"] is True


def test_measured_policy_quality_is_available_without_reusable_checkpoint_labels(returned):
    _, evidence = returned
    raw = evidence.model_dump(mode="python")
    for query in raw["corpus"]["queries"]:
        query["outcomes"] = [o for o in query["outcomes"] if o["checkpoint_index"] != 3]
    sparse = ReturnedFeedback.model_validate(raw)
    candidate = next(a for a in sparse.benchmark.arms if a.kind == "candidate")
    report = OfflineEvaluator(sparse).evaluate(candidate.policy)
    assert report["overall"]["counts"] == {"unknown_stop": 60}
    quality = report["learning_qualification"]
    assert quality["replay_quality_passed"] is False
    assert quality["quality_source"] == "measured_policy_executions"
    assert quality["aggregate_quality_passed"] is True
    assert quality["regimes"]["activation-cold"]["training_feasible"] is True


def test_ablation_is_separate_and_uses_actual_predicates_without_claiming_qualification(
    returned, tmp_path
):
    (package, _, _, _), evidence = returned
    before = evidence.evidence_hash
    out = tmp_path / "predicate-context-v1"
    result = prepare_ablation(evidence, package, out)
    assert result["native_qualified"] is False
    study = json.loads((out / "study.json").read_text())
    context = json.loads((out / "query-context.json").read_text())
    assert {r["features"][FEATURE] for r in context} == {0, 32}
    assert study["arms"]["baseline"]["runtime_profile_hash"] == evidence.corpus.profile.fingerprint
    assert study["planned_context_profile_hash"] != study["base_runtime_profile_hash"]
    assert (
        study["budget_reset"] is False
        and study["measurement_contract"]["confirmation_queries"] == 0
    )
    assert study["existing_timings_apply_to_context_arm"] is False
    assert study["shared_objective"] == evidence.corpus.objective.model_dump(mode="json")
    assert evidence.evidence_hash == before
    with pytest.raises(ValidationError):
        parse_evidence(study)
    with pytest.raises(AgentError, match="preserve"):
        prepare_ablation(evidence, package, out)
    assert (
        predicate_context(
            {"id": "votes108", "filter": {"field": "m_000000", "op": "gte", "value": 32}}
        )
        == 32
    )
    with pytest.raises(AgentError):
        predicate_context({"filter": {"field": "m_000000", "op": "lt", "value": 32}})


def test_cli_qualify_tool_and_ablation_and_stage1_hash_stays_stable(returned, tmp_path):
    (package, _, _, _), evidence = returned
    path = tmp_path / "evidence.json"
    write_new(path, evidence.model_dump(mode="json"))
    request = tmp_path / "request.json"
    write_new(request, {"operation": "inspect"})
    runner = CliRunner()
    result = runner.invoke(app, ["tool", str(path), str(request)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["study_version"] == "measured-feedback-v2"
    result = runner.invoke(
        app,
        ["prepare-ablation", str(path), str(package), "--output", str(tmp_path / "cli-ablation")],
    )
    assert result.exit_code == 0, result.output
    original = make_corpus()
    assert parse_evidence(original.model_dump(mode="json")).evidence_hash == original.evidence_hash
