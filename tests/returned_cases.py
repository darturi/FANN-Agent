"""Independent, small raw-result archives for returned-feedback contract tests."""

import hashlib
import json
import math
import tarfile
from collections import defaultdict

import numpy as np
from test_learning_import import package_fixture, repin, save

from fannagent.api import FeatureDefinition, validate_policy
from fannagent.learning.returned import source_arms
from fannagent.store import digest


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def reference_summary(rows, config):
    # Independent matrix bootstrap, matching the sealed experiment's definition.
    groups = defaultdict(list)
    for r in rows:
        groups[r["group"]].append(r)
    matrix = np.asarray(
        [
            [
                np.mean([r["policy_ms"] - r["native_ms"] for r in rs]),
                np.mean([r["policy_outer_ms"] - r["native_outer_ms"] for r in rs]),
                np.mean([r["recall_delta"] for r in rs]),
                np.mean([math.log(r["policy_ms"] / r["native_ms"]) for r in rs]),
            ]
            for rs in groups.values()
        ]
    )
    rng = np.random.default_rng(config["seed"])
    boot = matrix[
        rng.integers(0, len(matrix), size=(config["bootstrap_samples"], len(matrix)))
    ].mean(1)
    ci = np.quantile(boot, [0.025, 0.975], axis=0)

    def mean(key):
        return float(np.mean([r[key] for r in rows]))

    return {
        "pairs": len(rows),
        "independent_vectors": len(groups),
        "native_ms": mean("native_ms"),
        "policy_ms": mean("policy_ms"),
        "gap_ms": float(matrix[:, 0].mean()),
        "gap_ci95": ci[:, 0].tolist(),
        "outer_gap_ms": float(matrix[:, 1].mean()),
        "outer_gap_ci95": ci[:, 1].tolist(),
        "recall_delta": float(matrix[:, 2].mean()),
        "recall_delta_ci95": ci[:, 2].tolist(),
        "log_latency_ratio_ci95": ci[:, 3].tolist(),
        "native_recall": mean("native_recall"),
        "policy_recall": mean("policy_recall"),
        "returned_count": mean("returned_count"),
        "collection_ms": 0.0,
        "layer0_distances": float(
            np.mean([r["work"]["layer0_distance_evaluations"] for r in rows])
        ),
        "all_valid": all(r["valid"] for r in rows),
        "recall_noninferior": bool(ci[0, 2] >= -config["recall_tolerance"]),
        "latency_improved": bool(ci[1, 3] < 0),
    }


def reference_filters(rows, config):
    return {
        "overall": reference_summary(rows, config),
        "per_filter": {
            f: reference_summary([r for r in rows if r["stratum"] == f], config)
            for f in config["filters"]
        },
    }


def seal(campaign, verification):
    analysis = campaign / "analysis"
    raw = {
        str(p.relative_to(campaign)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (campaign / "blocks").rglob("*")
        if p.is_file()
    }
    old = json.loads((analysis / "verification.json").read_text())
    save(analysis / "verification.json", {**old, "raw_files_sha256": raw})
    receipt = json.loads((analysis / "feedback-receipt.json").read_text())
    for name, field in [
        ("training-feedback.jsonl", "training_feedback_sha256"),
        ("performance.json", "performance_sha256"),
        ("verification.json", "verification_sha256"),
    ]:
        receipt[field] = hashlib.sha256((analysis / name).read_bytes()).hexdigest()
    save(analysis / "feedback-receipt.json", receipt)
    archives = {}
    for feedback in (False, True):
        path = campaign.parent / (campaign.name + ("-feedback" if feedback else "") + ".tar.gz")
        with tarfile.open(path, "w:gz") as tar:
            paths = sorted(analysis.iterdir()) if feedback else sorted(campaign.rglob("*"))
            for p in paths:
                if p.is_file():
                    tar.add(
                        p,
                        arcname="feedback/" + p.name
                        if feedback
                        else campaign.name + "/" + str(p.relative_to(campaign)),
                        recursive=False,
                    )
        archives[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    save(
        verification,
        {
            "status": "verified",
            "provider_calls": 0,
            "confirmation_queries": 0,
            "source_archive_sha256": archives,
        },
    )


def returned_fixture(tmp_path):
    package, profile = package_fixture(tmp_path, groups=30)
    config = json.loads((package / "experiment.json").read_text())
    config.update(
        blocks=2,
        cold_passes=1,
        warmups=1,
        warm_passes=2,
        maximum_new_labels_per_query=10,
        row_count=100,
        optimized_module_sha256="1" * 64,
        image_sha256="2" * 64,
        frozen_query_method_sha256="3" * 64,
    )
    save(package / "experiment.json", config)
    raw_profile = profile.model_dump()
    for name in ("checkpoint_index", "predicate_leaf_count"):
        raw_profile["features"][name] = FeatureDefinition(name=name, kind="int").model_dump()
    profile = type(profile).model_validate(raw_profile)
    original = [
        json.loads(s)
        for s in (package / "inputs/training-640-light.jsonl").read_text().splitlines()
    ]
    for r in original:
        for state in r["states"]:
            state["features"].update(
                checkpoint_index=state["checkpoint_index"],
                predicate_leaf_count=int(r["query_id"].endswith("-filtered")),
            )
    jsonl(package / "inputs/training-640-light.jsonl", original)
    names = list(original[0]["states"][0]["features"])
    receipt = json.loads((package / "inputs/original-learning-receipt.json").read_text())
    receipt["qualified_features"]["640/light"] = names
    save(package / "inputs/original-learning-receipt.json", receipt)
    budget = {
        "shared_ledger": "/original/campaign/state.sqlite3",
        "original_ceiling_usd": "15",
        "committed_usd": "3.174666",
        "remaining_usd": "11.825334",
        "provider_attempts": 42,
    }
    save(package / "inputs/budget-receipt.json", budget)
    qq = [json.loads(s) for s in (package / "inputs/queries.jsonl").read_text().splitlines()]
    for r in qq:
        r["query"]["filter"] = (
            {"field": "m_000000", "op": "gte", "value": 32}
            if r["query"]["id"].endswith("-filtered")
            else None
        )
    jsonl(package / "inputs/queries.jsonl", qq)
    policy = {
        "name": "source",
        "feature_groups": ["basic"],
        "root": {
            "if": {"op": "gte", "args": [{"feature": "layer0_distance_evaluations"}, {"int": 30}]},
            "then": "stop",
            "else": "continue",
        },
    }
    candidates = [
        {
            "id": "source",
            "policy": policy,
            "policy_hash": validate_policy(policy, profile).policy_hash,
            "predicted_checkpoints": {r["query_id"]: 3 for r in original},
        }
    ]
    save(
        package / "inputs/candidates.json",
        {
            "feature_pool": names,
            "training_view_sha256": hashlib.sha256(
                (package / "inputs/training-640-light.jsonl").read_bytes()
            ).hexdigest(),
            "candidates": candidates,
        },
    )
    repin(package)
    manifest_hash = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    updated = []
    acquired = []
    for r in original:
        label = {
            "checkpoint_index": 2,
            "recall": 0.8,
            "returned_count": 10,
            "valid": True,
            "actual_work": 20,
            "prefix_matches": True,
            "reference_prefix_sha256": digest(r["states"][:2]),
            "preserves_default": False,
            "label_origin": "safe_boundary_refinement",
        }
        updated.append(
            {
                **r,
                "labels": sorted([*r["labels"], label], key=lambda v: v["checkpoint_index"]),
                "new_actual_labels": 1,
            }
        )
        acquired.append({"query_id": r["query_id"], "group": r["group"], "ef_search": 640, **label})
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    arms = source_arms(candidates, original, profile, ["basic"])
    all_rows = []
    per_block = {}
    for b in range(2):
        folder = campaign / "blocks" / ("block-" + str(b))
        folder.mkdir(parents=True)
        jsonl(folder / "training-updated.jsonl", updated)
        jsonl(folder / "new-labels.jsonl", acquired)
        save(
            folder / "status.json",
            {
                "status": "complete",
                "provider_calls": 0,
                "confirmation_queries": 0,
                "candidate_lock": False,
                "canonical_acceptance_established": False,
                "retained_pairs": len(original) * len(arms) * 3,
            },
        )
        save(
            folder / "job-exit.json",
            {
                "exit_code": 0,
                "completed_runs_unchanged": True,
                "confirmation_inputs_unchanged": True,
                "slurm_job_id": str(100 + b),
            },
        )
        save(folder / "protected-source-before.json", {})
        save(folder / "protected-source-after.json", {})
        save(
            folder / "runtime-identity.json",
            {
                "package_manifest_sha256": manifest_hash,
                "query_file_sha256": hashlib.sha256(
                    (package / "inputs/queries.jsonl").read_bytes()
                ).hexdigest(),
                "candidate_file_sha256": hashlib.sha256(
                    (package / "inputs/candidates.json").read_bytes()
                ).hexdigest(),
                "runtime_profile_hash": profile.fingerprint,
                "module_sha256": "1" * 64,
                "image_sha256": "2" * 64,
                "frozen_query_method_sha256": "3" * 64,
            },
        )
        save(folder / "database-identity.json", {"row_count": 100})
        save(folder / "settings.json", {"hnsw.ef_search": "640"})
        save(folder / "qualified-features.json", {"qualified_features": names})
        rows = []
        for r in original:
            for arm in arms:
                stopped = arm.kind in ("candidate", "oracle")
                h = (
                    arm.per_query_policy_hashes[r["query_id"]]
                    if arm.kind == "oracle"
                    else validate_policy(arm.policy, profile).policy_hash
                )
                for regime, passes in [("activation-cold", 1), ("reused-warm", 2)]:
                    for rep in range(passes):
                        rows.append(
                            {
                                "block": b,
                                "ef_search": 640,
                                "tier": "light",
                                "arm": arm.arm,
                                "kind": arm.kind,
                                "regime": regime,
                                "repetition": rep,
                                "query_id": r["query_id"],
                                "group": r["query_id"].rsplit("-", 1)[0],
                                "stratum": r["query_id"].rsplit("-", 1)[1],
                                "policy_hash": h,
                                "order": ["native", "policy"],
                                "policy_already_activated": regime == "reused-warm",
                                "native_ms": 2.0,
                                "policy_ms": 1.0 if stopped else 2.2,
                                "native_outer_ms": 2.1,
                                "policy_outer_ms": 1.1 if stopped else 2.3,
                                "native_recall": 1.0,
                                "policy_recall": 1.0,
                                "recall_delta": 0.0,
                                "valid": True,
                                "returned_count": 10,
                                "checkpoint_count": 3,
                                "stop_reason": "policy_stop" if stopped else "native_limit",
                                "work": {
                                    "layer0_distance_evaluations": 30 if stopped else 40,
                                    "feature_collection_ns": 0,
                                    "frontier_snapshot_count": 0,
                                    "frontier_sort_count": 0,
                                    "frontier_traversal_ns": 0,
                                    "frontier_statistics_ns": 0,
                                    "frontier_sort_ns": 0,
                                    "frontier_quantile_ns": 0,
                                },
                                **{
                                    m + "_" + key: value
                                    for m in ("native", "policy")
                                    for key, value in [
                                        ("ids", list(range(1, 11))),
                                        ("distances", [float(i) for i in range(10)]),
                                    ]
                                },
                                "truth_strict": list(range(1, 10)),
                                "truth_ties": [10],
                                "truth_k": 10,
                            }
                        )
        jsonl(folder / "pairs.jsonl", rows)
        all_rows += rows
        per_block[str(b)] = {
            a.arm: {
                reg: reference_filters(
                    [r for r in rows if r["arm"] == a.arm and r["regime"] == reg], config
                )
                for reg in ("activation-cold", "reused-warm")
            }
            for a in arms
        }
        save(folder / "summary.json", per_block[str(b)])
    overall = {
        a.arm: {
            reg: reference_filters(
                [r for r in all_rows if r["arm"] == a.arm and r["regime"] == reg], config
            )
            for reg in ("activation-cold", "reused-warm")
        }
        for a in arms
    }
    save(
        campaign / "analysis/performance.json",
        {
            "provider_calls": 0,
            "confirmation_queries": 0,
            "candidate_lock": False,
            "retained_pairs": len(all_rows),
            "overall": overall,
            "per_block": per_block,
            "candidates": {
                "source": {
                    reg: {"training_feasible": True, "report": rr}
                    for reg, rr in overall["source"].items()
                }
            },
        },
    )
    jsonl(campaign / "analysis/training-feedback.jsonl", updated)
    save(
        campaign / "analysis/verification.json",
        {
            "status": "verified",
            "provider_calls": 0,
            "confirmation_queries": 0,
            "original_labels_preserved": True,
            "new_actual_labels": len(original),
            "retained_pairs": len(all_rows),
        },
    )
    save(
        campaign / "analysis/feedback-receipt.json",
        {
            "package_manifest_sha256": manifest_hash,
            "original_learning_receipt_sha256": hashlib.sha256(
                (package / "inputs/original-learning-receipt.json").read_bytes()
            ).hexdigest(),
            "budget_receipt": budget,
            "ef_search": 640,
            "tier": "light",
            "qualified_features": names,
            "training_queries": len(original),
            "training_groups": 30,
            "confirmation_outcomes_exported": False,
            "query_vectors_exported": False,
            "candidate_lock": False,
            "provider_calls": 0,
        },
    )
    verification = tmp_path / "local-verification.json"
    seal(campaign, verification)
    return package, campaign, verification, profile
