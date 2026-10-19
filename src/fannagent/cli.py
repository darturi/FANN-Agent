from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path

import typer
from pydantic import ValidationError

from .api import require_capabilities
from .backends import discover, extension
from .budget import Budget
from .config import ModelConfig, load_config
from .controller import explore, open_run
from .errors import AgentError
from .learning.cli import app as learning_app
from .store import ReadOnlyStore
from .study import Study

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def output(value):
    typer.echo(json.dumps(value, indent=2, default=str))


@app.command("init")
def init_config(
    backend: str = typer.Option("fake"),
    output_path: Path = typer.Option(Path("fannagent.yaml"), "--output"),
):
    """Create a private configuration without replacing an existing file."""
    from .onboarding import initialize

    output(initialize(backend, output_path))


@app.command()
def doctor(config: Path, check_source: bool = False):
    """Check installation readiness without creating a run or spending model money."""
    from .onboarding import diagnose

    result = diagnose(config, check_source=check_source)
    output(result)
    if not result["ready"]:
        raise typer.Exit(1)


@app.command()
def inspect(config: Path, run: Path = Path("runs/default")):
    """Inspect an existing target without loading or rebuilding data."""
    _, store, backend = open_run(run, load_config(config))
    try:
        output(
            {
                **backend.inspect_target(),
                "checkpoint_policy_hash": (store.get("candidate_checkpoint") or {}).get(
                    "policy_hash"
                ),
            }
        )
    finally:
        backend.close()


@app.command()
def prepare(config: Path, run: Path = Path("runs/default")):
    """Restore and qualify a separately owned observation copy."""
    _, store, backend = open_run(run, load_config(config))
    try:
        with store.lease("prepare"):
            require_capabilities(backend, preparation=True)
            prepared = backend.prepare_copy()
            store.set("prepared", prepared.serialize())
            output(prepared.serialize())
    finally:
        backend.close()


@app.command("run")
def run_agent(config: Path, run: Path = Path("runs/default"), steps: int = 1000):
    """Create a study and explore it with the configured model."""
    config, store, backend = open_run(run, load_config(config))
    try:
        output(explore(config, store, backend, step_limit=steps))
    finally:
        backend.close()


@app.command()
def resume(run: Path = Path("runs/default"), steps: int = 1000):
    """Resume the same study and original monetary contract."""
    config, store, backend = open_run(run)
    try:
        output(explore(config, store, backend, resume=True, step_limit=steps))
    finally:
        backend.close()


@app.command()
def evaluate(run: Path = Path("runs/default")):
    """Consume the frozen policy's evaluator-only final test entitlement."""
    config, store, backend = open_run(run)
    try:
        with store.lease("run"):
            output(Study(config, store, backend).final())
    finally:
        backend.close()


@app.command()
def status(run: Path = Path("runs/default")):
    from .experiments import ExperimentJournal

    store = ReadOnlyStore(run)
    config = ModelConfig.model_validate(store.get("config")["model"])
    output(
        {
            "status": store.get("status", "prepared" if store.get("prepared") else "new"),
            "prepared": store.get("prepared"),
            "frozen": store.get("frozen"),
            "test_entitlement": store.get("test_entitlement"),
            "budget": Budget(store, config, readonly=True).summary(),
            "checkpoint_policy_hash": (store.get("candidate_checkpoint") or {}).get("policy_hash"),
            "submission_recovery": store.get("submission_recovery"),
            "research": ExperimentJournal(store).summary(),
            **(store.get("finalization") or {}),
        }
    )


@app.command()
def report(run: Path = Path("runs/default")):
    """Render results locally, without another model call."""
    store = ReadOnlyStore(run)
    identity = store.get("report")
    from .experiments import ExperimentJournal

    fallback = (
        store.get("budget_exhaustion_report") or store.get("invalid_submission_report")
        if not store.get("test_entitlement")
        else None
    )
    if not identity and not fallback:
        raise AgentError("no completed evaluation report")
    value = fallback or store.read(identity)
    value.update(store.get("finalization") or {})
    config = store.get("config")
    value["budget"] = Budget(
        store, ModelConfig.model_validate(config["model"]), readonly=True
    ).summary()
    value["copy_manifest"] = store.get("prepared")
    value["research"] = ExperimentJournal(store).summary()
    text = f"# Filtered ANN policy study\n\nOutcome: **{value['status']}**\n\n"
    if value.get("simulated"):
        text += "This run used simulated latency. It provides no database performance claim.\n\n"
    text += "```json\n" + json.dumps(value, indent=2) + "\n```\n\n"
    text += (
        "The observation database is a snapshot. Application cutover, writes, replication "
        "and HA require separate operations.\n"
        "Rollback: stop using the policy session and issue ordinary default queries.\n"
    )
    path = store.root / "REPORT.md"
    path.write_text(text)
    output({"report": str(path), "result": value})


@app.command()
def experiments(
    run: Path = Path("runs/default"),
    experiment_id: str | None = None,
    offset: int = 0,
    limit: int = 20,
):
    """Inspect experiment plans and recorded outcomes without model or database calls."""
    from .experiments import ExperimentJournal

    journal = ExperimentJournal(ReadOnlyStore(run))
    args = {"action": "get" if experiment_id else "list", "offset": offset, "limit": limit}
    if experiment_id:
        args["experiment_id"] = experiment_id
    output({"research": journal.summary(), "journal": journal.call(args)})


@app.command()
def deploy(
    run: Path = Path("runs/default"),
    target: Path = typer.Option(
        ..., help="Explicit run containing the selected qualified instrumented deployment."
    ),
):
    """Install an accepted policy; never redirect application traffic."""
    config, store, backend = open_run(run)
    tc, ts, tb = open_run(target)
    try:
        with ExitStack() as locks:
            stores = {store.root: store, ts.root: ts}
            for root in sorted(stores):
                locks.enter_context(stores[root].lease("run"))
                locks.enter_context(stores[root].lease("prepare"))
            identity = store.get("report")
            if not identity or store.read(identity)["status"] != "accepted":
                raise AgentError("deployment requires an accepted final evaluation")
            policy = Study(config, store, backend).frozen_policy()
            if (
                tc.backend.name != config.backend.name
                or not ts.get("prepared", {}).get("qualified")
                or tb.compatibility() != backend.compatibility()
                or tb.snapshot().identity != backend.snapshot().identity
            ):
                raise AgentError(
                    "deployment compatibility differs from the frozen evaluated target"
                )
            require_capabilities(tb, serving=True)
            ack = tb.install_policy(policy)
            ts.set(
                "deployment",
                {
                    **ack,
                    "source_frozen": store.get("frozen"),
                    "policy": policy.model_dump(mode="json"),
                    "compatibility": backend.compatibility(),
                    "rollback": "ordinary default query path",
                },
            )
            output(
                {
                    **ack,
                    "session_required": True,
                    "instruction": (
                        "Use fannagent.client.open_session on this run; "
                        "installation is connection-local."
                    ),
                }
            )
    finally:
        backend.close()
        tb.close()


@app.command()
def clean(run: Path = Path("runs/default")):
    """Remove only Docker resources whose labels prove this run owns them."""
    _, store, backend = open_run(run)
    try:
        with store.lease("run"), store.lease("prepare"):
            from .environment import clean_sandboxes

            clean_sandboxes(store)
            require_capabilities(backend, preparation=True)
            result = backend.cleanup()
            store.set("cleaned", True)
            output(result)
    finally:
        backend.close()


backends_app = typer.Typer(no_args_is_help=True)
app.add_typer(backends_app, name="backends")

app.add_typer(learning_app, name="learning")


@backends_app.command("list")
def list_backends():
    output([extension(name).manifest().serialize() for name in sorted(discover())])


@backends_app.command("describe")
def describe_backend(name: str):
    output(extension(name).manifest().serialize())


def main():
    try:
        app()
    except (AgentError, ValidationError) as exc:
        typer.echo(str(exc), err=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
