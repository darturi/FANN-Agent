"""Verify returned Torch files as data. Never execute a campaign's source code."""

from __future__ import annotations

import hashlib
import math
import tarfile
from pathlib import Path, PurePosixPath

from ..api import AgentError, RuntimeProfile, validate_policy
from ..store import digest
from .files import decode, read_bytes
from .importers import import_torch_training
from .models import StopOutcome, TimingSchedule, TrainingQuery
from .returned_models import BenchmarkArm, BenchmarkEvidence, BenchmarkPair, ReturnedFeedback
from .statistics import compare_numeric, feasible, with_filters

REGIMES = ("activation-cold", "reused-warm")


def require(condition, message):
    if not condition:
        raise AgentError(message)


def read_under(root: Path, name: str) -> bytes:
    path = PurePosixPath(name)
    require(
        not path.is_absolute() and ".." not in path.parts and str(path) == name,
        "unsafe evidence path",
    )
    target = root
    for part in path.parts:
        target = target / part
        require(not target.is_symlink(), "evidence path contains a symbolic link")
    return read_bytes(target)


def _sha(content):
    return hashlib.sha256(content).hexdigest()


def verify_archives(campaign: Path, verification: Path) -> dict[str, str]:
    record = decode(read_bytes(verification))
    require(
        record.get("status") == "verified"
        and record.get("confirmation_queries") == 0
        and record.get("provider_calls") == 0,
        "verification is not training-only",
    )
    expected = record["source_archive_sha256"]
    names = {campaign.name + ".tar.gz", campaign.name + "-feedback.tar.gz"}
    require(set(expected) == names, "source archive inventory differs")
    file_hashes = {}
    for filename in sorted(names):
        archive = campaign.parent / filename
        require(_sha(read_bytes(archive)) == expected[filename], "source archive checksum differs")
        feedback = filename.endswith("-feedback.tar.gz")
        seen = set()
        total = 0
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar:
                path = PurePosixPath(member.name)
                require(
                    member.isfile()
                    and not path.is_absolute()
                    and ".." not in path.parts
                    and member.name not in seen
                    and member.size <= 128 * 2**20,
                    "unsafe or oversized returned archive member",
                )
                seen.add(member.name)
                total += member.size
                require(
                    len(seen) <= 256 and total <= 512 * 2**20, "returned archive exceeds bounds"
                )
                if feedback:
                    require(
                        member.name
                        in {
                            "feedback/" + n
                            for n in (
                                "training-feedback.jsonl",
                                "feedback-receipt.json",
                                "performance.json",
                                "verification.json",
                            )
                        },
                        "unexpected feedback archive member",
                    )
                    relative = "analysis/" + path.name
                else:
                    require(
                        path.parts[0] == campaign.name and len(path.parts) > 1,
                        "full archive root differs",
                    )
                    relative = str(PurePosixPath(*path.parts[1:]))
                stream = tar.extractfile(member)
                require(stream is not None, "archive member has no regular content")
                assert stream is not None
                member_hash = hashlib.sha256()
                while chunk := stream.read(2**20):
                    member_hash.update(chunk)
                actual = member_hash.hexdigest()
                require(
                    _sha(read_under(campaign, relative)) == actual,
                    "extracted returned file differs from its source archive",
                )
                if not feedback:
                    file_hashes[relative] = actual
            require(not feedback or len(seen) == 4, "incomplete feedback archive")
    file_hashes["local-verification.json"] = _sha(read_bytes(verification))
    file_hashes.update({"archive/" + k: v for k, v in expected.items()})
    return file_hashes


def _stop(name, groups, ordinal=None):
    root = (
        "continue"
        if ordinal is None
        else {
            "if": {"op": "gte", "args": [{"feature": "checkpoint_index"}, {"int": ordinal}]},
            "then": "stop",
            "else": "continue",
        }
    )
    return {"name": name, "feature_groups": groups, "root": root}


def _matched(raw):
    def replace(node):
        return (
            "continue"
            if isinstance(node, str)
            else {"if": node["if"], "then": replace(node["then"]), "else": replace(node["else"])}
        )

    return {
        "name": "matched-continue-" + raw["name"],
        "root": replace(raw["root"]),
        "feature_groups": raw["feature_groups"],
    }


def source_arms(candidates, original, profile, groups):
    arms = []
    for candidate in candidates:
        arms.extend(
            [
                BenchmarkArm(arm=candidate["id"], kind="candidate", policy=candidate["policy"]),
                BenchmarkArm(
                    arm="matched-" + candidate["id"],
                    kind="matched-continue",
                    policy=_matched(candidate["policy"]),
                    matched_candidate=candidate["id"],
                ),
            ]
        )
    arms.append(
        BenchmarkArm(
            arm="continue-light", kind="continue", policy=_stop("feedback-continue", groups)
        )
    )
    for work in (4096, 8192):
        arms.append(
            BenchmarkArm(
                arm="fixed-" + str(work),
                kind="fixed",
                policy={
                    "name": "feedback-fixed-" + str(work),
                    "feature_groups": groups,
                    "root": {
                        "if": {
                            "op": "gte",
                            "args": [{"feature": "layer0_distance_evaluations"}, {"int": work}],
                        },
                        "then": "stop",
                        "else": "continue",
                    },
                },
            )
        )
    arms.append(
        BenchmarkArm(
            arm="oracle-original",
            kind="oracle",
            per_query_policy_hashes={
                row["query_id"]: validate_policy(
                    _stop("feedback-oracle-original", groups, row["oracle_checkpoint"]), profile
                ).policy_hash
                for row in original
            },
        )
    )
    return arms


def _validate_result(row, query):
    require(
        row["order"] in (["native", "policy"], ["policy", "native"]), "invalid measurement ordering"
    )
    require(row["truth_k"] == query.effective_k, "exact reference effective k differs")
    strict, ties = set(row["truth_strict"]), set(row["truth_ties"])
    require(
        not strict & ties and len(strict) <= query.effective_k, "invalid exact reference boundary"
    )
    for mode in ("native", "policy"):
        ids, distances = row[mode + "_ids"], row[mode + "_distances"]
        require(
            len(ids) == len(set(ids)) == len(distances)
            and len(ids) <= query.effective_k
            and all(type(d) in (int, float) and math.isfinite(d) for d in distances),
            "invalid measured result",
        )
        recall = (
            len(set(ids) & strict) + min(query.effective_k - len(strict), len(set(ids) & ties))
        ) / query.effective_k
        require(
            abs(recall - row[mode + "_recall"]) <= 1e-12, "result-based recall does not reproduce"
        )
    require(
        len(row["native_ids"]) == query.effective_k
        and row["returned_count"] == len(row["policy_ids"])
        and type(row["valid"]) is bool
        and row["valid"] == (row["returned_count"] == query.effective_k)
        and abs(row["recall_delta"] - (row["policy_recall"] - row["native_recall"])) <= 1e-12,
        "measured completeness or recall delta differs",
    )


def _import_feedback(package, campaign, verification, profile):
    package, campaign = package.resolve(), campaign.resolve()
    base = import_torch_training(package, profile)
    files = verify_archives(campaign, verification)

    def read(relative):
        content = read_under(campaign, relative)
        require(_sha(content) == files.get(relative), "returned source changed during import")
        return decode(content)

    def lines(relative):
        content = read_under(campaign, relative)
        require(_sha(content) == files.get(relative), "returned source changed during import")
        return [decode(line) for line in content.splitlines()]

    def source(relative):
        content = read_under(package, relative)
        require(_sha(content) == base.source_hashes[relative], "original source changed")
        return decode(content)

    config = source("experiment.json")
    receipt = read("analysis/feedback-receipt.json")
    raw_verification = read("analysis/verification.json")
    saved = read("analysis/performance.json")
    require(
        receipt["package_manifest_sha256"] == base.source_hashes["manifest.json"]
        and receipt["original_learning_receipt_sha256"]
        == base.source_hashes["inputs/original-learning-receipt.json"]
        and receipt["budget_receipt"] == source("inputs/budget-receipt.json")
        and receipt["ef_search"] == 640
        and receipt["tier"] == "light"
        and receipt["qualified_features"] == base.qualified_features
        and receipt["training_queries"] == len(base.queries)
        and receipt["training_groups"] == len({q.group for q in base.queries}),
        "returned receipt does not bind the original study",
    )
    require(
        all(
            receipt[k] is False
            for k in ("confirmation_outcomes_exported", "query_vectors_exported", "candidate_lock")
        )
        and receipt["provider_calls"] == 0
        and raw_verification["status"] == "verified"
        and raw_verification["original_labels_preserved"] is True
        and all(
            v[k] == 0
            for v in (raw_verification, saved)
            for k in ("provider_calls", "confirmation_queries")
        )
        and saved["candidate_lock"] is False,
        "returned evidence is not training-only",
    )
    for name, field in (
        ("training-feedback.jsonl", "training_feedback_sha256"),
        ("performance.json", "performance_sha256"),
        ("verification.json", "verification_sha256"),
    ):
        require(files["analysis/" + name] == receipt[field], "feedback receipt file hash differs")
    raw_hashes = {k: v for k, v in files.items() if k.startswith("blocks/")}
    require(raw_hashes == raw_verification["raw_files_sha256"], "raw file inventory differs")
    original_content = read_under(package, "inputs/training-640-light.jsonl")
    require(
        _sha(original_content) == base.source_hashes["inputs/training-640-light.jsonl"],
        "original training source changed",
    )
    originals = [decode(line) for line in original_content.splitlines()]
    original = {r["query_id"]: r for r in originals}
    updated = lines("analysis/training-feedback.jsonl")
    require(
        len(updated) == len(base.queries) and {r["query_id"] for r in updated} == set(original),
        "feedback query inventory differs",
    )
    new_rows = []
    new_count = 0
    new_keys = set()
    for row in updated:
        old = original[row["query_id"]]
        require(
            set(row) == set(old) | {"new_actual_labels"}
            and all(
                row[k] == old[k]
                for k in old
                if k not in ("labels", "oracle_checkpoint", "oracle_definition")
            ),
            "feedback changed original trajectory or native reference",
        )
        labels = {label["checkpoint_index"]: label for label in row["labels"]}
        require(
            len(labels) == len(row["labels"])
            and all(labels.get(label["checkpoint_index"]) == label for label in old["labels"]),
            "original label changed or stopping labels duplicated",
        )
        new = [
            label
            for label in row["labels"]
            if label["checkpoint_index"] not in {x["checkpoint_index"] for x in old["labels"]}
        ]
        require(
            type(row["new_actual_labels"]) is int
            and row["new_actual_labels"] == len(new)
            and 0 <= len(new) <= config["maximum_new_labels_per_query"],
            "new-label accounting differs",
        )
        for label in new:
            cp = label["checkpoint_index"]
            new_keys.add((row["query_id"], cp))
            require(
                1 <= cp <= len(row["states"])
                and label["prefix_matches"] is True
                and label["reference_prefix_sha256"] == digest(row["states"][:cp])
                and label["label_origin"] in ("candidate_first_stop", "safe_boundary_refinement"),
                "new label has no verified causal prefix or acquisition origin",
            )
        previous = next(q for q in base.queries if q.query_id == row["query_id"])
        outcomes = []
        for label in row["labels"]:
            preserves = (
                label["valid"]
                and label["returned_count"] == previous.effective_k
                and label["recall"] >= previous.native_recall
            )
            require(
                type(label["preserves_default"]) is bool
                and label["preserves_default"] == preserves,
                "proposal label differs",
            )
            outcomes.append(
                StopOutcome(
                    **{
                        k: label[k]
                        for k in (
                            "checkpoint_index",
                            "recall",
                            "returned_count",
                            "valid",
                            "actual_work",
                            "prefix_matches",
                        )
                    },
                    source_prefix_sha256=label["reference_prefix_sha256"],
                    source_ref=(
                        "returned/analysis/training-feedback.jsonl:"
                        + row["query_id"]
                        + ":"
                        + str(label["checkpoint_index"])
                    )
                    if label in new
                    else next(
                        o.source_ref
                        for o in previous.outcomes
                        if o.checkpoint_index == label["checkpoint_index"]
                    ),
                )
            )
        new_rows.append(
            TrainingQuery.model_validate(
                {**previous.model_dump(), "outcomes": [o.model_dump() for o in outcomes]}
            )
        )
        new_count += len(new)
    require(
        new_count == raw_verification["new_actual_labels"], "total acquired-label count differs"
    )
    merged_by_id = {r["query_id"]: r for r in updated}
    candidates = source("inputs/candidates.json")["candidates"]
    arms = source_arms(candidates, originals, profile, base.collection_groups)
    arm_map = {a.arm: a for a in arms}
    queries = {q.query_id: q for q in new_rows}
    pairs = []
    allocations = {}
    native_results: dict[str, tuple] = {}
    truths: dict[str, tuple] = {}
    for block in range(config["blocks"]):
        prefix = "blocks/block-" + str(block) + "/"
        status, exit_record = read(prefix + "status.json"), read(prefix + "job-exit.json")
        require(
            status["status"] == "complete"
            and status["provider_calls"] == 0
            and status["confirmation_queries"] == 0
            and status["candidate_lock"] is False
            and status["canonical_acceptance_established"] is False
            and exit_record["exit_code"] == 0
            and exit_record["completed_runs_unchanged"] is True
            and exit_record["confirmation_inputs_unchanged"] is True
            and read(prefix + "protected-source-before.json")
            == read(prefix + "protected-source-after.json"),
            "block execution or preservation failed",
        )
        allocations[str(block)] = str(exit_record["slurm_job_id"])
        runtime = read(prefix + "runtime-identity.json")
        expected_runtime = {
            "package_manifest_sha256": base.source_hashes["manifest.json"],
            "query_file_sha256": base.source_hashes["inputs/queries.jsonl"],
            "candidate_file_sha256": base.source_hashes["inputs/candidates.json"],
            "runtime_profile_hash": profile.fingerprint,
            "module_sha256": config["optimized_module_sha256"],
            "image_sha256": config["image_sha256"],
            "frozen_query_method_sha256": config["frozen_query_method_sha256"],
        }
        require(
            all(runtime[k] == v for k, v in expected_runtime.items()), "runtime identity differs"
        )
        require(
            read(prefix + "database-identity.json")["row_count"] == config["row_count"]
            and read(prefix + "settings.json")["hnsw.ef_search"] == "640"
            and read(prefix + "qualified-features.json")["qualified_features"]
            == base.qualified_features,
            "database settings or qualified getters differ",
        )
        raw_updates = lines(prefix + "training-updated.jsonl")
        require(
            len(raw_updates) == len(queries)
            and {r["query_id"]: r for r in raw_updates} == merged_by_id,
            "training outcomes differ across allocations",
        )
        acquired = lines(prefix + "new-labels.jsonl")
        require(
            len(acquired) == new_count
            and {(r["query_id"], r["checkpoint_index"]) for r in acquired} == new_keys,
            "raw acquired-label inventory differs",
        )
        for label in acquired:
            q = label["query_id"]
            require(
                label["group"] == original[q]["group"] and label["ef_search"] == 640,
                "acquired-label query group or search case differs",
            )
            expected = next(
                measured
                for measured in merged_by_id[q]["labels"]
                if measured["checkpoint_index"] == label["checkpoint_index"]
            )
            require(
                {k: label[k] for k in expected} == expected,
                "raw acquired label differs from returned export",
            )
        block_pairs: list[BenchmarkPair] = []
        for row in lines(prefix + "pairs.jsonl"):
            q, arm = queries.get(row["query_id"]), arm_map.get(row["arm"])
            require(q is not None and arm is not None, "pair is outside declared training arms")
            assert q is not None and arm is not None
            require(
                row["block"] == block
                and row["ef_search"] == 640
                and row["tier"] == "light"
                and row["kind"] == arm.kind
                and (row["group"], row["stratum"]) == tuple(row["query_id"].rsplit("-", 1)),
                "raw grouping or study case differs",
            )
            _validate_result(row, q)
            native = (row["native_ids"], row["native_distances"])
            truth = (row["truth_strict"], row["truth_ties"], row["truth_k"])
            require(
                native_results.setdefault(q.query_id, native) == native
                and truths.setdefault(q.query_id, truth) == truth,
                "native result/reference changed",
            )
            work = row["work"]
            require(
                work["frontier_snapshot_count"] == work["frontier_sort_count"] == 0
                and sum(
                    work[k]
                    for k in (
                        "frontier_traversal_ns",
                        "frontier_statistics_ns",
                        "frontier_sort_ns",
                        "frontier_quantile_ns",
                    )
                )
                <= work["feature_collection_ns"],
                "lightweight collector contract differs",
            )
            if arm.kind in ("continue", "matched-continue"):
                require(
                    native == (row["policy_ids"], row["policy_distances"])
                    and row["stop_reason"] != "policy_stop",
                    "continue control changed results",
                )
            cp = row["checkpoint_count"] if row["stop_reason"] == "policy_stop" else None
            block_pairs.append(
                BenchmarkPair(
                    **{
                        k: row[k]
                        for k in (
                            "query_id",
                            "policy_hash",
                            "regime",
                            "block",
                            "repetition",
                            "native_ms",
                            "policy_ms",
                            "native_recall",
                            "policy_recall",
                            "valid",
                            "returned_count",
                            "arm",
                            "native_outer_ms",
                            "policy_outer_ms",
                            "policy_already_activated",
                            "work",
                        )
                    },
                    stopped_checkpoint=cp,
                    source_ref=prefix + "pairs.jsonl:" + str(len(block_pairs) + 1),
                )
            )
        require(len(block_pairs) == status["retained_pairs"], "block retained-pair count differs")
        pairs.extend(block_pairs)
    corpus = type(base).model_validate(
        {
            **base.model_dump(),
            "queries": [q.model_dump() for q in new_rows],
            "source_hashes": {
                **base.source_hashes,
                **{"returned/" + k: v for k, v in files.items()},
            },
        }
    )
    envelope = ReturnedFeedback(
        corpus=corpus,
        benchmark=BenchmarkEvidence(
            schedule=TimingSchedule(
                blocks=list(range(config["blocks"])),
                cold_passes=config["cold_passes"],
                warm_passes=config["warm_passes"],
            ),
            warmups=config["warmups"],
            allocation_ids=allocations,
            timing_boundary="Backend reported latency; cold includes activation on warm data",
            arms=arms,
            pairs=pairs,
        ),
        import_receipt={},
    )
    # First-stop replay is independent of the export's saved predictions.
    from .evaluate import OfflineEvaluator

    evaluator = OfflineEvaluator(corpus)
    predictions = {}
    candidate_map = {c["id"]: c for c in candidates}
    for arm in arms:
        if arm.policy is None:
            continue
        report = evaluator.evaluate(arm.policy)
        if arm.kind == "candidate":
            actual = {r["query_id"]: r["checkpoint_index"] for r in report["decisions"]}
            require(
                actual == candidate_map[arm.arm]["predicted_checkpoints"],
                "interpreter first-stop predictions differ",
            )
        predictions[arm.arm] = {r["query_id"]: r for r in report["decisions"]}
    for pair in pairs:
        arm = arm_map[pair.arm]
        if arm.policy is not None:
            decision = predictions[pair.arm][pair.query_id]
            require(
                pair.stopped_checkpoint == decision["checkpoint_index"]
                and decision["status"] != "runtime_error",
                "actual first stop differs from shared interpreter replay",
            )
        else:
            require(
                pair.stopped_checkpoint == original[pair.query_id]["oracle_checkpoint"],
                "actual oracle differs from its retrospective checkpoint",
            )
        if pair.stopped_checkpoint is not None:
            query = queries[pair.query_id]
            require(
                pair.work["layer0_distance_evaluations"]
                == query.checkpoints[pair.stopped_checkpoint - 1].features[corpus.work_feature],
                "measured stop work differs from its causal checkpoint",
            )
            outcome = next(
                (o for o in query.outcomes if o.checkpoint_index == pair.stopped_checkpoint), None
            )
            if outcome is not None:
                require(
                    pair.returned_count == outcome.returned_count
                    and pair.valid
                    == (outcome.valid and outcome.returned_count == query.effective_k)
                    and pair.policy_recall == outcome.recall,
                    "measured policy result differs from actual stopping label",
                )
        if arm.kind == "candidate":
            require(
                decision["status"] not in ("unknown_stop", "runtime_error")
                and abs((pair.policy_recall - pair.native_recall) - decision["recall_delta"])
                <= 1e-12,
                "actual candidate outcome differs from interpreter replay",
            )
    parity = scorer_parity(envelope, saved, reader=read)
    require(
        len(pairs) == raw_verification["retained_pairs"] == saved["retained_pairs"],
        "overall retained-pair count differs",
    )
    import_receipt = {
        "schema_version": 1,
        "status": "verified",
        "scope": "learning",
        "source_corpus_hash": base.evidence_hash,
        "new_actual_labels": new_count,
        "actual_stop_labels": sum(len(q.outcomes) for q in new_rows),
        "retained_pairs": len(pairs),
        "budget_receipt": receipt["budget_receipt"],
        "scorer_parity": parity,
        "provider_calls": 0,
        "confirmation_queries": 0,
        "canonical_acceptance_established": False,
    }
    return ReturnedFeedback(
        corpus=corpus, benchmark=envelope.benchmark, import_receipt=import_receipt
    )


def scorer_parity(evidence, saved, reader=None):
    benchmark, corpus = evidence.benchmark, evidence.corpus
    differences = []
    reports = {}
    per_block = {}
    for block in benchmark.schedule.blocks:
        block_rows = [p for p in benchmark.pairs if p.block == block]
        result = {
            a.arm: {
                regime: with_filters(
                    [p for p in block_rows if p.arm == a.arm and p.regime == regime],
                    corpus.queries,
                    corpus.objective,
                )
                for regime in REGIMES
            }
            for a in benchmark.arms
        }
        if reader is not None:
            differences.extend(
                compare_numeric(
                    reader("blocks/block-" + str(block) + "/summary.json"),
                    result,
                    path="block/" + str(block),
                )
            )
        per_block[str(block)] = result
    for arm in benchmark.arms:
        reports[arm.arm] = {
            regime: with_filters(
                [p for p in benchmark.pairs if p.arm == arm.arm and p.regime == regime],
                corpus.queries,
                corpus.objective,
            )
            for regime in REGIMES
        }
    differences.extend(compare_numeric(saved["overall"], reports, path="overall"))
    differences.extend(compare_numeric(saved["per_block"], per_block, path="per_block"))
    candidates = {
        a.arm: {
            r: {
                "training_feasible": feasible(reports[a.arm][r], corpus.objective),
                "report": reports[a.arm][r],
            }
            for r in REGIMES
        }
        for a in benchmark.arms
        if a.kind == "candidate"
    }
    differences.extend(compare_numeric(saved["candidates"], candidates, path="candidates"))
    return {
        "status": "passed",
        "arms": len(reports),
        "allocation_blocks": len(per_block),
        "tolerance": 1e-12,
        "rounding_fields": len(differences),
        "maximum_absolute_difference": max((r["absolute_error"] for r in differences), default=0.0),
        "candidate_feasibility": {
            a: {r: v["training_feasible"] for r, v in rr.items()} for a, rr in candidates.items()
        },
        "oracle_is_deployable": False,
    }


def import_returned_feedback(
    package: Path, campaign: Path, verification: Path, profile: RuntimeProfile
) -> ReturnedFeedback:
    try:
        return _import_feedback(package, campaign, verification, profile)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, tarfile.TarError) as exc:
        raise AgentError(f"invalid returned feedback: {exc}") from None
