"""Paired clean-start development benchmark with a scripted baseline."""

import uuid
from collections import defaultdict
from pathlib import Path

from fannagent.api.broad_policy import FEATURES

from .core import digest, read, write
from .search import qualified, quality_ok

DEFAULT_CHECKPOINTS = (1, 2, 4, 8, 16, 32, 64)
DEFAULT_FEATURES = ("qualifying_count", "frontier_distance", "frontier_gap")
REVISION_MODE = "agent_revision"


def vector_id(vector):
    return digest([float(value) or 0.0 for value in vector])


def prepare_design(plan, cases):
    keys = {"arm", "seed", "initial_groups", "followup_groups", "screen_groups"}
    if not isinstance(plan, dict) or set(plan) - {"mode"} != keys:
        raise ValueError("comparison design requires arm, seed and three group counts")
    if plan["arm"] not in ("scripted", "agent") or type(plan["seed"]) is not int:
        raise ValueError("comparison arm must be scripted or agent, with an integer seed")
    if "mode" in plan and (
        plan["mode"] != REVISION_MODE or plan["arm"] != "agent" or plan["followup_groups"] != 0
    ):
        raise ValueError("agent revision requires the agent arm and no scripted follow-up sample")
    for name in ("initial_groups", "followup_groups", "screen_groups"):
        minimum = 0 if name == "followup_groups" else 2
        if type(plan[name]) is not int or plan[name] < minimum:
            raise ValueError("invalid comparison group count: " + name)
    if plan["screen_groups"] > 73:
        raise ValueError("the native screen admits at most 73 complete seven-condition groups")
    roles = {}
    vectors = {}
    for case in cases:
        group, role = case["group"], case["role"]
        if group in roles:
            continue
        identity = vector_id(case["vector"])
        if identity in vectors and vectors[identity] != group:
            raise ValueError("identical vectors must belong to one group")
        vectors[identity] = group
        roles[group] = (role, identity)
    ndev = sum(role == "development" for role, _ in roles.values())
    if plan["initial_groups"] + plan["followup_groups"] + plan["screen_groups"] > ndev:
        raise ValueError("comparison sample sizes exceed the development groups")
    if sum(role == "test" for role, _ in roles.values()) < 2:
        raise ValueError("the experiment requires a protected test panel")
    return {
        **plan,
        "cohort_sha256": digest(roles),
        "bootstrap_checkpoints": list(DEFAULT_CHECKPOINTS),
        "bootstrap_features": list(DEFAULT_FEATURES),
    }


def panels(root, plan):
    grouped = defaultdict(list)
    for query in read(Path(root) / "agent/task.json")["queries"]:
        grouped[query["group"]].append(query["handle"])
    ordered = sorted(grouped, key=lambda key: digest([plan["seed"], "panel", key]))
    initial = plan["initial_groups"]
    followup = initial + plan["followup_groups"]
    screen = plan["screen_groups"]
    slices = (ordered[:initial], ordered[initial:followup], ordered[-screen:])
    return [[h for group in groups for h in sorted(grouped[group])] for groups in slices]


def batches(handles):
    # The native acquisition tool admits at most 512 cases, or 73 whole vector groups.
    for i in range(0, len(handles), 511):
        yield handles[i : i + 511]


def dispatch(controller, name, /, **args):
    controller.client.call("heartbeat")
    answer = controller.call(uuid.uuid4().hex, name, args)
    if "error" in answer or answer.get("fit_failed"):
        raise ValueError(f"{name}: {answer.get('error', answer.get('output'))}")
    controller.client.call("heartbeat")
    return answer


def acquire(controller, handles, plan):
    for subset in batches(handles):
        dispatch(
            controller,
            "acquire",
            handles=subset,
            checkpoints=plan["bootstrap_checkpoints"],
            features=plan["bootstrap_features"],
        )


def bootstrap(controller, plan):
    initial, _, screen = panels(controller.root, plan)
    dispatch(
        controller,
        "plan_search",
        plan="Collect the common clean-start panel across all filters. "
        "Fit candidates on fresh observations, screen on unused vector groups, "
        "and reserve enough queries for strict native confirmation.",
    )
    acquire(controller, initial, plan)
    return {
        "initial_handles_sha256": digest(initial),
        "screen_handles": screen,
        "initial_groups": plan["initial_groups"],
    }


def run_scripted(root, client):
    from .controller import Controller, empty_policy

    root = Path(root)
    plan = read(root / "config.json").get("comparison")
    if not plan or plan["arm"] != "scripted":
        raise ValueError("scripted runner requires its own sealed comparison arm")
    worker = client.status()
    if (
        worker.get("status") != "running"
        or worker.get("run_id") != read(root / "config.json")["run_id"]
    ):
        raise ValueError("scripted runner requires its matching fresh worker")
    controller = Controller(root, client)
    start = bootstrap(controller, plan)
    _, followup, screen = panels(root, plan)
    acquire(controller, followup, plan)
    portfolio = dispatch(
        controller,
        "fit_batch",
        name="scripted",
        checkpoints=plan["bootstrap_checkpoints"],
        features=plan["bootstrap_features"],
    )["candidates"]
    eligible_portfolio = [
        r
        for r in portfolio
        if r["all"]["stops"] and not (r["all"]["recall_losses"] or r["all"]["count_losses"])
    ]
    learned = next((r for r in eligible_portfolio if not r["name"].startswith("fixed-")), None)
    shortlist = eligible_portfolio[:4]
    if learned and learned not in shortlist:
        shortlist = [*shortlist[:3], learned]
    candidate_id = None
    reason = "No portfolio candidate passed first-stop replay and controlled native screening."
    if shortlist:
        screened = dispatch(
            controller,
            "evaluate",
            policy_paths=[r["policy_path"] for r in shortlist],
            handles=screen,
        )
        eligible = []
        for i, identity in enumerate(screened["candidate_ids"]):
            family = f"candidate:{i}"
            result = controller.state["candidates"][identity]["screen_result"]
            if quality_ok(result, family) and result["timing"]["controls_pass"]:
                estimate = result["timing"]["families"][family]
                for_native = estimate["all"].get("ci95", [0, 2])[1]
                for_matched = estimate["matched"].get("ci95", [0, 2])[1]
                if max(for_native, for_matched) < 1:
                    eligible.append((for_native, identity))
        if eligible:
            _, nominee = min(eligible)
            dispatch(controller, "confirm", candidate_id=nominee)
            if qualified(controller.state["candidates"][nominee]["confirmation"], "candidate:0"):
                candidate_id = nominee
                reason = "The best eligible screen passed full strict native confirmation."
            else:
                reason = "The selected screen failed full strict native confirmation."

    policy = (
        controller.state["candidates"][candidate_id]["policy"] if candidate_id else empty_policy()
    )
    disposition = {
        "status": "policy_frozen" if candidate_id else "abstained",
        "candidate_id": candidate_id,
        "reason": reason,
    }
    controller.state["terminal"] = disposition
    write(controller.path, controller.state)
    freeze = {
        "run_id": controller.run_id,
        "policy": policy,
        "disposition": disposition,
        "test_feedback_seen": False,
    }
    write(root / "host/freeze.json", freeze)
    result = {
        "run_id": controller.run_id,
        "status": disposition["status"],
        "model_closed": True,
        "freeze_sha256": digest(freeze),
        "model_charged_usd": "0",
        **start,
    }
    write(root / "host/model-closed.json", result)
    return result


def check_portfolio(checkpoints, features):
    if not 1 <= len(checkpoints) <= 12 or checkpoints != sorted(set(checkpoints)):
        raise ValueError("supply up to twelve sorted distinct checkpoints")
    if (
        any(not 1 <= c <= 4096 for c in checkpoints)
        or not features
        or not set(features) <= set(FEATURES)
    ):
        raise ValueError("choose legal checkpoints and causal features")


def compare_reports(reports):
    by_seed = defaultdict(dict)
    used = set()
    cohort = None
    for result in reports:
        metadata = result["comparison"]
        seed, arm = metadata["seed"], metadata["arm"]
        if cohort is None:
            cohort = metadata["cohort_sha256"]
        if cohort != metadata["cohort_sha256"]:
            raise ValueError("all seeds must use the same static queries and split")
        if (
            arm not in ("scripted", "agent")
            or arm in by_seed[seed]
            or result["run_id"] in used
            or not metadata["initial_handles_sha256"]
            or result.get("test_feedback_returned_to_agent") is not False
            or result["accounting"]["unsettled_requests"]
        ):
            raise ValueError("comparison requires distinct settled runs and a shared initial panel")
        by_seed[seed][arm] = result
        used.add(result["run_id"])
    seeds = []
    for seed, arms in sorted(by_seed.items()):
        if set(arms) != {"scripted", "agent"}:
            raise ValueError(f"seed {seed} requires both finalized arms")
        excluded = {"arm", "model_calls", "model_charged_usd"}
        identities = [
            {k: v for k, v in result["comparison"].items() if k not in excluded}
            for result in arms.values()
        ]
        if identities[0] != identities[1]:
            raise ValueError(
                f"seed {seed} arms differ in dataset, software, initial panel or limits"
            )
        outcome = {}
        for arm, result in arms.items():
            metadata = result["comparison"]
            held_out = result["cohorts"]["held_out"]
            timing = held_out["timing"]
            outcome[arm] = {
                "run_id": result["run_id"],
                "status": result["agent_disposition"]["status"],
                "quality": held_out["quality"]["candidate:0"],
                "controls_pass": timing["controls_pass"],
                "timing": timing["families"]["candidate:0"]["all"],
                "qualified": held_out["qualified_agent_win"],
                "discovery_queries": result["accounting"]["discovery_queries"],
                "model_calls": metadata["model_calls"],
                "model_charged_usd": metadata["model_charged_usd"],
            }
        seeds.append({"seed": seed, **outcome})
    return {
        "schema": "fannagent.paired-clean-start.v1",
        "pair_count": len(seeds),
        "qualified_runs": {
            arm: sum(p[arm]["qualified"] for p in seeds) for arm in ("scripted", "agent")
        },
        "pairs": seeds,
    }
