"""Trusted development evidence, policy replay, and the original tie-aware scorer."""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass
from importlib.machinery import PathFinder
from pathlib import Path
from types import SimpleNamespace

from rb_plan import (
    CHECKPOINTS,
    PACKAGE,
    PILOT_BLOCK,
    PILOT_MANIFEST,
    PROFILES,
    ROOT,
    SEED_ID,
    digest,
    file_sha,
    pinned,
    pinned_lines,
    require,
)

PILOT_REFS = "45094511cd1be8849a33c5fd0a617a9f8eaf6eb2affc6edbc46d938e04bfe73f"
PILOT_PROOFS = "61045ea8a1bdefc424f201d47553cac4a4512c6a159b560cd7fc3c6c23340795"
ACQUIRE = (
    Path("trials/torch-reviews-results/reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y")
    / "acquire"
)
ACQUIRE_PROOFS = (
    "ccd270a742a9224b34cab3389702f52e2a0a7dbfeb0393869c6e0defe7f08dc6",
    "46ca2a8934d0f6583cdb92a80fe24ca6cd3e0242caf9a1f7756123872ca6c3ca",
)
DATASET = Path("trials/torch-reviews-first/inputs/reviews.parquet")
DATASET_SHA = "06eae31a43ecfd63a647f6fa93a9c00bcb2350ca6fe2f2bcd35d007c13b2e4ee"


def load_frozen(root=ROOT):
    """Load the pinned pilot code in a clean process, with provider imports disabled."""
    package = (Path(root) / PACKAGE).resolve()
    pins = json.loads(pinned(package / "manifest.json", PILOT_MANIFEST))["files"]
    names = (
        "contract",
        "legacy_contract",
        "legacy_execution",
        "reference_backend",
        "fd_contract",
        "fd_execution",
        "fd_policy_tools",
        "policy",
        "execution",
        "no_models",
        "database",
        "runtime_base",
        "design",
    )
    roots = {*names, "fannagent", "fannagent_pgvector"}
    require(not any(name.split(".")[0] in roots for name in sys.modules), "Use a clean process")
    wanted = {f"{name}.py" for name in names}
    wanted.update(path for path in pins if path.startswith("vendor/") and path.endswith(".py"))
    vendor = package / "vendor"
    found = {str(p.relative_to(package)) for p in vendor.rglob("*.py")}
    require(found == {p for p in wanted if p.startswith("vendor/")}, "Unpinned vendor code")
    require(not any(package.rglob("*.pyc")), "Unexpected bytecode in the frozen package")
    for name in sorted(wanted):
        path = package / name
        require(path.resolve() == path, f"Unexpected code path: {name}")
        pinned(path, pins[name])
    search_path = [str(package), str(vendor)]
    for name in roots:
        spec = PathFinder.find_spec(name, search_path)
        path = package / f"{name}.py" if name in names else vendor / name / "__init__.py"
        require(spec is not None and spec.origin == str(path), f"Frozen import shadowed: {name}")
    sys.dont_write_bytecode = True
    sys.path[:0] = search_path
    try:
        importlib.import_module("no_models").enforce()
        policy = importlib.import_module("policy")
        execution = importlib.import_module("execution")
        legacy = importlib.import_module("legacy_execution")
        feature = importlib.import_module("fd_execution")
        predictor = importlib.import_module("fd_policy_tools")
        evaluation = importlib.import_module("fannagent.evaluation")
        api = importlib.import_module("fannagent.api")
        profiles = importlib.import_module("fannagent_pgvector.profiles")
        database = importlib.import_module("database")
        runtime = importlib.import_module("runtime_base")
        return SimpleNamespace(
            policy=policy,
            execution=execution,
            native=legacy.execute,
            prefix=legacy.prefix,
            qualify=feature.qualify,
            predict=predictor.predict,
            profile=profiles.PROFILE,
            exact_truth=api.ExactTruth,
            score=evaluation.score,
            restore=database.prepare,
            stop=database.stop,
            verify_import=runtime.verify_import,
            verify_index=runtime.verify_index,
        )
    finally:
        # Later frozen functions use lazy imports from these same, verified roots.
        require(sys.path[:2] == [str(package), str(vendor)], "Frozen import path changed")


def eligible_ids(root=ROOT):
    from pyarrow import parquet

    path = Path(root) / DATASET
    require(
        path.is_file() and not path.is_symlink() and file_sha(path) == DATASET_SHA,
        "Indexed dataset digest changed",
    )
    rows = []
    for batch in parquet.ParquetFile(path).iter_batches(
        columns=["source_id", "metadata.total_votes"], use_threads=False
    ):
        rows.extend((row["source_id"], row["metadata"]["total_votes"]) for row in batch.to_pylist())
    rows.sort()
    require(
        len(rows) == 247286 and len({source for source, _ in rows}) == len(rows),
        "Indexed source ID coverage changed",
    )
    # Snapshot assigns logical IDs by ascending integral source ID.
    eligible = {"unfiltered": frozenset(range(len(rows)))}
    for threshold in (32, 108):
        eligible[f"votes{threshold}"] = frozenset(
            index
            for index, (_, votes) in enumerate(rows)
            if votes is not None and votes >= threshold
        )
    require(
        [len(ids) for ids in eligible.values()] == [247286, 123692, 49498],
        "Filter eligibility counts changed",
    )
    return eligible


def outcome(row, prefix):
    return [row[f"{prefix}_ids"], row[f"{prefix}_distances"]]


@dataclass(frozen=True)
class Evidence:
    references: dict
    eligible: dict
    policies: dict
    identities: dict
    outcomes: dict


def stop_proofs(root, candidate_profile=None):
    proofs = {}

    def add(profile, row):
        key = (profile, row["query_id"], row["checkpoint"])
        record = (row["observed_prefix_sha256"], outcome(row, "policy"))
        require(proofs.setdefault(key, record) == record, f"Saved stop proof differs: {key}")

    package = root / PACKAGE
    manifest = json.loads(pinned(package / "manifest.json", PILOT_MANIFEST))["files"]
    policies = json.loads(pinned(package / "candidates.json", manifest["candidates.json"]))
    pilot_profiles = {name: entry["policy"]["profile"] for name, entry in policies.items()}
    pilot_profiles["sparse-oracle"] = "light19"
    for row in pinned_lines(root / PILOT_BLOCK / "proofs.jsonl", PILOT_PROOFS):
        if row["checkpoint"] is not None:
            require(row["native_bypass"] is False, "A bypass cannot prove a stop")
            add(pilot_profiles[row["arm"].removeprefix("matched-")], row)
    if candidate_profile in ("static23", "progress34"):
        families = {"base": "static23", "local": "progress34"}
        for part, expected in enumerate(ACQUIRE_PROOFS):
            path = root / ACQUIRE / f"part-{part}" / "proofs.jsonl"
            for row in pinned_lines(path, expected):
                add(families[row["family"]], row)
    return proofs


def expected_outcome(frozen, raw, case, ref, states, proofs):
    bypass = frozen.policy.route(case.query) not in raw["eligible"]
    require(frozen.policy.route(case.query) == case.stratum, "Actual predicate route changed")
    checkpoint = None
    prefix = None
    result = ref["native"]
    if not bypass:
        # The validated canonical guard makes every off-grid observation continue.
        checkpoint = frozen.predict(
            raw["tree"], [s for s in states if s["checkpoint_index"] in CHECKPOINTS], frozen.profile
        )
        prefix = states if checkpoint is None else states[:checkpoint]
        if checkpoint is not None:
            key = (raw["profile"], case.id, checkpoint)
            require(key in proofs, f"Missing compatible actual stop: {key}")
            expected_prefix, result = proofs[key]
            require(digest(prefix) == expected_prefix, f"Saved stop prefix differs: {key}")
    return {
        "bypass": bypass,
        "checkpoint_count": None if bypass else len(prefix),
        "stop": checkpoint is not None,
        "prefix": None if bypass else digest(prefix),
        "output": result,
    }


def load_evidence(plan, frozen, candidate=None, root=ROOT):
    root = Path(root)
    seed, seed_id = frozen.policy.validate(plan.seed, plan.config)
    require(seed_id == SEED_ID, "Credited seed identity changed")
    policies = {"seed": seed}
    identities = {"seed": seed_id}
    if candidate is not None:
        raw, identity = frozen.policy.validate(candidate, plan.config)
        require(identity != seed_id, "Proposal duplicates the credited seed")
        policies["candidate"] = raw
        identities["candidate"] = identity
    proofs = stop_proofs(root, policies.get("candidate", {}).get("profile"))
    cases = plan.cases
    references = {}
    outcomes = {family: {} for family in policies}
    for row in pinned_lines(root / PILOT_BLOCK / "references.jsonl", PILOT_REFS):
        case = cases[row["query_id"]]
        require(case.id not in references and case.group == row["group"], "Saved case changed")
        states = row["states"]
        require(set(states) == set(PROFILES), "Saved continue profiles changed")
        ref = {
            "query_id": case.id,
            "truth": {key: row[f"truth_{key}"] for key in ("strict", "ties", "k")},
            "native": outcome(row, "native"),
            "continues": {
                profile: {"length": len(trace), "digest": digest(trace)}
                for profile, trace in states.items()
            },
        }
        references[case.id] = ref
        for family, raw in policies.items():
            outcomes[family][case.id] = expected_outcome(
                frozen, raw, case, ref, states[raw["profile"]], proofs
            )
    require(set(references) == set(cases), "Saved reference coverage changed")
    return Evidence(references, eligible_ids(root), policies, identities, outcomes)
