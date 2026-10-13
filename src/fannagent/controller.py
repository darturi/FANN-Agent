from __future__ import annotations

import json
import shlex
from contextlib import ExitStack, nullcontext

from .api import LegacyRun, require_capabilities
from .backends import create as create_backend
from .backends import extension
from .broker import FileBroker, Tools
from .budget import Budget
from .config import RunConfig
from .environment import ContainerEnvironment, ScriptedEnvironment, clean_sandboxes
from .errors import AgentError, BudgetExceeded
from .experiments import ExperimentJournal, scripted_conclusion, scripted_plan
from .guidance import check_initial_bound, pin_prompt, read_guidance, system_guidance
from .store import ReadOnlyStore, Store, digest
from .study import Study, checkpoint_failure, no_checkpoint_outcome
from .submission import CORRECTION_GUIDANCE, MAX_CONSECUTIVE_INVALID_TURNS, InvalidSubmission
from .workflow import TOOL_GUIDANCE, workflow_notice

CHECKPOINT_GUIDANCE = """Candidate checkpointing is available. To designate your fallback, call
calibrate with {"policy": YOUR_POLICY, "checkpoint": true}. Only an accepted, valid calibration
replaces the saved choice; unmarked or rejected candidates leave it unchanged. If your model
budget expires, the controller freezes this choice using cached evidence without another
model request. Continue exploring or submit explicitly. Final testing remains evaluator-only.
"""

SYSTEM = (
    """You explore a filtered ANN dataset offline and propose a bounded termination policy.
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
    + CHECKPOINT_GUIDANCE
    + CORRECTION_GUIDANCE
    + TOOL_GUIDANCE
)


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


def _run_result(config, store, budget, study, status, **details):
    result = {
        "status": status,
        "budget": budget.summary(),
        "run_identity": digest(config.public()),
        "checkpoint_policy_hash": (store.get("candidate_checkpoint") or {}).get("policy_hash"),
        "research": ExperimentJournal(store).summary(),
        **(store.get("finalization") or {}),
        **details,
    }
    if status == "frozen":
        result["policy_hash"] = study.frozen_policy().policy_hash
    return result


def _save_exhausted_ledger(store, budget):
    summary = budget.summary()
    try:
        store.set("ledger", store.put("ledger", summary))
    except Exception as exc:
        # Charges are already durable in SQLite. Retain the summary if artifact storage is full.
        store.set_many(
            {
                "ledger_summary": summary,
                "ledger_storage_failure": {"failure": type(exc).__name__, "message": str(exc)},
            }
        )


def _finish_exhaustion(config, store, backend, budget, study=None):
    journal = ExperimentJournal(store)
    journal.recover()
    journal.interrupt("budget_exhausted", terminal=True)
    store.set("status", "budget_exhausted")
    _save_exhausted_ledger(store, budget)
    if not store.get("candidate_checkpoint"):
        outcome = no_checkpoint_outcome()
    else:
        try:
            study = study or Study(config, store, backend)
            outcome = study.finalize_checkpoint()
        except Exception as exc:
            outcome = checkpoint_failure(
                "checkpoint_ineligible",
                (store.get("candidate_checkpoint") or {}).get("policy_hash"),
                exc,
            )
    if outcome["status"] == "frozen":
        return _run_result(config, store, budget, study, "frozen")
    finalization = {"termination_reason": "budget_exhausted"}
    store.set("finalization", finalization)
    # A completed or consumed final test must never be replaced by an exploration report.
    if not store.get("test_entitlement"):
        try:
            simulated = bool(backend.inspect_target().get("simulated"))
        except Exception:
            simulated = None
        report = {
            **outcome,
            **finalization,
            "run_status": "budget_exhausted",
            "simulated": simulated,
        }
        try:
            identity = store.put("report", report)
        except Exception as exc:
            report["report_storage_failure"] = {"failure": type(exc).__name__, "message": str(exc)}
            store.set("budget_exhaustion_report", report)
        else:
            store.set_many({"report": identity}, delete=("budget_exhaustion_report",))
    return _run_result(
        config,
        store,
        budget,
        study,
        "budget_exhausted",
        **{k: v for k, v in outcome.items() if k != "status"},
    )


def _finish_invalid_submissions(config, store, budget):
    status = "invalid_submission_limit"
    recovery = store.get("submission_recovery") or {}
    store.set("status", status)
    report = {
        "status": "no_recommendation",
        "run_status": status,
        "valid": True,
        "reason_code": status,
        "reason": "exploration stopped after three consecutive invalid submission turns",
        "submission_recovery": recovery,
    }
    if not store.get("test_entitlement"):
        try:
            identity = store.put("report", report)
        except AgentError:
            store.set("invalid_submission_report", report)
        else:
            store.set_many({"report": identity}, delete=("invalid_submission_report",))
    return _run_result(config, store, budget, None, status, submission_recovery=recovery)


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
    require_capabilities(backend, study=True)
    system = SYSTEM + "\nSelected profile:\n" + json.dumps(backend.runtime_profile.describe())
    with store.lease("run"):
        clean_sandboxes(store)
        budget = Budget(store, config.model)
        budget.recover()
        read_guidance(store)
        if store.get("frozen"):
            return _run_result(config, store, budget, Study(config, store, backend), "frozen")
        if store.get("status") == "invalid_submission_limit":
            return _finish_invalid_submissions(config, store, budget)
        if resume and store.get("status") == "budget_exhausted":
            return _finish_exhaustion(config, store, backend, budget)
        saved = store.get("trajectory") if resume else None
        trajectory = store.read(saved) if saved else None
        study = Study(config, store, backend)
        tools = Tools(study, budget, turn_limit=step_limit)
        if tools.experiments.required and not resume and store.get("trajectory"):
            raise AgentError("research conversation already exists; use resume or a new run")
        if resume:
            tools.experiments.recover()
        initial_context = tools.startup_context() if trajectory is None else None
        startup_metadata = (
            {"startup_context_version": 1}
            if trajectory is None
            else {k: trajectory[k] for k in ("startup_context_version",) if k in trajectory}
        )
        if tools.experiments.required:
            # Existing trajectories retain their original orientation and pacing protocol.
            if trajectory is None:
                startup_metadata["workflow_protocol_version"] = 2
            elif "workflow_protocol_version" in trajectory:
                startup_metadata["workflow_protocol_version"] = trajectory[
                    "workflow_protocol_version"
                ]
            if trajectory is not None:
                if trajectory.get("research_protocol_version") != 1:
                    raise AgentError("unsupported saved research trajectory protocol")
                system = trajectory["messages"][0]["content"]
            else:
                system += system_guidance(store)
            startup_metadata.update(pin_prompt(store, system))
            if trajectory is not None and any(
                trajectory.get(key) != value
                for key, value in startup_metadata.items()
                if key.startswith("research_")
            ):
                raise AgentError("saved research trajectory identity changed")
            if trajectory is None:
                check_initial_bound(config.model, system, initial_context)
        checkpoint_notice = (
            trajectory is not None and "checkpoint_protocol_version" not in trajectory
        )
        startup_metadata["checkpoint_protocol_version"] = 1
        recovery_notice = trajectory is not None and "recovery_protocol_version" not in trajectory
        startup_metadata["recovery_protocol_version"] = 1
        recovery = dict(
            (trajectory or {}).get("submission_recovery")
            or {
                "consecutive_invalid_turns": 0,
                "last_error": None,
            }
        )
        if recovery["consecutive_invalid_turns"] >= MAX_CONSECUTIVE_INVALID_TURNS:
            store.set("submission_recovery", recovery)
            return _finish_invalid_submissions(config, store, budget)
        startup_metadata["submission_recovery"] = recovery
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
                command("calibrate", {"policy": good, "checkpoint": True}),
                command("submit", {"policy": good}),
            ]
            if tools.experiments.required:
                saved_actions = store.get("research_scripted_actions")
                actions = saved_actions or []
                for key, operation, args, purpose in (
                    ()
                    if saved_actions
                    else (
                        ("initial-probe", "probe", {"query": first}, "investigation"),
                        ("premature-calibration", "calibrate", {"policy": bad}, "calibration"),
                        (
                            "profile-calibration",
                            "calibrate",
                            {"policy": good, "checkpoint": True},
                            "calibration",
                        ),
                    )
                ):
                    actions.extend(
                        [
                            command(
                                "experiment",
                                {"action": "start", "plan": scripted_plan(key, purpose)},
                            ),
                            command(operation, args),
                            command(
                                "experiment",
                                {
                                    "action": "finish",
                                    "client_key": key,
                                    "conclusion": scripted_conclusion(),
                                },
                            ),
                        ]
                    )
                if not saved_actions:
                    actions.append(command("submit", {"policy": good}))
                    store.set("research_scripted_actions", actions)
            if trajectory is not None and "startup_context_version" not in trajectory:
                actions.insert(0, command("inspect", {}))
            model = ScriptedModel(actions)
            context = nullcontext()
        else:
            model = BudgetedModel(config.model, budget)
            private = store.root / "private"
            private.mkdir(parents=True, exist_ok=True)
            context = FileBroker(tools, store.root / "workspace" / ".broker")
        with context as broker, ExitStack() as resources:
            env = (
                ScriptedEnvironment(tools)
                if scripted
                else ContainerEnvironment(store.root / "workspace", broker)
            )
            if not scripted:
                resources.callback(env.close)
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
                if checkpoint_notice:
                    agent.add_messages(
                        model.format_message(role="user", content=CHECKPOINT_GUIDANCE)
                    )
                if recovery_notice:
                    agent.add_messages(
                        model.format_message(role="user", content=CORRECTION_GUIDANCE)
                    )
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
                if trajectory is None or checkpoint_notice or recovery_notice:
                    store.set(
                        "trajectory", store.put("trajectory", agent.serialize(startup_metadata))
                    )
                while agent.n_calls < step_limit:
                    if startup_metadata.get("workflow_protocol_version") in {1, 2} and agent.n_calls:
                        notice = workflow_notice(tools, step_limit, agent.n_calls)
                        agent.add_messages(
                            model.format_message(
                                role="user",
                                content="Study workflow progress:\n" + json.dumps(notice),
                            )
                        )
                        store.set(
                            "trajectory", store.put("trajectory", agent.serialize(startup_metadata))
                        )
                    turn_id = tools.submissions.begin_turn()
                    env.turn_id = turn_id
                    try:
                        agent.step()
                    except FormatError as exc:
                        agent.add_messages(*exc.messages)
                        extra = exc.messages[0].get("extra", {})
                        # DefaultAgent.query never receives the billed malformed response.
                        agent.cost += extra.get("cost", 0.0)
                        info = (
                            extra.get("error_info")
                            or InvalidSubmission(
                                "invalid_tool_call", "model response was improperly formatted"
                            ).info
                        )
                        tools.submissions.record(turn_id, error=info, success=False)
                    except InterruptAgentFlow as exc:
                        agent.add_messages(*exc.messages)
                        status = "no_recommendation"
                        break
                    finally:
                        invalid, successful = tools.submissions.finish_turn()
                        if invalid is not None:
                            recovery["consecutive_invalid_turns"] += 1
                            recovery["last_error"] = invalid
                        elif successful:
                            recovery["consecutive_invalid_turns"] = 0
                        if recovery[
                            "consecutive_invalid_turns"
                        ] >= MAX_CONSECUTIVE_INVALID_TURNS and not store.get("frozen"):
                            status = "invalid_submission_limit"
                            # Persist a small terminal outcome even if evidence storage is full.
                            store.set_many({"status": status, "submission_recovery": recovery})
                        store.set_many(
                            {
                                "trajectory": store.put(
                                    "trajectory", agent.serialize(startup_metadata)
                                ),
                                "submission_recovery": recovery,
                            }
                        )
                    if store.get("frozen"):
                        status = "frozen"
                        break
                    if status == "invalid_submission_limit":
                        break
                    if scripted and model.index >= len(model.actions):
                        status = "no_recommendation"
                        break
            except BudgetExceeded:
                status = "budget_exhausted"
            finally:
                try:
                    if not scripted:
                        resources.close()
                except Exception:
                    status = "interrupted"
                    raise
                finally:
                    if store.get("frozen"):
                        status = "frozen"
                    store.set("status", status)
                    if status in {"budget_exhausted", "invalid_submission_limit"}:
                        _save_exhausted_ledger(store, budget)
                    else:
                        store.set("ledger", store.put("ledger", budget.summary()))
        # The broker is joined and the sandbox stopped before trusted finalization.
        tools.experiments.interrupt(status, terminal=status != "interrupted")
        if status == "budget_exhausted":
            return _finish_exhaustion(config, store, backend, budget, study)
        if status == "invalid_submission_limit":
            return _finish_invalid_submissions(config, store, budget)
        if status == "no_recommendation" and not store.get("test_entitlement"):
            store.set(
                "report",
                store.put(
                    "report",
                    {
                        "status": "no_recommendation",
                        "run_status": status,
                        "valid": True,
                        "reason": "no candidate submitted",
                        "simulated": bool(backend.inspect_target().get("simulated")),
                    },
                ),
            )
        return _run_result(config, store, budget, study, status)
