import hashlib
import json

import pytest
from learning_cases import make_corpus

from fannagent.api import AgentError, validate_policy
from fannagent.learning.importers import import_torch_training
from fannagent.store import digest


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False))


def repin(package):
    files = {
        str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in package.rglob("*")
        if p.is_file() and p.name != "manifest.json"
    }
    save(package / "manifest.json", {"schema_version": 1, "files": files})


def package_fixture(tmp_path, groups=6):
    corpus = make_corpus(groups)
    package = tmp_path / "training-package"
    package.mkdir()
    config = {
        "name": "torch-reviews-policy-feedback",
        "ef_search_levels": [640],
        "tiers": ["light"],
        "confirmation_queries_allowed": 0,
        "maximum_model_calls_on_Torch": 0,
        "filters": ["plain", "filtered"],
        "learning_groups": groups,
        "recall_tolerance": 0.005,
        "minimum_native_recall": 0.95,
        "bootstrap_samples": 300,
        "seed": 20261019,
    }
    queries, rows = [], []
    for query in corpus.queries:
        queries.append(
            {
                "split": "learning",
                "group": query.group,
                "query": {"id": query.query_id, "k": 10, "vector": [1.0, 0.0]},
            }
        )
        rows.append(
            {
                "query_id": query.query_id,
                "group": query.group,
                "ef_search": 640,
                "checkpoint_count": len(query.checkpoints),
                "native_recall": query.native_recall,
                "native_work": query.native_work,
                "oracle_checkpoint": 3,
                "oracle_definition": "tested native-preserving stop",
                "states": [c.model_dump() for c in query.checkpoints],
                "labels": [
                    {
                        "checkpoint_index": o.checkpoint_index,
                        "recall": o.recall,
                        "returned_count": o.returned_count,
                        "valid": o.valid,
                        "actual_work": o.actual_work,
                        "prefix_matches": True,
                        "preserves_default": o.recall >= query.native_recall,
                        "reference_prefix_sha256": o.source_prefix_sha256,
                    }
                    for o in query.outcomes
                ],
            }
        )
    # This fixture uses a different counter name; the Torch adapter requires its real work name.
    raw_profile = corpus.profile.model_dump()
    definition = raw_profile["features"].pop("work")
    definition["name"] = "layer0_distance_evaluations"
    raw_profile["features"][definition["name"]] = definition
    profile = type(corpus.profile).model_validate(raw_profile)
    names = ["layer0_distance_evaluations" if n == "work" else n for n in corpus.qualified_features]
    for row in rows:
        for checkpoint in row["states"]:
            checkpoint["features"]["layer0_distance_evaluations"] = checkpoint["features"].pop(
                "work"
            )
    save(package / "experiment.json", config)
    save(
        package / "inputs/original-learning-receipt.json",
        {
            "status": "complete",
            "confirmation_outcomes_exported": False,
            "canonical_test_consumed": False,
            "package_manifest_sha256": "a" * 64,
            "qualified_features": {"640/light": names},
        },
    )
    save(
        package / "inputs/split-provenance.json",
        {
            "training_confirmation_disjoint": True,
            "confirmation_vectors_in_package": False,
            "confirmation_outcomes_in_package": False,
            "base_manifest_sha256": "a" * 64,
            "training_query_ids_sha256": digest(sorted(q.query_id for q in corpus.inventory)),
        },
    )
    for filename, items in (("queries.jsonl", queries), ("training-640-light.jsonl", rows)):
        (package / "inputs" / filename).write_text("\n".join(json.dumps(r) for r in items) + "\n")
    policy = {"name": "source", "root": "continue", "feature_groups": ["basic"]}
    save(
        package / "inputs/candidates.json",
        {
            "feature_pool": names,
            "training_view_sha256": hashlib.sha256(
                (package / "inputs/training-640-light.jsonl").read_bytes()
            ).hexdigest(),
            "candidates": [
                {"policy": policy, "policy_hash": validate_policy(policy, profile).policy_hash}
            ],
        },
    )
    repin(package)
    return package, profile


def test_import_is_data_only_keeps_native_provenance_and_excludes_vectors(tmp_path):
    package, profile = package_fixture(tmp_path)
    before = {str(p): p.read_bytes() for p in package.rglob("*") if p.is_file()}
    result = import_torch_training(package, profile)
    assert len(result.queries) == 12
    assert sum(len(q.outcomes) for q in result.queries) == 24
    assert "vector" not in result.model_dump_json()
    assert result.queries[0].outcomes[0].source_prefix_sha256 == digest([0, "plain", 1])
    assert {str(p): p.read_bytes() for p in package.rglob("*") if p.is_file()} == before


def test_import_rejects_changed_inputs_and_runtime_profile(tmp_path):
    package, profile = package_fixture(tmp_path)
    changed = profile.model_copy(update={"checkpoint_interval": 20})
    with pytest.raises(AgentError, match="runtime profile"):
        import_torch_training(package, changed)
    (package / "inputs/training-640-light.jsonl").write_text("{}\n")
    with pytest.raises(AgentError, match="hash differs"):
        import_torch_training(package, profile)


@pytest.mark.parametrize(
    "field,value",
    [
        ("training_confirmation_disjoint", False),
        ("confirmation_vectors_in_package", True),
        ("confirmation_outcomes_in_package", True),
    ],
)
def test_import_refuses_confirmation_boundaries_even_with_valid_checksums(tmp_path, field, value):
    package, profile = package_fixture(tmp_path)
    path = package / "inputs/split-provenance.json"
    data = json.loads(path.read_text())
    data[field] = value
    save(path, data)
    repin(package)
    with pytest.raises(AgentError, match="training-only"):
        import_torch_training(package, profile)


def test_import_rejects_confirmation_record_and_symlink(tmp_path):
    package, profile = package_fixture(tmp_path)
    path = package / "inputs/queries.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["split"] = "confirmation"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    repin(package)
    with pytest.raises(AgentError, match="non-learning"):
        import_torch_training(package, profile)
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    (package / "escape").symlink_to(outside)
    manifest = json.loads((package / "manifest.json").read_text())
    manifest["files"]["escape"] = hashlib.sha256(outside.read_bytes()).hexdigest()
    save(package / "manifest.json", manifest)
    with pytest.raises(AgentError, match="symbolic"):
        import_torch_training(package, profile)
