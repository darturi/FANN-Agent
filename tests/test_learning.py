import copy
import json
import subprocess
import sys

import pytest
from learning_cases import make_corpus, stop_at
from pydantic import ValidationError
from typer.testing import CliRunner

from fannagent.api import AgentError, evaluate_policy, validate_policy
from fannagent.cli import app
from fannagent.learning.archive import CandidateArchive
from fannagent.learning.describe import describe_corpus
from fannagent.learning.evaluate import OfflineEvaluator
from fannagent.learning.files import read_json, write_new
from fannagent.learning.fit import FitConfig, fit_policy
from fannagent.learning.models import FeedbackCorpus, TimingPair, TimingSchedule, policy_input
from fannagent.store import Store


def changed(corpus, mutate):
    raw = corpus.model_dump(mode="python")
    mutate(raw)
    return FeedbackCorpus.model_validate(raw)


def test_replay_agrees_with_public_interpreter_and_never_labels_unknown_stops():
    corpus = make_corpus()
    evaluator = OfflineEvaluator(corpus)
    for work, expected in (
        (10, "measured_recall_loss"),
        (20, "unknown_stop"),
        (30, "measured_preserving"),
        (40, "continued"),
    ):
        raw = stop_at(work)
        report = evaluator.evaluate(raw)
        assert report["overall"]["counts"] == {expected: 12}
        artifact = validate_policy(raw, corpus.profile)
        for query, decision in zip(corpus.queries, report["decisions"]):
            first = next(
                (
                    c.checkpoint_index
                    for c in query.checkpoints
                    if evaluate_policy(artifact, policy_input(c), corpus.profile).value == "stop"
                ),
                None,
            )
            assert decision["checkpoint_index"] == first
        assert all(r["training_feasible"] is None for r in report["timings"].values())
        assert report["canonical_acceptance_established"] is False
        if work == 20:
            assert report["overall"]["mean_observed_recall_delta"] is None
            assert len(report["measurement_requests"]) == 12
            assert report["overall"]["quality_coverage_complete"] is False
        if work == 40:
            assert (
                report["feedback"]["unnecessary_continuation_examples"][0][
                    "avoidable_work_against_measured_preserving_stop"
                ]
                == 10
            )


def test_missing_features_guards_and_arithmetic_failures_match_runtime():
    corpus = changed(
        make_corpus(), lambda d: d["queries"][0]["checkpoints"][0]["features"].update(nullable=None)
    )
    evaluator = OfflineEvaluator(corpus)
    condition = {"op": "gte", "args": [{"feature": "nullable"}, {"float": 0.1}]}
    unguarded = {"name": "unguarded", "root": {"if": condition, "then": "stop", "else": "continue"}}
    report = evaluator.evaluate(unguarded)
    assert report["overall"]["counts"]["runtime_error"] == 1
    assert report["decisions"][0]["recall_delta"] is None
    guarded = {
        "name": "guarded",
        "root": {
            "if": {"op": "is_available", "args": [{"feature": "nullable"}]},
            "then": unguarded["root"],
            "else": "continue",
        },
    }
    report = evaluator.evaluate(guarded)
    assert "runtime_error" not in report["overall"]["counts"]
    assert report["decisions"][0]["checkpoint_index"] == 2
    overflow = {
        "name": "overflow",
        "root": {
            "if": {
                "op": "gt",
                "args": [
                    {"op": "mul", "args": [{"feature": "work"}, {"int": 2**63 - 1}]},
                    {"int": 0},
                ],
            },
            "then": "stop",
            "else": "continue",
        },
    }
    assert evaluator.evaluate(overflow)["overall"]["counts"] == {"runtime_error": 12}


def test_unqualified_feature_and_collection_changes_are_rejected():
    evaluator = OfflineEvaluator(make_corpus())
    raw = {
        "name": "unqualified",
        "root": {
            "if": {"op": "is_available", "args": [{"feature": "unqualified"}]},
            "then": "stop",
            "else": "continue",
        },
    }
    with pytest.raises(AgentError, match="qualification"):
        evaluator.evaluate(raw)
    with pytest.raises(AgentError, match="collection"):
        evaluator.evaluate({**stop_at(30), "feature_groups": []})
    with pytest.raises(AgentError, match="training subset"):
        evaluator.evaluate(stop_at(30), groups=["confirmation"])
    report = evaluator.evaluate(stop_at(30), groups=["1", "2"])
    assert report["overall"]["queries"] == 4
    assert {r["group"] for r in report["decisions"]} == {"1", "2"}
    assert report["timings"]["reused-warm"]["training_feasible"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(scope="confirmation"),
        lambda d: d["queries"][0].update(split="confirmation"),
        lambda d: d["queries"][0].update(group="held-out"),
        lambda d: d["queries"].append(copy.deepcopy(d["queries"][0])),
        lambda d: d["queries"][0].update(trajectory_complete=False),
        lambda d: d["queries"][0]["checkpoints"].pop(0),
        lambda d: d["queries"][0]["checkpoints"][0]["features"].update(unqualified=1.0),
        lambda d: d["queries"][0]["checkpoints"][0]["features"].update(work=True),
        lambda d: d["queries"][0]["checkpoints"][0]["features"].update(signal=float("nan")),
        lambda d: d["queries"][0]["outcomes"][0].update(prefix_matches=False),
        lambda d: d["queries"][0]["outcomes"][0].update(actual_work=11),
        lambda d: d["queries"][0]["outcomes"].append(copy.deepcopy(d["queries"][0]["outcomes"][0])),
    ],
)
def test_corpus_rejects_scope_and_evidence_corruption(mutation):
    with pytest.raises(ValidationError):
        changed(make_corpus(), mutation)


def timed_corpus(groups=6, loss=0.0):
    corpus = make_corpus(groups)
    policy = OfflineEvaluator(corpus).validate(stop_at(30))
    pairs = [
        TimingPair(
            query_id=q.query_id,
            policy_hash=policy.policy_hash,
            regime=regime,
            block=block,
            repetition=repetition,
            native_ms=2.0,
            policy_ms=1.0,
            native_recall=1.0,
            policy_recall=1.0 - (loss if q.group == "0" else 0.0),
            valid=True,
            returned_count=10,
            source_ref=f"timing:{q.query_id}:{block}:{regime}:{repetition}",
        )
        for q in corpus.queries
        for block in (0, 1)
        for regime, passes in (("activation-cold", 1), ("reused-warm", 2))
        for repetition in range(passes)
    ]
    return FeedbackCorpus.model_validate(
        {
            **corpus.model_dump(),
            "timings": [p.model_dump() for p in pairs],
            "timing_schedule": TimingSchedule(blocks=[0, 1], warm_passes=2).model_dump(),
        }
    )


def test_measured_qualification_requires_complete_pairs_and_groups_repetitions():
    corpus = timed_corpus()
    report = OfflineEvaluator(corpus).evaluate(stop_at(30))
    warm = report["timings"]["reused-warm"]
    assert warm["training_feasible"] is True
    assert warm["overall"]["independent_groups"] == 6
    assert warm["pairs"] == 48
    assert set(warm["per_block"]) == {"0", "1"}
    partial = changed(corpus, lambda d: d["timings"].pop())
    warm = OfflineEvaluator(partial).evaluate(stop_at(30))["timings"]["reused-warm"]
    assert warm["status"] == "incomplete" and warm["training_feasible"] is None


def test_per_query_loss_does_not_replace_the_declared_aggregate_objective():
    # One 0.1 recall loss among 100 independent vectors per filter: a real top-10 step.
    corpus = timed_corpus(groups=100, loss=0.1)
    warm = OfflineEvaluator(corpus).evaluate(stop_at(30))["timings"]["reused-warm"]
    assert warm["training_feasible"] is True
    assert warm["overall"]["mean_recall_delta"] < 0
    failing = timed_corpus(groups=6, loss=0.1)
    assert (
        OfflineEvaluator(failing).evaluate(stop_at(30))["timings"]["reused-warm"][
            "training_feasible"
        ]
        is False
    )


def test_duplicate_or_invented_timing_records_are_rejected():
    corpus = timed_corpus()
    with pytest.raises(ValidationError, match="duplicate timing"):
        changed(corpus, lambda d: d["timings"].append(copy.deepcopy(d["timings"][0])))
    with pytest.raises(ValidationError, match="query or native recall"):
        changed(corpus, lambda d: d["timings"][0].update(query_id="confirmation"))
    with pytest.raises(ValidationError):
        changed(corpus, lambda d: d["timings"][0].update(policy_ms=float("inf")))


def test_fitter_is_deterministic_and_holds_all_filter_variants_of_a_group_together():
    corpus = make_corpus()
    config = FitConfig(minimum_leaf_groups=1, folds=3)
    first = fit_policy(OfflineEvaluator(corpus), config)
    second = fit_policy(OfflineEvaluator(corpus), config)
    assert first == second
    assert first["measured_labels_used"] == 24  # Never the unlabelled checkpoint states.
    assert first["canonical_acceptance_established"] is False
    for fold in first["cross_validation"]:
        train, held = set(fold["training_groups"]), set(fold["held_out_groups"])
        assert not train & held and train | held == {str(g) for g in range(6)}
        assert fold["overall"]["queries"] == 2 * len(held)
    OfflineEvaluator(corpus).validate(first["policy"])


def test_candidate_archive_is_idempotent_and_preserves_study_ledgers(tmp_path):
    evaluator = OfflineEvaluator(make_corpus())
    archive = CandidateArchive(tmp_path / "archive", create=True)
    first = archive.record(evaluator, stop_at(30), fitting={"method": "fixture"})
    second = archive.record(evaluator, stop_at(30), fitting={"method": "fixture"})
    assert first == second
    view = CandidateArchive(tmp_path / "archive", readonly=True)
    saved = view.read(first["receipt"])
    assert saved["candidate"]["policy_hash"] == saved["assessment"]["policy_hash"]
    assert saved["assessment"]["evidence_hash"] == evaluator.evidence_hash
    with pytest.raises(AgentError, match="read-only"):
        view.record(evaluator, stop_at(30))
    run = Store(tmp_path / "existing-study", create=True)
    run.set("budget_contract", {"ceiling_usd": "15", "committed": "3.17"})
    before = run.path.read_bytes()
    with pytest.raises(AgentError, match="study runs are separate"):
        CandidateArchive(run.root)
    assert run.path.read_bytes() == before
    assert run.get("budget_contract") == {"ceiling_usd": "15", "committed": "3.17"}
    with archive.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM charges").fetchone()[0] == 0


def test_archive_checks_content_integrity_on_read(tmp_path):
    archive = CandidateArchive(tmp_path / "archive", create=True)
    receipt = archive.record(OfflineEvaluator(make_corpus()), stop_at(30))
    with archive.store.connect() as db:
        path = db.execute(
            "SELECT path FROM artifacts WHERE hash=?", (receipt["candidate"],)
        ).fetchone()[0]
    target = archive.store.root / path
    target.write_text(target.read_text().replace("stop-30", "stop-31"))
    with pytest.raises(AgentError, match="identity changed"):
        CandidateArchive(archive.store.root, readonly=True).read(receipt["receipt"])


def test_archive_recovers_interrupted_publication(tmp_path, monkeypatch):
    archive = CandidateArchive(tmp_path / "archive", create=True)
    evaluator = OfflineEvaluator(make_corpus())
    original = archive.store.set

    def interrupted(*args):
        raise AgentError("interrupted before receipt publication")

    monkeypatch.setattr(archive.store, "set", interrupted)
    with pytest.raises(AgentError, match="interrupted"):
        archive.record(evaluator, stop_at(30))
    assert CandidateArchive(archive.store.root, readonly=True).list()["receipts"] == []
    monkeypatch.setattr(archive.store, "set", original)
    receipt = archive.record(evaluator, stop_at(30))
    assert archive.read(receipt["receipt"])["candidate"]["policy_hash"] == receipt["policy_hash"]
    with archive.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 4


def test_information_conflicts_are_diagnostics_and_replay_owns_its_evidence():
    original = make_corpus()
    evaluator = OfflineEvaluator(original)
    original.queries[0].checkpoints[0].features["work"] = 999
    assert evaluator.evaluate(stop_at(30))["overall"]["counts"] == {"measured_preserving": 12}
    corpus = changed(make_corpus(), lambda d: d["queries"][1]["outcomes"][1].update(recall=0.5))
    report = describe_corpus(corpus)
    assert report["conflicting_native_preservation_states"] == 1
    assert {r["preserves_native"] for r in report["conflict_examples"][0]} == {True, False}


def test_cli_fit_evaluate_archive_and_recovery_work_together(tmp_path):
    corpus = tmp_path / "corpus.json"
    fit = tmp_path / "fit.json"
    write_new(corpus, make_corpus().model_dump(mode="json"))
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "learning",
            "fit",
            str(corpus),
            "--output",
            str(fit),
            "--minimum-leaf-groups",
            "1",
            "--folds",
            "3",
        ],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["learning", "evaluate", str(corpus), str(fit)])
    assert result.exit_code == 0, result.output
    archive = tmp_path / "candidates"
    result = runner.invoke(
        app, ["learning", "archive", str(corpus), str(fit), "--archive", str(archive)]
    )
    assert result.exit_code == 0, result.output
    receipt = json.loads(result.stdout)["receipt"]
    result = runner.invoke(app, ["learning", "candidates", "--archive", str(archive)])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["receipts"][0]["receipt"] == receipt
    result = runner.invoke(app, ["learning", "show", receipt, "--archive", str(archive)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["candidate"]["fitting"]["folds"] == 3
    value = read_json(fit)
    value["evidence_hash"] = "0" * 64
    stale = tmp_path / "stale.json"
    write_new(stale, value)
    result = runner.invoke(app, ["learning", "evaluate", str(corpus), str(stale)])
    assert result.exit_code != 0


def test_bad_policy_and_nonregular_file_are_rejected(tmp_path):
    with pytest.raises(AgentError, match="must be an object"):
        OfflineEvaluator(make_corpus()).evaluate([])
    target = tmp_path / "target.json"
    write_new(target, {})
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(AgentError, match="cannot read"):
        read_json(link)
    with pytest.raises(ValidationError):
        changed(
            make_corpus(),
            lambda d: d["queries"][0]["checkpoints"][0]["features"].update(signal=10**400),
        )


def test_cli_evaluates_fits_and_archives_without_model_or_database_modules(tmp_path):
    corpus_path, policy_path = tmp_path / "corpus.json", tmp_path / "policy.json"
    write_new(corpus_path, make_corpus().model_dump(mode="json"))
    write_new(policy_path, stop_at(20))
    runner = CliRunner()
    result = runner.invoke(app, ["learning", "evaluate", str(corpus_path), str(policy_path)])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["measurement_requests_count"] == 12 and "decisions" not in report
    output = tmp_path / "assessment.json"
    args = ["learning", "evaluate", str(corpus_path), str(policy_path), "--output", str(output)]
    assert runner.invoke(app, args).exit_code == 0
    assert runner.invoke(app, args).exit_code != 0  # Exclusive output, no silent overwrite.
    assert len(read_json(output)["decisions"]) == 12
    code = (
        "import sys; import fannagent.learning; "
        "assert not any(n.startswith(('psycopg','fannagent_pgvector','litellm',"
        "'minisweagent')) for n in sys.modules)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


@pytest.mark.parametrize("value", ['{"a":1,"a":2}', '{"a":NaN}'])
def test_json_input_rejects_duplicate_keys_and_nonfinite_values(tmp_path, value):
    path = tmp_path / "bad.json"
    path.write_text(value)
    with pytest.raises(AgentError):
        read_json(path)
