from __future__ import annotations

import json
import shlex
from contextlib import nullcontext

from .api import LegacyRun, require_capabilities
from .backends import create as create_backend
from .backends import extension
from .broker import FileBroker, Tools
from .budget import Budget
from .config import RunConfig
from .environment import ContainerEnvironment, ScriptedEnvironment
from .errors import AgentError, BudgetExceeded
from .store import ReadOnlyStore, Store, digest
from .study import Study

SYSTEM = """You explore a filtered ANN dataset offline and propose a bounded termination policy.
Your objective is recall equivalent to ordinary default execution, with tolerance 0.005,
at lower complete latency for easy queries. Use shell calls to fannagent-tool OP 'JSON'.
Available operations: inspect, queries, sample, count, probe, audit, labels, artifact,
descriptors, development_evaluate, validate, calibrate, submit.
Query vectors and portable filters must be within development scope.
Large evidence is referenced by hash; use artifact to fetch it and Python for analysis.
Development artifacts are JSON files at /workspace/artifacts/HASH.json.
The feature registry describes populations, provenance, availability, and collection cost.
Only runtime features may appear in a policy. Offline membership reconstructions are descriptors.
Policies use the bounded tree AST: name and root; root is continue/stop or an if/then/else tree.
Expressions are {feature: name}, {int: n}, {float: x}, or {op: operator, args: [...]}.
Checkpoint, scope and work-unit semantics are specified by the selected runtime profile.
Missing observations and interpreter errors continue search. A policy may stop only where the
backend supplies and qualifies stopping. Initial searches may have no executor feedback yet.
Use the supplied backend context and guidance. Inspect or fetch artifacts for additional detail.
Preserve default search settings. Choose your own experiments.
Calibration returns aggregates only. Submit a candidate only after passing calibration.
There is no online LLM. Spending is enforced externally and every attempt is accounted.
If no candidate works, end with a shell tool call containing command 'exit 0'.
"""


def open_run(root, config=None):
    if (root / "state.sqlite3").exists():
        if ReadOnlyStore(root).get("run_schema_version") != 2:
            raise LegacyRun(
                "legacy run is inspection-only; use a fresh schema v2 run "
                "or the pinned legacy environment for operations"
            )
    if config is not None:
        selected = extension(config.backend.name)
        config.backend.options = selected.normalize_options(
            config.backend.options, config.configuration_origin
        ).model_dump(mode="json", by_alias=True)
    store = Store(root, create=config is not None)
    if config is not None:
        old = store.get("config")
        if old and old != config.public():
            raise AgentError("run configuration is immutable; use a new run")
        store.set("config", config.public())
        store.set("run_schema_version", 2)
        store.set("configuration_origin", str(config.configuration_origin))
    else:
        config = RunConfig.model_validate(store.get("config"))
        from pathlib import Path

        config._origin = Path(store.get("configuration_origin"))
    selected = extension(config.backend.name)
    manifest = selected.manifest()
    current = {
        "extension": manifest.serialize(),
        "profile_hash": manifest.runtime_profile.fingerprint if manifest.runtime_profile else None,
        "native_identity": {
            "protocol": manifest.runtime_profile.native_protocol,
            "registry_hash": manifest.runtime_profile.native_registry_hash,
        }
        if manifest.runtime_profile
        else None,
    }
    previous = store.get("extension_manifest")
    if previous and (
        previous["profile_hash"] != current["profile_hash"]
        or previous["native_identity"] != current["native_identity"]
    ):
        raise AgentError("extension runtime profile changed; use a new run")
    if not previous:
        store.set("extension_manifest", current)

    backend = create_backend(config, store)
    return config, store, backend


def command(op, args):
    return "fannagent-tool " + op + " " + shlex.quote(json.dumps(args))


def explore(config, store, backend, *, resume=False, step_limit=1000):
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.exceptions import FormatError, InterruptAgentFlow

    from .model import BudgetedModel, ScriptedModel

    if store.get("cleaned"):
        raise AgentError("this run's resources were removed; prepare a new run")
    if not store.get("prepared"):
        raise AgentError("prepare a compatible copy before running")
    if not store.get("prepared")["qualified"]:
        raise AgentError("observation copy has not passed qualification")
    if store.get("frozen"):
        return {
            "status": "frozen",
            "policy_hash": Study(config, store, backend).frozen_policy().policy_hash,
        }
    require_capabilities(backend, study=True)
    system = SYSTEM + "\nSelected profile:\n" + json.dumps(backend.runtime_profile.describe())
    with store.lease("run"):
        budget = Budget(store, config.model)
        budget.recover()
        saved = store.get("trajectory") if resume else None
        trajectory = store.read(saved) if saved else None
        study = Study(config, store, backend)
        tools = Tools(study, budget)
        initial_context = tools.startup_context() if trajectory is None else None
        startup_metadata = (
            {"startup_context_version": 1}
            if trajectory is None
            else {k: trajectory[k] for k in ("startup_context_version",) if k in trajectory}
        )
        scripted = config.model.model == "scripted"
        if scripted:
            first = study.development[0]["query"]
            bad = {"name": "premature", "root": "stop"}
            good = backend.runtime_profile.scripted_policy
            if good is None:
                raise AgentError("selected profile supplies no scripted simulation candidate")
            actions = [
                command("probe", {"query": first}),
                command("calibrate", {"policy": bad}),
                command("calibrate", {"policy": good}),
                command("submit", {"policy": good}),
            ]
            if trajectory is not None and "startup_context_version" not in trajectory:
                actions.insert(0, command("inspect", {}))
            model = ScriptedModel(actions)
            context = nullcontext()
        else:
            model = BudgetedModel(config.model, budget)
            private = store.root / "private"
            private.mkdir(parents=True, exist_ok=True)
            context = FileBroker(tools, store.root / "workspace" / ".broker")
        with context as broker:
            env = (
                ScriptedEnvironment(tools)
                if scripted
                else ContainerEnvironment(store.root / "workspace", broker)
            )
            agent = DefaultAgent(
                model,
                env,
                system_template=system,
                instance_template="{{ task }}",
                cost_limit=0,
                step_limit=step_limit,
            )
            if trajectory is not None:
                agent.messages = trajectory["messages"]
                agent.n_calls = trajectory["info"]["model_stats"]["api_calls"]
                agent.cost = trajectory["info"]["model_stats"]["instance_cost"]
                if scripted:
                    model.index = trajectory.get("scripted_index", 0)
            else:
                agent.add_messages(
                    model.format_message(role="system", content=system),
                    model.format_message(
                        role="user",
                        content=(
                            "Generate a policy using the supplied prepared-run context. "
                            "Inspect or fetch artifacts when additional detail is needed.\n"
                            "Initial backend context:\n"
                            + json.dumps(initial_context, sort_keys=True, allow_nan=False)
                        ),
                    ),
                )
            status = "interrupted"
            try:
                if trajectory is None:
                    store.set(
                        "trajectory", store.put("trajectory", agent.serialize(startup_metadata))
                    )
                while agent.n_calls < step_limit:
                    try:
                        agent.step()
                    except FormatError as exc:
                        agent.add_messages(*exc.messages)
                    except InterruptAgentFlow as exc:
                        agent.add_messages(*exc.messages)
                        status = "no_recommendation"
                        break
                    finally:
                        store.set(
                            "trajectory", store.put("trajectory", agent.serialize(startup_metadata))
                        )
                    if store.get("frozen"):
                        status = "frozen"
                        break
                    if scripted and model.index >= len(model.actions):
                        status = "no_recommendation"
                        break
            except BudgetExceeded:
                status = "budget_exhausted"
            finally:
                if not scripted:
                    env.close()
                store.set("status", status)
                store.set("ledger", store.put("ledger", budget.summary()))
            if status in {"no_recommendation", "budget_exhausted"}:
                store.set(
                    "report",
                    store.put(
                        "report",
                        {
                            "status": "no_recommendation",
                            "run_status": status,
                            "valid": True,
                            "reason": (
                                "monetary ceiling reached before a candidate was submitted"
                                if status == "budget_exhausted"
                                else "no candidate passed calibration"
                            ),
                            "simulated": bool(backend.inspect_target().get("simulated")),
                        },
                    ),
                )
            return {
                "status": status,
                "budget": budget.summary(),
                "run_identity": digest(config.public()),
            }
