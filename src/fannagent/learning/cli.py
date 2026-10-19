from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError

from ..api import AgentError
from .archive import CandidateArchive
from .describe import describe_corpus
from .evaluate import OfflineEvaluator
from .files import read_json, write_new
from .fit import FitConfig, fit_policy
from .importers import import_torch_training
from .models import FeedbackCorpus

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def load_corpus(path: Path) -> FeedbackCorpus:
    return FeedbackCorpus.model_validate(read_json(path))


def emit(value, output: Path | None = None):
    if output is not None:
        write_new(output, value)
        typer.echo(json.dumps({"output": str(output), "written": True}))
    else:
        typer.echo(json.dumps(value, indent=2, allow_nan=False))


def policy_from_file(path: Path, evaluator: OfflineEvaluator):
    value = read_json(path)
    if isinstance(value, dict) and value.get("format") == "fannagent.learning.fit.v1":
        if (
            value.get("scope") != "learning"
            or value.get("evidence_hash") != evaluator.evidence_hash
        ):
            raise AgentError("fitted policy belongs to different training evidence")
        artifact = evaluator.validate(value["policy"])
        if artifact.policy_hash != value["policy_hash"]:
            raise AgentError("fitted policy hash differs")
        return value["policy"], value["configuration"]
    return value, None


@app.command("inspect")
def inspect_corpus(corpus: Path):
    """Show training coverage, qualified features and observed information conflicts."""
    emit(describe_corpus(load_corpus(corpus)))


@app.command("import-torch")
def import_torch(
    package: Path,
    output: Path = typer.Option(..., "--output"),
    backend: str = "pgvector",
):
    """Normalize the pinned training package; never execute its scripts or query a DB."""
    from ..backends import extension

    profile = extension(backend).manifest().runtime_profile
    if profile is None:
        raise AgentError("backend has no runtime policy profile")
    corpus = import_torch_training(package, profile)
    emit(corpus.model_dump(mode="json"), output)
    typer.echo(json.dumps({"evidence_hash": corpus.evidence_hash, "queries": len(corpus.queries)}))


@app.command("evaluate")
def evaluate(
    corpus: Path,
    policy: Path,
    output: Path | None = None,
    maximum_examples: int = typer.Option(20, min=1, max=100),
):
    """Assess first stops against measured labels; unknown outcomes stay unknown."""
    evaluator = OfflineEvaluator(load_corpus(corpus))
    raw, _ = policy_from_file(policy, evaluator)
    report = evaluator.evaluate(raw, maximum_examples=maximum_examples)
    if output is not None:
        emit(report, output)
    else:
        view = {k: v for k, v in report.items() if k not in {"decisions", "measurement_requests"}}
        view["measurement_requests_count"] = len(report["measurement_requests"])
        emit(view)


@app.command("fit")
def fit(
    corpus: Path,
    output: Path = typer.Option(..., "--output"),
    depth: int = 2,
    minimum_leaf_groups: int = 8,
    risk_weight: float = 20.0,
    folds: int = 5,
):
    """Fit a deterministic measured-label tree with grouped cross-validation."""
    result = fit_policy(
        OfflineEvaluator(load_corpus(corpus)),
        FitConfig(
            depth=depth,
            minimum_leaf_groups=minimum_leaf_groups,
            risk_weight=risk_weight,
            folds=folds,
        ),
    )
    emit(result, output)


@app.command("archive")
def archive(
    corpus: Path,
    policy: Path,
    archive: Path = typer.Option(..., "--archive"),
    fitting: Path | None = None,
):
    """Save a reproducible training assessment without selecting a serving policy."""
    evaluator = OfflineEvaluator(load_corpus(corpus))
    raw, configuration = policy_from_file(policy, evaluator)
    evaluator.validate(raw)
    target = CandidateArchive(archive, create=not archive.exists())
    receipt = target.record(
        evaluator,
        raw,
        fitting=read_json(fitting) if fitting is not None else configuration,
    )
    emit(receipt)


@app.command("show")
def show(receipt: str, archive: Path = typer.Option(..., "--archive")):
    """Read a saved assessment without schema writes, model requests or DB calls."""
    emit(CandidateArchive(archive, readonly=True).read(receipt))


@app.command("candidates")
def candidates(archive: Path = typer.Option(..., "--archive"), offset: int = 0, limit: int = 20):
    """List saved receipts without changing the archive or selecting a candidate."""
    emit(CandidateArchive(archive, readonly=True).list(offset=offset, limit=limit))


def main():
    try:
        app()
    except (AgentError, ValidationError, KeyError, TypeError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise SystemExit(1) from None
